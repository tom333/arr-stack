"""Shared pytest fixtures for arrconf tests.

Fixture layout (WR-07 — Phase 3 code review clarification):

``fixtures/sonarr/`` carries the canonical "fresh-from-cluster" GET response
shapes (one file per endpoint, e.g. ``downloadclient.json``, ``tag.json``).
These are the baselines a real reconcile starts from.

``fixtures/sonarr/edge_cases/`` carries narrower scenarios that diverge from
the baseline — e.g. ``tag_with_arrconf_managed.json`` (cluster ALREADY has
the managed tag at id=1, used to assert idempotence of _ensure_managed_tag)
or ``downloadclient_with_unmanaged_tag.json`` (managed-tag protection at
prune time). The split keeps the "baseline" fixtures small (so a quick
read tells you what the API normally looks like) and isolates scenario
fixtures so a future contributor doesn't accidentally trample a
load-bearing fixture by editing it for a one-off test.

If you add a new fixture: pick the location based on intent (baseline →
top-level; scenario → edge_cases/). Reference it via ``_load_fixture`` so
a missing file emits a clear error.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURE_ROOT = Path(__file__).parent / "fixtures"


def _load_fixture(relative_path: str) -> Any:
    """Read a JSON fixture; raise a clear error if missing.

    Pre-fix (WR-07): a missing fixture surfaced as a confusing FileNotFoundError
    inside the fixture function. This helper surfaces the relative path and the
    fixture root, making the error message actionable.
    """
    p = FIXTURE_ROOT / relative_path
    if not p.exists():
        raise FileNotFoundError(
            f"Fixture missing: {relative_path!r} (resolved to {p}). "
            f"Available fixtures under {FIXTURE_ROOT} — check tests/conftest.py "
            "docstring for the canonical / edge_cases layout."
        )
    return json.loads(p.read_text())


@pytest.fixture
def sonarr_downloadclient_fixture() -> list[dict[str, Any]]:
    """Sonarr GET /api/v3/downloadclient response (1 qBit client, redacted)."""
    return _load_fixture("sonarr/downloadclient.json")


@pytest.fixture
def sonarr_tag_managed_fixture() -> list[dict[str, Any]]:
    """Sonarr GET /api/v3/tag with arrconf-managed tag at id=1.

    Lives under edge_cases/ because it's a scenario fixture (cluster ALREADY
    has the managed tag) — distinct from the empty baseline ``sonarr/tag.json``.
    """
    return _load_fixture("sonarr/edge_cases/tag_with_arrconf_managed.json")


@pytest.fixture
def sonarr_tag_empty_fixture() -> list[dict[str, Any]]:
    """Sonarr GET /api/v3/tag empty list (baseline — no managed tag yet)."""
    return _load_fixture("sonarr/tag.json")


@pytest.fixture
def sonarr_indexer_fixture() -> list[dict[str, Any]]:
    """Sonarr GET /api/v3/indexer (REDACTED apiKey values)."""
    return _load_fixture("sonarr/indexer.json")


@pytest.fixture
def sonarr_notification_fixture() -> list[dict[str, Any]]:
    """Sonarr GET /api/v3/notification (REDACTED apiKey/token values)."""
    return _load_fixture("sonarr/notification.json")


@pytest.fixture
def sonarr_rootfolder_fixture() -> list[dict[str, Any]]:
    """Sonarr GET /api/v3/rootfolder (no secrets — path-only)."""
    return _load_fixture("sonarr/rootfolder.json")


@pytest.fixture
def sonarr_hostconfig_fixture() -> dict[str, Any]:
    """Sonarr GET /api/v3/config/host (REDACTED apiKey/password)."""
    return _load_fixture("sonarr/config_host.json")


@pytest.fixture
def sonarr_base_url() -> str:
    return "http://sonarr.test"
