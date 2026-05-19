"""Phase 10 idempotence FP regression tests (REQ-idempotence-fp-fix).

Each FP fix gets one focused test asserting that cluster GET responses with
extra (server-side) fields no longer cause spurious UPDATE plans.

Coverage:
- test_qbit_category_fp_fix (FP #1 — Plan 10-C) <- THIS TASK
- test_seerr_user_fp_fix    (FP #3 — Plan 10-F, to be added)
- test_prowlarr_app_fp_fix  (FP #2 — Plan 10-H, to be added)
"""

from __future__ import annotations

from arrconf.differ import Action, reconcile
from arrconf.reconcilers.qbittorrent import (
    QBIT_CATEGORY_MANAGED_FIELDS,
    _fetch_current_categories,
)
from arrconf.resources.qbittorrent.category import Category


class _StubClient:
    """Minimal QbittorrentClient stand-in for unit testing _fetch_current_categories."""

    def __init__(self, raw: dict[str, dict[str, object]]) -> None:
        self._raw = raw

    def get(self, _path: str) -> dict[str, dict[str, object]]:
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
