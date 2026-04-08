-- Mean normalized external bureau scores by outcome (TARGET); NULLs ignored by AVG.
SELECT
    target,
    AVG(ext_source_1) AS avg_ext_source_1,
    AVG(ext_source_2) AS avg_ext_source_2,
    AVG(ext_source_3) AS avg_ext_source_3
FROM application_train
GROUP BY target
ORDER BY target;
