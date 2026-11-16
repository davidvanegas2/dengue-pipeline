# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "altair>=5.4",
#     "duckdb>=1.4",
#     "marimo>=0.25.2",
#     "pdfplumber>=0.11",
#     "polars>=1.30",
#     "pyarrow>=18",
# ]
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="Taller · Del PDF a la tabla oro")

with app.setup:
    import io
    import json
    import os
    import re
    import urllib.parse
    import urllib.request
    from datetime import date, timedelta
    from pathlib import Path

    import altair as alt
    import duckdb
    import marimo as mo
    import pdfplumber
    import polars as pl

    # When this notebook runs outside the repository (for example, in molab),
    # download data from GitHub. Update this URL if you use a fork or another branch.
    REPO_URL = "https://raw.githubusercontent.com/davidvanegas2/dengue-pipeline/main"


@app.function
def plot_signal(data: pl.DataFrame, cases: str, rainfall: str, title: str) -> alt.VConcatChart:
    """Plot weekly cases above weekly rainfall for one territorial entity."""
    _base = alt.Chart(data).encode(x=alt.X("week_start:T", title=None))
    _cases = _base.mark_line(color="#d1495b").encode(
        y=alt.Y(f"{cases}:Q", title="Casos por semana")
    )
    _rainfall = _base.mark_bar(color="#2e86ab", opacity=0.75).encode(
        y=alt.Y(f"{rainfall}:Q", title="Lluvia semanal (mm)")
    )
    return alt.vconcat(
        _cases.properties(title=title, width=640, height=170),
        _rainfall.properties(width=640, height=110),
    )


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # 🦟 Del PDF a la tabla oro
    ### Taller de ingeniería de datos · Hackathon Loka × WIE ICESI 2026

    *Cada semana, una secretaría de salud en algún lugar de Colombia abre un PDF y
    descubre que el dengue ya llegó.* Hoy vamos a construir la tubería que convierte
    tres fuentes dispersas en **una sola tabla** lista para gráficas y modelos.

    | Símbolo | Significa |
    |---|---|
    | ✏️ **TODO** | Te toca escribir código (poquito, lo prometo) |
    | ✅ **Checkpoint** | Una verificación automática: verde = vas bien |
    | 🔍 **Trampa** | Un problema real de los datos que vamos a cazar |
    | 🤔 **Predice** | Adivina antes de correr |

    **¿Primera vez en marimo?** Es un notebook *reactivo*: cuando cambias una celda,
    todas las que dependen de ella se vuelven a ejecutar solas. No hay "estado
    escondido" ni que correr las celdas en orden. Ejecuta una celda con `Ctrl/⌘ + Enter`.
    """)
    return


@app.cell(hide_code=True)
def _():
    FILES = {
        "bulletin_26": "data/raw/boletines/extracto_bes_2026_s26.pdf",
        "bulletin_27": "data/raw/boletines/extracto_bes_2026_s27.pdf",
        "sivigila": "data/raw/sivigila/sivigila_dengue_piloto.csv",
        "sivigila_origin": "data/raw/sivigila/ORIGEN.txt",
        "ideam": "data/raw/ideam/precipitacion_diaria_piloto.parquet",
        "divipola": "data/reference/divipola_piloto.csv",
        "entities": "data/reference/entidades_territoriales_piloto.csv",
        "alias": "data/reference/alias_municipios_ideam.csv",
        "gold": "data/gold/weekly_dengue_signal.parquet",
    }
    # DENGUE_REPO_ROOT overrides the notebook's parent directory.
    _directory = mo.notebook_dir()
    _root = Path(
        os.environ.get("DENGUE_REPO_ROOT")
        or (_directory.parent if _directory is not None else Path.cwd())
    )
    _cache = Path.home() / ".cache" / "dengue-workshop"

    def path(key: str) -> Path:
        """Find a workshop file locally, downloading it when running outside the repository."""
        _relative = FILES[key]
        if (_root / _relative).is_file():
            return _root / _relative
        _destination = _cache / _relative
        if not _destination.is_file():
            _destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                urllib.request.urlretrieve(f"{REPO_URL}/{_relative}", _destination)
            except OSError as _error:
                raise RuntimeError(
                    f"Could not find or download {_relative}. When running outside the "
                    "repository, check REPO_URL at the top of the notebook."
                ) from _error
        return _destination

    SIVIGILA_ORIGIN = path("sivigila_origin").read_text(encoding="utf-8").split()[0]
    return SIVIGILA_ORIGIN, path


@app.cell(hide_code=True)
def _(SIVIGILA_ORIGIN):
    mo.callout(
        mo.md(
            "**Ojo:** los casos de SIVIGILA que trae este repositorio son una "
            "**muestra sintética** (mismo formato, números inventados). Sirve para "
            "aprender la técnica, pero cualquier patrón que veas en ellos es ruido."
        ),
        kind="warn",
    ) if SIVIGILA_ORIGIN == "SINTETICO" else mo.md("")
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 1 · Empieza por el final

    Esta es la tabla que vas a construir en los próximos 45 minutos: **una fila por
    entidad territorial y semana epidemiológica**, con casos de dengue y lluvia.
    Es la que usará el taller de ML.
    """)
    return


@app.cell
def _(path):
    final_gold = pl.read_parquet(path("gold"))
    selected_entity = mo.ui.dropdown(
        sorted(final_gold["territorial_entity"].unique().to_list()),
        value="Santiago de Cali",
        label="Entidad territorial",
    )
    return selected_entity, final_gold


