# Agent guide — credit-risk-ml

This file orients automated assistants and contributors to what this repository is for, how it is organized, and how to write code here.

## Project aim

This repo is a **credit default risk** learning and portfolio project built on the [Kaggle Home Credit Default Risk](https://www.kaggle.com/competitions/home-credit-default-risk/data) dataset (~307k loan applications across seven related tables).

**Goals:**

- Practice **multi-table SQL** (window functions, CTEs, joins) and turn bureau / instalment / previous-application history into applicant-level features.
- Build **tabular ML** pipelines (baselines, XGBoost, LightGBM) with disciplined validation and **credit-relevant metrics** (ROC-AUC, Gini, KS, precision–recall).
- Use **MLflow** for experiment tracking and reproducible runs.
- Progress toward **calibration** (reliability, Brier, calibration methods), **SHAP** explainability, **survival analysis** (time-to-default, lifelines), and eventually a **served model** (FastAPI, Docker, optional cloud deploy).

Each phase is meant to produce a concrete artifact (EDA + SQL, modelling notebook + logged runs, calibration notebook, survival notebook, API + container). The overarching story: move from exploratory SQL and notebooks toward a **reproducible, explainable, deployable** credit risk modelling workflow.

## Repository structure

Layout follows a phased build. Some paths are **planned** (from the project roadmap); others **exist today** as the project grows.

| Area | Role |
|------|------|
| `data/` | Raw CSVs and DuckDB database files — **not committed**; populate locally per README. |
| `sql/load.sql` | Load raw tables into DuckDB (e.g. `application_train`, `bureau`, …). |
| `sql/eda/` | Named analytical SQL files for EDA (business questions, risk bands, joins). |
| `sql/features/` | SQL that aggregates supplementary tables to **one row per applicant** for modelling. |
| `notebooks/` | Story-driven notebooks: EDA (`01_eda.ipynb`), modelling (`02_modelling.ipynb`), and later calibration / survival. |
| `src/` | Shared Python: feature helpers, metrics, MLflow utilities, and (later) training and API code. |
| `model/` | Saved trained pipelines (e.g. `pipeline.pkl`) when you export models. |
| `mlflow.db` | MLflow **tracking** metadata (SQLite). |
| `mlruns/` | MLflow **artifact** root for logged models and files (may be gitignored — follow project `.gitignore`). |

**Planned additions** (as the roadmap advances): `notebooks/03_calibration.ipynb`, `notebooks/04_survival.ipynb`, `src/api.py`, `Dockerfile`, `docker-compose.yml`, and deployment docs in README.

Keep new SQL **focused and named** (one main question per file). Keep notebooks **narrative** (problem → data → findings → next steps). Prefer **pipelines** (preprocessing + estimator) for anything that must be serialized or deployed.

## Coding standards

- **Strings:** Prefer **f-strings** for formatting (`f"... {var} ..."`). Avoid `%` formatting and `str.format` for new code unless interoperability requires it.
- **Python version:** Project targets **Python 3.12+** (see `pyproject.toml`).
- **Dependencies:** Add runtime dependencies in **`pyproject.toml`**; keep the environment reproducible.
- **Style:** Match existing modules in `src/`: clear names, small focused functions, minimal unnecessary abstraction.
- **ML / experiments:** Log meaningful params and metrics via MLflow helpers in `src/mlflow_helpers.py` where appropriate; keep random seeds explicit when comparing models.
- **Scope:** Change only what the task needs; avoid drive-by refactors and unrelated files.

## Related docs

- **`README.md`** — how to obtain data, run load SQL, and where EDA lives.
- **`sql/eda/README.md`** — index of EDA queries (when present).

A detailed week-by-week roadmap (phases, deliverables, interview talking points) may live in **`PLAN.md`** locally; it is not required for coding but aligns long-term structure with this guide.
