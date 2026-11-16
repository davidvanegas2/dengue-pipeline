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

with app.setup(hide_code=True):
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


@app.function(hide_code=True)
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
    | ✏️ **TODO** | Uno de los dos ejercicios guiados: fechas y agregación |
    | ✅ **Checkpoint** | Una verificación automática; lee qué está comprobando |
    | 👀 **Demostración** | Observa, predice y comenta; el código ya está preparado |
    | 🔍 **Trampa** | Un problema real de los datos que vamos a cazar |
    | 🤔 **Predice** | Adivina antes de correr |

    **¿Primera vez en marimo?** Es un notebook *reactivo*: cuando cambias una celda,
    todas las que dependen de ella se vuelven a ejecutar solas. No hay "estado
    escondido" ni que correr las celdas en orden. Ejecuta una celda con `Ctrl/⌘ + Enter`.

    Trabajen en **parejas**. Solo necesitan editar las celdas de los **TODOs 1 y 2**;
    el código de apoyo se puede desplegar para consultarlo. Cada ejercicio tiene una
    pista y una **solución para continuar** si se atascan. La tabla oficial para ML
    está disponible desde el comienzo, aunque no terminen los ejercicios.
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
    _refreshed: set[str] = set()

    def path(key: str) -> Path:
        """Find a workshop file locally, downloading it when running outside the repository."""
        _relative = FILES[key]
        if (_root / _relative).is_file():
            return _root / _relative
        _destination = _cache / _relative
        if _relative not in _refreshed:
            # Download once per session so the cache never serves an old version. Write to a
            # temporary file first: an interrupted download must not replace a complete copy.
            _destination.parent.mkdir(parents=True, exist_ok=True)
            _partial = _destination.with_name(_destination.name + ".part")
            try:
                # read() raises if the connection closes before the whole file arrives.
                with urllib.request.urlopen(f"{REPO_URL}/{_relative}", timeout=60) as _response:
                    _partial.write_bytes(_response.read())
                _partial.replace(_destination)
            except Exception as _error:  # any network or HTTP failure: use the saved copy
                _partial.unlink(missing_ok=True)
                if not _destination.is_file():
                    raise RuntimeError(
                        f"Could not find or download {_relative}. When running outside the "
                        "repository, check REPO_URL at the top of the notebook."
                    ) from _error
                print(f"Aviso: no se pudo actualizar {_relative}; uso la copia guardada.")
            _refreshed.add(_relative)
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

    Esta es la tabla que vamos a construir durante el taller: **una fila por
    entidad territorial y semana epidemiológica**, con casos de dengue y lluvia.
    Es la que usará el taller de ML.
    """)
    return


@app.cell(hide_code=True)
def _(path):
    # The official table for the ML workshop: the exact bytes exported by the pipeline.
    ml_export = path("gold").read_bytes()
    final_gold = pl.read_parquet(io.BytesIO(ml_export))
    selected_entity = mo.ui.dropdown(
        sorted(final_gold["territorial_entity"].unique().to_list()),
        value="Santiago de Cali",
        label="Entidad territorial",
    )
    return final_gold, ml_export, selected_entity


@app.cell(hide_code=True)
def _(selected_entity, final_gold, ml_export):
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
            mo.download(
                data=ml_export,
                filename="weekly_dengue_signal.parquet",
                label="⬇️ Descargar tabla oficial para ML",
            ),
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


@app.cell(hide_code=True)
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


@app.cell(hide_code=True)
def _(path, bulletin_week, bulletin_page):
    # mo.pdf only opens on initial_page when src is a URL string. Serve the file through
    # marimo first (what mo.pdf does with a Path) and pass that URL instead.
    _pdf_path = path(bulletin_week.value)
    try:
        from marimo._output.data.data import pdf as _serve_pdf

        _src = _serve_pdf(_pdf_path.read_bytes()).url
    except Exception:  # private marimo API that may change: fall back to page 1
        _src = _pdf_path
    mo.pdf(src=_src, initial_page=bulletin_page, height="55vh")
    return


@app.cell(hide_code=True)
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


@app.cell(hide_code=True)
def _(path, bulletin_week):
    def find_table(pdf_path: Path):
        """Find the table by title because its page and number change every week."""
        _title = re.compile(r"Casos notificados de dengue por entidad territorial", re.I)
        # Read the file into memory so no file handle stays open after each run.
        _pdf = pdfplumber.open(io.BytesIO(pdf_path.read_bytes()))
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


@app.cell(hide_code=True)
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

    ### 👀 Demostración · Números colombianos
    El código ya está resuelto: quitamos los espacios antes de usar `int` y cambiamos
    la coma por un punto antes de usar `float`. Predice cuánto vale `"9 504"` después
    de convertirlo y compruébalo en la tabla. No tienes que editar esta celda.
    """)
    return


