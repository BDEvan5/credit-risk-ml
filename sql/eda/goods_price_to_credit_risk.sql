-- Loan structure: goods price vs disbursed credit (candidate feature: how much of the loan finances the good).
-- Values far below 1 can indicate fees/cash-out; useful for segmentation.
WITH app AS (
    SELECT
        target,
        amt_goods_price / NULLIF(amt_credit, 0) AS goods_to_credit
    FROM application_train
    WHERE amt_credit > 0
      AND amt_goods_price IS NOT NULL
),
bins AS (
    SELECT
        target,
        NTILE(10) OVER (ORDER BY goods_to_credit) AS decile
    FROM app
    WHERE goods_to_credit IS NOT NULL AND isfinite(goods_to_credit)
)
SELECT
    decile,
    COUNT(*) AS n,
    SUM(target) AS n_default,
    AVG(target) * 100 AS default_rate_pct
FROM bins
GROUP BY decile
ORDER BY decile;
