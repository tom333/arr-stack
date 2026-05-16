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


# ---------------------------------------------------------------------------
# Phase 5 fixtures — qBittorrent reconciler + Sonarr/Radarr split
# ---------------------------------------------------------------------------


@pytest.fixture
def qbit_categories_fixture() -> dict[str, Any]:
    """qBit GET /api/v2/torrents/categories — dict keyed by category name.

    Baseline: 3 pre-existing entries (cleanuparr-unlinked, radarr, sonarr)
    all with empty savePath (R-04 mitigation context — no per-category paths
    were configured before the Phase 5 reconciler runs).
    """
    return _load_fixture("qbittorrent/categories.json")


@pytest.fixture
def qbit_preferences_fixture() -> dict[str, Any]:
    """qBit GET /api/v2/app/preferences — singleton (trimmed to allowlist + peripheral keys).

    Allowlist keys (Q2 resolution): auto_tmm_enabled, category_changed_tmm_enabled,
    torrent_changed_tmm_enabled, save_path, temp_path.
    Peripheral keys for realism: locale, max_active_downloads, max_active_uploads,
    queueing_enabled.
    Sensitive fields (web_ui_password, web_ui_username, etc.) are intentionally omitted.
    """
    return _load_fixture("qbittorrent/preferences.json")


@pytest.fixture
def qbit_login_response_body() -> str:
    """Body fixture for qBit login success — single line 'Ok.' (no trailing newline).

    Used by respx login mocks per Pitfall 1 (qBit returns plain-text 'Ok.' on
    successful cookie-based auth, not JSON).
    """
    path = Path(__file__).parent / "fixtures" / "qbittorrent" / "auth_login_ok.txt"
    return path.read_text().rstrip("\n")


@pytest.fixture
def sonarr_series_with_no_tags_fixture() -> list[dict[str, Any]]:
    """Sonarr GET /api/v3/series — 8 series, all tags=[] (D-05-MIG-01 starting state).

    Baseline fixture representing the cluster state before the Phase 5 tag
    migration runs. All 8 series have no tags assigned.
    """
    return _load_fixture("sonarr/series_with_no_tags.json")


@pytest.fixture
def sonarr_series_with_tv_tag_fixture() -> list[dict[str, Any]]:
    """Sonarr GET /api/v3/series — 8 series, all tags=[<tv_id>] (D-05-MIG-01 idempotence proof).

    Edge case fixture: post-migration state where all series already have the
    'tv' tag assigned (id=2). Used to verify that re-running the reconciler
    does not emit redundant PUT calls.
    """
    return _load_fixture("sonarr/edge_cases/series_with_tv_tag.json")


@pytest.fixture
def sonarr_remotepathmapping_fixture() -> list[dict[str, Any]]:
    """Sonarr GET /api/v3/remotepathmapping — 1 existing entry mapping qBit's
    /data/complete/ to Sonarr's /data/torrents/complete/.

    Baseline: one remote path mapping already configured in cluster pointing
    qBittorrent's download path to Sonarr's import path.
    """
    return _load_fixture("sonarr/remotepathmapping.json")


@pytest.fixture
def radarr_movie_with_no_tags_fixture() -> list[dict[str, Any]]:
    """Radarr GET /api/v3/movie — 11 movies, all tags=[].

    Baseline fixture mirroring Sonarr's series_with_no_tags pattern but for
    the Radarr movie library. All 11 movies have no tags assigned.
    """
    return _load_fixture("radarr/movie_with_no_tags.json")


@pytest.fixture
def radarr_remotepathmapping_fixture() -> list[dict[str, Any]]:
    """Radarr GET /api/v3/remotepathmapping — 1 entry mirroring Sonarr.

    Baseline: same remote path mapping configuration as Sonarr — single entry
    pointing qBittorrent's complete path to Radarr's import path.
    """
    return _load_fixture("radarr/remotepathmapping.json")


# ---------------------------------------------------------------------------
# Phase 6 — Seerr fixtures (D-06-SCOPE-01).
# ---------------------------------------------------------------------------


@pytest.fixture
def seerr_settings_sonarr_fixture() -> list[dict[str, Any]]:
    """Seerr GET /api/v1/settings/sonarr response (1 default-true Sonarr service, redacted).

    Shape: list of service objects. Each has `id` (Plan 06-04 must NOT echo `id`
    in PUT body — Seerr returns 400 with `"request.body.id is read-only"`), `isDefault`
    (the match key — D-06-SCOPE-01 single-instance per ADR-7), `apiKey` (preserved
    via D-06-CREDS-01 manual pattern — Plan 06-04 must NOT overwrite if YAML omits it),
    `animeTags` + `activeAnimeDirectory` + `activeAnimeProfileId` (the D-06-Q10-01 anime
    routing fields — Sonarr-side ONLY).
    """
    return _load_fixture("seerr/settings_sonarr.json")


@pytest.fixture
def seerr_settings_radarr_fixture() -> list[dict[str, Any]]:
    """Seerr GET /api/v1/settings/radarr response (1 default-true Radarr service, redacted).

    Research-verified: NO `animeTags`, NO `activeAnimeDirectory`, NO `activeAnimeProfileId`
    on the Radarr-side service shape — anime/family routing for movies is handled
    entirely by Plan 06-05's content_tags step (D-06-Q10-01 + scope_directive #6).
    """
    return _load_fixture("seerr/settings_radarr.json")


@pytest.fixture
def seerr_user_fixture() -> dict[str, Any]:
    """Seerr GET /api/v1/user paginated response (1 admin user, permissions=2).

    Shape: `{pageInfo: {...}, results: [user]}`. The single admin user has
    permissions=2 (ADMIN in Seerr v3.2.0 fork — research-verified live; CONTEXT.md
    originally said 8388608, that is AUTO_REQUEST not full admin).
    """
    return _load_fixture("seerr/user.json")


@pytest.fixture
def seerr_settings_main_fixture() -> dict[str, Any]:
    """Seerr GET /api/v1/settings/main response (23-key body, apiKey REDACTED).

    Plan 06-04 reads the FULL body and modifies ONLY `defaultPermissions` +
    `defaultQuotas` before POSTing (Pitfall 2 — settings/main uses POST not PUT;
    D-06-SCOPE-01 scoped subset). All other 21 keys (locale/region/UI/mediaServer/etc.)
    flow through untouched. apiKey is excluded from POST body (Pitfall 1).
    """
    return _load_fixture("seerr/settings_main.json")
