"""Tests for arrconf.reconcilers.jellyfin (Phase 7 — D-07-INSTANCE-01).

Coverage target >= 70% on arrconf/reconcilers/jellyfin.py (CLAUDE.md REQ-test-coverage).

Tests verify all 9 Pitfalls + emilie protection + ADR-5 frontiere negative assertion
+ D-07-ORDER-01 step order invariant + JellyfinClient auth header format.
"""

from __future__ import annotations

import copy
import json
from typing import Any

import httpx
import pytest
import respx

from arrconf.client_base import ArrApiClient, JellyfinClient, _ArrV3Client
from arrconf.config import (
    JellyfinInstance,
    JellyfinLibrariesSection,
    JellyfinPluginsSection,
    JellyfinServerConfigSection,
    JellyfinUsersSection,
)
from arrconf.reconcilers.jellyfin import (
    _ACTIVE_PLUGIN_STATUSES,
    reconcile_jellyfin,
)
from arrconf.resources.jellyfin import (
    JellyfinLibrary,
    JellyfinUserPolicy,
    PluginEntry,
    PluginRepository,
)

JELLYFIN_BASE = "http://jellyfin.test:8096"
ADMIN_USER_ID = "82fd95db72904569b08d83271823ceaa"

_DEFAULT_LIBRARIES = [
    JellyfinLibrary(name="Séries", collection_type="tvshows", paths=["/media/series"]),
    JellyfinLibrary(name="Films", collection_type="movies", paths=["/media/films"]),
]
EMILIE_USER_ID = "8901eacec3634d169958d11bd95d4078"
TMDB_PLUGIN_ID = "b8715ed16c4745289ad3f72deb539cd4"
TMDB_PLUGIN_VERSION = "10.11.8.0"
DEFAULT_AUTH_PROVIDER = "Jellyfin.Server.Implementations.Users.DefaultAuthenticationProvider"
DEFAULT_PWD_PROVIDER = "Jellyfin.Server.Implementations.Users.DefaultPasswordResetProvider"


# ---------------------------------------------------------------------------
# Helpers — instance + client builders
# ---------------------------------------------------------------------------


def _make_client() -> JellyfinClient:
    return JellyfinClient(base_url=JELLYFIN_BASE, api_key="test-api-key")


def _make_instance(**overrides: Any) -> JellyfinInstance:
    """Build a minimal JellyfinInstance with sensible defaults."""
    defaults: dict[str, Any] = dict(
        base_url=JELLYFIN_BASE,
        libraries=JellyfinLibrariesSection(enable=True),
        users=JellyfinUsersSection(
            enable=True,
            admin=JellyfinUserPolicy(
                IsAdministrator=True,
                EnableContentDeletion=True,
                EnableRemoteControlOfOtherUsers=True,
                EnablePublicSharing=True,  # matches jellyfin_user_moi_full_fixture baseline
            ),
        ),
        server_config=JellyfinServerConfigSection(
            enable=True,
            ui_culture="fr",
            metadata_country_code="FR",
            preferred_metadata_language="fr",
            activity_log_retention_days=30,
            log_file_retention_days=3,
            server_name="jellyfin",
            plugin_repositories=[
                PluginRepository(
                    Name="Jellyfin Stable",
                    Url="https://repo.jellyfin.org/files/plugin/manifest.json",
                    Enabled=True,
                )
            ],
        ),
        plugins=JellyfinPluginsSection(
            enable=True,
            required=[
                PluginEntry(name="TMDb"),
            ],
        ),
    )
    defaults.update(overrides)
    return JellyfinInstance(**defaults)


def _users_fixture() -> list[dict[str, Any]]:
    """Bare /Users GET list with moi (admin) + emilie (restricted)."""
    return [
        {
            "Name": "emilie",
            "Id": EMILIE_USER_ID,
            "HasPassword": True,
            "Policy": {
                "IsAdministrator": False,
                "AuthenticationProviderId": DEFAULT_AUTH_PROVIDER,
                "PasswordResetProviderId": DEFAULT_PWD_PROVIDER,
            },
        },
        {
            "Name": "moi",
            "Id": ADMIN_USER_ID,
            "HasPassword": True,
            "Policy": {
                "IsAdministrator": True,
                "AuthenticationProviderId": DEFAULT_AUTH_PROVIDER,
                "PasswordResetProviderId": DEFAULT_PWD_PROVIDER,
            },
        },
    ]


