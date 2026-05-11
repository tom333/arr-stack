"""Radarr reconciler — Phase 3 scope (D-03-01 full parity with Sonarr).

Topological order (RESEARCH.md §10):

1. Ensure the ``arrconf-managed`` tag exists (D-02 / REQ-managed-tag).
2. Reconcile ``indexers`` (list resource, match by ``name``).
3. Reconcile ``root_folders`` (list resource, match by ``path`` — Pitfall 1).
4. Reconcile ``download_clients`` with managed-tag protection
   (D-04 / D-09 / T-01-04).
5. Reconcile ``notifications`` (list resource, match by ``name``).
6. Reconcile ``host_config`` (singleton, opt-in via section.enable — D-03-04).

Implementation note: This file intentionally mirrors the Sonarr reconciler
verbatim with the appropriate client substituted. Extracting the shared
helpers (`_execute`, `_reconcile_list_resource`, `_reconcile_host_config`,
`_ensure_managed_tag`) into a shared module is a future cleanup tracked in
RESEARCH.md Open Question 1 — deferred from Phase 3 to keep the file
ownership boundaries clean across parallel Wave-3 plans.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog
from pydantic import BaseModel

from arrconf.client_base import RadarrClient
from arrconf.config import HostConfigSection, RadarrInstance
from arrconf.differ import (
    Action,
    PlannedAction,
    diff_models,
    merge_fields_for_put,
    reconcile,
)
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
TAG_PATH = "/tag"
DOWNLOAD_CLIENT_PATH = "/downloadclient"
INDEXER_PATH = "/indexer"
NOTIFICATION_PATH = "/notification"
ROOT_FOLDER_PATH = "/rootfolder"
HOST_CONFIG_PATH = "/config/host"


@dataclass
class RadarrResult:
    """Result of a Radarr reconcile run (mirrors SonarrResult)."""

    plan: list[PlannedAction[DownloadClient]] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)
    managed_tag_id: int | None = None


def _ensure_managed_tag(client: RadarrClient, dry_run: bool) -> Tag:
    """Get or create the arrconf-managed tag (mirror of Sonarr — D-02)."""
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
    """Return a copy of dc with managed_tag_id appended to its tags if missing (D-02)."""
    if managed_tag_id in dc.tags:
        return dc
    return dc.model_copy(update={"tags": list(dc.tags) + [managed_tag_id]})


def _execute(
    client: RadarrClient,
    path: str,
    plan: list[PlannedAction[Any]],
    dry_run: bool,
) -> list[str]:
    """Execute the plan against the Radarr API. Mirror of sonarr._execute.

    Re-injects ``id`` after merge_fields_for_put (Pitfall 4); inherits
    forceSave=true on UPDATE PUT via the RadarrClient base (_ArrV3Client).
    """
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
            body = merge_fields_for_put(p.current, p.desired)
            body["id"] = p.current.id
            client.put(path, id=p.current.id, json=body)
            actions_taken.append(f"update:{p.name}")
        elif p.action == Action.DELETE:
            assert p.current is not None
            assert p.current.id is not None
            client.delete(path, id=p.current.id)
            actions_taken.append(f"delete:{p.name}")
    return actions_taken


def _reconcile_list_resource[T: BaseModel](
    client: RadarrClient,
    path: str,
    raw_current: list[dict[str, Any]],
    model_cls: type[T],
    desired_items: list[T],
    match_key: str,
    prune: bool,
    managed_tag_id: int | None,
    dry_run: bool,
) -> list[str]:
    """Reconcile a list-type resource (indexers / notifications / root_folders).

    Mirror of sonarr._reconcile_list_resource. Generic over T so the same
    helper works for every list resource Radarr reconciles.
    """
    current = [model_cls.model_validate(x) for x in raw_current]
    plan = reconcile(
        current=current,
        desired=desired_items,
        match_key=match_key,
        prune=prune,
        managed_tag_id=managed_tag_id,
    )
    return _execute(client, path, plan, dry_run)


def _reconcile_host_config(
    client: RadarrClient,
    section: HostConfigSection,
    dry_run: bool,
) -> None:
    """Reconcile Radarr host_config (singleton, D-03-04 opt-in gated).

    Mirror of sonarr._reconcile_host_config. Same Pitfall 4 (re-inject id)
    + forceSave-inherited discipline.

    CR-01 (Phase 3 code review): scope the diff to ONLY the keys declared
    by the operator in HostConfigSection. HostConfig uses extra="allow", so
    a parse of the raw GET carries every server-only field
    (analyticsEnabled, backupInterval, backupRetention, ...). Comparing
    a sparse desired against the full cluster state would flag drift on
    every server-only field and the resulting PUT body would OMIT those
    fields — silently dropping server config on every reconcile. Mirror of
    sonarr._reconcile_host_config (lines 200-227).
    """
    if not section.enable:
        log.info("host_config_reconcile_skipped")
        return

    raw = client.get(HOST_CONFIG_PATH)
    current_full = HostConfig.model_validate(raw)
    # Build desired from the section's writable fields only (enable is metadata):
    desired_payload = section.model_dump(exclude_none=True, exclude={"enable"})
    desired = HostConfig.model_validate(desired_payload)

    # CR-01: scope the diff to only the keys that the operator declared in HostConfigSection.
    # HostConfig uses extra="allow" so current_full carries ALL server fields; comparing
    # against a sparse desired would flag diffs on every server-only field (analyticsEnabled,
    # backupInterval, etc.) and the constructed PUT body would omit them. We want idempotence:
    # if the operator's desired subset matches the cluster, no PUT should be issued.
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
    if current_full.id is None:
        raise ReconcileError(
            "host_config GET returned no id — cannot construct PUT (this should never happen)"
        )
    body["id"] = current_full.id
    client.put(HOST_CONFIG_PATH, id=current_full.id, json=body)


def reconcile_radarr(
    client: RadarrClient,
    instance: RadarrInstance,
    dry_run: bool,
) -> RadarrResult:
    """Reconcile a Radarr instance (full parity with Sonarr — D-03-01).

    Topological order: tags → indexers → root_folders → download_clients →
    notifications → host_config (D-03-04 opt-in). See module docstring.
    """
    managed_tag = _ensure_managed_tag(client, dry_run)
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
        managed_tag_id=managed_tag.id,
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

    # 4. Download clients (managed-tag-stamped desired list).
    raw_current = client.get(DOWNLOAD_CLIENT_PATH)
    current_dcs = [DownloadClient.model_validate(x) for x in raw_current]
    desired_dcs = [
        _ensure_managed_tag_in_desired(dc, managed_tag_id) for dc in instance.download_clients.items
    ]
    dc_plan = reconcile(
        current=current_dcs,
        desired=desired_dcs,
        match_key="name",
        prune=instance.download_clients.prune,
        managed_tag_id=managed_tag.id,
    )
    actions_taken += _execute(client, DOWNLOAD_CLIENT_PATH, dc_plan, dry_run)

    # 5. Notifications.
    actions_taken += _reconcile_list_resource(
        client,
        NOTIFICATION_PATH,
        client.get(NOTIFICATION_PATH),
        Notification,
        instance.notifications.items,
        match_key="name",
        prune=instance.notifications.prune,
        managed_tag_id=managed_tag.id,
        dry_run=dry_run,
    )

    # 6. host_config (D-03-04 opt-in; singleton).
    _reconcile_host_config(client, instance.host_config, dry_run)

    return RadarrResult(
        plan=dc_plan,
        actions_taken=actions_taken,
        managed_tag_id=managed_tag.id,
    )
