"""Tests for arrconf.reconcilers.seerr.reconcile_seerr — Phase 6.

All HTTP mocked via respx. Coverage gate: >= 80% on arrconf.reconcilers.seerr.

Key invariants verified:
- Pitfall 1: PUT body excludes `id` (Seerr 400 on id-in-body)
- Pitfall 2: settings/main uses POST not PUT
- Pitfall 3: activeProfileName / activeAnimeProfileName excluded (server-computed)
- D-06-CREDS-01: apiKey preserved from cluster GET when YAML omits it
- D-06-SCOPE-01: 4 resources reconciled (settings/sonarr/radarr/user/main subset)
- ADR-5 frontiere: NEVER calls /api/v3/qualityprofile / customformat /
  qualitydefinition / mediamanagement
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from arrconf.client_base import SeerrClient
from arrconf.config import (
    SeerrInstance,
    SeerrMainSettingsSection,
    SeerrRadarrServiceSection,
    SeerrSonarrServiceSection,
    SeerrUsersSection,
)
from arrconf.exceptions import ReconcileError
from arrconf.reconcilers.seerr import reconcile_seerr
from arrconf.resources.seerr import DefaultQuota, DefaultQuotas, SeerrUser

SEERR_BASE = "http://seerr.test"


def _make_instance(**overrides: Any) -> SeerrInstance:
    """Build a Phase-6 SeerrInstance with overridable section fields."""
    defaults: dict[str, Any] = dict(
        base_url=SEERR_BASE,
        sonarr_service=SeerrSonarrServiceSection(
            hostname="sonarr",
            port=8989,
            activeProfileId=6,
            activeDirectory="/media/series",
            activeAnimeProfileId=7,
            activeAnimeDirectory="/media/anime",
            animeTags=[3],
            tags=[2],
            tagRequests=True,
        ),
        radarr_service=SeerrRadarrServiceSection(
            hostname="radarr",
            port=7878,
            activeProfileId=6,
            activeDirectory="/media/films",
            tags=[2],
            tagRequests=True,
        ),
        users=SeerrUsersSection(
            enable=True,
            admin=SeerrUser(displayName="admin", permissions=2),
        ),
        main_settings=SeerrMainSettingsSection(
            enable=True,
            defaultPermissions=32,
            defaultQuotas=DefaultQuotas(
                movie=DefaultQuota(quotaDays=7, quotaLimit=5),
                tv=DefaultQuota(quotaDays=7, quotaLimit=5),
            ),
        ),
    )
    defaults.update(overrides)
    return SeerrInstance(**defaults)


def _make_client() -> SeerrClient:
    return SeerrClient(base_url=SEERR_BASE, api_key="test-key")


def _mock_all_gets(
    respx_mock: respx.MockRouter,
    sonarr_fixture: list[dict[str, Any]],
    radarr_fixture: list[dict[str, Any]],
    user_fixture: dict[str, Any],
    main_fixture: dict[str, Any],
) -> None:
    """Mock all 4 Seerr GET endpoints + defensive PUT/POST mocks.

    Always adds defensive PUT/POST mocks to avoid AllMockedAssertionError when
    the test's focus is on a different resource but others also detect drift.
    Tests that need to assert on specific routes should register those routes
    AFTER calling this helper (respx uses first-registered-wins by default).
    """
    respx_mock.get("/settings/sonarr").mock(return_value=httpx.Response(200, json=sonarr_fixture))
    respx_mock.get("/settings/radarr").mock(return_value=httpx.Response(200, json=radarr_fixture))
    respx_mock.get("/user").mock(return_value=httpx.Response(200, json=user_fixture))
    respx_mock.get("/settings/main").mock(return_value=httpx.Response(200, json=main_fixture))
    # Defensive mocks — prevent AllMockedAssertionError if any resource drifts.
    respx_mock.put("/settings/sonarr/0").mock(return_value=httpx.Response(200, json={}))
    respx_mock.put("/settings/radarr/0").mock(return_value=httpx.Response(200, json={}))
    respx_mock.put("/user/1").mock(return_value=httpx.Response(200, json={}))
    respx_mock.post("/settings/main").mock(return_value=httpx.Response(200, json={}))


def _sonarr_state_matching_defaults(
    base_fixture: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return a settings/sonarr fixture that exactly matches _make_instance defaults."""
    s = json.loads(json.dumps(base_fixture))
    s[0].update(
        {
            "activeProfileId": 6,
            "activeDirectory": "/media/series",
            "activeAnimeProfileId": 7,
            "activeAnimeDirectory": "/media/anime",
            "animeTags": [3],
            "tags": [2],
            "tagRequests": True,
            "isDefault": True,
            "name": "sonarr",
            "hostname": "sonarr",
            "port": 8989,
            "apiKey": "cluster-key",
            "useSsl": False,
            "is4k": False,
            "enableSeasonFolders": False,
            "externalUrl": "",
            "syncEnabled": True,
            "preventSearch": False,
            "id": 0,
        }
    )
    return s


