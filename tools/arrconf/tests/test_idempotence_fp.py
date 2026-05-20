"""Phase 10 idempotence FP regression tests (REQ-idempotence-fp-fix).

Each FP fix gets one focused test asserting that cluster GET responses with
extra (server-side) fields no longer cause spurious UPDATE plans.

Coverage:
- test_qbit_category_fp_fix (FP #1 — Plan 10-C)
- test_seerr_user_fp_fix    (FP #3 — Plan 10-F)
- test_prowlarr_app_fp_fix  (FP #2 — Plan 10-H, to be added)
"""

from __future__ import annotations

from typing import Any

from arrconf.differ import Action, reconcile
from arrconf.reconcilers.qbittorrent import (
    QBIT_CATEGORY_MANAGED_FIELDS,
    _fetch_current_categories,
)
from arrconf.resources.qbittorrent.category import Category


class _StubClient:
    """Minimal QbittorrentClient stand-in for unit testing _fetch_current_categories."""

    def __init__(self, raw: dict[str, dict[str, Any]]) -> None:
        self._raw = raw

    def get(self, _path: str) -> dict[str, dict[str, Any]]:
        return self._raw


def test_qbit_category_managed_fields_constant() -> None:
    """QBIT_CATEGORY_MANAGED_FIELDS exposes exactly the 2 managed keys."""
    assert QBIT_CATEGORY_MANAGED_FIELDS == frozenset({"name", "savePath"})


def test_qbit_category_fp_fix_no_op_on_extras() -> None:
    """FP #1: cluster returns extra fields; differ should emit only NO_OP.

    Pre-fix: download_path/ratio_limit/etc. roundtripped via extra='allow'
    caused spurious UPDATE on every reconcile run.
    """
    cluster_with_extras = {
        "series-zoe": {
            "name": "series-zoe",
            "savePath": "/data/torrents/series-zoe",
            "download_path": None,
            "inactive_seeding_time_limit": -2,
            "ratio_limit": -2,
            "seeding_time_limit": -2,
            "share_limit_action": "Default",
        },
        "films": {
            "name": "films",
            "savePath": "/data/torrents/films",
            "download_path": None,
            "ratio_limit": -2,
        },
    }
    stub = _StubClient(cluster_with_extras)
    current = _fetch_current_categories(stub)  # type: ignore[arg-type]

    # Filtered models must have no extra keys in their model_dump output:
    for c in current:
        dumped = c.model_dump()
        for forbidden_key in (
            "download_path",
            "ratio_limit",
            "seeding_time_limit",
            "share_limit_action",
            "inactive_seeding_time_limit",
        ):
            assert forbidden_key not in dumped, (
                f"FP #1 leak: {forbidden_key} still in cluster-derived model after filter"
            )

    desired = [
        Category(name="series-zoe", savePath="/data/torrents/series-zoe"),
        Category(name="films", savePath="/data/torrents/films"),
    ]
    plan = reconcile(current=current, desired=desired, match_key="name", prune=False)

    # The full SC#2 dispositive: all-NO_OP plan when cluster == desired (modulo extras).
    assert plan, "reconcile returned empty plan — fixture mismatch with 2 desired entries"
    for p in plan:
        assert p.action == Action.NO_OP, (
            f"FP #1 NOT FIXED: plan action {p.action} for {p.name} "
            f"(diff_fields={p.diff_fields}). Expected NO_OP."
        )


# ===== FP #3: Seerr user =====

from arrconf.reconcilers.seerr import SEERR_USER_MANAGED_FIELDS  # noqa: E402


def test_seerr_user_managed_fields_constant() -> None:
    """SEERR_USER_MANAGED_FIELDS exposes exactly the 6 writable fields."""
    assert SEERR_USER_MANAGED_FIELDS == frozenset(
        {
            "displayName",
            "permissions",
            "movieQuotaDays",
            "movieQuotaLimit",
            "tvQuotaDays",
            "tvQuotaLimit",
        }
    )


