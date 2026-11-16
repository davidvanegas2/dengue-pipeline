# Fuentes de datos

Todas son públicas y oficiales. Aquí está lo que trae cada una, cómo se obtuvo la copia
del repositorio y las trampas que **ya encontramos** (con evidencia).

## 1. Boletín Epidemiológico Semanal (BES) · INS

* **Qué es:** el reporte oficial semanal del año en curso, en PDF.
* **Dónde:** <https://www.ins.gov.co/buscador-eventos/Paginas/Vista-Boletin-Epidemilogico.aspx>
* **En el repo:** `data/raw/boletines/extracto_bes_2026_s26.pdf` y `..._s27.pdf`: extractos
  de 6-7 páginas (la sección de dengue) de los boletines de las semanas 26 y 27 de 2026.
  Se recortaron para que el repositorio pese poco; el código funciona igual con el PDF
  completo porque busca la tabla por su título.
* **Tabla usada:** *"Casos notificados de dengue por entidad territorial de procedencia y
  clasificación"*. Columnas: entidad territorial, casos totales (acumulados en el año),
  % con signos de alarma, % grave, esperado y observado en las últimas cuatro semanas.

| Trampa | Evidencia |
|---|---|
| La tabla cambia de número y de página | Semana 26: Tabla 17, página 28. Semana 27: Tabla 23, página 33 |
| La página tiene dos columnas y la tabla cambia de lado | Semana 26: izquierda. Semana 27: derecha |
| `crop()` deja colar letras de la otra columna | `Putumayo 318 24,8 1,3 48 66 e`: se pierden 733 casos (4 filas) |
| Números en formato colombiano | `9 504`, `30,3` |
| Números partidos por el PDF | `Meta 9 504 30,3 0,9 2 139 20 79` (2139 y 2079) |
| Los distritos van aparte de su departamento | "Valle del Cauca" no incluye a Santiago de Cali ni a Buenaventura |
| El acumulado puede bajar | Putumayo: 318 (sem. 26) → 309 (sem. 27) |
| El formato puede variar entre semanas | Solo se verificaron las semanas 26 y 27. Valida cada boletín contra su fila *Total* antes de confiar en él |

## 2. SIVIGILA · microdatos (INS)

* **Qué es:** un registro por caso notificado, desde 2007. **Solo años cerrados.**
* **Dónde:** portal SIVIGILA → *Buscador de microdatos* (<https://portalsivigila.ins.gov.co/>).
  Se descarga a mano por evento y año. Pasos: [`data/raw/sivigila/LEEME.md`](../data/raw/sivigila/LEEME.md).
* **En el repo:** `data/raw/sivigila/sivigila_dengue_piloto.csv`: microdatos **reales** del
  INS para Valle del Cauca y Atlántico, dengue (210) y dengue grave (220), años 2024 y 2025
  (112 908 casos). Se prepararon con `dengue-pipeline prepare-sivigila` a partir de 4
  archivos nacionales (`Datos_AAAA_EEE.xlsx`). `ORIGEN.txt` dice `INS`; si dijera
  `SINTETICO`, serían números inventados.
* **Columnas que usa el piloto** (el archivo real trae unas 74):

| Columna | Significado |
|---|---|
| `cod_eve` | Evento: 210 dengue, 220 dengue grave, 580 mortalidad por dengue |
| `semana`, `ano` | Semana y año epidemiológicos |
| `cod_dpto_o`, `cod_mun_o` | Departamento y municipio de **ocurrencia** (también hay `_r` de residencia y `_n` de notificación) |
| `fec_not`, `ini_sin` | Fecha de notificación e inicio de síntomas |
| `tip_cas` | Clasificación inicial del caso |
| `ajuste` | Seguimiento y clasificación final (6 = descartado, D = error de digitación; verifícalo en el diccionario del INS) |
| `pac_hos`, `con_fin` | Hospitalizado, condición final |

| Trampa | Evidencia |
|---|---|
| Fechas guardadas como texto en español | `2/12/2024 12:00:00 a. m.` (día/mes/año). `CAST(... AS DATE)` lanza un error de conversión; `TRY_CAST(... AS DATE)` devuelve `NULL`. La macro `parse_date_text()` las convierte |
| Los códigos pueden perder los ceros | Las descargas del INS traen `08` y `001`, pero Excel puede quitarlos o convertirlos en decimales (`8.0`): la macro `dane_code()` limpia y rellena |
| Casos descartados | Las descargas de 2024 y 2025 traen `ajuste` 0, 3, 5 y 7 (ninguno 6 ni D); el piloto filtra 6 y D por seguridad |

Referencia útil: el paquete de R [`sivirep`](https://github.com/epiverse-trace/sivirep)
documenta las columnas de los microdatos.

## 3. IDEAM · precipitación (datos.gov.co)

* **Qué es:** lecturas de lluvia de estaciones automáticas, cada 10 minutos.
* **Dónde:** <https://www.datos.gov.co/resource/s54a-sgyg.json> (API Socrata, consultas SoQL).
  Temperatura: `sbwg-7ju4`. Humedad: `uext-mhny`. Series históricas validadas: portal
  DHIME del IDEAM.
* **Tamaño:** más de **165 millones de filas**. No se descarga completo: se pide la
  suma diaria por estación (`GROUP BY` en el servidor) mes a mes.
* **En el repo:** `data/raw/ideam/precipitacion_diaria_piloto.parquet`: 17 698
  días-estación, Valle del Cauca y Atlántico, del 1 de enero de 2024 al 13 de noviembre
  de 2026 (descargado el 14 de noviembre de 2026). Para actualizarlo:
  `uv run dengue-pipeline download-ideam`.

| Trampa | Evidencia |
|---|---|
| El nombre del departamento cambió en 2026 | `VALLE DEL CAUCA` → `Valle Del Cauca`, `ATLANTICO` → `Atlantico` |
| No trae código DIVIPOLA; los nombres no coinciden con el DANE | IDEAM `CALI` vs DANE `SANTIAGO DE CALI`; `BUGA` vs `GUADALAJARA DE BUGA` |
| Mismo nombre en dos departamentos | `CANDELARIA` existe en Valle (76130) y Atlántico (08141) |
| Lecturas duplicadas | Días con hasta 16 416 lecturas en una estación (lo normal: 144) |
| Valores imposibles | 825,8 mm en un día en Juan de Acosta (Atlántico), 2026-05-10 |
| Huecos de cobertura | Enero-agosto de 2024: solo 6-8 estaciones en el piloto; desde 2025: 20-29 |
| Datos crudos sin validar | El propio IDEAM advierte que son instantáneos y sin validación |

## 4. DIVIPOLA · DANE (datos.gov.co)

* **Qué es:** códigos oficiales de departamentos y municipios.
* **Dónde:** <https://www.datos.gov.co/resource/gdxc-w37w.json>
* **En el repo:** `data/reference/divipola_piloto.csv`: los 65 municipios del Valle y del Atlántico.
* **Trampa:** las coordenadas vienen con coma decimal (`-74,815546`).

## 5. Referencias propias del piloto

* `data/reference/entidades_territoriales_piloto.csv`: las 5 entidades del piloto y qué
  municipios son distritos.
* `data/reference/alias_municipios_ideam.csv`: nombres del IDEAM que no coinciden con DIVIPOLA.
