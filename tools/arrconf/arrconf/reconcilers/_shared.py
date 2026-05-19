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

    Raises ReconcileError if a declared label has no matching tag — the operator
    must add the label to instance.tags.items so it is created in step 2 first.

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
                    f"download_client '{dc.name}': tag label '{label}' not found in {app_name} — "
                    "declare it in instance.tags.items so it is reconciled first (D-05-ORDER-01)"
                )
            tag_id = label_to_id[label]
            if tag_id not in resolved_ids:
                resolved_ids.append(tag_id)
        resolved.append(dc.model_copy(update={"tags": resolved_ids}))
    return resolved


def merge_with_manual(
    manual_items: list[Any],
    generated_items: list[Any],
    *,
    app: str,
    resource: str,
) -> list[Any]:
    """Per-resource toggle bridging Categories-derived resources with manual YAML (D-02).

    Phase 10 contract: when an operator has declared resources manually in the
    v0.2.0 flat section (``manual_items`` non-empty), arrconf uses the manual
    list verbatim and SKIPS the Categories-generated list entirely. When the
    manual list is empty, the Categories-derived list takes effect. There is
    no item-level merging — the toggle is per-resource (e.g. one toggle for
    ``sonarr.tags``, one for ``sonarr.root_folders``, etc.).

    Operator escape hatch: declare the full resource list manually to opt out
    of Categories-driven generation for that one resource. The transition layer
    is planned for removal in v0.4.0+ (REQ-categories-deprecation).

    Args:
        manual_items: the v0.2.0 ``instance.<section>.items`` list.
        generated_items: the Categories-derived list from
            ``arrconf.generators.categories``.
        app: app name for the log event (e.g. ``"sonarr"``, ``"qbit"``).
        resource: resource name for the log event (e.g. ``"tags"``,
            ``"root_folders"``, ``"download_clients"``).

    Returns:
        The list that should be passed to the reconciler. Caller assigns it
        back to ``instance.<section>.items`` before reconciler dispatch.

    Log events:
        - ``merge_decision`` with ``source="manual"``, ``n=len(manual_items)``,
          ``generated_skipped=len(generated_items)`` when manual wins.
        - ``merge_decision`` with ``source="categories"``,
          ``n=len(generated_items)`` when generated wins.

    Shared across all 6 reconciler pre-merge callsites (D-02). Called from
    ``arrconf.__main__`` per-app branches before reconciler dispatch.

    """
    if manual_items:
        log.info(
            "merge_decision",
            app=app,
            resource=resource,
            source="manual",
            n=len(manual_items),
            generated_skipped=len(generated_items),
        )
        return manual_items
    log.info(
        "merge_decision",
        app=app,
        resource=resource,
        source="categories",
        n=len(generated_items),
    )
    return generated_items
