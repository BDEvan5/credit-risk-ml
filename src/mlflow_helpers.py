"""MLflow logging helpers for sklearn pipelines (params, metrics, model artifact)."""

from __future__ import annotations

from typing import Any

import mlflow
import mlflow.sklearn
from mlflow.models import infer_signature


DEFAULT_EXPERIMENT = "credit-risk-modelling"


def set_experiment(name: str = DEFAULT_EXPERIMENT) -> str:
    """Point MLflow at the project experiment; returns the experiment id."""
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
            mlflow.sklearn.log_model(
                model, name="pipeline", signature=sig
            )
        except Exception:
            mlflow.sklearn.log_model(model, name="pipeline")
