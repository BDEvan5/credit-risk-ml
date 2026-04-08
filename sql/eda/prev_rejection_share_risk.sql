-- Prior underwriting friction: share of previous applications with a recorded rejection reason (candidate aggregate feature).
-- Only applicants with at least one previous application in the table.
WITH pa AS (
    SELECT
        sk_id_curr,
        COUNT(*) AS n_prev,
        SUM(CASE WHEN code_reject_reason IS NOT NULL THEN 1 ELSE 0 END) AS n_with_reject
    FROM previous_application
    GROUP BY sk_id_curr
),
app AS (
    SELECT
        trn.target,
        (pa.n_with_reject::DOUBLE / pa.n_prev) AS reject_share
    FROM application_train AS trn
    INNER JOIN pa ON trn.sk_id_curr = pa.sk_id_curr
    WHERE pa.n_prev >= 1
),
bins AS (
    SELECT
        target,
        NTILE(10) OVER (ORDER BY reject_share) AS decile
    FROM app
    WHERE reject_share IS NOT NULL AND isfinite(reject_share)
)
SELECT
    decile,
    COUNT(*) AS n,
    SUM(target) AS n_default,
    AVG(target) * 100 AS default_rate_pct
FROM bins
GROUP BY decile
ORDER BY decile;