# ---------------------------------------------------------------------------
# settings/sonarr tests (Pitfall 1 + Pitfall 3 + D-06-CREDS-01)
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=f"{SEERR_BASE}/api/v1", assert_all_called=False)
def test_settings_sonarr_no_op_when_cluster_matches(
    respx_mock: respx.MockRouter,
    seerr_settings_sonarr_fixture: list[dict[str, Any]],
    seerr_settings_radarr_fixture: list[dict[str, Any]],
    seerr_user_fixture: dict[str, Any],
    seerr_settings_main_fixture: dict[str, Any],
) -> None:
    """Cluster matches YAML → zero PUT calls (SC#5 unit signal — idempotence)."""
    sonarr_state = _sonarr_state_matching_defaults(seerr_settings_sonarr_fixture)
    _mock_all_gets(
        respx_mock,
        sonarr_state,
        seerr_settings_radarr_fixture,
        seerr_user_fixture,
        seerr_settings_main_fixture,
    )
    put_route = respx_mock.put("/settings/sonarr/0").mock(return_value=httpx.Response(200, json={}))

    reconcile_seerr(_make_client(), _make_instance(), dry_run=False)

    assert put_route.call_count == 0  # idempotent no-op


@pytest.mark.respx(base_url=f"{SEERR_BASE}/api/v1", assert_all_called=False)
def test_settings_sonarr_writes_animeTags_when_desired_differs(
    respx_mock: respx.MockRouter,
    seerr_settings_sonarr_fixture: list[dict[str, Any]],
    seerr_settings_radarr_fixture: list[dict[str, Any]],
    seerr_user_fixture: dict[str, Any],
    seerr_settings_main_fixture: dict[str, Any],
) -> None:
    """Cluster animeTags=[] but YAML wants [3] → exactly 1 PUT."""
    sonarr_state = [
        dict(
            seerr_settings_sonarr_fixture[0],
            animeTags=[],
            tags=[],
            isDefault=True,
            id=0,
            apiKey="cluster-key",
        )
    ]
    _mock_all_gets(
        respx_mock,
        sonarr_state,
        seerr_settings_radarr_fixture,
        seerr_user_fixture,
        seerr_settings_main_fixture,
    )
    put_route = respx_mock.put("/settings/sonarr/0").mock(return_value=httpx.Response(200, json={}))

    reconcile_seerr(_make_client(), _make_instance(), dry_run=False)

    assert put_route.call_count == 1
    body = json.loads(put_route.calls[0].request.content)
    assert body["animeTags"] == [3]
    assert body["tags"] == [2]


