-- Share of installment rows paid after scheduled date, broken out by train TARGET.
SELECT
    trn.target,
    COUNT(*) AS n_payment_rows,
    SUM(CASE WHEN ip.days_entry_payment > ip.days_instalment THEN 1 ELSE 0 END) AS n_late_rows,
    100.0 * SUM(CASE WHEN ip.days_entry_payment > ip.days_instalment THEN 1 ELSE 0 END) / COUNT(*) AS pct_late_rows
FROM installments_payments ip
INNER JOIN application_train AS trn ON ip.sk_id_curr = trn.sk_id_curr
WHERE ip.days_instalment IS NOT NULL
  AND ip.days_entry_payment IS NOT NULL
GROUP BY trn.target
ORDER BY trn.target;
