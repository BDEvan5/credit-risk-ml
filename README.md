# Credit risk ML 💳

## Intro

The aim of this project is to **model the probability of loan default** using application and bureau data, then **compare alternative feature sets and modeling choices** (e.g. baselines vs richer pipelines, validation discipline) so decisions are evidence-based. Longer term, the intent is to **move from experiments toward a production-grade pipeline**: reproducible data loading, feature builds, training/evaluation, and deployment hooks.

**Getting started with the data:** Download the [Home Credit Default Risk](https://www.kaggle.com/competitions/home-credit-default-risk/data) competition files from Kaggle and place the CSVs under **`data/`**. Run **`sql/load.sql`** against DuckDB to create tables (e.g. `application_train`, `bureau`, …) and materialize **`data/home_credit.db`**. After that you can run SQL under `sql/eda/` or open the EDA notebook, which reads the same database.

## EDA 📊

Exploratory analysis asks how strong applicants’ characteristics are related to **`TARGET`** (default vs not). See the notebook **[`notebooks/01_eda.ipynb`](notebooks/01_eda.ipynb)** for plots and tables (DuckDB → `data/home_credit.db`, queries from `sql/eda/`).

- **Occupation and concentration** — Occupation is a strong predictor of default rate and a simple feature to use with 12 unique values.
- **Payment burden (annuity / income)** — Higher payment burdens lead to higher default rates. Individuals in the lower median of payment burden are less likely to default. The single exception is the 10th decile, where a significant drop is seen from the 9th decile.
- **Income × credit (leverage)** — The safest applicants tend to be on the edges of the credit amount distributions, with the highest risk applicants in the middle. Additionally, the lower the income, the larger the risk-band and the higher the default rate.
- **Bureau depth, thin files, external scores** — More information about applications leads to significantly better predictions. Applicants with no bureau history, or very few lines on record, are more likely to default. Additionally, the available external signals provide signal on default rate.
- **Age bands** — Older applicants are monotonically safer and less likely to default. The high-risk segment is concentrated among younger applicants.

Index of EDA query files and what each returns: **[`sql/eda/README.md`](sql/eda/README.md)**.

## Modelling

Notebook **[`notebooks/02_modelling.ipynb`](notebooks/02_modelling.ipynb)** compares logistic regression, XGBoost, and LightGBM on one feature set (MLflow experiment `credit-risk-modelling`). Scripted training and the same metrics live in **`src/train.py`** (`uv run python -m src.train`).

<!-- MLFLOW_README_SYNC_BEGIN -->

_Auto-generated from MLflow — refresh: `uv run python scripts/sync_readme_from_mlflow.py`_

**MLflow run** `8272b5c1491c471f8a9c7255a9c42b79` — **xgb_2000_depth4_sub075_lambda2**

| Metric | Test |
| --- | --- |
| ROC-AUC | 0.7921 |
| Gini (2×AUC − 1) | 0.5843 |
| Average precision (PR-AUC) | 0.2929 |
| KS statistic | 0.4477 |
| Accuracy | 0.7459 |

![ROC and precision–recall (test holdout, same split as training)](docs/figures/mlflow_eval_curves.png)

<!-- MLFLOW_README_SYNC_END -->

## Future work 🔮

- Calibrate model with a reliability diagram. Additionally, add some explainability to understand the model's decisions.
- Deploy the model to a web service to enable real-time scoring.


## Commands to run the project

Run **`mlflow`** locally to view experiments: `uv run mlflow ui --backend-store-uri sqlite:///mlflow.db`

### Training and README metrics

From the **repository root**, with **`data/home_credit.db`** in place, train the XGBoost pipeline and log a run to **`mlflow.db`** (the script prints the MLflow run id when finished):

```bash
uv run python -m src.train
```
This script internally calls the `build_feature_matrix` function to build the feature matrix and then trains the model.

To **refresh the Modelling section** in this README (metrics table, ROC/PR figure) from MLflow, run the sync script. It uses the run id configured in the script unless you override it with `--run-id`:

```bash
uv run python scripts/sync_readme_from_mlflow.py --run-id 8272b5c1491c471f8a9c7255a9c42b79
```

The script will update the README with the latest metrics and figure.