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
