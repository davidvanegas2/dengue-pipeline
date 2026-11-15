"""DuckDB warehouse with bronze, silver and gold schemas.

Bronze preserves source data; silver cleans types and shared keys; gold holds
consumption-ready tables for charts and machine learning.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import polars as pl

log = logging.getLogger(__name__)

SCHEMAS = ("bronze", "silver", "gold")


def connect(path: Path | str | None = None) -> duckdb.DuckDBPyConnection:
    """Open or create the warehouse and its schemas. Use ``path=None`` for an in-memory database."""
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path) if path is not None else ":memory:")
    for schema in SCHEMAS:
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    return con


def load_dataframe(con: duckdb.DuckDBPyConnection, table: str, data: pl.DataFrame) -> int:
    """Replace ``table`` (``schema.name``) with the contents of the DataFrame."""
    _validate_name(table)
    con.register("_temporary_df", data)
    try:
        con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM _temporary_df")
    finally:
        con.unregister("_temporary_df")
    log.info("%s: %s rows", table, data.height)
    return data.height


def load_file(con: duckdb.DuckDBPyConnection, table: str, path: Path) -> int:
    """Load a CSV or Parquet file. Read every CSV column as text."""
    _validate_name(table)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        reader = "read_csv(?, all_varchar = true, header = true)"
    elif suffix == ".parquet":
        reader = "read_parquet(?)"
    else:
        raise ValueError(f"Unsupported warehouse format: {path.name}")
    con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM {reader}", [str(path)])
    rows = count_rows(con, table)
    log.info("%s: %s rows (from %s)", table, rows, path.name)
    return rows


def count_rows(con: duckdb.DuckDBPyConnection, table: str) -> int:
    _validate_name(table)
    # Consume the complete result set before issuing another query.
    rows = con.execute(f"SELECT count(*) FROM {table}").fetchall()
    return int(rows[0][0]) if rows else 0


def _validate_name(table: str) -> None:
    """Reject SQL injection by accepting only simple ``schema.table`` names."""
    parts = table.split(".")
    if len(parts) != 2 or not all(p.isidentifier() for p in parts):
        raise ValueError(f"Invalid table name: {table!r} (use 'schema.table').")
    if parts[0] not in SCHEMAS:
        raise ValueError(f"Unknown schema {parts[0]!r}; use one of {SCHEMAS}.")
