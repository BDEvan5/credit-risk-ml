"""MLflow logging helpers for sklearn pipelines (params, metrics, model artifact).

Tracking uses SQLite at the repo root (``mlflow.db``), not the deprecated file-store backend.
To move existing runs from ``./mlruns`` into SQLite, see
https://mlflow.org/docs/latest/self-hosting/migrate-from-file-store (``mlflow migrate-filestore``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import mlflow
import mlflow.sklearn
from mlflow.models import infer_signature


DEFAULT_EXPERIMENT = "credit-risk-modelling"


def _repo_root() -> Path:
    cwd = Path.cwd().resolve()
    return cwd.parent if cwd.name == "notebooks" else cwd


def _project_tracking_uri() -> str:
    """SQLite tracking URI at the repo root (``mlflow.db``), not CWD when the kernel cwd is ``notebooks/``."""
    db = _repo_root() / "mlflow.db"
    return f"sqlite:///{db.resolve().as_posix()}"


def set_experiment(name: str = DEFAULT_EXPERIMENT) -> str:
    """Point MLflow at the project experiment; returns the experiment id."""
    mlflow.set_tracking_uri(_project_tracking_uri())
    return mlflow.set_experiment(name).experiment_id


def _safe_log_param(key: str, val: Any) -> None:
    if val is None:
        mlflow.log_param(key, "None")
    elif isinstance(val, (bool, int, float, str)):
        mlflow.log_param(key, val)
    else:
        mlflow.log_param(key, str(val))


def log_pipeline_run(
    run_name: str,
    model,
    *,
    metrics: dict[str, float],
    params: dict[str, Any],
    signature_sample,
    experiment_name: str = DEFAULT_EXPERIMENT,
) -> None:
    """
    One MLflow run: experiment, tags, params, metrics, and the fitted Pipeline as ``pipeline/``.

    ``signature_sample`` should be a small slice of the feature matrix (e.g. ``X_test.iloc[:500]``)
    so MLflow can record inputs/outputs for the model registry.
    """
    set_experiment(experiment_name)
    with mlflow.start_run(run_name=run_name):
        mlflow.set_tag("model_name", run_name)
        for key, val in params.items():
            _safe_log_param(key, val)
        for key, val in metrics.items():
            if isinstance(val, float) and val != val:
                continue
            mlflow.log_metric(key, float(val))
        try:
            sig = infer_signature(
                signature_sample,
                model.predict_proba(signature_sample),
            )
            mlflow.sklearn.log_model(model, name="pipeline", signature=sig)
        except Exception:
            mlflow.sklearn.log_model(model, name="pipeline")
