"""Orchestrate bronze -> silver -> gold -> quality checks -> exports.

A production scheduler could call this weekly. The pilot exposes one function
that can run from the terminal, tests or a notebook.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import duckdb

from dengue_pipeline import quality, transform, warehouse
from dengue_pipeline.config import (
    IDEAM_DATASETS,
    PILOT_DEPARTMENTS,
    PILOT_START_DATE,
    Paths,
)
from dengue_pipeline.extract import bulletin, ideam, sivigila

log = logging.getLogger(__name__)


@dataclass
class PipelineSummary:
    bronze_rows: dict[str, int] = field(default_factory=dict)
    gold_rows: int = 0
    checks: list[quality.CheckResult] = field(default_factory=list)
    sivigila_origin: str = "DESCONOCIDO"
    exports: list[Path] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not quality.has_errors(self.checks)


def load_bronze(
    con: duckdb.DuckDBPyConnection, paths: Paths, *, refresh_ideam: bool = False
) -> dict[str, int]:
    """Extract each source into the bronze schema without transforming its fields."""
    rows: dict[str, int] = {}

    pdfs = sorted(paths.bulletins.glob("*.pdf"))
    rows["bronze.dengue_bulletin"] = warehouse.load_dataframe(
        con, "bronze.dengue_bulletin", bulletin.extract_bulletins(pdfs)
    )

    if not paths.sivigila_pilot.is_file():
        raise FileNotFoundError(
            f"Missing {paths.sivigila_pilot}. Download the microdata and run "
            "'dengue-pipeline prepare-sivigila <files>' (see docs/fuentes.md)."
        )
    rows["bronze.sivigila"] = warehouse.load_file(con, "bronze.sivigila", paths.sivigila_pilot)

    if refresh_ideam:
        download_ideam(paths, end_date=date.today())
    rows["bronze.ideam_daily_precipitation"] = warehouse.load_file(
        con, "bronze.ideam_daily_precipitation", paths.ideam_precipitation
    )

    references = {
        "bronze.divipola": "divipola_piloto.csv",
        "bronze.territorial_entities": "entidades_territoriales_piloto.csv",
        "bronze.ideam_municipality_aliases": "alias_municipios_ideam.csv",
    }
    for table, filename in references.items():
        rows[table] = warehouse.load_file(con, table, paths.reference / filename)
    return rows


def download_ideam(paths: Paths, *, start_date: date = PILOT_START_DATE, end_date: date) -> Path:
    """Download pilot precipitation again from datos.gov.co."""
    data = ideam.download_daily_precipitation(
        IDEAM_DATASETS["precipitation"], PILOT_DEPARTMENTS.values(), start_date, end_date
    )
    paths.ideam_precipitation.parent.mkdir(parents=True, exist_ok=True)
    data.write_parquet(paths.ideam_precipitation, compression="zstd")
    log.info("IDEAM saved to %s (%s rows)", paths.ideam_precipitation, data.height)
    return paths.ideam_precipitation


def export_gold(con: duckdb.DuckDBPyConnection, directory: Path) -> list[Path]:
    """Export gold as Parquet for ML and CSV for spreadsheet applications."""
    directory.mkdir(parents=True, exist_ok=True)
    outputs = []
    for extension, file_format in (("parquet", "PARQUET"), ("csv", "CSV, HEADER")):
        path = directory / f"weekly_dengue_signal.{extension}"
        con.execute(f"COPY {quality.GOLD_TABLE} TO '{path.as_posix()}' (FORMAT {file_format})")
        outputs.append(path)
    return outputs


def run_pipeline(
    paths: Paths,
    *,
    database_path: Path | None = None,
    refresh_ideam: bool = False,
    export: bool = True,
) -> PipelineSummary:
    summary = PipelineSummary(sivigila_origin=sivigila.data_origin(paths.sivigila_origin))
    if summary.sivigila_origin == sivigila.SYNTHETIC_ORIGIN:
        log.warning("⚠️  SIVIGILA: using the SYNTHETIC SAMPLE. Replace it with real data.")

    con = warehouse.connect(database_path if database_path is not None else paths.database)
    try:
        summary.bronze_rows = load_bronze(con, paths, refresh_ideam=refresh_ideam)
        transform.run_transformations(con, paths.sql)
        summary.gold_rows = warehouse.count_rows(con, quality.GOLD_TABLE)
        summary.checks = quality.run_checks(con)
        if export:
            summary.exports = export_gold(con, paths.gold)
    finally:
        con.close()
    return summary
