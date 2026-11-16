"""Run workshop notebooks end to end without opening a browser.

Simulate a student solving TODOs one at a time and verify that checkpoints
pass at the intended step.
"""

from __future__ import annotations

import base64
import importlib.util
import io
import shutil
import sys
import urllib.request
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import polars as pl
import pypdfium2 as pdfium
import pytest

from dengue_pipeline.config import Paths

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_sivigila_sample as sample  # noqa: E402
import generate_student_notebook as generator  # noqa: E402

pytestmark = pytest.mark.slow

CHECKPOINTS = ("todo1_ok", "checkpoint_1", "checkpoint_2", "checkpoint_3")
GOLD = ROOT / "data" / "gold" / "weekly_dengue_signal.parquet"
REPO_URL_LINE = 'REPO_URL = "https://raw.githubusercontent.com/davidvanegas2/dengue-pipeline/main"'
OFFICIAL_DOWNLOAD = "Descargar tabla oficial para ML"

TODO4_STUB = (
    "precipitation_mm AS mean_precipitation_mm,\n"
    "               1 AS stations_with_data\n"
    "        FROM silver.entity_daily_rainfall"
)

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
    # Same result as the repository: weekly total per station, averaged over stations.
    "todo4": [
        (
            "SELECT territorial_entity,\n"
            "               epi_year(observation_date) AS epi_year, "
            "epi_week(observation_date) AS epi_week,\n"
            "               " + TODO4_STUB,
            "WITH per_station AS (\n"
            "            SELECT territorial_entity, station_code,\n"
            "                   epi_year(observation_date) AS epi_year,\n"
            "                   epi_week(observation_date) AS epi_week,\n"
            "                   sum(precipitation_mm) AS mm\n"
            "            FROM silver.entity_daily_rainfall\n"
            "            GROUP BY ALL\n"
            "        )\n"
            "        SELECT territorial_entity, epi_year, epi_week,\n"
            "               round(avg(mm), 2) AS mean_precipitation_mm,\n"
            "               count(*) AS stations_with_data\n"
            "        FROM per_station\n"
            "        GROUP BY ALL",
        )
    ],
    # Right grain, different quantity: the mean daily rainfall (mm/day).
    "todo4_daily_mean": [
        (
            TODO4_STUB,
            "avg(precipitation_mm) AS mean_precipitation_mm,\n"
            "               count(DISTINCT station_code) AS stations_with_data\n"
            "        FROM silver.entity_daily_rainfall\n"
            "        GROUP BY ALL",
        )
    ],
    # Right grain, but summing every station (DECIMAL in DuckDB) and counting station-days.
    "todo4_sum": [
        (
            TODO4_STUB,
            "sum(precipitation_mm) AS mean_precipitation_mm,\n"
            "               count(*) AS stations_with_data\n"
            "        FROM silver.entity_daily_rainfall\n"
            "        GROUP BY ALL",
        )
    ],
    # Not a TODO: turn on the municipality-alias switch in section 5.
    "aliases": [('mo.ui.switch(label="Usar', 'mo.ui.switch(value=True, label="Usar')],
}

TODOS = ("todo1", "todo2", "todo3", "todo4")


