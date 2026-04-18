-- Credit bureau history rolled up to one row per current applicant (SK_ID_CURR).
SELECT
    SK_ID_CURR,
    COUNT(*) AS bureau_n_records,
    COUNT(DISTINCT SK_ID_BUREAU) AS bureau_n_distinct,
    SUM(CASE WHEN CREDIT_ACTIVE = 'Active' THEN 1 ELSE 0 END) AS bureau_num_active,
    SUM(CASE WHEN CREDIT_ACTIVE = 'Closed' THEN 1 ELSE 0 END) AS bureau_num_closed,
    SUM(CASE WHEN CREDIT_ACTIVE = 'Sold' THEN 1 ELSE 0 END) AS bureau_num_sold,
    SUM(CASE WHEN CREDIT_TYPE IN ('Credit card', 'Consumer credit') THEN 1 ELSE 0 END) AS bureau_n_card_or_consumer,
    SUM(AMT_CREDIT_SUM) AS bureau_total_credit_sum,
    SUM(AMT_CREDIT_SUM_DEBT) AS bureau_total_debt,
    SUM(AMT_CREDIT_SUM_LIMIT) AS bureau_total_limit,
    SUM(AMT_CREDIT_SUM_OVERDUE) AS bureau_total_overdue,
    MAX(CREDIT_DAY_OVERDUE) AS bureau_max_days_overdue,
    MAX(AMT_CREDIT_MAX_OVERDUE) AS bureau_max_amt_overdue,
    SUM(CASE WHEN CREDIT_ACTIVE = 'Active' THEN AMT_CREDIT_SUM ELSE 0 END) AS bureau_total_active_credit,
    AVG(DAYS_CREDIT) AS bureau_mean_days_credit,
    MIN(DAYS_CREDIT_ENDDATE) AS bureau_min_days_credit_enddate,
    MAX(DAYS_CREDIT_ENDDATE) AS bureau_max_days_credit_enddate,
    SUM(DAYS_CREDIT_ENDDATE - DAYS_CREDIT) AS bureau_sum_credit_duration,
    SUM(AMT_CREDIT_SUM_DEBT) / NULLIF(SUM(AMT_CREDIT_SUM), 0) AS bureau_debt_to_credit_ratio,
    SUM(AMT_CREDIT_SUM_OVERDUE) / NULLIF(SUM(AMT_CREDIT_SUM), 0) AS bureau_overdue_to_credit_ratio,
    -- Recency: most recent bureau record start and update (less negative = more recent)
    MAX(DAYS_CREDIT) AS bureau_most_recent_credit_days,
    MAX(DAYS_CREDIT_UPDATE) AS bureau_most_recent_update_days,
    -- Active credits with any current overdue
    SUM(CASE WHEN CREDIT_ACTIVE = 'Active' AND CREDIT_DAY_OVERDUE > 0 THEN 1 ELSE 0 END) AS bureau_n_active_overdue,
    -- Active debt-to-credit ratio (tighter signal than all-credit ratio)
    SUM(CASE WHEN CREDIT_ACTIVE = 'Active' THEN AMT_CREDIT_SUM_DEBT ELSE 0 END)
        / NULLIF(SUM(CASE WHEN CREDIT_ACTIVE = 'Active' THEN AMT_CREDIT_SUM ELSE 0 END), 0) AS bureau_active_debt_to_credit,
    -- Credit type diversity
    COUNT(DISTINCT CREDIT_TYPE) AS bureau_n_credit_types,
    -- Average prolongation count (sign of repayment difficulty)
    AVG(CNT_CREDIT_PROLONG) AS bureau_mean_prolongation
FROM bureau
GROUP BY SK_ID_CURR;