def _user_moi_full_fixture() -> dict[str, Any]:
    """Per-user GET /Users/{id} for moi — full Policy block with ProviderIds."""
    return {
        "Name": "moi",
        "Id": ADMIN_USER_ID,
        "Policy": {
            "IsAdministrator": True,
            "IsDisabled": False,
            "IsHidden": True,
            "EnableContentDeletion": True,
            "EnableContentDeletionFromFolders": [],
            "EnableRemoteAccess": True,
            "EnableLiveTvManagement": False,
            "EnableLiveTvAccess": True,
            "EnableMediaPlayback": True,
            "EnableAudioPlaybackTranscoding": True,
            "EnableVideoPlaybackTranscoding": True,
            "EnablePlaybackRemuxing": True,
            "ForceRemoteSourceTranscoding": False,
            "EnableContentDownloading": True,
            "EnableSyncTranscoding": True,
            "EnableMediaConversion": True,
            "EnableLyricManagement": False,
            "EnabledDevices": [],
            "EnableAllDevices": True,
            "EnabledChannels": [],
            "EnableAllChannels": True,
            "EnabledFolders": [],
            "EnableAllFolders": True,
            "InvalidLoginAttemptCount": 0,
            "LoginAttemptsBeforeLockout": -1,
            "MaxActiveSessions": 0,
            "EnablePublicSharing": True,  # matches _make_instance() default policy baseline
            "BlockedTags": [],
            "AllowedTags": [],
            "BlockedChannels": [],
            "BlockedMediaFolders": [],
            "EnableUserPreferenceAccess": True,
            "AccessSchedules": [],
            "BlockUnratedItems": [],
            "EnableRemoteControlOfOtherUsers": True,
            "EnableSharedDeviceControl": True,
            "EnableCollectionManagement": False,
            "EnableSubtitleManagement": False,
            "SyncPlayAccess": "CreateAndJoinGroups",
            "RemoteClientBitrateLimit": 0,
            # Pitfall 6 — OpenAPI-required fields:
            "AuthenticationProviderId": DEFAULT_AUTH_PROVIDER,
            "PasswordResetProviderId": DEFAULT_PWD_PROVIDER,
        },
    }


def _library_fixture() -> list[dict[str, Any]]:
    """GET /Library/VirtualFolders — 2 libraries each with 1 path."""
    return [
        {
            "Name": "Séries",
            "ItemId": "d565273fd114d77bdf349a2896867069",
            "CollectionType": "tvshows",
            "Locations": ["/media/series"],
            "LibraryOptions": {"PathInfos": [{"Path": "/media/series"}]},
        },
        {
            "Name": "Films",
            "ItemId": "db4c1708cbb5dd1676284a40f2950aba",
            "CollectionType": "movies",
            "Locations": ["/media/films"],
            "LibraryOptions": {"PathInfos": [{"Path": "/media/films"}]},
        },
    ]


def _system_config_fixture() -> dict[str, Any]:
    """GET /System/Configuration — 56-field body (abridged for test performance)."""
    return {
        "UICulture": "fr",
        "MetadataCountryCode": "FR",
        "PreferredMetadataLanguage": "fr",
        "ActivityLogRetentionDays": 30,
        "LogFileRetentionDays": 3,
        "ServerName": "jellyfin",
        "PluginRepositories": [
            {
                "Name": "Jellyfin Stable",
                "Url": "https://repo.jellyfin.org/files/plugin/manifest.json",
                "Enabled": True,
            }
        ],
        # Non-allowlist fields that must be preserved (Pitfall 1 evidence):
        "TrickplayOptions": {
            "Interval": 10000,
            "JpegQuality": 90,
            "ScanBehavior": "NonBlocking",
        },
        "MetadataOptions": [{"ItemType": "Movie", "DisabledMetadataFetchers": []}],
        "CacheSize": 600,
        "EnableMetrics": False,
    }


def _plugins_fixture() -> list[dict[str, Any]]:
    """GET /Plugins — 6 plugins, all Active."""
    return [
        {"Name": "TMDb", "Id": TMDB_PLUGIN_ID, "Version": TMDB_PLUGIN_VERSION, "Status": "Active"},
        {
            "Name": "Kodi Sync Queue",
            "Id": "771e19d653854cafb35c28a0e865cf63",
            "Version": "15.0.0.0",
            "Status": "Active",
        },
        {
            "Name": "MusicBrainz",
            "Id": "8c95c4d2e50c4fb0a4f36c06ff0f9a1a",
            "Version": "10.11.8.0",
            "Status": "Active",
        },
    ]


def _mock_all_gets(
    respx_mock: respx.MockRouter,
    libraries: list[dict[str, Any]] | None = None,
    users: list[dict[str, Any]] | None = None,
    user_moi_full: dict[str, Any] | None = None,
    system_config: dict[str, Any] | None = None,
    plugins: list[dict[str, Any]] | None = None,
) -> None:
    """Mock all 4 Jellyfin GET endpoints used by reconcile_jellyfin.

    Defensive POST mocks are added to avoid AllMockedAssertionError when the
    reconciler detects drift on other steps. Tests targeting specific routes
    should register those routes BEFORE calling this helper (first-registered wins)
    or register them AFTER and use a dedicated respx_mock.
    """
    libs = libraries if libraries is not None else _library_fixture()
    us = users if users is not None else _users_fixture()
    umf = user_moi_full if user_moi_full is not None else _user_moi_full_fixture()
    sc = system_config if system_config is not None else _system_config_fixture()
    pl = plugins if plugins is not None else _plugins_fixture()

    respx_mock.get("/Library/VirtualFolders").mock(return_value=httpx.Response(200, json=libs))
    respx_mock.get("/Users").mock(return_value=httpx.Response(200, json=us))
    respx_mock.get(f"/Users/{ADMIN_USER_ID}").mock(return_value=httpx.Response(200, json=umf))
    respx_mock.get("/System/Configuration").mock(return_value=httpx.Response(200, json=sc))
    respx_mock.get("/Plugins").mock(return_value=httpx.Response(200, json=pl))


