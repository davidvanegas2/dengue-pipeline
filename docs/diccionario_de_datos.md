# Diccionario de datos · `gold.weekly_dengue_signal`

Una fila por **entidad territorial** y **semana epidemiológica**. Se exporta a
`data/gold/weekly_dengue_signal.parquet` (y `.csv`; el CSV se genera al correr el pipeline
y no está versionado). Las columnas van en el mismo orden que en la tabla.

**Llave:** `territorial_entity` + `epi_year` + `epi_week` (única, verificada en cada ejecución).

| Columna | Tipo | Descripción |
|---|---|---|
| `territorial_entity` | texto | Como la reporta el INS: departamento o distrito (Santiago de Cali, Barranquilla y Buenaventura van aparte de su departamento) |
| `entity_type` | texto | `departamento` o `distrito` |
| `department_code` | texto | Código DIVIPOLA del departamento, 2 dígitos (`08`, `76`) |
| `epi_year` | entero | Año **epidemiológico** (puede diferir del calendario en los bordes del año) |
| `epi_week` | entero | Semana epidemiológica, 1 a 52 o 53 (domingo a sábado) |
| `week_start` | fecha | Domingo en que empieza la semana |
| `bulletin_cumulative_cases` | entero | Casos **acumulados en el año** hasta esa semana, según el Boletín Epidemiológico Semanal. Solo las semanas con boletín cargado |
| `mean_precipitation_mm` | decimal (`DOUBLE`, 2 decimales) | Lluvia total de la semana por estación, promediada entre las estaciones de la entidad (mm) |
| `stations_with_data` | entero | Estaciones del IDEAM con al menos un día de dato esa semana |
| `suspicious_days` | entero | Días-estación marcados como sospechosos (más de 144 lecturas o más de 300 mm) |
| `sivigila_cases` | entero | Casos de dengue (eventos 210 y 220) notificados esa semana según SIVIGILA, sin descartados. Solo años cerrados; vacío en el año en curso |
| `sivigila_severe_cases` | entero | Solo dengue grave (evento 220) |
| `case_source` | texto | `sivigila`, `bulletin` o vacío: de dónde salen los casos de esa fila |

## Valores ausentes

Con los datos del piloto (750 filas):

* `mean_precipitation_mm`, `stations_with_data` y `suspicious_days` quedan vacíos (`NULL`)
  cuando ninguna estación de la entidad reportó esa semana: 164 filas. Nunca valen 0
  estaciones; el mínimo es 1.
* `sivigila_cases` y `sivigila_severe_cases` valen `0` (no vacío) en las semanas de años
  cerrados sin casos, y quedan vacíos en todo el año en curso (las 225 filas de 2026).
* `bulletin_cumulative_cases` solo tiene valor en 10 filas: 5 entidades × las semanas 26 y 27
  de 2026.
* `case_source` es `sivigila` en 525 filas, `bulletin` en 10 y vacío en 215: las semanas de
  2026 sin boletín cargado no tienen ninguna fuente de casos.

## Advertencias

* `sivigila_cases` y `bulletin_cumulative_cases` **no son comparables directamente**:
  uno es semanal y el otro acumulado (ver `RETOS.md` #2).
* La lluvia incluye días sospechosos: están contados, no excluidos (ver `RETOS.md` #6).
* Si `data/raw/sivigila/ORIGEN.txt` dice `SINTETICO`, `sivigila_cases` no es real.

## Tablas intermedias (capa plata)

| Tabla | Grano |
|---|---|
| `silver.divipola` | Municipio (código de 5 dígitos, nombre normalizado, coordenadas) |
| `silver.territorial_entities` | Entidad territorial del piloto |
| `silver.municipality_entity` | Municipio → entidad territorial (resuelve los distritos) |
| `silver.sivigila_cases` | Caso individual con códigos y fechas limpias |
| `silver.sivigila_weekly_cases` | Entidad × semana |
| `silver.ideam_municipality_aliases` | Nombre de municipio como lo escribe el IDEAM → código DIVIPOLA |
| `silver.ideam_daily_precipitation` | Estación × día, con código DIVIPOLA y bandera `suspicious_reading` |
| `silver.ideam_weekly_precipitation` | Entidad × semana |
| `silver.bulletin_cumulative_cases` | Entidad del boletín × semana del boletín |
