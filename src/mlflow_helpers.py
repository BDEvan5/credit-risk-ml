"""MLflow logging helpers for sklearn pipelines (params, metrics, model artifact).

Tracking uses SQLite at the repo root (``mlflow.db``), not the deprecated file-store backend.
To move existing runs from ``./mlruns`` into SQLite, see
https://mlflow.org/docs/latest/self-hosting/migrate-from-file-store (``mlflow migrate-filestore``).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import mlflow
import mlflow.sklearn
import numpy as np
from mlflow.models import infer_signature
from sklearn.calibration import calibration_curve


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
) -> tuple[str, str]:
    """
    One MLflow run: experiment, tags, params, metrics, and the fitted Pipeline as ``pipeline/``.

    ``signature_sample`` should be a small slice of the feature matrix (e.g. ``X_test.iloc[:500]``)
    so MLflow can record inputs/outputs for the model registry.

    Returns ``(run_id, run_name)`` as assigned by the tracking store (``run_name`` may differ from
    the requested name if MLflow disambiguates).
    """
    set_experiment(experiment_name)
    with mlflow.start_run(run_name=run_name) as active:
        run_id = active.info.run_id
        resolved_name = active.info.run_name
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
    return run_id, resolved_name


def _plot_reliability_raw_vs_calibrated(
    y_true: np.ndarray,
    p_raw: np.ndarray,
    p_cal: np.ndarray,
    *,
    n_bins: int = 10,
    path: Path,
) -> None:
    """Save a reliability diagram with uncalibrated and calibrated curves."""
    y_true = np.asarray(y_true).astype(int)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 5))
    for probs, label, color in (
        (p_raw, "Uncalibrated", "C0"),
        (p_cal, "Isotonic calibrated", "C1"),
    ):
        prob_true, prob_pred = calibration_curve(
            y_true, probs, n_bins=n_bins, strategy="uniform"
        )
        ax.plot(prob_pred, prob_true, marker="o", label=label, color=color)
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Perfect")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Fraction of positives (actual)")
    ax.set_title("Reliability — test holdout")
    ax.legend(loc="best")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def log_credit_train_run(
    run_name: str,
    *,
    pipeline_uncalibrated,
    model_calibrated,
    metrics: dict[str, float],
    params: dict[str, Any],
    signature_sample,
    y_test,
    p_test_raw: np.ndarray,
    p_test_calibrated: np.ndarray,
    experiment_name: str = DEFAULT_EXPERIMENT,
) -> tuple[str, str]:
    """
    One MLflow run: params, metrics, reliability plot, and two sklearn artefacts
    ``model_uncalibrated`` and ``model_calibrated``.
    """
    set_experiment(experiment_name)
    with mlflow.start_run(run_name=run_name) as active:
        run_id = active.info.run_id
        resolved_name = active.info.run_name
        mlflow.set_tag("model_name", run_name)
        mlflow.set_tag("calibration", "isotonic")
        for key, val in params.items():
            _safe_log_param(key, val)
        for key, val in metrics.items():
            if isinstance(val, float) and val != val:
                continue
            mlflow.log_metric(key, float(val))

        with tempfile.TemporaryDirectory() as td:
            plot_path = Path(td) / "reliability_raw_vs_calibrated.png"
            _plot_reliability_raw_vs_calibrated(
                y_test.values,
                p_test_raw,
                p_test_calibrated,
                path=plot_path,
            )
            mlflow.log_artifact(str(plot_path), artifact_path="plots")

        def _log_sklearn(name: str, model) -> None:
            try:
                sig = infer_signature(
                    signature_sample,
                    model.predict_proba(signature_sample),
                )
                mlflow.sklearn.log_model(model, name=name, signature=sig)
            except Exception:
                mlflow.sklearn.log_model(model, name=name)

        _log_sklearn("model_uncalibrated", pipeline_uncalibrated)
        _log_sklearn("model_calibrated", model_calibrated)

    return run_id, resolved_name