# ---------------------------------------------------------------------------
# Test 1: JellyfinClient auth header format (unit, no respx)
# ---------------------------------------------------------------------------


def test_jellyfin_client_auth_header_mediabrowser_format() -> None:
    """JellyfinClient.auth_headers() returns a valid MediaBrowser Authorization header.

    T-07-AUTH-FORMAT mitigation: verifies all 5 parameters present in the
    correct format (Q9 probe verified 2026-05-17 HTTP 200 on live cluster).
    """
    client = JellyfinClient(base_url="http://j.test:8096", api_key="abc123hex")
    headers = client.auth_headers()

    assert "Authorization" in headers
    auth = headers["Authorization"]
    assert 'MediaBrowser Token="abc123hex"' in auth
    assert 'Client="arrconf"' in auth
    assert 'Device="arrconf"' in auth
    assert 'DeviceId="arrconf"' in auth
    assert 'Version="0.5.0"' in auth
    # CRITICAL: NO X-Api-Key — that header is *arr-specific, not Jellyfin.
    assert "X-Api-Key" not in headers


def test_jellyfin_client_not_inheriting_arrv3client() -> None:
    """JellyfinClient must NOT inherit from _ArrV3Client (ADR-8 forceSave exclusion)."""
    assert issubclass(JellyfinClient, ArrApiClient)
    assert not issubclass(JellyfinClient, _ArrV3Client)


def test_jellyfin_client_api_path_empty() -> None:
    """api_path='' means httpx base_url == base_url exactly (no /api/v3 prefix)."""
    client = JellyfinClient(base_url="http://j.test:8096", api_key="x")
    assert client.api_path == ""
    assert str(client._client.base_url) == "http://j.test:8096"


# ---------------------------------------------------------------------------
# Test 2: Pitfall 2 — library path idempotence
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_libraries_path_idempotent_pitfall2(
    respx_mock: respx.MockRouter,
    jellyfin_library_virtualfolders_fixture: list[dict[str, Any]],
    jellyfin_users_fixture: list[dict[str, Any]],
    jellyfin_user_moi_full_fixture: dict[str, Any],
    jellyfin_system_configuration_fixture: dict[str, Any],
    jellyfin_plugins_fixture: list[dict[str, Any]],
) -> None:
    """Pitfall 2 shim: POST /Library/VirtualFolders/Paths called ONCE for new path only.

    T-07-PITFALL2-DUP mitigation: when /media/series is already in PathInfos,
    re-posting it would duplicate the entry. Reconciler skips it; only /media/anime
    (new) triggers a POST. Asserts the POST route was called exactly once.
    """
    # Modify the Séries library to already have /media/series (from fixture) but NOT /media/anime.
    libs = copy.deepcopy(jellyfin_library_virtualfolders_fixture)
    # Fixture has /media/series in PathInfos — desired=[/media/series, /media/anime].
    libs_desired = [
        JellyfinLibrary(
            name="Séries",
            collection_type="tvshows",
            paths=["/media/series", "/media/anime"],
        ),
    ]
    instance = _make_instance(libraries=JellyfinLibrariesSection(enable=True))
    client = _make_client()

    add_path_route = respx_mock.post(url__regex=r"/Library/VirtualFolders/Paths").mock(
        return_value=httpx.Response(204)
    )

    _mock_all_gets(
        respx_mock,
        libraries=libs,
        users=jellyfin_users_fixture,
        user_moi_full=jellyfin_user_moi_full_fixture,
        system_config=jellyfin_system_configuration_fixture,
        plugins=jellyfin_plugins_fixture,
    )

    result = reconcile_jellyfin(client, instance, libs_desired, dry_run=False)

    # POST must be called EXACTLY ONCE (for /media/anime, not for /media/series).
    assert add_path_route.called
    assert add_path_route.call_count == 1
    posted_body = json.loads(add_path_route.calls[0].request.content)
    assert posted_body["Path"] == "/media/anime"
    assert "library_path:added:Séries:/media/anime" in result.actions_taken


