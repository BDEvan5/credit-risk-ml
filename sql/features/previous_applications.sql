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
    MIN(CASE WHEN CODE_REJECT_REASON IS NOT NULL THEN CODE_REJECT_REASON END) AS first_rejection_reason
FROM previous_application
GROUP BY SK_ID_CURR;
