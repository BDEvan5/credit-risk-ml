-- Joint distribution: income decile × credit amount decile → default rate and counts.
WITH inc AS (
    SELECT
        sk_id_curr,
        target,
        NTILE(10) OVER (ORDER BY amt_income_total) AS income_decile
    FROM application_train
    WHERE amt_income_total IS NOT NULL
),
cr AS (
    SELECT
        sk_id_curr,
        NTILE(10) OVER (ORDER BY amt_credit) AS credit_decile
    FROM application_train
    WHERE amt_credit IS NOT NULL
),
j AS (
    SELECT
        i.target,
        i.income_decile,
        c.credit_decile
    FROM inc AS i
    INNER JOIN cr AS c ON i.sk_id_curr = c.sk_id_curr
)
SELECT
    income_decile,
    credit_decile,
    COUNT(*) AS n,
    SUM(target) AS n_default,
    AVG(target) * 100 AS default_rate_pct
FROM j
GROUP BY income_decile, credit_decile
ORDER BY income_decile, credit_decile;