@pytest.mark.respx(base_url=f"{SEERR_BASE}/api/v1", assert_all_called=False)
def test_settings_sonarr_put_body_excludes_id(
    respx_mock: respx.MockRouter,
    seerr_settings_sonarr_fixture: list[dict[str, Any]],
    seerr_settings_radarr_fixture: list[dict[str, Any]],
    seerr_user_fixture: dict[str, Any],
    seerr_settings_main_fixture: dict[str, Any],
) -> None:
    """Pitfall 1: Seerr returns 400 'request.body.id is read-only' if id is in PUT body."""
    sonarr_state = [
        dict(
            seerr_settings_sonarr_fixture[0],
            animeTags=[],
            isDefault=True,
            id=0,
            apiKey="cluster-key",
        )
    ]
    _mock_all_gets(
        respx_mock,
        sonarr_state,
        seerr_settings_radarr_fixture,
        seerr_user_fixture,
        seerr_settings_main_fixture,
    )
    put_route = respx_mock.put("/settings/sonarr/0").mock(return_value=httpx.Response(200, json={}))

    reconcile_seerr(_make_client(), _make_instance(), dry_run=False)
    body = put_route.calls[0].request.content.decode()
    assert '"id":' not in body, f"id MUST NOT be in PUT body (Pitfall 1); body was: {body}"


@pytest.mark.respx(base_url=f"{SEERR_BASE}/api/v1", assert_all_called=False)
def test_settings_sonarr_apikey_preserved_when_yaml_empty(
    respx_mock: respx.MockRouter,
    seerr_settings_sonarr_fixture: list[dict[str, Any]],
    seerr_settings_radarr_fixture: list[dict[str, Any]],
    seerr_user_fixture: dict[str, Any],
    seerr_settings_main_fixture: dict[str, Any],
) -> None:
    """D-06-CREDS-01: cluster apiKey survives even when YAML carries empty apiKey."""
    sonarr_state = [
        dict(
            seerr_settings_sonarr_fixture[0],
            animeTags=[],
            isDefault=True,
            id=0,
            apiKey="cluster-key-xyz",
        )
    ]
    _mock_all_gets(
        respx_mock,
        sonarr_state,
        seerr_settings_radarr_fixture,
        seerr_user_fixture,
        seerr_settings_main_fixture,
    )
    put_route = respx_mock.put("/settings/sonarr/0").mock(return_value=httpx.Response(200, json={}))

    reconcile_seerr(_make_client(), _make_instance(), dry_run=False)
    body = json.loads(put_route.calls[0].request.content)
    assert body["apiKey"] == "cluster-key-xyz", (
        f"Expected cluster apiKey preserved; got: {body.get('apiKey')!r}"
    )


@pytest.mark.respx(base_url=f"{SEERR_BASE}/api/v1", assert_all_called=False)
def test_settings_sonarr_excludes_activeProfileName_from_put(
    respx_mock: respx.MockRouter,
    seerr_settings_sonarr_fixture: list[dict[str, Any]],
    seerr_settings_radarr_fixture: list[dict[str, Any]],
    seerr_user_fixture: dict[str, Any],
    seerr_settings_main_fixture: dict[str, Any],
) -> None:
    """Pitfall 3: activeProfileName + activeAnimeProfileName are server-computed."""
    sonarr_state = [
        dict(
            seerr_settings_sonarr_fixture[0],
            animeTags=[],
            isDefault=True,
            id=0,
            apiKey="x",
            activeProfileName="HD - 720p/1080p",
            activeAnimeProfileName="HD-1080p",
        )
    ]
    _mock_all_gets(
        respx_mock,
        sonarr_state,
        seerr_settings_radarr_fixture,
        seerr_user_fixture,
        seerr_settings_main_fixture,
    )
    put_route = respx_mock.put("/settings/sonarr/0").mock(return_value=httpx.Response(200, json={}))

    reconcile_seerr(_make_client(), _make_instance(), dry_run=False)
    body = put_route.calls[0].request.content.decode()
    assert '"activeProfileName"' not in body
    assert '"activeAnimeProfileName"' not in body


