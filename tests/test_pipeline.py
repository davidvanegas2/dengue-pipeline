"""End-to-end bronze, silver and gold tests against an isolated repository."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import duckdb
import polars as pl
import pytest

from dengue_pipeline import quality, warehouse
from dengue_pipeline.config import Paths
from dengue_pipeline.pipeline import export_gold, run_pipeline

Warehouse = tuple[Paths, duckdb.DuckDBPyConnection]


@pytest.fixture
def ready_warehouse(tmp_paths: Paths) -> Iterator[Warehouse]:
    summary = run_pipeline(tmp_paths)
    assert summary.ok, [str(v) for v in summary.checks]
    con = warehouse.connect(tmp_paths.database)
    yield tmp_paths, con
    con.close()


def _scalar(con: duckdb.DuckDBPyConnection, sql: str) -> object:
    rows = con.execute(sql).fetchall()
    assert rows
    return rows[0][0]


def test_pipeline_summary(tmp_paths: Paths) -> None:
    summary = run_pipeline(tmp_paths)
    assert summary.ok
    assert summary.bronze_rows["bronze.dengue_bulletin"] == 78
    assert summary.bronze_rows["bronze.divipola"] == 65
    assert summary.gold_rows > 0
    assert summary.sivigila_origin in {"SINTETICO", "INS"}
    assert {r.name for r in summary.exports} == {
        "weekly_dengue_signal.parquet",
        "weekly_dengue_signal.csv",
    }


def test_gold_has_one_row_per_entity_and_week(ready_warehouse: Warehouse) -> None:
    _, con = ready_warehouse
    gold = con.sql(f"SELECT * FROM {quality.GOLD_TABLE}").pl()
    keys = ["territorial_entity", "epi_year", "epi_week"]
    assert gold.select(keys).n_unique() == gold.height
    assert gold["territorial_entity"].n_unique() == 5
    assert gold.height == 5 * gold.select("epi_year", "epi_week").n_unique()


def test_bulletin_values_reach_gold(ready_warehouse: Warehouse) -> None:
    _, con = ready_warehouse
    values = dict(
        con.execute(
            f"""
            SELECT territorial_entity || '-' || epi_week, bulletin_cumulative_cases
            FROM {quality.GOLD_TABLE}
            WHERE epi_year = 2026 AND bulletin_cumulative_cases IS NOT NULL
            """
        ).fetchall()
    )
    assert values["Santiago de Cali-26"] == 793
    assert values["Santiago de Cali-27"] == 824
    assert values["Barranquilla-27"] == 1814
    assert values["Valle del Cauca-26"] == 895
    assert len(values) == 10  # 5 entities x 2 bulletins


def test_gold_cases_match_silver(ready_warehouse: Warehouse) -> None:
    _, con = ready_warehouse
    in_gold = _scalar(con, f"SELECT sum(sivigila_cases) FROM {quality.GOLD_TABLE}")
    in_silver = _scalar(con, "SELECT sum(cases) FROM silver.sivigila_weekly_cases")
    valid = _scalar(
        con,
        """
        SELECT count(*) FROM silver.sivigila_cases
        WHERE event_code IN ('210', '220') AND adjustment NOT IN ('6', 'D')
        """,
    )
    assert in_gold == in_silver == valid


def test_leading_zeros_preserve_cali_and_atlantico(ready_warehouse: Warehouse) -> None:
    _, con = ready_warehouse
    missing_entity = _scalar(
        con,
        """
        SELECT count(*) FROM silver.sivigila_cases AS c
        LEFT JOIN silver.municipality_entity AS m ON c.municipality_code = m.municipality_code
        WHERE m.territorial_entity IS NULL
        """,
    )
    assert missing_entity == 0
    assert (
        _scalar(con, "SELECT count(*) FROM silver.sivigila_cases WHERE municipality_code = '08001'")
        > 0
    )


def test_districts_are_separate_from_departments(ready_warehouse: Warehouse) -> None:
    _, con = ready_warehouse
    entity = dict(
        con.execute(
            "SELECT municipality_code, territorial_entity FROM silver.municipality_entity "
            "WHERE municipality_code IN ('76001', '76520', '08001', '08758')"
        ).fetchall()
    )
    assert entity == {
        "76001": "Santiago de Cali",
        "76520": "Valle del Cauca",
        "08001": "Barranquilla",
        "08758": "Atlántico",
    }


def test_aliases_match_all_stations_to_municipalities(ready_warehouse: Warehouse) -> None:
    _, con = ready_warehouse
    assert (
        _scalar(
            con,
            "SELECT count(*) FROM silver.ideam_daily_precipitation WHERE municipality_code IS NULL",
        )
        == 0
    )
    assert (
        _scalar(
            con,
            "SELECT count(DISTINCT station_code) FROM silver.ideam_daily_precipitation "
            "WHERE municipality_code = '76001'",
        )
        >= 1
    )


def test_suspicious_days_are_flagged_not_removed(ready_warehouse: Warehouse) -> None:
    _, con = ready_warehouse
    bronze_total = _scalar(con, "SELECT count(*) FROM bronze.ideam_daily_precipitation")
    silver_total = _scalar(con, "SELECT count(*) FROM silver.ideam_daily_precipitation")
    assert bronze_total == silver_total
    assert (
        _scalar(
            con, "SELECT count(*) FROM silver.ideam_daily_precipitation WHERE suspicious_reading"
        )
        > 0
    )


def test_exports_gold(ready_warehouse: Warehouse) -> None:
    paths, con = ready_warehouse
    exported = pl.read_parquet(paths.gold / "weekly_dengue_signal.parquet")
    assert exported.height == warehouse.count_rows(con, quality.GOLD_TABLE)


def test_exports_gold_to_path_with_apostrophe_spaces_and_accents(
    ready_warehouse: Warehouse, tmp_path: Path
) -> None:
    """Home folders such as ``C:\\Users\\María D'Costa`` must not break the export SQL."""
    _, con = ready_warehouse
    directory = tmp_path / "María D'Costa" / "gold dir"
    outputs = export_gold(con, directory)
    assert [p.name for p in outputs] == ["weekly_dengue_signal.parquet", "weekly_dengue_signal.csv"]
    exported = pl.read_parquet(directory / "weekly_dengue_signal.parquet")
    assert exported.height == warehouse.count_rows(con, quality.GOLD_TABLE)


