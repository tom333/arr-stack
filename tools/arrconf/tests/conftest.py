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


# ---------------------------------------------------------------------------
# Phase 5 fixtures — qBittorrent reconciler + Sonarr/Radarr split
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Phase 7 — Jellyfin fixtures (D-07-INSTANCE-01).
# ---------------------------------------------------------------------------


@pytest.fixture
def jellyfin_library_virtualfolders_fixture() -> list[dict[str, Any]]:
    """Jellyfin GET /Library/VirtualFolders response (2 libraries — Séries + Films).

    Shape: bare list (NO pagination wrapper). Each library has `Name` (match key
    per D-07-LIB-01 — Plan 07-04 reconciler matches by Name, NOT ItemId),
    `CollectionType` (out of scope D-07-LIB-02 — read-only), `LibraryOptions.PathInfos[].Path`
    (the source-of-truth set Pitfall 2 idempotence shim uses), and `Locations`
    (display projection, Pitfall 8 — reconciler IGNORES this field).
    """
    return _load_fixture("jellyfin/library_virtualfolders.json")


@pytest.fixture
def jellyfin_users_fixture() -> list[dict[str, Any]]:
    """Jellyfin GET /Users response (2 users — admin moi + restricted emilie).

    Shape: bare list (NO pagination). admin user matched by Name="moi" → Id
    82fd95db72904569b08d83271823ceaa (D-07-USERS-01 single-user scope). emilie
    present in baseline for operator-managed-coverage proof but Plan 07-04
    reconciler test asserts emilie is NEVER touched (`prune=False` hardcoded).
    """
    return _load_fixture("jellyfin/users.json")


@pytest.fixture
def jellyfin_user_moi_full_fixture() -> dict[str, Any]:
    """Jellyfin GET /Users/{id} response for moi — full Policy block.

    Shape: single dict (Jellyfin's per-user endpoint returns one user, not a list).
    Critical: `Policy.AuthenticationProviderId` and `Policy.PasswordResetProviderId`
    are set to the Jellyfin default class names. Plan 07-04 reconciler test
    asserts these 2 values appear VERBATIM in the POST body (Pitfall 6 / D-06-OPENAPI-01
    carry-forward — pydantic-excluded fields re-injected from this exact GET response).
    """
    return _load_fixture("jellyfin/user_moi_full.json")


@pytest.fixture
def jellyfin_system_configuration_fixture() -> dict[str, Any]:
    """Jellyfin GET /System/Configuration response (56-field body baseline).

    Pitfall 1 contract: POST /System/Configuration is FULL REPLACE. Plan 07-04
    reconciler test mocks this GET, builds a merged body (cluster GET + 7-field
    allowlist override from YAML), and asserts the POST body contains BOTH the
    7 allowlist overrides AND the 49 non-allowlist cluster fields preserved.
    DO NOT shrink this fixture — the 49 non-allowlist fields are load-bearing
    for the preservation test.
    """
    return _load_fixture("jellyfin/system_configuration.json")


@pytest.fixture
def jellyfin_plugins_fixture() -> list[dict[str, Any]]:
    """Jellyfin GET /Plugins response (6 plugins baseline — all Status=Active).

    Shape: bare list. Each plugin has `Name`, `Id`, `Version`, `Status`, `CanUninstall`.
    Plan 07-04 reconciler tests MUTATE a copy of this fixture (e.g. flip TMDb
    Status to "Disabled") to assert the Enable POST goes to the right URL
    with the right version (Pitfall 5 — `/Plugins/{id}/{version}/Enable`,
    NOT `/Plugins/{id}/Enable`).
    """
    return _load_fixture("jellyfin/plugins.json")
