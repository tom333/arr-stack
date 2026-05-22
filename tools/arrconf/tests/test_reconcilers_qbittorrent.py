"""Tests for arrconf.reconcilers.qbittorrent.reconcile_qbittorrent — Phase 5.

All HTTP mocked via respx. Login is mocked in every test via _mock_qbit_login().
Coverage gate: >= 70% on arrconf.reconcilers.qbittorrent.

Key invariants verified:
- Pitfall 1: Referer header sent on login POST
- Pitfall 3: createCategory includes explicit savePath in form body
- Pitfall 4: setPreferences uses json.dumps (JSON-typed booleans, not strings)
- R-04: prune=False default keeps unmanaged categories (cleanuparr-unlinked etc.)
- ADR-5 frontière: qBit reconciler MUST NOT reach quality_profile/custom_format
- SC#2 unit signal: 6 categories created with correct savePaths
- SC#5 unit signal: idempotent — zero writes when cluster matches desired
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
import respx

from arrconf.client_base import QbittorrentClient
from arrconf.config import (
    CategoriesSection,
    PreferencesSection,
    QbittorrentInstance,
)
from arrconf.exceptions import AuthError
from arrconf.reconcilers.qbittorrent import reconcile_qbittorrent
from arrconf.resources.qbittorrent.category import Category
from arrconf.resources.qbittorrent.preferences import QbitPreferences

QBIT_BASE = "http://qbittorrent.test"
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "qbittorrent"

# ---------------------------------------------------------------------------
# The 6 Phase-5 categories (SC#2 / D-05-PATHS-01)
# ---------------------------------------------------------------------------

PHASE5_CATEGORIES = [
    Category(name="sonarr-tv", savePath="/data/series"),
    Category(name="sonarr-anime", savePath="/data/anime"),
    Category(name="sonarr-family", savePath="/data/family"),
    Category(name="radarr-movies", savePath="/data/films"),
    Category(name="radarr-anime", savePath="/data/films-anime"),
    Category(name="radarr-family", savePath="/data/films-family"),
]

# The 3 pre-existing cluster categories (qbit_categories_fixture baseline)
CLUSTER_EXISTING_CATEGORIES: dict[str, dict] = {
    "cleanuparr-unlinked": {"name": "cleanuparr-unlinked", "savePath": ""},
    "radarr": {"name": "radarr", "savePath": ""},
    "sonarr": {"name": "sonarr", "savePath": ""},
}


def _mock_qbit_login(respx_mock: respx.MockRouter) -> respx.Route:
    """Register the login POST mock on the respx router.

    Returns 200 "Ok." with a Set-Cookie SID header — the format qBit uses.
    All tests call this first since QbittorrentClient.__init__ performs the login.
    Returns the respx Route for call assertion.
    """
    return respx_mock.post(f"{QBIT_BASE}/api/v2/auth/login").mock(
        return_value=httpx.Response(
            200,
            text="Ok.",
            headers={"set-cookie": "SID=fake-sid-token; HttpOnly; SameSite=Strict; path=/"},
        )
    )


def _build_instance(
    categories: list[Category] | None = None,
    prune: bool = False,
    pref_enable: bool = False,
    pref_values: QbitPreferences | None = None,
) -> QbittorrentInstance:
    """Build a QbittorrentInstance for tests."""
    return QbittorrentInstance(
        base_url=QBIT_BASE,
        categories=CategoriesSection(prune=prune),
        preferences=PreferencesSection(
            enable=pref_enable,
            values=pref_values or QbitPreferences(),
        ),
    )


def _make_categories_response(cats: list[Category]) -> dict:
    """Build a qBit-style categories GET response dict from a list of Category objects."""
    return {c.name: {"name": c.name, "savePath": c.savePath} for c in cats}


# ===========================================================================
# Authentication tests (Pitfall 1, T-05-AUTH)
# ===========================================================================


@pytest.mark.respx(base_url=f"{QBIT_BASE}/api/v2", assert_all_called=False)
def test_login_with_referer_header(respx_mock: respx.MockRouter) -> None:
    """Pitfall 1: login POST MUST include Referer header for qBit CSRF protection.

    The respx mock asserts the Referer header value equals the base URL.
    """
    login_route = _mock_qbit_login(respx_mock)
    respx_mock.get("/torrents/categories").mock(
        return_value=httpx.Response(200, json={}, headers={"content-type": "application/json"})
    )

    client = QbittorrentClient(base_url=QBIT_BASE, username="admin", password="testpass")

    # Assert Referer was sent on the login request
    assert login_route.call_count == 1
    login_req = login_route.calls.last.request
    assert login_req.headers.get("referer") == QBIT_BASE, (
        f"Pitfall 1: Referer header missing or wrong. Got: {login_req.headers.get('referer')!r}"
    )
    client.close()


@pytest.mark.respx(base_url=f"{QBIT_BASE}/api/v2", assert_all_called=False)
def test_login_failure_raises_AuthError(respx_mock: respx.MockRouter) -> None:
    """T-05-AUTH: HTTP 403 on login → AuthError. Password NOT in exception message."""
    respx_mock.post(f"{QBIT_BASE}/api/v2/auth/login").mock(
        return_value=httpx.Response(403, text="Fails.")
    )

    with pytest.raises(AuthError) as exc_info:
        QbittorrentClient(base_url=QBIT_BASE, username="admin", password="supersecret")

    error_msg = str(exc_info.value)
    assert "403" in error_msg, f"AuthError should mention HTTP status 403, got: {error_msg!r}"
    assert "supersecret" not in error_msg, (
        "T-05-AUTH: password MUST NOT appear in AuthError message"
    )


@pytest.mark.respx(base_url=f"{QBIT_BASE}/api/v2", assert_all_called=False)
def test_login_missing_sid_cookie_raises_AuthError(respx_mock: respx.MockRouter) -> None:
    """T-05-AUTH: login returns 200 'Ok.' but no Set-Cookie → AuthError."""
    respx_mock.post(f"{QBIT_BASE}/api/v2/auth/login").mock(
        return_value=httpx.Response(200, text="Ok.")
        # No Set-Cookie header — SID not returned
    )

    with pytest.raises(AuthError) as exc_info:
        QbittorrentClient(base_url=QBIT_BASE, username="admin", password="testpass")

    assert "SID" in str(exc_info.value) or "cookie" in str(exc_info.value).lower()


@pytest.mark.respx(base_url=f"{QBIT_BASE}/api/v2", assert_all_called=False)
def test_login_qbit_5x_accepts_204_and_port_suffixed_cookie(
    respx_mock: respx.MockRouter,
) -> None:
    """qBit 5.x returns HTTP 204 No Content + Set-Cookie QBT_SID_<port>=... — must succeed.

    Regression: qBit 4.x returns 200 + 'Ok.' + SID cookie; 5.x diverges. arrconf
    initially rejected 5.x logins as failures because the legacy branch only
    accepted (200, 'Ok.', 'SID'). The cluster runs linuxserver/qbittorrent:5.x.
    """
    respx_mock.post(f"{QBIT_BASE}/api/v2/auth/login").mock(
        return_value=httpx.Response(
            204,
            headers={"set-cookie": "QBT_SID_8080=qbit5-sid-token; HttpOnly; path=/"},
        )
    )
    respx_mock.get("/torrents/categories").mock(
        return_value=httpx.Response(200, json={}, headers={"content-type": "application/json"})
    )

    # Should NOT raise — must accept 204 + QBT_SID_8080 cookie as a successful login
    client = QbittorrentClient(base_url=QBIT_BASE, username="admin", password="testpass")

    # Confirm the long-lived client carries the port-suffixed cookie verbatim
    # (sending "SID" instead would 401 on qBit 5.x).
    assert "QBT_SID_8080" in client._client.cookies
    assert client._client.cookies["QBT_SID_8080"] == "qbit5-sid-token"
    client.close()


# ===========================================================================
# Categories ADD tests
# ===========================================================================


@pytest.mark.respx(base_url=f"{QBIT_BASE}/api/v2", assert_all_called=False)
def test_add_new_category(respx_mock: respx.MockRouter) -> None:
    """Pitfall 3: createCategory POST body includes explicit savePath (URL-encoded)."""
    _mock_qbit_login(respx_mock)
    respx_mock.get("/torrents/categories").mock(
        return_value=httpx.Response(200, json={}, headers={"content-type": "application/json"})
    )
    create_route = respx_mock.post("/torrents/createCategory").mock(
        return_value=httpx.Response(200, text="Ok.")
    )

    desired = [Category(name="sonarr-tv", savePath="/data/series")]
    instance = _build_instance(categories=desired)
    client = QbittorrentClient(base_url=QBIT_BASE, username="admin", password="testpass")
    reconcile_qbittorrent(client, instance, desired, dry_run=False)
    client.close()

    assert create_route.call_count == 1
    body = create_route.calls.last.request.content.decode()
    # Form-encoded: category=sonarr-tv&savePath=%2Fdata%2Fseries
    assert "category=sonarr-tv" in body, f"Expected 'category=sonarr-tv' in form body: {body!r}"
    assert "savePath=%2Fdata%2Fseries" in body or "savePath=/data/series" in body, (
        f"Pitfall 3: savePath must be present in form body: {body!r}"
    )


@pytest.mark.respx(base_url=f"{QBIT_BASE}/api/v2", assert_all_called=False)
def test_create_six_categories_with_correct_savepaths(respx_mock: respx.MockRouter) -> None:
    """SC#2 unit signal: 6 createCategory POSTs with correct savePaths (D-05-PATHS-01)."""
    _mock_qbit_login(respx_mock)
    respx_mock.get("/torrents/categories").mock(
        return_value=httpx.Response(200, json={}, headers={"content-type": "application/json"})
    )
    create_route = respx_mock.post("/torrents/createCategory").mock(
        return_value=httpx.Response(200, text="Ok.")
    )

    instance = _build_instance(categories=PHASE5_CATEGORIES)
    client = QbittorrentClient(base_url=QBIT_BASE, username="admin", password="testpass")
    reconcile_qbittorrent(client, instance, PHASE5_CATEGORIES, dry_run=False)
    client.close()

    assert create_route.call_count == 6, (
        f"SC#2: expected 6 createCategory POSTs, got {create_route.call_count}"
    )

    # Verify each category name+savePath appears in the posted bodies
    posted_bodies = [parse_qs(call.request.content.decode()) for call in create_route.calls]
    posted_names = [b["category"][0] for b in posted_bodies]

    expected = {cat.name: cat.savePath for cat in PHASE5_CATEGORIES}
    for body in posted_bodies:
        name = body["category"][0]
        path = body["savePath"][0]
        assert name in expected, f"Unexpected category name: {name!r}"
        assert path == expected[name], (
            f"Wrong savePath for {name!r}: expected {expected[name]!r}, got {path!r}"
        )

    assert set(posted_names) == set(expected.keys())