def test_seerr_user_fp_fix_no_op_on_extras() -> None:
    """FP #3: cluster GET returns extras (settings, avatar, requestCount, timestamps).

    Pre-fix: admin_current carried all extra keys → _payloads_equivalent saw
    them in current but not in put_body → returned False → spurious UPDATE.
    Post-fix: cluster_filtered limited to SEERR_USER_MANAGED_FIELDS → equivalent.
    """
    import respx

    from arrconf.client_base import SeerrClient
    from arrconf.config import SeerrUsersSection
    from arrconf.reconcilers.seerr import _reconcile_user
    from arrconf.resources.seerr import SeerrUser

    base_url = "http://seerr.test:5055"
    cluster_with_extras = [
        {
            "id": 1,
            "displayName": "Admin",
            "permissions": 2,
            "movieQuotaDays": None,
            "movieQuotaLimit": None,
            "tvQuotaDays": None,
            "tvQuotaLimit": None,
            # extras that USED to cause FP:
            "username": "admin",
            "email": "admin@example.com",
            "userType": 1,
            "plexId": None,
            "jellyfinUserId": None,
            "avatar": "/avatars/1.png",
            "avatarETag": "abc123",
            "avatarVersion": 5,
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-05-19T12:00:00Z",
            "requestCount": 14,
            "warnings": [],
            "settings": {"notifications": True},
        }
    ]

    with respx.mock(base_url=f"{base_url}/api/v1") as router:
        router.get("/user").respond(json=cluster_with_extras)
        # No PUT mock — if FP fires, the test fails because the unhandled request raises.

        client = SeerrClient(base_url=base_url, api_key="test-key")

        section = SeerrUsersSection(
            enable=True,
            admin=SeerrUser(
                displayName="Admin",
                permissions=2,
                movieQuotaDays=None,
                movieQuotaLimit=None,
                tvQuotaDays=None,
                tvQuotaLimit=None,
            ),
        )

        result = _reconcile_user(client, section, dry_run=False)

    # FP fix dispositive: no actions taken because cluster_filtered == put_body.
    assert result == [], f"FP #3 NOT FIXED: _reconcile_user emitted {result}"


# ===== FP #2: Prowlarr Application =====

from arrconf.reconcilers.prowlarr import (  # noqa: E402
    PROWLARR_APP_MANAGED_FIELD_NAMES,
    PROWLARR_APP_MANAGED_FIELDS,
)


def test_prowlarr_app_managed_fields_constant() -> None:
    """PROWLARR_APP_MANAGED_FIELDS exposes the 7 managed top-level fields."""
    assert PROWLARR_APP_MANAGED_FIELDS == frozenset(
        {
            "name",
            "enable",
            "implementation",
            "configContract",
            "syncLevel",
            "fields",
            "tags",
        }
    )


def test_prowlarr_app_managed_field_names_constant() -> None:
    """PROWLARR_APP_MANAGED_FIELD_NAMES exposes the 3 managed sub-fields (B2b allowlist)."""
    assert PROWLARR_APP_MANAGED_FIELD_NAMES == frozenset({"prowlarrUrl", "baseUrl", "apiKey"})


