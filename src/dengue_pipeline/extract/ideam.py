"""Download IDEAM observations through the datos.gov.co Socrata / SoQL API.

Aggregate rainfall by station and day on the server, requesting one month
at a time. Preserve the bundled raw-cache schema, including its Spanish fields.

Department capitalization changed in 2026, so queries include name variants.
Stations may report excessive readings or rainfall and use municipality names
without DIVIPOLA codes. The silver layer handles matching and flags outliers.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import polars as pl

from dengue_pipeline.config import SOCRATA_BASE
from dengue_pipeline.text import strip_accents

log = logging.getLogger(__name__)

COLUMNS = (
    "codigoestacion",
    "nombreestacion",
    "departamento",
    "municipio",
    "latitud",
    "longitud",
    "fecha",
    "precipitacion_mm",
    "n_lecturas",
)

JsonOpener = Callable[[str, float], Any]


@dataclass(frozen=True)
class IdeamQuery:
    dataset_id: str
    departments: tuple[str, ...]
    start_date: date
    end_date: date


def name_variants(name: str) -> list[str]:
    """Return spelling variants used for a department in IDEAM data.

    >>> name_variants("Atlántico")
    ['ATLANTICO', 'ATLÁNTICO', 'Atlantico', 'Atlántico']
    """
    base = {name, strip_accents(name)}
    return sorted({form for b in base for form in (b.upper(), b.title())})


def build_params(query: IdeamQuery, *, limit: int = 50_000, offset: int = 0) -> dict[str, str]:
    """Build SoQL daily station aggregation filtered by dates and departments."""
    names = sorted({v for d in query.departments for v in name_variants(d)})
    name_list = ", ".join("'" + n.replace("'", "''") + "'" for n in names)
    return {
        "$select": (
            "codigoestacion, nombreestacion, departamento, municipio, latitud, longitud, "
            "date_trunc_ymd(fechaobservacion) AS fecha, "
            "sum(valorobservado) AS precipitacion_mm, count(*) AS n_lecturas"
        ),
        "$where": (
            f"fechaobservacion between '{query.start_date.isoformat()}T00:00:00' "
            f"and '{query.end_date.isoformat()}T23:59:59' AND departamento in ({name_list})"
        ),
        "$group": (
            "codigoestacion, nombreestacion, departamento, municipio, latitud, longitud, fecha"
        ),
        "$order": "fecha, codigoestacion",
        "$limit": str(limit),
        "$offset": str(offset),
    }


def query_url(query: IdeamQuery, **kwargs: int) -> str:
    params = build_params(query, **kwargs)
    return f"{SOCRATA_BASE}/{query.dataset_id}.json?{urllib.parse.urlencode(params)}"


def _open_json(url: str, timeout: float) -> Any:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def download(
    query: IdeamQuery,
    *,
    opener: JsonOpener = _open_json,
    limit: int = 50_000,
    timeout: float = 170.0,
    retries: int = 3,
    retry_delay: float = 5.0,
) -> list[dict[str, Any]]:
    """Download all query pages with retries."""
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        url = query_url(query, limit=limit, offset=offset)
        for attempt in range(1, retries + 1):
            try:
                page = opener(url, timeout)
                break
            except (OSError, TimeoutError) as error:
                if attempt == retries:
                    raise
                log.warning("Attempt %s failed (%s); retrying in %ss", attempt, error, retry_delay)
                time.sleep(retry_delay)
        rows.extend(page)
        if len(page) < limit:
            return rows
        offset += limit


def monthly_ranges(start_date: date, end_date: date) -> list[tuple[date, date]]:
    """Split a date range into calendar-month intervals.

    >>> monthly_ranges(date(2026, 1, 15), date(2026, 3, 2))[0]
    (datetime.date(2026, 1, 15), datetime.date(2026, 1, 31))
    """
    if end_date < start_date:
        raise ValueError("'end_date' must be on or after 'start_date'.")
    ranges = []
    start = start_date
    while start <= end_date:
        next_month_start = (start.replace(day=1) + timedelta(days=32)).replace(day=1)
        end = min(next_month_start - timedelta(days=1), end_date)
        ranges.append((start, end))
        start = end + timedelta(days=1)
    return ranges


def download_daily_precipitation(
    dataset_id: str,
    departments: Iterable[str],
    start_date: date,
    end_date: date,
    *,
    opener: JsonOpener = _open_json,
) -> pl.DataFrame:
    """Return daily station rainfall with every bronze column stored as text."""
    rows: list[dict[str, Any]] = []
    for start, end in monthly_ranges(start_date, end_date):
        query = IdeamQuery(dataset_id, tuple(departments), start, end)
        batch = download(query, opener=opener)
        log.info("IDEAM %s to %s: %s rows", start, end, len(batch))
        rows.extend(batch)
    records = [{c: _to_text(f.get(c)) for c in COLUMNS} for f in rows]
    return pl.DataFrame(records, schema=dict.fromkeys(COLUMNS, pl.Utf8))


def _to_text(value: Any) -> str | None:
    return None if value is None else str(value)