@pytest.mark.respx(base_url=f"{QBIT_BASE}/api/v2", assert_all_called=False)
def test_update_category_when_savePath_changes(respx_mock: respx.MockRouter) -> None:
    """UPDATE path: when savePath differs → editCategory POST, no create, no delete."""
    _mock_qbit_login(respx_mock)
    # Cluster has sonarr-tv with wrong savePath
    cluster_state = {"sonarr-tv": {"name": "sonarr-tv", "savePath": "/wrong"}}
    respx_mock.get("/torrents/categories").mock(
        return_value=httpx.Response(
            200, json=cluster_state, headers={"content-type": "application/json"}
        )
    )
    create_route = respx_mock.post("/torrents/createCategory").mock(
        return_value=httpx.Response(200, text="Ok.")
    )
    edit_route = respx_mock.post("/torrents/editCategory").mock(
        return_value=httpx.Response(200, text="Ok.")
    )
    remove_route = respx_mock.post("/torrents/removeCategories").mock(
        return_value=httpx.Response(200, text="Ok.")
    )

    desired = [Category(name="sonarr-tv", savePath="/data/series")]
    instance = _build_instance(categories=desired)
    client = QbittorrentClient(base_url=QBIT_BASE, username="admin", password="testpass")
    reconcile_qbittorrent(client, instance, desired, dry_run=False)
    client.close()

    assert edit_route.call_count == 1, "Expected exactly 1 editCategory POST"
    assert create_route.call_count == 0, "No createCategory when only updating"
    assert remove_route.call_count == 0, "No removeCategories (prune=False)"

    body = parse_qs(edit_route.calls.last.request.content.decode())
    assert body["category"][0] == "sonarr-tv"
    assert body["savePath"][0] == "/data/series"