def test_prowlarr_app_fp_fix_no_op_on_extras() -> None:
    """FP #2: cluster GET with server-side extras (presets, message, etc.) -> no UPDATE.

    Verifies that filtering to PROWLARR_APP_MANAGED_FIELDS before model_validate
    drops the extra top-level keys so the differ doesn't see them as drift.
    """
    from arrconf.differ import Action, reconcile
    from arrconf.reconcilers.prowlarr import PROWLARR_APP_MANAGED_FIELDS
    from arrconf.resources.prowlarr.application import Application

    cluster_with_extras = [
        {
            "id": 1,
            "name": "Sonarr",
            "enable": True,
            "implementation": "Sonarr",
            "configContract": "SonarrSettings",
            "syncLevel": "fullSync",
            "fields": [],
            "tags": [],
            # extras causing FP #2:
            "implementationName": "Sonarr",
            "infoLink": "https://wiki.servarr.com/prowlarr/applications",
            "presets": None,
            "message": None,
        },
    ]

    desired = [
        Application(
            name="Sonarr",
            enable=True,
            implementation="Sonarr",
            configContract="SonarrSettings",
            syncLevel="fullSync",
            fields=[],
            tags=[],
        ),
    ]

    # Apply the FP fix filter (mirrors the prowlarr.py callsite):
    current_apps = [
        Application.model_validate({k: v for k, v in x.items() if k in PROWLARR_APP_MANAGED_FIELDS})
        for x in cluster_with_extras
    ]

    plan = reconcile(current=current_apps, desired=desired, match_key="name", prune=False)
    assert plan, "reconcile returned empty plan"
    for p in plan:
        assert p.action == Action.NO_OP, (
            f"FP #2 NOT FIXED: plan action {p.action} for {p.name} "
            f"(diff_fields={p.diff_fields}). Expected NO_OP."
        )


def test_prowlarr_app_subfield_fp_fix_no_op_on_extra_fields() -> None:
    """FP #2 sub-field filter (B2b): cluster fields[] with extras does not trigger UPDATE.

    Prowlarr GET /applications returns 10+ FieldKV entries per app
    (syncCategories, importListSyncInterval, animeSyncCategories, etc.).
    The reconciler only manages 3 (prowlarrUrl, baseUrl, apiKey).
    Without the sub-field allowlist, diff_models flags "fields" as drifted
    on every run even when the 3 managed fields are unchanged.

    Mirrors the callsite logic in reconcile_prowlarr: filter cluster fields[]
    to PROWLARR_APP_MANAGED_FIELD_NAMES before model_validate.
    """
    from arrconf.differ import Action, reconcile
    from arrconf.resources.prowlarr.application import Application
    from arrconf.resources.sonarr.download_client import FieldKV

    # Cluster response with 3 managed fields + many extras (realistic production shape):
    cluster_with_extra_fields = [
        {
            "id": 1,
            "name": "Sonarr",
            "enable": True,
            "implementation": "Sonarr",
            "configContract": "SonarrSettings",
            "syncLevel": "fullSync",
            "tags": [],
            "fields": [
                {"name": "prowlarrUrl", "value": "http://prowlarr:9696"},
                {"name": "baseUrl", "value": "http://sonarr:8989"},
                {"name": "apiKey", "value": "secret-key", "privacy": "apiKey"},
                # extras causing FP #2 sub-field drift:
                {"name": "syncCategories", "value": [5000, 5030]},
                {"name": "importListSyncInterval", "value": 60},
                {"name": "animeSyncCategories", "value": [5070]},
                {"name": "searchFallback", "value": False},
                {"name": "syncRejectBlocklistedTorrentHashesWhileGrabbing", "value": False},
            ],
        }
    ]

    desired = [
        Application(
            name="Sonarr",
            enable=True,
            implementation="Sonarr",
            configContract="SonarrSettings",
            syncLevel="fullSync",
            fields=[
                FieldKV(name="prowlarrUrl", value="http://prowlarr:9696"),
                FieldKV(name="baseUrl", value="http://sonarr:8989"),
                FieldKV(name="apiKey", value="secret-key", privacy="apiKey"),
            ],
            tags=[],
        ),
    ]

    # Mirror the reconcile_prowlarr filter callsite (B2 + B2b):
    _app_keep = PROWLARR_APP_MANAGED_FIELDS | {"id"}
    current_apps = []
    for x in cluster_with_extra_fields:
        filtered = {k: v for k, v in x.items() if k in _app_keep}
        if "fields" in filtered and isinstance(filtered["fields"], list):
            filtered["fields"] = [
                f
                for f in filtered["fields"]
                if isinstance(f, dict) and f.get("name") in PROWLARR_APP_MANAGED_FIELD_NAMES
            ]
        current_apps.append(Application.model_validate(filtered))

    plan = reconcile(current=current_apps, desired=desired, match_key="name", prune=False)
    assert plan, "reconcile returned empty plan"
    for p in plan:
        assert p.action == Action.NO_OP, (
            f"FP #2 sub-field NOT FIXED: plan action {p.action} for {p.name} "
            f"(diff_fields={p.diff_fields}). Expected NO_OP — extra fields[] entries "
            "must be filtered before model_validate."
        )


