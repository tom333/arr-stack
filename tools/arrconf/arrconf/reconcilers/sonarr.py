"""Sonarr reconciler — Phase 1 scope: download_clients only (D-08).

Topological order (Pitfall 3):

1. Ensure the ``arrconf-managed`` tag exists (D-02 / REQ-managed-tag).
2. Reconcile ``download_clients`` with managed-tag protection
   (D-04 / D-09 / T-01-04).

The managed tag itself is NEVER deleted by the reconciler — Phase 1
operates on download_clients only and the tag lifecycle is owned here
exclusively (creation only).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from arrconf.client_base import SonarrClient
from arrconf.config import SonarrInstance
from arrconf.differ import Action, PlannedAction, reconcile
from arrconf.resources.sonarr.download_client import DownloadClient
from arrconf.resources.sonarr.tag import Tag

log = structlog.get_logger()

MANAGED_TAG_LABEL = "arrconf-managed"
DRY_RUN_TAG_SENTINEL_ID = -1
DOWNLOAD_CLIENT_PATH = "/downloadclient"
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
            body = p.desired.model_dump(exclude_none=True, by_alias=False)
            # API requires id in PUT body; merge it from the current cluster state.
            body["id"] = p.current.id
            client.put(path, id=p.current.id, json=body)
            actions_taken.append(f"update:{p.name}")
        elif p.action == Action.DELETE:
            assert p.current is not None
            assert p.current.id is not None
            client.delete(path, id=p.current.id)
            actions_taken.append(f"delete:{p.name}")
    return actions_taken


def reconcile_sonarr(
    client: SonarrClient,
    instance: SonarrInstance,
    dry_run: bool,
) -> SonarrResult:
    """Reconcile a Sonarr instance.

    Phase 1 scope: ``download_clients`` only (D-08). Other resources land in
    later phases. The arrconf-managed tag is reconciled FIRST (Pitfall 3) so
    its id is available for stamping desired download_clients (D-02 /
    Pitfall 1: tag IDs not names).
    """
    managed_tag = _ensure_managed_tag(client, dry_run)
    managed_tag_id = managed_tag.id if managed_tag.id is not None else DRY_RUN_TAG_SENTINEL_ID

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
        managed_tag_id=managed_tag.id,
    )

    actions_taken = _execute(client, DOWNLOAD_CLIENT_PATH, plan, dry_run)

    return SonarrResult(
        plan=plan,
        actions_taken=actions_taken,
        managed_tag_id=managed_tag.id,
    )
