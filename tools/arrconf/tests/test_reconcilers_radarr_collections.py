"""Tests for arrconf.reconcilers.radarr.reconcile_radarr_collections — SAGAS-02.

All HTTP mocked via respx. Coverage gate enforced via pyproject.toml.
Fixtures loaded inline (no conftest.py changes — keeps plans parallelizable).

Test matrix:
  - no_op: all fields match → 0 PUT calls, returns []
  - drift_put: monitored=False drift → 1 PUT, returns "collection:updated:..."
  - absent_skip: collection not in Radarr → log warning, 0 PUT calls, returns []
  - profile_missing: quality profile not found → ConfigError raised
  - idempotence: two consecutive calls on no-op fixture both return []
  - dry_run: drift + dry_run=True → 0 PUT calls, returns "collection:dry_run:..."
  - kind_series_ignored: series saga → no Radarr calls at all
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from arrconf.client_base import RadarrClient
from arrconf.exceptions import ConfigError
from arrconf.intent_config import SagaEntry
from arrconf.reconcilers.radarr import reconcile_radarr_collections

RADARR_BASE = "http://radarr.test"
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "radarr"


def _load(name: str) -> Any:
    return json.loads((FIXTURE_ROOT / name).read_text())


# Fixture: collection matching all desired fields (for no-op / idempotence tests)
FIXTURE_COLLECTION: dict[str, Any] = _load("collection.json")

# Quality profile list matching the saga's profile name
QP_LIST: list[dict[str, Any]] = [{"id": 3, "name": "MULTi.VF"}]

# A standard movie saga that matches FIXTURE_COLLECTION exactly
_SAGA_BOND = SagaEntry(
    name="James Bond",
    kind="movies",
    tmdb_collection=645,
    profile="MULTi.VF",
    root="/media/films",
)


def _client() -> RadarrClient:
    return RadarrClient(base_url=RADARR_BASE, api_key="fake-key")


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_collection_no_op_when_fields_match(respx_mock: respx.MockRouter) -> None:
    """No PUT when cluster already matches desired state (strict idempotence — D-07)."""
    respx_mock.get("/collection").mock(return_value=httpx.Response(200, json=[FIXTURE_COLLECTION]))
    respx_mock.get("/qualityprofile").mock(return_value=httpx.Response(200, json=QP_LIST))
    # No PUT route registered — assert_all_called=False so it's fine if never called

    actions = reconcile_radarr_collections(_client(), [_SAGA_BOND], dry_run=False)

    assert actions == []


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_collection_put_on_drift_monitored(respx_mock: respx.MockRouter) -> None:
    """PUT fires exactly once when monitored field drifts; body includes id (Pitfall 1)."""
    drifted = dict(FIXTURE_COLLECTION)
    drifted["monitored"] = False  # drift

    respx_mock.get("/collection").mock(return_value=httpx.Response(200, json=[drifted]))
    respx_mock.get("/qualityprofile").mock(return_value=httpx.Response(200, json=QP_LIST))
    put_route = respx_mock.put(url__regex=rf"^{RADARR_BASE}/api/v3/collection/\d+(?:\?.*)?$").mock(
        return_value=httpx.Response(202, json={"id": 1})
    )

    actions = reconcile_radarr_collections(_client(), [_SAGA_BOND], dry_run=False)

    assert put_route.call_count == 1
    # Verify that the PUT body contains id (Pitfall 1 re-inject — T-29-04 mitigation)
    put_body = json.loads(put_route.calls[0].request.content)
    assert put_body["id"] == FIXTURE_COLLECTION["id"]
    assert put_body["monitored"] is True  # desired override applied
    assert any("updated" in a for a in actions)
    assert any("James Bond" in a for a in actions)


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_collection_absent_skip_no_put(respx_mock: respx.MockRouter) -> None:
    """Absent collection → log warning + skip; no PUT fired (D-03)."""
    respx_mock.get("/collection").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/qualityprofile").mock(return_value=httpx.Response(200, json=QP_LIST))

    actions = reconcile_radarr_collections(_client(), [_SAGA_BOND], dry_run=False)

    assert actions == []


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_collection_profile_missing_raises_config_error(respx_mock: respx.MockRouter) -> None:
    """ConfigError when saga.profile not found in Radarr qualityprofile list (D-06)."""
    respx_mock.get("/collection").mock(return_value=httpx.Response(200, json=[FIXTURE_COLLECTION]))
    # Quality profile list does NOT contain the saga's profile
    respx_mock.get("/qualityprofile").mock(
        return_value=httpx.Response(200, json=[{"id": 99, "name": "SomeOtherProfile"}])
    )

    saga = SagaEntry(
        name="James Bond",
        kind="movies",
        tmdb_collection=645,
        profile="NonExistentProfile",
        root="/media/films",
    )

    with pytest.raises(ConfigError, match="NonExistentProfile"):
        reconcile_radarr_collections(_client(), [saga], dry_run=False)


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_collection_idempotence_two_runs(respx_mock: respx.MockRouter) -> None:
    """Two consecutive calls on no-drift fixture both return [] (2nd run = 0 actions — D-07)."""
    respx_mock.get("/collection").mock(return_value=httpx.Response(200, json=[FIXTURE_COLLECTION]))
    respx_mock.get("/qualityprofile").mock(return_value=httpx.Response(200, json=QP_LIST))

    first = reconcile_radarr_collections(_client(), [_SAGA_BOND], dry_run=False)
    second = reconcile_radarr_collections(_client(), [_SAGA_BOND], dry_run=False)

    assert first == []
    assert second == []


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_collection_dry_run_no_put(respx_mock: respx.MockRouter) -> None:
    """Drift present + dry_run=True → no PUT fires; action string contains 'dry_run'."""
    drifted = dict(FIXTURE_COLLECTION)
    drifted["monitored"] = False  # drift

    respx_mock.get("/collection").mock(return_value=httpx.Response(200, json=[drifted]))
    respx_mock.get("/qualityprofile").mock(return_value=httpx.Response(200, json=QP_LIST))
    # No PUT route registered — dry_run must NOT fire any PUT

    actions = reconcile_radarr_collections(_client(), [_SAGA_BOND], dry_run=True)

    assert any("dry_run" in a for a in actions)
    assert any("James Bond" in a for a in actions)


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_kind_series_ignored_no_radarr_calls(respx_mock: respx.MockRouter) -> None:
    """kind=series saga produces no Radarr /collection or /qualityprofile calls."""
    collection_route = respx_mock.get("/collection").mock(
        return_value=httpx.Response(200, json=[FIXTURE_COLLECTION])
    )
    qp_route = respx_mock.get("/qualityprofile").mock(
        return_value=httpx.Response(200, json=QP_LIST)
    )

    series_saga = SagaEntry(
        name="Star Wars Saga",
        kind="series",
        items=["The Mandalorian", "Andor"],
    )

    actions = reconcile_radarr_collections(_client(), [series_saga], dry_run=False)

    assert actions == []
    # No GET calls should have been made for series-only saga list
    assert collection_route.call_count == 0
    assert qp_route.call_count == 0


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_collection_multiple_sagas_only_drifted_puts(respx_mock: respx.MockRouter) -> None:
    """Multiple sagas: only the drifted one triggers PUT; no-op saga stays silent."""
    # Second collection: Spider-Man, all fields in sync
    spiderman_fixture: dict[str, Any] = {
        "id": 2,
        "title": "Spider-Man Collection",
        "sortTitle": "spider-man collection",
        "tmdbId": 556,
        "monitored": True,
        "qualityProfileId": 3,
        "rootFolderPath": "/media/films",
        "searchOnAdd": True,
        "minimumAvailability": "released",
        "missingMovies": 0,
        "movies": [],
        "tags": [],
        "images": [],
    }
    # Bond: drift (rootFolderPath mismatch)
    bond_drifted = dict(FIXTURE_COLLECTION)
    bond_drifted["rootFolderPath"] = "/media/old-films"

    respx_mock.get("/collection").mock(
        return_value=httpx.Response(200, json=[bond_drifted, spiderman_fixture])
    )
    respx_mock.get("/qualityprofile").mock(return_value=httpx.Response(200, json=QP_LIST))
    put_route = respx_mock.put(url__regex=rf"^{RADARR_BASE}/api/v3/collection/\d+(?:\?.*)?$").mock(
        return_value=httpx.Response(202, json={"id": 1})
    )

    spiderman_saga = SagaEntry(
        name="Spider-Man",
        kind="movies",
        tmdb_collection=556,
        profile="MULTi.VF",
        root="/media/films",
    )

    actions = reconcile_radarr_collections(_client(), [_SAGA_BOND, spiderman_saga], dry_run=False)

    # Only Bond PUT fires; Spider-Man is no-op
    assert put_route.call_count == 1
    assert any("updated" in a and "James Bond" in a for a in actions)
    assert not any("Spider-Man" in a for a in actions)
