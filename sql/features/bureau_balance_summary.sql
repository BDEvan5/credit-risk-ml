-- First, roll bureau_balance up to bureau level, then join to get SK_ID_CURR
WITH bureau_balance_agg AS (
    SELECT
        SK_ID_BUREAU,
        COUNT(*)                                                        AS total_months,
        SUM(CASE WHEN STATUS NOT IN ('0', 'C', 'X') THEN 1 ELSE 0 END) AS months_1plus_dpd,
        SUM(CASE WHEN STATUS IN ('2','3','4','5')    THEN 1 ELSE 0 END) AS months_2plus_dpd,
        SUM(CASE WHEN STATUS IN ('3','4','5')        THEN 1 ELSE 0 END) AS months_3plus_dpd
    FROM bureau_balance
    GROUP BY SK_ID_BUREAU
)
SELECT
    b.SK_ID_CURR,
    SUM(bba.total_months)                                               AS total_bureau_months,
    SUM(bba.months_1plus_dpd)                                           AS total_months_1plus_dpd,
    SUM(bba.months_2plus_dpd)                                           AS total_months_2plus_dpd,
    SUM(bba.months_3plus_dpd)                                           AS total_months_3plus_dpd,
    SUM(bba.months_1plus_dpd) / NULLIF(SUM(bba.total_months), 0)       AS pct_months_1plus_dpd,
    SUM(bba.months_2plus_dpd) / NULLIF(SUM(bba.total_months), 0)       AS pct_months_2plus_dpd,
    SUM(bba.months_3plus_dpd) / NULLIF(SUM(bba.total_months), 0)       AS pct_months_3plus_dpd
FROM bureau b
JOIN bureau_balance_agg bba ON b.SK_ID_BUREAU = bba.SK_ID_BUREAU
GROUP BY b.SK_ID_CURR;