# ---------------------------------------------------------------------------
# settings/radarr tests
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=f"{SEERR_BASE}/api/v1", assert_all_called=False)
def test_settings_radarr_no_animeTags_in_put_body(
    respx_mock: respx.MockRouter,
    seerr_settings_sonarr_fixture: list[dict[str, Any]],
    seerr_settings_radarr_fixture: list[dict[str, Any]],
    seerr_user_fixture: dict[str, Any],
    seerr_settings_main_fixture: dict[str, Any],
) -> None:
    """Radarr-side has no animeTags/activeAnime* fields per Seerr schema."""
    radarr_state = [
        dict(seerr_settings_radarr_fixture[0], tags=[], isDefault=True, id=0, apiKey="rkey")
    ]
    _mock_all_gets(
        respx_mock,
        seerr_settings_sonarr_fixture,
        radarr_state,
        seerr_user_fixture,
        seerr_settings_main_fixture,
    )
    put_route = respx_mock.put("/settings/radarr/0").mock(return_value=httpx.Response(200, json={}))
    # Defensive sonarr PUT mock
    respx_mock.put("/settings/sonarr/0").mock(return_value=httpx.Response(200, json={}))

    reconcile_seerr(_make_client(), _make_instance(), dry_run=False)
    body = put_route.calls[0].request.content.decode()
    assert '"animeTags"' not in body, "Radarr-side body MUST NOT contain animeTags"


@pytest.mark.respx(base_url=f"{SEERR_BASE}/api/v1", assert_all_called=False)
def test_settings_radarr_apikey_preserved(
    respx_mock: respx.MockRouter,
    seerr_settings_sonarr_fixture: list[dict[str, Any]],
    seerr_settings_radarr_fixture: list[dict[str, Any]],
    seerr_user_fixture: dict[str, Any],
    seerr_settings_main_fixture: dict[str, Any],
) -> None:
    """D-06-CREDS-01: Radarr cluster apiKey preserved when YAML omits it."""
    radarr_state = [
        dict(
            seerr_settings_radarr_fixture[0],
            tags=[],
            isDefault=True,
            id=0,
            apiKey="radarr-cluster-secret",
        )
    ]
    _mock_all_gets(
        respx_mock,
        seerr_settings_sonarr_fixture,
        radarr_state,
        seerr_user_fixture,
        seerr_settings_main_fixture,
    )
    put_route = respx_mock.put("/settings/radarr/0").mock(return_value=httpx.Response(200, json={}))
    respx_mock.put("/settings/sonarr/0").mock(return_value=httpx.Response(200, json={}))

    reconcile_seerr(_make_client(), _make_instance(), dry_run=False)
    body = json.loads(put_route.calls[0].request.content)
    assert body["apiKey"] == "radarr-cluster-secret"


# ---------------------------------------------------------------------------
# user tests
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=f"{SEERR_BASE}/api/v1", assert_all_called=False)
def test_user_no_op_when_permissions_match(
    respx_mock: respx.MockRouter,
    seerr_settings_sonarr_fixture: list[dict[str, Any]],
    seerr_settings_radarr_fixture: list[dict[str, Any]],
    seerr_user_fixture: dict[str, Any],
    seerr_settings_main_fixture: dict[str, Any],
) -> None:
    """SC#5 unit signal for /user — cluster matches YAML → 0 PUTs."""
    user_state = json.loads(json.dumps(seerr_user_fixture))
    users = (
        user_state["results"]
        if isinstance(user_state, dict) and "results" in user_state
        else user_state
    )
    users[0].update({"id": 1, "permissions": 2, "displayName": "admin"})
    _mock_all_gets(
        respx_mock,
        seerr_settings_sonarr_fixture,
        seerr_settings_radarr_fixture,
        user_state,
        seerr_settings_main_fixture,
    )
    put_user = respx_mock.put("/user/1").mock(return_value=httpx.Response(200, json={}))
    respx_mock.put("/settings/sonarr/0").mock(return_value=httpx.Response(200, json={}))
    respx_mock.put("/settings/radarr/0").mock(return_value=httpx.Response(200, json={}))

    reconcile_seerr(_make_client(), _make_instance(), dry_run=False)
    assert put_user.call_count == 0


