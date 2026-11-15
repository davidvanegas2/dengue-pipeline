"""Generate a SYNTHETIC sample matching the SIVIGILA microdata format.

Real microdata must be downloaded manually from INS (see docs/fuentes.md).
This sample makes a fresh clone usable while preserving source quirks such as
missing leading zeros, discarded cases and different residence/occurrence codes.

These numbers are invented and unrelated to rainfall. Any apparent pattern is
noise. Replace the sample with ``dengue-pipeline prepare-sivigila <INS files>``.

Usage: ``uv run python scripts/generate_sivigila_sample.py``
"""

from __future__ import annotations

import csv
import math
import random
from datetime import timedelta
from pathlib import Path

from dengue_pipeline.config import Paths
from dengue_pipeline.extract.sivigila import SYNTHETIC_ORIGIN, USEFUL_COLUMNS
from dengue_pipeline.weeks import epidemiological_week, week_start_date, weeks_in_year

SEED = 2026
YEARS = {2024: 110.0, 2025: 70.0}  # mean weekly cases across the pilot

MUNICIPALITY_WEIGHTS = {
    "76001": 40,  # Santiago de Cali
    "08001": 25,  # Barranquilla
    "08758": 10,  # Soledad
    "76520": 6,  # Palmira
    "76834": 5,  # Tuluá
    "76364": 4,  # Jamundí
    "08433": 4,  # Malambo
    "76109": 3,  # Buenaventura
    "76111": 3,  # Guadalajara de Buga
    "76147": 3,  # Cartago
    "76892": 3,  # Yumbo
    "76130": 2,  # Candelaria (Valle)
    "08141": 1,  # Candelaria (Atlántico): same name, different department
}
DEFAULT_WEIGHT = 0.4

EVENTS = (
    ("210", "DENGUE", 0.955),
    ("220", "DENGUE GRAVE", 0.042),
    ("580", "MORTALIDAD POR DENGUE", 0.003),
)
ADJUSTMENTS = (("0", 0.55), ("3", 0.15), ("5", 0.10), ("6", 0.12), ("7", 0.07), ("D", 0.01))
CASE_TYPES = (("2", 0.60), ("3", 0.30), ("5", 0.10))


def _choose(rng: random.Random, options: tuple[tuple[str, float], ...]) -> str:
    values, weights = zip(*options, strict=True)
    return rng.choices(values, weights=weights, k=1)[0]


def _poisson(rng: random.Random, lam: float) -> int:
    """Use a normal approximation for large lambda and Knuth sampling otherwise."""
    if lam > 30:
        return max(0, round(rng.gauss(lam, math.sqrt(lam))))
    limit, k, p = math.exp(-lam), 0, 1.0
    while p > limit:
        k += 1
        p *= rng.random()
    return k - 1


def _municipalities(paths: Paths) -> tuple[list[dict[str, str]], list[float]]:
    with (paths.reference / "divipola_piloto.csv").open(encoding="utf-8") as filename:
        municipalities = list(csv.DictReader(filename))
    weights = [
        float(MUNICIPALITY_WEIGHTS.get(m["cod_mpio"], DEFAULT_WEIGHT)) for m in municipalities
    ]
    return municipalities, weights


def generate(paths: Paths, seed: int = SEED) -> int:
    rng = random.Random(seed)
    municipalities, weights = _municipalities(paths)
    rows: list[dict[str, str]] = []

    for year, base in YEARS.items():
        for week in range(1, weeks_in_year(year) + 1):
            seasonality = 1 + 0.6 * math.sin(2 * math.pi * (week - 10) / 52)
            for _ in range(_poisson(rng, base * seasonality)):
                municipality = rng.choices(municipalities, weights=weights, k=1)[0]
                event_code, event_name, _ = rng.choices(EVENTS, weights=[e[2] for e in EVENTS])[0]
                notification = week_start_date(year, week) + timedelta(days=rng.randint(0, 6))
                epi_year, epi_week = epidemiological_week(notification)
                department_code, municipality_code = (
                    municipality["cod_dpto"],
                    municipality["cod_mpio"],
                )
                lives_elsewhere = rng.random() < 0.03
                rows.append(
                    {
                        "cod_eve": event_code,
                        "semana": str(epi_week),
                        "ano": str(epi_year),
                        # Match source files: numeric codes without leading zeros.
                        "cod_dpto_o": str(int(department_code)),
                        "cod_mun_o": str(int(municipality_code[2:])),
                        "fec_not": notification.isoformat(),
                        "ini_sin": (notification - timedelta(days=rng.randint(0, 9))).isoformat(),
                        "tip_cas": _choose(rng, CASE_TYPES),
                        "pac_hos": "1" if rng.random() < 0.3 else "2",
                        "con_fin": "2" if event_code == "580" else "1",
                        "ajuste": _choose(rng, ADJUSTMENTS),
                        "edad": str(min(90, int(rng.expovariate(1 / 22)))),
                        "uni_med": "1",
                        "sexo": rng.choice("FM"),
                        "cod_dpto_r": "19" if lives_elsewhere else str(int(department_code)),
                        "cod_mun_r": "1" if lives_elsewhere else str(int(municipality_code[2:])),
                        "nombre_evento": event_name,
                        "departamento_ocurrencia": municipality["dpto"],
                        "municipio_ocurrencia": municipality["nom_mpio"],
                    }
                )

    paths.sivigila.mkdir(parents=True, exist_ok=True)
    with paths.sivigila_pilot.open("w", newline="", encoding="utf-8") as filename:
        writer = csv.DictWriter(filename, fieldnames=list(USEFUL_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)
    paths.sivigila_origin.write_text(
        f"{SYNTHETIC_ORIGIN}\n"
        "Sample generated by scripts/generate_sivigila_sample.py. These are NOT real data.\n",
        encoding="utf-8",
    )
    return len(rows)


def main() -> None:
    paths = Paths.from_root(Path(__file__).resolve().parents[1])
    rows = generate(paths)
    print(f"Synthetic sample: {rows:,} cases -> {paths.sivigila_pilot}")


if __name__ == "__main__":
    main()