@app.cell(hide_code=True)
def _():
    def parse_integer(text: str) -> int | None:
        """'9 504' -> 9504. The bulletin uses spaces as thousands separators."""
        return int(text.replace(" ", "").replace(" ", ""))

    def parse_decimal(text: str) -> float | None:
        """'30,3' -> 30.3. The bulletin uses a decimal comma."""
        return float(text.replace(",", "."))

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
    numbers_ok = all(f["ok"] for f in _rows)
    mo.vstack(
        [
            mo.callout(
                mo.md(
                    "✅ **Demostración:** las conversiones numéricas son correctas."
                    if numbers_ok
                    else "❌ **Demostración:** revisa las conversiones numéricas."
                ),
                kind="success" if numbers_ok else "danger",
            ),
            pl.DataFrame(_rows),
        ]
    )
    return (numbers_ok,)


@app.cell(hide_code=True)
def _():
    def crop_table(page, title):
        """Keep the left or right page column containing the table."""
        _half = page.width / 2
        _x0, _x1 = (0, _half) if title["x0"] < _half else (_half, page.width)
        _bbox = (_x0, title["top"] - 2, _x1, page.height)
        return page.within_bbox(_bbox)

    return (crop_table,)


@app.cell(hide_code=True)
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


@app.cell(hide_code=True)
def _(page, title, read_rows):
    _half = page.width / 2
    _x0, _x1 = (0, _half) if title["x0"] < _half else (_half, page.width)
    _bbox = (_x0, title["top"] - 2, _x1, page.height)
    _results = []
    for _method, _cropped in (
        ("crop", page.crop(_bbox)),
        ("within_bbox", page.within_bbox(_bbox)),
    ):
        _rows, _ = read_rows(_cropped.extract_text())
        _total = sum(r["total_cases"] for r in _rows if r["territorial_entity"] == "Total")
        _sum = sum(r["total_cases"] for r in _rows if r["territorial_entity"] != "Total")
        _results.append(
            {
                "method": _method,
                "rows": len(_rows),
                "sum": _sum,
                "total": _total,
                "lost": _total - _sum,
            }
        )
    pdf_comparison = pl.DataFrame(_results)
    mo.vstack(
        [
            mo.md(
                "### 👀 Demostración · ¿Se perdieron casos al extraer?\n"
                "Compara los dos recortes de la misma página. `rows` incluye la fila Total; "
                "`lost` es la diferencia entre el total publicado y la suma extraída. "
                "**¿Cuál conservarías y cómo comprobarías que funcionó?** "
                "Cambia entre las semanas 26 y 27: un método puede funcionar en una y fallar en otra."
            ),
            pdf_comparison,
            mo.md(
                "`crop` incluye caracteres que tocan el borde; `within_bbox` conserva solo "
                "los que están completamente adentro. En la semana 26 entran letras de la "
                "columna vecina y se pierden filas. El resto del notebook ya usa `within_bbox`."
            ),
        ]
    )
    return (pdf_comparison,)


@app.cell(hide_code=True)
def _(read_rows, page, crop_table, title):
    _text = crop_table(page, title).extract_text()
    _rows, discarded_lines = read_rows(_text)
    bulletin_table = pl.DataFrame(_rows)
    bulletin_table
    return discarded_lines, bulletin_table


@app.cell(hide_code=True)
def _(bulletin_table, bulletin_week, crop_table, find_table, path, read_rows):
    _ready = bulletin_table.height > 0 and bulletin_table["total_cases"].null_count() == 0
    if not _ready:
        checkpoint_1 = False
        _output = mo.callout(
            mo.md("❌ **Validación del PDF:** revisa las conversiones numéricas."), kind="danger"
        )
    else:
        # Validate every bulletin against its own Total row, not only the selected one:
        # both are loaded into the warehouse below, and one can read fine while the other
        # loses rows.
        _results = []
        for _key in ("bulletin_26", "bulletin_27"):
            _, _page, _title = find_table(path(_key))
            _text = crop_table(_page, _title).extract_text()
            _week = int(re.search(r"semana epidemiol[oó]gica (\d+) de \d{4}", _text).group(1))
            _rows, _discarded = read_rows(_text)
            _total = sum(_r["total_cases"] for _r in _rows if _r["territorial_entity"] == "Total")
            _total_sum = sum(
                _r["total_cases"] for _r in _rows if _r["territorial_entity"] != "Total"
            )
            _results.append(
                {
                    "key": _key,
                    "week": _week,
                    "entities": sum(_r["territorial_entity"] != "Total" for _r in _rows),
                    "total": _total,
                    "sum": _total_sum,
                    "broken": [_l for _l in _discarded if re.search(r"\d+,\d", _l)],
                }
            )
        # Show the selected bulletin first when more than one fails.
        _failed = sorted(
            (_r for _r in _results if not _r["total"] or _r["total"] != _r["sum"]),
            key=lambda _r: _r["key"] != bulletin_week.value,
        )
        checkpoint_1 = not _failed
        if checkpoint_1:
            _detail = " y ".join(
                f"las {_r['entities']} entidades de la semana {_r['week']} suman **{_r['sum']:,}**"
                for _r in _results
            )
            _output = mo.callout(
                mo.md(
                    f"✅ **Validación del PDF:** {_detail} casos, igual que la fila *Total* de cada "
                    "boletín. Validar contra el propio documento es la mejor prueba que existe."
                ),
                kind="success",
            )
        else:
            _r = _failed[0]
            _broken = "\n".join(_r["broken"])
            _other = (
                ""
                if _r["key"] == bulletin_week.value
                else "El boletín que tienes seleccionado cuadra, pero la bodega carga los "
                "dos y este otro no.\n\n"
            )
            _output = mo.callout(
                mo.md(
                    f"❌ **Validación del PDF (semana {_r['week']}):** las entidades "
                    f"suman **{_r['sum']:,}**, pero el boletín dice **{_r['total']:,}**. "
                    f"Faltan **{_r['total'] - _r['sum']:,} casos**.\n\n"
                    f"{_other}"
                    f"Estas líneas tienen números pero no se pudieron leer:\n\n```\n{_broken}\n```\n\n"
                    "Revisa el recorte y las conversiones de la demostración. "
                    "Esta validación protege la carga de los dos boletines."
                ),
                kind="danger",
            )
    _output
    return (checkpoint_1,)


