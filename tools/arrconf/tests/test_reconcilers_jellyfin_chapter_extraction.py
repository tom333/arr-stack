"""Tests for chapter-image-extraction reconciler logic (Phase 24, JFSKIP-04, D-06).

Covers:
  - New library with enable_chapter_image_extraction=True: POST /Library/VirtualFolders body
  - Existing library, cluster EnableChapterImageExtraction=False, desired=True: update POST
  - Existing library already True: no-op (idempotent)
  - dry_run=True: zero writes

All Jellyfin endpoints mocked via respx — NEVER calls a real Jellyfin instance.
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
    PluginRepository,
)

JELLYFIN_BASE = "http://jellyfin.test:8096"
ADMIN_USER_ID = "82fd95db72904569b08d83271823ceaa"
DEFAULT_AUTH_PROVIDER = "Jellyfin.Server.Implementations.Users.DefaultAuthenticationProvider"
DEFAULT_PWD_PROVIDER = "Jellyfin.Server.Implementations.Users.DefaultPasswordResetProvider"


# ---------------------------------------------------------------------------
# Helpers — client and instance builders
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
                EnableRemoteControlOfOtherUsers=False,
                EnablePublicSharing=False,
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
        plugins=JellyfinPluginsSection(enable=False, required=[]),
    )
    defaults.update(overrides)
    return JellyfinInstance(**defaults)


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
            "EnablePublicSharing": False,
            "BlockedTags": [],
            "AllowedTags": [],
            "BlockedChannels": [],
            "BlockedMediaFolders": [],
            "EnableUserPreferenceAccess": True,
            "AccessSchedules": [],
            "BlockUnratedItems": [],
            "EnableRemoteControlOfOtherUsers": False,
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
    }


def _plugins_fixture() -> list[dict[str, Any]]:
    return []


def _mock_all_gets(
    respx_mock: respx.MockRouter,
    libraries: list[dict[str, Any]] | None = None,
    users: list[dict[str, Any]] | None = None,
    user_moi_full: dict[str, Any] | None = None,
    system_config: dict[str, Any] | None = None,
    plugins: list[dict[str, Any]] | None = None,
) -> None:
    """Mock all Jellyfin GET endpoints used by reconcile_jellyfin."""
    libs = libraries if libraries is not None else []
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
# Test 1: New library with enable_chapter_image_extraction=True
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_chapter_extraction_enabled_on_library_create(
    respx_mock: respx.MockRouter,
) -> None:
    """D-06: POST /Library/VirtualFolders body carries LibraryOptions on chapter extraction."""
    captured_body: dict[str, Any] = {}

    def capture_post(request: httpx.Request) -> httpx.Response:
        nonlocal captured_body
        try:
            captured_body = json.loads(request.content)
        except Exception:
            captured_body = {}
        return httpx.Response(204)

    # Register POST route with capture BEFORE _mock_all_gets
    respx_mock.post("/Library/VirtualFolders").mock(side_effect=capture_post)

    # No existing libraries in cluster (new library case)
    _mock_all_gets(respx_mock, libraries=[])

    client = _make_client()
    desired_libs = [
        JellyfinLibrary(
            name="Séries",
            collection_type="tvshows",
            paths=["/media/series"],
            enable_chapter_image_extraction=True,
        )
    ]
    instance = _make_instance(libraries=JellyfinLibrariesSection(enable=True))

    result = reconcile_jellyfin(client, instance, desired_libs, dry_run=False)

    # Verify body has LibraryOptions with EnableChapterImageExtraction
    assert "LibraryOptions" in captured_body, (
        f"Expected LibraryOptions in body, got: {captured_body}"
    )
    assert captured_body["LibraryOptions"]["EnableChapterImageExtraction"] is True
    assert any("library_created:Séries" in a for a in result.actions_taken)


# ---------------------------------------------------------------------------
# Test 2: Existing library, cluster EnableChapterImageExtraction=False → update
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_chapter_extraction_update_existing_library(
    respx_mock: respx.MockRouter,
) -> None:
    """D-06: POST /Library/VirtualFolders/LibraryOptions when cluster=False, desired=True."""
    lib_options_route = respx_mock.post("/Library/VirtualFolders/LibraryOptions").mock(
        return_value=httpx.Response(204)
    )

    # Existing library with EnableChapterImageExtraction=False
    existing_libs = [
        {
            "Name": "Séries",
            "ItemId": "abc123",
            "CollectionType": "tvshows",
            "Locations": ["/media/series"],
            "LibraryOptions": {
                "PathInfos": [{"Path": "/media/series"}],
                "EnableChapterImageExtraction": False,
            },
        }
    ]
    _mock_all_gets(respx_mock, libraries=existing_libs)

    client = _make_client()
    desired_libs = [
        JellyfinLibrary(
            name="Séries",
            collection_type="tvshows",
            paths=["/media/series"],
            enable_chapter_image_extraction=True,
        )
    ]
    instance = _make_instance(libraries=JellyfinLibrariesSection(enable=True))

    result = reconcile_jellyfin(client, instance, desired_libs, dry_run=False)

    assert lib_options_route.called, (
        "Expected POST /Library/VirtualFolders/LibraryOptions to be called"
    )
    assert any("library_options_updated:Séries" in a for a in result.actions_taken)


# ---------------------------------------------------------------------------
# Test 3: No-op when already enabled
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_chapter_extraction_no_op_when_already_enabled(
    respx_mock: respx.MockRouter,
) -> None:
    """D-06: No POST when cluster EnableChapterImageExtraction already matches desired."""
    lib_options_route = respx_mock.post("/Library/VirtualFolders/LibraryOptions").mock(
        return_value=httpx.Response(204)
    )

    # Existing library with EnableChapterImageExtraction already True
    existing_libs = [
        {
            "Name": "Séries",
            "ItemId": "abc123",
            "CollectionType": "tvshows",
            "Locations": ["/media/series"],
            "LibraryOptions": {
                "PathInfos": [{"Path": "/media/series"}],
                "EnableChapterImageExtraction": True,
            },
        }
    ]
    _mock_all_gets(respx_mock, libraries=existing_libs)

    client = _make_client()
    desired_libs = [
        JellyfinLibrary(
            name="Séries",
            collection_type="tvshows",
            paths=["/media/series"],
            enable_chapter_image_extraction=True,
        )
    ]
    instance = _make_instance(libraries=JellyfinLibrariesSection(enable=True))

    result = reconcile_jellyfin(client, instance, desired_libs, dry_run=False)

    assert not lib_options_route.called, (
        "Expected no POST /Library/VirtualFolders/LibraryOptions (no-op)"
    )
    assert not any("library_options_updated" in a for a in result.actions_taken)


# ---------------------------------------------------------------------------
# Test 4: dry_run=True → zero writes
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_chapter_extraction_dry_run_no_post(
    respx_mock: respx.MockRouter,
) -> None:
    """dry_run=True: no POST, all chapter actions contain 'dry_run'."""
    lib_options_route = respx_mock.post("/Library/VirtualFolders/LibraryOptions").mock(
        return_value=httpx.Response(204)
    )
    create_route = respx_mock.post("/Library/VirtualFolders").mock(return_value=httpx.Response(204))

    # Existing library with EnableChapterImageExtraction=False — would trigger update
    existing_libs = [
        {
            "Name": "Séries",
            "ItemId": "abc123",
            "CollectionType": "tvshows",
            "Locations": ["/media/series"],
            "LibraryOptions": {
                "PathInfos": [{"Path": "/media/series"}],
                "EnableChapterImageExtraction": False,
            },
        }
    ]
    _mock_all_gets(respx_mock, libraries=existing_libs)

    client = _make_client()
    desired_libs = [
        JellyfinLibrary(
            name="Séries",
            collection_type="tvshows",
            paths=["/media/series"],
            enable_chapter_image_extraction=True,
        )
    ]
    instance = _make_instance(libraries=JellyfinLibrariesSection(enable=True))

    result = reconcile_jellyfin(client, instance, desired_libs, dry_run=True)

    assert not lib_options_route.called, "dry_run: expected no POST"
    assert not create_route.called, "dry_run: expected no create POST"
    # All chapter-related actions should indicate dry_run
    chapter_actions = [a for a in result.actions_taken if "library_options" in a]
    for action in chapter_actions:
        assert "dry_run" in action, f"Expected dry_run in action '{action}'"
