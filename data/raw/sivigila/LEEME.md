# SIVIGILA: cómo usar datos reales

`sivigila_dengue_piloto.csv` es el archivo que lee el pipeline. `ORIGEN.txt` dice de
dónde salió:

* `SINTETICO`: muestra generada por `scripts/generate_sivigila_sample.py`. Mismo formato
  que los microdatos reales, **números inventados**.
* `INS`: preparado con `dengue-pipeline prepare-sivigila` a partir de descargas reales.

## Reemplazar la muestra por datos reales

1. Entra al portal de SIVIGILA del INS (<https://portalsivigila.ins.gov.co/>) y busca el
   **Buscador de microdatos**.
2. Selecciona el evento (por ejemplo **DENGUE**, y si quieres **DENGUE GRAVE**), el año
   (2024, 2025…) y pulsa **Buscar**. Descarga el archivo de cada año.
3. Guarda las descargas en `data/raw/sivigila/descargas/` (esa carpeta está en
   `.gitignore`: los archivos nacionales son pesados).
4. Filtra al piloto y regenera la tabla oro:

   ```bash
   uv run dengue-pipeline prepare-sivigila data/raw/sivigila/descargas/*.xlsx
   uv run dengue-pipeline run
   ```

5. Versiona `sivigila_dengue_piloto.csv`, `ORIGEN.txt` y
   `data/gold/weekly_dengue_signal.parquet` (el notebook muestra esa tabla al inicio).

`prepare-sivigila` acepta `.xlsx`, `.xls`, `.csv` y `.parquet`, ignora mayúsculas en
los nombres de columna y exige al menos `cod_eve`, `semana`, `ano`, `cod_dpto_o` y
`cod_mun_o`.

> Los pasos del portal pueden cambiar. Si algo no coincide, el objetivo es el mismo:
> un archivo con un registro por caso y las columnas de arriba.
