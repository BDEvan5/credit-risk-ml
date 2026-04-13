"""Train an XGBoost credit-default model (sklearn Pipeline) and log to MLflow.

Run from the repository root::

    uv run python -m src.train
    uv run python -m src.train --config my_overrides.json

Optional JSON is merged onto :class:`TrainConfig` (flat keys, same names as fields).
"""

from __future__ import annotations

import argparse
import json
import logging
import resource
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Running `python src/train.py` puts `src/` on sys.path, not the repo root, so
# `import src.*` fails unless the project root is added (``python -m src.train`` does this).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import duckdb
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier

from src.features import build_feature_matrix
from src.metrics import binary_classifier_metrics, format_metrics_lines
from src.mlflow_helpers import DEFAULT_EXPERIMENT, log_pipeline_run

logger = logging.getLogger(__name__)


def _peak_rss_mb() -> float:
    """Best-effort peak resident set size (MB) for this process (POSIX ``getrusage``)."""
    try:
        ru = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except (OSError, ValueError):
        return float("nan")
    if sys.platform == "darwin":
        return ru / (1024.0 * 1024.0)
    return ru / 1024.0


def _log_autoresearch_summary(
    *,
    roc_auc: float,
    training_seconds: float,
    total_seconds: float,
    n_train: int,
    n_test: int,
    n_features: int,
) -> None:
    """Print a fixed-width block for agents (grep ``^roc_auc:`` / ``^peak_memory_mb:``)."""
    def _num(x: float) -> str:
        return "nan" if x != x else f"{x:.6f}"

    peak_mb = _peak_rss_mb()
    lines = (
        "---",
        f"roc_auc:          {_num(roc_auc)}",
        f"training_seconds: {training_seconds:.1f}",
        f"total_seconds:    {total_seconds:.1f}",
        f"peak_memory_mb:   {_num(peak_mb)}",
        f"n_train:          {n_train}",
        f"n_test:           {n_test}",
        f"n_features:       {n_features}",
    )
    for line in lines:
        logger.info("%s", line)
def _sklearn_safe_features(X: pd.DataFrame) -> pd.DataFrame:
    """Normalize DuckDB/pandas nulls and dtypes for sklearn ``SimpleImputer``.

    DuckDB ``.df()`` can return ``pd.NA`` (and nullable extension dtypes). Object-column
    imputation uses equality checks that raise on ``pd.NA``; nullable integers may also be
    excluded from ``select_dtypes(include=[np.number])`` depending on pandas version.
    """
    out = X.replace(pd.NA, np.nan)
    for col in out.columns:
        s = out[col]
        if pd.api.types.is_extension_array_dtype(s.dtype) and pd.api.types.is_numeric_dtype(
            s.dtype
        ):
            out[col] = s.astype("float64")
    return out


@dataclass
class TrainConfig:
    """All training, data, model, and MLflow settings in one place."""

    random_state: int = 42
    target_col: str = "TARGET"
    id_col: str = "SK_ID_CURR"

    duckdb_path: Path = field(default_factory=lambda: _REPO_ROOT / "data" / "home_credit.db")
    use_cached_features: bool = False
    sample_frac: float | None = None
    test_size: float = 0.2
    validation_size: float = 0.15

    numeric_imputer_strategy: str = "median"
    categorical_imputer_strategy: str = "most_frequent"
    onehot_max_categories: int = 50
    onehot_min_frequency: float = 0.001
    column_transformer_n_jobs: int = -1

    n_estimators: int = 400
    max_depth: int = 5
    learning_rate: float = 0.05
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    reg_lambda: float = 1.0
    reg_alpha: float = 0.0
    gamma: float = 0.0
    min_child_weight: float = 1.0
    max_delta_step: float = 0.0
    n_jobs: int = -1
    tree_method: str = "hist"
    eval_metric: str = "logloss"
    early_stopping_rounds: int | None = None

    experiment_name: str = DEFAULT_EXPERIMENT
    run_name: str = "xgboost_train"
    signature_sample_rows: int = 500

    model_output_path: Path | None = field(
        default_factory=lambda: _REPO_ROOT / "model" / "xgb_pipeline.joblib"
    )


def load_config(path: Path | None) -> TrainConfig:
    """Defaults, optionally merged with a flat JSON object."""
    cfg = TrainConfig()
    if path is None:
        return cfg
    overrides = json.loads(path.read_text())
    d = asdict(cfg)
    d.update(overrides)
    for key in ("duckdb_path", "model_output_path"):
        val = d.get(key)
        if val is not None and not isinstance(val, Path):
            d[key] = Path(val)
    return TrainConfig(**d)


