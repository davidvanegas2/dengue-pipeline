-- Silver SIVIGILA: typed cases with complete DANE codes, then weekly entity counts.

CREATE OR REPLACE TABLE silver.sivigila_cases AS
SELECT
    dane_code(cod_dpto_o, 2) AS department_code,
    municipality_code(cod_dpto_o, cod_mun_o) AS municipality_code,
    cast(ano AS INTEGER) AS epi_year,
    cast(semana AS INTEGER) AS epi_week,
    trim(cod_eve) AS event_code,
    upper(trim(coalesce(ajuste, '0'))) AS adjustment,
    trim(tip_cas) AS case_type,
    trim(pac_hos) AS hospitalization,
    trim(con_fin) AS final_condition,
    coalesce(
        try_cast(fec_not AS DATE), cast(try_strptime(fec_not, '%d/%m/%Y') AS DATE)
    ) AS notification_date,
    coalesce(
        try_cast(ini_sin AS DATE), cast(try_strptime(ini_sin, '%d/%m/%Y') AS DATE)
    ) AS symptom_onset_date
FROM bronze.sivigila;

-- Pilot assumptions to revisit in RETOS.md #3:
-- * Count event 210 (dengue) and 220 (severe dengue).
-- * Exclude adjustment 6 (discarded) and D (data-entry error).
-- * Use the reported week, not the symptom-onset week.
CREATE OR REPLACE TABLE silver.sivigila_weekly_cases AS
SELECT
    me.territorial_entity,
    c.epi_year,
    c.epi_week,
    count(*) FILTER (WHERE c.event_code IN ('210', '220')) AS cases,
    count(*) FILTER (WHERE c.event_code = '220') AS severe_cases,
    count(*) FILTER (WHERE c.event_code IN ('210', '220') AND c.hospitalization = '1')
        AS hospitalized
FROM silver.sivigila_cases AS c
INNER JOIN silver.municipality_entity AS me
    ON c.municipality_code = me.municipality_code
WHERE c.adjustment NOT IN ('6', 'D')
GROUP BY me.territorial_entity, c.epi_year, c.epi_week;
