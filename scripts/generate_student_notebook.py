"""Generate notebooks/workshop.py from workshop_facilitator.py.

The facilitator notebook is the single source of truth. Blocks use SOLUTION
and STUDENT markers, prefixed with # in Python or -- in SQL::

    # >>> SOLUTION
    return int(text.replace(" ", ""))
    # <<< SOLUTION
    # >>> STUDENT
    # return None
    # <<< STUDENT

Remove SOLUTION blocks, uncomment STUDENT blocks by one level, and remove markers.

Usage::

    uv run python scripts/generate_student_notebook.py
    uv run python scripts/generate_student_notebook.py --check
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "notebooks" / "workshop_facilitator.py"
DESTINATION = ROOT / "notebooks" / "workshop.py"

_MARKER = re.compile(r"^\s*(?:#|--) (?P<dir>>>>|<<<) (?P<block>SOLUTION|STUDENT)\s*$")
_COMMENT = re.compile(r"^(?P<indent>\s*)(?:#|--)(?: (?P<remainder>.*))?$")

NOTICE = (
    "# GENERATED FILE by scripts/generate_student_notebook.py: DO NOT edit by hand.\n"
    "# Edit notebooks/workshop_facilitator.py and rerun this script.\n"
)


class InvalidMarkersError(ValueError):
    """A block marker is nested, unmatched or left open."""


def uncomment(line: str) -> str:
    """Remove one comment level while preserving indentation."""
    match = _COMMENT.match(line)
    if match is None:
        raise InvalidMarkersError(f"Uncommented line in STUDENT block: {line!r}")
    return match["indent"] + (match["remainder"] or "")


def generate(text: str) -> str:
    output: list[str] = []
    block: str | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        marker = _MARKER.match(line)
        if marker:
            if marker["dir"] == ">>>":
                if block is not None:
                    raise InvalidMarkersError(f"Line {number}: nested block.")
                block = marker["block"]
            else:
                if block != marker["block"]:
                    raise InvalidMarkersError(f"Line {number}: unexpected closing marker.")
                block = None
            continue
        if block == "SOLUTION":
            continue
        output.append(uncomment(line) if block == "STUDENT" else line)
    if block is not None:
        raise InvalidMarkersError(f"Block {block} was never closed.")

    result = "\n".join(output) + "\n"
    result = result.replace("\nimport marimo\n", f"\n{NOTICE}\nimport marimo\n", 1)
    return _format_code(result)


def _format_code(code: str) -> str:
    """Run ruff format so generated code follows repository formatting."""
    ruff = shutil.which("ruff")
    if ruff is None:
        return code
    process = subprocess.run(
        [ruff, "format", "--stdin-filename", str(DESTINATION), "-"],
        input=code,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        cwd=ROOT,
    )
    return process.stdout if process.returncode == 0 else code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="Fail when notebooks/workshop.py is out of date."
    )
    args = parser.parse_args(argv)

    expected = generate(SOURCE.read_text(encoding="utf-8"))
    if args.check:
        current = DESTINATION.read_text(encoding="utf-8") if DESTINATION.is_file() else ""
        if current != expected:
            print(
                "notebooks/workshop.py is out of date. Run: make student-notebook",
                file=sys.stderr,
            )
            return 1
        print("notebooks/workshop.py is up to date.")
        return 0

    DESTINATION.write_text(expected, encoding="utf-8")
    print(f"Generated {DESTINATION.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