@app.cell
def _(selected_entity, final_gold):
    mo.vstack(
        [
            selected_entity,
            plot_signal(
                final_gold.filter(pl.col("territorial_entity") == selected_entity.value),
                cases="sivigila_cases",
                rainfall="mean_precipitation_mm",
                title=f"{selected_entity.value}: casos y lluvia por semana epidemiológica",
            ),
            final_gold.head(8),
        ]
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 2 · El mapa

    Tres fuentes, tres formatos, tres granularidades. La técnica para no perderse
    es la **arquitectura medallón**: como en una cocina.

    * **Bronce** = el mercado. Los datos tal como llegan, sin tocar.
    * **Plata** = la *mise en place*. Limpios, con tipos correctos y llaves comunes.
    * **Oro** = el plato servido. Listos para comer (graficar o entrenar).
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.mermaid(
        """
        flowchart LR
          A["📄 Boletín INS<br/>PDF semanal"] --> B[("🥉 bronce")]
          S["🗂️ SIVIGILA<br/>casos individuales"] --> B
          I["🌧️ IDEAM<br/>API datos.gov.co"] --> B
          B -- "limpiar, tipos,<br/>códigos DANE" --> P[("🥈 plata")]
          P -- "cruzar por<br/>entidad × semana" --> O[("🥇 oro")]
          O --> G["📈 gráficas"]
          O --> M["🤖 taller de ML"]
        """
    )
    return


@app.cell
def _():
    # DuckDB is an analytical database stored in a file or in memory.
    # No server or credentials are needed: install it with pip install duckdb.
    con = duckdb.connect()
    for _schema in ("bronze", "silver", "gold"):
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {_schema}")
    return (con,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 3 · Fuente 1: el boletín en PDF (la difícil)

    El Instituto Nacional de Salud publica cada semana el *Boletín Epidemiológico
    Semanal*. Es la información **más reciente** que existe… y viene en PDF.

    🤔 **Antes de seguir:** ¿cómo sacarías esta tabla del PDF? (copiar y pegar,
    Excel, a mano…). Piensa en hacerlo **cada semana, para siempre**.
    """)
    return


@app.cell
def _(path, bulletin_week, bulletin_page):
    mo.pdf(src=path(bulletin_week.value), initial_page=bulletin_page, height="55vh")
    return


@app.cell
def _():
    bulletin_week = mo.ui.dropdown(
        {
            "Semana 26 (28 jun – 4 jul 2026)": "bulletin_26",
            "Semana 27 (5 – 11 jul 2026)": "bulletin_27",
        },
        value="Semana 26 (28 jun – 4 jul 2026)",
        label="Boletín",
    )
    bulletin_week
    return (bulletin_week,)


@app.cell
def _(path, bulletin_week):
    def find_table(pdf_path: Path):
        """Find the table by title because its page and number change every week."""
        _title = re.compile(r"Casos notificados de dengue por entidad territorial", re.I)
        _pdf = pdfplumber.open(pdf_path)
        for _number, _page in enumerate(_pdf.pages, start=1):
            _matches = _page.search(_title)
            if _matches:
                return _number, _page, _matches[0]
        raise ValueError(f"Could not find the dengue table in {pdf_path.name}")

    bulletin_page, page, title = find_table(path(bulletin_week.value))
    _side = "izquierdo" if title["x0"] < page.width / 2 else "derecho"
    mo.md(
        f"La tabla está en la **página {bulletin_page}** del PDF. Su título empieza en "
        f"x = {title['x0']:.0f} de {page.width:.0f} puntos → lado **{_side}**. "
        "Cambia de semana arriba y mira qué pasa. 🔍"
    )
    return bulletin_page, find_table, page, title


@app.cell
def _(page):
    # First attempt: extract the entire page text.
    mo.plain_text("\n".join(page.extract_text().splitlines()[5:22]))
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    🔍 **Trampa 1: la página tiene dos columnas** y `extract_text()` mezcla la tabla
    con el texto de al lado. Además los números vienen en formato colombiano:
    `9 504` (miles con espacio) y `30,3` (coma decimal).

    ### ✏️ TODO 1 · Convierte los números colombianos
    """)
    return


@app.cell
def _():
    def parse_integer(text: str) -> int | None:
        """'9 504' -> 9504. The bulletin uses spaces as thousands separators."""
        # >>> SOLUTION
        return int(text.replace(" ", "").replace(" ", ""))
        # <<< SOLUTION
        # >>> STUDENT
        # # ✏️ TODO 1a: remove spaces and convert to an integer with int()
        # return None
        # <<< STUDENT

    def parse_decimal(text: str) -> float | None:
        """'30,3' -> 30.3. The bulletin uses a decimal comma."""
        # >>> SOLUTION
        return float(text.replace(",", "."))
        # <<< SOLUTION
        # >>> STUDENT
        # # ✏️ TODO 1b: replace the comma with a dot and convert with float()
        # return None
        # <<< STUDENT

    return parse_decimal, parse_integer


@app.cell(hide_code=True)
def _(parse_decimal, parse_integer):
    _tests = [
        ("parse_integer('9 504')", lambda: parse_integer("9 504"), 9504),
        ("parse_integer('56 797')", lambda: parse_integer("56 797"), 56797),
        ("parse_integer('75')", lambda: parse_integer("75"), 75),
        ("parse_decimal('30,3')", lambda: parse_decimal("30,3"), 30.3),
        ("parse_decimal('0,9')", lambda: parse_decimal("0,9"), 0.9),
    ]
    _rows = []
    for _name, _call, _expected in _tests:
        try:
            _actual = _call()
        except Exception as _error:  # show any exception to the student
            _actual = f"error: {_error}"
        _rows.append(
            {
                "test": _name,
                "expected": str(_expected),
                "actual": str(_actual),
                "ok": _actual == _expected,
            }
        )
    todo1_ok = all(f["ok"] for f in _rows)
    mo.vstack(
        [
            mo.callout(
                mo.md(
                    "✅ **TODO 1 listo.**"
                    if todo1_ok
                    else "⏳ **TODO 1:** aún hay pruebas en rojo."
                ),
                kind="success" if todo1_ok else "neutral",
            ),
            pl.DataFrame(_rows),
        ]
    )
    return (todo1_ok,)


@app.cell
def _():
    def crop_table(page, title):
        """Keep the left or right page column containing the table."""
        _half = page.width / 2
        _x0, _x1 = (0, _half) if title["x0"] < _half else (_half, page.width)
        _bbox = (_x0, title["top"] - 2, _x1, page.height)
        # >>> SOLUTION
        return page.within_bbox(_bbox)
        # <<< SOLUTION
        # >>> STUDENT
        # # ✏️ TODO 2 (discover this at checkpoint 1)
        # return page.crop(_bbox)
        # <<< STUDENT

    return (crop_table,)


@app.cell
def _(parse_decimal, parse_integer):
    # Table row: entity, cases, warning-sign percentage, severe percentage and remainder.
    ROW = re.compile(
        r"^(?P<entity>[^\d]+?)\s+(?P<cases>\d{1,3}(?: \d{3})*)\s+"
        r"(?P<warning>\d+,\d)\s+(?P<severe>\d+,\d)(?P<remainder>(?:\s+[\d ]+)?)\s*$"
    )

    def read_rows(text: str) -> tuple[list[dict], list[str]]:
        """Parse table rows and return unrecognized lines for inspection."""
        _rows, _discarded = [], []
        for _line in text.splitlines():
            _m = ROW.match(_line.strip())
            if _m is None:
                _discarded.append(_line)
                continue
            _rows.append(
                {
                    "territorial_entity": _m["entity"].strip(),
                    "total_cases": parse_integer(_m["cases"]),
                    "warning_signs_pct": parse_decimal(_m["warning"]),
                    "severe_pct": parse_decimal(_m["severe"]),
                    # Expected/observed values can be split ("20 79"); leave this for the challenge.
                    "raw_variation": _m["remainder"].strip(),
                }
            )
            if _m["entity"].strip() == "Total":
                break
        return _rows, _discarded

    return (read_rows,)


@app.cell
def _(read_rows, page, crop_table, title):
    _text = crop_table(page, title).extract_text()
    _rows, discarded_lines = read_rows(_text)
    bulletin_table = pl.DataFrame(_rows)
    bulletin_table
    return discarded_lines, bulletin_table


@app.cell(hide_code=True)
def _(discarded_lines, bulletin_table):
    _ready = bulletin_table.height > 0 and bulletin_table["total_cases"].null_count() == 0
    if not _ready:
        checkpoint_1 = False
        _output = mo.callout(
            mo.md("⏳ **Checkpoint 1:** completa primero el TODO 1."), kind="neutral"
        )
    else:
        _is_total = pl.col("territorial_entity") == "Total"
        _total = bulletin_table.filter(_is_total)["total_cases"].sum()
        _total_sum = bulletin_table.filter(~_is_total)["total_cases"].sum()
        checkpoint_1 = bool(_total) and _total == _total_sum
        if checkpoint_1:
            _output = mo.callout(
                mo.md(
                    f"✅ **Checkpoint 1:** las {bulletin_table.height - 1} entidades suman "
                    f"**{_total_sum:,}** casos, igual que la fila *Total* del boletín. "
                    "Validar contra el propio documento es la mejor prueba que existe."
                ),
                kind="success",
            )
        else:
            _broken = "\n".join(_l for _l in discarded_lines if re.search(r"\d+,\d", _l))
            _output = mo.callout(
                mo.md(
                    f"❌ **Checkpoint 1:** las entidades suman **{_total_sum:,}**, pero el "
                    f"boletín dice **{_total:,}**. Faltan **{_total - _total_sum:,} casos**.\n\n"
                    f"Estas líneas tienen números pero no se pudieron leer:\n\n```\n{_broken}\n```\n\n"
                    "✏️ **TODO 2:** mira el final de cada línea. ¿De dónde salió esa "
                    "letra? Arregla `crop_table` (abre la ayuda de abajo si te atascas)."
                ),
                kind="danger",
            )
    _output
    return (checkpoint_1,)


@app.cell(hide_code=True)
def _():
    mo.accordion(
        {
            "💡 Ayuda para el TODO 2": mo.md(
                "pdfplumber tiene dos formas de recortar una página:\n\n"
                "* `page.crop(bbox)` conserva los caracteres que **tocan** la caja.\n"
                "* `page.within_bbox(bbox)` conserva solo los que están **completamente adentro**.\n\n"
                "Las primeras letras de la otra columna tocan el borde… Prueba también "
                "con la semana 27: ¿por qué allí sí funcionaba?"
            )
        }
    )
    return


@app.cell
def _(find_table, checkpoint_1, con, read_rows, crop_table, path):
    mo.stop(
        not checkpoint_1,
        mo.md("⏳ *Cuando pases el checkpoint 1, aquí cargamos los dos boletines a la bodega.*"),
    )
    _tables = []
    for _key in ("bulletin_26", "bulletin_27"):
        _, _page, _title = find_table(path(_key))
        _text = crop_table(_page, _title).extract_text()
        _week = int(re.search(r"semana epidemiol[oó]gica (\d+) de \d{4}", _text).group(1))
        _rows, _ = read_rows(_text)
        _tables.append(
            pl.DataFrame(_rows).with_columns(
                epi_year=pl.lit(2026), epi_week=pl.lit(_week), filename=pl.lit(_key)
            )
        )
    bulletins_df = pl.concat(_tables)
    # Register the DataFrame as a view, then copy it to a warehouse table.
    con.register("bulletins_df", bulletins_df)
    con.execute("CREATE OR REPLACE TABLE bronze.bulletin AS SELECT * FROM bulletins_df")
    bronze_bulletin = con.sql(
        """
        SELECT epi_week, count(*) AS rows,
               max(total_cases) FILTER (WHERE territorial_entity = 'Total') AS national_total
        FROM bronze.bulletin GROUP BY ALL ORDER BY epi_week
        """
    ).pl()
    bronze_bulletin
    return (bronze_bulletin,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 4 · Fuente 2: SIVIGILA (ya preparada)

    Los **microdatos** de SIVIGILA traen un registro por caso notificado desde 2007
    (solo años cerrados). Se descargan a mano desde el portal del INS; aquí ya
    tenemos el archivo del piloto (Valle del Cauca y Atlántico).

    Cargarlo a la bodega es **una línea de SQL**. Fíjate en `all_varchar = true`:
    en la capa bronce **todo se lee como texto**. ¿Por qué? Ya lo verás.
    """)
    return


@app.cell
def _(con, path):
    con.execute(
        "CREATE OR REPLACE TABLE bronze.sivigila AS SELECT * FROM read_csv(?, all_varchar = true)",
        [str(path("sivigila"))],
    )
    con.execute(
        "CREATE OR REPLACE TABLE bronze.divipola AS SELECT * FROM read_csv(?, all_varchar = true)",
        [str(path("divipola"))],
    )
    bronze_sivigila = con.sql(
        """
        SELECT municipio_ocurrencia, cod_dpto_o, cod_mun_o, fec_not, ini_sin, ano, semana, cod_eve
        FROM bronze.sivigila
        WHERE municipio_ocurrencia IN ('BARRANQUILLA', 'SANTIAGO DE CALI', 'PALMIRA')
        LIMIT 6
        """
    ).pl()
    bronze_sivigila
    return (bronze_sivigila,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    🔍 **Trampa 2: fechas que parecen fechas.** SIVIGILA guarda la fecha de notificación
    (`fec_not`) como **texto**, tal como la escribe Excel en español:
    `2/12/2024 12:00:00 a. m.`. Mira la tabla de arriba: ¿`2/12/2024` es el 2 de
    diciembre o el 12 de febrero? Compárala con `ini_sin` en la misma fila
    (`28/11/2024`): no existe el mes 28, así que el formato es **día/mes/año**.

    Con ese texto, `CAST(fec_not AS DATE)` lanza un error de conversión.
    `TRY_CAST(fec_not AS DATE)` devuelve `NULL` cuando no puede convertirlo: la consulta
    sigue ejecutándose, pero pierde la fecha.
    (Los códigos de municipio sí vienen completos, `08` y `001`, pero se pierden si
    alguien guarda el archivo desde Excel; por eso el código de abajo los rellena con
    `lpad` por seguridad.)

    ### ✏️ TODO 3 · Convierte `fec_not` en una fecha
    La fecha es lo que está **antes del primer espacio**. Pistas: `split_part(texto, ' ', 1)`
    para quedarte con esa parte y `try_strptime(texto, '%d/%m/%Y')` para leerla.

    La muestra sintética usa fechas ISO (`2024-12-02`), que `try_cast(... AS DATE)` ya
    entiende. Para aceptar ambos formatos, combina las conversiones con `coalesce`,
    que elige el primer resultado que no sea `NULL`.
    """)
    return


@app.cell
def _(bronze_sivigila, con):
    mo.stop(bronze_sivigila is None)
    con.execute(
        """
        CREATE OR REPLACE TABLE silver.cases AS
        SELECT
            cod_dpto_o AS original_department_code,
            -- The INS files already include leading zeros ('08', '001'). lpad is a safeguard
            -- for exports that lose them, for example after saving the file from Excel.
            lpad(cod_dpto_o, 2, '0') || lpad(cod_mun_o, 3, '0') AS municipality_code,
            -- >>> SOLUTION
            coalesce(
                CAST(try_strptime(split_part(trim(fec_not), ' ', 1), '%d/%m/%Y') AS DATE),
                try_cast(split_part(trim(fec_not), ' ', 1) AS DATE)
            ) AS notification_date,
            -- <<< SOLUTION
            -- >>> STUDENT
            -- try_cast(fec_not AS DATE) AS notification_date,  -- ✏️ TODO 3: INS dates become NULL. Why?
            -- <<< STUDENT
            CAST(ano AS INTEGER) AS epi_year,
            CAST(semana AS INTEGER) AS epi_week,
            cod_eve AS event_code,
            ajuste AS adjustment
        FROM bronze.sivigila
        """
    )
    cases_by_department = con.sql(
        """
        SELECT
            c.original_department_code,
            count(*) AS cases,
            count(d.cod_mpio) AS with_valid_municipality,
            round(100 * count(d.cod_mpio) / count(*), 1) AS matched_pct,
            count(c.notification_date) AS with_valid_date,
            round(100 * count(c.notification_date) / count(*), 1) AS date_pct
        FROM silver.cases AS c
        LEFT JOIN bronze.divipola AS d ON c.municipality_code = d.cod_mpio
        GROUP BY ALL ORDER BY 1
        """
    ).pl()
    cases_by_department
    return (cases_by_department,)


@app.cell(hide_code=True)
def _(cases_by_department):
    checkpoint_2 = bool(
        not cases_by_department.is_empty()
        and (cases_by_department["with_valid_municipality"] == cases_by_department["cases"]).all()
        and (cases_by_department["with_valid_date"] == cases_by_department["cases"]).all()
    )
    mo.callout(
        mo.md(
            "✅ **Checkpoint 2:** el 100 % de los casos tiene municipio y fecha de notificación."
            if checkpoint_2
            else "❌ **Checkpoint 2:** hay casos sin municipio o fecha de notificación. "
            "Revisa los conteos exactos de la tabla y el TODO 3: los porcentajes están redondeados."
        ),
        kind="success" if checkpoint_2 else "danger",
    )
    return (checkpoint_2,)


@app.cell
def _(checkpoint_2, con, path):
    mo.stop(not checkpoint_2, mo.md("⏳ *Pasa el checkpoint 2 para seguir.*"))
    con.execute(
        "CREATE OR REPLACE TABLE bronze.entities AS SELECT * FROM read_csv(?, all_varchar = true)",
        [str(path("entities"))],
    )
    con.execute(
        """
        -- INS reports districts separately from their department.
        CREATE OR REPLACE TABLE silver.municipality_entity AS
        SELECT d.cod_mpio AS municipality_code, coalesce(dist.entidad_territorial, dep.entidad_territorial) AS territorial_entity
        FROM bronze.divipola AS d
        LEFT JOIN bronze.entities AS dist ON d.cod_mpio = dist.cod_mpio
        LEFT JOIN bronze.entities AS dep ON d.cod_dpto = dep.cod_dpto AND dep.tipo = 'departamento';

        -- Pilot assumptions (see RETOS.md): dengue (210) and severe dengue (220),
        -- excluding discarded cases (6) and data-entry errors (D). The real INS downloads
        -- contain neither (adjustment is 0, 3, 5 or 7); keep the filter as a safeguard.
        CREATE OR REPLACE TABLE silver.weekly_cases AS
        SELECT me.territorial_entity, c.epi_year, c.epi_week, count(*) AS cases
        FROM silver.cases AS c
        JOIN silver.municipality_entity AS me ON c.municipality_code = me.municipality_code
        WHERE c.event_code IN ('210', '220') AND c.adjustment NOT IN ('6', 'D')
        GROUP BY ALL;
        """
    )
    weekly_cases_summary = con.sql(
        """
        PIVOT (SELECT territorial_entity, epi_year, cases FROM silver.weekly_cases)
        ON epi_year USING sum(cases) ORDER BY territorial_entity
        """
    ).pl()
    weekly_cases_summary
    return (weekly_cases_summary,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    🔍 **Trampa 3: "Valle del Cauca" no es todo el Valle.** El boletín reporta
    *Santiago de Cali* y *Buenaventura* como entidades aparte. Si sumas mal, cuentas
    a Cali dos veces (o ninguna). Por eso la llave común no es el departamento sino
    la **entidad territorial**.

    ## 5 · Fuente 3: IDEAM (lluvia) por API

    El conjunto de precipitación del IDEAM en datos.gov.co tiene **más de 165 millones
    de filas** (una lectura cada 10 minutos por estación). No lo descargues: pídele a
    la API que **sume por día** del lado del servidor. Así se ve una consulta SoQL:
    """)
    return


@app.cell
def _():
    api_button = mo.ui.run_button(
        label="🌧️ Consultar la API del IDEAM en vivo (Valle, últimos 7 días)"
    )
    api_button
    return (api_button,)


@app.cell
def _(api_button):
    mo.stop(
        not api_button.value,
        mo.md(
            "*Pulsa el botón. Si el internet falla, no pasa nada: seguimos con la copia guardada.*"
        ),
    )
    _start_date = date.today() - timedelta(days=7)
    _params = {
        "$select": "municipio, date_trunc_ymd(fechaobservacion) AS fecha, "
        "sum(valorobservado) AS mm, count(*) AS lecturas",
        "$where": f"fechaobservacion >= '{_start_date.isoformat()}T00:00:00' "
        "AND departamento in ('VALLE DEL CAUCA', 'Valle Del Cauca')",
        "$group": "municipio, fecha",
        "$order": "fecha DESC, mm DESC",
        "$limit": "200",
    }
    _url = "https://www.datos.gov.co/resource/s54a-sgyg.json?" + urllib.parse.urlencode(_params)
    try:
        with urllib.request.urlopen(_url, timeout=60) as _response:
            _output = pl.DataFrame(json.load(_response))
    except Exception as _error:  # workshop Wi-Fi can fail
        _output = mo.callout(
            mo.md(f"No se pudo consultar la API (`{_error}`). Seguimos con la copia guardada."),
            kind="warn",
        )
    mo.vstack([mo.md(f"`GET {_url[:160]}…`"), _output])
    return


@app.cell
def _(con, path):
    con.execute(
        "CREATE OR REPLACE TABLE bronze.ideam AS SELECT * FROM read_parquet(?)",
        [str(path("ideam"))],
    )
    con.execute(
        "CREATE OR REPLACE TABLE bronze.alias AS SELECT * FROM read_csv(?, all_varchar = true)",
        [str(path("alias"))],
    )
    ideam_names = con.sql(
        """
        SELECT departamento AS department, count(*) AS station_days,
               min(fecha)[:10] AS start_date, max(fecha)[:10] AS end_date
        FROM bronze.ideam GROUP BY ALL ORDER BY start_date
        """
    ).pl()
    ideam_names
    return (ideam_names,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    🔍 **Trampa 4: el mismo departamento, escrito de dos formas.** En 2026 el IDEAM
    cambió `VALLE DEL CAUCA` por `Valle Del Cauca`. Para cruzar nombres hay que
    **normalizarlos** (mayúsculas, sin tildes). Y el IDEAM no trae código DIVIPOLA:
    hay que emparejar **por nombre** de departamento + municipio. ¿Por qué no solo
    municipio? Porque *Candelaria* existe en el Valle y en el Atlántico.
    """)
    return


@app.cell
def _(con, ideam_names):
    mo.stop(ideam_names is None)
    # Macros are reusable SQL functions.
    con.execute(
        """
        CREATE OR REPLACE MACRO normalize(text) AS
            trim(regexp_replace(upper(strip_accents(text)), '[^A-Z0-9 ]', ' ', 'g'));
        -- Epidemiological weeks run Sunday through Saturday, unlike ISO weeks.
        CREATE OR REPLACE MACRO epi_week_start(observation_date) AS
            CAST(observation_date AS DATE) - CAST(dayofweek(CAST(observation_date AS DATE)) AS INTEGER);
        CREATE OR REPLACE MACRO epi_year(observation_date) AS year(epi_week_start(observation_date) + 3);
        CREATE OR REPLACE MACRO epi_week(observation_date) AS
            1 + datediff('day', epi_week_start(make_date(epi_year(observation_date), 1, 4)),
                         epi_week_start(observation_date)) // 7;
        """
    )
    macros_ready = True
    use_aliases = mo.ui.switch(label="Usar la tabla de alias (CALI → SANTIAGO DE CALI)")
    return macros_ready, use_aliases


@app.cell
def _(con, macros_ready, use_aliases):
    mo.stop(not macros_ready)
    _use_aliases = "TRUE" if use_aliases.value else "FALSE"
    con.execute(
        f"""
        CREATE OR REPLACE TABLE silver.daily_rainfall AS
        WITH base AS (
            SELECT codigoestacion AS station_code,
                   normalize(departamento) AS department,
                   normalize(municipio) AS municipality,
                   CAST(fecha[:10] AS DATE) AS observation_date,
                   CAST(precipitacion_mm AS DOUBLE) AS precipitation_mm,
                   CAST(n_lecturas AS INTEGER) AS reading_count
            FROM bronze.ideam
        )
        SELECT b.*, d.cod_mpio AS municipality_code
        FROM base AS b
        LEFT JOIN bronze.alias AS a
            ON {_use_aliases}
            AND b.department = normalize(a.departamento)
            AND b.municipality = normalize(a.municipio_ideam)
        LEFT JOIN bronze.divipola AS d
            ON b.department = normalize(d.dpto)
            AND coalesce(normalize(a.municipio_divipola), b.municipality) = normalize(d.nom_mpio)
        """
    )
    missing_municipalities = con.sql(
        """
        SELECT department, municipality, count(DISTINCT station_code) AS stations, count(*) AS days
        FROM silver.daily_rainfall WHERE municipality_code IS NULL GROUP BY ALL ORDER BY days DESC
        """
    ).pl()
    mo.vstack(
        [
            use_aliases,
            mo.callout(mo.md("✅ Todas las estaciones encontraron su municipio."), kind="success")
            if missing_municipalities.is_empty()
            else mo.vstack(
                [
                    mo.callout(
                        mo.md(
                            "🔍 **¿Dónde está Cali?** El IDEAM dice `CALI`; el DANE dice "
                            "`SANTIAGO DE CALI`. Activa la tabla de alias y mira cómo todo "
                            "lo que depende de esta celda se recalcula solo."
                        ),
                        kind="warn",
                    ),
                    missing_municipalities,
                ]
            ),
        ]
    )
    return (missing_municipalities,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 6 · Transformar y cruzar

    Ya tenemos casos **por semana** y lluvia **por día**. Para cruzarlos necesitamos
    la misma granularidad. Primero, 🔍 **trampa 5**: la semana epidemiológica no es la
    semana ISO que trae `week()`. Mira la misma semana con ambas reglas:
    """)
    return


@app.cell
def _(con, macros_ready):
    mo.stop(not macros_ready)
    con.sql(
        """
        SELECT CAST(d AS DATE) AS observation_date, dayname(d) AS day,
               week(d) AS iso_week, epi_week(d) AS epidemiological_week
        FROM unnest(generate_series(TIMESTAMP '2026-06-27', TIMESTAMP '2026-07-05', INTERVAL 1 DAY)) AS t(d)
        """
    ).pl()
    return


@app.cell
def _(weekly_cases_summary, con, missing_municipalities):
    mo.stop(weekly_cases_summary is None or missing_municipalities is None)
    con.execute(
        """
        CREATE OR REPLACE TABLE silver.entity_daily_rainfall AS
        SELECT me.territorial_entity, l.*
        FROM silver.daily_rainfall AS l
        JOIN silver.municipality_entity AS me ON l.municipality_code = me.municipality_code
        """
    )
    entity_rainfall_ready = True
    return (entity_rainfall_ready,)


@app.cell
def _(con, entity_rainfall_ready):
    mo.stop(not entity_rainfall_ready)
    prediction = mo.ui.number(
        start=0, stop=10_000_000, step=1, value=0, label="Mi predicción (filas)"
    )
    reveal = mo.ui.run_button(label="Revelar")
    _case_rows = con.sql("SELECT count(*) FROM silver.weekly_cases").fetchall()[0][0]
    mo.vstack(
        [
            mo.md(
                f"🤔 **Predice:** `silver.weekly_cases` tiene **{_case_rows:,} filas** "
                "(una por entidad y semana). Si la cruzamos *directamente* con la lluvia "
                "**diaria** por entidad y semana, ¿cuántas filas tendrá el resultado?"
            ),
            mo.hstack([prediction, reveal], justify="start"),
        ]
    )
    return prediction, reveal


@app.cell
def _(con, prediction, reveal):
    mo.stop(not reveal.value, mo.md("*Escribe tu predicción y pulsa **Revelar**.*"))
    _rows, _inflated_cases = con.sql(
        """
        SELECT count(*), sum(c.cases)
        FROM silver.weekly_cases AS c
        JOIN silver.entity_daily_rainfall AS l
          ON c.territorial_entity = l.territorial_entity
         AND c.epi_year = epi_year(l.observation_date) AND c.epi_week = epi_week(l.observation_date)
        """
    ).fetchall()[0]
    _actual_cases = con.sql("SELECT sum(cases) FROM silver.weekly_cases").fetchall()[0][0]
    mo.callout(
        mo.md(
            f"El cruce tiene **{_rows:,} filas** (tu predicción: {prediction.value:,}).\n\n"
            f"Y si sumamos los casos: **{_inflated_cases:,}** en vez de **{_actual_cases:,}**. "
            "Cada semana de casos se repitió una vez por cada día y por cada estación: "
            "**una explosión de filas**. Cruza siempre tablas con la **misma granularidad**."
        ),
        kind="danger",
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### ✏️ TODO 4 · Lleva la lluvia a una fila por entidad y semana
    Completa la consulta para que `silver.weekly_rainfall` tenga **una sola fila** por
    `territorial_entity`, `epi_year` y `epi_week`.
    """)
    return


@app.cell
def _(con, entity_rainfall_ready):
    mo.stop(not entity_rainfall_ready)
    con.execute(
        """
        CREATE OR REPLACE TABLE silver.weekly_rainfall AS
        -- >>> SOLUTION
        WITH per_station AS (
            -- First, total weekly rainfall for each station...
            SELECT territorial_entity, station_code,
                   epi_year(observation_date) AS epi_year, epi_week(observation_date) AS epi_week,
                   sum(precipitation_mm) AS mm
            FROM silver.entity_daily_rainfall
            GROUP BY ALL
        )
        -- ...then average the stations within each territorial entity.
        SELECT territorial_entity, epi_year, epi_week,
               round(avg(mm), 1) AS rainfall_mm, count(*) AS stations
        FROM per_station
        GROUP BY ALL
        -- <<< SOLUTION
        -- >>> STUDENT
        -- -- ✏️ TODO 4: this returns one row per DAY and station. Aggregate by week.
        -- SELECT territorial_entity,
        --        epi_year(observation_date) AS epi_year, epi_week(observation_date) AS epi_week,
        --        precipitation_mm AS rainfall_mm,
        --        1 AS stations
        -- FROM silver.entity_daily_rainfall
        -- <<< STUDENT
        """
    )
    weekly_rainfall_ready = True
    return (weekly_rainfall_ready,)


@app.cell(hide_code=True)
def _():
    mo.accordion(
        {
            "💡 Ayuda para el TODO 4": mo.md(
                "Usa una función de agregación (`sum`, `avg`) sobre `precipitation_mm` y "
                "`GROUP BY` las columnas de la llave. Una versión válida:\n\n"
                "```sql\nSELECT territorial_entity, epi_year(observation_date) AS epi_year,\n"
                "       epi_week(observation_date) AS epi_week,\n"
                "       avg(precipitation_mm) AS rainfall_mm,\n"
                "       count(DISTINCT station_code) AS stations\n"
                "FROM silver.entity_daily_rainfall\nGROUP BY ALL\n```\n\n"
                "¿Es lo mismo promediar días que sumar la semana por estación y luego "
                "promediar estaciones? Discútanlo."
            )
        }
    )
    return


@app.cell
def _(bronze_bulletin, con, weekly_rainfall_ready):
    mo.stop(not weekly_rainfall_ready or bronze_bulletin is None)
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.signal AS
        -- Include every week in the period, even without source observations.
        WITH weeks AS (
            SELECT DISTINCT epi_year(d) AS epi_year, epi_week(d) AS epi_week
            FROM unnest(generate_series(
                TIMESTAMP '2024-01-01',
                (SELECT max(observation_date) FROM silver.daily_rainfall)::TIMESTAMP,
                INTERVAL 1 DAY
            )) AS t(d)
        ),
        -- The spine includes every entity-week combination, with or without data.
        spine AS (
            SELECT e.entidad_territorial AS territorial_entity, s.epi_year, s.epi_week
            FROM bronze.entities AS e CROSS JOIN weeks AS s
        )
        SELECT
            es.territorial_entity, es.epi_year, es.epi_week,
            make_date(es.epi_year, 1, 4) - CAST(dayofweek(make_date(es.epi_year, 1, 4)) AS INTEGER)
                + CAST(7 * (es.epi_week - 1) AS INTEGER) AS week_start,
            CASE WHEN es.epi_year IN (SELECT epi_year FROM silver.cases) THEN coalesce(c.cases, 0) END
                AS sivigila_cases,
            b.total_cases AS bulletin_cumulative_cases,
            l.rainfall_mm,
            l.stations
        FROM spine AS es
        LEFT JOIN silver.weekly_cases AS c
            ON es.territorial_entity = c.territorial_entity
            AND es.epi_year = c.epi_year AND es.epi_week = c.epi_week
        LEFT JOIN silver.weekly_rainfall AS l
            ON es.territorial_entity = l.territorial_entity
            AND es.epi_year = l.epi_year AND es.epi_week = l.epi_week
        LEFT JOIN bronze.bulletin AS b
            ON es.territorial_entity = b.territorial_entity
            AND es.epi_year = b.epi_year AND es.epi_week = b.epi_week
        ORDER BY ALL
        """
    )
    gold = con.sql("SELECT * FROM gold.signal").pl()
    gold
    return (gold,)


@app.cell(hide_code=True)
def _(gold):
    _keys = ["territorial_entity", "epi_year", "epi_week"]
    _duplicates = gold.height - gold.select(_keys).n_unique()
    _weeks = gold.select("epi_year", "epi_week").n_unique()
    _entities = gold["territorial_entity"].n_unique()
    checkpoint_3 = _duplicates == 0 and gold.height == _weeks * _entities
    mo.callout(
        mo.md(
            f"✅ **Checkpoint 3:** {gold.height:,} filas = {_entities} entidades × "
            f"{_weeks} semanas, sin llaves repetidas. **¡Tienes tu tabla oro!** 🥇"
            if checkpoint_3
            else f"❌ **Checkpoint 3:** hay **{_duplicates:,} filas repetidas** "
            "(misma entidad y semana). ¿Agrupaste la lluvia por semana en el TODO 4?"
        ),
        kind="success" if checkpoint_3 else "danger",
    )
    return (checkpoint_3,)


@app.cell
def _(checkpoint_3, gold, final_gold, path):
    mo.stop(not checkpoint_3)
    _mine = gold.group_by("territorial_entity").agg(student_cases=pl.col("sivigila_cases").sum())
    _repo = final_gold.group_by("territorial_entity").agg(repo_cases=pl.col("sivigila_cases").sum())
    _comparison = _mine.join(_repo, on="territorial_entity").sort("territorial_entity")
    _equal = (_comparison["student_cases"] == _comparison["repo_cases"]).all()
    _filename = io.BytesIO()
    gold.write_parquet(_filename)
    ml_export = path("gold").read_bytes()
    mo.vstack(
        [
            mo.md(
                "**¿Coinciden los conteos de casos con la tabla del inicio?** "
                + ("Sí ✅" if _equal else "No del todo 🤔")
            ),
            _comparison,
            mo.download(
                data=_filename.getvalue(),
                filename="mi_weekly_dengue_signal.parquet",
                label="⬇️ Descargar mi tabla del ejercicio",
            ),
            mo.md(
                "**Para el taller de ML, usa la tabla oficial de abajo.** La tabla del "
                "ejercicio tiene menos columnas y su lluvia depende de tu solución al "
                "TODO 4. La oficial conserva las 13 columnas del diccionario de datos "
                "y suma la lluvia semanal por estación antes de promediar estaciones."
            ),
            mo.download(
                data=ml_export,
                filename="weekly_dengue_signal.parquet",
                label="⬇️ Descargar tabla oficial para ML",
            ),
        ]
    )
    return (ml_export,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 7 · Lo que no cuadra 🕵️

    Tu tabla funciona… para el piloto. Pero los datos reales esconden preguntas que
    **nadie ha resuelto todavía**. Estas son algunas; el resto está en `RETOS.md`.
    """)
    return


