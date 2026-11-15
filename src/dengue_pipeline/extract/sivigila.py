"""Read SIVIGILA microdata: individual dengue cases from closed reporting years.

Download files manually from the INS portal (see docs/fuentes.md). Preserve
source field names and read every column as text. This keeps leading zeros
available for the silver SQL layer to normalize.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

import polars as pl

REQUIRED_COLUMNS: tuple[str, ...] = ("cod_eve", "semana", "ano", "cod_dpto_o", "cod_mun_o")

USEFUL_COLUMNS: tuple[str, ...] = (
    *REQUIRED_COLUMNS,
    "fec_not",
    "ini_sin",
    "tip_cas",
    "pac_hos",
    "con_fin",
    "ajuste",
    "edad",
    "uni_med",
    "sexo",
    "cod_dpto_r",
    "cod_mun_r",
    "nombre_evento",
    "departamento_ocurrencia",
    "municipio_ocurrencia",
)

SUPPORTED_EXTENSIONS = (".csv", ".xlsx", ".xls", ".parquet")

SYNTHETIC_ORIGIN = "SINTETICO"
INS_ORIGIN = "INS"


class MissingColumnsError(ValueError):
    """The input lacks required SIVIGILA microdata columns."""


def normalize_code(value: str | None) -> str | None:
    """Clean Excel codes: "8.0" -> "8" and " 76 " -> "76". SQL adds leading zeros.

    >>> normalize_code("8.0"), normalize_code("076"), normalize_code(None)
    ('8', '076', None)
    """
    if value is None:
        return None
    cleaned = value.strip()
    if cleaned.endswith(".0"):
        cleaned = cleaned[:-2]
    return cleaned or None


def read_file(path: Path) -> pl.DataFrame:
    """Read all columns as text and lowercase source column names."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        data = pl.read_csv(path, infer_schema=False, encoding="utf8-lossy")
    elif suffix in {".xlsx", ".xls"}:
        data = pl.read_excel(path, engine="calamine", infer_schema_length=0)
    elif suffix == ".parquet":
        data = pl.read_parquet(path)
    else:
        raise ValueError(f"Unsupported format: {path.name}. Use {SUPPORTED_EXTENSIONS}.")

    data = data.rename({c: c.strip().lower() for c in data.columns})
    data = data.with_columns(pl.all().cast(pl.Utf8))
    missing = [c for c in REQUIRED_COLUMNS if c not in data.columns]
    if missing:
        raise MissingColumnsError(
            f"{path.name} does not look like SIVIGILA microdata; missing {missing}."
        )
    return data


def read_microdata(paths: Sequence[Path]) -> pl.DataFrame:
    """Combine files, retaining useful source columns and filename provenance."""
    if not paths:
        raise FileNotFoundError("No SIVIGILA files to read.")
    tables = []
    for path in sorted(paths):
        data = read_file(path)
        columns = [c for c in USEFUL_COLUMNS if c in data.columns]
        tables.append(data.select(columns).with_columns(pl.lit(path.name).alias("filename")))
    return pl.concat(tables, how="diagonal_relaxed")


def filter_departments(data: pl.DataFrame, department_codes: Iterable[str]) -> pl.DataFrame:
    """Keep cases occurring in the requested departments ("08" or "8")."""
    requested = {c.lstrip("0") for c in department_codes}
    code = pl.col("cod_dpto_o").map_elements(normalize_code, return_dtype=pl.Utf8)
    return data.filter(code.str.strip_chars_start("0").is_in(requested))


def prepare_pilot(
    downloaded_paths: Sequence[Path],
    output_path: Path,
    origin_path: Path,
    department_codes: Iterable[str],
) -> int:
    """Write the filtered pilot CSV and origin record; return the number of rows."""
    pilot = filter_departments(read_microdata(downloaded_paths), department_codes)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pilot.drop("filename").write_csv(output_path)
    names = ", ".join(sorted(r.name for r in downloaded_paths))
    origin_path.write_text(f"{INS_ORIGIN}\nFiles: {names}\n", encoding="utf-8")
    return pilot.height


def data_origin(origin_path: Path) -> str:
    """Read the SINTETICO, INS or DESCONOCIDO provenance label from ORIGEN.txt."""
    if not origin_path.is_file():
        return "DESCONOCIDO"
    first_line = origin_path.read_text(encoding="utf-8").splitlines()[:1]
    return first_line[0].strip().upper() if first_line else "DESCONOCIDO"
