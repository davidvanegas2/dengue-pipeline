from pathlib import Path

import polars as pl
import pytest

from dengue_pipeline import warehouse


def test_connect_creates_schemas() -> None:
    con = warehouse.connect()
    schemas = {row[0] for row in con.execute("SELECT schema_name FROM duckdb_schemas()").fetchall()}
    assert {"bronze", "silver", "gold"} <= schemas


def test_connect_on_disk(tmp_path: Path) -> None:
    path = tmp_path / "sub" / "bodega.duckdb"
    warehouse.connect(path).close()
    assert path.is_file()


def test_load_dataframe_and_count_rows() -> None:
    con = warehouse.connect()
    rows = warehouse.load_dataframe(con, "bronze.test", pl.DataFrame({"a": [1, 2, 3]}))
    assert rows == 3
    assert warehouse.count_rows(con, "bronze.test") == 3


def test_load_csv_preserves_leading_zeros(tmp_path: Path) -> None:
    path = tmp_path / "codes.csv"
    path.write_text("department_code,municipality_code\n08,08001\n76,76001\n", encoding="utf-8")
    con = warehouse.connect()
    warehouse.load_file(con, "bronze.codes", path)
    assert con.execute("SELECT department_code FROM bronze.codes ORDER BY 1").fetchall() == [
        ("08",),
        ("76",),
    ]


def test_load_parquet(tmp_path: Path) -> None:
    path = tmp_path / "x.parquet"
    pl.DataFrame({"x": [1.5]}).write_parquet(path)
    con = warehouse.connect()
    assert warehouse.load_file(con, "bronze.x", path) == 1


def test_load_unsupported_format(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        warehouse.load_file(warehouse.connect(), "bronze.x", tmp_path / "x.json")


@pytest.mark.parametrize(
    "name",
    ["table_without_schema", "bronze.x; DROP TABLE y", "other.table", "bronze.", "a.b.c"],
)
def test_invalid_table_names(name: str) -> None:
    with pytest.raises(ValueError, match=r"(Invalid|Unknown)"):
        warehouse.count_rows(warehouse.connect(), name)