@app.cell
def _(bronze_bulletin, con):
    mo.stop(bronze_bulletin is None)
    _changes = con.sql(
        """
        SELECT s26.territorial_entity,
               s26.total_cases AS week_26_cumulative,
               s27.total_cases AS week_27_cumulative,
               s27.total_cases - s26.total_cases AS difference
        FROM bronze.bulletin AS s26
        JOIN bronze.bulletin AS s27
          ON lower(s26.territorial_entity) = lower(s27.territorial_entity)
         AND s26.epi_week = 26 AND s27.epi_week = 27
        ORDER BY difference
        """
    ).pl()
    _total = _changes.filter(pl.col("territorial_entity") == "Total")
    _t26, _t27 = _total["week_26_cumulative"][0], _total["week_27_cumulative"][0]
    mo.vstack(
        [
            mo.md(
                f"""
                ### 🕵️ Incógnita 1: el pasado cambia
                El boletín de la semana 27 dice: *"se notificaron **2 847** casos de dengue:
                2 118 de esta semana y 729 de semanas anteriores"*. Pero el acumulado pasó
                de **{_t26:,}** a **{_t27:,}**: solo **{_t27 - _t26:,}** más.
                **¿Dónde están los {2847 - (_t27 - _t26):,} casos que faltan?** Y mira las
                entidades donde el acumulado **bajó**:
                """
            ),
            _changes.filter(pl.col("difference") < 0),
        ]
    )
    return