def test_committed_snapshot_is_current(repo_paths: Paths, tmp_paths: Paths) -> None:
    """The committed gold Parquet used by the notebook must match pipeline output."""
    run_pipeline(tmp_paths)
    new = pl.read_parquet(tmp_paths.gold / "weekly_dengue_signal.parquet")
    committed = pl.read_parquet(repo_paths.gold / "weekly_dengue_signal.parquet")
    assert new.equals(committed), "Run `make pipeline` and commit data/gold/*.parquet"


def test_missing_sivigila_has_clear_error(tmp_paths: Paths) -> None:
    tmp_paths.sivigila_pilot.unlink()
    with pytest.raises(FileNotFoundError, match="prepare-sivigila"):
        run_pipeline(tmp_paths)


def test_sivigila_dates_are_parsed(ready_warehouse: Warehouse) -> None:
    """Every notification and symptom-onset date in the source must reach silver."""
    _, con = ready_warehouse
    unparsed = _scalar(
        con,
        """
        SELECT count(*) FROM silver.sivigila_cases
        WHERE notification_date IS NULL OR symptom_onset_date IS NULL
        """,
    )
    assert unparsed == 0


def test_unparsed_dates_raise_a_warning(ready_warehouse: Warehouse) -> None:
    _, con = ready_warehouse
    assert quality.sivigila_dates_parsed(con).ok
    con.execute("UPDATE silver.sivigila_cases SET notification_date = NULL")
    result = quality.sivigila_dates_parsed(con)
    assert not result.ok
    assert not result.critical  # gold does not use the dates, so the pipeline can continue
    assert "fec_not" in result.details


def test_checks_detect_duplicates(ready_warehouse: Warehouse) -> None:
    _, con = ready_warehouse
    con.execute(f"INSERT INTO {quality.GOLD_TABLE} SELECT * FROM {quality.GOLD_TABLE} LIMIT 1")
    result = quality.unique_key(con)
    assert not result.ok
    assert quality.has_errors([result])
    assert str(result).startswith("❌")


def test_warnings_are_not_errors() -> None:
    warning = quality.CheckResult("x", ok=False, details="y", critical=False)
    assert not quality.has_errors([warning])
    assert str(warning).startswith("⚠️")