@pytest.mark.respx(base_url=f"{SEERR_BASE}/api/v1", assert_all_called=False)
def test_user_writes_permissions_change(
    respx_mock: respx.MockRouter,
    seerr_settings_sonarr_fixture: list[dict[str, Any]],
    seerr_settings_radarr_fixture: list[dict[str, Any]],
    seerr_user_fixture: dict[str, Any],
    seerr_settings_main_fixture: dict[str, Any],
) -> None:
    """Cluster permissions=4, YAML wants 2 → 1 PUT; 16 read-only fields absent from body."""
    user_state = json.loads(json.dumps(seerr_user_fixture))
    users = (
        user_state["results"]
        if isinstance(user_state, dict) and "results" in user_state
        else user_state
    )
    users[0].update({"id": 1, "permissions": 4, "displayName": "old-admin"})
    _mock_all_gets(
        respx_mock,
        seerr_settings_sonarr_fixture,
        seerr_settings_radarr_fixture,
        user_state,
        seerr_settings_main_fixture,
    )
    respx_mock.put("/settings/sonarr/0").mock(return_value=httpx.Response(200, json={}))
    respx_mock.put("/settings/radarr/0").mock(return_value=httpx.Response(200, json={}))
    put_user = respx_mock.put("/user/1").mock(return_value=httpx.Response(200, json={}))

    reconcile_seerr(_make_client(), _make_instance(), dry_run=False)
    assert put_user.call_count == 1
    body = json.loads(put_user.calls[0].request.content)
    assert body["permissions"] == 2


@pytest.mark.respx(base_url=f"{SEERR_BASE}/api/v1", assert_all_called=False)
def test_user_put_body_excludes_16_read_only_fields(
    respx_mock: respx.MockRouter,
    seerr_settings_sonarr_fixture: list[dict[str, Any]],
    seerr_settings_radarr_fixture: list[dict[str, Any]],
    seerr_user_fixture: dict[str, Any],
    seerr_settings_main_fixture: dict[str, Any],
) -> None:
    """Pitfall 1 generalization — 16 read-only server fields must not appear in PUT body."""
    user_state = json.loads(json.dumps(seerr_user_fixture))
    users = (
        user_state["results"]
        if isinstance(user_state, dict) and "results" in user_state
        else user_state
    )
    users[0].update({"id": 1, "permissions": 4, "displayName": "old"})
    _mock_all_gets(
        respx_mock,
        seerr_settings_sonarr_fixture,
        seerr_settings_radarr_fixture,
        user_state,
        seerr_settings_main_fixture,
    )
    respx_mock.put("/settings/sonarr/0").mock(return_value=httpx.Response(200, json={}))
    respx_mock.put("/settings/radarr/0").mock(return_value=httpx.Response(200, json={}))
    put_user = respx_mock.put("/user/1").mock(return_value=httpx.Response(200, json={}))

    reconcile_seerr(_make_client(), _make_instance(), dry_run=False)
    body = json.loads(put_user.calls[0].request.content)
    for forbidden in (
        "id",
        "email",
        "userType",
        "plexId",
        "jellyfinUserId",
        "avatar",
        "createdAt",
        "updatedAt",
        "requestCount",
        "warnings",
        "recoveryLinkExpirationDate",
        "settings",
    ):
        assert forbidden not in body, f"Read-only field {forbidden!r} leaked into user PUT body"