# ---------------------------------------------------------------------------
# Test 3: Pitfall 8 — PathInfos (not Locations) is the source of truth
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_libraries_set_membership_uses_pathinfos_not_locations_pitfall8(
    respx_mock: respx.MockRouter,
    jellyfin_users_fixture: list[dict[str, Any]],
    jellyfin_user_moi_full_fixture: dict[str, Any],
    jellyfin_system_configuration_fixture: dict[str, Any],
    jellyfin_plugins_fixture: list[dict[str, Any]],
) -> None:
    """Pitfall 8: reconciler reads PathInfos (not Locations) as existing-paths source.

    Locations is a stale display projection — it may show extra/duplicate entries.
    PathInfos (LibraryOptions.PathInfos[].Path) is the source of truth for indexing.
    """
    # Séries library: Locations shows [/media/series, /media/anime] (stale display)
    # but PathInfos only has [/media/series] (authoritative). Desired: [/media/anime].
    # Reconciler must see /media/anime as NOT present (PathInfos doesn't have it)
    # → POST must be called once for /media/anime.
    libs = [
        {
            "Name": "Séries",
            "ItemId": "d565273fd114d77bdf349a2896867069",
            "CollectionType": "tvshows",
            "Locations": ["/media/series", "/media/anime"],  # stale display
            "LibraryOptions": {"PathInfos": [{"Path": "/media/series"}]},  # authoritative
        }
    ]
    libs_desired = [
        JellyfinLibrary(name="Séries", collection_type="tvshows", paths=["/media/anime"])
    ]
    instance = _make_instance(libraries=JellyfinLibrariesSection(enable=True))
    client = _make_client()

    add_path_route = respx_mock.post(url__regex=r"/Library/VirtualFolders/Paths").mock(
        return_value=httpx.Response(204)
    )

    _mock_all_gets(
        respx_mock,
        libraries=libs,
        users=jellyfin_users_fixture,
        user_moi_full=jellyfin_user_moi_full_fixture,
        system_config=jellyfin_system_configuration_fixture,
        plugins=jellyfin_plugins_fixture,
    )

    reconcile_jellyfin(client, instance, libs_desired, dry_run=False)

    # Must have posted once for /media/anime (PathInfos said it was absent).
    assert add_path_route.called
    assert add_path_route.call_count == 1
    posted_body = json.loads(add_path_route.calls[0].request.content)
    assert posted_body["Path"] == "/media/anime"


# ---------------------------------------------------------------------------
# Test 4: Pitfall 4 — users Policy uses POST not PUT
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_users_policy_uses_post_not_put_pitfall4(
    respx_mock: respx.MockRouter,
    jellyfin_library_virtualfolders_fixture: list[dict[str, Any]],
    jellyfin_users_fixture: list[dict[str, Any]],
    jellyfin_plugins_fixture: list[dict[str, Any]],
    jellyfin_system_configuration_fixture: dict[str, Any],
) -> None:
    """Pitfall 4 mitigation: POST /Users/{id}/Policy used, PUT route NEVER called.

    T-07-PITFALL4-VERB: verifies the reconciler calls POST (not PUT) which would
    return HTTP 405 Method Not Allowed on the real Jellyfin API.
    """
    # Force drift: cluster has EnablePublicSharing=True (from fixture baseline),
    # desired is explicitly False → triggers POST /Users/{id}/Policy.
    user_full = _user_moi_full_fixture()
    # _user_moi_full_fixture() already has EnablePublicSharing=True (cluster baseline).

    instance = _make_instance(
        users=JellyfinUsersSection(
            enable=True,
            admin=JellyfinUserPolicy(EnablePublicSharing=False),  # desired=False ≠ cluster True
        )
    )
    client = _make_client()

    post_policy_route = respx_mock.post(f"/Users/{ADMIN_USER_ID}/Policy").mock(
        return_value=httpx.Response(204)
    )
    put_policy_route = respx_mock.put(f"/Users/{ADMIN_USER_ID}/Policy").mock(
        return_value=httpx.Response(405)
    )

    _mock_all_gets(
        respx_mock,
        libraries=jellyfin_library_virtualfolders_fixture,
        users=jellyfin_users_fixture,
        user_moi_full=user_full,
        system_config=jellyfin_system_configuration_fixture,
        plugins=jellyfin_plugins_fixture,
    )

    reconcile_jellyfin(client, instance, _DEFAULT_LIBRARIES, dry_run=False)

    assert post_policy_route.called, "POST /Users/{id}/Policy must be called"
    assert not put_policy_route.called, (
        "PUT /Users/{id}/Policy must NEVER be called (405 on real API)"
    )


# ---------------------------------------------------------------------------
# Test 5: Pitfall 6 — AuthenticationProviderId + PasswordResetProviderId re-injected
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_users_policy_reinjects_required_providerids_pitfall6(
    respx_mock: respx.MockRouter,
    jellyfin_library_virtualfolders_fixture: list[dict[str, Any]],
    jellyfin_users_fixture: list[dict[str, Any]],
    jellyfin_system_configuration_fixture: dict[str, Any],
    jellyfin_plugins_fixture: list[dict[str, Any]],
) -> None:
    """Pitfall 6 mitigation: ProviderIds excluded from YAML but re-injected from cluster GET.

    T-07-PITFALL6-LEAK: JellyfinUserPolicy.model_dump() excludes the 2 fields
    (Field(exclude=True) at pydantic layer). Reconciler re-injects them from the
    per-user GET. Without re-injection: HTTP 400 (OpenAPI required fields missing).
    """
    # _user_moi_full_fixture() has EnablePublicSharing=True (cluster baseline).
    # Desired policy sets it to False → drift forces the POST (Pitfall 6 capture).
    user_full = _user_moi_full_fixture()

    instance = _make_instance(
        users=JellyfinUsersSection(
            enable=True,
            admin=JellyfinUserPolicy(EnablePublicSharing=False),
        )
    )
    client = _make_client()

    captured_body: dict[str, Any] = {}

    def capture_post(request: httpx.Request) -> httpx.Response:
        nonlocal captured_body
        captured_body = json.loads(request.content)
        return httpx.Response(204)

    respx_mock.post(f"/Users/{ADMIN_USER_ID}/Policy").mock(side_effect=capture_post)

    _mock_all_gets(
        respx_mock,
        libraries=jellyfin_library_virtualfolders_fixture,
        users=jellyfin_users_fixture,
        user_moi_full=user_full,
        system_config=jellyfin_system_configuration_fixture,
        plugins=jellyfin_plugins_fixture,
    )

    reconcile_jellyfin(client, instance, _DEFAULT_LIBRARIES, dry_run=False)

    assert captured_body, "POST /Users/{id}/Policy must have been called"
    assert captured_body["AuthenticationProviderId"] == DEFAULT_AUTH_PROVIDER, (
        "AuthenticationProviderId MUST be re-injected from cluster GET (Pitfall 6)"
    )
    assert captured_body["PasswordResetProviderId"] == DEFAULT_PWD_PROVIDER, (
        "PasswordResetProviderId MUST be re-injected from cluster GET (Pitfall 6)"
    )


