"""Tests for Intro Skipper install/config logic in reconcile_jellyfin (Phase 24 Plan 02).

JFSKIP-02: Install when absent (two-run model, D-01/D-02), distinguish queued-install vs active.
JFSKIP-03: Intro+credits config applied with MaxParallelism=1, idempotent, dry-run-safe.

All 7 plugin install/config scenarios are covered here.
Pre-existing plugin tests live in test_reconcilers_jellyfin.py.

D-01 reversal: plugin_install_queued when absent + install fields set (JFSKIP-02)
D-02: no enable/config in same run as install
D-04/D-05: plugin config GET+diff+POST after restart (run N+1)
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from arrconf.client_base import JellyfinClient
from arrconf.config import (
    JellyfinInstance,
    JellyfinLibrariesSection,
    JellyfinPluginsSection,
    JellyfinServerConfigSection,
    JellyfinUsersSection,
)
from arrconf.reconcilers.jellyfin import reconcile_jellyfin
from arrconf.resources.jellyfin import (
    JellyfinLibrary,
    JellyfinUserPolicy,
    PluginEntry,
    PluginRepository,
)
from arrconf.resources.jellyfin.plugin import IntroSkipperConfig

JELLYFIN_BASE = "http://jellyfin.test:8096"
INTRO_SKIPPER_GUID = "c83d86bb-a1e0-4c35-a113-e2101cf4ee6b"
INTRO_SKIPPER_VERSION = "1.10.11.19"
INTRO_SKIPPER_REPO = "https://intro-skipper.org/manifest.json"
ADMIN_USER_ID = "82fd95db72904569b08d83271823ceaa"
DEFAULT_AUTH_PROVIDER = "Jellyfin.Server.Implementations.Users.DefaultAuthenticationProvider"
DEFAULT_PWD_PROVIDER = "Jellyfin.Server.Implementations.Users.DefaultPasswordResetProvider"

_DEFAULT_LIBRARIES = [
    JellyfinLibrary(name="Séries", collection_type="tvshows", paths=["/media/series"]),
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _plugins_no_intro_skipper() -> list[dict[str, Any]]:
    """GET /Plugins — Intro Skipper absent (pre-install, Run N)."""
    return [
        {
            "Name": "TMDb",
            "Id": "b8715ed16c4745289ad3f72deb539cd4",
            "Version": "10.11.8.0",
            "Status": "Active",
        },
        {
            "Name": "Kodi Sync Queue",
            "Id": "771e19d653854cafb35c28a0e865cf63",
            "Version": "15.0.0.0",
            "Status": "Active",
        },
    ]


def _plugins_with_intro_skipper_active() -> list[dict[str, Any]]:
    """GET /Plugins — Intro Skipper present + Active (post-restart, Run N+1)."""
    return [
        {
            "Name": "TMDb",
            "Id": "b8715ed16c4745289ad3f72deb539cd4",
            "Version": "10.11.8.0",
            "Status": "Active",
        },
        {
            "Name": "Intro Skipper",
            "Id": INTRO_SKIPPER_GUID,
            "Version": INTRO_SKIPPER_VERSION,
            "Status": "Active",
        },
    ]


def _plugins_with_intro_skipper_not_active() -> list[dict[str, Any]]:
    """GET /Plugins — Intro Skipper present but Disabled (post-install, pre-restart)."""
    return [
        {
            "Name": "TMDb",
            "Id": "b8715ed16c4745289ad3f72deb539cd4",
            "Version": "10.11.8.0",
            "Status": "Active",
        },
        {
            "Name": "Intro Skipper",
            "Id": INTRO_SKIPPER_GUID,
            "Version": INTRO_SKIPPER_VERSION,
            "Status": "Disabled",
        },
    ]


def _library_fixture() -> list[dict[str, Any]]:
    return [
        {
            "Name": "Séries",
            "ItemId": "d565273fd114d77bdf349a2896867069",
            "CollectionType": "tvshows",
            "Locations": ["/media/series"],
            "LibraryOptions": {"PathInfos": [{"Path": "/media/series"}]},
        },
    ]


def _users_fixture() -> list[dict[str, Any]]:
    return [
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
            "EnablePublicSharing": True,
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
            "AuthenticationProviderId": DEFAULT_AUTH_PROVIDER,
            "PasswordResetProviderId": DEFAULT_PWD_PROVIDER,
        },
    }


def _system_config_fixture() -> dict[str, Any]:
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
        "CacheSize": 600,
    }


def _intro_skipper_plugin_config_cluster() -> dict[str, Any]:
    """GET /Plugins/{id}/Configuration response — default cluster state (no custom config)."""
    return {
        "AutoSkip": False,
        "AutoSkipCredits": False,
        "MaxParallelism": 3,  # differs from desired (1) → should trigger a POST
        "SkipButtonEndTimePadding": 5,
        "SkipButtonStartTimePadding": 10,
    }


def _intro_skipper_plugin_config_matching() -> dict[str, Any]:
    """GET /Plugins/{id}/Configuration — already matches desired config (no-op)."""
    return {
        "AutoSkip": False,
        "AutoSkipCredits": False,
        "MaxParallelism": 1,  # matches desired → no-op
        "SkipButtonEndTimePadding": 5,
        "SkipButtonStartTimePadding": 10,
    }


# ---------------------------------------------------------------------------
# Client + Instance builders
# ---------------------------------------------------------------------------


def _make_client() -> JellyfinClient:
    return JellyfinClient(base_url=JELLYFIN_BASE, api_key="test-api-key")


def _make_instance_with_intro_skipper(**overrides: Any) -> JellyfinInstance:
    """Build a JellyfinInstance with Intro Skipper in plugins.required."""
    defaults: dict[str, Any] = dict(
        base_url=JELLYFIN_BASE,
        libraries=JellyfinLibrariesSection(enable=True),
        users=JellyfinUsersSection(
            enable=True,
            admin=JellyfinUserPolicy(
                IsAdministrator=True,
                EnableContentDeletion=True,
                EnableRemoteControlOfOtherUsers=True,
                EnablePublicSharing=True,
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
                PluginEntry(
                    name="Intro Skipper",
                    install_guid=INTRO_SKIPPER_GUID,
                    install_version=INTRO_SKIPPER_VERSION,
                    install_repo_url=INTRO_SKIPPER_REPO,
                    config=IntroSkipperConfig(
                        AutoSkip=False,
                        AutoSkipCredits=False,
                        MaxParallelism=1,
                    ),
                )
            ],
        ),
    )
    defaults.update(overrides)
    return JellyfinInstance(**defaults)


def _mock_all_gets(
    respx_mock: respx.MockRouter,
    plugins: list[dict[str, Any]] | None = None,
) -> None:
    """Mock all Jellyfin GET endpoints (minimal fixture set for plugin tests)."""
    respx_mock.get("/Library/VirtualFolders").mock(
        return_value=httpx.Response(200, json=_library_fixture())
    )
    respx_mock.get("/Users").mock(return_value=httpx.Response(200, json=_users_fixture()))
    respx_mock.get(f"/Users/{ADMIN_USER_ID}").mock(
        return_value=httpx.Response(200, json=_user_moi_full_fixture())
    )
    respx_mock.get("/System/Configuration").mock(
        return_value=httpx.Response(200, json=_system_config_fixture())
    )
    respx_mock.get("/Plugins").mock(
        return_value=httpx.Response(
            200,
            json=plugins if plugins is not None else _plugins_no_intro_skipper(),
        )
    )


# ---------------------------------------------------------------------------
# Test 1: plugin_install_queued when plugin absent + install fields set
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_plugin_install_queued_when_absent(respx_mock: respx.MockRouter) -> None:
    """D-01/D-02: POST /Packages/Installed fired when plugin absent + install fields present.

    JFSKIP-02: install queued, action=plugin_install_queued; no enable/config same run.
    Query params: assemblyGuid, version, repositoryUrl must match arrconf.yml values.
    """
    install_route = respx_mock.post(
        url__regex=r"/Packages/Installed/Intro%20Skipper|/Packages/Installed/Intro Skipper"
    ).mock(return_value=httpx.Response(204))

    _mock_all_gets(respx_mock, plugins=_plugins_no_intro_skipper())

    client = _make_client()
    instance = _make_instance_with_intro_skipper()
    result = reconcile_jellyfin(client, instance, _DEFAULT_LIBRARIES, dry_run=False)

    assert install_route.called, "POST /Packages/Installed should have been called"
    assert "plugin_install_queued:Intro Skipper" in result.actions_taken

    req = install_route.calls[0].request
    assert req.url.params["assemblyGuid"] == INTRO_SKIPPER_GUID
    assert req.url.params["version"] == INTRO_SKIPPER_VERSION
    assert req.url.params["repositoryUrl"] == INTRO_SKIPPER_REPO

    # D-02: no enable/config in same run
    assert not any("plugin_enabled" in a for a in result.actions_taken)
    assert not any("plugin_config" in a for a in result.actions_taken)


# ---------------------------------------------------------------------------
# Test 2: install idempotent when plugin already present
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_plugin_install_idempotent_when_present(respx_mock: respx.MockRouter) -> None:
    """Run N+1: plugin present → no install POST; goes to enable/config path."""
    install_route = respx_mock.post(url__regex=r"/Packages/Installed/.*").mock(
        return_value=httpx.Response(204)
    )

    # Mock config GET/POST for active plugin
    respx_mock.get(f"/Plugins/{INTRO_SKIPPER_GUID}/Configuration").mock(
        return_value=httpx.Response(200, json=_intro_skipper_plugin_config_cluster())
    )
    respx_mock.post(f"/Plugins/{INTRO_SKIPPER_GUID}/Configuration").mock(
        return_value=httpx.Response(204)
    )

    _mock_all_gets(respx_mock, plugins=_plugins_with_intro_skipper_active())

    client = _make_client()
    instance = _make_instance_with_intro_skipper()
    result = reconcile_jellyfin(client, instance, _DEFAULT_LIBRARIES, dry_run=False)

    assert not install_route.called, "Install POST must NOT be called when plugin already present"
    # plugin already active so plugin_already_active path — no plugin_enabled action
    assert not any("plugin_install_queued" in a for a in result.actions_taken)


# ---------------------------------------------------------------------------
# Test 3: no action when install fields absent (bare PluginEntry — old behavior)
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_plugin_install_no_action_when_install_fields_absent(
    respx_mock: respx.MockRouter,
) -> None:
    """PluginEntry without install fields → plugin_missing_skip path (D-07-PLUGINS-01 legacy)."""
    install_route = respx_mock.post(url__regex=r"/Packages/Installed/.*").mock(
        return_value=httpx.Response(204)
    )

    _mock_all_gets(respx_mock, plugins=_plugins_no_intro_skipper())

    client = _make_client()
    # Bare PluginEntry — no install_guid/version/repo
    instance = _make_instance_with_intro_skipper(
        plugins=JellyfinPluginsSection(
            enable=True,
            required=[PluginEntry(name="Intro Skipper")],
        )
    )
    result = reconcile_jellyfin(client, instance, _DEFAULT_LIBRARIES, dry_run=False)

    assert not install_route.called, "Install POST must NOT be called without install fields"
    assert not any("plugin_install_queued" in a for a in result.actions_taken)


# ---------------------------------------------------------------------------
# Test 4: dry_run=True — zero writes
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_plugin_install_dry_run_no_post(respx_mock: respx.MockRouter) -> None:
    """dry_run=True: no install POST; action contains 'dry_run'."""
    install_route = respx_mock.post(url__regex=r"/Packages/Installed/.*").mock(
        return_value=httpx.Response(204)
    )

    _mock_all_gets(respx_mock, plugins=_plugins_no_intro_skipper())

    client = _make_client()
    instance = _make_instance_with_intro_skipper()
    result = reconcile_jellyfin(client, instance, _DEFAULT_LIBRARIES, dry_run=True)

    assert not install_route.called, "Install POST must NOT be called in dry_run mode"
    # dry_run actions should have 'dry_run' in them, not real actions
    plugin_actions = [a for a in result.actions_taken if "plugin_install" in a]
    assert any("dry_run" in a for a in plugin_actions), (
        f"Expected dry_run action for plugin_install, got: {plugin_actions}"
    )


# ---------------------------------------------------------------------------
# Test 5: plugin_config_applied when plugin Active + config differs
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_plugin_config_applied_when_plugin_active(respx_mock: respx.MockRouter) -> None:
    """JFSKIP-03: GET+diff+POST /Plugins/{id}/Configuration when Active and config drifted.

    Cluster has MaxParallelism=3 (differs from desired=1) → POST fires.
    Body must contain AutoSkip, AutoSkipCredits, MaxParallelism.
    """
    captured_body: dict[str, Any] = {}

    def capture_config_post(request: httpx.Request) -> httpx.Response:
        nonlocal captured_body
        captured_body = json.loads(request.content)
        return httpx.Response(204)

    respx_mock.get(f"/Plugins/{INTRO_SKIPPER_GUID}/Configuration").mock(
        return_value=httpx.Response(200, json=_intro_skipper_plugin_config_cluster())
    )
    config_post_route = respx_mock.post(f"/Plugins/{INTRO_SKIPPER_GUID}/Configuration").mock(
        side_effect=capture_config_post
    )

    _mock_all_gets(respx_mock, plugins=_plugins_with_intro_skipper_active())

    client = _make_client()
    instance = _make_instance_with_intro_skipper()
    result = reconcile_jellyfin(client, instance, _DEFAULT_LIBRARIES, dry_run=False)

    assert config_post_route.called, "POST /Plugins/{id}/Configuration should have been called"
    assert "plugin_config_applied:Intro Skipper" in result.actions_taken
    assert captured_body.get("AutoSkip") is False
    assert captured_body.get("AutoSkipCredits") is False
    assert captured_body.get("MaxParallelism") == 1


# ---------------------------------------------------------------------------
# Test 6: plugin_config_no_op when config already matches
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_plugin_config_no_op_when_already_matches(respx_mock: respx.MockRouter) -> None:
    """Config already matches desired → no POST (idempotent, no-op)."""
    config_post_route = respx_mock.post(f"/Plugins/{INTRO_SKIPPER_GUID}/Configuration").mock(
        return_value=httpx.Response(204)
    )
    respx_mock.get(f"/Plugins/{INTRO_SKIPPER_GUID}/Configuration").mock(
        return_value=httpx.Response(200, json=_intro_skipper_plugin_config_matching())
    )

    _mock_all_gets(respx_mock, plugins=_plugins_with_intro_skipper_active())

    client = _make_client()
    instance = _make_instance_with_intro_skipper()
    result = reconcile_jellyfin(client, instance, _DEFAULT_LIBRARIES, dry_run=False)

    assert not config_post_route.called, "Config POST must NOT be called when config matches"
    assert not any("plugin_config_applied" in a for a in result.actions_taken)


# ---------------------------------------------------------------------------
# Test 7: plugin_config_skipped when plugin not Active (post-install, pre-restart)
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_plugin_config_skipped_when_plugin_not_active(respx_mock: respx.MockRouter) -> None:
    """Two-run model: config only applied after restart+Active; not when Status=Disabled.

    D-02: post-install (Status=Disabled) → enable fires but config is skipped.
    Run N+1 after restart applies config.
    """
    # Plugin is Disabled → enable step fires (version in path per Pitfall 5)
    respx_mock.post(
        url__regex=rf"/Plugins/{INTRO_SKIPPER_GUID}/{INTRO_SKIPPER_VERSION}/Enable"
    ).mock(return_value=httpx.Response(204))

    config_get_route = respx_mock.get(f"/Plugins/{INTRO_SKIPPER_GUID}/Configuration").mock(
        return_value=httpx.Response(200, json=_intro_skipper_plugin_config_cluster())
    )
    config_post_route = respx_mock.post(f"/Plugins/{INTRO_SKIPPER_GUID}/Configuration").mock(
        return_value=httpx.Response(204)
    )

    _mock_all_gets(respx_mock, plugins=_plugins_with_intro_skipper_not_active())

    client = _make_client()
    instance = _make_instance_with_intro_skipper()
    result = reconcile_jellyfin(client, instance, _DEFAULT_LIBRARIES, dry_run=False)

    # Config GET/POST must NOT fire when plugin is not Active (D-02)
    assert not config_get_route.called, "Config GET must not fire when plugin not Active"
    assert not config_post_route.called, "Config POST must not fire when plugin not Active"
    assert not any("plugin_config" in a for a in result.actions_taken)
