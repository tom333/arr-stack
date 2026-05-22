"""Tests for D-12 ScopeViolationError — frontière configarr (ADR-5).

These tests harden T-01-05: scope-guard bypass would let arrconf overwrite
TRaSH-Guides quality profiles. Each frontière module MUST raise
ScopeViolationError BEFORE any httpx call could possibly happen.

Phase-5 extensions (test_series_tags_does_not_touch_quality_endpoints,
test_remote_path_mappings_does_not_touch_quality_endpoints) verify that the new
sub-reconcilers in reconcile_sonarr do NOT call any quality-endpoint paths.
"""

from __future__ import annotations

from types import ModuleType
from typing import Any

import httpx
import pytest
import respx

from arrconf.client_base import SonarrClient
from arrconf.config import (
    RemotePathMappingsSection,
    SeriesTagsSection,
    SonarrInstance,
    TagItem,
    TagsSection,
)
from arrconf.exceptions import ScopeViolationError
from arrconf.generators.categories import SonarrDerived
from arrconf.reconcilers.sonarr import reconcile_sonarr
from arrconf.resources.radarr import (
    custom_format as radarr_custom_format,
)
from arrconf.resources.radarr import (
    media_naming as radarr_media_naming,
)
from arrconf.resources.radarr import (
    quality_definition as radarr_quality_definition,
)
from arrconf.resources.radarr import (
    quality_profile as radarr_quality_profile,
)
from arrconf.resources.sonarr import (
    custom_format,
    media_naming,
    quality_definition,
    quality_profile,
)
from arrconf.resources.sonarr.remote_path_mapping import RemotePathMapping

SONARR_BASE = "http://sonarr.test"
MANAGED_TAG_ID = 1
TV_TAG_ID = 2

QUALITY_PATHS = [
    "/api/v3/qualityprofile",
    "/api/v3/customformat",
    "/api/v3/qualitydefinition",
    "/api/v3/mediamanagement",
]

FRONTIERE_MODULES: list[ModuleType] = [
    # Sonarr frontière (REQ-configarr-coexistence — original):
    quality_profile,
    custom_format,
    quality_definition,
    media_naming,
    # Radarr frontière (REQ-configarr-coexistence — Phase 3 / D-03-01):
    radarr_quality_profile,
    radarr_custom_format,
    radarr_quality_definition,
    radarr_media_naming,
]


@pytest.mark.parametrize("module", FRONTIERE_MODULES, ids=lambda m: m.__name__.split(".")[-1])
def test_scope_violation_raised_with_configarr_message(module: ModuleType) -> None:
    """Each frontière module raises ScopeViolationError mentioning configarr.yml (D-12)."""
    with pytest.raises(ScopeViolationError, match=r"configarr\.yml"):
        module.reconcile(client=None, config=None, dry_run=False)


@pytest.mark.parametrize("module", FRONTIERE_MODULES, ids=lambda m: m.__name__.split(".")[-1])
@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_scope_violation_raises_BEFORE_any_http_call(  # noqa: N802 (T-01-05 emphasis)
    respx_mock: respx.MockRouter,
    module: ModuleType,
) -> None:
    """T-01-05 mitigation: ScopeViolationError must raise pre-network.

    Even if a future bug introduced httpx into the frontière modules,
    this test catches it: respx records ALL calls. If any route is hit,
    the assertion ``respx_mock.calls.call_count == 0`` fails.
    """
    # Intentionally do NOT register any routes — any call would surface as
    # an unhandled-route error before the assertion would even fire.
    with pytest.raises(ScopeViolationError):
        module.reconcile(client=None, config=None, dry_run=False)
    # Hard assertion: zero HTTP calls were recorded.
    assert respx_mock.calls.call_count == 0, (
        f"{module.__name__}: ScopeViolationError raised, but {respx_mock.calls.call_count} "
        f"HTTP calls were attempted. T-01-05 violated."
    )


@pytest.mark.parametrize("module", FRONTIERE_MODULES, ids=lambda m: m.__name__.split(".")[-1])
def test_scope_violation_message_names_resource(module: ModuleType) -> None:
    """Error message must name the specific resource type for actionable error reporting."""
    resource_name = module.__name__.split(".")[-1]
    # Allow either the singular ("media_naming") or the plural form ("quality_profiles").
    plural = resource_name + "s" if not resource_name.endswith("s") else resource_name
    with pytest.raises(ScopeViolationError) as exc:
        module.reconcile(client=None, config=None, dry_run=False)
    msg = str(exc.value)
    assert resource_name in msg or plural in msg, (
        f"Error message must mention '{resource_name}' or '{plural}': {msg}"
    )


