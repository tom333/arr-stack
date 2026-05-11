"""Sonarr reconciler — Phase 3 scope (D-03-01).

Covers: download_clients + indexers + notifications + root_folders +
host_config (opt-in gated, D-03-04).

Topological order (RESEARCH.md §10):

1. Ensure the ``arrconf-managed`` tag exists (D-02 / REQ-managed-tag).
2. Reconcile ``indexers`` (list resource, match by ``name``).
3. Reconcile ``root_folders`` (list resource, match by ``path`` — Pitfall 1).
4. Reconcile ``download_clients`` with managed-tag protection
   (D-04 / D-09 / T-01-04). Original Phase 1 scope.
5. Reconcile ``notifications`` (list resource, match by ``name``).
6. Reconcile ``host_config`` (singleton, opt-in via section.enable — D-03-04).

Rationale for ordering: tags first (referenced by other resources). Indexers
are read-mostly alignment (created by Prowlarr sync, not by arrconf directly).
Root folders before download_clients because some download clients reference
root folder paths in their category routing. host_config last — it has the
highest destructive potential (can lock arrconf out of the app); opt-in
default keeps it from running unless the operator explicitly enables it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog
from pydantic import BaseModel

from arrconf.client_base import SonarrClient
from arrconf.config import (
    HostConfigSection,
    SonarrInstance,
)
from arrconf.differ import Action, PlannedAction, diff_models, merge_fields_for_put, reconcile
from arrconf.exceptions import ReconcileError
from arrconf.resources.sonarr.download_client import DownloadClient
from arrconf.resources.sonarr.host_config import HostConfig
from arrconf.resources.sonarr.indexer import Indexer
from arrconf.resources.sonarr.notification import Notification
from arrconf.resources.sonarr.root_folder import RootFolder
from arrconf.resources.sonarr.tag import Tag

log = structlog.get_logger()

MANAGED_TAG_LABEL = "arrconf-managed"
DRY_RUN_TAG_SENTINEL_ID = -1
DOWNLOAD_CLIENT_PATH = "/downloadclient"
INDEXER_PATH = "/indexer"
NOTIFICATION_PATH = "/notification"
ROOT_FOLDER_PATH = "/rootfolder"
HOST_CONFIG_PATH = "/config/host"
TAG_PATH = "/tag"


@dataclass
class SonarrResult:
    """Result of a Sonarr reconcile run."""

    plan: list[PlannedAction[DownloadClient]] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)
    managed_tag_id: int | None = None


def _ensure_managed_tag(client: SonarrClient, dry_run: bool) -> Tag:
    """Get or create the arrconf-managed tag.

    The tag is the single source of truth for "this resource was created by
    arrconf and may be pruned" (D-02). It is created idempotently and never
    deleted by the reconciler (REQ-managed-tag).
    """
    existing = [Tag.model_validate(t) for t in client.get(TAG_PATH)]
    for t in existing:
        if t.label == MANAGED_TAG_LABEL:
            log.info("managed_tag_found", id=t.id)
            return t
    if dry_run:
        log.info("would_create_managed_tag")
        return Tag(id=DRY_RUN_TAG_SENTINEL_ID, label=MANAGED_TAG_LABEL)
    created = client.post(TAG_PATH, json={"label": MANAGED_TAG_LABEL})
    new_tag = Tag.model_validate(created)
    log.info("managed_tag_created", id=new_tag.id)
    return new_tag


def _ensure_managed_tag_in_desired(
    dc: DownloadClient,
    managed_tag_id: int,
) -> DownloadClient:
    """Return a copy of ``dc`` with ``managed_tag_id`` appended to its tags if missing (D-02)."""
    if managed_tag_id in dc.tags:
        return dc
    return dc.model_copy(update={"tags": list(dc.tags) + [managed_tag_id]})


def _execute(
    client: SonarrClient,
    path: str,
    plan: list[PlannedAction[DownloadClient]],
    dry_run: bool,
) -> list[str]:
    """Execute the plan against the API. Returns list of action labels actually issued."""
    actions_taken: list[str] = []
    for p in plan:
        if p.action in (Action.NO_OP, Action.PRUNE_SKIP, Action.PRUNE_PROTECTED):
            continue
        if dry_run:
            log.info("dry_run_skip", action=p.action.value, name=p.name)
            continue
        if p.action == Action.ADD:
            assert p.desired is not None
            body = p.desired.model_dump(exclude_none=True, by_alias=False)
            client.post(path, json=body)
            actions_taken.append(f"add:{p.name}")
        elif p.action == Action.UPDATE:
            assert p.desired is not None
            assert p.current is not None
            assert p.current.id is not None
            # D-31/D-32: merge cluster's stored field values into the PUT body so empty
            # YAML values (e.g. credentials handled by env-only secret discipline) do
            # not overwrite cluster state. Asymmetric per D-32 — ADD has no cluster row.
            body = merge_fields_for_put(p.current, p.desired)
            # API requires id in PUT body; merge helper drops _READ_ONLY_FIELDS, so
            # re-inject from current.
            body["id"] = p.current.id
            client.put(path, id=p.current.id, json=body)
            actions_taken.append(f"update:{p.name}")
        elif p.action == Action.DELETE:
            assert p.current is not None
            assert p.current.id is not None
            client.delete(path, id=p.current.id)
            actions_taken.append(f"delete:{p.name}")
    return actions_taken


def _reconcile_list_resource(
    client: SonarrClient,
    path: str,
    raw_current: list[dict[str, Any]],
    model_cls: type[BaseModel],
    desired_items: list[Any],
    match_key: str,
    prune: bool,
    managed_tag_id: int | None,
    dry_run: bool,
) -> list[str]:
    """Reconcile a list-type resource (indexers / notifications / root_folders).

    Convenience wrapper around ``differ.reconcile`` + ``_execute`` that
    parses the raw GET response into Pydantic models. Generic over T so
    Radarr can reuse the same pattern in Plan 04 by copy-paste.

    For root folders, ``match_key="path"`` (NOT "name" — Pitfall 1). For all
    other list resources match_key defaults to "name" (D-20).
    """
    current = [model_cls.model_validate(x) for x in raw_current]
    plan = reconcile(
        current=current,
        desired=desired_items,
        match_key=match_key,
        prune=prune,
        managed_tag_id=managed_tag_id,
    )
    # NOTE: _execute is typed to DownloadClient today; the cast to a generic
    # list is safe at runtime because _execute only uses BaseModel API
    # (model_dump, .id). If a future refactor extracts _execute to
    # ``differ.execute_plan[T]`` generically, this cast can be removed.
    # For Plan 03 we keep the minimal-surface approach.
    return _execute(client, path, plan, dry_run)


def _reconcile_host_config(
    client: SonarrClient,
    section: HostConfigSection,
    dry_run: bool,
) -> None:
    """Reconcile the singleton host_config resource (D-03-04 opt-in gated).

    Pattern (RESEARCH.md Pattern 2):
        1. If section.enable is False → log skip event, return (no GET issued).
        2. GET /config/host → parse as HostConfig.
        3. Build desired HostConfig from section's writable fields.
        4. diff_models → if no diffs, log no-op, return.
        5. If dry_run → log dry_run_skip, return.
        6. merge_fields_for_put + re-inject id → PUT /config/host/{id} (forceSave inherited).

    Credentials in HostConfig (apiKey, password, passwordConfirmation, username)
    are excluded from the model (Plan 01 — Task 1.2), so they NEVER appear in
    desired/current dumps and NEVER reach the PUT body. The id MUST be
    re-injected after merge_fields_for_put strips it (Pitfall 4) — same
    pattern as the UPDATE branch of _execute() at line 103.
    """
    if not section.enable:
        log.info("host_config_reconcile_skipped")
        return

    raw = client.get(HOST_CONFIG_PATH)
    current_full = HostConfig.model_validate(raw)
    # Build desired from the section's writable fields only (enable is metadata):
    desired_payload = section.model_dump(exclude_none=True, exclude={"enable"})
    desired = HostConfig.model_validate(desired_payload)

    # Scope the diff to only the keys that the operator declared in HostConfigSection.
    # HostConfig uses extra="allow" so current_full carries ALL server fields; comparing
    # against a sparse desired would flag diffs on every server-only field (analyticsEnabled,
    # backupInterval, etc.). We want idempotence: if the operator's desired subset matches
    # the cluster, no PUT should be issued.
    scoped_keys = set(desired_payload.keys())
    current_scoped = HostConfig.model_validate({k: v for k, v in raw.items() if k in scoped_keys})

    diffs = diff_models(current_scoped, desired)
    if not diffs:
        log.info("host_config_no_op")
        return

    if dry_run:
        log.info("dry_run_skip", action="update", resource="host_config", diff_fields=diffs)
        return

    body = merge_fields_for_put(current_scoped, desired)
    # Pitfall 4: merge_fields_for_put strips _READ_ONLY_FIELDS (which includes id);
    # re-inject the cluster-known id so the PUT body validates server-side.
    if current_full.id is not None:
        body["id"] = current_full.id
        client.put(HOST_CONFIG_PATH, id=current_full.id, json=body)
    else:
        # Defensive: a host_config GET should always return id. If it doesn't,
        # surface as a reconciler-level error rather than silently issuing a
        # malformed PUT.
        raise ReconcileError(
            "host_config GET returned no id — cannot construct PUT (this should never happen)"
        )


def reconcile_sonarr(
    client: SonarrClient,
    instance: SonarrInstance,
    dry_run: bool,
) -> SonarrResult:
    """Reconcile a Sonarr instance (Phase 3 — D-03-01 full scope).

    Topological order: tags → indexers → root_folders → download_clients →
    notifications → host_config (D-03-04 opt-in). See module docstring for
    rationale.
    """
    managed_tag = _ensure_managed_tag(client, dry_run)
    # WR-04 (Phase 3 code review): use the defensive sentinel CONSISTENTLY everywhere.
    # Pre-fix, the sentinel was only applied to _ensure_managed_tag_in_desired and
    # raw managed_tag.id was passed to reconcile() / _reconcile_list_resource(),
    # so the defensive fallback only protected one call site. Now both forms use
    # managed_tag_id (with sentinel fallback) — defense in depth across the file.
    managed_tag_id = managed_tag.id if managed_tag.id is not None else DRY_RUN_TAG_SENTINEL_ID
    actions_taken: list[str] = []

    # 2. Indexers (read-mostly alignment; created by Prowlarr sync).
    actions_taken += _reconcile_list_resource(
        client,
        INDEXER_PATH,
        client.get(INDEXER_PATH),
        Indexer,
        instance.indexers.items,
        match_key="name",
        prune=instance.indexers.prune,
        managed_tag_id=managed_tag_id,
        dry_run=dry_run,
    )

    # 3. Root folders (match by PATH — Pitfall 1; no managed tag).
    actions_taken += _reconcile_list_resource(
        client,
        ROOT_FOLDER_PATH,
        client.get(ROOT_FOLDER_PATH),
        RootFolder,
        instance.root_folders.items,
        match_key="path",
        prune=instance.root_folders.prune,
        managed_tag_id=None,
        dry_run=dry_run,
    )

    # 4. Download clients (original Phase 1 — managed-tag-stamped desired list).
    raw_current = client.get(DOWNLOAD_CLIENT_PATH)
    current_dcs = [DownloadClient.model_validate(x) for x in raw_current]

    desired_dcs = [
        _ensure_managed_tag_in_desired(dc, managed_tag_id) for dc in instance.download_clients.items
    ]

    plan = reconcile(
        current=current_dcs,
        desired=desired_dcs,
        match_key="name",
        prune=instance.download_clients.prune,
        managed_tag_id=managed_tag_id,
    )

    actions_taken += _execute(client, DOWNLOAD_CLIENT_PATH, plan, dry_run)

    # 5. Notifications.
    actions_taken += _reconcile_list_resource(
        client,
        NOTIFICATION_PATH,
        client.get(NOTIFICATION_PATH),
        Notification,
        instance.notifications.items,
        match_key="name",
        prune=instance.notifications.prune,
        managed_tag_id=managed_tag_id,
        dry_run=dry_run,
    )

    # 6. host_config (D-03-04 opt-in; singleton).
    _reconcile_host_config(client, instance.host_config, dry_run)

    return SonarrResult(
        plan=plan,
        actions_taken=actions_taken,
        managed_tag_id=managed_tag_id,
    )
