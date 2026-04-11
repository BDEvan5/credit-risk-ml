-- Default rate by age band (years). DAYS_BIRTH is negative days from application; older applicants have more negative values.
-- sort_key keeps plot order left-to-right by age.
WITH ages AS (
    SELECT
        TARGET,
        FLOOR((-DAYS_BIRTH) / 365.25)::INTEGER AS age_years
    FROM application_train
    WHERE DAYS_BIRTH IS NOT NULL
),
banded AS (
    SELECT
        TARGET,
        age_years,
        CASE
            WHEN age_years < 25 THEN 'Under 25'
            WHEN age_years < 30 THEN '25–29'
            WHEN age_years < 35 THEN '30–34'
            WHEN age_years < 40 THEN '35–39'
            WHEN age_years < 45 THEN '40–44'
            WHEN age_years < 50 THEN '45–49'
            WHEN age_years < 55 THEN '50–54'
            WHEN age_years < 60 THEN '55–59'
            ELSE '60 and over'
        END AS age_band,
        CASE
            WHEN age_years < 25 THEN 1
            WHEN age_years < 30 THEN 2
            WHEN age_years < 35 THEN 3
            WHEN age_years < 40 THEN 4
            WHEN age_years < 45 THEN 5
            WHEN age_years < 50 THEN 6
            WHEN age_years < 55 THEN 7
            WHEN age_years < 60 THEN 8
            ELSE 9
        END AS sort_key
    FROM ages
    WHERE age_years BETWEEN 18 AND 100
)
SELECT
    age_band,
    sort_key,
    COUNT(*) AS n,
    SUM(TARGET) AS n_default,
    AVG(TARGET) * 100 AS default_rate_pct
FROM banded
GROUP BY age_band, sort_key
ORDER BY sort_key;
