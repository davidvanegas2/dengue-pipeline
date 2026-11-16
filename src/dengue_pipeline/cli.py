"""Command-line interface: ``uv run dengue-pipeline --help``."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from dengue_pipeline import quality, warehouse
from dengue_pipeline.config import PILOT_DEPARTMENTS, PILOT_START_DATE, Paths
from dengue_pipeline.extract import bulletin, sivigila
from dengue_pipeline.pipeline import download_ideam, run_pipeline


def _cmd_run(args: argparse.Namespace, paths: Paths) -> int:
    summary = run_pipeline(
        paths,
        database_path=args.db,
        refresh_ideam=args.refresh_ideam,
        export=not args.no_export,
    )
    print("\nBronze layer:")
    for table, rows in summary.bronze_rows.items():
        print(f"  {table:<40} {rows:>8,} rows")
    print(f"\nGold layer: {quality.GOLD_TABLE} -> {summary.gold_rows:,} rows")
    print(f"SIVIGILA origin: {summary.sivigila_origin}\n")
    for result in summary.checks:
        print(f"  {result}")
    for path in summary.exports:
        print(f"\nExported: {path.relative_to(paths.root)}")
    return 0 if summary.ok else 1


def _cmd_check(args: argparse.Namespace, paths: Paths) -> int:
    database_path = args.db or paths.database
    if not Path(database_path).is_file():
        print(f"Missing {database_path}. Run first: dengue-pipeline run", file=sys.stderr)
        return 2
    con = warehouse.connect(database_path)
    try:
        results = quality.run_checks(con)
    finally:
        con.close()
    for result in results:
        print(result)
    return 1 if quality.has_errors(results) else 0


def _cmd_prepare_sivigila(args: argparse.Namespace, paths: Paths) -> int:
    rows = sivigila.prepare_pilot(
        [Path(a) for a in args.files],
        paths.sivigila_pilot,
        paths.sivigila_origin,
        PILOT_DEPARTMENTS.keys(),
    )
    print(f"{rows:,} pilot cases saved to {paths.sivigila_pilot}")
    return 0


def _cmd_download_ideam(args: argparse.Namespace, paths: Paths) -> int:
    path = download_ideam(paths, start_date=args.start_date, end_date=args.end_date)
    print(f"Precipitation saved to {path}")
    return 0


def _cmd_bulletin(args: argparse.Namespace, _paths: Paths) -> int:
    table = bulletin.extract_dengue_table(args.pdf)
    print(f"{table.filename}: page {table.page}, week {table.week} of {table.year}")
    print(table.to_dataframe())
    status = "matches" if table.totals_match() else "DOES NOT match"
    print(f"Sum {table.entity_sum:,} vs Total {table.reported_total}: {status}")
    return 0 if table.totals_match() else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dengue-pipeline",
        description="Pilot pipeline: INS bulletins + SIVIGILA + IDEAM -> weekly gold table.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable detailed logging.")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run bronze -> silver -> gold -> quality checks.")
    run.add_argument("--db", type=Path, help="Optional DuckDB database path.")
    run.add_argument(
        "--refresh-ideam", action="store_true", help="Download IDEAM again (requires internet)."
    )
    run.add_argument("--no-export", action="store_true", help="Skip exports to data/gold/.")
    run.set_defaults(func=_cmd_run)

    check = sub.add_parser("check", help="Run quality checks against the warehouse.")
    check.add_argument("--db", type=Path)
    check.set_defaults(func=_cmd_check)

    prepare = sub.add_parser(
        "prepare-sivigila", help="Filter national SIVIGILA downloads to the pilot."
    )
    prepare.add_argument("files", nargs="+", help="Downloaded .xlsx/.csv files.")
    prepare.set_defaults(func=_cmd_prepare_sivigila)

    download = sub.add_parser("download-ideam", help="Download pilot precipitation.")
    download.add_argument("--start-date", type=date.fromisoformat, default=PILOT_START_DATE)
    download.add_argument("--end-date", type=date.fromisoformat, default=date.today())
    download.set_defaults(func=_cmd_download_ideam)

    read_bulletin = sub.add_parser("bulletin", help="Extract the dengue table from a PDF.")
    read_bulletin.add_argument("pdf", type=Path)
    read_bulletin.set_defaults(func=_cmd_bulletin)
    return parser


def _use_utf8_output() -> None:
    """Keep ✅, ⚠️ and table borders printable when stdout is not UTF-8.

    On Windows a piped or redirected stdout, Git Bash and some IDE panels default to cp1252,
    which made a successful run end in ``UnicodeEncodeError``.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: Sequence[str] | None = None) -> int:
    _use_utf8_output()
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    code: int = args.func(args, Paths.from_root())
    return code


if __name__ == "__main__":
    raise SystemExit(main())
