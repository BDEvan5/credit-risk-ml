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
        COALESCE(bc.n_bureau, 0)::BIGINT AS n_bureau
    FROM application_train AS trn
    LEFT JOIN bc ON trn.sk_id_curr = bc.sk_id_curr
)
SELECT
    n_bureau,
    COUNT(*) AS n,
    SUM(target) AS n_default,
    AVG(target) * 100 AS default_rate_pct
FROM app
GROUP BY n_bureau
ORDER BY n_bureau;