@app.cell
def _(checkpoint_3, gold):
    mo.stop(not checkpoint_3)
    _cali = gold.filter(pl.col("territorial_entity") == "Santiago de Cali").with_columns(
        pl.col("week_start").cast(pl.Date)
    )
    _weekly = (
        alt.Chart(_cali)
        .mark_line(color="#d1495b")
        .encode(x=alt.X("week_start:T", title=None), y=alt.Y("sivigila_cases:Q", title="Casos"))
    )
    _cumulative = (
        alt.Chart(_cali.filter(pl.col("bulletin_cumulative_cases").is_not_null()))
        .mark_point(color="#000", size=80, filled=True)
        .encode(x="week_start:T", y="bulletin_cumulative_cases:Q")
    )
    mo.vstack(
        [
            mo.md(
                "### 🕵️ Incógnita 2: la costura\nLa línea son casos **por semana** "
                "(SIVIGILA, hasta 2025). Los puntos negros son casos **acumulados** del "
                "boletín (2026). ¿Cómo los pones en la misma escala? ¿Y qué pasa con las "
                "demás semanas de 2026?"
            ),
            (_weekly + _cumulative).properties(width=640, height=220),
        ]
    )
    return


@app.cell
def _(con, missing_municipalities):
    mo.stop(missing_municipalities is None)
    _unusual = con.sql(
        """
        SELECT observation_date, department, municipality, station_code, precipitation_mm, reading_count
        FROM silver.daily_rainfall
        ORDER BY precipitation_mm DESC LIMIT 6
        """
    ).pl()
    mo.vstack(
        [
            mo.md(
                "### 🕵️ Incógnita 3: ¿825 mm en un día?\nUna estación normal reporta "
                "144 lecturas al día (una cada 10 minutos). ¿Es real esta lluvia? ¿Qué "
                "harías con esos días: borrarlos, corregirlos, marcarlos?"
            ),
            _unusual,
        ]
    )
    return


