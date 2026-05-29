"""Shared pytest fixtures.

Pattern: every test that mutates arrconf.yml copies the canonical file to
a tmp_path and monkeypatches `arrconf_ui.locator.arrconf_yml_path` to point
at the copy. This guarantees tests NEVER touch the real
charts/arr-stack/files/arrconf.yml.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_ARRCONF_YML = REPO_ROOT / "charts" / "arr-stack" / "files" / "arrconf.yml"
CANONICAL_SCHEMA_JSON = REPO_ROOT / "schemas" / "arrconf-schema.json"
CANONICAL_CONFIGARR_YML = REPO_ROOT / "charts" / "arr-stack" / "files" / "configarr.yml"


@pytest.fixture
def sandboxed_arrconf_yml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Copy the canonical arrconf.yml to tmp_path; patch locator to return the copy."""
    target = tmp_path / "arrconf.yml"
    shutil.copy(CANONICAL_ARRCONF_YML, target)

    def fake_path() -> Path:
        return target

    # Patch the locator module's symbol used by io+app.
    monkeypatch.setattr("arrconf_ui.locator.arrconf_yml_path", fake_path)
    monkeypatch.setattr("arrconf_ui.app.arrconf_yml_path", fake_path)
    yield target


@pytest.fixture
def sandboxed_configarr_yml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Copy the canonical configarr.yml to tmp_path; patch locator to return the copy."""
    target = tmp_path / "configarr.yml"
    shutil.copy(CANONICAL_CONFIGARR_YML, target)

    def fake_path() -> Path:
        return target

    # Patch the locator module's symbol.
    monkeypatch.setattr("arrconf_ui.locator.configarr_yml_path", fake_path)
    # arrconf_ui.app may not yet re-export configarr_yml_path (added in Plan 03).
    # Use raising=False so this fixture works in both wave-1 (pre-Plan-03) and
    # wave-2 (post-Plan-03) contexts without modification.
    monkeypatch.setattr("arrconf_ui.app.configarr_yml_path", fake_path, raising=False)
    yield target


@pytest.fixture
def sandboxed_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Copy the canonical schema to tmp_path; patch locator."""
    target = tmp_path / "arrconf-schema.json"
    shutil.copy(CANONICAL_SCHEMA_JSON, target)
    monkeypatch.setattr("arrconf_ui.locator.schema_json_path", lambda: target)
    monkeypatch.setattr("arrconf_ui.app.schema_json_path", lambda: target)
    yield target