@app.cell(hide_code=True)
def _():
    mo.accordion(
        {
            "Para consultar: los dos métodos de recorte": mo.md(
                "pdfplumber tiene dos formas de recortar una página:\n\n"
                "* `page.crop(bbox)` conserva los caracteres que **tocan** la caja.\n"
                "* `page.within_bbox(bbox)` conserva solo los que están **completamente adentro**.\n\n"
                "Las primeras letras de la otra columna tocan el borde… Prueba también "
                "con la semana 27: ¿por qué allí sí funcionaba?"
            )
        }
    )
    return


@app.cell(hide_code=True)
def _(find_table, checkpoint_1, con, read_rows, crop_table, path):
    mo.stop(
        not checkpoint_1,
        mo.md("⏳ *La carga espera que los dos boletines coincidan con sus totales.*"),
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


@app.cell(hide_code=True)
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

    ### ✏️ TODO 1 · Elige el formato de la fecha · 8 minutos
    **Cambia solo el texto entre comillas de `notification_date_format` en la celda
    siguiente.** Está escrito para año-mes-día; nuestros datos vienen en día/mes/año.
    Usa `%d` para día, `%m` para mes y `%Y` para año de cuatro cifras, con los mismos
    separadores que la fuente. Ejecuta la celda con `Ctrl/⌘ + Enter`.

    La plantilla ya separa la fecha de la hora, la convierte a `DATE` y conserva la
    alternativa ISO para la muestra sintética. No necesitas escribir esas funciones.
    **Comprueba:** todas las filas deben tener fecha válida. Explica a tu pareja por
    qué un `NULL` no significa que el caso no tenga fecha en la fuente.
    """)
    return


@app.cell
def _():
    # >>> SOLUTION
    notification_date_format = "%d/%m/%Y"
    # <<< SOLUTION
    # >>> STUDENT
    # # TODO 1: match the source's day/month/year format.
    # notification_date_format = "%Y-%m-%d"
    # <<< STUDENT
    return (notification_date_format,)


@app.cell(hide_code=True)
def _():
    mo.accordion(
        {
            "💡 Pista del TODO 1": mo.md(
                "En `2/12/2024`, el primer número es el día. Ordena los tres códigos "
                "como aparecen en la fuente y sepáralos con `/`. La fecha que buscamos "
                "es el **2 de diciembre de 2024**."
            ),
            "🛟 Solución para continuar · fechas": mo.md(
                'Cambia la línea por `notification_date_format = "%d/%m/%Y"` y ejecútala. '
                "Después, comprueba los conteos de fechas válidas y explica el resultado "
                "antes de continuar."
            ),
            "Opcional: qué hace la plantilla SQL": mo.md(
                "`split_part` conserva lo que hay antes del primer espacio; `try_strptime` "
                "interpreta ese texto con el formato elegido. `CAST` fija el tipo `DATE`. "
                "`coalesce` usa la conversión ISO alternativa si la primera devuelve `NULL`."
            ),
        }
    )
    return


@app.cell(hide_code=True)
def _(bronze_sivigila, con, notification_date_format):
    mo.stop(bronze_sivigila is None)
    try:
        con.execute(
            """
            CREATE OR REPLACE TABLE silver.cases AS
            SELECT
                cod_dpto_o AS original_department_code,
                -- The INS files already include leading zeros ('08', '001'). lpad is a safeguard
                -- for exports that lose them, for example after saving the file from Excel.
                lpad(cod_dpto_o, 2, '0') || lpad(cod_mun_o, 3, '0') AS municipality_code,
                coalesce(
                    CAST(try_strptime(split_part(trim(fec_not), ' ', 1), ?) AS DATE),
                    try_cast(split_part(trim(fec_not), ' ', 1) AS DATE)
                ) AS notification_date,
                CAST(ano AS INTEGER) AS epi_year,
                CAST(semana AS INTEGER) AS epi_week,
                cod_eve AS event_code,
                ajuste AS adjustment
            FROM bronze.sivigila
            """,
            [notification_date_format],
        ).fetchall()
    except duckdb.Error as _error:
        # An unknown format code (%D, a lone %) raises instead of returning NULL. The
        # checkpoint below turns it into a TODO 1 hint instead of a traceback.
        date_format_error = str(_error).splitlines()[0]
        cases_by_department = None
    else:
        date_format_error = None
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
    return cases_by_department, date_format_error


@app.cell(hide_code=True)
def _(cases_by_department, con, date_format_error, notification_date_format):
    _complete = bool(
        cases_by_department is not None
        and not cases_by_department.is_empty()
        and (cases_by_department["with_valid_municipality"] == cases_by_department["cases"]).all()
        and (cases_by_department["with_valid_date"] == cases_by_department["cases"]).all()
    )
    # A non-NULL value is not enough: the column must be a date, and each date must fit the
    # week the case was reported in (ano, semana). In the INS files a notification is never
    # earlier than that week, while a wrong format code such as %M (minutes) moves every
    # date to January.
    _date_type = None
    _out_of_range = 0
    if _complete:
        _type = con.sql("SELECT typeof(notification_date) FROM silver.cases LIMIT 1").fetchall()
        _date_type = _type[0][0] if _type else None
    _is_date = _date_type is not None and _date_type.startswith(("DATE", "TIMESTAMP"))
    if _is_date:
        _out_of_range = con.sql(
            """
            SELECT count(*) FROM silver.cases
            WHERE CAST(notification_date AS DATE)
                    < make_date(epi_year, 1, 4) - CAST(dayofweek(make_date(epi_year, 1, 4)) AS INTEGER)
                      + CAST(7 * (epi_week - 1) AS INTEGER)
               OR abs(year(notification_date) - epi_year) > 1
            """
        ).fetchall()[0][0]
    checkpoint_2 = _complete and _is_date and _out_of_range == 0
    if checkpoint_2:
        _message = (
            "✅ **TODO 1 completo:** el 100 % de los casos tiene municipio y fecha de notificación."
        )
    elif date_format_error is not None:
        _message = (
            f'❌ **TODO 1 pendiente:** DuckDB no reconoce el formato `"{notification_date_format}"`. '
            "Usa solo códigos de `strptime` como `%d`, `%m` y `%Y`, separados como en la fuente "
            f"(`2/12/2024`).\n\nDetalle de DuckDB: `{date_format_error}`"
        )
    elif not _complete:
        _message = (
            "❌ **TODO 1 pendiente:** hay casos sin municipio o fecha de notificación. "
            "Revisa el formato del TODO 1 y los conteos exactos: los porcentajes están redondeados."
        )
    elif not _is_date:
        _message = (
            f"❌ **TODO 1 pendiente:** `notification_date` no está vacía, pero sigue siendo "
            f"**texto** (`{_date_type}`), no una fecha. Revisa la plantilla del TODO 1 y "
            "`try_strptime`."
        )
    else:
        _message = (
            f"❌ **TODO 1 pendiente:** hay **{_out_of_range:,} fechas** que no cuadran con la "
            "semana del caso (`ano`, `semana`): una notificación no puede ser anterior a esa "
            "semana ni caer en otro año. ¿Qué código representa el **mes** en `2/12/2024`? "
            "Revisa el TODO 1."
        )
    mo.callout(mo.md(_message), kind="success" if checkpoint_2 else "danger")
    return (checkpoint_2,)


@app.cell(hide_code=True)
def _(checkpoint_2, con, path):
    mo.stop(
        not checkpoint_2,
        mo.md("⏳ *Completa el TODO 1; tienes una solución para continuar en su ayuda.*"),
    )
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
        SELECT
            me.territorial_entity,
            c.epi_year,
            c.epi_week,
            count(*) AS cases,
            count(*) FILTER (WHERE c.event_code = '220') AS severe_cases
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

    **👀 Demostración del facilitador.** La consulta en vivo es opcional; para el
    ejercicio usamos la copia guardada. Puedes seguir sin pulsar el botón.
    """)
    return


