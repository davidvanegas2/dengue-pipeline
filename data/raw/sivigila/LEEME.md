# SIVIGILA: cómo usar datos reales

`sivigila_dengue_piloto.csv` es el archivo que lee el pipeline. `ORIGEN.txt` dice de
dónde salió:

* `SINTETICO`: muestra generada por `scripts/generate_sivigila_sample.py`. Mismas columnas
  que los microdatos reales (pero con códigos sin ceros y fechas ISO), **números
  inventados**.
* `INS`: preparado con `dengue-pipeline prepare-sivigila` a partir de descargas reales.

## Reemplazar la muestra por datos reales

1. Entra al portal de SIVIGILA del INS (<https://portalsivigila.ins.gov.co/>) y busca el
   **Buscador de microdatos**.
2. Selecciona el evento y el año y pulsa **Buscar**. El pipeline cuenta **DENGUE (210)** y
   **DENGUE GRAVE (220)**, y el piloto va de **2024** a **2025** (2026 aún no es un año
   cerrado): descarga esos 4 archivos (evento × año). Verifica que el de 2025 llegue
   hasta la semana 53.
3. Guarda las descargas en `data/raw/sivigila/descargas/` (esa carpeta está en
   `.gitignore`: los archivos nacionales son pesados).
4. Filtra al piloto y regenera la tabla oro:

   ```bash
   uv run dengue-pipeline prepare-sivigila data/raw/sivigila/descargas/*.xlsx
   uv run dengue-pipeline run
   ```

5. Versiona `sivigila_dengue_piloto.csv`, `ORIGEN.txt` y
   `data/gold/weekly_dengue_signal.parquet` (el notebook muestra esa tabla al inicio).

Los archivos reales traen las fechas como texto (`2/12/2024 12:00:00 a. m.`); el pipeline
las convierte en la capa plata.

`prepare-sivigila` acepta `.xlsx`, `.xls`, `.csv` y `.parquet`, ignora mayúsculas en
los nombres de columna y exige al menos `cod_eve`, `semana`, `ano`, `cod_dpto_o` y
`cod_mun_o`.

> Los pasos del portal pueden cambiar. Si algo no coincide, el objetivo es el mismo:
> un archivo con un registro por caso y las columnas de arriba.
