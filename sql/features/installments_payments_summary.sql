-- Per-applicant aggregates from installments_payments (Kaggle-style payment behaviour).
-- DAYS_INSTALMENT is negative (days before application). Recent = closer to 0.
WITH per_loan AS (
    SELECT
        SK_ID_CURR,
        SK_ID_PREV,
        COUNT(*) AS n_inst_rows,
        SUM(AMT_INSTALMENT) AS sum_instalment,
        SUM(AMT_PAYMENT) AS sum_payment,
        SUM(CASE WHEN DAYS_ENTRY_PAYMENT > DAYS_INSTALMENT THEN 1 ELSE 0 END) AS n_late_by_schedule,
        SUM(CASE WHEN AMT_PAYMENT < AMT_INSTALMENT AND AMT_INSTALMENT > 0 THEN 1 ELSE 0 END) AS n_underpaid,
        -- Last 365 days of payment history
        SUM(CASE WHEN DAYS_INSTALMENT >= -365 AND DAYS_ENTRY_PAYMENT > DAYS_INSTALMENT THEN 1 ELSE 0 END) AS n_late_last365,
        SUM(CASE WHEN DAYS_INSTALMENT >= -365 THEN 1 ELSE 0 END) AS n_inst_last365,
        SUM(CASE WHEN DAYS_INSTALMENT >= -365 THEN AMT_PAYMENT ELSE 0 END) AS sum_pay_last365,
        SUM(CASE WHEN DAYS_INSTALMENT >= -365 THEN AMT_INSTALMENT ELSE 0 END) AS sum_inst_last365
    FROM installments_payments
    GROUP BY SK_ID_CURR, SK_ID_PREV
)
SELECT
    SK_ID_CURR,
    COUNT(*) AS inst_num_prev_loans,
    SUM(n_inst_rows) AS inst_total_rows,
    SUM(sum_instalment) AS inst_sum_instalment,
    SUM(sum_payment) AS inst_sum_payment,
    SUM(n_late_by_schedule) AS inst_sum_late_vs_schedule,
    SUM(n_underpaid) AS inst_sum_underpaid,
    AVG(sum_payment / NULLIF(sum_instalment, 0)) AS inst_mean_payment_ratio_per_loan,
    SUM(sum_payment) / NULLIF(SUM(sum_instalment), 0) AS inst_overall_payment_to_instalment,
    -- Recency features
    SUM(n_late_last365)::DOUBLE / NULLIF(SUM(n_inst_last365), 0) AS inst_pct_late_last365,
    SUM(sum_pay_last365) / NULLIF(SUM(sum_inst_last365), 0) AS inst_payment_ratio_last365
FROM per_loan
GROUP BY SK_ID_CURR;
