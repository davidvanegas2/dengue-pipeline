"""Epidemiological weeks using the INS MMWR calendar.

Weeks run from Sunday to Saturday. Week 1 contains at least four days of the
new year, so January 1, 2026 belongs to week 53 of 2025.
DuckDB's week() and isodow() follow ISO weeks instead. Equivalent MMWR SQL
macros live in sql/macros.sql.
"""

from __future__ import annotations

from datetime import date, timedelta


def week_start(day_date: date) -> date:
    """Return the Sunday starting the epidemiological week of ``day_date``."""
    days_since_sunday = (day_date.weekday() + 1) % 7  # weekday(): Monday=0 ... Sunday=6
    return day_date - timedelta(days=days_since_sunday)


def _first_week_start(year: int) -> date:
    """Return the Sunday starting week 1, which contains January 4."""
    return week_start(date(year, 1, 4))


def epidemiological_week(day_date: date) -> tuple[int, int]:
    """Return ``(epidemiological_year, week)`` for a date.

    >>> epidemiological_week(date(2026, 6, 28))
    (2026, 26)
    >>> epidemiological_week(date(2026, 1, 1))
    (2025, 53)
    """
    sunday = week_start(day_date)
    year = (sunday + timedelta(days=3)).year  # Wednesday determines the year
    week = (sunday - _first_week_start(year)).days // 7 + 1
    return year, week


def week_start_date(year: int, week: int) -> date:
    """Return the Sunday starting ``week`` of epidemiological ``year``.

    >>> week_start_date(2026, 26)
    datetime.date(2026, 6, 28)
    """
    if not 1 <= week <= weeks_in_year(year):
        raise ValueError(f"Epidemiological year {year} has no week {week}.")
    return _first_week_start(year) + timedelta(weeks=week - 1)


def weeks_in_year(year: int) -> int:
    """Return 52 or 53, depending on the epidemiological year."""
    return (_first_week_start(year + 1) - _first_week_start(year)).days // 7