# ===========================================================================
# Idempotence test (SC#5)
# ===========================================================================


@pytest.mark.respx(base_url=f"{QBIT_BASE}/api/v2", assert_all_called=False)
def test_idempotent_no_op(respx_mock: respx.MockRouter) -> None:
    """SC#5 unit signal: cluster already matches desired → ZERO write calls of any kind."""
    _mock_qbit_login(respx_mock)
    # Cluster has exactly the 6 desired categories with matching savePaths
    cluster_state = _make_categories_response(PHASE5_CATEGORIES)
    respx_mock.get("/torrents/categories").mock(
        return_value=httpx.Response(
            200, json=cluster_state, headers={"content-type": "application/json"}
        )
    )
    create_route = respx_mock.post("/torrents/createCategory").mock(
        return_value=httpx.Response(200, text="Ok.")
    )
    edit_route = respx_mock.post("/torrents/editCategory").mock(
        return_value=httpx.Response(200, text="Ok.")
    )
    remove_route = respx_mock.post("/torrents/removeCategories").mock(
        return_value=httpx.Response(200, text="Ok.")
    )
    pref_route = respx_mock.post("/app/setPreferences").mock(
        return_value=httpx.Response(200, text="Ok.")
    )

    instance = _build_instance(categories=PHASE5_CATEGORIES, pref_enable=False)
    client = QbittorrentClient(base_url=QBIT_BASE, username="admin", password="testpass")
    result = reconcile_qbittorrent(client, instance, PHASE5_CATEGORIES, dry_run=False)
    client.close()

    assert create_route.call_count == 0, "SC#5: no createCategory on idempotent run"
    assert edit_route.call_count == 0, "SC#5: no editCategory on idempotent run"
    assert remove_route.call_count == 0, "SC#5: no removeCategories on idempotent run"
    assert pref_route.call_count == 0, "SC#5: no setPreferences on idempotent run"
    # All planned actions should be NO_OP
    from arrconf.differ import Action

    for p in result.plan:
        assert p.action == Action.NO_OP, f"Expected NO_OP but got {p.action} for {p.name!r}"


