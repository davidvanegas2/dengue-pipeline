import os
import subprocess
import sys
from pathlib import Path

import polars as pl
import pytest

from dengue_pipeline.cli import build_parser, main
from dengue_pipeline.config import ROOT_ENV_VAR, Paths


@pytest.fixture
def isolated_repo(tmp_paths: Paths, monkeypatch: pytest.MonkeyPatch) -> Paths:
    monkeypatch.setenv(ROOT_ENV_VAR, str(tmp_paths.root))
    return tmp_paths


def test_help_lists_commands() -> None:
    help_text = build_parser().format_help()
    for command in ("run", "check", "prepare-sivigila", "download-ideam", "bulletin"):
        assert command in help_text


def test_bulletin_command(bulletin_27: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["bulletin", str(bulletin_27)]) == 0
    output = capsys.readouterr().out
    assert "week 27 of 2026" in output
    assert "matches" in output


def test_run_and_check(isolated_repo: Paths, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run"]) == 0
    output = capsys.readouterr().out
    assert "gold.weekly_dengue_signal" in output
    assert (isolated_repo.gold / "weekly_dengue_signal.parquet").is_file()

    assert main(["check"]) == 0
    assert "Unique key" in capsys.readouterr().out


def test_run_without_exports_in_another_warehouse(isolated_repo: Paths, tmp_path: Path) -> None:
    db = tmp_path / "other.duckdb"
    assert main(["run", "--db", str(db), "--no-export"]) == 0
    assert db.is_file()
    assert not (isolated_repo.gold / "weekly_dengue_signal.csv").exists()


def test_check_without_warehouse(isolated_repo: Paths, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check", "--db", str(isolated_repo.root / "missing.duckdb")]) == 2
    assert "Run first" in capsys.readouterr().err


def test_prepare_sivigila(isolated_repo: Paths, tmp_path: Path) -> None:
    download = tmp_path / "Datos_2025_210.csv"
    pl.DataFrame(
        {
            "COD_EVE": ["210", "210"],
            "SEMANA": ["1", "2"],
            "ANO": ["2025", "2025"],
            "COD_DPTO_O": ["76", "11"],
            "COD_MUN_O": ["1", "1"],
        }
    ).write_csv(download)
    assert main(["prepare-sivigila", str(download)]) == 0
    assert pl.read_csv(isolated_repo.sivigila_pilot).height == 1
    assert isolated_repo.sivigila_origin.read_text(encoding="utf-8").startswith("INS")


def test_cli_output_survives_a_cp1252_stdout(bulletin_27: Path) -> None:
    """Windows pipes, redirects and Git Bash use cp1252, which cannot encode ✅ or table borders."""
    env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
    process = subprocess.run(
        [sys.executable, "-m", "dengue_pipeline.cli", "bulletin", str(bulletin_27)],
        capture_output=True,
        env=env,
        check=False,
    )
    assert process.returncode == 0, process.stderr.decode("utf-8", errors="replace")
    output = process.stdout.decode("utf-8")
    assert "week 27 of 2026" in output
    assert "┌" in output  # polars table border, not encodable in cp1252