@app.cell(hide_code=True)
def _():
    api_button = mo.ui.run_button(
        label="🌧️ Consultar la API del IDEAM en vivo (Valle, últimos 7 días)"
    )
    api_button
    return (api_button,)


@app.cell(hide_code=True)
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


@app.cell(hide_code=True)
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


@app.cell(hide_code=True)
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
    use_aliases = mo.ui.switch(value=True, label="Usar la tabla de alias (CALI → SANTIAGO DE CALI)")
    return macros_ready, use_aliases


@app.cell(hide_code=True)
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
                   CAST(precipitacion_mm AS DECIMAL(14, 4)) AS precipitation_mm,
                   CAST(n_lecturas AS INTEGER) AS reading_count
            FROM bronze.ideam
        )
        SELECT
            b.*,
            d.cod_mpio AS municipality_code,
            (b.reading_count > 144 OR b.precipitation_mm > 300) AS suspicious_reading
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
            mo.md(
                "**👀 Demostración de alias:** vienen activados. Desactívalos para ver "
                "qué estaciones pierden su municipio y vuelve a activarlos antes del TODO 2."
            ),
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


@app.cell(hide_code=True)
def _(con, macros_ready):
    mo.stop(not macros_ready)
    _week_comparison = con.sql(
        """
        SELECT CAST(d AS DATE) AS observation_date, dayname(d) AS day,
               week(d) AS iso_week, epi_week(d) AS epidemiological_week
        FROM unnest(generate_series(TIMESTAMP '2026-06-27', TIMESTAMP '2026-07-05', INTERVAL 1 DAY)) AS t(d)
        """
    ).pl()
    mo.accordion({"Opcional: comparar semanas ISO y epidemiológicas": _week_comparison})
    return


