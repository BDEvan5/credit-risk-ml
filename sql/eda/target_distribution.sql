-- Train-set class balance: counts and share for TARGET (0 = no default, 1 = default).
SELECT
    target,
    COUNT(*) AS n,
    100.0 * COUNT(*) / SUM(COUNT(*)) OVER () AS pct
FROM application_train
GROUP BY target
ORDER BY target;
