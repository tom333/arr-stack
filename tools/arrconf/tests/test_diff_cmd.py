"""Tests for arrconf.diff_cmd — jellyfin diff additions (Phase 7).

Tests verify diff_jellyfin behavior:
1. Returns 0 when cluster matches desired (no drift).
2. Returns 3 when drift detected (at least one :dry_run: action).
3. Round-trip with dump_jellyfin returns 0 (SC#4 unit-layer mirror).

The SC#4 dispositive (test 3) is the unit-test layer proof that:
    arrconf dump --apps jellyfin --output X.yml
    arrconf --config X.yml diff --apps jellyfin  # → exit 0

is satisfied. The live-cluster verification is in Plan 07-06 Task 6.2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from arrconf.client_base import JellyfinClient
from arrconf.config import load_config
from arrconf.diff_cmd import diff_jellyfin
from arrconf.dump import dump_jellyfin

JELLYFIN_BASE = "http://jellyfin.test:8096"
ADMIN_USER_ID = "82fd95db72904569b08d83271823ceaa"
TMDB_ID = "b8715ed16c4745289ad3f72deb539cd4"
TMDB_VERSION = "10.11.8.0"


def _make_client() -> JellyfinClient:
    return JellyfinClient(base_url=JELLYFIN_BASE, api_key="test-api-key")


def _mock_cluster_no_drift(respx_mock: respx.MockRouter) -> None:
    """Mock cluster state that perfectly matches the default desired instance.

    Libraries: Séries=[/media/series], Films=[/media/films] — both present in PathInfos.
    Users: moi Policy matches _make_instance() defaults (no drift).
    Server config: all 7 allowlist fields match.
    Plugins: TMDb Active → no-op.
    """
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
            json=[{"Name": "moi", "Id": ADMIN_USER_ID}],
        )
    )
    # Full policy matching what the diff test YAML will expect after round-trip.
    policy: dict[str, Any] = {
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
            json={"Name": "moi", "Id": ADMIN_USER_ID, "Policy": policy},
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
                }
            ],
        )
    )


# ---------------------------------------------------------------------------
# Test 1: returns 0 when desired matches cluster (no drift)
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_diff_jellyfin_zero_drift_when_desired_matches_cluster(
    respx_mock: respx.MockRouter,
    tmp_path: Path,
) -> None:
    """diff_jellyfin returns 0 when all 4 resources match cluster (no-op plan).

    Mocks cluster to exactly match the YAML desired state. All 4 reconcile steps
    produce no :dry_run: actions → reconcile_jellyfin(dry_run=True) actions_taken = [].
    """
    _mock_cluster_no_drift(respx_mock)

    # Build a YAML that matches the cluster exactly via dump + reload.
    out = tmp_path / "jelly.yml"
    dump_jellyfin(_make_client(), out)
    root = load_config(out)

    code = diff_jellyfin(_make_client(), root, [])
    assert code == 0, f"Expected code=0 (no drift) but got {code}"


# ---------------------------------------------------------------------------
# Test 2: returns 3 when drift detected
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_diff_jellyfin_returns_3_on_drift(
    respx_mock: respx.MockRouter,
    tmp_path: Path,
) -> None:
    """diff_jellyfin returns 3 when at least one resource has drift.

    The cluster's ServerName differs from the YAML desired value → server_config
    step emits 'server_config:dry_run' → non_noop list has 1 entry → return 3.
    """
    from arrconf.config import (
        JellyfinInstance,
        JellyfinLibrariesSection,
        JellyfinPluginsSection,
        JellyfinServerConfigSection,
        JellyfinUsersSection,
    )
    from arrconf.resources.jellyfin import JellyfinUserPolicy, PluginRepository

    # Cluster has ServerName="old-name" (drift vs desired "jellyfin").
    respx_mock.get("/Library/VirtualFolders").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "Name": "Séries",
                    "CollectionType": "tvshows",
                    "Locations": ["/media/series"],
                    "LibraryOptions": {"PathInfos": [{"Path": "/media/series"}]},
                }
            ],
        )
    )
    respx_mock.get("/Users").mock(
        return_value=httpx.Response(
            200,
            json=[{"Name": "moi", "Id": ADMIN_USER_ID}],
        )
    )
    # User policy matching desired so users step is a no-op.
    respx_mock.get(f"/Users/{ADMIN_USER_ID}").mock(
        return_value=httpx.Response(
            200,
            json={
                "Name": "moi",
                "Id": ADMIN_USER_ID,
                "Policy": {
                    "IsAdministrator": True,
                    "EnablePublicSharing": True,
                    "AuthenticationProviderId": (
                        "Jellyfin.Server.Implementations.Users.DefaultAuthenticationProvider"
                    ),
                    "PasswordResetProviderId": (
                        "Jellyfin.Server.Implementations.Users.DefaultPasswordResetProvider"
                    ),
                },
            },
        )
    )
    # Cluster ServerName="old-name" → drift!
    respx_mock.get("/System/Configuration").mock(
        return_value=httpx.Response(
            200,
            json={
                "UICulture": "fr",
                "MetadataCountryCode": "FR",
                "PreferredMetadataLanguage": "fr",
                "ActivityLogRetentionDays": 30,
                "LogFileRetentionDays": 3,
                "ServerName": "old-name",  # DRIFT: desired is "jellyfin"
                "PluginRepositories": [
                    {
                        "Name": "Jellyfin Stable",
                        "Url": "https://repo.jellyfin.org/files/plugin/manifest.json",
                        "Enabled": True,
                    }
                ],
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
                }
            ],
        )
    )

    # Build a RootConfig with desired ServerName="jellyfin".
    from arrconf.config import RootConfig

    inst = JellyfinInstance(
        base_url=JELLYFIN_BASE,
        libraries=JellyfinLibrariesSection(enable=True),
        users=JellyfinUsersSection(
            enable=True,
            admin=JellyfinUserPolicy(IsAdministrator=True, EnablePublicSharing=True),
        ),
        server_config=JellyfinServerConfigSection(
            enable=True,
            ui_culture="fr",
            metadata_country_code="FR",
            preferred_metadata_language="fr",
            activity_log_retention_days=30,
            log_file_retention_days=3,
            server_name="jellyfin",  # desired ≠ cluster "old-name"
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
            required=[],
        ),
    )
    root = RootConfig(jellyfin={"main": inst})

    code = diff_jellyfin(_make_client(), root, [])
    assert code == 3, f"Expected code=3 (drift) but got {code}"


# ---------------------------------------------------------------------------
# Test 3: SC#4 round-trip dispositive — dump then diff returns 0
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_diff_jellyfin_round_trip_with_dump(
    respx_mock: respx.MockRouter,
    tmp_path: Path,
) -> None:
    """SC#4 unit-layer mirror: dump_jellyfin → load_config → diff_jellyfin returns 0.

    Property: given cluster state X, dump_jellyfin(X) produces YAML that, when
    loaded and applied (dry_run=True) against the same cluster state X, produces
    zero :dry_run: actions — i.e. diff_jellyfin returns 0.

    This is the unit-layer proof of ROADMAP SC#4:
        arrconf dump --apps jellyfin --output X.yml &&
        arrconf --config X.yml diff --apps jellyfin  # → exit 0
    Live-cluster verification in Plan 07-06 Task 6.2.
    """
    _mock_cluster_no_drift(respx_mock)

    # Step 1: dump cluster state → YAML.
    out = tmp_path / "jelly.yml"
    dump_jellyfin(_make_client(), out)

    # Step 2: reload YAML → RootConfig.
    root = load_config(out)
    assert "main" in root.jellyfin

    # Step 3: diff against the SAME cluster state → must return 0 (no drift).
    code = diff_jellyfin(_make_client(), root, [])
    assert code == 0, (
        f"SC#4 round-trip violated: diff_jellyfin returned {code} instead of 0 — "
        "the dumped YAML, when applied against the same cluster, should produce zero drift"
    )
