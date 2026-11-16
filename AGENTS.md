# AGENTS.md

Guidance for AI coding agents (Codex, Claude Code, …) working in this repository.
`CLAUDE.md` imports this file, so it is the single source of truth.

## What this is

A didactic data-engineering workshop for the Loka × WIE ICESI 2026 hackathon (50 min, Dec 4).
A pilot pipeline takes three sources (INS weekly bulletin PDF, SIVIGILA microdata, IDEAM
rainfall via the Socrata API) plus DIVIPOLA references through DuckDB bronze → silver → gold,
producing `gold.weekly_dengue_signal` (one row per territorial entity × epidemiological week).
The gold table is the input of the ML workshop that follows.

## Ground rules (read first)

- **This repo must not solve the challenge.** Every team gets it. It is a pilot: 2 departments,
  2 bulletin extracts, rainfall only. Do not implement anything listed in `RETOS.md` (all
  bulletins, reporting lag/nowcasting, cumulative → weekly series, national scale,
  expected/observed columns, temperature/humidity, cleaning suspicious rain days). Do not widen
  the pilot (`PILOT_DEPARTMENTS`, entity and alias reference tables) unless explicitly asked.
  If in doubt, add a question to `RETOS.md` instead of code.
- **SIVIGILA data is synthetic** until `data/raw/sivigila/ORIGEN.txt` says `INS`. Never present
  patterns in it (e.g. rain–case correlations) as findings.

## Commands

uv manages Python (version in `.python-version`). `make` wraps everything; on Windows use the
`uv run …` equivalent shown in the Makefile.

- `make install`: `uv sync` + pre-commit hooks
- `make pipeline`: `uv run dengue-pipeline run` (offline, full pipeline + quality checks);
  `dengue-pipeline check` runs only the checks on the existing warehouse
- `make format`: ruff format/fix + `sqlfluff fix sql`
- `make lint`: ruff, sqlfluff, mypy (strict), `marimo check`, student-notebook staleness check
- `make test`: pytest with coverage; `make test-fast` skips `network` and `slow` markers
- `make student-notebook`: regenerate `notebooks/workshop.py`
- Single test: `uv run pytest tests/test_pipeline.py::test_name -q`

Before finishing a change: `make format && make lint && make test-fast`. CI runs `make lint`,
pytest without network tests (slow ones included), and `dengue-pipeline run`.

## Architecture

- `src/dengue_pipeline/extract/` (`bulletin.py` via pdfplumber, `sivigila.py` via polars,
  `ideam.py` via Socrata) returns untransformed DataFrames; `pipeline.load_bronze()` loads them
  into `data/dengue.duckdb`.
- `sql/`: `macros.sql` first, then `silver/*.sql` and `gold/*.sql` in alphabetical order. Each
  file must be idempotent (`CREATE OR REPLACE TABLE schema.table AS …`).
- `quality.py`: `CHECKS`, each returning a `CheckResult` (`critical=False` = warning only).
  `cli.py` is the entry point; `weeks.py` / `text.py` handle epidemiological weeks and
  Colombian numbers and names.
- Bronze reads CSVs as text. Typing, zero-padded DIVIPOLA codes and name normalization happen
  in silver. Gold is exported to `data/gold/*.parquet`.
- Rationale: `docs/arquitectura.md`. Data dictionary: `docs/diccionario_de_datos.md`.
  Facilitator guide: `docs/guia_facilitador.md`.

## Gotchas

- **DuckDB 2.x API:** relations have no `fetchone()`, and `con.execute(…)` has no `.pl()`. Use
  `con.sql(…).pl()` / `.fetchall()`. Always fully consume `execute()` results with
  `fetchall()`: an unfinished result makes the next `con.sql()` on that connection raise
  `ResourceInUseException`.
- **Gold snapshot and determinism:** `data/gold/*.parquet` is committed (the notebook opens
  with it) and a test compares it to a fresh run. After changing SQL, reference data or raw
  data, run `make pipeline` and commit the parquet. Rainfall is cast to `DECIMAL` before
  aggregating because parallel `DOUBLE` sums vary in the last decimal; keep aggregations
  deterministic.
- **Epidemiological weeks (MMWR, Sunday–Saturday) are not ISO weeks.** Never use DuckDB
  `week()` / `yearweek()`; use `sql/macros.sql` or `weeks.py` (both tested against `epiweeks`).
- **Bulletin PDFs:** find the table by its title (number, page and side change weekly), crop
  with `within_bbox` (not `crop`), and validate each bulletin against its own Total row. Tests
  pin real values (totals 56,797 / 59,262; 39 rows; 733 cases lost with `crop`). Never edit
  expected values to make a test pass.
- **IDEAM:** more than 165M rows. Never download raw data: aggregate server-side (SoQL
  `GROUP BY`) in monthly chunks, and expect 10–110 s per request. Department names changed
  format in 2026 (`VALLE DEL CAUCA` → `Valle Del Cauca`). ins.gov.co and the SIVIGILA portal
  may block automated access; SIVIGILA files are downloaded by hand.
- **sqlfluff:** it misparses `CREATE MACRO` (`macros.sql` disables CP03/CP05), and a SQL
  comment starting with the word "sqlfluff" is read as inline config.

## Notebooks (important)

- `notebooks/workshop_facilitator.py` (solved) is the single source of truth.
  `notebooks/workshop.py` is generated: never edit it by hand. Mark solution and student code
  with `# >>> SOLUTION … # <<< SOLUTION` and `# >>> STUDENT … # <<< STUDENT` (`--` prefix in
  SQL). STUDENT blocks are written commented and get uncommented one level. Run
  `make student-notebook` after every edit.
- Notebooks must be self-contained: never import `dengue_pipeline`. molab syncs only the `.py`
  file and downloads data from `URL_REPO`. The `DENGUE_REPO_RAIZ` env var overrides the data
  root (tests use it).
- marimo rules: each global is defined in exactly one cell; `_`-prefixed names are cell-local.
  marimo does not track DuckDB side effects, so a cell that creates a table must return a
  variable that downstream cells reference (e.g. `mo.stop(x is None)`). `@app.function`
  helpers may only use names from the setup cell.
- Tests run notebooks headless via `app.run()`, with UI elements at their defaults (button
  clicks are simulated by text replacement). `tests/test_notebooks.py` solves each TODO with
  exact string replacements on `workshop.py` and asserts `todo1_ok` and
  `checkpoint_1`…`checkpoint_3`. If you change TODO text or rename a checkpoint, update that
  test in the same change.
- The numbers in `docs/guia_facilitador.md` ("Números que vas a ver") come from the data.
  Update them when data or notebook logic changes.

## Conventions

- English: code, comments, docstrings, tests, filenames, tables/columns, commands.
  Spanish: README, `RETOS.md`, `docs/`, and everything participants see at runtime (notebook
  text, CLI output, quality-check messages).
- Keep original source names and values in `data/raw/`, `data/reference/` and bronze (e.g.
  `cod_eve`, `semana`, place names); expose English names via aliases in silver.
- Type annotations on all public functions (mypy strict).
- Mark tests that need internet with `@pytest.mark.network` and slow ones with
  `@pytest.mark.slow`.
- `.gitattributes` keeps source CSV bytes (CRLF; Python's `csv` module writes CRLF and a test
  compares the synthetic sample byte for byte) and marks PDF/parquet as binary. Don't
  normalize line endings in `*.csv`.
- Commit messages follow Conventional Commits and explain what and why (e.g.
  `feat(extract): …`).