@app.cell(hide_code=True)
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


@app.cell(hide_code=True)
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


@app.cell(hide_code=True)
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
    ### ✏️ TODO 2 · Combina las estaciones de una semana · 12 minutos
    La plantilla ya calcula `per_station`: **una fila por estación y semana**, con
    la suma de sus días de lluvia. También están preparados la llave, el `GROUP BY`
    y el conteo de estaciones. Debemos obtener **una fila por entidad y semana**.

    | Paso ya resuelto | Resultado de ejemplo |
    |---|---|
    | Estación A: 10 + 20 mm en sus días con datos | 30 mm en la semana |
    | Estación B: 20 + 40 mm en sus días con datos | 60 mm en la semana |

    **Edita solo `sum(mm)` en el SELECT final** de la celda siguiente. La columna
    pide el **promedio entre los totales semanales de las estaciones**: para el ejemplo
    debe dar **45 mm**, no 90 mm. Elige entre `sum`, `avg` y `count`.

    Conserva la suma del primer paso y las columnas de agrupación. Después de ejecutar,
    comprueba tanto la **estructura** como el **cálculo**. Explica a tu pareja qué
    representa una fila antes y después de cada agrupación.
    """)
    return


@app.cell
def _(con, entity_rainfall_ready):
    mo.stop(not entity_rainfall_ready)
    con.execute(
        """
        CREATE OR REPLACE TABLE silver.weekly_rainfall AS
        WITH per_station AS (
            -- First, total weekly rainfall for each station...
            SELECT territorial_entity, station_code,
                   epi_year(observation_date) AS epi_year, epi_week(observation_date) AS epi_week,
                   sum(precipitation_mm) AS mm
            FROM silver.entity_daily_rainfall
            GROUP BY ALL
        )
        -- ...then combine the station totals of each territorial entity and week.
        SELECT territorial_entity, epi_year, epi_week,
        -- >>> SOLUTION
               round(avg(mm), 2) AS mean_precipitation_mm,
        -- <<< SOLUTION
        -- >>> STUDENT
        --        round(sum(mm), 2) AS mean_precipitation_mm,  -- TODO 2: combine station totals.
        -- <<< STUDENT
               count(DISTINCT station_code) AS stations_with_data
        FROM per_station
        GROUP BY ALL
        """
    ).fetchall()
    weekly_rainfall_ready = True
    return (weekly_rainfall_ready,)


@app.cell(hide_code=True)
def _():
    mo.accordion(
        {
            "💡 Pista del TODO 2": mo.md(
                "La primera agrupación ya sumó los días de cada estación. En la segunda, "
                "`sum` acumula las estaciones, `avg` calcula su promedio y `count` cuenta "
                "filas. ¿Cuál representa `(30 + 60) / 2`? El conteo de estaciones viene resuelto."
            ),
            "🛟 Solución para continuar · agregación": mo.md(
                "En el SELECT final, usa `round(avg(mm), 2) AS mean_precipitation_mm`. "
                "Conserva `sum(precipitation_mm)` en `per_station`. Ejecuta y explica por qué "
                "promediar directamente los días daría otra cantidad."
            ),
            "Opcional: seguir investigando": mo.md(
                "¿Cómo influye que una estación tenga días sin datos? ¿Qué diferencia hay "
                "entre `count(*)` y `count(DISTINCT station_code)` en cada paso? "
                "La definición de las columnas está en `docs/diccionario_de_datos.md`; "
                "las decisiones sobre datos sospechosos quedan en `RETOS.md`."
            ),
        }
    )
    return


@app.cell(hide_code=True)
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
            SELECT
                e.entidad_territorial AS territorial_entity,
                e.tipo AS entity_type,
                lpad(e.cod_dpto, 2, '0') AS department_code,
                s.epi_year,
                s.epi_week
            FROM bronze.entities AS e CROSS JOIN weeks AS s
        ),
        suspicious AS (
            SELECT
                territorial_entity,
                epi_year(observation_date) AS epi_year,
                epi_week(observation_date) AS epi_week,
                CAST(count(*) FILTER (WHERE suspicious_reading) AS INTEGER) AS suspicious_days
            FROM silver.entity_daily_rainfall
            GROUP BY ALL
        )
        SELECT
            es.territorial_entity,
            es.entity_type,
            es.department_code,
            es.epi_year,
            es.epi_week,
            make_date(es.epi_year, 1, 4) - CAST(dayofweek(make_date(es.epi_year, 1, 4)) AS INTEGER)
                + CAST(7 * (es.epi_week - 1) AS INTEGER) AS week_start,
            b.total_cases AS bulletin_cumulative_cases,
            -- Gold fixes the column types, whatever aggregation TODO 2 used
            -- (sum() over DECIMAL stays DECIMAL, which charts cannot serialize).
            CAST(l.mean_precipitation_mm AS DOUBLE) AS mean_precipitation_mm,
            CAST(l.stations_with_data AS BIGINT) AS stations_with_data,
            sp.suspicious_days,
            CASE WHEN es.epi_year IN (SELECT epi_year FROM silver.cases) THEN coalesce(c.cases, 0) END
                AS sivigila_cases,
            CASE WHEN es.epi_year IN (SELECT epi_year FROM silver.cases) THEN coalesce(c.severe_cases, 0) END
                AS sivigila_severe_cases,
            CASE
                WHEN es.epi_year IN (SELECT epi_year FROM silver.cases) THEN 'sivigila'
                WHEN b.total_cases IS NOT NULL THEN 'bulletin'
            END AS case_source
        FROM spine AS es
        LEFT JOIN silver.weekly_cases AS c
            ON es.territorial_entity = c.territorial_entity
            AND es.epi_year = c.epi_year AND es.epi_week = c.epi_week
        LEFT JOIN silver.weekly_rainfall AS l
            ON es.territorial_entity = l.territorial_entity
            AND es.epi_year = l.epi_year AND es.epi_week = l.epi_week
        LEFT JOIN suspicious AS sp
            ON es.territorial_entity = sp.territorial_entity
            AND es.epi_year = sp.epi_year AND es.epi_week = sp.epi_week
        LEFT JOIN bronze.bulletin AS b
            ON es.territorial_entity = b.territorial_entity
            AND es.epi_year = b.epi_year AND es.epi_week = b.epi_week
        ORDER BY es.territorial_entity, es.epi_year, es.epi_week
        """
    )
    gold = con.sql("SELECT * FROM gold.signal").pl()
    gold
    return (gold,)


