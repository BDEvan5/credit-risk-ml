-- Per-applicant aggregates from installments_payments.
-- Payment delay = DAYS_ENTRY_PAYMENT - DAYS_INSTALMENT (positive = late).
SELECT
    SK_ID_CURR,
    COUNT(*)                                                                     AS inst_num_payments,
    SUM(CASE WHEN DAYS_ENTRY_PAYMENT > DAYS_INSTALMENT THEN 1 ELSE 0 END)       AS inst_num_late,
    AVG(GREATEST(DAYS_ENTRY_PAYMENT - DAYS_INSTALMENT, 0))                      AS inst_avg_days_late,
    MAX(GREATEST(DAYS_ENTRY_PAYMENT - DAYS_INSTALMENT, 0))                      AS inst_max_days_late,
    SUM(CASE WHEN DAYS_ENTRY_PAYMENT > DAYS_INSTALMENT THEN 1 ELSE 0 END)
        ::DOUBLE / COUNT(*)                                                      AS inst_pct_late,
    SUM(AMT_PAYMENT) / NULLIF(SUM(AMT_INSTALMENT), 0)                           AS inst_payment_ratio,
    SUM(AMT_INSTALMENT - AMT_PAYMENT)                                            AS inst_total_underpaid
FROM installments_payments
GROUP BY SK_ID_CURR;
