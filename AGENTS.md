# AGENTS.md

This file provides guidance to AI coding agents (Codex, Claude Code, etc.) when working with code in this repository. `CLAUDE.md` imports it, so this is the single source of truth.

## What this is

A didactic dengue data-engineering workshop (Hackathon Loka × WIE ICESI 2026). A pilot pipeline takes three sources (INS bulletin PDF, SIVIGILA microdata, IDEAM rainfall API) plus DIVIPOLA references through DuckDB bronze → silver → gold, producing `gold.weekly_dengue_signal` (one row per territorial entity × epidemiological week). It is intentionally a pilot that does not solve the challenge (`RETOS.md`). SIVIGILA data is a **synthetic sample** (see `data/raw/sivigila/ORIGEN.txt`).

## Commands

Uses `uv` (Python from `.python-version`); `make` wraps everything (on Windows use the `uv run` equivalent).

- `make install` — `uv sync` + pre-commit hooks
- `make pipeline` — `uv run dengue-pipeline run` (offline, full pipeline + quality checks); `dengue-pipeline check` runs only quality checks on the existing warehouse
- `make lint` — ruff check/format check, sqlfluff lint, mypy (strict), `marimo check`, and the student-notebook staleness check (what CI runs)
- `make format` — ruff format/fix + `sqlfluff fix sql`
- `make test` — pytest with coverage; `make test-fast` skips `network` and `slow` markers
- Single test: `uv run pytest tests/test_pipeline.py::test_name -q`
- `make student-notebook` — regenerate `notebooks/workshop.py`

## Architecture

- `src/dengue_pipeline/`: `extract/` (bulletin.py via pdfplumber, sivigila.py via polars, ideam.py via Socrata API) return **untransformed** DataFrames; `pipeline.load_bronze()` loads them into DuckDB (`data/dengue.duckdb`); `transform.py` runs SQL files; `quality.py` holds `CHECKS` (each returns a `CheckResult`; `critical=False` = warning only); `cli.py` is the entry point; `weeks.py`/`text.py` handle epidemiological weeks and Colombian numbers/names.
- `sql/`: `macros.sql` first, then `silver/*.sql` and `gold/*.sql` executed in alphabetical order. Each must be idempotent (`CREATE OR REPLACE TABLE schema.table AS ...`).
- Bronze reads CSVs **all as text**; typing, zero-padded DIVIPOLA codes and name normalization happen in silver. Gold is exported to `data/gold/*.parquet`.
- Design rationale (why DuckDB, marimo, SQL in files) is in `docs/arquitectura.md`; data dictionary in `docs/diccionario_de_datos.md`; facilitator guide in `docs/guia_facilitador.md`.

## Notebook generation (important)

`notebooks/workshop_facilitator.py` (solved) is the single source of truth. `notebooks/workshop.py` (student version) is **generated — never edit by hand**. Mark student-visible parts with `# >>> SOLUTION … # <<< SOLUTION` and `# >>> STUDENT … # <<< STUDENT` blocks (`--` prefix in SQL); STUDENT blocks are written commented and get uncommented one level. After editing the facilitator notebook run `make student-notebook`; `make lint` fails if `workshop.py` is stale.

## Conventions

- Code, comments, docstrings, tests, filenames, tables/columns, and commands in **English**; README, retos, docs, and notebook-visible explanations in **Spanish**.
- Preserve original source names/values in `data/raw/`, `data/reference/` and bronze (e.g. `cod_eve`, `semana`, place names); expose English names via aliases in silver.
- Type annotations on all public functions (mypy strict).
- Tests needing internet use `@pytest.mark.network`; slow ones `@pytest.mark.slow`.
- `.gitattributes` preserves source CSV bytes (CRLF) and marks PDF/parquet binary — don't normalize line endings in `*.csv`.
- Commit messages: Conventional Commits explaining what and why (e.g. `feat(extract): ...`).
