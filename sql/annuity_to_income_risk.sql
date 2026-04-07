-- Payment burden: loan annuity relative to declared income (candidate feature: annuity / income).
-- Higher installments vs income should stress cashflow and correlate with default.
WITH app AS (
    SELECT
        target,
        amt_annuity / NULLIF(amt_income_total, 0) AS annuity_to_income
    FROM application_train
    WHERE amt_income_total > 0
      AND amt_annuity IS NOT NULL
),
bins AS (
    SELECT
        target,
        NTILE(10) OVER (ORDER BY annuity_to_income) AS decile
    FROM app
    WHERE annuity_to_income IS NOT NULL AND isfinite(annuity_to_income)
)
SELECT
    decile,
    COUNT(*) AS n,
    SUM(target) AS n_default,
    AVG(target) * 100 AS default_rate_pct
FROM bins
GROUP BY decile
ORDER BY decile;
