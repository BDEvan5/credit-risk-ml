-- Default rate by age quartile (DAYS_BIRTH is negative days; higher values = younger).
WITH q AS (
    SELECT
        target,
        days_birth,
        NTILE(4) OVER (ORDER BY days_birth DESC) AS age_quartile
    FROM application_train
    WHERE days_birth IS NOT NULL
)
SELECT
    age_quartile,
    MIN(days_birth) AS days_birth_min,
    MAX(days_birth) AS days_birth_max,
    ROUND((-MAX(days_birth) / 365.25)::DOUBLE, 1) AS age_years_min,
    ROUND((-MIN(days_birth) / 365.25)::DOUBLE, 1) AS age_years_max,
    COUNT(*) AS n,
    SUM(target) AS n_default,
    AVG(target) * 100 AS default_rate_pct
FROM q
GROUP BY age_quartile
ORDER BY age_quartile;
