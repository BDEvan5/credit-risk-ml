# Credit Risk ML

Pipeline for predicting Home Credit Default Risk

> This project builds a credit risk model that estimates the risk of default on a loan application.

## Dataset

The dataset is from the [Home Credit Default Risk](https://www.kaggle.com/competitions/home-credit-default-risk/data) competition on Kaggle.
To replicate, the data can be downloaded and placed in the `data/` directory.

Data loading (CSV to DuckDB) is defined in `sql/load.sql`. Run that before EDA or feature builds.

## SQL layout

| Location | Purpose |
|----------|---------|
| `sql/load.sql` | Create tables from CSVs under `data/` |
| `sql/eda/` | Exploratory queries: default rate by factor (deciles, buckets, class means) |
| `sql/features/` | Queries that materialize **per-id feature tables** (aggregates for joining to applications) |

## Exploratory data analysis

EDA lives in `notebooks/eda.ipynb`. Each section runs **one** SQL file from `sql/eda/` or `sql/features/` against `data/home_credit.db`, shows a **3-row preview** of the result, then a **chart** when the query is an aggregated risk view. Feature-table scripts (under `sql/features/`) only show the preview and row counts.

### `sql/eda/`

| File | Description |
|------|-------------|
| `target_distribution.sql` | Class balance: counts and % of `TARGET` in train |
| `amt_credit_risk.sql` | Default rate by decile of `AMT_CREDIT` |
| `amt_income_risk.sql` | Default rate by decile of declared income |
| `annuity_to_income_risk.sql` | Default rate by decile of annuity / income (payment burden) |
| `credit_to_income_risk.sql` | Default rate by decile of credit / income (leverage) |
| `goods_price_to_credit_risk.sql` | Default rate by decile of goods price / credit |
| `age_risk.sql` | Default rate by age quartile (`DAYS_BIRTH`) |
| `occupational_risk.sql` | Default rate by `OCCUPATION_TYPE` |
| `external_scores_by_target.sql` | Mean `EXT_SOURCE_*` by `TARGET` |
| `bureau_depth_risk.sql` | Default rate by decile of bureau trade-line count |
| `prev_rejection_share_risk.sql` | Default rate by decile of prior rejection-reason share |
| `installments_target_summary.sql` | Late installment row share by `TARGET` |
| `credit_card_util_risk.sql` | Default rate by decile of mean CC balance / limit |

### `sql/features/`

| File | Description |
|------|-------------|
| `bureau_summary.sql` | Per-applicant aggregates from `bureau` |
| `bureau_balance_summary.sql` | Per-applicant monthly bureau status rollups |
| `previous_applications.sql` | Per-`SK_ID_CURR` aggregates from `previous_application` |

## Planned pipeline

- Feature engineering & model design
- Model calibration
- Survival analysis
- Deploy a live API endpoint
