-- POS_CASH_balance: monthly snapshots per previous credit; aggregate to applicant level.
SELECT
    SK_ID_CURR,
    COUNT(*) AS pos_n_rows,
    COUNT(DISTINCT SK_ID_PREV) AS pos_n_prev_loans,
    SUM(CNT_INSTALMENT_FUTURE) AS pos_sum_instalments_future,
    AVG(CNT_INSTALMENT_FUTURE) AS pos_mean_instalments_future,
    MAX(CNT_INSTALMENT_FUTURE) AS pos_max_instalments_future,
    SUM(SK_DPD) AS pos_sum_dpd,
    MAX(SK_DPD) AS pos_max_dpd,
    SUM(SK_DPD_DEF) AS pos_sum_dpd_def,
    MAX(SK_DPD_DEF) AS pos_max_dpd_def,
    AVG(SK_DPD) AS pos_mean_dpd,
    SUM(CASE WHEN NAME_CONTRACT_STATUS = 'Active' THEN 1 ELSE 0 END) AS pos_n_status_active,
    SUM(CASE WHEN NAME_CONTRACT_STATUS = 'Completed' THEN 1 ELSE 0 END) AS pos_n_status_completed,
    SUM(CASE WHEN NAME_CONTRACT_STATUS = 'Signed' THEN 1 ELSE 0 END) AS pos_n_status_signed,
    -- Recency: DPD in last 12 months vs overall
    SUM(CASE WHEN MONTHS_BALANCE >= -12 AND SK_DPD > 0 THEN 1 ELSE 0 END) AS pos_n_dpd_last12,
    SUM(CASE WHEN MONTHS_BALANCE >= -12 THEN 1 ELSE 0 END) AS pos_n_rows_last12,
    SUM(CASE WHEN MONTHS_BALANCE >= -12 AND SK_DPD > 0 THEN 1 ELSE 0 END)::DOUBLE
        / NULLIF(SUM(CASE WHEN MONTHS_BALANCE >= -12 THEN 1 ELSE 0 END), 0) AS pos_pct_dpd_last12
FROM POS_CASH_balance
GROUP BY SK_ID_CURR;