def train(cfg: TrainConfig) -> Pipeline:
    t_total_start = time.perf_counter()
    training_seconds = 0.0

    db = cfg.duckdb_path
    if not db.exists():
        raise FileNotFoundError(
            f"DuckDB database not found at {db}. Load data per project README."
        )

    conn = duckdb.connect(str(db))
    try:
        df = build_feature_matrix(
            conn, force_rebuild=not cfg.use_cached_features
        )
    finally:
        conn.close()

    if cfg.sample_frac is not None:
        df = df.sample(
            frac=cfg.sample_frac,
            random_state=cfg.random_state,
        ).reset_index(drop=True)

    if cfg.target_col not in df.columns or cfg.id_col not in df.columns:
        raise KeyError(
            f"Expected columns {cfg.target_col!r} and {cfg.id_col!r} in feature frame."
        )

    X = df.drop(columns=[cfg.target_col, cfg.id_col])
    # Coerce pandas extension-array dtypes (Int64, boolean, etc.) to numpy types
    # so that pd.NA becomes np.nan and sklearn imputers work correctly.
    X = X.where(X.notna(), np.nan)
    for col in X.select_dtypes(include="number").columns:
        if pd.api.types.is_extension_array_dtype(X[col].dtype):
            X[col] = X[col].astype("float64")
    X = _sklearn_safe_features(df.drop(columns=[cfg.target_col, cfg.id_col]))
    y = df[cfg.target_col]
    num_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = [c for c in X.columns if c not in num_cols]

    X_temp, X_test, y_temp, y_test = train_test_split(
        X,
        y,
        test_size=cfg.test_size,
        random_state=cfg.random_state,
        stratify=y,
    )

    X_val, y_val = None, None
    if cfg.early_stopping_rounds is not None:
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp,
            y_temp,
            test_size=cfg.validation_size,
            random_state=cfg.random_state,
            stratify=y_temp,
        )
    else:
        X_train, y_train = X_temp, y_temp

    numeric_pipe = Pipeline(
        steps=[("imputer", SimpleImputer(strategy=cfg.numeric_imputer_strategy))]
    )
    categorical_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy=cfg.categorical_imputer_strategy)),
            (
                "onehot",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=True,
                    max_categories=cfg.onehot_max_categories,
                    min_frequency=cfg.onehot_min_frequency,
                ),
            ),
        ]
    )
    preprocess = ColumnTransformer(
        transformers=[
            ("num", numeric_pipe, num_cols),
            ("cat", categorical_pipe, cat_cols),
        ],
        n_jobs=cfg.column_transformer_n_jobs,
    )

    scale_pos_weight = float((y_train == 0).sum() / max((y_train == 1).sum(), 1))
    clf = XGBClassifier(
        n_estimators=cfg.n_estimators,
        max_depth=cfg.max_depth,
        learning_rate=cfg.learning_rate,
        subsample=cfg.subsample,
        colsample_bytree=cfg.colsample_bytree,
        reg_lambda=cfg.reg_lambda,
        reg_alpha=cfg.reg_alpha,
        gamma=cfg.gamma,
        min_child_weight=cfg.min_child_weight,
        max_delta_step=cfg.max_delta_step,
        random_state=cfg.random_state,
        n_jobs=cfg.n_jobs,
        tree_method=cfg.tree_method,
        eval_metric=cfg.eval_metric,
        scale_pos_weight=scale_pos_weight,
    )
    pipeline = Pipeline([("preprocess", preprocess), ("clf", clf)])

    logger.info(
        "Training: n_train=%s n_val=%s n_test=%s n_features=%s",
        len(X_train),
        len(X_val) if X_val is not None else 0,
        len(X_test),
        X.shape[1],
    )

    t_fit_start = time.perf_counter()
    if cfg.early_stopping_rounds is None:
        pipeline.fit(X_train, y_train)
    else:
        if X_val is None or y_val is None:
            raise ValueError(
                "Internal error: validation set missing with early_stopping_rounds set."
            )
        pre = pipeline.named_steps["preprocess"]
        est = pipeline.named_steps["clf"]
        X_tr = pre.fit_transform(X_train, y_train)
        X_va = pre.transform(X_val)
        est.fit(
            X_tr,
            y_train,
            eval_set=[(X_va, y_val)],
            early_stopping_rounds=cfg.early_stopping_rounds,
            verbose=False,
        )
    training_seconds = time.perf_counter() - t_fit_start

    y_score = pipeline.predict_proba(X_test)[:, 1]
    y_pred = pipeline.predict(X_test)
    test_metrics = binary_classifier_metrics(y_test, y_score, y_pred=y_pred)

    mlflow_params: dict = {}
    for k, v in asdict(cfg).items():
        if isinstance(v, Path):
            mlflow_params[k] = str(v.resolve())
        else:
            mlflow_params[k] = v
    mlflow_params.update(
        {
            "scale_pos_weight": scale_pos_weight,
            "n_train": len(X_train),
            "n_val": len(X_val) if X_val is not None else 0,
            "n_test": len(X_test),
            "n_features": int(X.shape[1]),
            "n_numeric_cols": len(num_cols),
            "n_categorical_cols": len(cat_cols),
        }
    )
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        mlflow_params["git_sha_short"] = sha
    except (OSError, subprocess.CalledProcessError):
        pass

    n_sig = min(cfg.signature_sample_rows, len(X_test))
    log_pipeline_run(
        cfg.run_name,
        pipeline,
        metrics=test_metrics,
        params=mlflow_params,
        signature_sample=X_test.iloc[:n_sig],
        experiment_name=cfg.experiment_name,
    )

    logger.info("Test metrics:\n%s", format_metrics_lines(test_metrics))

    total_seconds = time.perf_counter() - t_total_start
    roc_auc = float(test_metrics.get("roc_auc", float("nan")))
    _log_autoresearch_summary(
        roc_auc=roc_auc,
        training_seconds=training_seconds,
        total_seconds=total_seconds,
        n_train=len(X_train),
        n_test=len(X_test),
        n_features=int(X.shape[1]),
    )

    if cfg.model_output_path is not None:
        out = Path(cfg.model_output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(pipeline, out)
        logger.info("Saved pipeline to %s", out.resolve())

    return pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Train XGBoost credit-default pipeline.")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional JSON file of flat TrainConfig overrides.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Optional path to write the same logs as stderr (e.g. run.log for autoresearch).",
    )
    parser.add_argument(
        "--rebuild-features",
        action="store_true",
        help="Rebuild data/features.parquet from SQL (required after edits to sql/features/ or features.py).",
    )
    args = parser.parse_args()

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, args.log_level))
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    root.addHandler(sh)
    if args.log_file is not None:
        args.log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(args.log_file, mode="w", encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)
    cfg = load_config(args.config)
    if args.rebuild_features:
        cfg.use_cached_features = False
    train(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