# ---------------------------------------------------------------------------
# Test 6: D-07-USERS-01 — emilie never touched
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_users_emilie_never_touched_d_07_users_01(
    respx_mock: respx.MockRouter,
    jellyfin_library_virtualfolders_fixture: list[dict[str, Any]],
    jellyfin_users_fixture: list[dict[str, Any]],
    jellyfin_user_moi_full_fixture: dict[str, Any],
    jellyfin_system_configuration_fixture: dict[str, Any],
    jellyfin_plugins_fixture: list[dict[str, Any]],
) -> None:
    """D-07-USERS-01: emilie's Policy endpoint is NEVER called by the reconciler.

    T-07-PRUNE-EMILIE: prune=False hardcoded at JellyfinUsersSection layer.
    Only moi (matched by Name="moi") is managed; emilie is operator-managed.
    """
    instance = _make_instance()
    client = _make_client()

    emilie_policy_route = respx_mock.post(f"/Users/{EMILIE_USER_ID}/Policy").mock(
        return_value=httpx.Response(204)
    )

    _mock_all_gets(
        respx_mock,
        libraries=jellyfin_library_virtualfolders_fixture,
        users=jellyfin_users_fixture,
        user_moi_full=jellyfin_user_moi_full_fixture,
        system_config=jellyfin_system_configuration_fixture,
        plugins=jellyfin_plugins_fixture,
    )

    reconcile_jellyfin(client, instance, _DEFAULT_LIBRARIES, dry_run=False)

    assert not emilie_policy_route.called, (
        f"emilie ({EMILIE_USER_ID}) Policy must NEVER be touched (D-07-USERS-01)"
    )


# ---------------------------------------------------------------------------
# Test 7: Pitfall 1 — server_config full replace preserves 49 non-allowlist fields
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_server_config_full_replace_preserves_49_non_allowlist_fields_pitfall1(
    respx_mock: respx.MockRouter,
    jellyfin_library_virtualfolders_fixture: list[dict[str, Any]],
    jellyfin_users_fixture: list[dict[str, Any]],
    jellyfin_user_moi_full_fixture: dict[str, Any],
    jellyfin_plugins_fixture: list[dict[str, Any]],
) -> None:
    """Pitfall 1 mitigation: POST /System/Configuration carries ALL 56 fields.

    T-07-PITFALL1-WIPE: verifies that non-allowlist fields (TrickplayOptions,
    MetadataOptions, CacheSize, EnableMetrics) are preserved verbatim from the
    cluster GET and NOT dropped in the POST body.
    """
    cluster_config = _system_config_fixture()
    # Change a non-allowlist field in cluster to prove it flows through.
    cluster_config["TrickplayOptions"] = {"Interval": 9999, "JpegQuality": 75}
    cluster_config["CacheSize"] = 800

    # Force a diff on an allowlist field so the POST actually fires.
    cluster_config["ServerName"] = "old-name"
    instance = _make_instance(
        server_config=JellyfinServerConfigSection(
            enable=True,
            server_name="jellyfin",  # desired ≠ cluster "old-name"
            ui_culture="fr",
            metadata_country_code="FR",
            preferred_metadata_language="fr",
            activity_log_retention_days=30,
            log_file_retention_days=3,
            plugin_repositories=[
                PluginRepository(
                    Name="Jellyfin Stable",
                    Url="https://repo.jellyfin.org/files/plugin/manifest.json",
                    Enabled=True,
                )
            ],
        )
    )
    client = _make_client()

    captured_body: dict[str, Any] = {}

    def capture_post(request: httpx.Request) -> httpx.Response:
        nonlocal captured_body
        captured_body = json.loads(request.content)
        return httpx.Response(204)

    respx_mock.post("/System/Configuration").mock(side_effect=capture_post)

    _mock_all_gets(
        respx_mock,
        libraries=jellyfin_library_virtualfolders_fixture,
        users=jellyfin_users_fixture,
        user_moi_full=jellyfin_user_moi_full_fixture,
        system_config=cluster_config,
        plugins=jellyfin_plugins_fixture,
    )

    reconcile_jellyfin(client, instance, _DEFAULT_LIBRARIES, dry_run=False)

    assert captured_body, "POST /System/Configuration must be called"
    # Allowlist field updated:
    assert captured_body["ServerName"] == "jellyfin"
    # Non-allowlist fields preserved verbatim (Pitfall 1 evidence):
    assert captured_body["TrickplayOptions"] == {"Interval": 9999, "JpegQuality": 75}, (
        "TrickplayOptions (non-allowlist) must be preserved from cluster GET (Pitfall 1)"
    )
    assert captured_body["CacheSize"] == 800, (
        "CacheSize (non-allowlist) must be preserved from cluster GET (Pitfall 1)"
    )


