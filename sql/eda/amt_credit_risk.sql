-- Default rate by decile of requested credit amount (AMT_CREDIT).
WITH bins AS (
    SELECT
        target,
        NTILE(10) OVER (ORDER BY amt_credit) AS decile
    FROM application_train
    WHERE amt_credit IS NOT NULL
)
SELECT
    decile,
    COUNT(*) AS n,
    SUM(target) AS n_default,
    AVG(target) * 100 AS default_rate_pct
FROM bins
GROUP BY decile
ORDER BY decile;
