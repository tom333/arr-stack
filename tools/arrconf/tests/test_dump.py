"""Tests for arrconf.dump — jellyfin dump additions (Phase 7).

Tests verify the round-trip property for dump_jellyfin:
1. Modeline emitted as line 1 (D-16).
2. Round-trip via load_config produces semantically equivalent JellyfinInstance.
3. All 4 resources serialised (libraries, users, server_config, plugins).
4. Pitfall 6: AuthenticationProviderId + PasswordResetProviderId NOT in YAML output.
5. Pitfall 5: plugins.required entries carry name+id only, NEVER version.
6. server_config emits only 7 allowlist keys (non-allowlist fields omitted).

SC#4 unit-layer mirror: dump_jellyfin → load_config → diff_jellyfin returns 0
(exercised in test_diff_cmd.py::test_diff_jellyfin_round_trip_with_dump).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from arrconf.client_base import JellyfinClient
from arrconf.config import load_config
from arrconf.dump import dump_jellyfin

JELLYFIN_BASE = "http://jellyfin.test:8096"
ADMIN_USER_ID = "82fd95db72904569b08d83271823ceaa"
TMDB_ID = "b8715ed16c4745289ad3f72deb539cd4"
TMDB_VERSION = "10.11.8.0"


def _make_client() -> JellyfinClient:
    return JellyfinClient(base_url=JELLYFIN_BASE, api_key="test-api-key")


def _mock_cluster(respx_mock: respx.MockRouter) -> None:
    """Mock all 5 Jellyfin GET endpoints for a minimal realistic cluster state."""
    respx_mock.get("/Library/VirtualFolders").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "Name": "Séries",
                    "CollectionType": "tvshows",
                    "Locations": ["/media/series"],
                    "LibraryOptions": {"PathInfos": [{"Path": "/media/series"}]},
                },
                {
                    "Name": "Films",
                    "CollectionType": "movies",
                    "Locations": ["/media/films"],
                    "LibraryOptions": {"PathInfos": [{"Path": "/media/films"}]},
                },
            ],
        )
    )
    respx_mock.get("/Users").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "Name": "moi",
                    "Id": ADMIN_USER_ID,
                    "Policy": {
                        "IsAdministrator": True,
                        "AuthenticationProviderId": (
                            "Jellyfin.Server.Implementations.Users"
                            ".DefaultAuthenticationProvider"
                        ),
                        "PasswordResetProviderId": (
                            "Jellyfin.Server.Implementations.Users"
                            ".DefaultPasswordResetProvider"
                        ),
                    },
                }
            ],
        )
    )
    # Full per-user GET with Pitfall 6 fields that MUST be stripped from dump.
    user_policy: dict[str, Any] = {
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
        # Pitfall 6 fields — must be stripped from dump output:
        "AuthenticationProviderId": (
            "Jellyfin.Server.Implementations.Users.DefaultAuthenticationProvider"
        ),
        "PasswordResetProviderId": (
            "Jellyfin.Server.Implementations.Users.DefaultPasswordResetProvider"
        ),
    }
    respx_mock.get(f"/Users/{ADMIN_USER_ID}").mock(
        return_value=httpx.Response(
            200,
            json={"Name": "moi", "Id": ADMIN_USER_ID, "Policy": user_policy},
        )
    )
    respx_mock.get("/System/Configuration").mock(
        return_value=httpx.Response(
            200,
            json={
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
                # Non-allowlist fields (must NOT appear in dump output):
                "TrickplayOptions": {"Interval": 10000},
                "CacheSize": 600,
            },
        )
    )
    respx_mock.get("/Plugins").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "Name": "TMDb",
                    "Id": TMDB_ID,
                    "Version": TMDB_VERSION,
                    "Status": "Active",
                },
                {
                    "Name": "Kodi Sync Queue",
                    "Id": "771e19d653854cafb35c28a0e865cf63",
                    "Version": "15.0.0.0",
                    "Status": "Active",
                },
            ],
        )
    )


# ---------------------------------------------------------------------------
# Test 1: modeline on line 1 (D-16)
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_dump_jellyfin_writes_yaml_modeline(
    respx_mock: respx.MockRouter,
    tmp_path: Path,
) -> None:
    """dump_jellyfin must write '# yaml-language-server: $schema=...' as line 1 (D-16)."""
    _mock_cluster(respx_mock)

    client = _make_client()
    out = tmp_path / "jelly.yml"
    dump_jellyfin(client, out)

    txt = out.read_text()
    first_line = txt.splitlines()[0]
    assert first_line.startswith("# yaml-language-server: $schema="), (
        f"Expected D-16 modeline as first line, got: {first_line!r}"
    )
    assert "jellyfin:" in txt
    assert "main:" in txt


# ---------------------------------------------------------------------------
# Test 2: round-trip via load_config
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_dump_jellyfin_round_trip_via_load_config(
    respx_mock: respx.MockRouter,
    tmp_path: Path,
) -> None:
    """dump_jellyfin → load_config → JellyfinInstance must be fully populated.

    SC#4 unit-layer mirror: the dumped YAML is semantically equivalent to the
    cluster state. load_config must produce a valid JellyfinInstance.
    """
    _mock_cluster(respx_mock)

    client = _make_client()
    out = tmp_path / "jelly.yml"
    dump_jellyfin(client, out)

    root = load_config(out)
    assert "main" in root.jellyfin, "jellyfin.main must be present in reloaded RootConfig"
    inst = root.jellyfin["main"]
    assert inst.base_url == JELLYFIN_BASE
    # Libraries round-tripped
    assert inst.libraries.enable is True
    assert len(inst.libraries.items) == 2
    assert inst.libraries.items[0].name == "Séries"
    assert "/media/series" in inst.libraries.items[0].paths
    # Users round-tripped (admin policy present)
    assert inst.users.enable is True
    assert inst.users.admin.IsAdministrator is True
    # Server config round-tripped (7 allowlist keys)
    assert inst.server_config.enable is True
    assert inst.server_config.ui_culture == "fr"
    assert inst.server_config.server_name == "jellyfin"
    assert len(inst.server_config.plugin_repositories) == 1
    # Plugins round-tripped (name + id, no version)
    assert inst.plugins.enable is True
    assert len(inst.plugins.required) == 2
    assert inst.plugins.required[0].name == "TMDb"
    assert inst.plugins.required[0].id == TMDB_ID


# ---------------------------------------------------------------------------
# Test 3: 4 resources serialised — none missing from YAML output
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_dump_jellyfin_serialises_4_resources(
    respx_mock: respx.MockRouter,
    tmp_path: Path,
) -> None:
    """All 4 Jellyfin resources must appear under jellyfin.main in the YAML output."""
    _mock_cluster(respx_mock)

    client = _make_client()
    out = tmp_path / "jelly.yml"
    dump_jellyfin(client, out)

    txt = out.read_text()
    assert "libraries:" in txt, "libraries block missing from dump output"
    assert "users:" in txt, "users block missing from dump output"
    assert "server_config:" in txt, "server_config block missing from dump output"
    assert "plugins:" in txt, "plugins block missing from dump output"


# ---------------------------------------------------------------------------
# Test 4: Pitfall 6 — AuthenticationProviderId + PasswordResetProviderId NOT in YAML
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_dump_jellyfin_strips_pitfall6_fields(
    respx_mock: respx.MockRouter,
    tmp_path: Path,
) -> None:
    """Pitfall 6: dump MUST NOT emit AuthenticationProviderId or PasswordResetProviderId.

    These 2 fields are OpenAPI-required at apply time and re-injected from cluster GET.
    """
    _mock_cluster(respx_mock)

    client = _make_client()
    out = tmp_path / "jelly.yml"
    dump_jellyfin(client, out)

    txt = out.read_text()
    assert "AuthenticationProviderId" not in txt, (
        "Pitfall 6 violation: AuthenticationProviderId must NOT appear in dump YAML"
    )
    assert "PasswordResetProviderId" not in txt, (
        "Pitfall 6 violation: PasswordResetProviderId must NOT appear in dump YAML"
    )


# ---------------------------------------------------------------------------
# Test 5: Pitfall 5 — plugins.required entries have name+id only, no version
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_dump_jellyfin_plugins_no_version(
    respx_mock: respx.MockRouter,
    tmp_path: Path,
) -> None:
    """Pitfall 5: dump must emit name+id for plugins but NEVER the version field.

    Version is re-resolved from cluster GET at apply time (/Plugins/{id}/{version}/Enable).
    """
    _mock_cluster(respx_mock)

    client = _make_client()
    out = tmp_path / "jelly.yml"
    dump_jellyfin(client, out)

    root = load_config(out)
    inst = root.jellyfin["main"]
    for entry in inst.plugins.required:
        assert entry.id is not None and entry.id != "", (
            f"Plugin {entry.name} must have an id in dump output"
        )
    txt = out.read_text()
    # The TMDb version string must NOT appear in the YAML output.
    assert TMDB_VERSION not in txt, (
        f"Pitfall 5: plugin version {TMDB_VERSION!r} must NOT be emitted in dump YAML"
    )


# ---------------------------------------------------------------------------
# Test 6: server_config emits only 7 allowlist keys (non-allowlist fields omitted)
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_dump_jellyfin_server_config_7_allowlist_only(
    respx_mock: respx.MockRouter,
    tmp_path: Path,
) -> None:
    """Server config dump emits only the 7 D-07-CONFIG-01 allowlist keys.

    Non-allowlist fields (TrickplayOptions, CacheSize, etc.) must NOT appear in YAML.
    """
    _mock_cluster(respx_mock)

    client = _make_client()
    out = tmp_path / "jelly.yml"
    dump_jellyfin(client, out)

    txt = out.read_text()
    assert "TrickplayOptions" not in txt, "Non-allowlist field must NOT be in server_config dump"
    assert "CacheSize" not in txt, "Non-allowlist field must NOT be in server_config dump"
    assert "ui_culture:" in txt, "ui_culture must be in server_config dump"
    assert "server_name:" in txt, "server_name must be in server_config dump"
    assert "plugin_repositories:" in txt, "plugin_repositories must be in server_config dump"
