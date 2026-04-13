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

---
name: karpathy-guidelines
description: Behavioral guidelines to reduce common LLM coding mistakes. Use when writing, reviewing, or refactoring code to avoid overcomplication, make surgical changes, surface assumptions, and define verifiable success criteria.
license: MIT
---

# Karpathy Guidelines

Behavioral guidelines to reduce common LLM coding mistakes, derived from [Andrej Karpathy's observations](https://x.com/karpathy/status/2015883857489522876) on LLM coding pitfalls.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.