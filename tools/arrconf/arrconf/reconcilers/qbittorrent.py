"""qBittorrent reconciler — Phase 5 scope (D-05-QBT-01 + D-05-QBT-02).

Covers: categories CRUD + preferences allowlist (opt-in).

The qBittorrent API diverges from *arr:
- Auth: cookie-based (POST /api/v2/auth/login → Set-Cookie SID) — handled by
  QbittorrentClient, NOT this reconciler.
- Categories GET: returns a dict keyed by category name, NOT a list. The
  helper ``_fetch_current_categories`` normalizes to list[Category].
- Categories create/update: both use form-encoded POST (not JSON).
- No DELETE endpoint for categories (use removeCategories POST). No PUT.
- Preferences: GET returns ~80 keys; arrconf manages ONLY the 4-key allowlist
  (QbitPreferences, extra="forbid"). Diff is scalar-dict comparison.
  Apply uses json.dumps — booleans MUST be JSON-typed true/false (Pitfall 4).

Scope strictly limited per ADR-5 / frontière arrconf/configarr:
- MUST NOT touch /api/v3/qualityprofile, /api/v3/customformat,
  /api/v3/qualitydefinition, or /api/v3/mediamanagement (configarr owns those).
- No torrent-level management (no add/remove/pause torrents).
- No managed-tag concept (R-05: qBit categories carry no arrconf-managed tags).

Topological order:
1. _reconcile_categories (CRUD list, match by name)
2. _reconcile_preferences (singleton, opt-in)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import structlog

from arrconf.client_base import QbittorrentClient
from arrconf.config import PreferencesSection, QbittorrentInstance
from arrconf.differ import Action, PlannedAction, reconcile
from arrconf.resources.qbittorrent.category import Category

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# API paths (relative to /api/v2 — the long-lived client base_url)
# ---------------------------------------------------------------------------

CATEGORIES_PATH = "/torrents/categories"
CREATE_CATEGORY_PATH = "/torrents/createCategory"
EDIT_CATEGORY_PATH = "/torrents/editCategory"
REMOVE_CATEGORIES_PATH = "/torrents/removeCategories"
APP_PREFERENCES_PATH = "/app/preferences"
SET_PREFERENCES_PATH = "/app/setPreferences"


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class QbittorrentResult:
    """Result of a qBittorrent reconcile run (mirrors ProwlarrResult).

    The plan field is populated EVEN IN DRY-RUN so the diff CLI gate can
    detect drift via ``any(p.action != Action.NO_OP for p in result.plan)``.
    The actions_taken list reflects writes actually issued (empty in dry-run).
    """

    plan: list[PlannedAction[Category]] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fetch_current_categories(client: QbittorrentClient) -> list[Category]:
    """GET /api/v2/torrents/categories and normalize dict response to list.

    qBit returns a dict keyed by category name:
        {"sonarr-tv": {"name": "sonarr-tv", "savePath": "/data/series"}, ...}

    We normalize to list[Category] using model_validate on each value.
    """
    raw = client.get(CATEGORIES_PATH)
    return [Category.model_validate(v) for v in raw.values()]


# ---------------------------------------------------------------------------
# Sub-reconcilers
# ---------------------------------------------------------------------------


def _reconcile_categories(
    client: QbittorrentClient,
    items: list[Category],
    prune: bool,
    dry_run: bool,
) -> tuple[list[PlannedAction[Category]], list[str]]:
    """Reconcile qBittorrent categories (list resource, match by name).

    Uses differ.reconcile with match_key="name". No managed-tag concept for
    qBit categories (R-05 — qBit has no tags on categories). Prune defaults
    to False (R-04 — cleanuparr depends on cleanuparr-unlinked surviving).

    Pitfall 3 (RESEARCH.md): createCategory body MUST send explicit savePath
    even if it's an empty string — qBit treats a missing savePath as "use
    default save path" which is /data/complete (the wrong location).
    """
    current = _fetch_current_categories(client)
    plan = reconcile(
        current=current,
        desired=items,
        match_key="name",
        prune=prune,
        managed_tag_id=None,  # R-05: no managed-tag concept for qBit categories
    )

    actions_taken: list[str] = []
    for p in plan:
        if p.action == Action.ADD:
            assert p.desired is not None
            log.info("plan_action", action="add", name=p.name)
            if dry_run:
                log.info("dry_run_skip", action="add", name=p.name)
            else:
                # Pitfall 3: send explicit savePath (even if empty string)
                client.post_form(
                    CREATE_CATEGORY_PATH,
                    data={"category": p.desired.name, "savePath": p.desired.savePath},
                )
                actions_taken.append(f"add:{p.name}")

        elif p.action == Action.UPDATE:
            assert p.desired is not None
            log.info("plan_action", action="update", name=p.name, diff_fields=p.diff_fields)
            if dry_run:
                log.info("dry_run_skip", action="update", name=p.name)
            else:
                client.post_form(
                    EDIT_CATEGORY_PATH,
                    data={"category": p.desired.name, "savePath": p.desired.savePath},
                )
                actions_taken.append(f"update:{p.name}")

        elif p.action == Action.DELETE:
            # Standard DELETE path — not reached for qBit categories because
            # differ.reconcile() emits PRUNE_PROTECTED when managed_tag_id=None.
            # Kept for completeness; unreachable in normal qBit usage.
            assert p.current is not None
            log.info("plan_action", action="delete", name=p.name)
            if dry_run:
                log.info("dry_run_skip", action="delete", name=p.name)
            else:
                client.post_form(
                    REMOVE_CATEGORIES_PATH,
                    data={"categories": p.current.name},
                )
                actions_taken.append(f"delete:{p.name}")

        elif p.action == Action.NO_OP:
            log.info("category_no_op", name=p.name)

        elif p.action == Action.PRUNE_SKIP:
            # prune=False default: log but do NOT delete (R-04)
            log.info("prune_skip", resource="qbit_category", name=p.name)

        elif p.action == Action.PRUNE_PROTECTED:
            # qBit categories have no managed-tag concept (R-05), so differ.reconcile()
            # emits PRUNE_PROTECTED (not DELETE) when managed_tag_id=None + prune=True.
            # We override here: if the operator explicitly set prune=True, execute the
            # delete (no tag guard needed — the operator is the trust boundary).
            assert p.current is not None
            if prune:
                log.info("plan_action", action="delete", name=p.name)
                if dry_run:
                    log.info("dry_run_skip", action="delete", name=p.name)
                else:
                    client.post_form(
                        REMOVE_CATEGORIES_PATH,
                        data={"categories": p.current.name},
                    )
                    actions_taken.append(f"delete:{p.name}")
            else:
                log.info("prune_skip", resource="qbit_category", name=p.name)

    return plan, actions_taken


def _reconcile_preferences(
    client: QbittorrentClient,
    section: PreferencesSection,
    dry_run: bool,
) -> None:
    """Reconcile qBit preferences allowlist (opt-in singleton, D-03-04 mirror).

    Pattern (mirrors _reconcile_host_config in sonarr.py):
    1. If section.enable is False → log skip event, return (no GET issued).
    2. GET /app/preferences → raw dict.
    3. Compute desired = section.values.model_dump(exclude_none=True).
    4. Diff against raw: diffs = {k: v for k, v in desired if raw.get(k) != v}.
    5. If no diffs → log no-op, return.
    6. If dry_run → log dry_run_skip with diff keys, return.
    7. Apply: POST /app/setPreferences with data={"json": json.dumps(diffs)}.
       Pitfall 4: json.dumps produces JSON-typed booleans (true/false), NOT
       quoted strings ("true"/"false"). MUST use json.dumps, not str().
    """
    if not section.enable:
        log.info("qbit_preferences_reconcile_skipped")
        return

    raw = client.get(APP_PREFERENCES_PATH)
    desired = section.values.model_dump(exclude_none=True)

    if not desired:
        log.info("qbit_preferences_no_op", reason="no keys declared in YAML")
        return

    # Scalar-dict diff (no pydantic diff_models — preferences is a flat dict)
    diffs = {k: v for k, v in desired.items() if raw.get(k) != v}

    if not diffs:
        log.info("qbit_preferences_no_op")
        return

    if dry_run:
        log.info(
            "dry_run_skip",
            action="update",
            resource="qbit_preferences",
            diff_keys=list(diffs),
        )
        return

    # Pitfall 4: json.dumps so booleans become JSON-typed true/false, NOT "true"/"false"
    client.post_form(SET_PREFERENCES_PATH, data={"json": json.dumps(diffs)})
    log.info("qbit_preferences_applied", diff_keys=list(diffs))


# ---------------------------------------------------------------------------
# Top-level reconciler
# ---------------------------------------------------------------------------


def reconcile_qbittorrent(
    client: QbittorrentClient,
    instance: QbittorrentInstance,
    dry_run: bool,
) -> QbittorrentResult:
    """Reconcile a qBittorrent instance (Phase 5 — D-05-QBT-02 full scope).

    Topological order:
    1. categories (CRUD list, match by name) — NO managed-tag step (R-05)
    2. preferences (singleton, opt-in)

    Returns QbittorrentResult with plan (populated in dry-run) + actions_taken
    (empty in dry-run). The diff CLI gates on result.plan, not actions_taken.
    """
    # Step 1: categories
    cat_plan, cat_actions = _reconcile_categories(
        client,
        instance.categories.items,
        prune=instance.categories.prune,
        dry_run=dry_run,
    )

    # Step 2: preferences (opt-in, default disabled)
    _reconcile_preferences(client, instance.preferences, dry_run=dry_run)

    log.info(
        "qbittorrent_reconcile_complete",
        categories_planned=len(cat_plan),
        categories_applied=len(cat_actions),
        dry_run=dry_run,
    )

    return QbittorrentResult(plan=cat_plan, actions_taken=cat_actions)
