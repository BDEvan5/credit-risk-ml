# Container image for the credit-risk FastAPI service.
# Designed for Google Cloud Run: listens on $PORT (Cloud Run injects 8080 by default)
# and runs as a non-root user. Model file is baked in so the container is fully
# self-contained — no runtime downloads, no external storage dependencies.
#
# Dependency management: uses uv with `--no-dev` to install ONLY the runtime deps
# from [project.dependencies] (fastapi, sklearn, xgboost, pandas, joblib, pydantic,
# uvicorn). Training deps (mlflow/lightgbm/shap/lifelines/matplotlib/ipykernel/
# kaggle/duckdb/pyarrow) live in [dependency-groups.dev] and are excluded here,
# keeping the image ~500 MB instead of ~2 GB.

# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

# Pull just the uv binary from the official image — avoids a curl+install step
# and pins uv by the image tag (use a dated tag for fully reproducible builds).
COPY --from=ghcr.io/astral-sh/uv:0.9.10 /uv /uvx /usr/local/bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # copy instead of hardlink so the venv is self-contained
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    # put the venv at a predictable path so we can add it to PATH below
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install deps first so the layer caches when only application code or the model changes.
# --frozen: fail if uv.lock is out of sync with pyproject.toml (guarantees reproducibility).
# --no-dev: skip [dependency-groups.dev] (the training stack).
# --no-install-project: we don't need the project itself installed; uvicorn finds src/ via CWD.
# NB: no BuildKit `--mount=type=cache` — Cloud Build's default docker builder doesn't
# enable BuildKit, so cache mounts fail the build there. uv resolves fast enough without.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Application code and the pickled calibrated model.
COPY src/api.py ./src/api.py
COPY model/model_calibrated.pkl ./model/model_calibrated.pkl

# Cloud Run requires the container to run as a non-root user in gVisor / 2nd-gen
# execution; generally sound practice regardless.
RUN useradd --create-home --uid 1001 appuser && chown -R appuser:appuser /app
USER appuser

ENV PORT=8080
EXPOSE 8080

# Local smoke check — Cloud Run ignores this and uses its own HTTP probes.
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8080\")}/health').read()" \
  || exit 1

# --host 0.0.0.0 so the container accepts traffic from outside itself.
# Shell form so ${PORT} is expanded at runtime (Cloud Run sets this).
CMD ["sh", "-c", "uvicorn src.api:app --host 0.0.0.0 --port ${PORT}"]