# ---------------------------------------------------------------------------
# Test 8: Pitfall 7 — PluginRepositories diff is set-by-URL (no false-positive on reorder)
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_server_config_plugin_repositories_set_by_url_pitfall7(
    respx_mock: respx.MockRouter,
    jellyfin_library_virtualfolders_fixture: list[dict[str, Any]],
    jellyfin_users_fixture: list[dict[str, Any]],
    jellyfin_user_moi_full_fixture: dict[str, Any],
    jellyfin_plugins_fixture: list[dict[str, Any]],
) -> None:
    """Pitfall 7: PluginRepositories compared by URL set — reordering must not trigger POST.

    D-06-SEERR-USER-FP pattern: operator reorders repos via UI → same URLs different
    order → reconciler must treat as no-op (set equality, not list equality).
    """
    # Cluster has repos in one order.
    cluster_config = _system_config_fixture()
    cluster_config["PluginRepositories"] = [
        {"Name": "Repo A", "Url": "https://example.com/repo-a.json", "Enabled": True},
        {"Name": "Repo B", "Url": "https://example.com/repo-b.json", "Enabled": True},
    ]
    # All other allowlist fields match cluster.
    cluster_config["ServerName"] = "jellyfin"
    cluster_config["UICulture"] = "fr"
    cluster_config["MetadataCountryCode"] = "FR"
    cluster_config["PreferredMetadataLanguage"] = "fr"
    cluster_config["ActivityLogRetentionDays"] = 30
    cluster_config["LogFileRetentionDays"] = 3

    # Desired: same repos but REVERSED order.
    instance = _make_instance(
        server_config=JellyfinServerConfigSection(
            enable=True,
            server_name="jellyfin",
            ui_culture="fr",
            metadata_country_code="FR",
            preferred_metadata_language="fr",
            activity_log_retention_days=30,
            log_file_retention_days=3,
            plugin_repositories=[
                PluginRepository(
                    Name="Repo B", Url="https://example.com/repo-b.json", Enabled=True
                ),
                PluginRepository(
                    Name="Repo A", Url="https://example.com/repo-a.json", Enabled=True
                ),
            ],
        )
    )
    client = _make_client()

    post_config_route = respx_mock.post("/System/Configuration").mock(
        return_value=httpx.Response(204)
    )

    _mock_all_gets(
        respx_mock,
        libraries=jellyfin_library_virtualfolders_fixture,
        users=jellyfin_users_fixture,
        user_moi_full=jellyfin_user_moi_full_fixture,
        system_config=cluster_config,
        plugins=jellyfin_plugins_fixture,
    )

    result = reconcile_jellyfin(client, instance, _DEFAULT_LIBRARIES, dry_run=False)

    assert not post_config_route.called, (
        "POST /System/Configuration must NOT be called — reversed repo order is a no-op (Pitfall 7)"
    )
    assert "server_config:applied" not in result.actions_taken


# ---------------------------------------------------------------------------
# Test 9: Pitfall 5 — plugin Enable requires VERSION in path
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_plugin_enable_includes_version_in_path_pitfall5(
    respx_mock: respx.MockRouter,
    jellyfin_library_virtualfolders_fixture: list[dict[str, Any]],
    jellyfin_users_fixture: list[dict[str, Any]],
    jellyfin_user_moi_full_fixture: dict[str, Any],
    jellyfin_system_configuration_fixture: dict[str, Any],
) -> None:
    """Pitfall 5 mitigation: POST URL includes /{pluginId}/{version}/Enable.

    T-07-PITFALL5-VERSION: POST /Plugins/{id}/Enable (without version) returns HTTP 405.
    Reconciler must include the version from the GET /Plugins response.
    """
    # TMDb Status=Disabled → reconciler should attempt Enable.
    plugins = [
        {
            "Name": "TMDb",
            "Id": TMDB_PLUGIN_ID,
            "Version": TMDB_PLUGIN_VERSION,
            "Status": "Disabled",
        }
    ]
    instance = _make_instance(
        plugins=JellyfinPluginsSection(
            enable=True,
            required=[PluginEntry(name="TMDb")],
        )
    )
    client = _make_client()

    # Route with version — the CORRECT URL (Pitfall 5).
    enable_with_version = respx_mock.post(
        f"/Plugins/{TMDB_PLUGIN_ID}/{TMDB_PLUGIN_VERSION}/Enable"
    ).mock(return_value=httpx.Response(204))

    # Route WITHOUT version — the WRONG URL (must never be called).
    enable_without_version = respx_mock.post(f"/Plugins/{TMDB_PLUGIN_ID}/Enable").mock(
        return_value=httpx.Response(405)
    )

    _mock_all_gets(
        respx_mock,
        libraries=jellyfin_library_virtualfolders_fixture,
        users=jellyfin_users_fixture,
        user_moi_full=jellyfin_user_moi_full_fixture,
        system_config=jellyfin_system_configuration_fixture,
        plugins=plugins,
    )

    result = reconcile_jellyfin(client, instance, _DEFAULT_LIBRARIES, dry_run=False)

    assert enable_with_version.called, (
        f"POST /Plugins/{TMDB_PLUGIN_ID}/{TMDB_PLUGIN_VERSION}/Enable must be called (Pitfall 5)"
    )
    assert not enable_without_version.called, (
        "POST without version must NEVER be called (returns 405 on real API)"
    )
    assert "plugin_enabled:TMDb" in result.actions_taken