def test_prowlarr_app_real_change_still_detected() -> None:
    """Sanity: managed field drift (syncLevel: fullSync -> disabled) still fires UPDATE."""
    from arrconf.differ import Action, reconcile
    from arrconf.reconcilers.prowlarr import PROWLARR_APP_MANAGED_FIELDS
    from arrconf.resources.prowlarr.application import Application

    cluster = [
        {
            "id": 1,
            "name": "Sonarr",
            "enable": True,
            "implementation": "Sonarr",
            "configContract": "SonarrSettings",
            "syncLevel": "fullSync",
            "fields": [],
            "tags": [],
        },
    ]
    desired = [
        Application(
            name="Sonarr",
            enable=True,
            implementation="Sonarr",
            configContract="SonarrSettings",
            syncLevel="disabled",
            fields=[],
            tags=[],
        )
    ]

    current_apps = [
        Application.model_validate({k: v for k, v in x.items() if k in PROWLARR_APP_MANAGED_FIELDS})
        for x in cluster
    ]
    plan = reconcile(current=current_apps, desired=desired, match_key="name", prune=False)
    update_actions = [p for p in plan if p.action == Action.UPDATE]
    assert len(update_actions) == 1, f"Real change not detected; plan={plan}"


# ===== FP #4: Prowlarr prowlarr_url vs base_url separation =====


def test_prowlarr_url_override_no_op_with_live_fixture() -> None:
    """FP #4 (D-10-FP3-PROWLARR-URL): prowlarr_url field prevents prowlarrUrl field drift.

    When the operator accesses Prowlarr via an external URL (e.g. a reverse-proxy
    or tunnel) but the cluster stores the in-cluster service URL in the Application's
    prowlarrUrl field, the reconciler MUST inject the in-cluster URL (prowlarr_url)
    into the desired Application — NOT the external access URL (base_url).

    Pre-fix: _build_desired_application always used instance.base_url as prowlarrUrl,
    so external-URL configs caused diff_fields=['fields'] on EVERY run (prowlarrUrl
    in cluster = in-cluster URL; desired = external URL → never converges).

    Post-fix: reconcile_prowlarr passes instance.prowlarr_url or instance.base_url
    to _build_desired_application — operators set prowlarr_url to the in-cluster URL
    and the diff converges to NO_OP.

    Uses the live cluster fixture captured 2026-05-20 (tests/fixtures/prowlarr/
    applications_live_2026-05-20.json) — real Prowlarr GET /applications shape.
    """
    import json
    import os
    from pathlib import Path

    from arrconf.config import AppEntry
    from arrconf.differ import Action, reconcile
    from arrconf.reconcilers.prowlarr import (
        PROWLARR_APP_MANAGED_FIELD_NAMES,
        PROWLARR_APP_MANAGED_FIELDS,
        _build_desired_application,
    )
    from arrconf.resources.prowlarr.application import Application

    fixture_path = (
        Path(__file__).parent / "fixtures" / "prowlarr" / "applications_live_2026-05-20.json"
    )
    raw_current = json.loads(fixture_path.read_text())

    # Apply B2 + B2b filter (mirrors reconcile_prowlarr callsite):
    _app_keep = PROWLARR_APP_MANAGED_FIELDS | {"id"}
    current_apps = []
    for x in raw_current:
        filtered = {k: v for k, v in x.items() if k in _app_keep}
        if "fields" in filtered and isinstance(filtered["fields"], list):
            filtered["fields"] = [
                f
                for f in filtered["fields"]
                if isinstance(f, dict) and f.get("name") in PROWLARR_APP_MANAGED_FIELD_NAMES
            ]
        current_apps.append(Application.model_validate(filtered))

    # Desired built using the production in-cluster prowlarr_url (same as stored in cluster):
    os.environ.setdefault("SONARR_API_KEY", "test-sonarr-key")
    os.environ.setdefault("RADARR_API_KEY", "test-radarr-key")

    prowlarr_url = "http://prowlarr.selfhost.svc.cluster.local:9696"  # in-cluster URL
    entries = [
        AppEntry(
            name="Sonarr",
            type="sonarr",
            base_url="http://sonarr.selfhost.svc.cluster.local:8989",
            api_key_env="SONARR_API_KEY",
            sync_level="fullSync",
        ),
        AppEntry(
            name="Radarr",
            type="radarr",
            base_url="http://radarr.selfhost.svc.cluster.local:7878",
            api_key_env="RADARR_API_KEY",
            sync_level="fullSync",
        ),
    ]
    desired_apps = [_build_desired_application(e, prowlarr_url=prowlarr_url) for e in entries]

    plan = reconcile(current=current_apps, desired=desired_apps, match_key="name", prune=False)
    assert plan, "reconcile returned empty plan — fixture mismatch"
    for p in plan:
        assert p.action == Action.NO_OP, (
            f"FP #4 NOT FIXED: plan action {p.action} for {p.name} "
            f"(diff_fields={p.diff_fields}). Expected NO_OP.\n"
            "If this fails, prowlarr_url separation is broken or the live fixture "
            "values have changed."
        )


