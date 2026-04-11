-- Default rate by occupation. Missing/blank occupation labeled 'Unknown'.
-- Ordered by default rate (highest first); always check n before over-interpreting small groups.
SELECT
    COALESCE(
        NULLIF(TRIM(CAST(occupation_type AS VARCHAR)), ''),
        'Unknown'
    ) AS occupation_type,
    COUNT(*) AS n,
    SUM(target) AS n_default,
    AVG(target) * 100 AS default_rate_pct
FROM application_train
GROUP BY 1
ORDER BY default_rate_pct DESC;
