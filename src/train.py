"""Train an XGBoost credit-default model behind a sklearn Pipeline and log to MLflow.

Run from the repository root, for example::

    uv run python -m src.train
    uv run python -m src.train --config path/to/train_config.json

Configuration is expressed as :class:`TrainConfig` (dataclasses only). Optional JSON
overrides are deep-merged onto the defaults; nested keys match the dataclass field names.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path
from types import UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints

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

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _repo_root() -> Path:
    return _REPO_ROOT


@dataclass(frozen=True)
class DataConfig:
    """Paths and row-level sampling for the feature matrix."""

    duckdb_path: Path = field(
        default_factory=lambda: _repo_root() / "data" / "home_credit.db"
    )
    use_cached_features: bool = True
    sample_frac: float | None = None
    test_size: float = 0.2
    """Holdout fraction for the test set (stratified)."""
    validation_size: float = 0.15
    """Fraction of the non-test data used for early stopping (when enabled)."""


@dataclass(frozen=True)
class PreprocessConfig:
    """ColumnTransformer + OHE settings aligned with ``02_modelling.ipynb``."""

    numeric_imputer_strategy: str = "median"
    categorical_imputer_strategy: str = "most_frequent"
    onehot_max_categories: int = 50
    onehot_min_frequency: float = 0.001
    column_transformer_n_jobs: int = -1


@dataclass(frozen=True)
class XGBoostConfig:
    """Hyperparameters passed to :class:`xgboost.XGBClassifier`."""

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
    random_state: int = 42
    n_jobs: int = -1
    tree_method: str = "hist"
    eval_metric: str = "logloss"
    early_stopping_rounds: int | None = None
    """If set, fits with a validation fold and passes ``early_stopping_rounds`` to XGBoost."""


@dataclass(frozen=True)
class MLflowConfig:
    experiment_name: str = DEFAULT_EXPERIMENT
    run_name: str = "xgboost_train"
    signature_sample_rows: int = 500


@dataclass(frozen=True)
class TrainConfig:
    """Top-level training run configuration."""

    random_state: int = 42
    target_col: str = "TARGET"
    id_col: str = "SK_ID_CURR"
    data: DataConfig = field(default_factory=DataConfig)
    preprocess: PreprocessConfig = field(default_factory=PreprocessConfig)
    xgb: XGBoostConfig = field(default_factory=XGBoostConfig)
    mlflow: MLflowConfig = field(default_factory=MLflowConfig)
    model_output_path: Path | None = field(
        default_factory=lambda: _repo_root() / "model" / "xgb_pipeline.joblib"
    )
    """If ``None``, the fitted pipeline is not written to disk."""


def _asdict_paths_to_jsonable(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj.resolve())
    if is_dataclass(obj):
        return _asdict_paths_to_jsonable(asdict(obj))
    if isinstance(obj, dict):
        return {k: _asdict_paths_to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_asdict_paths_to_jsonable(v) for v in obj]
    return obj


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, val in override.items():
        if (
            key in out
            and isinstance(out[key], dict)
            and isinstance(val, dict)
        ):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def _dict_to_dataclass(cls: type, d: dict[str, Any]) -> Any:
    """Build a dataclass instance from a dict, recursing into nested dataclasses."""
    globalns = sys.modules[cls.__module__].__dict__
    hints = get_type_hints(cls, globalns=globalns)
    kwargs: dict[str, Any] = {}
    for f in fields(cls):
        if f.name not in d:
            raise KeyError(f"Missing key {f.name!r} for {cls.__name__}")
        raw = d[f.name]
        ftype = hints[f.name]
        if is_dataclass(ftype):
            kwargs[f.name] = _dict_to_dataclass(ftype, raw)
            continue
        if ftype is Path:
            kwargs[f.name] = Path(raw)
            continue
        origin = get_origin(ftype)
        args = get_args(ftype)
        optional = bool(args and type(None) in args)
        if origin in (Union, UnionType) or isinstance(ftype, UnionType):
            if raw is None and optional:
                kwargs[f.name] = None
            elif args and Path in args and raw is not None:
                kwargs[f.name] = Path(raw)
            elif args and Path in args and raw is None:
                kwargs[f.name] = None
            else:
                kwargs[f.name] = raw
            continue
        kwargs[f.name] = raw
    return cls(**kwargs)


def train_config_from_json(path: Path) -> TrainConfig:
    """Load JSON overrides and merge onto :func:`default_train_config`."""
    override = json.loads(path.read_text())
    base = _asdict_paths_to_jsonable(default_train_config())
    merged = _deep_merge(base, override)
    return _dict_to_dataclass(TrainConfig, merged)


def default_train_config() -> TrainConfig:
    """Default training configuration (same defaults as module-level dataclasses)."""
    return TrainConfig()


def dataclass_to_mlflow_params(cfg: TrainConfig, prefix: str = "") -> dict[str, Any]:
    """Flatten nested dataclasses into dot-separated keys for MLflow."""
    out: dict[str, Any] = {}

    def walk(obj: Any, pfx: str) -> None:
        if is_dataclass(obj):
            for f in fields(obj):
                val = getattr(obj, f.name)
                key = f"{pfx}.{f.name}" if pfx else f.name
                if is_dataclass(val):
                    walk(val, key)
                elif isinstance(val, Path):
                    out[key] = str(val.resolve())
                else:
                    out[key] = val
        else:
            raise TypeError("expected dataclass")

    walk(cfg, prefix)
    return out


def _git_sha_short() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_repo_root(),
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def load_feature_frame(cfg: TrainConfig) -> pd.DataFrame:
    """Load the training table via DuckDB and :func:`build_feature_matrix`."""
    db = cfg.data.duckdb_path
    if not db.exists():
        raise FileNotFoundError(
            f"DuckDB database not found at {db}. Load data per project README."
        )
    conn = duckdb.connect(str(db))
    try:
        if cfg.data.use_cached_features:
            df = build_feature_matrix(conn, force_rebuild=False)
        else:
            df = build_feature_matrix(conn, force_rebuild=True)
    finally:
        conn.close()

    if cfg.data.sample_frac is not None:
        df = df.sample(
            frac=cfg.data.sample_frac,
            random_state=cfg.random_state,
        ).reset_index(drop=True)

    return df


def build_tree_preprocessor(
    cfg: TrainConfig,
    num_cols: list[str],
    cat_cols: list[str],
) -> ColumnTransformer:
    """ColumnTransformer with median impute + OHE (same layout as ``02_modelling.ipynb``)."""
    pre = cfg.preprocess
    numeric_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy=pre.numeric_imputer_strategy)),
        ]
    )
    categorical_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy=pre.categorical_imputer_strategy)),
            (
                "onehot",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=True,
                    max_categories=pre.onehot_max_categories,
                    min_frequency=pre.onehot_min_frequency,
                ),
            ),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("num", numeric_pipe, num_cols),
            ("cat", categorical_pipe, cat_cols),
        ],
        n_jobs=pre.column_transformer_n_jobs,
    )


def make_xgb_classifier(cfg: TrainConfig, scale_pos_weight: float) -> XGBClassifier:
    x = cfg.xgb
    return XGBClassifier(
        n_estimators=x.n_estimators,
        max_depth=x.max_depth,
        learning_rate=x.learning_rate,
        subsample=x.subsample,
        colsample_bytree=x.colsample_bytree,
        reg_lambda=x.reg_lambda,
        reg_alpha=x.reg_alpha,
        gamma=x.gamma,
        min_child_weight=x.min_child_weight,
        max_delta_step=x.max_delta_step,
        random_state=x.random_state,
        n_jobs=x.n_jobs,
        tree_method=x.tree_method,
        eval_metric=x.eval_metric,
        scale_pos_weight=scale_pos_weight,
    )


def fit_xgb_pipeline(
    pipeline: Pipeline,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame | None,
    y_val: pd.Series | None,
    cfg: TrainConfig,
) -> Pipeline:
    """Fit the pipeline; optionally use a validation set for early stopping."""
    xcfg = cfg.xgb
    pre = pipeline.named_steps["preprocess"]
    clf = pipeline.named_steps["clf"]

    if xcfg.early_stopping_rounds is None:
        pipeline.fit(X_train, y_train)
        return pipeline

    if X_val is None or y_val is None:
        raise ValueError("Validation frame required when early_stopping_rounds is set.")

    X_tr = pre.fit_transform(X_train, y_train)
    X_va = pre.transform(X_val)
    clf.fit(
        X_tr,
        y_train,
        eval_set=[(X_va, y_val)],
        early_stopping_rounds=xcfg.early_stopping_rounds,
        verbose=False,
    )
    return pipeline


def train(cfg: TrainConfig) -> Pipeline:
    """Load data, fit the XGBoost sklearn Pipeline, log to MLflow, optionally persist."""
    df = load_feature_frame(cfg)
    if cfg.target_col not in df.columns or cfg.id_col not in df.columns:
        raise KeyError(
            f"Expected columns {cfg.target_col!r} and {cfg.id_col!r} in feature frame."
        )

    X = df.drop(columns=[cfg.target_col, cfg.id_col])
    y = df[cfg.target_col]

    num_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = [c for c in X.columns if c not in num_cols]

    X_temp, X_test, y_temp, y_test = train_test_split(
        X,
        y,
        test_size=cfg.data.test_size,
        random_state=cfg.random_state,
        stratify=y,
    )

    X_val: pd.DataFrame | None = None
    y_val: pd.Series | None = None
    if cfg.xgb.early_stopping_rounds is not None:
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp,
            y_temp,
            test_size=cfg.data.validation_size,
            random_state=cfg.random_state,
            stratify=y_temp,
        )
    else:
        X_train, y_train = X_temp, y_temp

    tree_preprocess = build_tree_preprocessor(cfg, num_cols, cat_cols)
    scale_pos_weight = float((y_train == 0).sum() / max((y_train == 1).sum(), 1))
    clf = make_xgb_classifier(cfg, scale_pos_weight=scale_pos_weight)
    pipeline = Pipeline(steps=[("preprocess", tree_preprocess), ("clf", clf)])

    logger.info(
        "Training: n_train=%s n_val=%s n_test=%s n_features=%s",
        len(X_train),
        len(X_val) if X_val is not None else 0,
        len(X_test),
        X.shape[1],
    )

    fit_xgb_pipeline(pipeline, X_train, y_train, X_val, y_val, cfg)

    y_score = pipeline.predict_proba(X_test)[:, 1]
    y_pred = pipeline.predict(X_test)
    test_metrics = binary_classifier_metrics(y_test, y_score, y_pred=y_pred)

    mlflow_params = dataclass_to_mlflow_params(cfg)
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
    sha = _git_sha_short()
    if sha:
        mlflow_params["git_sha_short"] = sha

    n_sig = min(cfg.mlflow.signature_sample_rows, len(X_test))
    signature_sample = X_test.iloc[:n_sig]

    log_pipeline_run(
        cfg.mlflow.run_name,
        pipeline,
        metrics=test_metrics,
        params=mlflow_params,
        signature_sample=signature_sample,
        experiment_name=cfg.mlflow.experiment_name,
    )

    logger.info("Test metrics:\n%s", format_metrics_lines(test_metrics))

    if cfg.model_output_path is not None:
        out = Path(cfg.model_output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(pipeline, out)
        logger.info("Saved pipeline to %s", out.resolve())

    return pipeline


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train XGBoost credit-default pipeline.")
    p.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional JSON file with nested overrides for TrainConfig.",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    cfg = train_config_from_json(args.config) if args.config else default_train_config()
    train(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
