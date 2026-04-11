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

I've added three default-prediction models in **[`notebooks/02_modelling.ipynb`](notebooks/02_modelling.ipynb)** — logistic regression, XGBoost, and LightGBM — on the same train/test split and feature set, with runs logged to MLflow (`credit-risk-modelling`). On the **test** set, **ROC-AUC** is:

- **Logistic regression** — 0.7565  
- **XGBoost** — 0.7682  
- **LightGBM** — 0.7691  

## Future work 🔮

- Productionise the training of xgboost model to a script and further optimise training.
- Build a **feature pipeline** (see `sql/features/`) and join engineered tables to applications. There is currently a draft feature pipeline in `src/features.py` that can be expanded to include more features. Additionally features should be pruned to remove any that are not relevant to the model.
- Calibrate model with a reliability diagram.
- Deploy the model to a web service.


## Notes

Run mlflow locally to view experiments: `uv run mlflow ui --backend-store-uri sqlite:///mlflow.db`