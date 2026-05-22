"""Round-trip integration test — REQ-idempotence + ROADMAP success criteria 3-4.

Property: given that the cluster state EQUALS the YAML desired state,
``apply --dry-run`` performs ZERO HTTP writes (no POST/PUT/DELETE).

Phase 12-B (D-01): download_clients are now generator-derived from
``categories[]`` rather than YAML-declared items. With an empty ``categories``
list and empty ``SonarrDerived(...)`` (the round-trip test scenario), the
reconciler sees the cluster's existing download clients as "not in YAML" and
emits ``PRUNE_SKIP`` (default ``prune=False`` guards against deletion). The
"no writes" property still holds; the "all NO_OP" wording was v0.2.0-era.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from arrconf.client_base import SonarrClient
from arrconf.config import load_config
from arrconf.differ import Action
from arrconf.dump import dump_sonarr
from arrconf.generators.categories import SonarrDerived
from arrconf.reconcilers.sonarr import reconcile_sonarr


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_round_trip_dump_apply_dry_run_is_noop(
    respx_mock,  # noqa: ANN001
    sonarr_downloadclient_fixture: list[dict],
    sonarr_tag_managed_fixture: list[dict],
    tmp_path: Path,
) -> None:
    """D-11 round-trip property.

    1. Dump cluster state → YAML.
    2. Reload YAML → desired list.
    3. ``reconcile_sonarr(dry_run=True)`` against the same cluster state.
    4. Result: ALL NO_OP, ZERO POST/PUT/DELETE.

    Cluster state must include the managed tag stamp (``tags=[1]``) for the
    round-trip to hold: the reconciler stamps the managed tag onto every
    desired item before diffing (D-02). If the cluster fixture had
    ``tags=[]`` but desired has ``tags=[1]`` (post-stamp), ``diff_models``
    would correctly flag UPDATE on ``tags``. Mirrors 01-02-PLAN.md
    ``test_dump_apply_no_op``.
    """
    cluster_payload: list[dict] = [{**dc, "tags": [1]} for dc in sonarr_downloadclient_fixture]
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=sonarr_tag_managed_fixture))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=cluster_payload))
    # Phase 3 extension: reconcile_sonarr also reads these endpoints.
    respx_mock.get("/indexer").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/rootfolder").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/notification").mock(return_value=httpx.Response(200, json=[]))
    # Phase 5 extension: reconcile_sonarr now also reads remotepathmapping and series.
    respx_mock.get("/remotepathmapping").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/series").mock(return_value=httpx.Response(200, json=[]))
    post_route = respx_mock.post("/downloadclient")
    # Use url__regex so the route matches BOTH the bare collection path AND
    # /downloadclient/{id}. The bare-URL `httpx.URL(...).join("")` form only
    # matches the collection path — a regression introducing real PUT-by-id
    # / DELETE-by-id would silently slip past `call_count == 0` because the
    # bare-URL mock would never see those requests. Mirrors 01-02-PLAN.md
    # Task 2 (lines 446-447).
    put_route = respx_mock.put(url__regex=r"^http://sonarr\.test/api/v3/downloadclient(/\d+)?$")
    delete_route = respx_mock.delete(url__regex=r"^http://sonarr\.test/api/v3/downloadclient/\d+$")
    post_tag_route = respx_mock.post("/tag")

    # Step 1: dump cluster → YAML file
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    out = tmp_path / "round-trip.yml"
    dump_sonarr(client, out)

    # Verify modeline is line 1 (D-16)
    first_line = out.read_text().splitlines()[0]
    assert first_line == "# yaml-language-server: $schema=../schemas/arrconf-schema.json"

    # Step 2: reload YAML → desired
    root = load_config(out)
    assert "main" in root.sonarr
    instance = root.sonarr["main"]

    # Step 3: reconcile against same cluster state, dry_run=True
    client2 = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(
        client2,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=True,
    )

    # Step 4: assert no write-class actions (POST/PUT/DELETE). PRUNE_SKIP is
    # tolerated since Phase 12-B (D-01) removed the v0.2.0 items round-trip:
    # cluster download_clients are now "not in YAML" by definition, and
    # prune=False makes that a deliberate skip rather than a delete.
    write_actions = [p for p in result.plan if p.action not in (Action.NO_OP, Action.PRUNE_SKIP)]
    assert write_actions == [], (
        f"Round-trip violated: expected no writes, got: "
        f"{[(p.action.value, p.name, p.diff_fields) for p in write_actions]}"
    )
    assert result.actions_taken == [], (
        f"actions_taken should be empty in dry_run: {result.actions_taken}"
    )
    assert post_route.call_count == 0, "Round-trip violated: POST /downloadclient was called"
    assert put_route.call_count == 0, "Round-trip violated: PUT /downloadclient was called"
    assert delete_route.call_count == 0, "Round-trip violated: DELETE /downloadclient was called"
    assert post_tag_route.call_count == 0, (
        "Round-trip violated: POST /tag was called (managed tag already exists)"
    )


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_round_trip_with_redacted_credentials_is_noop(
    respx_mock,  # noqa: ANN001
    sonarr_downloadclient_fixture: list[dict],
    sonarr_tag_managed_fixture: list[dict],
    tmp_path: Path,
) -> None:
    """D-31/D-35/D-36 contract — dump filter + merge helper together preserve round-trip.

    Cluster has password=***REDACTED***. Dump filter (D-36) omits that entry from YAML.
    Reload → desired's fields[] has no password entry. Reconcile against same cluster
    state → diff sees no change on fields → ALL NO_OP. Without the dump filter or
    without the merge helper, this property fails (canary).
    """
    cluster_payload: list[dict] = [{**dc, "tags": [1]} for dc in sonarr_downloadclient_fixture]
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=sonarr_tag_managed_fixture))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=cluster_payload))
    # Phase 3 extension: reconcile_sonarr also reads these endpoints.
    respx_mock.get("/indexer").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/rootfolder").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/notification").mock(return_value=httpx.Response(200, json=[]))
    # Phase 5 extension: reconcile_sonarr now also reads remotepathmapping and series.
    respx_mock.get("/remotepathmapping").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/series").mock(return_value=httpx.Response(200, json=[]))
    post_route = respx_mock.post("/downloadclient")
    put_route = respx_mock.put(url__regex=r"^http://sonarr\.test/api/v3/downloadclient(/\d+)?$")
    delete_route = respx_mock.delete(url__regex=r"^http://sonarr\.test/api/v3/downloadclient/\d+$")
    post_tag_route = respx_mock.post("/tag")

    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    out = tmp_path / "round-trip-redacted.yml"
    dump_sonarr(client, out)

    # Dump filter MUST have removed the password entry (D-36 emit-side)
    dumped_text = out.read_text()
    assert "***REDACTED***" not in dumped_text, "Dump filter (D-36) failed: REDACTED still in YAML"

    root = load_config(out)
    assert "main" in root.sonarr
    instance = root.sonarr["main"]

    client2 = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(
        client2,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=True,
    )

    # Phase 12-B (D-01): PRUNE_SKIP tolerated — see module docstring.
    write_actions = [p for p in result.plan if p.action not in (Action.NO_OP, Action.PRUNE_SKIP)]
    assert write_actions == [], (
        f"Round-trip with REDACTED credentials violated: "
        f"{[(p.action.value, p.name, p.diff_fields) for p in write_actions]}"
    )
    assert result.actions_taken == []
    assert post_route.call_count == 0
    assert put_route.call_count == 0
    assert delete_route.call_count == 0
    assert post_tag_route.call_count == 0


def test_committed_baseline_yaml_loads() -> None:
    """examples/baseline-sonarr.yml must be a valid arrconf config (D-11 round-trip artifact)."""
    baseline = Path(__file__).parent.parent.parent.parent / "examples/baseline-sonarr.yml"
    if not baseline.exists():
        pytest.skip("baseline-sonarr.yml not yet committed")
    root = load_config(baseline)
    assert "main" in root.sonarr
    # First line is the modeline (D-16, Pitfall 5)
    first = baseline.read_text().splitlines()[0]
    assert first.startswith("# yaml-language-server: $schema="), first
    assert "../schemas/arrconf-schema.json" in first, first