@app.cell(hide_code=True)
def _(con, gold):
    _keys = ["territorial_entity", "epi_year", "epi_week"]
    _duplicates = gold.height - gold.select(_keys).n_unique()
    _weeks = gold.select("epi_year", "epi_week").n_unique()
    _entities = gold["territorial_entity"].n_unique()
    # Unique keys are not enough: the gold spine is always complete, so a rainfall table
    # with the wrong weeks would simply not join. Compare its keys with the epidemiological
    # weeks that actually have rainfall data.
    _extra, _missing = con.sql(
        """
        WITH expected AS (
            SELECT DISTINCT territorial_entity,
                   epi_year(observation_date) AS epi_year, epi_week(observation_date) AS epi_week
            FROM silver.entity_daily_rainfall
        ),
        actual AS (
            SELECT DISTINCT territorial_entity, epi_year, epi_week FROM silver.weekly_rainfall
        )
        SELECT
            (SELECT count(*) FROM (SELECT * FROM actual EXCEPT SELECT * FROM expected)),
            (SELECT count(*) FROM (SELECT * FROM expected EXCEPT SELECT * FROM actual))
        """
    ).fetchall()[0]
    _right_weeks = _extra == 0 and _missing == 0
    checkpoint_3 = _duplicates == 0 and gold.height == _weeks * _entities and _right_weeks
    if checkpoint_3:
        _message = (
            f"✅ **Estructura correcta:** {gold.height:,} filas = {_entities} entidades × "
            f"{_weeks} semanas, sin llaves repetidas. Esto verifica las llaves; "
            "**el cálculo del TODO 2 se comprueba abajo**."
        )
    elif _duplicates:
        _message = (
            f"❌ **Estructura pendiente:** hay **{_duplicates:,} filas repetidas** "
            "(misma entidad y semana). Revisa las agrupaciones de la plantilla del TODO 2."
        )
    else:
        _message = (
            "❌ **Estructura pendiente:** tu tabla de lluvia no tiene filas repetidas, pero sus "
            "semanas no son las semanas epidemiológicas de los datos: "
            f"**faltan {_missing:,}** combinaciones de entidad y semana y **sobran {_extra:,}**. "
            "En el TODO 2 conserva `epi_year(observation_date)` y `epi_week(observation_date)` "
            "(no uses `week()`: las semanas ISO empiezan en lunes)."
        )
    mo.callout(mo.md(_message), kind="success" if checkpoint_3 else "danger")
    return (checkpoint_3,)


@app.cell(hide_code=True)
def _(final_gold, gold):
    # Validate every entity-week, not just entity summaries that can hide offsetting errors.
    # This cell does not wait for the structure check, so the summary in section 8 always
    # gets a TODO 2 status; the next cell shows the comparison once the structure is right.
    _keys = ["territorial_entity", "epi_year", "epi_week"]
    _pairs = {
        "cases": "sivigila_cases",
        "stations": "stations_with_data",
        "rainfall": "mean_precipitation_mm",
    }
    _weekly = gold.select(*_keys, *_pairs.values(), pl.lit(True).alias("student_present")).join(
        final_gold.select(*_keys, *_pairs.values(), pl.lit(True).alias("repo_present")),
        on=_keys,
        how="full",
        coalesce=True,
        suffix="_repo",
    )
    _present = _weekly["student_present"].fill_null(False) & _weekly["repo_present"].fill_null(
        False
    )
    _differs = {
        _name: ~(_present & _weekly[_column].eq_missing(_weekly[f"{_column}_repo"]))
        for _name, _column in _pairs.items()
    }
    gold_mismatches = [_name for _name, _rows in _differs.items() if _rows.any()]
    gold_matches_repo = not gold_mismatches
    cases_match = "cases" not in gold_mismatches
    aggregation_ok = "stations" not in gold_mismatches and "rainfall" not in gold_mismatches
    # Keep only the entity-weeks and columns that differ, next to the repository values.
    _mask = pl.repeat(False, _weekly.height, eager=True)
    _shown = []
    for _name in gold_mismatches:
        _mask = _mask | _differs[_name]
        _column = _pairs[_name]
        _shown += [
            pl.col(_column).alias(f"student_{_column}"),
            pl.col(f"{_column}_repo").alias(f"repo_{_column}"),
        ]
    gold_differences = _weekly.filter(_mask).select(*_keys, *_shown).sort(_keys)
    return aggregation_ok, cases_match, gold_differences, gold_matches_repo, gold_mismatches


