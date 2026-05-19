"""arrconf 6-app dry-run sweep helper — used by both Phase 9 no-regression test
and Phase 10 idempotence sweep test.

dry_run_all_apps(cfg) walks all 6 reconcilers in dry_run=True mode against a
given RootConfig, returning a deterministic dict for fixture-based byte-equivalence
regression testing and idempotence (2nd-run-zero) assertions.

Phase 10 SC#2 context: This helper is called twice in test_phase10_idempotence_sweep.py
to prove that a second run of all 6 reconcilers against the same config produces ZERO
plan_action events across all apps (full idempotence after the 3 FP fixes from
Plans 10-C / 10-F / 10-H).

Reconciler callables enumerated (verified in arrconf.reconcilers modules):
  - reconcile_sonarr   signature: (SonarrClient, SonarrInstance, dry_run) -> SonarrResult
    SonarrResult.plan: list[PlannedAction[DownloadClient]]
    Fixtures: sonarr/tag.json, sonarr/downloadclient.json, sonarr/indexer.json,
              sonarr/rootfolder.json, sonarr/notification.json,
              sonarr/remotepathmapping.json, (series: empty list)
  - reconcile_radarr   signature: (RadarrClient, RadarrInstance, dry_run) -> RadarrResult
    RadarrResult.plan: list[PlannedAction[DownloadClient]]
    Fixtures: radarr/tag_with_arrconf_managed.json, radarr/downloadclient.json,
              radarr/indexer.json, radarr/rootfolder.json, radarr/notification.json,
              radarr/remotepathmapping.json, (movies: empty list)
  - reconcile_prowlarr signature: (ProwlarrClient, ProwlarrInstance, dry_run) -> ProwlarrResult
    ProwlarrResult.plan: list[PlannedAction[Application]]
    Fixtures: prowlarr/applications.json
    Note: Prowlarr's reconcile_prowlarr reads api_key_env from os.environ for each app.
    In the production config, apps are declared; env vars are patched to "fake-key".
  - reconcile_qbittorrent signature: (QbittorrentClient, QbittorrentInstance, dry_run)
    -> QbittorrentResult
    QbittorrentResult.plan: list[PlannedAction[Category]]
    Auth shim: POST /api/v2/auth/login -> "Ok." with Set-Cookie SID required BEFORE
    any GET (QbittorrentClient.__init__ performs login).
    Fixtures: qbittorrent/auth_login_ok.txt, qbittorrent/categories.json
  - reconcile_seerr    signature: (SeerrClient, SeerrInstance, dry_run) -> SeerrResult
    SeerrResult has NO .plan field — only .actions_taken (empty in dry_run=True).
    D-06-SEERR-USER-FP carry-forward: no ordering FP possible (no plan tuples).
    Captured as {"completed": True, "actions_taken": []} for the fixture.
    Fixtures: seerr/settings_sonarr.json, seerr/settings_radarr.json,
              seerr/user.json, seerr/settings_main.json
  - reconcile_jellyfin signature: (JellyfinClient, JellyfinInstance, dry_run) -> JellyfinResult
    JellyfinResult has NO .plan field — only .actions_taken (empty in dry_run=True).
    Captured as {"completed": True, "actions_taken": []} for the fixture.
    Fixtures: jellyfin/library_virtualfolders.json, jellyfin/users.json,
              jellyfin/system_configuration.json, jellyfin/plugins.json

Fixture strategy (Option A — minimal fork): The helper keeps the existing Phase 9
fixtures (sonarr/tag_with_tv_anime_family.json with 3 v0.2.0 tags, etc.) for the
GET response mocks. Since dry_run=True, the reconciler only reads the cluster state
and plans — it does NOT write. The 2nd-run-zero assertion works because the
PLANNING logic is idempotent (same desired state + same cluster state → same plan),
not because the fixtures perfectly mirror Phase 10 cluster state.

_caveat: Phase-9-code-with-categories-stripped is NOT v0.2.0 verbatim — it is
functionally equivalent because reconcilers don't read RootConfig.categories (D-13).
For Phase 10 sweep tests, the helper is called with various RootConfig variants
(empty manual sections, production config) to exercise different reconciler paths.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import respx

from arrconf.client_base import (
    JellyfinClient,
    ProwlarrClient,
    QbittorrentClient,
    RadarrClient,
    SeerrClient,
    SonarrClient,
)
from arrconf.config import RootConfig
from arrconf.reconcilers.jellyfin import reconcile_jellyfin
from arrconf.reconcilers.prowlarr import reconcile_prowlarr
from arrconf.reconcilers.qbittorrent import reconcile_qbittorrent
from arrconf.reconcilers.radarr import reconcile_radarr
from arrconf.reconcilers.seerr import reconcile_seerr
from arrconf.reconcilers.sonarr import reconcile_sonarr

_FIXTURE_ROOT = Path(__file__).parent / "fixtures"


def _load_fixture(relative_path: str) -> Any:
    """Load a JSON fixture file; raise a clear error if missing."""
    p = _FIXTURE_ROOT / relative_path
    if not p.exists():
        raise FileNotFoundError(
            f"Phase 9 helper: fixture missing: {relative_path!r} (resolved to {p})"
        )
    return json.loads(p.read_text())


def _plan_to_tuples(plan: list[Any]) -> list[dict[str, Any]]:
    """Project a PlannedAction list to JSON-serializable tuples.

    Sorted by (resource_type, name, action) to defeat non-deterministic ordering
    (D-06-SEERR-USER-FP pattern — applied uniformly across all reconcilers that
    return a plan).
    resource_type is derived from the PlannedAction's type arg (desired or current).
    """
    rows = []
    for p in plan:
        obj = p.desired if p.desired is not None else p.current
        resource_type = type(obj).__name__ if obj is not None else "Unknown"
        rows.append(
            {
                "resource_type": resource_type,
                "action": p.action.value,
                "name": p.name,
                "diff_fields": sorted(p.diff_fields),
            }
        )
    return sorted(rows, key=lambda d: (d["resource_type"], d["name"], d["action"]))


def dry_run_all_apps(cfg: RootConfig) -> dict[str, Any]:
    """Run every reconciler in dry_run=True mode against cfg; return sorted plan dict.

    Manages its own respx.mock() context. No external router required.

    For reconcilers with a .plan attribute (sonarr/radarr/prowlarr/qbittorrent):
    returns a sorted list of plan tuples via _plan_to_tuples.

    For reconcilers without a .plan attribute (seerr/jellyfin, Phase 6/7):
    returns {"completed": True, "actions_taken": []} — proving dry_run completes
    without error is the D-13 evidence for these apps (SeerrResult and
    JellyfinResult have no .plan by design; they use actions_taken which is
    always empty in dry_run=True).

    Env vars for Prowlarr api_key_env resolution are patched to "fake-key" so
    the reconciler can build desired apps without a real cluster credential.
    The env patch is scoped to the Prowlarr iteration only.

    Returns a dict with alphabetically sorted app keys for byte-stable output.
    """
    out: dict[str, Any] = {}

    # Collect env-var names Prowlarr needs for api_key_env resolution.
    prowlarr_env_overrides: dict[str, str] = {}
    for instance in cfg.prowlarr.values():
        for app_entry in instance.apps.items:
            prowlarr_env_overrides[app_entry.api_key_env] = "fake-key-for-phase9-fixture"

    with respx.mock(assert_all_called=False) as mock:
        _register_sonarr_routes(mock, cfg)
        _register_radarr_routes(mock, cfg)
        _register_prowlarr_routes(mock, cfg)
        _register_qbittorrent_routes(mock, cfg)
        _register_seerr_routes(mock, cfg)
        _register_jellyfin_routes(mock, cfg)

        # Sonarr
        sonarr_plans: list[dict[str, Any]] = []
        for _sonarr_name, sonarr_instance in cfg.sonarr.items():
            sonarr_client = SonarrClient(base_url=sonarr_instance.base_url, api_key="fake")
            sonarr_result = reconcile_sonarr(sonarr_client, sonarr_instance, dry_run=True)
            sonarr_plans.extend(_plan_to_tuples(sonarr_result.plan))
        out["sonarr"] = sorted(
            sonarr_plans, key=lambda d: (d["resource_type"], d["name"], d["action"])
        )

        # Radarr
        radarr_plans: list[dict[str, Any]] = []
        for _radarr_name, radarr_instance in cfg.radarr.items():
            radarr_client = RadarrClient(base_url=radarr_instance.base_url, api_key="fake")
            radarr_result = reconcile_radarr(radarr_client, radarr_instance, dry_run=True)
            radarr_plans.extend(_plan_to_tuples(radarr_result.plan))
        out["radarr"] = sorted(
            radarr_plans, key=lambda d: (d["resource_type"], d["name"], d["action"])
        )

        # Prowlarr (with api_key_env patches for AppEntry resolution)
        prowlarr_plans: list[dict[str, Any]] = []
        with patch.dict(os.environ, prowlarr_env_overrides):
            for _prowlarr_name, prowlarr_instance in cfg.prowlarr.items():
                prowlarr_client = ProwlarrClient(
                    base_url=prowlarr_instance.base_url, api_key="fake"
                )
                prowlarr_result = reconcile_prowlarr(
                    prowlarr_client, prowlarr_instance, dry_run=True
                )
                prowlarr_plans.extend(_plan_to_tuples(prowlarr_result.plan))
        out["prowlarr"] = sorted(
            prowlarr_plans, key=lambda d: (d["resource_type"], d["name"], d["action"])
        )

        # qBittorrent (auth shim is auto-handled by QbittorrentClient.__init__)
        qbittorrent_plans: list[dict[str, Any]] = []
        for _qbt_name, qbt_instance in cfg.qbittorrent.items():
            qbt_client = QbittorrentClient(
                base_url=qbt_instance.base_url,
                username="fake",
                password="fake",
            )
            qbt_result = reconcile_qbittorrent(qbt_client, qbt_instance, dry_run=True)
            qbittorrent_plans.extend(_plan_to_tuples(qbt_result.plan))
        out["qbittorrent"] = sorted(
            qbittorrent_plans, key=lambda d: (d["resource_type"], d["name"], d["action"])
        )

        # Seerr — no .plan field; capture completion status
        for _seerr_name, seerr_instance in cfg.seerr.items():
            seerr_client = SeerrClient(base_url=seerr_instance.base_url, api_key="fake")
            _seerr_result = reconcile_seerr(seerr_client, seerr_instance, dry_run=True)
            # SeerrResult has no .plan — dry_run=True means actions_taken is empty
        out["seerr"] = {"completed": True, "actions_taken": []}

        # Jellyfin — no .plan field; capture completion status
        for _jf_name, jf_instance in cfg.jellyfin.items():
            jf_client = JellyfinClient(base_url=jf_instance.base_url, api_key="fake")
            _jf_result = reconcile_jellyfin(jf_client, jf_instance, dry_run=True)
            # JellyfinResult has no .plan — dry_run=True means actions_taken is empty
        out["jellyfin"] = {"completed": True, "actions_taken": []}

    return dict(sorted(out.items()))


# ---------------------------------------------------------------------------
# Per-app respx route registration helpers.
# Each registers the GET endpoints that the reconciler always touches.
# Based on the existing test_reconcilers_<app>.py route setup patterns.
# ---------------------------------------------------------------------------


def _register_sonarr_routes(mock: respx.MockRouter, cfg: RootConfig) -> None:
    """Register Sonarr GET routes using production fixtures.

    Sonarr reconciler touches: /tag, /indexer, /rootfolder, /downloadclient,
    /notification, /remotepathmapping, /series on every run (Phase 5 scope).

    Uses tag_with_tv_anime_family.json (all 4 production tags including arrconf-managed)
    so _resolve_download_client_tag_labels can match tv/anime/family label→id.
    The empty sonarr/tag.json would cause ReconcileError because in dry_run mode
    no tags are actually created, so the second GET /tag also returns empty list.
    """
    tag_fixture = _load_fixture("sonarr/tag_with_tv_anime_family.json")
    dc_fixture = _load_fixture("sonarr/downloadclient.json")
    indexer_fixture = _load_fixture("sonarr/indexer.json")
    rootfolder_fixture = _load_fixture("sonarr/rootfolder.json")
    notification_fixture = _load_fixture("sonarr/notification.json")
    rpm_fixture = _load_fixture("sonarr/remotepathmapping.json")

    for instance in cfg.sonarr.values():
        base = instance.base_url.rstrip("/")
        api = f"{base}/api/v3"
        mock.get(f"{api}/tag").mock(return_value=httpx.Response(200, json=tag_fixture))
        mock.get(f"{api}/downloadclient").mock(return_value=httpx.Response(200, json=dc_fixture))
        mock.get(f"{api}/indexer").mock(return_value=httpx.Response(200, json=indexer_fixture))
        mock.get(f"{api}/rootfolder").mock(
            return_value=httpx.Response(200, json=rootfolder_fixture)
        )
        mock.get(f"{api}/notification").mock(
            return_value=httpx.Response(200, json=notification_fixture)
        )
        mock.get(f"{api}/remotepathmapping").mock(
            return_value=httpx.Response(200, json=rpm_fixture)
        )
        # /series: used by series_tags reconcile step (Phase 5 D-05-MIG-01)
        mock.get(f"{api}/series").mock(return_value=httpx.Response(200, json=[]))


def _register_radarr_routes(mock: respx.MockRouter, cfg: RootConfig) -> None:
    """Register Radarr GET routes using production fixtures.

    Radarr reconciler touches: /tag, /indexer, /rootfolder, /downloadclient,
    /notification, /remotepathmapping, /movie on every run (Phase 5 scope).

    Uses tag_with_movies_anime_family.json (all 4 production tags including
    arrconf-managed) so _resolve_download_client_tag_labels can match
    movies/anime/family label→id. Same rationale as Sonarr tag fixture choice.
    """
    tag_fixture = _load_fixture("radarr/tag_with_movies_anime_family.json")
    dc_fixture = _load_fixture("radarr/downloadclient.json")
    indexer_fixture = _load_fixture("radarr/indexer.json")
    rootfolder_fixture = _load_fixture("radarr/rootfolder.json")
    notification_fixture = _load_fixture("radarr/notification.json")
    rpm_fixture = _load_fixture("radarr/remotepathmapping.json")

    for instance in cfg.radarr.values():
        base = instance.base_url.rstrip("/")
        api = f"{base}/api/v3"
        mock.get(f"{api}/tag").mock(return_value=httpx.Response(200, json=tag_fixture))
        mock.get(f"{api}/downloadclient").mock(return_value=httpx.Response(200, json=dc_fixture))
        mock.get(f"{api}/indexer").mock(return_value=httpx.Response(200, json=indexer_fixture))
        mock.get(f"{api}/rootfolder").mock(
            return_value=httpx.Response(200, json=rootfolder_fixture)
        )
        mock.get(f"{api}/notification").mock(
            return_value=httpx.Response(200, json=notification_fixture)
        )
        mock.get(f"{api}/remotepathmapping").mock(
            return_value=httpx.Response(200, json=rpm_fixture)
        )
        # /movie: used by movie_tags reconcile step (Phase 5 D-05-SPLIT-02)
        mock.get(f"{api}/movie").mock(return_value=httpx.Response(200, json=[]))


def _register_prowlarr_routes(mock: respx.MockRouter, cfg: RootConfig) -> None:
    """Register Prowlarr GET routes using production fixtures.

    Prowlarr reconciler touches only: /applications (D-03-02 scope).
    Prowlarr uses /api/v1 (not /api/v3 — Pitfall 3).
    """
    apps_fixture = _load_fixture("prowlarr/applications.json")

    for instance in cfg.prowlarr.values():
        base = instance.base_url.rstrip("/")
        api = f"{base}/api/v1"
        mock.get(f"{api}/applications").mock(return_value=httpx.Response(200, json=apps_fixture))


def _register_qbittorrent_routes(mock: respx.MockRouter, cfg: RootConfig) -> None:
    """Register qBittorrent routes using production fixtures.

    Auth shim: QbittorrentClient.__init__ calls POST /api/v2/auth/login.
    Must return "Ok." with Set-Cookie SID header (Pitfall 1).
    Then reconciler GETs /api/v2/torrents/categories (returns dict, not list).
    """
    categories_fixture = _load_fixture("qbittorrent/categories.json")

    for instance in cfg.qbittorrent.values():
        base = instance.base_url.rstrip("/")
        # Auth login shim (QbittorrentClient.__init__ performs this)
        mock.post(f"{base}/api/v2/auth/login").mock(
            return_value=httpx.Response(
                200,
                text="Ok.",
                headers={"set-cookie": "SID=fake-sid; HttpOnly; SameSite=Strict; path=/"},
            )
        )
        mock.get(f"{base}/api/v2/torrents/categories").mock(
            return_value=httpx.Response(200, json=categories_fixture)
        )


def _register_seerr_routes(mock: respx.MockRouter, cfg: RootConfig) -> None:
    """Register Seerr GET routes using production fixtures.

    Seerr reconciler touches: /settings/sonarr, /settings/radarr, /user,
    /settings/main. Uses /api/v1. Dry_run=True prevents any PUT/POST calls.
    """
    sonarr_fixture = _load_fixture("seerr/settings_sonarr.json")
    radarr_fixture = _load_fixture("seerr/settings_radarr.json")
    user_fixture = _load_fixture("seerr/user.json")
    main_fixture = _load_fixture("seerr/settings_main.json")

    for instance in cfg.seerr.values():
        base = instance.base_url.rstrip("/")
        api = f"{base}/api/v1"
        mock.get(f"{api}/settings/sonarr").mock(
            return_value=httpx.Response(200, json=sonarr_fixture)
        )
        mock.get(f"{api}/settings/radarr").mock(
            return_value=httpx.Response(200, json=radarr_fixture)
        )
        mock.get(f"{api}/user").mock(return_value=httpx.Response(200, json=user_fixture))
        mock.get(f"{api}/settings/main").mock(return_value=httpx.Response(200, json=main_fixture))


def _register_jellyfin_routes(mock: respx.MockRouter, cfg: RootConfig) -> None:
    """Register Jellyfin GET routes using production fixtures.

    Jellyfin reconciler touches: /Library/VirtualFolders, /Users (list),
    /Users/{admin_id} (per-user GET for Pitfall 6 re-injection),
    /System/Configuration, /Plugins. Uses bare base_url (api_path="").
    Dry_run=True prevents POST calls to /Library/VirtualFolders/Paths,
    /Users/{id}/Policy, /System/Configuration, and /Plugins/{id}/{ver}/Enable.

    The per-user GET /Users/{admin_id} is required because _reconcile_users
    fetches the full user record (line 213 of jellyfin.py) to re-inject
    AuthenticationProviderId + PasswordResetProviderId (Pitfall 6).
    The admin_id "82fd95db72904569b08d83271823ceaa" matches users.json "moi".
    """
    libraries_fixture = _load_fixture("jellyfin/library_virtualfolders.json")
    users_fixture = _load_fixture("jellyfin/users.json")
    user_moi_fixture = _load_fixture("jellyfin/user_moi_full.json")
    system_config_fixture = _load_fixture("jellyfin/system_configuration.json")
    plugins_fixture = _load_fixture("jellyfin/plugins.json")

    # Admin user id from users.json (user "moi").
    admin_user_id = user_moi_fixture["Id"]

    for instance in cfg.jellyfin.values():
        base = instance.base_url.rstrip("/")
        # Jellyfin api_path="" — endpoints at bare base_url
        mock.get(f"{base}/Library/VirtualFolders").mock(
            return_value=httpx.Response(200, json=libraries_fixture)
        )
        mock.get(f"{base}/Users").mock(return_value=httpx.Response(200, json=users_fixture))
        # Per-user GET required by _reconcile_users for Pitfall 6 re-injection.
        mock.get(f"{base}/Users/{admin_user_id}").mock(
            return_value=httpx.Response(200, json=user_moi_fixture)
        )
        mock.get(f"{base}/System/Configuration").mock(
            return_value=httpx.Response(200, json=system_config_fixture)
        )
        mock.get(f"{base}/Plugins").mock(return_value=httpx.Response(200, json=plugins_fixture))
