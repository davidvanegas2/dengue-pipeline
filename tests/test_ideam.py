import urllib.parse
from datetime import date
from typing import Any

import pytest

from dengue_pipeline.config import IDEAM_DATASETS
from dengue_pipeline.extract.ideam import (
    COLUMNS,
    IdeamQuery,
    build_params,
    download,
    download_daily_precipitation,
    monthly_ranges,
    name_variants,
    query_url,
)

QUERY = IdeamQuery("s54a-sgyg", ("VALLE DEL CAUCA",), date(2026, 1, 1), date(2026, 1, 31))


def test_variants_cover_actual_formats() -> None:
    """2025: 'VALLE DEL CAUCA', 'ATLANTICO'. 2026: 'Valle Del Cauca', 'Atlantico'."""
    assert {"VALLE DEL CAUCA", "Valle Del Cauca"} <= set(name_variants("VALLE DEL CAUCA"))
    assert {"ATLANTICO", "Atlantico", "ATLÁNTICO"} <= set(name_variants("ATLÁNTICO"))


def test_params_aggregate_on_server() -> None:
    params = build_params(QUERY)
    assert "sum(valorobservado)" in params["$select"]
    assert "date_trunc_ymd(fechaobservacion)" in params["$select"]
    assert "fecha" in params["$group"]
    assert "'2026-01-01T00:00:00'" in params["$where"]
    assert "'Valle Del Cauca'" in params["$where"]


def test_params_escape_quotes() -> None:
    query = IdeamQuery("x", ("O'Higgins",), date(2026, 1, 1), date(2026, 1, 2))
    assert "O''Higgins" in build_params(query)["$where"]


def test_query_url() -> None:
    url = query_url(QUERY, limit=10, offset=20)
    assert url.startswith("https://www.datos.gov.co/resource/s54a-sgyg.json?")
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert query["$limit"] == ["10"]
    assert query["$offset"] == ["20"]


def test_monthly_ranges() -> None:
    ranges = monthly_ranges(date(2025, 12, 15), date(2026, 2, 3))
    assert ranges == [
        (date(2025, 12, 15), date(2025, 12, 31)),
        (date(2026, 1, 1), date(2026, 1, 31)),
        (date(2026, 2, 1), date(2026, 2, 3)),
    ]


def test_reversed_date_range() -> None:
    with pytest.raises(ValueError, match="on or after"):
        monthly_ranges(date(2026, 2, 1), date(2026, 1, 1))


class _FakeApi:
    """Simulate Socrata pagination with total rows and limit rows per page."""

    def __init__(self, total: int, failures: int = 0) -> None:
        self.total, self.failures, self.calls = total, failures, 0

    def __call__(self, url: str, timeout: float) -> list[dict[str, Any]]:
        self.calls += 1
        if self.failures:
            self.failures -= 1
            raise TimeoutError("API request timed out")
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        limit, start_date = int(query["$limit"][0]), int(query["$offset"][0])
        end_date = min(start_date + limit, self.total)
        return [
            {"codigoestacion": str(i), "precipitacion_mm": "1.5", "n_lecturas": "144"}
            for i in range(start_date, end_date)
        ]


def test_download_paginates_to_end() -> None:
    api = _FakeApi(total=25)
    rows = download(QUERY, opener=api, limit=10)
    assert len(rows) == 25
    assert api.calls == 3


def test_download_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("dengue_pipeline.extract.ideam.time.sleep", lambda _s: None)
    api = _FakeApi(total=3, failures=2)
    assert len(download(QUERY, opener=api, limit=10, retries=3)) == 3


def test_download_exhausts_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("dengue_pipeline.extract.ideam.time.sleep", lambda _s: None)
    with pytest.raises(TimeoutError):
        download(QUERY, opener=_FakeApi(total=3, failures=5), retries=2)


def test_download_daily_precipitation_as_text() -> None:
    data = download_daily_precipitation(
        "s54a-sgyg", ["VALLE DEL CAUCA"], date(2026, 1, 1), date(2026, 2, 28), opener=_FakeApi(4)
    )
    assert data.columns == list(COLUMNS)
    assert data.height == 8  # 4 rows for each of the 2 monthly intervals
    assert data["precipitacion_mm"][0] == "1.5"


@pytest.mark.network
def test_live_api_responds() -> None:
    """Make a small live query to datos.gov.co; skip with -m "not network"."""
    data = download_daily_precipitation(
        IDEAM_DATASETS["precipitation"], ["ATLÁNTICO"], date(2026, 3, 1), date(2026, 3, 2)
    )
    assert data.height > 0
    assert set(data.columns) == set(COLUMNS)