def run_app(
    path: Path, monkeypatch: pytest.MonkeyPatch, *, data_root: Path = ROOT
) -> tuple[Sequence[Any], dict[str, Any]]:
    """Run a marimo notebook as a script and return its cell outputs and global definitions."""
    monkeypatch.setenv("DENGUE_REPO_ROOT", str(data_root))
    spec = importlib.util.spec_from_file_location(f"nb_{path.stem}", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    outputs, definitions = module.app.run()
    return outputs, dict(definitions)


def run_notebook(
    path: Path, monkeypatch: pytest.MonkeyPatch, *, data_root: Path = ROOT
) -> dict[str, Any]:
    """Run a marimo notebook as a script and return its global definitions."""
    return run_app(path, monkeypatch, data_root=data_root)[1]


def html_outputs(outputs: Sequence[Any], marker: str) -> list[str]:
    """Return the rendered HTML of every cell output that contains ``marker``."""
    return [o.text for o in outputs if marker in getattr(o, "text", "")]


def assert_ml_contract(export: bytes) -> None:
    """The official ML table is the committed gold snapshot: 750 rows x 13 columns."""
    table = pl.read_parquet(io.BytesIO(export))
    assert table.shape == (750, 13)
    assert table.select("territorial_entity", "epi_year", "epi_week").n_unique() == 750


def lag_section(outputs: Sequence[Any]) -> str:
    """Return the rendered output of the rainfall-lag cell (Incógnita 4)."""
    (section,) = html_outputs(outputs, "Incógnita 4")
    return section


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
    rendered, definitions = run_app(ROOT / "notebooks" / "workshop_facilitator.py", monkeypatch)
    assert status(definitions) == dict.fromkeys(CHECKPOINTS, True)
    assert definitions["gold"].height == 750
    assert definitions["cases_match"] is True
    assert_ml_contract(definitions["ml_export"])
    assert definitions["gold"].schema == definitions["final_gold"].schema
    assert (
        definitions["missing_municipalities"].height == 2
    )  # CALI and BUGA, until aliases are enabled
    # Without aliases, Cali and the Buga station have no rainfall.
    assert definitions["gold_matches_repo"] is False
    assert definitions["gold_mismatches"] == ["stations", "rainfall"]
    # Cali has no rainfall to correlate; the lag section says how to fix it.
    assert "interruptor de alias" in lag_section(rendered)


@pytest.mark.parametrize("variant", ["facilitator", "student"])
def test_solved_notebooks_support_synthetic_dates(
    variant: str, notebook_paths: Paths, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = sample.generate(notebook_paths)
    notebook = (
        ROOT / "notebooks" / "workshop_facilitator.py"
        if variant == "facilitator"
        else student_with(tmp_path, *TODOS)
    )
    definitions = run_notebook(notebook, monkeypatch, data_root=notebook_paths.root)
    assert definitions["SIVIGILA_ORIGIN"] == "SINTETICO"
    assert definitions["cases_by_department"]["with_valid_date"].sum() == rows
    assert status(definitions) == dict.fromkeys(CHECKPOINTS, True)
    assert definitions["gold"].height == 750
    assert "cases" in definitions["gold_mismatches"]  # the snapshot uses INS cases


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
    outputs, definitions = run_app(student_with(tmp_path), monkeypatch)
    assert definitions["todo1_ok"] is False
    assert definitions["checkpoint_1"] is False
    assert definitions["checkpoint_2"] is False
    assert "checkpoint_3" not in definitions
    # The official ML table must not depend on the exercises: section 1 and the end of
    # section 6 offer it even when no TODO is solved.
    assert_ml_contract(definitions["ml_export"])
    buttons = html_outputs(outputs, OFFICIAL_DOWNLOAD)
    assert len(buttons) == 2
    # Headless runs embed download data as base64: both buttons must carry the gold bytes.
    gold_base64 = base64.b64encode(GOLD.read_bytes()).decode()
    assert all(gold_base64 in button for button in buttons)
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
        (TODOS, {"checkpoint_3": True}),
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


@pytest.mark.parametrize(
    ("selection", "filename", "cover_page", "page_number"),
    [
        ("Semana 26 (28 jun – 4 jul 2026)", "extracto_bes_2026_s26.pdf", False, 3),
        ("Semana 27 (5 – 11 jul 2026)", "extracto_bes_2026_s27.pdf", False, 3),
        # Both real extracts have the table on page 3. A blank cover page moves it to
        # page 4, so a hard-coded page number cannot pass this case.
        ("Semana 26 (28 jun – 4 jul 2026)", "extracto_bes_2026_s26.pdf", True, 4),
    ],
)
def test_pdf_viewer_opens_on_the_table_page(
    selection: str,
    filename: str,
    cover_page: bool,
    page_number: int,
    notebook_paths: Paths,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bulletin = notebook_paths.bulletins / filename
    if cover_page:
        pdf = pdfium.PdfDocument(bulletin.read_bytes())
        width, height = pdf[0].get_size()
        pdf.new_page(width, height, index=0)
        pdf.save(bulletin)
        pdf.close()
    notebook = _modified_facilitator(
        tmp_path,
        [('value="Semana 26 (28 jun – 4 jul 2026)"', f'value="{selection}"')],
    )
    outputs, definitions = run_app(notebook, monkeypatch, data_root=notebook_paths.root)
    assert definitions["checkpoint_1"] is True
    assert definitions["bulletin_page"] == page_number
    # Check the rendered iframe, not the arguments: mo.pdf silently drops initial_page
    # unless src is a URL. Headless runs embed the PDF as a data URL; a marimo server
    # serves the same bytes as ./@file/<size>-<name>.pdf.
    (viewer,) = html_outputs(outputs, "<iframe")
    assert base64.b64encode(bulletin.read_bytes()).decode() in viewer
    assert f"#page={page_number}&view=FitV" in viewer


@pytest.mark.parametrize("online", [True, False], ids=["online", "offline"])
def test_notebook_outside_the_repository_refreshes_its_downloads(
    online: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Simulate molab: no data next to the notebook, so every file comes from REPO_URL."""
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    cache = home / ".cache" / "dengue-workshop"
    cached_gold = cache / GOLD.relative_to(ROOT)
    if online:
        # A copy left by an earlier session must be replaced, not served as the ML table.
        cached_gold.parent.mkdir(parents=True)
        cached_gold.write_bytes(b"stale")
        source = ROOT
    else:
        # Without a connection, the last complete copies are reused.
        for directory in ("data/raw", "data/reference", "data/gold"):
            shutil.copytree(ROOT / directory, cache / directory)
        source = tmp_path / "unreachable"
    # An earlier session was interrupted mid-download: its partial file is never served.
    partial = cached_gold.with_name(cached_gold.name + ".part")
    partial.write_bytes(GOLD.read_bytes()[:100])
    requested: list[str] = []
    original_urlopen = urllib.request.urlopen

    def counting_urlopen(url: str, *args: Any, **kwargs: Any) -> Any:
        requested.append(url)
        return original_urlopen(url, *args, **kwargs)

    monkeypatch.setattr(urllib.request, "urlopen", counting_urlopen)
    notebook = _modified_facilitator(tmp_path, [(REPO_URL_LINE, f'REPO_URL = "{source.as_uri()}"')])
    empty_root = tmp_path / "empty"
    empty_root.mkdir()
    definitions = run_notebook(notebook, monkeypatch, data_root=empty_root)
    assert status(definitions) == dict.fromkeys(CHECKPOINTS, True)
    assert definitions["ml_export"] == GOLD.read_bytes()
    assert cached_gold.read_bytes() == GOLD.read_bytes()
    assert not list(cache.rglob("*.part"))
    # Each of the 9 workshop files is requested once per session, although the notebook
    # asks for some of them (the bulletins) several times.
    assert len(requested) == len(set(requested)) == 9
    warned = "no se pudo actualizar" in capsys.readouterr().out
    assert warned is not online


def test_case_comparison_reports_a_missing_entity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An entity missing from the exercise table must not count as matching case counts."""
    notebook = _modified_facilitator(
        tmp_path,
        [
            (
                "FROM bronze.entities AS e CROSS JOIN weeks AS s",
                "FROM bronze.entities AS e CROSS JOIN weeks AS s "
                "WHERE e.entidad_territorial <> 'Buenaventura'",
            )
        ],
    )
    definitions = run_notebook(notebook, monkeypatch)
    assert definitions["checkpoint_3"] is True  # 4 entities x 150 weeks, no duplicates
    assert definitions["gold"].height == 600
    assert definitions["cases_match"] is False


def test_reveal_button_and_aliases_enabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate the Reveal button and the municipality-alias switch."""
    path = _modified_facilitator(
        tmp_path,
        [
            ("not reveal.value", "False"),
            ('mo.ui.switch(label="Usar', 'mo.ui.switch(value=True, label="Usar'),
        ],
    )
    rendered, definitions = run_app(path, monkeypatch)
    assert definitions["missing_municipalities"].is_empty()  # aliases allow Cali to match
    assert definitions["checkpoint_3"] is True
    assert definitions["gold_matches_repo"] is True
    assert definitions["gold_mismatches"] == []
    assert "interruptor de alias" not in lag_section(rendered)  # every entity has rainfall


def test_student_solution_matches_repository_gold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    definitions = run_notebook(student_with(tmp_path, *TODOS, "aliases"), monkeypatch)
    assert status(definitions) == dict.fromkeys(CHECKPOINTS, True)
    assert definitions["gold"].schema == definitions["final_gold"].schema
    assert definitions["gold_mismatches"] == []
    assert definitions["gold_matches_repo"] is True


@pytest.mark.parametrize(
    ("todo4", "mismatches"),
    [("todo4_daily_mean", ["rainfall"]), ("todo4_sum", ["stations", "rainfall"])],
)
def test_other_todo4_answers_report_what_differs(
    todo4: str, mismatches: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A different aggregation keeps the grain but must say which columns differ."""
    path = student_with(tmp_path, "todo1", "todo2", "todo3", todo4, "aliases")
    rendered, definitions = run_app(path, monkeypatch)
    assert definitions["checkpoint_3"] is True
    # sum() over DECIMAL stays DECIMAL; gold casts it so the charts and the parquet work.
    assert definitions["gold"].schema == definitions["final_gold"].schema
    assert definitions["gold_mismatches"] == mismatches
    assert definitions["gold_matches_repo"] is False
    assert html_outputs(rendered, "Incógnita 2")  # the chart cell ran


@pytest.mark.network
def test_live_api_button(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = _modified_facilitator(tmp_path, [("not api_button.value", "False")])
    definitions = run_notebook(path, monkeypatch)
    assert definitions["checkpoint_3"] is True


def test_student_notebook_is_current() -> None:
    assert generator.main(["--check"]) == 0


def test_student_notebook_has_no_solutions() -> None:
    """Help accordions give hints, never an answer students can paste."""
    student = (ROOT / "notebooks" / "workshop.py").read_text(encoding="utf-8")
    assert "SOLUTION" not in student
    assert "STUDENT" not in student
    # The TODO 2 help names within_bbox on purpose; nothing before it may.
    assert "within_bbox" not in student.split("💡 Ayuda para el TODO 2")[0]
    facilitator = (ROOT / "notebooks" / "workshop_facilitator.py").read_text(encoding="utf-8")
    student_any_quotes = student.replace("'", '"')
    for answer in (
        'text.replace(",", ".")',  # TODO 1
        "try_strptime(split_part(",  # TODO 3
        "sum(precipitation_mm)",  # TODO 4
        "count(DISTINCT station_code) AS stations_with_data",  # TODO 4
    ):
        assert answer in facilitator  # the check below is not vacuous
        assert answer not in student_any_quotes, answer


def _student_with_edits(tmp_path: Path, todos: Sequence[str], edits: list[tuple[str, str]]) -> Path:
    """Solve some TODOs, then apply extra edits (wrong answers, widget defaults)."""
    path = student_with(tmp_path, *todos)
    code = path.read_text(encoding="utf-8")
    for original, new in edits:
        assert original in code, original
        code = code.replace(original, new)
    path.write_text(code, encoding="utf-8")
    return path


def test_checkpoint_1_validates_both_bulletins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Week 27 survives .crop(), so selecting it must not hide the rows lost in week 26."""
    notebook = _student_with_edits(
        tmp_path,
        ["todo1"],
        [('value="Semana 26 (28 jun – 4 jul 2026)"', 'value="Semana 27 (5 – 11 jul 2026)"')],
    )
    definitions = run_notebook(notebook, monkeypatch)
    assert definitions["bulletin_table"].height == 39  # the selected week reads fine
    assert definitions["checkpoint_1"] is False
    assert "bronze_bulletin" not in definitions
