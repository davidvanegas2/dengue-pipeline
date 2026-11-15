"""Extract dengue tables from the INS weekly epidemiological bulletin (BES).

Find tables by title because their page and table numbers change each week.
Crop the correct half of the two-column page and parse Colombian number formats.
Preserve split expected/observed values such as "20 79" in raw_variation.

Downloading all bulletins, handling other layouts and deriving weekly counts
from cumulative cases remain workshop challenges (see RETOS.md).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pdfplumber
import polars as pl

from dengue_pipeline.text import parse_decimal, parse_integer

TABLE_TITLE = re.compile(r"Casos notificados de dengue por entidad territorial", re.IGNORECASE)
BULLETIN_WEEK = re.compile(
    r"a\s+semana\s+epidemiol[oó]gica\s+(\d{1,2})\s+de\s+(\d{4})", re.IGNORECASE
)
_NUMBER = r"\d{1,3}(?:[  ]\d{3})*"
_LETTERS = r"A-Za-zÁÉÍÓÚÜÑáéíóúüñ"
ROW = re.compile(
    rf"^(?P<entity>[{_LETTERS}][{_LETTERS}.,' ]*?)\s+"
    rf"(?P<cases>{_NUMBER})\s+"
    r"(?P<warning>\d{1,3},\d)\s+"
    r"(?P<severe>\d{1,3},\d)"
    r"(?P<remainder>(?:\s+[\d ]+)?)\s*$"
)


class TableNotFoundError(RuntimeError):
    """The PDF does not contain a dengue table by territorial entity."""


@dataclass(frozen=True)
class BulletinRow:
    territorial_entity: str
    total_cases: int
    warning_signs_pct: float
    severe_pct: float
    raw_variation: str

    @property
    def is_total(self) -> bool:
        return self.territorial_entity.strip().lower() == "total"


@dataclass(frozen=True)
class BulletinTable:
    filename: str
    page: int
    year: int
    week: int
    rows: tuple[BulletinRow, ...]

    @property
    def reported_total(self) -> int | None:
        """Return the value printed in the bulletin Total row."""
        return next((f.total_cases for f in self.rows if f.is_total), None)

    @property
    def entity_sum(self) -> int:
        return sum(f.total_cases for f in self.rows if not f.is_total)

    def totals_match(self) -> bool:
        """Check whether entity cases add up to the document total."""
        return self.reported_total == self.entity_sum

    def to_dataframe(self) -> pl.DataFrame:
        return pl.DataFrame(
            [
                {
                    "filename": self.filename,
                    "page": self.page,
                    "bulletin_year": self.year,
                    "bulletin_week": self.week,
                    "territorial_entity": f.territorial_entity,
                    "total_cases": f.total_cases,
                    "warning_signs_pct": f.warning_signs_pct,
                    "severe_pct": f.severe_pct,
                    "raw_variation": f.raw_variation,
                    "is_total": f.is_total,
                }
                for f in self.rows
            ]
        )


def parse_row(line: str) -> BulletinRow | None:
    """Parse a table row, or return None when the line does not match.

    >>> parse_row("Meta 9 504 30,3 0,9 2 139 20 79").total_cases
    9504
    >>> parse_row("Fuente: Sivigila, Instituto Nacional de Salud") is None
    True
    """
    match = ROW.match(line.strip())
    if match is None:
        return None
    return BulletinRow(
        territorial_entity=match["entity"].strip(),
        total_cases=parse_integer(match["cases"]),
        warning_signs_pct=parse_decimal(match["warning"]),
        severe_pct=parse_decimal(match["severe"]),
        raw_variation=match["remainder"].strip(),
    )


def _find_page(pdf: Any) -> tuple[int, Any, dict[str, Any]]:
    for index, page in enumerate(pdf.pages):
        results = page.search(TABLE_TITLE)
        if results:
            return index, page, results[0]
    raise TableNotFoundError(
        "Could not find the title 'Casos notificados de dengue por entidad territorial'."
    )


def crop_table_half(page: Any, title: dict[str, Any]) -> Any:
    """Keep the page column containing the table.

    Use within_bbox to exclude characters touching the boundary. crop would keep
    letters from the neighboring column, breaking rows such as
    "Putumayo 318 24,8 1,3 48 66 e".
    """
    half = page.width / 2
    x0, x1 = (0, half) if title["x0"] < half else (half, page.width)
    return page.within_bbox((x0, title["top"] - 2, x1, page.height))


def extract_dengue_table(pdf_path: Path | str) -> BulletinTable:
    """Extract dengue cases by territorial entity from one bulletin."""
    path = Path(pdf_path)
    with pdfplumber.open(path) as pdf:
        index, page, title = _find_page(pdf)
        text = crop_table_half(page, title).extract_text() or ""

    week_year = BULLETIN_WEEK.search(text)
    if week_year is None:
        raise TableNotFoundError(f"Could not find the epidemiological week in {path.name}.")

    rows: list[BulletinRow] = []
    for line in text.splitlines():
        row = parse_row(line)
        if row is None:
            continue
        rows.append(row)
        if row.is_total:
            break

    if not rows:
        raise TableNotFoundError(f"Found the title but no rows in {path.name}.")

    return BulletinTable(
        filename=path.name,
        page=index + 1,
        year=int(week_year.group(2)),
        week=int(week_year.group(1)),
        rows=tuple(rows),
    )


def extract_bulletins(paths: list[Path]) -> pl.DataFrame:
    """Extract and concatenate several bulletins into one long-form DataFrame."""
    if not paths:
        raise FileNotFoundError("No bulletin PDFs to process.")
    return pl.concat([extract_dengue_table(r).to_dataframe() for r in sorted(paths)])