@app.cell
def _():
    lag = mo.ui.slider(0, 12, value=0, step=1, show_value=True, label="Rezago (semanas)")
    return (lag,)


@app.cell
def _(checkpoint_3, gold, lag):
    mo.stop(not checkpoint_3)
    _with_lag = (
        gold.sort("territorial_entity", "epi_year", "epi_week")
        .with_columns(
            earlier_rainfall=pl.col("rainfall_mm").shift(lag.value).over("territorial_entity")
        )
        .filter(pl.col("sivigila_cases").is_not_null())
    )
    _correlation = (
        _with_lag.group_by("territorial_entity")
        .agg(correlation=pl.corr("earlier_rainfall", "sivigila_cases").round(2))
        .sort("territorial_entity")
    )
    mo.vstack(
        [
            mo.md(
                "### 🕵️ Incógnita 4: ¿lluvia de cuándo?\nEl mosquito necesita agua para "
                "reproducirse, pero no de un día para otro. Mueve el rezago: ¿con cuántas "
                f"semanas de diferencia se parecen más la lluvia y los casos? *(Rezago = "
                f"{lag.value} semanas.)* Esta pregunta es el puente al taller de ML."
            ),
            lag,
            _correlation,
        ]
    )
    return


@app.cell(hide_code=True)
def _(checkpoint_1, checkpoint_2, checkpoint_3, todo1_ok):
    _status = [
        {"step": "TODO 1 · números colombianos", "ok": todo1_ok},
        {"step": "Checkpoint 1 · el PDF cuadra (TODO 2)", "ok": checkpoint_1},
        {"step": "Checkpoint 2 · fechas de notificación (TODO 3)", "ok": checkpoint_2},
        {"step": "Checkpoint 3 · tabla oro (TODO 4)", "ok": checkpoint_3},
    ]
    mo.md(
        "## 8 · Resumen\n\n"
        + "\n".join(f"* {'✅' if e['ok'] else '⏳'} {e['step']}" for e in _status)
        + "\n\n**¿Y ahora?** En la hackathon vas a escalar este piloto: todos los "
        "departamentos, todos los boletines, más variables de clima, y responder las "
        "incógnitas. Empieza por `RETOS.md` y por `uv run dengue-pipeline --help`."
    )
    return


if __name__ == "__main__":
    app.run()