# ===========================================================================
# Prune tests (R-04)
# ===========================================================================


@pytest.mark.respx(base_url=f"{QBIT_BASE}/api/v2", assert_all_called=False)
def test_prune_false_keeps_unmanaged_categories(respx_mock: respx.MockRouter) -> None:
    """R-04: prune=False (default) keeps cluster categories not in YAML.

    The 3 pre-existing cluster categories (cleanuparr-unlinked, radarr, sonarr)
    MUST survive — zero removeCategories calls.
    """
    _mock_qbit_login(respx_mock)
    # Cluster has the 3 existing + the 6 desired (fully in-sync)
    all_cluster_cats = list(PHASE5_CATEGORIES) + [
        Category(name="cleanuparr-unlinked", savePath=""),
        Category(name="radarr", savePath=""),
        Category(name="sonarr", savePath=""),
    ]
    cluster_state = _make_categories_response(all_cluster_cats)
    respx_mock.get("/torrents/categories").mock(
        return_value=httpx.Response(
            200, json=cluster_state, headers={"content-type": "application/json"}
        )
    )
    remove_route = respx_mock.post("/torrents/removeCategories").mock(
        return_value=httpx.Response(200, text="Ok.")
    )

    # prune=False (default) — unmanaged categories survive
    instance = _build_instance(categories=PHASE5_CATEGORIES, prune=False)
    client = QbittorrentClient(base_url=QBIT_BASE, username="admin", password="testpass")
    reconcile_qbittorrent(client, instance, PHASE5_CATEGORIES, dry_run=False)
    client.close()

    assert remove_route.call_count == 0, (
        "R-04: removeCategories must NOT be called when prune=False"
    )


