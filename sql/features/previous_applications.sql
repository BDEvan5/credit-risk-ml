-- Per-applicant aggregates from previous_application (join key: SK_ID_CURR).
SELECT
    SK_ID_CURR,
    COUNT(*) AS num_applications,
    SUM(AMT_APPLICATION) AS total_amount_applied,
    SUM(AMT_CREDIT) AS total_amount_credit,
    SUM(CASE WHEN AMT_CREDIT > 0 THEN 1 ELSE 0 END) AS num_successful_applications,
    SUM(CASE WHEN AMT_CREDIT > 0 THEN 1 ELSE 0 END)::DOUBLE / COUNT(*) AS pct_successful,
    CASE
        WHEN SUM(CASE WHEN AMT_CREDIT > 0 THEN 1 ELSE 0 END)::DOUBLE / COUNT(*) < 1.0 THEN 1
        ELSE 0
    END AS was_rejected,
    COUNT(DISTINCT CODE_REJECT_REASON) AS num_unique_rejection_reasons,
    MIN(CASE WHEN CODE_REJECT_REASON IS NOT NULL THEN CODE_REJECT_REASON END) AS first_rejection_reason,
    SUM(CASE WHEN FLAG_LAST_APPL_PER_CONTRACT = 'Y' THEN 1 ELSE 0 END) AS prev_n_last_per_contract,
    AVG(AMT_APPLICATION) AS prev_mean_amt_application,
    AVG(AMT_CREDIT) AS prev_mean_amt_credit,
    MAX(AMT_CREDIT) AS prev_max_amt_credit,
    MIN(DAYS_DECISION) AS prev_min_days_decision,
    MAX(DAYS_DECISION) AS prev_max_days_decision,
    SUM(CASE WHEN NAME_CONTRACT_STATUS = 'Approved' THEN 1 ELSE 0 END) AS prev_n_approved,
    SUM(CASE WHEN NAME_CONTRACT_STATUS = 'Refused' THEN 1 ELSE 0 END) AS prev_n_refused,
    SUM(CASE WHEN NAME_CONTRACT_STATUS = 'Canceled' THEN 1 ELSE 0 END) AS prev_n_canceled,
    SUM(CASE WHEN NAME_CLIENT_TYPE = 'Repeater' THEN 1 ELSE 0 END) AS prev_n_repeater,
    SUM(CASE WHEN NAME_CLIENT_TYPE = 'New' THEN 1 ELSE 0 END) AS prev_n_new_client,
    SUM(CASE WHEN NAME_PAYMENT_TYPE = 'Cash through the bank' THEN 1 ELSE 0 END) AS prev_n_pay_cash_bank,
    COUNT(DISTINCT NAME_PRODUCT_TYPE) AS prev_n_distinct_product_types
FROM previous_application
GROUP BY SK_ID_CURR;
