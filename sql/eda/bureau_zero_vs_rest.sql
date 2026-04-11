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
    CASE
        WHEN n_bureau = 0 THEN 'No bureau records'
        ELSE 'Has bureau history'
    END AS segment,
    COUNT(*) AS n,
    SUM(target) AS n_default,
    AVG(target) * 100 AS default_rate_pct
FROM app
GROUP BY 1
ORDER BY segment;