def test_prowlarr_url_fallback_to_base_url() -> None:
    """When prowlarr_url is None, _build_desired_application uses base_url (backward compat).

    This covers the production chart case: base_url IS the in-cluster URL, so no
    prowlarr_url override is needed. The fallback in reconcile_prowlarr
    (instance.prowlarr_url or instance.base_url) must pass base_url when prowlarr_url=None.
    """
    import os

    from arrconf.config import AppEntry
    from arrconf.reconcilers.prowlarr import _build_desired_application

    os.environ.setdefault("SONARR_API_KEY", "test-key")
    entry = AppEntry(
        name="Sonarr",
        type="sonarr",
        base_url="http://sonarr.selfhost.svc.cluster.local:8989",
        api_key_env="SONARR_API_KEY",
        sync_level="fullSync",
    )
    # When prowlarr_url IS the base_url (production chart scenario):
    app = _build_desired_application(
        entry,
        prowlarr_url="http://prowlarr.selfhost.svc.cluster.local:9696",
    )
    prowlarr_url_field = next(f for f in app.fields if f.name == "prowlarrUrl")
    assert prowlarr_url_field.value == "http://prowlarr.selfhost.svc.cluster.local:9696", (
        "prowlarrUrl field should equal the prowlarr_url argument"
    )


def test_prowlarr_instance_prowlarr_url_field() -> None:
    """ProwlarrInstance accepts optional prowlarr_url field (schema regression)."""
    from arrconf.config import ProwlarrInstance

    # Without prowlarr_url (backward-compat — production chart):
    inst_no_override = ProwlarrInstance(
        base_url="http://prowlarr.selfhost.svc.cluster.local:9696",
    )
    assert inst_no_override.prowlarr_url is None

    # With prowlarr_url (tunnel/reverse-proxy scenario):
    inst_with_override = ProwlarrInstance(
        base_url="https://prowlarr.tgu.ovh",
        prowlarr_url="http://prowlarr.selfhost.svc.cluster.local:9696",
    )
    assert inst_with_override.prowlarr_url == "http://prowlarr.selfhost.svc.cluster.local:9696"
    assert inst_with_override.base_url == "https://prowlarr.tgu.ovh"
