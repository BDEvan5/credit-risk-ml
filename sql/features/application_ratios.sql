-- Domain ratios and simple transforms on the current application (application_train only).
-- Mirrors common "simple features" from public kernels (credit/annuity/income ratios).
SELECT
    SK_ID_CURR,
    AMT_ANNUITY / NULLIF(AMT_CREDIT, 0) AS ratio_annuity_to_credit,
    AMT_GOODS_PRICE / NULLIF(AMT_CREDIT, 0) AS ratio_goods_price_to_credit,
    AMT_CREDIT / NULLIF(AMT_INCOME_TOTAL, 0) AS ratio_credit_to_income,
    AMT_ANNUITY / NULLIF(AMT_INCOME_TOTAL, 0) AS ratio_annuity_to_income,
    (AMT_CREDIT - AMT_GOODS_PRICE) / NULLIF(AMT_CREDIT, 0) AS ratio_credit_minus_goods_to_credit,
    EXT_SOURCE_1 * EXT_SOURCE_2 AS ext12_product,
    EXT_SOURCE_1 * EXT_SOURCE_3 AS ext13_product,
    EXT_SOURCE_2 * EXT_SOURCE_3 AS ext23_product,
    REGION_POPULATION_RELATIVE * EXT_SOURCE_1 AS ext1_times_pop_rel,
    REGION_POPULATION_RELATIVE * EXT_SOURCE_2 AS ext2_times_pop_rel,
    REGION_POPULATION_RELATIVE * EXT_SOURCE_3 AS ext3_times_pop_rel,
    -- NULL-aware mean of available EXT_SOURCE scores
    (COALESCE(EXT_SOURCE_1, 0) + COALESCE(EXT_SOURCE_2, 0) + COALESCE(EXT_SOURCE_3, 0))
        / NULLIF(
            (CASE WHEN EXT_SOURCE_1 IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN EXT_SOURCE_2 IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN EXT_SOURCE_3 IS NOT NULL THEN 1 ELSE 0 END), 0) AS ext_source_mean,
    -- Std-dev proxy: range of available EXT_SOURCE scores
    GREATEST(
        COALESCE(EXT_SOURCE_1, 0), COALESCE(EXT_SOURCE_2, 0), COALESCE(EXT_SOURCE_3, 0)
    ) - LEAST(
        COALESCE(EXT_SOURCE_1, 1), COALESCE(EXT_SOURCE_2, 1), COALESCE(EXT_SOURCE_3, 1)
    ) AS ext_source_range
FROM application_train;
