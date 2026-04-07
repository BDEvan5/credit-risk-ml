-- Credit history breadth: number of bureau trade lines per applicant (candidate feature: bureau row count).
-- More external history can be informative; relationship with default is empirical.
WITH bc AS (
    SELECT sk_id_curr, COUNT(*) AS n_bureau
    FROM bureau
    GROUP BY sk_id_curr
),
app AS (
    SELECT
        trn.target,
        COALESCE(bc.n_bureau, 0)::DOUBLE AS n_bureau
    FROM application_train AS trn
    LEFT JOIN bc ON trn.sk_id_curr = bc.sk_id_curr
),
bins AS (
    SELECT
        target,
        NTILE(10) OVER (ORDER BY n_bureau) AS decile
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
