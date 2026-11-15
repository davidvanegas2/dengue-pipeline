from pathlib import Path
from typing import Any

import pytest

from dengue_pipeline.extract import bulletin
from dengue_pipeline.extract.bulletin import (
    TableNotFoundError,
    extract_bulletins,
    extract_dengue_table,
    parse_row,
)


class TestParseRow:
    def test_normal_row(self) -> None:
        row = parse_row("Norte de Santander 3 428 38,4 1,7 511 521")
        assert row is not None
        assert row.territorial_entity == "Norte de Santander"
        assert row.total_cases == 3428
        assert row.warning_signs_pct == pytest.approx(38.4)
        assert row.severe_pct == pytest.approx(1.7)
        assert row.raw_variation == "511 521"

    def test_split_number_is_preserved_raw(self) -> None:
        """Keep the split "20 79" raw instead of guessing that it means 2079."""
        row = parse_row("Meta 9 504 30,3 0,9 2 139 20 79")
        assert row is not None
        assert row.total_cases == 9504
        assert row.raw_variation == "2 139 20 79"

    def test_total(self) -> None:
        row = parse_row("Total 56 797 38,7 1,0 9 665 10 062")
        assert row is not None
        assert row.is_total
        assert row.total_cases == 56797

    def test_accented_names(self) -> None:
        row = parse_row("Archipiélago de San Andrés 9 22,2 0,0 2 3")
        assert row is not None
        assert row.territorial_entity == "Archipiélago de San Andrés"

    @pytest.mark.parametrize(
        "line",
        [
            "Fuente: Sivigila, Instituto Nacional de Salud, Colombia, 2026",
            "28",
            "Colombia, a semana epidemiológica 26 de 2026",
            # A stray letter from the neighboring column makes this an invalid row.
            "Putumayo 318 24,8 1,3 48 66 e",
            "",
        ],
    )
    def test_non_row_lines(self, line: str) -> None:
        assert parse_row(line) is None


@pytest.mark.parametrize(
    ("fixture", "week", "page", "total", "cali", "barranquilla"),
    [
        ("bulletin_26", 26, 3, 56_797, 793, 1_728),
        ("bulletin_27", 27, 3, 59_262, 824, 1_814),
    ],
)
def test_extracts_real_table(
    request: pytest.FixtureRequest,
    fixture: str,
    week: int,
    page: int,
    total: int,
    cali: int,
    barranquilla: int,
) -> None:
    table = extract_dengue_table(request.getfixturevalue(fixture))
    by_name = {f.territorial_entity: f for f in table.rows}

    assert (table.year, table.week, table.page) == (2026, week, page)
    assert len(table.rows) == 39  # 37 entities + Exterior + Total
    assert table.reported_total == total
    assert table.totals_match(), "Entity cases must match the Total row"
    assert by_name["Santiago de Cali"].total_cases == cali
    assert by_name["Barranquilla"].total_cases == barranquilla


def test_table_changes_sides_between_weeks(bulletin_26: Path, bulletin_27: Path) -> None:
    """Extract both the left-hand week 26 table and the right-hand week 27 table."""
    import pdfplumber

    sides = []
    for path in (bulletin_26, bulletin_27):
        with pdfplumber.open(path) as pdf:
            _, page, title = bulletin._find_page(pdf)
            sides.append("left" if title["x0"] < page.width / 2 else "right")
    assert sides == ["left", "right"]


def test_crop_loses_rows_but_within_bbox_does_not(bulletin_26: Path) -> None:
    """Regression for stray letters from the adjacent page column."""
    import pdfplumber

    with pdfplumber.open(bulletin_26) as pdf:
        _, page, title = bulletin._find_page(pdf)
        half = page.width / 2
        bbox = (0, title["top"] - 2, half, page.height)
        with_crop = [parse_row(line) for line in page.crop(bbox).extract_text().splitlines()]
        with_within = [
            parse_row(line) for line in page.within_bbox(bbox).extract_text().splitlines()
        ]
    crop_rows = [f for f in with_crop if f]
    within_rows = [f for f in with_within if f]
    assert len(within_rows) == 39
    assert len(crop_rows) < len(within_rows)
    lost = sum(f.total_cases for f in within_rows if not f.is_total) - sum(
        f.total_cases for f in crop_rows if not f.is_total
    )
    assert lost == 733  # Putumayo + Quindío + Caldas + Risaralda


def test_to_dataframe(bulletin_27: Path) -> None:
    data = extract_dengue_table(bulletin_27).to_dataframe()
    assert data.height == 39
    assert set(data.columns) >= {
        "bulletin_year",
        "bulletin_week",
        "territorial_entity",
        "total_cases",
        "is_total",
    }
    assert data.filter(data["is_total"]).height == 1


def test_extract_bulletins_concatenates_tables(bulletin_26: Path, bulletin_27: Path) -> None:
    data = extract_bulletins([bulletin_27, bulletin_26])
    assert data.height == 78
    assert sorted(data["bulletin_week"].unique().to_list()) == [26, 27]


def test_extract_bulletins_without_files() -> None:
    with pytest.raises(FileNotFoundError):
        extract_bulletins([])


class _FakePage:
    def search(self, _pattern: Any) -> list[dict[str, Any]]:
        return []


class _FakePdf:
    pages = (_FakePage(), _FakePage())


def test_pdf_without_table() -> None:
    with pytest.raises(TableNotFoundError, match="Could not find the title"):
        bulletin._find_page(_FakePdf())
