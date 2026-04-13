-- credit_card_balance: rolling credit card utilisation and delinquency per applicant.
SELECT
    SK_ID_CURR,
    COUNT(*) AS cc_n_rows,
    COUNT(DISTINCT SK_ID_PREV) AS cc_n_prev_loans,
    SUM(AMT_BALANCE) AS cc_sum_balance,
    SUM(AMT_CREDIT_LIMIT_ACTUAL) AS cc_sum_limit,
    AVG(AMT_BALANCE / NULLIF(AMT_CREDIT_LIMIT_ACTUAL, 0)) AS cc_mean_utilisation,
    MAX(AMT_BALANCE / NULLIF(AMT_CREDIT_LIMIT_ACTUAL, 0)) AS cc_max_utilisation,
    SUM(AMT_DRAWINGS_ATM_CURRENT + AMT_DRAWINGS_POS_CURRENT) AS cc_sum_drawings,
    SUM(AMT_PAYMENT_TOTAL_CURRENT) AS cc_sum_payment_total,
    SUM(AMT_PAYMENT_CURRENT) AS cc_sum_payment_current,
    MAX(SK_DPD) AS cc_max_sk_dpd,
    SUM(SK_DPD) AS cc_sum_sk_dpd,
    SUM(CASE WHEN NAME_CONTRACT_STATUS = 'Active' THEN 1 ELSE 0 END) AS cc_n_active
FROM credit_card_balance
GROUP BY SK_ID_CURR;