@app.cell(hide_code=True)
def _(
    aggregation_ok,
    checkpoint_3,
    final_gold,
    gold,
    gold_differences,
    gold_matches_repo,
    gold_mismatches,
    missing_municipalities,
):
    mo.stop(not checkpoint_3)
    _mine = gold.group_by("territorial_entity").agg(
        student_cases=pl.col("sivigila_cases").sum(),
        student_rain_mm=pl.col("mean_precipitation_mm").mean().round(2),
        student_stations=pl.col("stations_with_data").max(),
    )
    _repo = final_gold.group_by("territorial_entity").agg(
        repo_cases=pl.col("sivigila_cases").sum(),
        repo_rain_mm=pl.col("mean_precipitation_mm").mean().round(2),
        repo_stations=pl.col("stations_with_data").max(),
    )
    # A full join keeps entities that are missing from either table, so they count as differences.
    _comparison = _mine.join(_repo, on="territorial_entity", how="full", coalesce=True).sort(
        "territorial_entity"
    )
    _hints = {
        "cases": "**Casos:** hay diferencias en `sivigila_cases` por entidad y semana. Los TODOs no "
        "cambian los casos: ¿estás usando otro archivo de SIVIGILA, como la muestra sintética?",
        "stations": "**Estaciones:** hay diferencias en `stations_with_data` por entidad y semana. "
        "¿Contaste estaciones distintas o filas (una por estación y día)?",
        "rainfall": "**Lluvia:** hay diferencias en `mean_precipitation_mm` por entidad y semana. El "
        "repositorio suma la lluvia de la semana en cada estación y luego promedia las "
        "estaciones de la entidad (mm por semana). ¿Qué calculaste tú?",
    }
    _aliases_off = not missing_municipalities.is_empty()
    if aggregation_ok:
        _status = mo.callout(
            mo.md("✅ **TODO 2 completo:** lluvia y estaciones coinciden por entidad y semana."),
            kind="success",
        )
    elif _aliases_off:
        # Without the aliases, Cali's stations never reach gold, so the comparison fails
        # whatever the aggregation is: point at the switch, not at the calculation.
        _unmatched = ", ".join(
            f"`{_name}`"
            for _name in missing_municipalities["municipality"].unique(maintain_order=True)
        )
        _status = mo.callout(
            mo.md(
                "⏳ **TODO 2 pendiente:** antes de revisar tu cálculo, vuelve a la "
                "**sección 5** y activa el interruptor **Usar la tabla de alias "
                f"(CALI → SANTIAGO DE CALI)**. Hay estaciones del IDEAM sin municipio "
                f"({_unmatched}), así que su lluvia no llega a la tabla oro y la "
                "comparación todavía no dice nada sobre tu agregación."
            ),
            kind="warn",
        )
    else:
        _status = mo.callout(
            mo.md(
                "⏳ **TODO 2 pendiente:** revisa el cálculo y el detalle de abajo. "
                "La ayuda incluye una solución para continuar."
            ),
            kind="warn",
        )
    if gold_matches_repo:
        _detail = [
            mo.callout(
                mo.md(
                    "✅ **¿Coincide con la tabla del inicio? Sí:** casos, estaciones y lluvia "
                    "coinciden en cada entidad y semana. La tabla de abajo resume por entidad."
                ),
                kind="success",
            ),
            _comparison,
        ]
    else:
        _shown_hints = [_name for _name in gold_mismatches if not _aliases_off or _name == "cases"]
        _detail = [
            mo.callout(
                mo.md(
                    "💡 **Hay diferencias de valores:** tener una fila por entidad y semana "
                    "no garantiza el cálculo correcto. Revisa estas columnas:\n\n"
                    + "\n".join(f"* {_hints[_name]}" for _name in _shown_hints)
                ),
                kind="info",
            )
            if _shown_hints
            else None,
            mo.md(
                f"**{gold_differences.height:,} combinaciones de entidad y semana** no coinciden "
                "con la tabla del repositorio (`student_…` es tu valor; `repo_…`, el esperado):"
            ),
            gold_differences,
        ]
    _buffer = io.BytesIO()
    gold.write_parquet(_buffer)
    mo.vstack(
        [
            _status,
            *(_item for _item in _detail if _item is not None),
            mo.download(
                data=_buffer.getvalue(),
                filename="mi_weekly_dengue_signal.parquet",
                label="⬇️ Descargar mi tabla del ejercicio",
            ),
        ]
    )
    return


