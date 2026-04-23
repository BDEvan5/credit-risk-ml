"""Train an XGBoost credit-default model (sklearn Pipeline), isotonic-calibrate, and log to MLflow.

Run from the repository root::

    uv run python -m src.train

Writes ``model/model_uncalibrated.pkl`` (preprocess + booster) and ``model/model_calibrated.pkl``
(``CalibratedClassifierCV`` wrapping the frozen pipeline). Edit :class:`TrainConfig` for
hyperparameters and paths. For JSON overrides, use :func:`load_config`.
"""

import json
import logging
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


import duckdb
import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.frozen import FrozenEstimator
from sklearn.impute import SimpleImputer
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier

from src.features import build_feature_matrix
from src.metrics import binary_classifier_metrics, format_metrics_lines
from src.mlflow_helpers import DEFAULT_EXPERIMENT, log_credit_train_run

logger = logging.getLogger(__name__)

# Running `python src/train.py` puts `src/` on sys.path, not the repo root, so
# `import src.*` fails unless the project root is added (``python -m src.train`` does this).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _sklearn_safe_features(X: pd.DataFrame) -> pd.DataFrame:
    """Normalize DuckDB/pandas nulls and dtypes for sklearn ``SimpleImputer``.

    DuckDB ``.df()`` can return ``pd.NA`` (and nullable extension dtypes). Object-column
    imputation uses equality checks that raise on ``pd.NA``; nullable integers may also be
    excluded from ``select_dtypes(include=[np.number])`` depending on pandas version.
    """
    out = X.replace(pd.NA, np.nan)
    for col in out.columns:
        s = out[col]
        if pd.api.types.is_extension_array_dtype(
            s.dtype
        ) and pd.api.types.is_numeric_dtype(s.dtype):
            out[col] = s.astype("float64")
    return out


@dataclass
class TrainConfig:
    """All training, data, model, and MLflow settings in one place."""

    random_state: int = 42
    target_col: str = "TARGET"
    id_col: str = "SK_ID_CURR"

    duckdb_path: Path = field(
        default_factory=lambda: _REPO_ROOT / "data" / "home_credit.db"
    )
    use_cached_features: bool = False
    rebuild_features: bool = False
    sample_frac: float | None = None
    test_size: float = 0.2
    validation_size: float = 0.15
    #: Stratified fraction of the non-test pool reserved for isotonic calibration only
    #: (not used to fit the booster).
    calibration_holdout_frac: float = 0.15

    numeric_imputer_strategy: str = "median"
    categorical_imputer_strategy: str = "most_frequent"
    onehot_max_categories: int = 50
    onehot_min_frequency: float = 0.001
    column_transformer_n_jobs: int = -1

    n_estimators: int = 2000
    max_depth: int = 4
    learning_rate: float = 0.02
    subsample: float = 0.75
    colsample_bytree: float = 0.75
    reg_lambda: float = 2.0
    reg_alpha: float = 0.05
    gamma: float = 0.0
    min_child_weight: float = 1.0
    max_delta_step: float = 0.0
    n_jobs: int = -1
    tree_method: str = "hist"
    eval_metric: str = "logloss"
    early_stopping_rounds: int | None = None

    experiment_name: str = DEFAULT_EXPERIMENT
    run_name: str = "xgb_2000_depth4_sub075_lambda2"
    signature_sample_rows: int = 500

    model_uncalibrated_path: Path | None = field(
        default_factory=lambda: _REPO_ROOT / "model" / "model_uncalibrated.pkl"
    )
    model_calibrated_path: Path | None = field(
        default_factory=lambda: _REPO_ROOT / "model" / "model_calibrated.pkl"
    )


def load_config(path: Path | None) -> TrainConfig:
    """Defaults, optionally merged with a flat JSON object."""
    cfg = TrainConfig()
    if path is None:
        return cfg
    overrides = json.loads(path.read_text())
    d = asdict(cfg)
    d.update(overrides)
    for key in ("duckdb_path", "model_uncalibrated_path", "model_calibrated_path"):
        val = d.get(key)
        if val is not None and not isinstance(val, Path):
            d[key] = Path(val)
    return TrainConfig(**d)


