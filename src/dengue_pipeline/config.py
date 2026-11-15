"""Central repository paths and pilot scope.

Keep processing scope here so adding departments, years or climate variables
requires configuration changes instead of changes to processing logic.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

# --- Pilot scope -------------------------------------------------------------

#: Pilot departments (DIVIPOLA code -> DANE name).
PILOT_DEPARTMENTS: dict[str, str] = {
    "76": "VALLE DEL CAUCA",
    "08": "ATLÁNTICO",
}

#: First day covered by the final table.
PILOT_START_DATE = date(2024, 1, 1)

# --- Sources -----------------------------------------------------------------

SOCRATA_BASE = "https://www.datos.gov.co/resource"

#: IDEAM datasets published on datos.gov.co (Socrata).
#: The pilot uses precipitation; temperature and humidity are workshop challenges.
IDEAM_DATASETS: dict[str, str] = {
    "precipitation": "s54a-sgyg",
    "temperature": "sbwg-7ju4",
    "humidity": "uext-mhny",
}

#: DIVIPOLA (DANE) dataset on datos.gov.co.
DIVIPOLA_DATASET = "gdxc-w37w"

#: Override the repository root through an environment variable (CI or Docker).
ROOT_ENV_VAR = "DENGUE_REPO_ROOT"


def find_root(start: Path | None = None) -> Path:
    """Find the repository root.

    Check DENGUE_REPO_ROOT first, then walk upward from ``start`` or the working
    directory looking for pyproject.toml and data/. Fall back to the package location.
    """
    if env := os.environ.get(ROOT_ENV_VAR):
        return Path(env).resolve()
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        if (directory / "pyproject.toml").is_file() and (directory / "data").is_dir():
            return directory
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Paths:
    """Standard project paths, all derived from the repository root."""

    root: Path

    @classmethod
    def from_root(cls, root: Path | None = None) -> Paths:
        return cls(root=(root or find_root()).resolve())

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def raw(self) -> Path:
        return self.data / "raw"

    @property
    def bulletins(self) -> Path:
        return self.raw / "boletines"

    @property
    def sivigila(self) -> Path:
        return self.raw / "sivigila"

    @property
    def ideam(self) -> Path:
        return self.raw / "ideam"

    @property
    def reference(self) -> Path:
        return self.data / "reference"

    @property
    def gold(self) -> Path:
        return self.data / "gold"

    @property
    def database(self) -> Path:
        return self.data / "dengue.duckdb"

    @property
    def sql(self) -> Path:
        return self.root / "sql"

    @property
    def ideam_precipitation(self) -> Path:
        return self.ideam / "precipitacion_diaria_piloto.parquet"

    @property
    def sivigila_pilot(self) -> Path:
        return self.sivigila / "sivigila_dengue_piloto.csv"

    @property
    def sivigila_origin(self) -> Path:
        return self.sivigila / "ORIGEN.txt"
