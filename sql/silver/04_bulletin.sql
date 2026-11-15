-- Silver INS bulletin: cumulative yearly cases by territorial entity.
-- Deriving weekly counts is a workshop challenge (RETOS.md #1).

CREATE OR REPLACE TABLE silver.bulletin_cumulative_cases AS
SELECT
    b.bulletin_year AS epi_year,
    b.bulletin_week AS epi_week,
    b.territorial_entity AS bulletin_entity,
    e.territorial_entity,
    b.total_cases AS cumulative_cases,
    b.warning_signs_pct,
    b.severe_pct,
    b.filename,
    e.territorial_entity IS NOT NULL AS in_pilot
FROM bronze.dengue_bulletin AS b
LEFT JOIN silver.territorial_entities AS e
    ON normalize_name(b.territorial_entity) = e.entity_normalized
WHERE NOT b.is_total;
