"""FastAPI service for scoring credit-default risk with the calibrated XGBoost pipeline.

Run locally from the repo root::

    uv run uvicorn src.api:app --reload --port 8080

Then POST an applicant payload to ``/predict`` (see ``example_request.txt``). Any field from
the training schema may be supplied; omitted fields are treated as missing and imputed by
the pipeline, so a minimal request with just the highest-signal features (e.g. ``EXT_SOURCE_*``,
``AMT_CREDIT``, ``DAYS_EMPLOYED``) is valid.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = Path(os.environ.get("MODEL_PATH", _REPO_ROOT / "model" / "model_calibrated.pkl"))
MODEL_VERSION = os.environ.get("MODEL_VERSION", "v1.0-calibrated")
API_KEY = os.environ.get("API_KEY")  # if set, requests must send matching X-API-Key

# Risk-tier thresholds on calibrated probability. Baseline default rate is ~8%, so we band
# around that: below baseline = Low, 2x baseline = High.
RISK_TIER_LOW_MAX = 0.10
RISK_TIER_MEDIUM_MAX = 0.30

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:4173,http://localhost:8080",
    ).split(",")
    if o.strip()
]


def _extract_expected_columns(model: Any) -> tuple[list[str], set[str]]:
    """Return the full ordered feature list plus the categorical-column set.

    Walks ``CalibratedClassifierCV -> FrozenEstimator -> Pipeline -> ColumnTransformer`` to
    recover the columns the preprocessor was fit on. Categorical columns must be object
    dtype at inference time so the one-hot encoder sees strings, not NaN floats.
    """
    pipeline = model
    for attr in ("estimator", "base_estimator"):
        if hasattr(pipeline, attr):
            pipeline = getattr(pipeline, attr)
    while hasattr(pipeline, "estimator") and not hasattr(pipeline, "named_steps"):
        pipeline = pipeline.estimator
    if not hasattr(pipeline, "named_steps"):
        raise RuntimeError("Could not locate fitted sklearn Pipeline inside loaded model")

    preprocess = pipeline.named_steps["preprocess"]
    ordered: list[str] = []
    categorical: set[str] = set()
    for name, _tr, cols in preprocess.transformers_:
        cols = list(cols)
        ordered.extend(cols)
        if name == "cat":
            categorical.update(cols)
    return ordered, categorical


def _force_single_threaded(model: Any) -> None:
    """Set ``n_jobs=1`` anywhere it exists in the loaded model.

    The ``ColumnTransformer`` was fit with ``n_jobs=-1`` for training throughput, but at
    inference on a single row parallel dispatch is pure overhead and — worse — causes
    intermittent ~1.3 s spikes when joblib spawns/attaches to a worker pool. Forcing
    single-threaded execution is both faster and more predictable for per-request latency.
    """
    pipeline = model
    for attr in ("estimator", "base_estimator"):
        if hasattr(pipeline, attr):
            pipeline = getattr(pipeline, attr)
    while hasattr(pipeline, "estimator") and not hasattr(pipeline, "named_steps"):
        pipeline = pipeline.estimator
    if not hasattr(pipeline, "named_steps"):
        return
    for step in pipeline.named_steps.values():
        if hasattr(step, "n_jobs"):
            step.n_jobs = 1


class ModelArtifacts:
    """Container for the loaded model and its column schema (populated at startup)."""

    model: Any = None
    expected_columns: list[str] = []
    categorical_columns: set[str] = set()


artifacts = ModelArtifacts()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Load the model and fully warm the predict path before accepting traffic.

    Loading the pickle is only part of the cold-start cost — the first real call
    into ``predict_proba`` also triggers lazy imports inside sklearn/xgboost (~1 s
    on first invocation). Firing a throwaway prediction here means the ``/health``
    warm-up ping from the frontend leaves the container fully hot: subsequent
    ``/predict`` calls then return in ~20 ms instead of ~1.3 s.
    """
    if not MODEL_PATH.exists():
        raise RuntimeError(f"Model file not found at {MODEL_PATH}. Run `uv run python -m src.train` first.")
    logger.info("Loading model from %s", MODEL_PATH)
    artifacts.model = joblib.load(MODEL_PATH)
    _force_single_threaded(artifacts.model)
    artifacts.expected_columns, artifacts.categorical_columns = _extract_expected_columns(
        artifacts.model
    )
    logger.info(
        "Model loaded: %d expected columns (%d categorical)",
        len(artifacts.expected_columns),
        len(artifacts.categorical_columns),
    )
    warmup_row, _ = _build_feature_frame({})
    _ = artifacts.model.predict_proba(warmup_row)
    logger.info("Predict path warmed")
    yield


app = FastAPI(
    title="Credit Risk API",
    description="Probability of default for Home Credit applications (calibrated XGBoost).",
    version=MODEL_VERSION,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    allow_credentials=False,
)


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """No-op if ``API_KEY`` is unset (local dev); otherwise require matching header."""
    if API_KEY is None:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


