"""Tests for the student-notebook and synthetic-sample generators."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import polars as pl
import pytest

from dengue_pipeline.config import Paths
from dengue_pipeline.extract.sivigila import USEFUL_COLUMNS, data_origin

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import generate_sivigila_sample as sample
import generate_student_notebook as generator


class TestNotebookGenerator:
    def test_python_block(self) -> None:
        fuente = (
            "def f():\n"
            "    # >>> SOLUTION\n"
            "    return 1\n"
            "    # <<< SOLUTION\n"
            "    # >>> STUDENT\n"
            "    # # ✏️ TODO\n"
            "    # return None\n"
            "    # <<< STUDENT\n"
        )
        result = generator.generate(fuente)
        assert "return 1" not in result
        assert "    # ✏️ TODO\n    return None\n" in result

    def test_sql_block_preserves_indentation(self) -> None:
        fuente = (
            "x = '''\n"
            "    SELECT\n"
            "        -- >>> SOLUTION\n"
            "        lpad(a, 2, '0') AS a,\n"
            "        -- <<< SOLUTION\n"
            "        -- >>> STUDENT\n"
            "        -- a AS a,  -- ✏️ TODO\n"
            "        --\n"
            "        -- <<< STUDENT\n"
            "'''\n"
        )
        result = generator.generate(fuente)
        assert "        a AS a,  -- ✏️ TODO\n" in result
        assert "lpad" not in result

    @pytest.mark.parametrize(
        "fuente",
        [
            "# >>> SOLUTION\nx = 1\n",
            "# <<< SOLUTION\n",
            "# >>> SOLUTION\n# >>> STUDENT\n",
            "# >>> STUDENT\nuncommented = 1\n# <<< STUDENT\n",
        ],
    )
    def test_invalid_markers(self, fuente: str) -> None:
        with pytest.raises(generator.InvalidMarkersError):
            generator.generate(fuente)

    def test_generated_file_notice(self) -> None:
        result = generator.generate("# x\n\nimport marimo\n")
        assert "GENERATED FILE" in result


def test_generator_check_works_in_a_non_utf8_locale() -> None:
    """The notebook has emoji; piping it to ruff must not depend on the Windows code page."""
    env = {**os.environ, "LC_ALL": "C", "LANG": "C", "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0"}
    env.pop("PYTHONIOENCODING", None)
    process = subprocess.run(
        [sys.executable, str(generator.__file__), "--check"],
        capture_output=True,
        env=env,
        check=False,
    )
    assert process.returncode == 0, process.stderr.decode("utf-8", errors="replace")


class TestSyntheticSample:
    def test_sample_is_reproducible_and_labeled(self, tmp_paths: Paths) -> None:
        rows_1 = sample.generate(tmp_paths, seed=7)
        content_1 = tmp_paths.sivigila_pilot.read_bytes()
        rows_2 = sample.generate(tmp_paths, seed=7)
        assert rows_1 == rows_2
        assert content_1 == tmp_paths.sivigila_pilot.read_bytes()
        assert data_origin(tmp_paths.sivigila_origin) == "SINTETICO"

    def test_sample_has_sivigila_format(self, tmp_paths: Paths) -> None:
        sample.generate(tmp_paths)
        data = pl.read_csv(tmp_paths.sivigila_pilot, infer_schema=False)
        assert data.columns == list(USEFUL_COLUMNS)
        # Match source files: codes without leading zeros.
        assert "8" in data["cod_dpto_o"].to_list()
        assert "08" not in data["cod_dpto_o"].to_list()
        assert {"6", "D"} <= set(data["ajuste"].to_list())  # discarded cases must be filtered

    def test_committed_sample_matches_generator(self, repo_paths: Paths, tmp_paths: Paths) -> None:
        if data_origin(repo_paths.sivigila_origin) != "SINTETICO":
            pytest.skip("The repository already uses real INS data.")
        sample.generate(tmp_paths)
        assert tmp_paths.sivigila_pilot.read_bytes() == repo_paths.sivigila_pilot.read_bytes()
