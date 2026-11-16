"""SQL macros that clean SIVIGILA text fields."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date

import duckdb
import pytest

from dengue_pipeline.config import Paths
from dengue_pipeline.transform import register_macros


@pytest.fixture
def con(repo_paths: Paths) -> Iterator[duckdb.DuckDBPyConnection]:
    connection = duckdb.connect()
    register_macros(connection, repo_paths.sql)
    yield connection
    connection.close()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Real INS Excel export: day first, Spanish AM/PM with a non-breaking space.
        ("16/05/2024 12:00:00 a.\xa0m.", date(2024, 5, 16)),
        ("6/08/2024 12:00:00 p.\xa0m.", date(2024, 8, 6)),  # day without leading zero
        ("31/12/2023", date(2023, 12, 31)),  # plain day-first date
        ("2023-12-31", date(2023, 12, 31)),  # ISO date
        ("2023-12-31 00:00:00", date(2023, 12, 31)),  # ISO timestamp
        ("  16/05/2024 12:00:00 a.\xa0m.", date(2024, 5, 16)),  # surrounding whitespace
        ("", None),
        (None, None),
        ("not a date", None),
        ("31/02/2024", None),  # impossible date
    ],
)
def test_parse_date_text(con: duckdb.DuckDBPyConnection, text: str | None, expected: date) -> None:
    assert con.execute("SELECT parse_date_text(?)", [text]).fetchone() == (expected,)


@pytest.mark.parametrize(
    ("department", "municipality", "expected"),
    [
        ("76", "1", "76001"),  # three-digit suffix that lost its zeros
        ("8", "1.0", "08001"),  # Excel float
        ("76", "76001", "76001"),  # complete code
        ("8", "8001", "08001"),  # complete code that lost its leading zero
        ("8", "8001.0", "08001"),
        ("08", "433", "08433"),
    ],
)
def test_municipality_code(
    con: duckdb.DuckDBPyConnection, department: str, municipality: str, expected: str
) -> None:
    row = con.execute("SELECT municipality_code(?, ?)", [department, municipality]).fetchone()
    assert row == (expected,)
