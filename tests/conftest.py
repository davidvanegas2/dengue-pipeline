"""Shared test fixtures."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from dengue_pipeline.config import Paths

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def repo_paths() -> Paths:
    """Return read-only paths to the real repository."""
    return Paths.from_root(REPO_ROOT)


@pytest.fixture
def tmp_paths(tmp_path: Path) -> Paths:
    """Copy data and SQL into an isolated repository for pipeline tests."""
    for directory in ("data/raw", "data/reference", "sql"):
        shutil.copytree(REPO_ROOT / directory, tmp_path / directory)
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'copy'\n", encoding="utf-8")
    return Paths.from_root(tmp_path)


@pytest.fixture(scope="session")
def bulletin_26(repo_paths: Paths) -> Path:
    return repo_paths.bulletins / "extracto_bes_2026_s26.pdf"


@pytest.fixture(scope="session")
def bulletin_27(repo_paths: Paths) -> Path:
    return repo_paths.bulletins / "extracto_bes_2026_s27.pdf"