@app.cell(hide_code=True)
def _(final_gold, ml_export):
    mo.vstack(
        [
            mo.md(
                "**Para el taller de ML, usa la tabla oficial** (es la misma del botón de "
                "la sección 1). La lluvia de la tabla del ejercicio depende de tu "
                f"solución al TODO 2. La oficial conserva las {final_gold.width} columnas del "
                "diccionario de datos y suma la lluvia semanal por estación "
                "antes de promediar estaciones."
            ),
            mo.download(
                data=ml_export,
                filename="weekly_dengue_signal.parquet",
                label="⬇️ Descargar tabla oficial para ML",
            ),
        ]
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 7 · Para explorar después del taller 🕵️

    **Material opcional.** En el cierre miraremos una pregunta; las demás quedan para
    la hackathon. El piloto deja abiertos problemas sobre acumulados, rezagos y datos
    sospechosos. Estas son algunas preguntas; el resto está en `RETOS.md`.
    """)
    return


@app.cell(hide_code=True)
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


@app.cell(hide_code=True)
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


@app.cell(hide_code=True)
def _(con, missing_municipalities):
    mo.stop(missing_municipalities is None)
    _unusual = con.sql(
        """
        SELECT observation_date, department, municipality, station_code,
               CAST(precipitation_mm AS DOUBLE) AS precipitation_mm, reading_count
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


@app.cell(hide_code=True)
def _():
    lag = mo.ui.slider(0, 12, value=0, step=1, show_value=True, label="Rezago (semanas)")
    return (lag,)


@app.cell(hide_code=True)
def _(checkpoint_3, gold, lag, missing_municipalities):
    mo.stop(not checkpoint_3)
    _with_lag = (
        gold.sort("territorial_entity", "epi_year", "epi_week")
        .with_columns(
            earlier_rainfall=pl.col("mean_precipitation_mm")
            .shift(lag.value)
            .over("territorial_entity")
        )
        .filter(pl.col("sivigila_cases").is_not_null())
    )
    _correlation = (
        _with_lag.group_by("territorial_entity")
        # An entity without rainfall gives NaN; show it as null.
        .agg(correlation=pl.corr("earlier_rainfall", "sivigila_cases").fill_nan(None).round(2))
        .sort("territorial_entity")
    )
    _without_rain = (
        gold.group_by("territorial_entity")
        .agg(has_rain=pl.col("mean_precipitation_mm").is_not_null().any())
        .filter(~pl.col("has_rain"))
        .sort("territorial_entity")["territorial_entity"]
        .to_list()
    )
    _notes = []
    if _without_rain and not missing_municipalities.is_empty():
        _verb = "no tiene" if len(_without_rain) == 1 else "no tienen"
        _notes.append(
            mo.callout(
                mo.md(
                    f"💡 **{', '.join(_without_rain)}** {_verb} lluvia, así que su correlación "
                    "queda en `null`: hay estaciones del IDEAM sin municipio. Activa el "
                    "interruptor de alias en la **sección 5** para calcularla."
                ),
                kind="warn",
            )
        )
    mo.vstack(
        [
            mo.md(
                "### 🕵️ Incógnita 4: ¿lluvia de cuándo?\nEl mosquito necesita agua para "
                "reproducirse, pero no de un día para otro. Mueve el rezago: ¿con cuántas "
                f"semanas de diferencia se parecen más la lluvia y los casos? *(Rezago = "
                f"{lag.value} semanas.)* Esta pregunta es el puente al taller de ML."
            ),
            *_notes,
            lag,
            _correlation,
        ]
    )
    return


@app.function(hide_code=True)
def progress_summary(todo1_ok: bool, todo2_ok: bool) -> mo.Html:
    """Render the closing summary with the status of both exercises."""
    _steps = {
        "TODO 1 · formato de fechas": todo1_ok,
        "TODO 2 · agregación semanal correcta": todo2_ok,
    }
    return mo.md(
        "## 8 · Resumen\n\n"
        + "\n".join(f"* {'✅' if _ok else '⏳'} {_step}" for _step, _ok in _steps.items())
        + "\n\n**¿Y ahora?** En la hackathon vas a escalar este piloto: todos los "
        "departamentos, todos los boletines, más variables de clima, y responder las "
        "incógnitas. Empieza por `RETOS.md` y por `uv run dengue-pipeline --help`."
    )


@app.cell(hide_code=True)
def _(checkpoint_2):
    # Every cell after TODO 1 waits for it, the next summary cell included, so this cell
    # shows the progress until TODO 1 passes.
    mo.stop(checkpoint_2)
    progress_summary(todo1_ok=False, todo2_ok=False)
    return


@app.cell(hide_code=True)
def _(aggregation_ok, checkpoint_2, checkpoint_3):
    progress_summary(todo1_ok=checkpoint_2, todo2_ok=checkpoint_3 and aggregation_ok)
    return


if __name__ == "__main__":
    app.run()
