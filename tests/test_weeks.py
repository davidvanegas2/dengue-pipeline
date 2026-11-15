from datetime import date, timedelta

import duckdb
import pytest
from epiweeks import Week

from dengue_pipeline.config import Paths
from dengue_pipeline.transform import register_macros
from dengue_pipeline.weeks import (
    epidemiological_week,
    week_start,
    week_start_date,
    weeks_in_year,
)


@pytest.mark.parametrize(
    ("day_date", "expected"),
    [
        # Dates printed in INS bulletins
        (date(2026, 6, 28), (2026, 26)),  # Epidemiological week 26: June 28 through July 4
        (date(2026, 7, 4), (2026, 26)),
        (date(2026, 7, 5), (2026, 27)),  # July 5 through July 11, 2026
        (date(2026, 7, 11), (2026, 27)),
        # Year boundaries
        (date(2026, 1, 1), (2025, 53)),
        (date(2026, 1, 4), (2026, 1)),
        (date(2024, 1, 1), (2024, 1)),
        (date(2023, 12, 31), (2024, 1)),
    ],
)
def test_epidemiological_week_matches_ins(day_date: date, expected: tuple[int, int]) -> None:
    assert epidemiological_week(day_date) == expected


def test_matches_epiweeks_over_twenty_years() -> None:
    """Compare every date against the reference CDC/MMWR implementation."""
    day = date(2007, 1, 1)
    while day <= date(2027, 12, 31):
        week = Week.fromdate(day, system="cdc")
        assert epidemiological_week(day) == (week.year, week.week), day
        day += timedelta(days=1)


def test_week_starts_on_sunday() -> None:
    assert week_start(date(2026, 11, 14)).weekday() == 6  # Sunday
    assert week_start(date(2026, 11, 15)) == date(2026, 11, 15)


@pytest.mark.parametrize(("year", "weeks"), [(2024, 52), (2025, 53), (2026, 52)])
def test_weeks_in_year(year: int, weeks: int) -> None:
    assert weeks_in_year(year) == weeks


def test_week_start_date_is_inverse() -> None:
    for year in (2024, 2025, 2026):
        for week in range(1, weeks_in_year(year) + 1):
            assert epidemiological_week(week_start_date(year, week)) == (year, week)


def test_week_start_date_rejects_nonexistent_weeks() -> None:
    with pytest.raises(ValueError, match="has no week 53"):
        week_start_date(2024, 53)


def test_sql_macros_match_python(repo_paths: Paths) -> None:
    con = duckdb.connect()
    register_macros(con, repo_paths.sql)
    rows = con.execute(
        """
        SELECT CAST(d AS DATE), epi_year(d), epi_week(d), epi_week_start(d)
        FROM unnest(generate_series(TIMESTAMP '2019-12-01', TIMESTAMP '2027-01-31', INTERVAL 1 DAY))
            AS t(d)
        """
    ).fetchall()
    assert len(rows) > 2500
    for day, year, week, start in rows:
        assert (year, week) == epidemiological_week(day), day
        assert start == week_start(day), day


def test_duckdb_week_is_not_epidemiological_week() -> None:
    """Document the trap: week() follows ISO weeks from Monday to Sunday."""
    con = duckdb.connect()
    iso_week = con.execute("SELECT week(DATE '2026-06-29')").fetchall()[0][0]
    assert iso_week == 27
    assert epidemiological_week(date(2026, 6, 29)) == (2026, 26)
