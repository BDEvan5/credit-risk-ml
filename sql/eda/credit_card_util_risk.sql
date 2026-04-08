-- Revolving utilization: mean balance / limit on credit cards over history (candidate feature: CC utilization).
-- Applicants with at least one CC balance row with positive limit.
WITH cc AS (
    SELECT
        sk_id_curr,
        AVG(amt_balance / NULLIF(amt_credit_limit_actual, 0)) AS avg_util
    FROM credit_card_balance
    WHERE amt_credit_limit_actual > 0
      AND amt_balance IS NOT NULL
    GROUP BY sk_id_curr
),
app AS (
    SELECT
        trn.target,
        cc.avg_util
    FROM application_train AS trn
    INNER JOIN cc ON trn.sk_id_curr = cc.sk_id_curr
    WHERE cc.avg_util IS NOT NULL AND isfinite(cc.avg_util)
),
bins AS (
    SELECT
        target,
        NTILE(10) OVER (ORDER BY avg_util) AS decile
    FROM app
)
SELECT
    decile,
    COUNT(*) AS n,
    SUM(target) AS n_default,
    AVG(target) * 100 AS default_rate_pct
FROM bins
GROUP BY decile
ORDER BY decile;