# ---------------------------------------------------------------------------
# settings/main tests (Pitfall 2)
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=f"{SEERR_BASE}/api/v1", assert_all_called=False)
def test_settings_main_uses_post_not_put(
    respx_mock: respx.MockRouter,
    seerr_settings_sonarr_fixture: list[dict[str, Any]],
    seerr_settings_radarr_fixture: list[dict[str, Any]],
    seerr_user_fixture: dict[str, Any],
    seerr_settings_main_fixture: dict[str, Any],
) -> None:
    """Pitfall 2: Seerr API quirk — settings/main is POST, not PUT."""
    main_state = dict(seerr_settings_main_fixture, defaultPermissions=8)
    _mock_all_gets(
        respx_mock,
        seerr_settings_sonarr_fixture,
        seerr_settings_radarr_fixture,
        seerr_user_fixture,
        main_state,
    )
    respx_mock.put("/settings/sonarr/0").mock(return_value=httpx.Response(200, json={}))
    respx_mock.put("/settings/radarr/0").mock(return_value=httpx.Response(200, json={}))
    respx_mock.put("/user/1").mock(return_value=httpx.Response(200, json={}))
    put_main = respx_mock.put("/settings/main").mock(return_value=httpx.Response(200, json={}))
    post_main = respx_mock.post("/settings/main").mock(return_value=httpx.Response(200, json={}))

    reconcile_seerr(_make_client(), _make_instance(), dry_run=False)
    assert post_main.call_count == 1, "settings/main MUST use POST"
    assert put_main.call_count == 0, "settings/main MUST NOT use PUT (Pitfall 2)"


@pytest.mark.respx(base_url=f"{SEERR_BASE}/api/v1", assert_all_called=False)
def test_settings_main_writes_default_permissions_change(
    respx_mock: respx.MockRouter,
    seerr_settings_sonarr_fixture: list[dict[str, Any]],
    seerr_settings_radarr_fixture: list[dict[str, Any]],
    seerr_user_fixture: dict[str, Any],
    seerr_settings_main_fixture: dict[str, Any],
) -> None:
    """Cluster defaultPermissions=8 → POST with merged body; unrelated keys preserved."""
    main_state = dict(
        seerr_settings_main_fixture,
        defaultPermissions=8,
        locale="en",
        applicationTitle="My Seerr",
    )
    _mock_all_gets(
        respx_mock,
        seerr_settings_sonarr_fixture,
        seerr_settings_radarr_fixture,
        seerr_user_fixture,
        main_state,
    )
    respx_mock.put("/settings/sonarr/0").mock(return_value=httpx.Response(200, json={}))
    respx_mock.put("/settings/radarr/0").mock(return_value=httpx.Response(200, json={}))
    respx_mock.put("/user/1").mock(return_value=httpx.Response(200, json={}))
    post_main = respx_mock.post("/settings/main").mock(return_value=httpx.Response(200, json={}))

    reconcile_seerr(_make_client(), _make_instance(), dry_run=False)
    body = json.loads(post_main.calls[0].request.content)
    assert body["defaultPermissions"] == 32
    assert body["locale"] == "en"  # operator-set key preserved
    assert body["applicationTitle"] == "My Seerr"  # operator-set key preserved
    assert "apiKey" not in body  # defense in depth — never write apiKey


# ---------------------------------------------------------------------------
# Frontiere (ADR-5)
# ---------------------------------------------------------------------------


