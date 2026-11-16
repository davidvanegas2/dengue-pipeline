"""Run workshop notebooks end to end without opening a browser.

Simulate a student solving TODOs one at a time and verify that checkpoints
pass at the intended step.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path
from typing import Any

import polars as pl
import pytest

from dengue_pipeline.config import Paths

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_sivigila_sample as sample  # noqa: E402
import generate_student_notebook as generator  # noqa: E402

pytestmark = pytest.mark.slow

CHECKPOINTS = ("todo1_ok", "checkpoint_1", "checkpoint_2", "checkpoint_3")

# Student solutions for each TODO (exact replacements in workshop.py).
SOLUTIONS: dict[str, list[tuple[str, str]]] = {
    "todo1": [
        (
            "# ✏️ TODO 1a: remove spaces and convert to an integer with int()\n        return None",
            'return int(text.replace(" ", ""))',
        ),
        (
            "# ✏️ TODO 1b: replace the comma with a dot and convert with float()\n"
            "        return None",
            'return float(text.replace(",", "."))',
        ),
    ],
    "todo2": [("return page.crop(_bbox)", "return page.within_bbox(_bbox)")],
    "todo3": [
        (
            "try_cast(fec_not AS DATE) AS notification_date,",
            "coalesce(CAST(try_strptime(split_part(trim(fec_not), ' ', 1), '%d/%m/%Y') AS DATE), "
            "try_cast(split_part(trim(fec_not), ' ', 1) AS DATE)) AS notification_date,",
        )
    ],
    "todo4": [
        (
            "precipitation_mm AS rainfall_mm,\n"
            "               1 AS stations\n"
            "        FROM silver.entity_daily_rainfall",
            "avg(precipitation_mm) AS rainfall_mm,\n"
            "               count(DISTINCT station_code) AS stations\n"
            "        FROM silver.entity_daily_rainfall\n"
            "        GROUP BY ALL",
        )
    ],
}


def run_notebook(
    path: Path, monkeypatch: pytest.MonkeyPatch, *, data_root: Path = ROOT
) -> dict[str, Any]:
    """Run a marimo notebook as a script and return its global definitions."""
    monkeypatch.setenv("DENGUE_REPO_ROOT", str(data_root))
    spec = importlib.util.spec_from_file_location(f"nb_{path.stem}", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _outputs, definitions = module.app.run()
    return dict(definitions)


def student_with(tmp_path: Path, *todos: str) -> Path:
    code = (ROOT / "notebooks" / "workshop.py").read_text(encoding="utf-8")
    for todo in todos:
        for original, replacement in SOLUTIONS[todo]:
            assert original in code, f"Could not find {todo} text in workshop.py"
            code = code.replace(original, replacement)
    path = tmp_path / f"workshop_{'_'.join(todos) or 'initial'}.py"
    path.write_text(code, encoding="utf-8")
    return path


def status(definitions: dict[str, Any]) -> dict[str, Any]:
    return {c: definitions.get(c, "not executed") for c in CHECKPOINTS}


@pytest.fixture
def notebook_paths(tmp_paths: Paths) -> Paths:
    """Include the opening gold snapshot when testing modified notebook inputs."""
    shutil.copytree(ROOT / "data" / "gold", tmp_paths.gold)
    return tmp_paths


def test_facilitator_passes_all_checkpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    definitions = run_notebook(ROOT / "notebooks" / "workshop_facilitator.py", monkeypatch)
    assert status(definitions) == dict.fromkeys(CHECKPOINTS, True)
    assert definitions["gold"].height == 750
    assert (
        definitions["missing_municipalities"].height == 2
    )  # CALI and BUGA, until aliases are enabled


@pytest.mark.parametrize("variant", ["facilitator", "student"])
def test_solved_notebooks_support_synthetic_dates(
    variant: str, notebook_paths: Paths, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = sample.generate(notebook_paths)
    notebook = (
        ROOT / "notebooks" / "workshop_facilitator.py"
        if variant == "facilitator"
        else student_with(tmp_path, "todo1", "todo2", "todo3", "todo4")
    )
    definitions = run_notebook(notebook, monkeypatch, data_root=notebook_paths.root)
    assert definitions["SIVIGILA_ORIGIN"] == "SINTETICO"
    assert definitions["cases_by_department"]["with_valid_date"].sum() == rows
    assert status(definitions) == dict.fromkeys(CHECKPOINTS, True)
    assert definitions["gold"].height == 750


@pytest.mark.parametrize(
    ("column", "invalid_value", "valid_count", "percentage"),
    [
        ("fec_not", "not a date", "with_valid_date", "date_pct"),
        ("cod_mun_o", "999", "with_valid_municipality", "matched_pct"),
    ],
)
def test_checkpoint_rejects_one_invalid_record_despite_rounded_percentage(
    column: str,
    invalid_value: str,
    valid_count: str,
    percentage: str,
    notebook_paths: Paths,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = pl.read_csv(notebook_paths.sivigila_pilot, infer_schema=False)
    data = (
        data.with_row_index("row_number")
        .with_columns(
            pl.when(pl.col("row_number") == 0)
            .then(pl.lit(invalid_value))
            .otherwise(pl.col(column))
            .alias(column)
        )
        .drop("row_number")
    )
    data.write_csv(notebook_paths.sivigila_pilot)
    definitions = run_notebook(
        ROOT / "notebooks" / "workshop_facilitator.py",
        monkeypatch,
        data_root=notebook_paths.root,
    )
    by_department = definitions["cases_by_department"]
    assert by_department["cases"].sum() - by_department[valid_count].sum() == 1
    assert (by_department[percentage] == 100.0).all()
    assert definitions["checkpoint_2"] is False
    assert "gold" not in definitions
    assert "checkpoint_3" not in definitions


def test_initial_student_notebook_waits_for_todos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    definitions = run_notebook(student_with(tmp_path), monkeypatch)
    assert definitions["todo1_ok"] is False
    assert definitions["checkpoint_1"] is False
    assert definitions["checkpoint_2"] is False
    assert "checkpoint_3" not in definitions
    # Date trap: municipalities match, but try_cast leaves every date empty, silently.
    by_department = definitions["cases_by_department"]
    assert by_department["matched_pct"].to_list() == [100.0] * by_department.height
    assert by_department["date_pct"].to_list() == [0.0] * by_department.height


def test_todo1_reveals_cropping_trap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    definitions = run_notebook(student_with(tmp_path, "todo1"), monkeypatch)
    assert definitions["todo1_ok"] is True
    assert definitions["checkpoint_1"] is False  # .crop() loses 4 rows in week 26
    table = definitions["bulletin_table"]
    assert table.height == 35


def test_full_progression(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    progress = [
        (("todo1", "todo2"), {"checkpoint_1": True, "checkpoint_2": False}),
        (("todo1", "todo2", "todo3"), {"checkpoint_2": True, "checkpoint_3": False}),
        (("todo1", "todo2", "todo3", "todo4"), {"checkpoint_3": True}),
    ]
    for todos, expected in progress:
        definitions = run_notebook(student_with(tmp_path, *todos), monkeypatch)
        actual = {key: definitions.get(key) for key in expected}
        assert actual == expected, f"With {todos}: {status(definitions)}"


def _modified_facilitator(tmp_path: Path, replacements: list[tuple[str, str]]) -> Path:
    code = (ROOT / "notebooks" / "workshop_facilitator.py").read_text(encoding="utf-8")
    for original, new in replacements:
        assert original in code, original
        code = code.replace(original, new)
    path = tmp_path / "modified_facilitator.py"
    path.write_text(code, encoding="utf-8")
    return path


def test_reveal_button_and_aliases_enabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate the Reveal button and the municipality-alias switch."""
    path = _modified_facilitator(
        tmp_path,
        [
            ("not reveal.value", "False"),
            ('mo.ui.switch(label="Usar', 'mo.ui.switch(value=True, label="Usar'),
        ],
    )
    definitions = run_notebook(path, monkeypatch)
    assert definitions["missing_municipalities"].is_empty()  # aliases allow Cali to match
    assert definitions["checkpoint_3"] is True


@pytest.mark.network
def test_live_api_button(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = _modified_facilitator(tmp_path, [("not api_button.value", "False")])
    definitions = run_notebook(path, monkeypatch)
    assert definitions["checkpoint_3"] is True


def test_student_notebook_is_current() -> None:
    assert generator.main(["--check"]) == 0


def test_student_notebook_has_no_solutions() -> None:
    student = (ROOT / "notebooks" / "workshop.py").read_text(encoding="utf-8")
    assert "SOLUTION" not in student
    assert "STUDENT" not in student
    assert "within_bbox" not in student.split("💡 Ayuda para el TODO 2")[0]
    facilitator = (ROOT / "notebooks" / "workshop_facilitator.py").read_text(encoding="utf-8")
    assert "try_strptime(split_part(" in facilitator  # the check below is not vacuous
    assert "try_strptime(split_part(" not in student
