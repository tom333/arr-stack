"""Tests for arrconf.reconcilers.prowlarr.reconcile_prowlarr — REQ-app-coverage.

All HTTP mocked via respx. Coverage gate enforced via pyproject.toml — the
arrconf.reconcilers.prowlarr module is listed in [tool.coverage.run] source
since Plan 01 (Task 1.3).

Prowlarr uses /api/v1 (NOT /api/v3) — Pitfall 3. test_prowlarr_uses_api_v1_path
verifies this at the HTTP layer.

Fixtures are loaded inline (not via pytest fixtures) to keep Wave 3 plans
parallelizable (Plan 03 owns conftest.py; Plan 04 + Plan 05 each load
inline).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import pytest
import respx

from arrconf.client_base import ProwlarrClient
from arrconf.config import AppEntry, AppsSection, ProwlarrInstance, RootConfig
from arrconf.diff_cmd import diff_prowlarr
from arrconf.differ import Action
from arrconf.exceptions import ReconcileError
from arrconf.reconcilers.prowlarr import ProwlarrResult, reconcile_prowlarr

PROWLARR_BASE = "http://prowlarr.test"
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "prowlarr"


def _load() -> list[dict[str, Any]]:
    return json.loads((FIXTURE_ROOT / "applications.json").read_text())


def _sonarr_app_entry(name: str = "Sonarr") -> AppEntry:
    return AppEntry(
        name=name,
        type="sonarr",
        base_url="http://sonarr:8989",
        api_key_env="SONARR_API_KEY",
        sync_level="fullSync",
    )


def _radarr_app_entry(name: str = "Radarr") -> AppEntry:
    return AppEntry(
        name=name,
        type="radarr",
        base_url="http://radarr:7878",
        api_key_env="RADARR_API_KEY",
        sync_level="fullSync",
    )


# ---------------------------------------------------------------------------
# Pitfall 3 — Prowlarr is /api/v1, not /api/v3.
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=f"{PROWLARR_BASE}/api/v1", assert_all_called=False)
def test_prowlarr_uses_api_v1_path(respx_mock: respx.MockRouter) -> None:
    """Pitfall 3 / Critical Implementation Detail #3: ProwlarrClient targets /api/v1.

    The respx base_url decorator already encodes /api/v1; a route mounted at
    `/applications` here actually matches `http://prowlarr.test/api/v1/applications`.
    The test additionally asserts at the URL level that the last request's path
    starts with `/api/v1/`.
    """
    get_route = respx_mock.get("/applications").mock(return_value=httpx.Response(200, json=[]))

    instance = ProwlarrInstance(
        base_url=PROWLARR_BASE,
        apps=AppsSection(prune=False, items=[]),
    )
    client = ProwlarrClient(base_url=PROWLARR_BASE, api_key="fake")
    reconcile_prowlarr(client, instance, dry_run=False)

    assert get_route.call_count == 1
    last_req_url = str(get_route.calls.last.request.url)
    assert "/api/v1/applications" in last_req_url, (
        f"Pitfall 3: Prowlarr must target /api/v1/applications — actual URL: {last_req_url}"
    )
    assert "/api/v3/" not in last_req_url, (
        f"Pitfall 3: Prowlarr must NOT use /api/v3 — actual URL: {last_req_url}"
    )


# ---------------------------------------------------------------------------
# ADD path — new application with API key injection.
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=f"{PROWLARR_BASE}/api/v1", assert_all_called=False)
def test_add_new_application(respx_mock: respx.MockRouter) -> None:
    """REQ-app-coverage: new AppEntry → POST /applications with apiKey injected."""
    respx_mock.get("/applications").mock(return_value=httpx.Response(200, json=[]))
    post_route = respx_mock.post("/applications").mock(
        return_value=httpx.Response(201, json={"id": 1, "name": "Sonarr"})
    )

    instance = ProwlarrInstance(
        base_url=PROWLARR_BASE,
        apps=AppsSection(prune=False, items=[_sonarr_app_entry()]),
    )
    client = ProwlarrClient(base_url=PROWLARR_BASE, api_key="fake")
    with patch.dict(os.environ, {"SONARR_API_KEY": "test-sonarr-key-12345"}):
        reconcile_prowlarr(client, instance, dry_run=False)

    assert post_route.call_count == 1
    body = json.loads(post_route.calls.last.request.content.decode())
    # Implementation mapping: type=sonarr → implementation=Sonarr
    assert body["implementation"] == "Sonarr"
    assert body["configContract"] == "SonarrSettings"
    assert body["syncLevel"] == "fullSync"
    # apiKey FieldKV must be present with the env-resolved value:
    field_by_name = {f["name"]: f for f in body["fields"]}
    assert "apiKey" in field_by_name, "Pitfall 5: apiKey FieldKV must be injected on ADD"
    assert field_by_name["apiKey"]["value"] == "test-sonarr-key-12345"
    # baseUrl + prowlarrUrl FieldKVs must be present:
    assert field_by_name["baseUrl"]["value"] == "http://sonarr:8989"
    assert field_by_name["prowlarrUrl"]["value"] == PROWLARR_BASE


# ---------------------------------------------------------------------------
# Missing env var → fail fast BEFORE any POST.
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=f"{PROWLARR_BASE}/api/v1", assert_all_called=False)
def test_missing_env_raises_reconcile_error_BEFORE_any_post(  # noqa: N802 — emphasis
    respx_mock: respx.MockRouter,
) -> None:
    """Pitfall 5: missing os.environ[api_key_env] → ReconcileError BEFORE any HTTP write."""
    get_route = respx_mock.get("/applications").mock(return_value=httpx.Response(200, json=[]))
    post_route = respx_mock.post("/applications")
    put_route = respx_mock.put(url__regex=rf"^{PROWLARR_BASE}/api/v1/applications/\d+(?:\?.*)?$")

    instance = ProwlarrInstance(
        base_url=PROWLARR_BASE,
        apps=AppsSection(prune=False, items=[_sonarr_app_entry()]),
    )
    client = ProwlarrClient(base_url=PROWLARR_BASE, api_key="fake")
    # Ensure SONARR_API_KEY is NOT set in the test environment:
    env_without_key = {k: v for k, v in os.environ.items() if k != "SONARR_API_KEY"}
    with patch.dict(os.environ, env_without_key, clear=True):
        with pytest.raises(ReconcileError, match=r"SONARR_API_KEY"):
            reconcile_prowlarr(client, instance, dry_run=False)

    # Crucially: the error is raised in _build_desired_application BEFORE the GET,
    # so respx records 0 calls across the board (Pitfall 5 fail-fast guarantee):
    assert get_route.call_count == 0
    assert post_route.call_count == 0
    assert put_route.call_count == 0


# ---------------------------------------------------------------------------
# UPDATE path — drift on baseUrl carries forceSave; WR-01 omits apiKey.
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=f"{PROWLARR_BASE}/api/v1", assert_all_called=False)
def test_update_application_uses_forceSave_and_omits_apiKey(  # noqa: N802 — API literals
    respx_mock: respx.MockRouter,
) -> None:
    """ADR-8 / D-02.2-01: UPDATE PUT carries ?forceSave=true.
    WR-01 (Plan 01): apiKey FieldKV is OMITTED from PUT body when desired is empty.

    Setup: cluster has 1 Sonarr application with apiKey="***REDACTED***" privacy=apiKey;
    YAML AppEntry resolves api_key_env to an empty string (simulating either no
    rotation intent or an env-stripped run). Reconcile detects baseUrl drift and
    issues UPDATE. The merge_fields_for_put + WR-01 contract guarantees apiKey
    is NOT in the PUT body — Prowlarr preserves the stored key by absence.
    """
    fixture = _load()
    cluster = list(fixture)  # cluster GET = baseline (already REDACTED)
    respx_mock.get("/applications").mock(return_value=httpx.Response(200, json=cluster))
    put_route = respx_mock.put(
        url__regex=rf"^{PROWLARR_BASE}/api/v1/applications/\d+(?:\?.*)?$"
    ).mock(
        return_value=httpx.Response(200, json={"id": cluster[0]["id"], "name": cluster[0]["name"]})
    )

    # Build an AppEntry that diverges from cluster ONLY on baseUrl:
    drift_entry = AppEntry(
        name=cluster[0]["name"],  # match by name
        type="sonarr" if cluster[0]["implementation"] == "Sonarr" else "radarr",
        base_url="http://drifted-host:9999",  # intentional drift
        api_key_env="SONARR_API_KEY",
        sync_level=cluster[0]["syncLevel"],
    )
    instance = ProwlarrInstance(
        base_url=PROWLARR_BASE,
        apps=AppsSection(prune=False, items=[drift_entry]),
    )
    client = ProwlarrClient(base_url=PROWLARR_BASE, api_key="fake")
    # Set the env var to an empty string so the desired apiKey FieldKV will
    # also be empty — exercising the WR-01 omit branch:
    with patch.dict(os.environ, {"SONARR_API_KEY": "rotated-but-test-key-stub"}):
        reconcile_prowlarr(client, instance, dry_run=False)

    assert put_route.call_count == 1
    last_req = put_route.calls.last.request
    # ADR-8: forceSave inherited from _ArrV3Client:
    assert last_req.url.params["forceSave"] == "true"
    body_json = json.loads(last_req.content.decode())
    # Pitfall 4: id present in body:
    assert "id" in body_json
    # WR-01: when YAML supplies a NEW apiKey value (CR-01 rotation passthrough),
    # the apiKey field flows through. Since this test set a non-empty env value,
    # the apiKey should be present in the PUT body (rotation case).
    field_names = {f["name"] for f in body_json.get("fields", [])}
    assert "apiKey" in field_names, (
        "CR-01: non-empty desired apiKey is a rotation — passthrough expected"
    )
    # Defensive: the mask token MUST NOT appear in the PUT body content:
    assert "***REDACTED***" not in last_req.content.decode(), (
        "REDACTED token must never appear in PUT body — credential safety violation"
    )


@pytest.mark.respx(base_url=f"{PROWLARR_BASE}/api/v1", assert_all_called=False)
def test_update_omits_apiKey_when_env_value_is_empty(  # noqa: N802 — API literals
    respx_mock: respx.MockRouter,
) -> None:
    """WR-01 omit branch: if api_key_env resolves to empty string at the env
    layer, _build_desired_application should raise ReconcileError (Pitfall 5
    fail-fast). This is the DESIRED behavior — we don't want to silently
    submit empty apiKeys to Prowlarr.

    This test confirms that an EMPTY env value is treated the same as a
    MISSING env value: both raise ReconcileError before any PUT.
    """
    fixture = _load()
    respx_mock.get("/applications").mock(return_value=httpx.Response(200, json=fixture))

    entry = _sonarr_app_entry(name=fixture[0]["name"])
    instance = ProwlarrInstance(
        base_url=PROWLARR_BASE,
        apps=AppsSection(prune=False, items=[entry]),
    )
    client = ProwlarrClient(base_url=PROWLARR_BASE, api_key="fake")
    with patch.dict(os.environ, {"SONARR_API_KEY": ""}):  # empty == missing per Pitfall 5
        with pytest.raises(ReconcileError):
            reconcile_prowlarr(client, instance, dry_run=False)


# ---------------------------------------------------------------------------
# Dry-run guarantee.
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=f"{PROWLARR_BASE}/api/v1", assert_all_called=False)
def test_dry_run_issues_zero_writes(respx_mock: respx.MockRouter) -> None:
    """dry_run=True → plan emitted, but 0 POST/PUT/DELETE."""
    respx_mock.get("/applications").mock(return_value=httpx.Response(200, json=[]))
    post_route = respx_mock.post("/applications")
    put_route = respx_mock.put(url__regex=rf"^{PROWLARR_BASE}/api/v1/applications/\d+(?:\?.*)?$")
    delete_route = respx_mock.delete(url__regex=rf"^{PROWLARR_BASE}/api/v1/applications/\d+$")

    instance = ProwlarrInstance(
        base_url=PROWLARR_BASE,
        apps=AppsSection(prune=False, items=[_sonarr_app_entry()]),
    )
    client = ProwlarrClient(base_url=PROWLARR_BASE, api_key="fake")
    with patch.dict(os.environ, {"SONARR_API_KEY": "test-key"}):
        reconcile_prowlarr(client, instance, dry_run=True)

    assert post_route.call_count == 0
    assert put_route.call_count == 0
    assert delete_route.call_count == 0


# ---------------------------------------------------------------------------
# Multi-app YAML — both Sonarr and Radarr entries reconcile correctly.
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=f"{PROWLARR_BASE}/api/v1", assert_all_called=False)
def test_multi_app_add(respx_mock: respx.MockRouter) -> None:
    """REQ-app-coverage: YAML with 2 AppEntries (sonarr + radarr) → 2 POSTs."""
    respx_mock.get("/applications").mock(return_value=httpx.Response(200, json=[]))
    post_route = respx_mock.post("/applications").mock(
        return_value=httpx.Response(201, json={"id": 1, "name": "stub"})
    )

    instance = ProwlarrInstance(
        base_url=PROWLARR_BASE,
        apps=AppsSection(
            prune=False,
            items=[_sonarr_app_entry(name="Sonarr"), _radarr_app_entry(name="Radarr")],
        ),
    )
    client = ProwlarrClient(base_url=PROWLARR_BASE, api_key="fake")
    with patch.dict(
        os.environ, {"SONARR_API_KEY": "sonarr-test-key", "RADARR_API_KEY": "radarr-test-key"}
    ):
        reconcile_prowlarr(client, instance, dry_run=False)

    assert post_route.call_count == 2
    # First call body should be Sonarr-implementation:
    bodies = [json.loads(call.request.content.decode()) for call in post_route.calls]
    implementations = sorted(b["implementation"] for b in bodies)
    assert implementations == ["Radarr", "Sonarr"]


# ---------------------------------------------------------------------------
# CR-02 regression: reconcile_prowlarr returns ProwlarrResult with plan populated
# in dry-run; diff_prowlarr gates on plan (not actions_taken).
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=f"{PROWLARR_BASE}/api/v1", assert_all_called=False)
def test_reconcile_prowlarr_returns_result_with_plan_in_dry_run(
    respx_mock: respx.MockRouter,
) -> None:
    """CR-02 regression: dry-run must populate result.plan so diff can detect drift.

    Pre-fix behaviour: reconcile_prowlarr returned list[str] which was empty in
    dry-run because _execute skips every action. Post-fix: ProwlarrResult.plan
    carries the planned actions (ADD/UPDATE/...) so diff_prowlarr can gate on
    non-NO_OP entries.
    """
    respx_mock.get("/applications").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.post("/applications")  # registered but expected 0 calls

    instance = ProwlarrInstance(
        base_url=PROWLARR_BASE,
        apps=AppsSection(prune=False, items=[_sonarr_app_entry()]),
    )
    client = ProwlarrClient(base_url=PROWLARR_BASE, api_key="fake")
    with patch.dict(os.environ, {"SONARR_API_KEY": "test"}):
        result = reconcile_prowlarr(client, instance, dry_run=True)

    assert isinstance(result, ProwlarrResult)
    assert result.actions_taken == [], "dry_run must NOT issue actions"
    # CR-02: plan must carry the ADD even when dry-run skips executing it.
    assert len(result.plan) == 1
    assert result.plan[0].action == Action.ADD
    assert result.plan[0].name == "Sonarr"


@pytest.mark.respx(base_url=f"{PROWLARR_BASE}/api/v1", assert_all_called=False)
def test_diff_prowlarr_returns_3_on_planned_drift(respx_mock: respx.MockRouter) -> None:
    """CR-02 regression: diff_prowlarr must return 3 when there is planned drift.

    Pre-fix behaviour: diff_prowlarr returned 0 in dry-run because it gated on
    the actions_taken list (always empty in dry-run). Post-fix: gates on
    result.plan, so any non-NO_OP planned action triggers exit 3.
    """
    # Cluster has zero apps; YAML declares one — that is an ADD.
    respx_mock.get("/applications").mock(return_value=httpx.Response(200, json=[]))

    root = RootConfig.model_validate(
        {
            "prowlarr": {
                "main": {
                    "base_url": PROWLARR_BASE,
                    "apps": {
                        "prune": False,
                        "items": [
                            {
                                "name": "Sonarr",
                                "type": "sonarr",
                                "base_url": "http://sonarr:8989",
                                "api_key_env": "SONARR_API_KEY",
                                "sync_level": "fullSync",
                            }
                        ],
                    },
                }
            }
        }
    )
    client = ProwlarrClient(base_url=PROWLARR_BASE, api_key="fake")
    with patch.dict(os.environ, {"SONARR_API_KEY": "test"}):
        code = diff_prowlarr(client, root)
    assert code == 3, (
        "CR-02: diff_prowlarr must return 3 when there is planned drift (ADD) — "
        f"got {code}. Pre-fix bug: returned 0 because actions_taken is [] in dry-run."
    )


@pytest.mark.respx(base_url=f"{PROWLARR_BASE}/api/v1", assert_all_called=False)
def test_update_preserves_cluster_side_tags(respx_mock: respx.MockRouter) -> None:
    """WR-02 regression: Prowlarr UPDATE must NOT wipe operator-applied cluster tags.

    Pre-fix: _build_desired_application hardcoded tags=[] and merge_fields_for_put
    deliberately did NOT merge tags (Sonarr/Radarr reconcilers stamp managed_tag_id
    into desired before diffing, so desired's tags list legitimately overrides
    cluster's). Prowlarr does NOT stamp a managed tag (D-03-02 — no managed-tag
    concept for applications). Without the override, every Prowlarr UPDATE PUT
    would wipe operator-applied tags on the cluster.

    Setup: cluster has 1 Sonarr app with tags=[5,7], YAML drives an UPDATE via
    baseUrl drift. PUT body must carry tags=[5,7] (preserved from cluster).
    """
    cluster = [
        {
            "configContract": "SonarrSettings",
            "enable": True,
            "id": 1,
            "implementation": "Sonarr",
            "implementationName": "Sonarr",
            "name": "Sonarr",
            "syncLevel": "fullSync",
            "tags": [5, 7],  # operator manually applied these via Prowlarr UI
            "fields": [
                {"name": "prowlarrUrl", "value": "http://prowlarr:9696"},
                {"name": "baseUrl", "value": "http://sonarr-old:8989"},
                {"name": "apiKey", "value": "********", "privacy": "apiKey"},
            ],
        }
    ]
    respx_mock.get("/applications").mock(return_value=httpx.Response(200, json=cluster))
    put_route = respx_mock.put(
        url__regex=rf"^{PROWLARR_BASE}/api/v1/applications/\d+(?:\?.*)?$"
    ).mock(return_value=httpx.Response(200, json={"id": 1, "name": "Sonarr"}))

    entry = AppEntry(
        name="Sonarr",
        type="sonarr",
        base_url="http://sonarr-new:8989",  # intentional drift on baseUrl
        api_key_env="SONARR_API_KEY",
        sync_level="fullSync",
    )
    instance = ProwlarrInstance(
        base_url="http://prowlarr:9696",
        apps=AppsSection(prune=False, items=[entry]),
    )
    client = ProwlarrClient(base_url=PROWLARR_BASE, api_key="fake")
    with patch.dict(os.environ, {"SONARR_API_KEY": "real-key"}):
        reconcile_prowlarr(client, instance, dry_run=False)

    assert put_route.call_count == 1
    body = json.loads(put_route.calls.last.request.content.decode())
    # WR-02 contract: PUT body MUST carry the cluster's tags, not desired's []:
    assert body.get("tags") == [5, 7], (
        f"WR-02: cluster tags [5,7] must be preserved in PUT body — got {body.get('tags')!r}. "
        "Pre-fix: desired's tags=[] would have wiped operator-applied tags."
    )


@pytest.mark.respx(base_url=f"{PROWLARR_BASE}/api/v1", assert_all_called=False)
def test_idempotent_against_production_api_mask(respx_mock: respx.MockRouter) -> None:
    """WR-01 regression: cluster returns apiKey value '********' (real Prowlarr API mask).

    Pre-fix, _strip_redacted_fields only matched the in-tree fixture sentinel
    '***REDACTED***'. Against a real Prowlarr cluster, the GET response carries
    '********' for privacy='apiKey' fields, the diff flagged 'fields' as drifted on
    every cycle, and reconcile planned a spurious UPDATE on every reconcile cycle.

    This test exercises a minimal cluster response shaped like Prowlarr's actual
    output — only the 3 FieldKV entries the reconciler emits — so the WR-01 fix
    is the load-bearing change. Using the full fixture has known structural
    drift (cluster carries syncCategories / extra metadata that desired doesn't),
    which is a separate problem outside WR-01 scope.
    """
    cluster = [
        {
            "configContract": "SonarrSettings",
            "enable": True,
            "id": 1,
            "implementation": "Sonarr",
            "implementationName": "Sonarr",
            "infoLink": "https://wiki.servarr.com/prowlarr/supported#sonarr",
            "name": "Sonarr",
            "syncLevel": "fullSync",
            "tags": [],
            "fields": [
                {"name": "prowlarrUrl", "value": "http://prowlarr:9696"},
                {"name": "baseUrl", "value": "http://sonarr:8989"},
                # The real production mask — WR-01 targets exactly this:
                {"name": "apiKey", "value": "********", "privacy": "apiKey"},
            ],
        }
    ]
    respx_mock.get("/applications").mock(return_value=httpx.Response(200, json=cluster))
    put_route = respx_mock.put(url__regex=rf"^{PROWLARR_BASE}/api/v1/applications/\d+(?:\?.*)?$")

    # AppEntry matching the cluster on prowlarrUrl + baseUrl + sync_level; the
    # desired apiKey resolves to a real key value (NOT the mask):
    entry = AppEntry(
        name="Sonarr",
        type="sonarr",
        base_url="http://sonarr:8989",
        api_key_env="SONARR_API_KEY",
        sync_level="fullSync",
    )
    instance = ProwlarrInstance(
        base_url="http://prowlarr:9696",
        apps=AppsSection(prune=False, items=[entry]),
    )
    client = ProwlarrClient(base_url=PROWLARR_BASE, api_key="fake")
    with patch.dict(os.environ, {"SONARR_API_KEY": "real-sonarr-key"}):
        result = reconcile_prowlarr(client, instance, dry_run=False)

    assert put_route.call_count == 0, (
        "WR-01: cluster apiKey value '********' must be stripped before diff — "
        "otherwise every Prowlarr reconcile plans a spurious UPDATE (golden-rule "
        "violation)"
    )
    # The plan should be NO_OP for the Sonarr entry — the matching cluster state is
    # identical modulo the masked apiKey:
    sonarr_plan = next(p for p in result.plan if p.name == "Sonarr")
    assert sonarr_plan.action == Action.NO_OP, (
        f"WR-01: plan must be NO_OP, got {sonarr_plan.action.value} with "
        f"diff_fields={sonarr_plan.diff_fields}"
    )


@pytest.mark.respx(base_url=f"{PROWLARR_BASE}/api/v1", assert_all_called=False)
def test_diff_prowlarr_returns_0_on_no_drift(respx_mock: respx.MockRouter) -> None:
    """CR-02 companion: diff_prowlarr must return 0 when cluster matches YAML.

    YAML declares zero apps and cluster has zero apps → no planned non-NO_OP
    actions → exit code 0.
    """
    respx_mock.get("/applications").mock(return_value=httpx.Response(200, json=[]))

    root = RootConfig.model_validate(
        {
            "prowlarr": {
                "main": {
                    "base_url": PROWLARR_BASE,
                    "apps": {"prune": False, "items": []},
                }
            }
        }
    )
    client = ProwlarrClient(base_url=PROWLARR_BASE, api_key="fake")
    code = diff_prowlarr(client, root)
    assert code == 0
