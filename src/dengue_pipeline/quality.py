"""Data quality checks.

Each check returns a CheckResult rather than raising an exception, so the CLI
and notebook can show all results together.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

GOLD_TABLE = "gold.weekly_dengue_signal"


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    details: str
    #: False turns a failed check into a warning so the pipeline can continue.
    critical: bool = True

    def __str__(self) -> str:
        icon = "✅" if self.ok else ("❌" if self.critical else "⚠️ ")
        return f"{icon} {self.name}: {self.details}"


def _scalar(con: duckdb.DuckDBPyConnection, sql: str) -> int:
    # Consume the complete result set before issuing another query.
    rows = con.execute(sql).fetchall()
    return int(rows[0][0]) if rows and rows[0][0] is not None else 0


def unique_key(con: duckdb.DuckDBPyConnection) -> CheckResult:
    duplicates = _scalar(
        con,
        f"""
        SELECT count(*) FROM (
            SELECT territorial_entity, epi_year, epi_week
            FROM {GOLD_TABLE}
            GROUP BY ALL HAVING count(*) > 1
        )
        """,
    )
    return CheckResult(
        "Unique key (entity, year, week)",
        duplicates == 0,
        "no duplicates" if duplicates == 0 else f"{duplicates} duplicate keys",
    )


def complete_entities(con: duckdb.DuckDBPyConnection) -> CheckResult:
    expected = _scalar(con, "SELECT count(*) FROM silver.territorial_entities")
    present = _scalar(con, f"SELECT count(DISTINCT territorial_entity) FROM {GOLD_TABLE}")
    return CheckResult(
        "All pilot entities",
        expected == present and expected > 0,
        f"{present} of {expected}",
    )


def continuous_weeks(con: duckdb.DuckDBPyConnection) -> CheckResult:
    gaps = _scalar(
        con,
        f"""
        SELECT count(*) FROM (
            SELECT
                week_start
                - lag(week_start) OVER (
                    PARTITION BY territorial_entity ORDER BY week_start
                ) AS gap
            FROM {GOLD_TABLE}
        )
        WHERE gap IS NOT NULL AND gap <> 7
        """,
    )
    return CheckResult(
        "Continuous weeks (no gaps in the spine)",
        gaps == 0,
        "ok" if gaps == 0 else f"{gaps} gaps",
    )


def nonnegative_precipitation(con: duckdb.DuckDBPyConnection) -> CheckResult:
    negatives = _scalar(con, f"SELECT count(*) FROM {GOLD_TABLE} WHERE mean_precipitation_mm < 0")
    return CheckResult("Precipitation >= 0", negatives == 0, f"{negatives} negative values")


def stations_without_municipality(con: duckdb.DuckDBPyConnection) -> CheckResult:
    """Find IDEAM stations whose municipality could not be matched to DIVIPOLA."""
    missing_codes = _scalar(
        con,
        """
        SELECT count(DISTINCT station_code)
        FROM silver.ideam_daily_precipitation
        WHERE municipality_code IS NULL
        """,
    )
    return CheckResult(
        "IDEAM stations with DIVIPOLA codes",
        missing_codes == 0,
        "all matched" if missing_codes == 0 else f"{missing_codes} stations without a municipality",
        critical=False,
    )


def suspicious_days(con: duckdb.DuckDBPyConnection) -> CheckResult:
    """Flag station days with more than 144 readings or 300 mm; keep all rows."""
    suspicious = _scalar(
        con, "SELECT count(*) FROM silver.ideam_daily_precipitation WHERE suspicious_reading"
    )
    total = _scalar(con, "SELECT count(*) FROM silver.ideam_daily_precipitation")
    return CheckResult(
        "Suspicious rainfall days (flagged, not filtered)",
        suspicious == 0,
        f"{suspicious} of {total} station days",
        critical=False,
    )


def bulletin_totals_match(con: duckdb.DuckDBPyConnection) -> CheckResult:
    """Check that entity cases sum to the printed Total row in each bulletin."""
    mismatches = _scalar(
        con,
        """
        SELECT count(*) FROM (
            SELECT
                filename,
                sum(total_cases) FILTER (WHERE NOT is_total) AS total_sum,
                max(total_cases) FILTER (WHERE is_total) AS total
            FROM bronze.dengue_bulletin
            GROUP BY filename
        )
        WHERE total_sum IS DISTINCT FROM total
        """,
    )
    return CheckResult(
        "Bulletins: entity sum = Total",
        mismatches == 0,
        "all match" if mismatches == 0 else f"{mismatches} bulletins do not match",
    )


CHECKS = (
    unique_key,
    complete_entities,
    continuous_weeks,
    nonnegative_precipitation,
    bulletin_totals_match,
    stations_without_municipality,
    suspicious_days,
)


def run_checks(con: duckdb.DuckDBPyConnection) -> list[CheckResult]:
    return [check(con) for check in CHECKS]


def has_errors(results: list[CheckResult]) -> bool:
    return any(r.critical and not r.ok for r in results)
