-- Gold: one row per territorial entity and epidemiological week.
-- Consumed by the ML workshop; see docs/diccionario_de_datos.md.

CREATE OR REPLACE TABLE gold.weekly_dengue_signal AS
WITH bounds AS (
    SELECT
        least(
            (SELECT min(observation_date) FROM silver.ideam_daily_precipitation),
            (SELECT make_date(min(epi_year), 1, 4) FROM silver.sivigila_cases)
        ) AS start_date,
        (SELECT max(observation_date) FROM silver.ideam_daily_precipitation) AS end_date
),

days AS (
    SELECT cast(unnest(generate_series(start_date, end_date, INTERVAL 1 DAY)) AS DATE) AS day_date
    FROM bounds
),

weeks AS (
    SELECT DISTINCT
        epi_year(day_date) AS epi_year,
        epi_week(day_date) AS epi_week,
        epi_week_start(day_date) AS week_start
    FROM days
),

sivigila_years AS (
    SELECT DISTINCT epi_year FROM silver.sivigila_cases
),

-- Build every entity-week combination, even when observations are missing.
spine AS (
    SELECT
        e.territorial_entity,
        e.entity_type,
        e.department_code,
        s.epi_year,
        s.epi_week,
        s.week_start,
        s.epi_year IN (SELECT a.epi_year FROM sivigila_years AS a) AS closed_year
    FROM silver.territorial_entities AS e
    CROSS JOIN weeks AS s
)

SELECT
    es.territorial_entity,
    es.entity_type,
    es.department_code,
    es.epi_year,
    es.epi_week,
    es.week_start,
    b.cumulative_cases AS bulletin_cumulative_cases,
    p.mean_precipitation_mm,
    p.stations_with_data,
    p.suspicious_days,
    CASE WHEN es.closed_year THEN coalesce(c.cases, 0) END AS sivigila_cases,
    CASE WHEN es.closed_year THEN coalesce(c.severe_cases, 0) END AS sivigila_severe_cases,
    CASE
        WHEN es.closed_year THEN 'sivigila'
        WHEN b.cumulative_cases IS NOT NULL THEN 'bulletin'
    END AS case_source
FROM spine AS es
LEFT JOIN silver.sivigila_weekly_cases AS c
    ON
        es.territorial_entity = c.territorial_entity
        AND es.epi_year = c.epi_year
        AND es.epi_week = c.epi_week
LEFT JOIN silver.bulletin_cumulative_cases AS b
    ON
        es.territorial_entity = b.territorial_entity
        AND es.epi_year = b.epi_year
        AND es.epi_week = b.epi_week
LEFT JOIN silver.ideam_weekly_precipitation AS p
    ON
        es.territorial_entity = p.territorial_entity
        AND es.epi_year = p.epi_year
        AND es.epi_week = p.epi_week
ORDER BY es.territorial_entity, es.epi_year, es.epi_week;
