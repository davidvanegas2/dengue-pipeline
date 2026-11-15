"""Run silver and gold SQL transformations in order.

Keep transformations in .sql files so they can be read, reviewed and linted
with sqlfluff independently of Python, without adding dbt to the workshop.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

log = logging.getLogger(__name__)

LAYERS = ("silver", "gold")


def execute_file(con: duckdb.DuckDBPyConnection, path: Path) -> None:
    log.info("SQL: %s", path.name)
    con.execute(path.read_text(encoding="utf-8"))


def register_macros(con: duckdb.DuckDBPyConnection, sql_directory: Path) -> None:
    """Create shared epidemiological-week and name-normalization macros."""
    execute_file(con, sql_directory / "macros.sql")


def execute_layer(con: duckdb.DuckDBPyConnection, sql_directory: Path, layer: str) -> list[Path]:
    """Run every .sql file in a layer in alphabetical order (01_, 02_, ...)."""
    if layer not in LAYERS:
        raise ValueError(f"Unknown layer {layer!r}; use one of {LAYERS}.")
    files = sorted((sql_directory / layer).glob("*.sql"))
    if not files:
        raise FileNotFoundError(f"No SQL files in {sql_directory / layer}.")
    for filename in files:
        execute_file(con, filename)
    return files


def run_transformations(con: duckdb.DuckDBPyConnection, sql_directory: Path) -> list[Path]:
    register_macros(con, sql_directory)
    executed: list[Path] = []
    for layer in LAYERS:
        executed += execute_layer(con, sql_directory, layer)
    return executed
