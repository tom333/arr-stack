"""Shared pytest fixtures for arrconf tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURE_ROOT = Path(__file__).parent / "fixtures"


@pytest.fixture
def sonarr_downloadclient_fixture() -> list[dict[str, Any]]:
    """Sonarr GET /api/v3/downloadclient response (1 qBit client, redacted)."""
    return json.loads((FIXTURE_ROOT / "sonarr/downloadclient.json").read_text())


@pytest.fixture
def sonarr_tag_managed_fixture() -> list[dict[str, Any]]:
    """Sonarr GET /api/v3/tag with arrconf-managed tag at id=1."""
    return json.loads(
        (FIXTURE_ROOT / "sonarr/edge_cases/tag_with_arrconf_managed.json").read_text()
    )


@pytest.fixture
def sonarr_tag_empty_fixture() -> list[dict[str, Any]]:
    """Sonarr GET /api/v3/tag empty list (baseline)."""
    return json.loads((FIXTURE_ROOT / "sonarr/tag.json").read_text())


@pytest.fixture
def sonarr_base_url() -> str:
    return "http://sonarr.test"
