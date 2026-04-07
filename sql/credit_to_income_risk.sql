-- Leverage: requested credit vs declared income (candidate feature: credit / income).
WITH app AS (
    SELECT
        target,
        amt_credit / NULLIF(amt_income_total, 0) AS credit_to_income
    FROM application_train
    WHERE amt_income_total > 0
      AND amt_credit IS NOT NULL
),
bins AS (
    SELECT
        target,
        NTILE(10) OVER (ORDER BY credit_to_income) AS decile
    FROM app
    WHERE credit_to_income IS NOT NULL AND isfinite(credit_to_income)
)
SELECT
    decile,
    COUNT(*) AS n,
    SUM(target) AS n_default,
    AVG(target) * 100 AS default_rate_pct
FROM bins
GROUP BY decile
ORDER BY decile;
