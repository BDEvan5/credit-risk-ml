# EDA SQL index

Queries in this folder aggregate Home Credit **`application_train`** (and joins to **`bureau`**, installments, etc.) to study how factors relate to **`TARGET`**. Use them from DuckDB against `data/home_credit.db` after running `sql/load.sql`.

| SQL file | What it fetches / processes |
|----------|------------------------------|
| `target_distribution.sql` | Counts and % of `TARGET` in `application_train` (class balance / baseline rate). |
| `occupational_risk.sql` | Default rate and counts by `OCCUPATION_TYPE` (missing → Unknown). |
| `risk_concentration_by_occupation.sql` | Cumulative % of applicants vs cumulative % of defaults when occupations are ordered by default rate (worst first). |
| `annuity_to_income_risk.sql` | Default rate by decile of annuity ÷ income (payment burden). |
| `income_credit_default_heatmap.sql` | Default rate for each pair of income decile × credit amount decile. |
| `bureau_depth_risk.sql` | Default rate by decile of bureau row count per applicant. |
| `bureau_zero_vs_rest.sql` | Default rate for “no bureau rows” vs “has bureau history”. |
| `external_scores_by_target.sql` | Mean `EXT_SOURCE_1/2/3` by `TARGET`. |
| `age_risk_bands.sql` | Default rate by age band (years from `DAYS_BIRTH`). |
| `age_risk.sql` | Default rate by age quartile. |
| `amt_credit_risk.sql` | Default rate by decile of `AMT_CREDIT`. |
| `amt_income_risk.sql` | Default rate by decile of `AMT_INCOME_TOTAL`. |
| `credit_to_income_risk.sql` | Default rate by decile of credit ÷ income. |
| `goods_price_to_credit_risk.sql` | Default rate by decile of goods price ÷ credit. |
| `prev_rejection_share_risk.sql` | Default rate by decile of prior rejection-reason share. |
| `installments_target_summary.sql` | Share of installment payment rows paid late vs on time, aggregated by `TARGET`. |
| `credit_card_util_risk.sql` | Default rate by decile of credit-card balance ÷ limit. |