# ---------------------------------------------------------------------------
# Phase-5 scope-boundary tests for series_tags and remote_path_mappings (ADR-5)
# ---------------------------------------------------------------------------


def _mock_reconcile_endpoints(
    respx_mock: respx.MockRouter,
    *,
    tags: list[dict[str, Any]],
    series: list[dict[str, Any]],
) -> None:
    """Mock the minimum set of endpoints for a full reconcile_sonarr call."""
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=tags))
    respx_mock.get("/indexer").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/rootfolder").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/notification").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/remotepathmapping").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/series").mock(return_value=httpx.Response(200, json=series))
    # NOTE: quality endpoints (/qualityprofile, /customformat, etc.) are intentionally
    # NOT mocked — if reconcile_sonarr were to call them, respx would raise AllMocked.


@pytest.mark.respx(base_url=f"{SONARR_BASE}/api/v3", assert_all_called=False)
def test_series_tags_does_not_touch_quality_endpoints(
    respx_mock: respx.MockRouter,
    sonarr_series_with_no_tags_fixture: list[dict[str, Any]],
) -> None:
    """ADR-5 frontière: series_tags sub-reconciler MUST NOT call any quality endpoint.

    Uses respx assert_all_called=False but explicitly checks that no quality-related
    paths were called. Any call to /qualityprofile, /customformat, /qualitydefinition,
    or /mediamanagement would be an ADR-5 violation — configarr owns those endpoints.
    """
    tags_fixture = [
        {"id": MANAGED_TAG_ID, "label": "arrconf-managed"},
        {"id": TV_TAG_ID, "label": "tv"},
    ]
    _mock_reconcile_endpoints(
        respx_mock,
        tags=tags_fixture,
        series=sonarr_series_with_no_tags_fixture,
    )
    respx_mock.put("/series/editor").mock(return_value=httpx.Response(202, json={}))

    tv_tag = TagItem(label="tv")
    instance = SonarrInstance(
        base_url=SONARR_BASE,
        series_tags=SeriesTagsSection(enable=True, default_tag="tv"),
    )
    client = SonarrClient(base_url=SONARR_BASE, api_key="fake")
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[tv_tag],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

    # Assert no quality endpoint was called.
    called_paths = [str(c.request.url.path) for c in respx_mock.calls]
    for quality_path in QUALITY_PATHS:
        # Strip the /api/v3 prefix since respx base_url handles it.
        short_path = quality_path.replace("/api/v3", "")
        assert not any(short_path in p for p in called_paths), (
            f"ADR-5 violated: series_tags sub-reconciler called {quality_path}. "
            f"Called paths: {called_paths}"
        )


@pytest.mark.respx(base_url=f"{SONARR_BASE}/api/v3", assert_all_called=False)
def test_remote_path_mappings_does_not_touch_quality_endpoints(
    respx_mock: respx.MockRouter,
) -> None:
    """ADR-5 frontière: remote_path_mappings sub-reconciler MUST NOT call quality endpoints.

    Same shape as the series_tags test — verifies the new Phase-5 sub-reconciler
    respects the configarr ownership boundary for quality management endpoints.
    """
    tags_fixture = [{"id": MANAGED_TAG_ID, "label": "arrconf-managed"}]
    _mock_reconcile_endpoints(
        respx_mock,
        tags=tags_fixture,
        series=[],  # no series → no series_tags work
    )
    respx_mock.post("/remotepathmapping").mock(return_value=httpx.Response(201, json={"id": 10}))

    desired_rpm = RemotePathMapping(
        host="qbittorrent.selfhost.svc.cluster.local",
        remotePath="/data/anime/",
        localPath="/data/torrents/anime/",
    )
    instance = SonarrInstance(
        base_url=SONARR_BASE,
        series_tags=SeriesTagsSection(enable=False),  # disable to keep focus on RPM
    )
    client = SonarrClient(base_url=SONARR_BASE, api_key="fake")
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[desired_rpm],
        ),
        dry_run=False,
    )

    called_paths = [str(c.request.url.path) for c in respx_mock.calls]
    for quality_path in QUALITY_PATHS:
        short_path = quality_path.replace("/api/v3", "")
        assert not any(short_path in p for p in called_paths), (
            f"ADR-5 violated: remote_path_mappings sub-reconciler called {quality_path}. "
            f"Called paths: {called_paths}"
        )