def _load_feature_xy(cfg: TrainConfig) -> tuple[pd.DataFrame, pd.Series]:
    """Load DuckDB features into ``X``, ``y`` (same preprocessing as :func:`train`)."""
    db = cfg.duckdb_path
    if not db.exists():
        raise FileNotFoundError(
            f"DuckDB database not found at {db}. Load data per project README."
        )
    conn = duckdb.connect(str(db))
    try:
        df = build_feature_matrix(
            conn,
            force_rebuild=cfg.rebuild_features or not cfg.use_cached_features,
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

    X = _sklearn_safe_features(df.drop(columns=[cfg.target_col, cfg.id_col]))
    y = df[cfg.target_col]
    return X, y


def load_test_holdout(cfg: TrainConfig) -> tuple[pd.DataFrame, pd.Series]:
    """Same stratified test split as :func:`train` (for eval / reporting tools)."""
    X, y = _load_feature_xy(cfg)
    _, X_test, _, y_test = train_test_split(
        X,
        y,
        test_size=cfg.test_size,
        random_state=cfg.random_state,
        stratify=y,
    )
    return X_test, y_test


def train(cfg: TrainConfig) -> tuple[Pipeline, CalibratedClassifierCV]:
    X, y = _load_feature_xy(cfg)
    num_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = [c for c in X.columns if c not in num_cols]

    X_temp, X_test, y_temp, y_test = train_test_split(
        X,
        y,
        test_size=cfg.test_size,
        random_state=cfg.random_state,
        stratify=y,
    )

    X_tree, X_cal, y_tree, y_cal = train_test_split(
        X_temp,
        y_temp,
        test_size=cfg.calibration_holdout_frac,
        random_state=cfg.random_state,
        stratify=y_temp,
    )

    X_val, y_val = None, None
    if cfg.early_stopping_rounds is not None:
        X_train, X_val, y_train, y_val = train_test_split(
            X_tree,
            y_tree,
            test_size=cfg.validation_size,
            random_state=cfg.random_state,
            stratify=y_tree,
        )
    else:
        X_train, y_train = X_tree, y_tree

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
        "Training: n_train=%s n_cal=%s n_val=%s n_test=%s n_features=%s",
        len(X_train),
        len(X_cal),
        len(X_val) if X_val is not None else 0,
        len(X_test),
        X.shape[1],
    )

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

    cal_model = CalibratedClassifierCV(
        estimator=FrozenEstimator(pipeline),
        method="isotonic",
        cv=3,
    )
    cal_model.fit(X_cal, y_cal)

    y_score = pipeline.predict_proba(X_test)[:, 1]
    y_pred = pipeline.predict(X_test)
    test_metrics = binary_classifier_metrics(y_test, y_score, y_pred=y_pred)

    p_cal = cal_model.predict_proba(X_test)[:, 1]
    test_metrics_cal = binary_classifier_metrics(y_test, p_cal)
    test_metrics["test_brier_raw"] = brier_score_loss(y_test, y_score)
    test_metrics["test_brier_calibrated"] = brier_score_loss(y_test, p_cal)

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
            "n_cal": len(X_cal),
            "n_val": len(X_val) if X_val is not None else 0,
            "n_test": len(X_test),
            "n_features": int(X.shape[1]),
            "n_numeric_cols": len(num_cols),
            "n_categorical_cols": len(cat_cols),
            "calibration_holdout_frac": cfg.calibration_holdout_frac,
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
    sig_rows = X_test.iloc[:n_sig]
    metrics_for_mlflow = {
        **test_metrics,
        **{f"cal_{k}": v for k, v in test_metrics_cal.items()},
    }
    mlflow_run_id, mlflow_run_name = log_credit_train_run(
        cfg.run_name,
        pipeline_uncalibrated=pipeline,
        model_calibrated=cal_model,
        metrics=metrics_for_mlflow,
        params=mlflow_params,
        signature_sample=sig_rows,
        y_test=y_test,
        p_test_raw=y_score,
        p_test_calibrated=p_cal,
        experiment_name=cfg.experiment_name,
    )
    print(
        f"MLflow run name={mlflow_run_name!r} run_id={mlflow_run_id}",
        flush=True,
    )

    logger.info("Test metrics (uncalibrated):\n%s", format_metrics_lines(test_metrics))
    logger.info(
        "Test metrics (calibrated proba):\n%s",
        format_metrics_lines(test_metrics_cal),
    )

    if cfg.model_uncalibrated_path is not None:
        out_u = Path(cfg.model_uncalibrated_path)
        out_u.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(pipeline, out_u)
        logger.info("Saved uncalibrated pipeline to %s", out_u.resolve())
    if cfg.model_calibrated_path is not None:
        out_c = Path(cfg.model_calibrated_path)
        out_c.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(cal_model, out_c)
        logger.info("Saved calibrated model to %s", out_c.resolve())

    return pipeline, cal_model


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    train(TrainConfig())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