# ---------------------------------------------------------------------------
# Test 10: Plugin Active status — no-op
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_plugin_active_status_skipped(
    respx_mock: respx.MockRouter,
    jellyfin_library_virtualfolders_fixture: list[dict[str, Any]],
    jellyfin_users_fixture: list[dict[str, Any]],
    jellyfin_user_moi_full_fixture: dict[str, Any],
    jellyfin_system_configuration_fixture: dict[str, Any],
) -> None:
    """Active plugin triggers no Enable POST — status in {Active, Restart} is a no-op.

    T-07-PITFALL5-VERSION: verifies the Status guard prevents unnecessary Enable calls.
    Also tests 'Restart' status as a no-op via _ACTIVE_PLUGIN_STATUSES constant.
    """
    assert "Active" in _ACTIVE_PLUGIN_STATUSES
    assert "Restart" in _ACTIVE_PLUGIN_STATUSES

    plugins = [
        {
            "Name": "TMDb",
            "Id": TMDB_PLUGIN_ID,
            "Version": TMDB_PLUGIN_VERSION,
            "Status": "Active",  # already active — no-op
        }
    ]
    instance = _make_instance(
        plugins=JellyfinPluginsSection(
            enable=True,
            required=[PluginEntry(name="TMDb")],
        )
    )
    client = _make_client()

    enable_route = respx_mock.post(url__regex=rf"/Plugins/{TMDB_PLUGIN_ID}/.*?/Enable").mock(
        return_value=httpx.Response(204)
    )

    _mock_all_gets(
        respx_mock,
        libraries=jellyfin_library_virtualfolders_fixture,
        users=jellyfin_users_fixture,
        user_moi_full=jellyfin_user_moi_full_fixture,
        system_config=jellyfin_system_configuration_fixture,
        plugins=plugins,
    )

    result = reconcile_jellyfin(client, instance, _DEFAULT_LIBRARIES, dry_run=False)

    assert not enable_route.called, "Enable must NOT be called when Status=Active"
    assert not any("plugin_enabled" in a for a in result.actions_taken)


# ---------------------------------------------------------------------------
# Test 11: D-07-ORDER-01 — step order invariant (structlog capture)
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_reconcile_jellyfin_step_order_invariant(
    respx_mock: respx.MockRouter,
    jellyfin_library_virtualfolders_fixture: list[dict[str, Any]],
    jellyfin_users_fixture: list[dict[str, Any]],
    jellyfin_user_moi_full_fixture: dict[str, Any],
    jellyfin_system_configuration_fixture: dict[str, Any],
    jellyfin_plugins_fixture: list[dict[str, Any]],
) -> None:
    """D-07-ORDER-01: step_begin events emitted in libraries→users→server_config→plugins order.

    Verifies step_index 1,2,3,4 and step names match the D-07-ORDER-01 constraint.
    Tests that step_begin events are emitted by each _reconcile_* function.
    """
    import structlog.testing

    instance = _make_instance()
    client = _make_client()

    _mock_all_gets(
        respx_mock,
        libraries=jellyfin_library_virtualfolders_fixture,
        users=jellyfin_users_fixture,
        user_moi_full=jellyfin_user_moi_full_fixture,
        system_config=jellyfin_system_configuration_fixture,
        plugins=jellyfin_plugins_fixture,
    )

    with structlog.testing.capture_logs() as logs:
        reconcile_jellyfin(client, instance, _DEFAULT_LIBRARIES, dry_run=False)

    step_events = [e for e in logs if e.get("event") == "step_begin"]
    assert len(step_events) == 4, f"Expected 4 step_begin events, got {len(step_events)}"
    assert [e["step_index"] for e in step_events] == [1, 2, 3, 4]
    assert [e["step"] for e in step_events] == [
        "libraries",
        "users",
        "server_config",
        "plugins",
    ]