@pytest.mark.respx(base_url=f"{QBIT_BASE}/api/v2", assert_all_called=False)
def test_prune_true_removes_unmanaged_categories(respx_mock: respx.MockRouter) -> None:
    """Opt-in prune: prune=True removes categories not in YAML.

    3 pre-existing legacy categories (cleanuparr-unlinked, radarr, sonarr) should
    be deleted when prune=True is explicitly set by the operator.
    """
    _mock_qbit_login(respx_mock)
    # Cluster has the 3 existing + the 6 desired (all in-sync for desired)
    all_cluster_cats = list(PHASE5_CATEGORIES) + [
        Category(name="cleanuparr-unlinked", savePath=""),
        Category(name="radarr", savePath=""),
        Category(name="sonarr", savePath=""),
    ]
    cluster_state = _make_categories_response(all_cluster_cats)
    respx_mock.get("/torrents/categories").mock(
        return_value=httpx.Response(
            200, json=cluster_state, headers={"content-type": "application/json"}
        )
    )
    remove_route = respx_mock.post("/torrents/removeCategories").mock(
        return_value=httpx.Response(200, text="Ok.")
    )

    # prune=True (operator opt-in)
    instance = _build_instance(categories=PHASE5_CATEGORIES, prune=True)
    client = QbittorrentClient(base_url=QBIT_BASE, username="admin", password="testpass")
    reconcile_qbittorrent(client, instance, PHASE5_CATEGORIES, dry_run=False)
    client.close()

    assert remove_route.call_count == 3, (
        f"Expected 3 removeCategories calls (one per legacy entry), got {remove_route.call_count}"
    )


# ===========================================================================
# Preferences tests (Pitfall 4, Q2)
# ===========================================================================


@pytest.mark.respx(base_url=f"{QBIT_BASE}/api/v2", assert_all_called=False)
def test_preferences_skipped_when_disabled(respx_mock: respx.MockRouter) -> None:
    """When preferences.enable=False (default), no GET /app/preferences is issued."""
    _mock_qbit_login(respx_mock)
    respx_mock.get("/torrents/categories").mock(
        return_value=httpx.Response(200, json={}, headers={"content-type": "application/json"})
    )
    # Register these routes to detect unexpected calls
    get_pref_route = respx_mock.get("/app/preferences").mock(
        return_value=httpx.Response(200, json={}, headers={"content-type": "application/json"})
    )
    set_pref_route = respx_mock.post("/app/setPreferences").mock(
        return_value=httpx.Response(200, text="Ok.")
    )

    # preferences.enable=False (default)
    instance = _build_instance(pref_enable=False)
    client = QbittorrentClient(base_url=QBIT_BASE, username="admin", password="testpass")
    reconcile_qbittorrent(client, instance, [], dry_run=False)
    client.close()

    assert get_pref_route.call_count == 0, "No GET /app/preferences when preferences disabled"
    assert set_pref_route.call_count == 0, "No setPreferences when preferences disabled"


