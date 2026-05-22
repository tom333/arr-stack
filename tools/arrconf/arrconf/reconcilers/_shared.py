"""Shared reconciler helpers — used by both Sonarr and Radarr reconcilers.

Extracted from sonarr.py (Plan 06) because these helpers are byte-equivalent
between the two reconcilers and diverging them would introduce maintenance drift.

Functions in this module are private to the reconcilers package (prefix ``_``).
They accept a ``client`` typed as ``ArrApiClient`` — the common base class for
both SonarrClient and RadarrClient (ADR-8 / client_base.py).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from arrconf.exceptions import ReconcileError
from arrconf.resources.sonarr.remote_path_mapping import RemotePathMapping
from arrconf.resources.sonarr.tag import Tag

if TYPE_CHECKING:
    from arrconf.client_base import ArrApiClient

log = structlog.get_logger()

REMOTE_PATH_MAPPING_PATH = "/remotepathmapping"
TAG_PATH = "/tag"


def _reconcile_remote_path_mappings(
    client: ArrApiClient,
    items: list[RemotePathMapping],
    prune: bool,
    dry_run: bool,
) -> list[str]:
    """Reconcile remote path mappings via composite-key matching (D-05-PATHMAP-01).

    The Sonarr/Radarr API has NO PUT endpoint for remote path mappings — updates
    are performed as DELETE (by id) then POST (RESEARCH Pattern 6 + Pitfall 1).

    Match key is the composite tuple (host, remotePath). localPath changes
    produce DELETE+ADD; key changes are treated as separate (different) entries.

    Pitfall 6: both remotePath AND localPath MUST end with '/' in the YAML.
    This reconciler does NOT auto-append slashes — YAML is the operator's
    responsibility. The smoke test (test_rpm_trailing_slash_invariant) documents
    the gap; Plan 07 enforces trailing slashes via chart-side YAML review.

    Shared between Sonarr and Radarr — byte-equivalent implementation (PATTERNS
    line 391). Both apps expose the same /remotepathmapping endpoint shape and
    use the same qBittorrent host.
    """
    raw = client.get(REMOTE_PATH_MAPPING_PATH)
    current = [RemotePathMapping.model_validate(x) for x in raw]
    cur_by_key: dict[tuple[str, str], RemotePathMapping] = {
        (c.host, c.remotePath): c for c in current
    }
    des_by_key: dict[tuple[str, str], RemotePathMapping] = {
        (d.host, d.remotePath): d for d in items
    }
    actions: list[str] = []

    for k, des in des_by_key.items():
        cur = cur_by_key.get(k)
        if cur is None:
            if dry_run:
                log.info("dry_run_skip", action="add", resource="rpm", key=str(k))
            else:
                client.post(REMOTE_PATH_MAPPING_PATH, json=des.model_dump(exclude_none=True))
            actions.append(f"add:{k[0]}|{k[1]}")
        elif cur.localPath != des.localPath:
            # No PUT endpoint — DELETE current then ADD desired (Pattern 6).
            if dry_run:
                log.info(
                    "dry_run_skip",
                    action="update_via_delete_add",
                    resource="rpm",
                    key=str(k),
                )
            else:
                assert cur.id is not None
                client.delete(REMOTE_PATH_MAPPING_PATH, id=cur.id)
                client.post(REMOTE_PATH_MAPPING_PATH, json=des.model_dump(exclude_none=True))
            actions.append(f"update:{k[0]}|{k[1]}")

    if prune:
        for k, cur in cur_by_key.items():
            if k not in des_by_key:
                if dry_run:
                    log.info("dry_run_skip", action="delete", resource="rpm", key=str(k))
                else:
                    assert cur.id is not None
                    client.delete(REMOTE_PATH_MAPPING_PATH, id=cur.id)
                actions.append(f"delete:{k[0]}|{k[1]}")
    else:
        for k in cur_by_key:
            if k not in des_by_key:
                log.info("prune_skip", resource="rpm", key=str(k))

    return actions


def _resolve_download_client_tag_labels(
    items: list[Any],
    all_tags: list[Tag],
    app_name: str = "Sonarr/Radarr",
) -> list[Any]:
    """Resolve label-based tags in DownloadClient.tag_labels to integer IDs.

    The YAML operator declares tag routing via ``tag_labels: [tv]`` (human-
    readable label names). This helper resolves each label to its server-assigned
    integer id using the post-reconcile ``all_tags`` list (step 2 of D-05-ORDER-01).

    Raises ReconcileError if a declared label has no matching tag. Post-Phase 12-B,
    tag labels are derived from ``categories[]`` — the operator declares a new
    category, the generator produces a matching tag, and step 2 reconciles it
    before this resolver runs. A mismatch usually signals a stale RadarrDerived /
    SonarrDerived test fixture.

    Returns new DownloadClient instances (immutable copy via model_copy) with
    resolved integer ids appended to the existing ``tags`` list.

    Shared between Sonarr and Radarr — byte-equivalent implementation (PATTERNS
    line 391). The ``app_name`` parameter is used only in the error message for
    operator-facing clarity.
    """
    label_to_id: dict[str, int] = {}
    for t in all_tags:
        if t.id is not None:
            label_to_id[t.label] = t.id

    resolved = []
    for dc in items:
        if not dc.tag_labels:
            resolved.append(dc)
            continue
        resolved_ids = list(dc.tags)
        for label in dc.tag_labels:
            if label not in label_to_id:
                raise ReconcileError(
                    f"download_client '{dc.name}': tag label '{label}' not found "
                    f"in {app_name} — generator output drifted from cluster tags "
                    "(Phase 12-B: tags derive from categories[]; this should not "
                    "happen at runtime — likely a stale test fixture)"
                )
            tag_id = label_to_id[label]
            if tag_id not in resolved_ids:
                resolved_ids.append(tag_id)
        resolved.append(dc.model_copy(update={"tags": resolved_ids}))
    return resolved