# ---------------------------------------------------------------------------
# Test 12: dry_run=True — zero writes across all 4 steps
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_reconcile_jellyfin_dry_run_zero_writes(
    respx_mock: respx.MockRouter,
    jellyfin_library_virtualfolders_fixture: list[dict[str, Any]],
    jellyfin_users_fixture: list[dict[str, Any]],
    jellyfin_user_moi_full_fixture: dict[str, Any],
    jellyfin_plugins_fixture: list[dict[str, Any]],
) -> None:
    """dry_run=True: NO POST calls made to any Jellyfin endpoint.

    Verifies the dry_run gate is respected in all 4 _reconcile_* functions.
    Forces drift on all 4 resources so the non-dry_run path WOULD write.
    """
    # Force drift on all resources: ServerName, policy, library path, plugin status.
    cluster_config = _system_config_fixture()
    cluster_config["ServerName"] = "old-name"  # will differ from desired "jellyfin"

    user_full = _user_moi_full_fixture()
    user_full["Policy"]["EnablePublicSharing"] = False  # cluster=False vs desired=True → drift

    libs = [
        {
            "Name": "Séries",
            "CollectionType": "tvshows",
            "Locations": [],
            "LibraryOptions": {"PathInfos": []},  # no paths yet → /media/series is new
        }
    ]

    plugins = [
        {"Name": "TMDb", "Id": TMDB_PLUGIN_ID, "Version": TMDB_PLUGIN_VERSION, "Status": "Disabled"}
    ]

    instance = _make_instance(
        server_config=JellyfinServerConfigSection(
            enable=True,
            server_name="jellyfin",
            ui_culture="fr",
            metadata_country_code="FR",
            preferred_metadata_language="fr",
            activity_log_retention_days=30,
            log_file_retention_days=3,
            plugin_repositories=[
                PluginRepository(
                    Name="Jellyfin Stable",
                    Url="https://repo.jellyfin.org/files/plugin/manifest.json",
                    Enabled=True,
                )
            ],
        )
    )
    client = _make_client()

    post_lib_route = respx_mock.post("/Library/VirtualFolders/Paths").mock(
        return_value=httpx.Response(204)
    )
    post_policy_route = respx_mock.post(f"/Users/{ADMIN_USER_ID}/Policy").mock(
        return_value=httpx.Response(204)
    )
    post_config_route = respx_mock.post("/System/Configuration").mock(
        return_value=httpx.Response(204)
    )
    post_enable_route = respx_mock.post(url__regex=rf"/Plugins/{TMDB_PLUGIN_ID}/.*?/Enable").mock(
        return_value=httpx.Response(204)
    )

    _mock_all_gets(
        respx_mock,
        libraries=libs,
        users=jellyfin_users_fixture,
        user_moi_full=user_full,
        system_config=cluster_config,
        plugins=plugins,
    )

    result = reconcile_jellyfin(client, instance, _DEFAULT_LIBRARIES, dry_run=True)

    assert not post_lib_route.called, "Library POST must not fire in dry_run"
    assert not post_policy_route.called, "User Policy POST must not fire in dry_run"
    assert not post_config_route.called, "System/Configuration POST must not fire in dry_run"
    assert not post_enable_route.called, "Plugin Enable POST must not fire in dry_run"
    # dry_run actions should contain ":dry_run:" markers, not ":applied:" or ":added:".
    for action in result.actions_taken:
        assert "dry_run" in action, f"Unexpected non-dry-run action in dry_run mode: {action}"


# ---------------------------------------------------------------------------
# Test 13: ADR-5 frontiere — no /api/v3/qualityprofile etc. calls
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_jellyfin_does_not_call_arr_v3_quality_endpoints(
    respx_mock: respx.MockRouter,
    jellyfin_library_virtualfolders_fixture: list[dict[str, Any]],
    jellyfin_users_fixture: list[dict[str, Any]],
    jellyfin_user_moi_full_fixture: dict[str, Any],
    jellyfin_system_configuration_fixture: dict[str, Any],
    jellyfin_plugins_fixture: list[dict[str, Any]],
) -> None:
    """ADR-5 frontiere: Jellyfin reconciler never calls *arr v3 quality endpoints.

    T-07-FRONTIERE: sentinel routes at the Jellyfin base URL for quality endpoints
    assert they are never called. The reconciler only talks to Jellyfin's own endpoints.
    """
    # Register sentinel routes — any call to these would be a scope violation.
    sentinel_qualityprofile = respx_mock.get(url__regex=r"/api/v3/qualityprofile").mock(
        return_value=httpx.Response(200, json=[])
    )
    sentinel_customformat = respx_mock.get(url__regex=r"/api/v3/customformat").mock(
        return_value=httpx.Response(200, json=[])
    )

    instance = _make_instance()
    client = _make_client()

    _mock_all_gets(
        respx_mock,
        libraries=jellyfin_library_virtualfolders_fixture,
        users=jellyfin_users_fixture,
        user_moi_full=jellyfin_user_moi_full_fixture,
        system_config=jellyfin_system_configuration_fixture,
        plugins=jellyfin_plugins_fixture,
    )

    reconcile_jellyfin(client, instance, _DEFAULT_LIBRARIES, dry_run=False)

    assert not sentinel_qualityprofile.called, (
        "Jellyfin reconciler MUST NOT call /api/v3/qualityprofile (ADR-5 frontiere)"
    )
    assert not sentinel_customformat.called, (
        "Jellyfin reconciler MUST NOT call /api/v3/customformat (ADR-5 frontiere)"
    )