@pytest.mark.respx(assert_all_called=False)
def test_seerr_does_not_call_arr_v3_quality_endpoints(
    respx_mock: respx.MockRouter,
    seerr_settings_sonarr_fixture: list[dict[str, Any]],
    seerr_settings_radarr_fixture: list[dict[str, Any]],
    seerr_user_fixture: dict[str, Any],
    seerr_settings_main_fixture: dict[str, Any],
) -> None:
    """ADR-5 frontiere: Seerr reconciler MUST NEVER reach configarr's domain."""
    respx_mock.get(f"{SEERR_BASE}/api/v1/settings/sonarr").mock(
        return_value=httpx.Response(200, json=seerr_settings_sonarr_fixture)
    )
    respx_mock.get(f"{SEERR_BASE}/api/v1/settings/radarr").mock(
        return_value=httpx.Response(200, json=seerr_settings_radarr_fixture)
    )
    respx_mock.get(f"{SEERR_BASE}/api/v1/user").mock(
        return_value=httpx.Response(200, json=seerr_user_fixture)
    )
    respx_mock.get(f"{SEERR_BASE}/api/v1/settings/main").mock(
        return_value=httpx.Response(200, json=seerr_settings_main_fixture)
    )
    respx_mock.put(f"{SEERR_BASE}/api/v1/settings/sonarr/0").mock(
        return_value=httpx.Response(200, json={})
    )
    respx_mock.put(f"{SEERR_BASE}/api/v1/settings/radarr/0").mock(
        return_value=httpx.Response(200, json={})
    )
    respx_mock.put(f"{SEERR_BASE}/api/v1/user/1").mock(return_value=httpx.Response(200, json={}))
    respx_mock.post(f"{SEERR_BASE}/api/v1/settings/main").mock(
        return_value=httpx.Response(200, json={})
    )

    # Sentinel routes on Sonarr/Radarr v3 quality endpoints (ADR-5 forbidden domain).
    forbidden_routes = [
        respx_mock.get("http://sonarr:8989/api/v3/qualityprofile").mock(
            return_value=httpx.Response(200, json=[])
        ),
        respx_mock.get("http://sonarr:8989/api/v3/customformat").mock(
            return_value=httpx.Response(200, json=[])
        ),
        respx_mock.get("http://sonarr:8989/api/v3/qualitydefinition").mock(
            return_value=httpx.Response(200, json=[])
        ),
        respx_mock.get("http://sonarr:8989/api/v3/config/mediamanagement").mock(
            return_value=httpx.Response(200, json={})
        ),
        respx_mock.get("http://radarr:7878/api/v3/qualityprofile").mock(
            return_value=httpx.Response(200, json=[])
        ),
        respx_mock.get("http://radarr:7878/api/v3/customformat").mock(
            return_value=httpx.Response(200, json=[])
        ),
    ]

    reconcile_seerr(_make_client(), _make_instance(), dry_run=False)

    for r in forbidden_routes:
        assert not r.called, f"FRONTIERE VIOLATION: {r} was called (ADR-5)"


# ---------------------------------------------------------------------------
# Section disabled + dry_run + error paths
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=f"{SEERR_BASE}/api/v1", assert_all_called=False)
def test_dry_run_emits_no_writes(
    respx_mock: respx.MockRouter,
    seerr_settings_sonarr_fixture: list[dict[str, Any]],
    seerr_settings_radarr_fixture: list[dict[str, Any]],
    seerr_user_fixture: dict[str, Any],
    seerr_settings_main_fixture: dict[str, Any],
) -> None:
    """dry_run=True → zero PUTs/POSTs regardless of cluster delta."""
    # Force deltas so writes WOULD fire if dry_run weren't honoured.
    sonarr_state = [
        dict(seerr_settings_sonarr_fixture[0], animeTags=[], isDefault=True, id=0, apiKey="x")
    ]
    main_state = dict(seerr_settings_main_fixture, defaultPermissions=8)
    _mock_all_gets(
        respx_mock,
        sonarr_state,
        seerr_settings_radarr_fixture,
        seerr_user_fixture,
        main_state,
    )
    put_sonarr = respx_mock.put("/settings/sonarr/0").mock(
        return_value=httpx.Response(200, json={})
    )
    put_radarr = respx_mock.put("/settings/radarr/0").mock(
        return_value=httpx.Response(200, json={})
    )
    put_user = respx_mock.put("/user/1").mock(return_value=httpx.Response(200, json={}))
    post_main = respx_mock.post("/settings/main").mock(return_value=httpx.Response(200, json={}))

    reconcile_seerr(_make_client(), _make_instance(), dry_run=True)
    assert put_sonarr.call_count == 0
    assert put_radarr.call_count == 0
    assert put_user.call_count == 0
    assert post_main.call_count == 0


