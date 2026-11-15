-- Silver reference tables: DANE DIVIPOLA, INS entities and IDEAM name aliases.
-- Preserve source field names in bronze and expose English aliases in silver.

CREATE OR REPLACE TABLE silver.divipola AS
SELECT
    nom_mpio AS municipality,
    dane_code(cod_dpto, 2) AS department_code,
    dane_code(cod_mpio, 5) AS municipality_code,
    normalize_name(dpto) AS department_normalized,
    normalize_name(nom_mpio) AS municipality_normalized,
    -- Source coordinates use decimal commas, for example "-74,815546".
    cast(replace(latitud, ',', '.') AS DOUBLE) AS latitude,
    cast(replace(longitud, ',', '.') AS DOUBLE) AS longitude
FROM bronze.divipola;

CREATE OR REPLACE TABLE silver.territorial_entities AS
SELECT
    entidad_territorial AS territorial_entity,
    tipo AS entity_type,
    normalize_name(entidad_territorial) AS entity_normalized,
    dane_code(cod_dpto, 2) AS department_code,
    CASE
        WHEN nullif(trim(cod_mpio), '') IS NOT NULL THEN dane_code(cod_mpio, 5)
    END AS municipality_code
FROM bronze.territorial_entities;

-- INS reports districts separately: the Valle del Cauca bulletin row excludes Cali.
CREATE OR REPLACE TABLE silver.municipality_entity AS
SELECT
    d.municipality_code,
    d.department_code,
    coalesce(dist.territorial_entity, dep.territorial_entity) AS territorial_entity
FROM silver.divipola AS d
LEFT JOIN silver.territorial_entities AS dist
    ON d.municipality_code = dist.municipality_code
LEFT JOIN silver.territorial_entities AS dep
    ON d.department_code = dep.department_code AND dep.entity_type = 'departamento';

CREATE OR REPLACE TABLE silver.ideam_municipality_aliases AS
SELECT
    normalize_name(departamento) AS department_normalized,
    normalize_name(municipio_ideam) AS ideam_municipality_normalized,
    normalize_name(municipio_divipola) AS divipola_municipality_normalized
FROM bronze.ideam_municipality_aliases;