class ApplicantFeatures(BaseModel):
    """Curated subset of the 224 training columns, documented for the demo UI.

    Any additional training-schema column may also be supplied (``extra='allow'``) — for
    example, ``bureau_total_debt`` or ``inst_pct_late_last365``. Unknown keys are dropped.
    Missing columns are imputed by the pipeline, so a minimal request is valid.
    """

    model_config = ConfigDict(extra="allow")

    NAME_CONTRACT_TYPE: str | None = Field(default=None, description='"Cash loans" or "Revolving loans"')
    CODE_GENDER: str | None = Field(default=None, description='"M", "F", or "XNA"')
    FLAG_OWN_CAR: str | None = Field(default=None, description='"Y" or "N"')
    FLAG_OWN_REALTY: str | None = Field(default=None, description='"Y" or "N"')
    CNT_CHILDREN: int | None = None
    AMT_INCOME_TOTAL: float | None = Field(default=None, description="Annual income")
    AMT_CREDIT: float | None = Field(default=None, description="Requested credit amount")
    AMT_ANNUITY: float | None = None
    AMT_GOODS_PRICE: float | None = None
    NAME_INCOME_TYPE: str | None = Field(
        default=None, description='e.g. "Working", "Pensioner", "Commercial associate"'
    )
    NAME_EDUCATION_TYPE: str | None = Field(
        default=None, description='e.g. "Higher education", "Secondary / secondary special"'
    )
    NAME_FAMILY_STATUS: str | None = None
    NAME_HOUSING_TYPE: str | None = None
    DAYS_BIRTH: int | None = Field(
        default=None, description="Age in days relative to application (negative; e.g. -12000 ~ 33 yrs)"
    )
    DAYS_EMPLOYED: int | None = Field(
        default=None, description="Days employed before application (negative); 365243 = unemployed sentinel"
    )
    OCCUPATION_TYPE: str | None = None
    CNT_FAM_MEMBERS: float | None = None
    REGION_RATING_CLIENT: int | None = Field(default=None, description="1 (best) to 3 (worst)")
    EXT_SOURCE_1: float | None = Field(default=None, description="External credit score 1, in [0, 1]")
    EXT_SOURCE_2: float | None = Field(default=None, description="External credit score 2, in [0, 1]")
    EXT_SOURCE_3: float | None = Field(default=None, description="External credit score 3, in [0, 1]")


class PredictionResponse(BaseModel):
    probability: float = Field(description="Calibrated probability of default in [0, 1]")
    risk_tier: str = Field(description="Low / Medium / High band for UI display")
    model_version: str
    n_features_provided: int = Field(
        description="How many of the 224 training columns the request actually set"
    )
    elapsed_ms: float = Field(
        description="Server-side wall-clock time from request-received to response-built (ms). "
        "Excludes network round-trip; useful for separating cold-start from steady-state latency."
    )


def _risk_tier(p: float) -> str:
    if p < RISK_TIER_LOW_MAX:
        return "Low"
    if p < RISK_TIER_MEDIUM_MAX:
        return "Medium"
    return "High"


def _build_feature_frame(payload: dict[str, Any]) -> tuple[pd.DataFrame, int]:
    """Construct a one-row DataFrame aligned to the model's expected schema.

    Fills missing columns with ``NaN`` and coerces categorical columns to object dtype so
    the one-hot encoder treats them as strings rather than numeric NaN.
    """
    expected = artifacts.expected_columns
    cat_cols = artifacts.categorical_columns
    provided = {k: v for k, v in payload.items() if k in set(expected) and v is not None}
    row: dict[str, Any] = {col: provided.get(col, np.nan) for col in expected}
    df = pd.DataFrame([row], columns=expected)
    for c in cat_cols:
        df[c] = df[c].astype("object")
        df.loc[df[c].isna(), c] = np.nan
    return df, len(provided)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe; also used as the frontend warm-up ping."""
    return {"status": "ok", "model_version": MODEL_VERSION}


# async so the handler runs on the event loop (same thread the lifespan warmup used),
# not in a starlette threadpool worker. Otherwise each previously-unused threadpool
# worker pays ~1.3 s of sklearn/joblib lazy init on its first call, making the first
# few predictions slow even after /health wakes the container. Blocking the loop for
# ~20 ms per request is fine for this demo's traffic (~100 calls/month).
@app.post("/predict", response_model=PredictionResponse, dependencies=[Depends(verify_api_key)])
async def predict(payload: ApplicantFeatures) -> PredictionResponse:
    if artifacts.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    start = time.perf_counter()
    features, n_provided = _build_feature_frame(payload.model_dump())
    proba = float(artifacts.model.predict_proba(features)[0, 1])
    elapsed_ms = (time.perf_counter() - start) * 1000
    return PredictionResponse(
        probability=proba,
        risk_tier=_risk_tier(proba),
        model_version=MODEL_VERSION,
        n_features_provided=n_provided,
        elapsed_ms=round(elapsed_ms, 2),
    )
