from pathlib import Path

import polars as pl
import pytest

from dengue_pipeline.config import Paths
from dengue_pipeline.extract.sivigila import (
    INS_ORIGIN,
    MissingColumnsError,
    data_origin,
    filter_departments,
    normalize_code,
    prepare_pilot,
    read_file,
    read_microdata,
)


def _microdata() -> pl.DataFrame:
    """Simulate a national download with uppercase fields and numeric codes."""
    return pl.DataFrame(
        {
            "CONSECUTIVE": [1, 2, 3, 4],
            "COD_EVE": [210, 210, 220, 210],
            "SEMANA": [5, 5, 6, 7],
            "ANO": [2025, 2025, 2025, 2025],
            "COD_DPTO_O": [8, 76, 5, 76],  # 5 = Antioquia, outside the pilot
            "COD_MUN_O": [1, 1, 1, 520],
            "AJUSTE": ["0", "6", "3", "0"],
            "Columna_Rara ": ["a", "b", "c", "d"],
        }
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [("8", "8"), ("8.0", "8"), (" 76 ", "76"), ("076", "076"), (None, None), ("", None)],
)
def test_normalize_code(value: str | None, expected: str | None) -> None:
    assert normalize_code(value) == expected


def test_read_csv_as_text_with_lowercase_columns(tmp_path: Path) -> None:
    path = tmp_path / "download.csv"
    _microdata().write_csv(path)
    data = read_file(path)
    assert "cod_dpto_o" in data.columns
    assert "columna_rara" in data.columns
    assert all(kind == pl.Utf8 for kind in data.dtypes)


def test_read_portal_excel_format(tmp_path: Path) -> None:
    path = tmp_path / "Datos_2025_210.xlsx"
    _microdata().write_excel(path)
    data = read_file(path)
    assert data.height == 4
    assert all(kind == pl.Utf8 for kind in data.dtypes)
    codes = {normalize_code(v) for v in data["cod_dpto_o"].to_list()}
    assert codes == {"8", "76", "5"}


def test_rejects_non_sivigila_file(tmp_path: Path) -> None:
    path = tmp_path / "other.csv"
    pl.DataFrame({"a": [1]}).write_csv(path)
    with pytest.raises(MissingColumnsError, match="missing"):
        read_file(path)


def test_unsupported_format(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported"):
        read_file(path)


def test_read_microdata_combines_years(tmp_path: Path) -> None:
    for year in (2024, 2025):
        _microdata().with_columns(pl.lit(year).alias("ANO")).write_csv(tmp_path / f"{year}.csv")
    data = read_microdata(sorted(tmp_path.glob("*.csv")))
    assert data.height == 8
    assert "columna_rara" not in data.columns  # only useful columns
    assert set(data["filename"].unique()) == {"2024.csv", "2025.csv"}


def test_read_microdata_without_files() -> None:
    with pytest.raises(FileNotFoundError):
        read_microdata([])


def test_filter_departments_accepts_padded_and_unpadded_codes() -> None:
    data = _microdata().rename(str.lower).with_columns(pl.all().cast(pl.Utf8))
    filtered = filter_departments(data, ["08", "76"])
    assert sorted(filtered["cod_dpto_o"].to_list()) == ["76", "76", "8"]


def test_prepare_pilot(tmp_path: Path) -> None:
    download = tmp_path / "Datos_2025_210.xlsx"
    _microdata().write_excel(download)
    output, origin = tmp_path / "pilot.csv", tmp_path / "ORIGEN.txt"

    rows = prepare_pilot([download], output, origin, ["76", "08"])

    assert rows == 3
    assert pl.read_csv(output, infer_schema=False).height == 3
    assert data_origin(origin) == INS_ORIGIN
    assert "Datos_2025_210.xlsx" in origin.read_text(encoding="utf-8")


def test_unknown_origin(tmp_path: Path) -> None:
    assert data_origin(tmp_path / "missing.txt") == "DESCONOCIDO"


def test_committed_sample_has_origin_label(repo_paths: Paths) -> None:
    """The origin file must say INS when real microdata replaces the sample."""
    origin = data_origin(repo_paths.sivigila_origin)
    assert origin in {"SINTETICO", "INS"}
    data = read_file(repo_paths.sivigila_pilot)
    assert set(data["cod_dpto_o"].map_elements(normalize_code, return_dtype=pl.Utf8)) <= {
        "8",
        "08",
        "76",
    }


def test_prepare_pilot_refuses_to_overwrite_with_zero_rows(tmp_path: Path) -> None:
    """A download without pilot rows must not replace the data or stamp it as INS."""
    download = tmp_path / "Datos_2025_210.xlsx"
    _microdata().write_excel(download)
    output, origin = tmp_path / "pilot.csv", tmp_path / "ORIGEN.txt"
    output.write_text("previous\n", encoding="utf-8")

    with pytest.raises(ValueError, match="pilot"):
        prepare_pilot([download], output, origin, ["99"])

    assert output.read_text(encoding="utf-8") == "previous\n"
    assert not origin.exists()