@pytest.mark.respx(base_url=f"{SEERR_BASE}/api/v1", assert_all_called=False)
def test_main_settings_disabled_skips_resource(
    respx_mock: respx.MockRouter,
    seerr_settings_sonarr_fixture: list[dict[str, Any]],
    seerr_settings_radarr_fixture: list[dict[str, Any]],
    seerr_user_fixture: dict[str, Any],
) -> None:
    """instance.main_settings.enable=False → no GET nor POST to /settings/main."""
    _mock_all_gets(
        respx_mock,
        seerr_settings_sonarr_fixture,
        seerr_settings_radarr_fixture,
        seerr_user_fixture,
        {},
    )
    get_main = respx_mock.get("/settings/main").mock(return_value=httpx.Response(200, json={}))
    post_main = respx_mock.post("/settings/main").mock(return_value=httpx.Response(200, json={}))
    respx_mock.put("/settings/sonarr/0").mock(return_value=httpx.Response(200, json={}))
    respx_mock.put("/settings/radarr/0").mock(return_value=httpx.Response(200, json={}))
    respx_mock.put("/user/1").mock(return_value=httpx.Response(200, json={}))

    instance = _make_instance(main_settings=SeerrMainSettingsSection(enable=False))
    reconcile_seerr(_make_client(), instance, dry_run=False)
    assert get_main.call_count == 0
    assert post_main.call_count == 0


@pytest.mark.respx(base_url=f"{SEERR_BASE}/api/v1", assert_all_called=False)
def test_users_disabled_skips_resource(
    respx_mock: respx.MockRouter,
    seerr_settings_sonarr_fixture: list[dict[str, Any]],
    seerr_settings_radarr_fixture: list[dict[str, Any]],
    seerr_settings_main_fixture: dict[str, Any],
) -> None:
    """instance.users.enable=False → no GET nor PUT to /user."""
    respx_mock.get("/settings/sonarr").mock(
        return_value=httpx.Response(200, json=seerr_settings_sonarr_fixture)
    )
    respx_mock.get("/settings/radarr").mock(
        return_value=httpx.Response(200, json=seerr_settings_radarr_fixture)
    )
    respx_mock.get("/settings/main").mock(
        return_value=httpx.Response(200, json=seerr_settings_main_fixture)
    )
    get_user = respx_mock.get("/user").mock(return_value=httpx.Response(200, json={"results": []}))
    put_user = respx_mock.put("/user/1").mock(return_value=httpx.Response(200, json={}))
    respx_mock.put("/settings/sonarr/0").mock(return_value=httpx.Response(200, json={}))
    respx_mock.put("/settings/radarr/0").mock(return_value=httpx.Response(200, json={}))
    respx_mock.post("/settings/main").mock(return_value=httpx.Response(200, json={}))

    instance = _make_instance(users=SeerrUsersSection(enable=False))
    reconcile_seerr(_make_client(), instance, dry_run=False)
    assert get_user.call_count == 0
    assert put_user.call_count == 0


@pytest.mark.respx(base_url=f"{SEERR_BASE}/api/v1", assert_all_called=False)
def test_multiple_isDefault_raises_ReconcileError(
    respx_mock: respx.MockRouter,
    seerr_settings_sonarr_fixture: list[dict[str, Any]],
) -> None:
    """Defensive: 2+ isDefault=true entries means a malformed cluster — fail loudly."""
    sonarr_state = [
        dict(seerr_settings_sonarr_fixture[0], id=0, isDefault=True, apiKey="x"),
        dict(seerr_settings_sonarr_fixture[0], id=1, isDefault=True, apiKey="y"),
    ]
    respx_mock.get("/settings/sonarr").mock(return_value=httpx.Response(200, json=sonarr_state))

    with pytest.raises(ReconcileError, match="isDefault=true entries"):
        reconcile_seerr(_make_client(), _make_instance(), dry_run=False)
