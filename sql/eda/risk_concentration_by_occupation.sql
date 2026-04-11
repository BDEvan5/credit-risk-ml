-- Cumulative % of applications and of defaults when occupations are ordered by default rate (highest first).
-- Same readout as a Lorenz-style curve: steep rise means defaults concentrate in a few high-rate job groups.
WITH occ AS (
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
),
ord AS (
    SELECT
        occupation_type,
        n,
        n_default,
        default_rate_pct,
        SUM(n) OVER (
            ORDER BY default_rate_pct DESC, occupation_type
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cum_n,
        SUM(n_default) OVER (
            ORDER BY default_rate_pct DESC, occupation_type
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cum_def
    FROM occ
),
tot AS (
    SELECT SUM(n) AS total_n, SUM(n_default) AS total_def FROM occ
)
SELECT
    occupation_type,
    n,
    n_default,
    default_rate_pct,
    100.0 * cum_n / NULLIF((SELECT total_n FROM tot), 0) AS cum_pop_pct_worst_first,
    100.0 * cum_def / NULLIF((SELECT total_def FROM tot), 0) AS cum_default_pct_worst_first
FROM ord
ORDER BY default_rate_pct DESC, occupation_type;