@pytest.mark.respx(base_url=f"{QBIT_BASE}/api/v2", assert_all_called=False)
def test_preferences_diff_uses_json_boolean_not_quoted(
    respx_mock: respx.MockRouter,
) -> None:
    """Pitfall 4: setPreferences body uses json.dumps → JSON-typed booleans (true/false).

    If the reconciler used str() or repr() instead of json.dumps, booleans would
    appear as 'True'/'False' (Python strings), which qBit rejects or misinterprets.
    This test asserts the form body carries json={'auto_tmm_enabled': true} (JSON bool).
    """
    _mock_qbit_login(respx_mock)
    respx_mock.get("/torrents/categories").mock(
        return_value=httpx.Response(200, json={}, headers={"content-type": "application/json"})
    )
    # Cluster has auto_tmm_enabled=false; desired is True → drift → setPreferences
    cluster_prefs = {
        "auto_tmm_enabled": False,
        "category_changed_tmm_enabled": False,
        "torrent_changed_tmm_enabled": True,
        "save_path": "/data/complete",
        "locale": "fr",
    }
    respx_mock.get("/app/preferences").mock(
        return_value=httpx.Response(
            200, json=cluster_prefs, headers={"content-type": "application/json"}
        )
    )
    set_pref_route = respx_mock.post("/app/setPreferences").mock(
        return_value=httpx.Response(200, text="Ok.")
    )

    pref_values = QbitPreferences(auto_tmm_enabled=True)
    instance = _build_instance(pref_enable=True, pref_values=pref_values)
    client = QbittorrentClient(base_url=QBIT_BASE, username="admin", password="testpass")
    reconcile_qbittorrent(client, instance, [], dry_run=False)
    client.close()

    assert set_pref_route.call_count == 1, "Expected 1 setPreferences POST"
    form_body = parse_qs(set_pref_route.calls.last.request.content.decode())
    assert "json" in form_body, "setPreferences form body must have a 'json' key"

    # Decode the JSON value and check it's a real JSON boolean (not a string)
    decoded = json.loads(form_body["json"][0])
    assert "auto_tmm_enabled" in decoded
    assert decoded["auto_tmm_enabled"] is True, (
        "Pitfall 4: auto_tmm_enabled must be JSON boolean True, not string 'True'"
    )
    assert isinstance(decoded["auto_tmm_enabled"], bool), (
        "Pitfall 4: value must be bool type, not str"
    )


@pytest.mark.respx(base_url=f"{QBIT_BASE}/api/v2", assert_all_called=False)
def test_preferences_no_op_when_in_sync(respx_mock: respx.MockRouter) -> None:
    """When preferences values match cluster exactly → zero setPreferences calls."""
    _mock_qbit_login(respx_mock)
    respx_mock.get("/torrents/categories").mock(
        return_value=httpx.Response(200, json={}, headers={"content-type": "application/json"})
    )
    # Cluster matches desired exactly
    cluster_prefs = {
        "auto_tmm_enabled": True,
        "category_changed_tmm_enabled": False,
        "torrent_changed_tmm_enabled": True,
        "save_path": "/data/complete",
        "locale": "fr",
    }
    respx_mock.get("/app/preferences").mock(
        return_value=httpx.Response(
            200, json=cluster_prefs, headers={"content-type": "application/json"}
        )
    )
    set_pref_route = respx_mock.post("/app/setPreferences").mock(
        return_value=httpx.Response(200, text="Ok.")
    )

    # Desired matches cluster exactly
    pref_values = QbitPreferences(
        auto_tmm_enabled=True,
        category_changed_tmm_enabled=False,
        torrent_changed_tmm_enabled=True,
        save_path="/data/complete",
    )
    instance = _build_instance(pref_enable=True, pref_values=pref_values)
    client = QbittorrentClient(base_url=QBIT_BASE, username="admin", password="testpass")
    reconcile_qbittorrent(client, instance, [], dry_run=False)
    client.close()

    assert set_pref_route.call_count == 0, (
        "SC#5 pref variant: no setPreferences when cluster matches desired"
    )
