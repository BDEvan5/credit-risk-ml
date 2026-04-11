-- Mean external bureau scores by outcome (TARGET); useful summary alongside distribution plots in the notebook.
SELECT
    target,
    AVG(ext_source_1) AS avg_ext_source_1,
    AVG(ext_source_2) AS avg_ext_source_2,
    AVG(ext_source_3) AS avg_ext_source_3
FROM application_train
GROUP BY target
ORDER BY target;
