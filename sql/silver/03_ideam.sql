-- Silver IDEAM: daily station precipitation and weekly territorial-entity totals.

CREATE OR REPLACE TABLE silver.ideam_daily_precipitation AS
WITH base AS (
    SELECT
        nombreestacion AS station_name,
        trim(codigoestacion) AS station_code,
        normalize_name(departamento) AS department_normalized,
        normalize_name(municipio) AS municipality_normalized,
        cast(substr(fecha, 1, 10) AS DATE) AS observation_date,
        -- DECIMAL makes parallel aggregation reproducible across runs.
        cast(precipitacion_mm AS DECIMAL(14, 4)) AS precipitation_mm,
        cast(n_lecturas AS INTEGER) AS reading_count
    FROM bronze.ideam_daily_precipitation
)

SELECT
    b.*,
    d.municipality_code,
    d.department_code,
    coalesce(a.divipola_municipality_normalized, b.municipality_normalized)
        AS divipola_municipality_normalized,
    -- Flag outliers without removing them; handling them is a workshop challenge.
    -- A station reporting every 10 minutes should have 144 daily readings.
    (b.reading_count > 144 OR b.precipitation_mm > 300) AS suspicious_reading
FROM base AS b
LEFT JOIN silver.ideam_municipality_aliases AS a
    ON
        b.department_normalized = a.department_normalized
        AND b.municipality_normalized = a.ideam_municipality_normalized
LEFT JOIN silver.divipola AS d
    ON
        b.department_normalized = d.department_normalized
        AND coalesce(a.divipola_municipality_normalized, b.municipality_normalized)
        = d.municipality_normalized;

CREATE OR REPLACE TABLE silver.ideam_weekly_precipitation AS
WITH per_station AS (
    SELECT
        me.territorial_entity,
        p.station_code,
        epi_year(p.observation_date) AS epi_year,
        epi_week(p.observation_date) AS epi_week,
        sum(p.precipitation_mm) AS precipitation_mm,
        count(*) AS days_with_data,
        count(*) FILTER (WHERE p.suspicious_reading) AS suspicious_days
    FROM silver.ideam_daily_precipitation AS p
    INNER JOIN silver.municipality_entity AS me
        ON p.municipality_code = me.municipality_code
    GROUP BY
        me.territorial_entity,
        p.station_code,
        epi_year(p.observation_date),
        epi_week(p.observation_date)
)

SELECT
    territorial_entity,
    epi_year,
    epi_week,
    round(avg(precipitation_mm), 2) AS mean_precipitation_mm,
    count(DISTINCT station_code) AS stations_with_data,
    cast(sum(days_with_data) AS INTEGER) AS station_days_with_data,
    cast(sum(suspicious_days) AS INTEGER) AS suspicious_days
FROM per_station
GROUP BY territorial_entity, epi_year, epi_week;
