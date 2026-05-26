"""Sonarr reconciler — Phase 5 scope (D-05-SPLIT-01, D-05-PATHMAP-01, D-05-MIG-01).

Covers: download_clients + indexers + notifications + root_folders +
host_config (opt-in gated, D-03-04) + tags (tv/anime/family, D-05-SPLIT-01) +
remote_path_mappings (composite-key DELETE+ADD, D-05-PATHMAP-01) +
series_tags (retroactive default-tag via bulk editor, D-05-MIG-01) +
content_tags (genre-keyword-driven post-import retagger, Phase 6, D-06-RETAG-01).

Topological order (D-05-ORDER-01 — regression-tested in test_reconcile_order):

1. Ensure the ``arrconf-managed`` tag exists (D-02 / REQ-managed-tag).
2. Reconcile ``tags`` (tv, anime, family) — MUST precede download_clients
   so tag IDs exist for label→id resolution.
3. Reconcile ``indexers`` (list resource, match by ``name``).
4. Reconcile ``root_folders`` (list resource, match by ``path`` — Pitfall 1).
5. Reconcile ``remote_path_mappings`` (composite-key DELETE+ADD — no PUT endpoint;
   D-05-PATHMAP-01).
6. Reconcile ``download_clients`` with managed-tag protection
   (D-04 / D-09 / T-01-04) and label→id resolution for tags.
7. Reconcile ``notifications`` (list resource, match by ``name``).
8. Reconcile ``host_config`` (singleton, opt-in via section.enable — D-03-04).
9. Reconcile ``series_tags`` — MUST run AFTER download_clients (D-05-ORDER-01)
   to ensure tagged series route to already-configured download clients.
10. Reconcile ``content_tags`` — MUST run AFTER series_tags (D-06-RETAG-01).
    Genre-keyword-driven post-import retagger layers per-genre tags on top of
    the bulk-tagged baseline.

Rationale for ordering: tags first (referenced by other resources). Indexers
are read-mostly alignment (created by Prowlarr sync, not by arrconf directly).
Root folders before download_clients because some download clients reference
root folder paths in their category routing. host_config last — it has the
highest destructive potential (can lock arrconf out of the app); opt-in
default keeps it from running unless the operator explicitly enables it.
series_tags last before content_tags — the bulk editor touches REAL series
collection (D-05-MIG-01). content_tags layers on top (D-06-RETAG-01).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog
from pydantic import BaseModel

from arrconf.client_base import SonarrClient
from arrconf.config import (
    ContentRoutingSection,
    HostConfigSection,
    SeriesTagsSection,
    SonarrInstance,
    TagItem,
    TagsSection,
)
from arrconf.differ import Action, PlannedAction, diff_models, merge_fields_for_put, reconcile
from arrconf.exceptions import ReconcileError
from arrconf.generators.categories import SonarrDerived
from arrconf.reconcilers._shared import (
    _reconcile_remote_path_mappings,
    _resolve_download_client_tag_labels,
    _resolve_qbit_credentials_from_env,
)
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
SERIES_PATH = "/series"
SERIES_EDITOR_PATH = "/series/editor"


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
    plan: list[PlannedAction[Any]],
    dry_run: bool,
) -> list[str]:
    """Execute the plan against the API. Returns list of action labels actually issued.

    WR-05 (Phase 3 code review): plan is typed ``list[PlannedAction[Any]]`` (mirror
    of Radarr's _execute at radarr.py:96) because the same function executes plans
    for DownloadClient, Indexer, Notification, and RootFolder. _execute only uses
    the BaseModel API (model_dump, .id) so the runtime contract is identical across
    types. Pre-fix the annotation was ``list[PlannedAction[DownloadClient]]`` and
    relied on covariance under type-erasure for the other resource types.
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
    force_prune: bool = False,   # NEW — passthrough to reconcile()
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
        force_prune=force_prune,   # NEW
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


def _reconcile_tags(
    client: SonarrClient,
    section: TagsSection,
    desired_tag_items: list[TagItem],
    dry_run: bool,
) -> list[Tag]:
    """Reconcile the operator-declared tags (e.g. tv, anime, family).

    ``desired_tag_items`` is the generator output (TagItem list from SonarrDerived.tags).
    The ``section`` parameter carries only ``prune`` — the items field was removed in
    Phase 12-B (D-01).

    Returns the post-reconcile tag list with IDs populated — downstream callers
    (label→id resolver, series_tags) consume this list instead of issuing a
    second GET /tag call (D-05-ORDER-01 efficiency).

    Uses _reconcile_list_resource (match_key="label") for the diff/execute loop.
    After the reconcile, re-fetches the tag list to capture server-assigned IDs
    for any newly POSTed tags (the POST response body carries the new id, but
    _reconcile_list_resource does not return individual response bodies).
    """
    raw_current = client.get(TAG_PATH)
    desired_tags = [Tag(label=item.label) for item in desired_tag_items]
    # Protect arrconf-managed from prune: it is not a Category-derived tag but
    # lives in the same /tag list that force_prune will sweep. Prepending it to
    # desired makes it match in by_name_desired and never reach the prune branch.
    if not any(t.label == MANAGED_TAG_LABEL for t in desired_tags):
        desired_tags = [Tag(label=MANAGED_TAG_LABEL)] + desired_tags
    _reconcile_list_resource(
        client,
        TAG_PATH,
        raw_current,
        Tag,
        desired_tags,
        match_key="label",
        prune=section.prune,
        managed_tag_id=None,
        dry_run=dry_run,
        force_prune=section.prune,   # NEW — D-04/D-05 legacy tag prune
    )
    # Re-fetch to get server-assigned IDs for any newly created tags.
    # In dry_run mode, no tags were actually created so the GET returns the
    # same list as before; callers must tolerate potentially-missing IDs.
    raw_after = client.get(TAG_PATH)
    return [Tag.model_validate(t) for t in raw_after]


# _resolve_download_client_tag_labels and _reconcile_remote_path_mappings are
# imported from arrconf.reconcilers._shared — shared byte-equivalent implementations
# used by both Sonarr and Radarr (PATTERNS line 391, Plan 06 extraction).


def _reconcile_series_tags(
    client: SonarrClient,
    section: SeriesTagsSection,
    all_tags: list[Tag],
    dry_run: bool,
) -> list[str]:
    """Retroactively tag untagged series with the default tag (D-05-MIG-01).

    Runs AFTER download_clients (D-05-ORDER-01) so series tag routing goes to
    already-configured download clients. Uses PUT /api/v3/series/editor with
    applyTags="add" so existing operator tags on series are NEVER removed (R-02).

    Pitfall 5: editor returns HTTP 202 Accepted — raise_for_status() accepts
    2xx already.

    Critical body invariants (T-05-CONTENT threat mitigation):
    - applyTags="add" (never "replace" or "remove")
    - moveFiles=False  (must NOT trigger file moves)
    - deleteFiles=False (must NOT delete files)
    """
    if not section.enable:
        log.info("series_tags_reconcile_skipped")
        return []

    raw_series = client.get(SERIES_PATH)
    untagged_ids = [s["id"] for s in raw_series if not s.get("tags")]
    if not untagged_ids:
        log.info("series_tags_no_op")
        return []

    # Resolve the default_tag label → id only when there is actual work to do.
    # Deferring until here avoids raising on misconfiguration when the cluster is
    # already fully tagged (idempotent runs in sync state stay error-free).
    default_tag = next((t for t in all_tags if t.label == section.default_tag), None)
    if default_tag is None or default_tag.id is None:
        raise ReconcileError(
            f"series_tags: default tag '{section.default_tag}' not found — "
            "ensure it is present in the categories config (D-05-ORDER-01)"
        )

    if dry_run:
        log.info("dry_run_skip", resource="series_tags", count=len(untagged_ids))
        return [f"series_tags:dry_run:{len(untagged_ids)}"]

    body = {
        "seriesIds": untagged_ids,
        "tags": [default_tag.id],
        "applyTags": "add",
        "moveFiles": False,
        "deleteFiles": False,
    }
    # Use _request directly — client.put() requires (path, id, json) signature with
    # a numeric id parameter, but the editor endpoint is PUT /series/editor (no id).
    client._request("PUT", SERIES_EDITOR_PATH, json=body)
    log.info("series_tags_applied", count=len(untagged_ids), tag_id=default_tag.id)
    return [f"series_tags:applied:{len(untagged_ids)}"]


def _reconcile_content_tags(
    client: SonarrClient,
    section: ContentRoutingSection,
    all_tags: list[Tag],
    dry_run: bool,
) -> list[str]:
    """Step 10 (Phase 6, D-06-RETAG-01). Genre-keyword-driven retagger.

    Runs AFTER series_tags (D-05-MIG-01) so the bulk-tagged baseline ('tv' tag)
    is already in place. content_tags then layers per-genre tags ('family', 'anime')
    on top.

    Matching algorithm:
      For each rule in section.rules:
        - resolve rule.tag label -> integer tag_id (via all_tags); fail loudly if missing
        - GET /series; filter to items whose genres[].lower() contains any
          rule.keywords[].lower() substring AND don't already have tag_id in tags[]
        - If non-empty: PUT /series/editor with seriesIds=matched, tags=[tag_id],
          applyTags='add' (T-05-CONTENT — never replace operator tags)

    Pitfall 5 (research): conservative keyword lists in Plan 06-06 chart YAML.
    NEVER add 'Animation' as a Sonarr family keyword — too broad, catches anime.

    Idempotent: items already carrying the rule's tag are filtered out before
    the editor PUT body is built. Second run = no_op (SC#5 mirror).

    Critical body invariants (T-05-CONTENT threat mitigation):
    - applyTags='add' (never 'replace' or 'remove')
    - moveFiles=False  (must NOT trigger file moves)
    - deleteFiles=False (must NOT delete files)
    """
    if not section.enable:
        log.info("content_tags_reconcile_skipped")
        return []

    if not section.rules:
        log.info("content_tags_no_rules")
        return []

    raw_series = client.get(SERIES_PATH)
    actions: list[str] = []

    for rule in section.rules:
        rule_tag = next((t for t in all_tags if t.label == rule.tag), None)
        if rule_tag is None or rule_tag.id is None:
            raise ReconcileError(
                f"content_tags: rule.tag '{rule.tag}' not found in reconciled tags — "
                "ensure it is present in the categories config (D-05-ORDER-01 mirror)"
            )

        keyword_lc = [kw.lower() for kw in rule.keywords]
        matching_ids: list[int] = []
        for s in raw_series:
            genres_lc = [g.lower() for g in s.get("genres", [])]
            # Case-insensitive substring intersection:
            if not any(kw in g for kw in keyword_lc for g in genres_lc):
                continue
            # Idempotent skip — already carries the tag:
            if rule_tag.id in s.get("tags", []):
                continue
            matching_ids.append(s["id"])

        if not matching_ids:
            log.info("content_tags_rule_no_op", rule_tag=rule.tag)
            continue

        if dry_run:
            log.info(
                "dry_run_skip", resource="content_tags", rule=rule.tag, count=len(matching_ids)
            )
            actions.append(f"content_tags:{rule.tag}:dry_run:{len(matching_ids)}")
            continue

        body = {
            "seriesIds": matching_ids,
            "tags": [rule_tag.id],
            "applyTags": "add",
            "moveFiles": False,
            "deleteFiles": False,
        }
        client._request("PUT", SERIES_EDITOR_PATH, json=body)
        log.info(
            "content_tags_applied",
            rule_tag=rule.tag,
            tag_id=rule_tag.id,
            count=len(matching_ids),
        )
        actions.append(f"content_tags:{rule.tag}:applied:{len(matching_ids)}")

    return actions


def reconcile_sonarr(
    client: SonarrClient,
    instance: SonarrInstance,
    derived: SonarrDerived,
    *,
    dry_run: bool,
) -> SonarrResult:
    """Reconcile a Sonarr instance (Phase 5 — D-05-SPLIT-01 full scope).

    Topological order (D-05-ORDER-01 — regression-tested in test_reconcile_order):
    managed-tag → tags → indexers → root_folders → remote_path_mappings →
    download_clients → notifications → host_config → series_tags → content_tags.

    step_begin log events carry step_index for ordering regression tests.

    ``derived`` carries the Categories-generator output (D-03, Phase 12-B).
    Items are passed directly to internal helpers — the Plan-A ``.items``
    attribute shim is removed (Phase 12-B D-01).
    """
    # Step 1: Ensure the arrconf-managed tag.
    log.info("step_begin", step="managed_tag", step_index=1)
    managed_tag = _ensure_managed_tag(client, dry_run)
    # WR-04 (Phase 3 code review): use the defensive sentinel CONSISTENTLY everywhere.
    # Pre-fix, the sentinel was only applied to _ensure_managed_tag_in_desired and
    # raw managed_tag.id was passed to reconcile() / _reconcile_list_resource(),
    # so the defensive fallback only protected one call site. Now both forms use
    # managed_tag_id (with sentinel fallback) — defense in depth across the file.
    managed_tag_id = managed_tag.id if managed_tag.id is not None else DRY_RUN_TAG_SENTINEL_ID
    actions_taken: list[str] = []

    # Step 2: Reconcile operator-declared tags (tv, anime, family).
    # MUST precede download_clients so IDs are available for label→id resolution.
    log.info("step_begin", step="tags", step_index=2)
    all_tags = _reconcile_tags(client, instance.tags, derived.tags, dry_run)

    # Step 3: Indexers (read-mostly alignment; created by Prowlarr sync).
    log.info("step_begin", step="indexers", step_index=3)
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

    # Step 4: Root folders (match by PATH — Pitfall 1; no managed tag).
    log.info("step_begin", step="root_folders", step_index=4)
    actions_taken += _reconcile_list_resource(
        client,
        ROOT_FOLDER_PATH,
        client.get(ROOT_FOLDER_PATH),
        RootFolder,
        derived.root_folders,
        match_key="path",
        prune=instance.root_folders.prune,
        managed_tag_id=None,
        dry_run=dry_run,
        force_prune=instance.root_folders.prune,   # NEW — D-04/D-05 legacy root prune
    )

    # Step 5: Remote path mappings (composite-key DELETE+ADD; D-05-PATHMAP-01).
    log.info("step_begin", step="remote_path_mappings", step_index=5)
    actions_taken += _reconcile_remote_path_mappings(
        client,
        derived.remote_path_mappings,
        prune=instance.remote_path_mappings.prune,
        dry_run=dry_run,
    )

    # Step 6: Download clients (original Phase 1 — managed-tag-stamped + label-resolved).
    # MUST run AFTER tags (step 2) so resolved IDs exist.
    log.info("step_begin", step="download_clients", step_index=6)
    raw_current = client.get(DOWNLOAD_CLIENT_PATH)
    current_dcs = [DownloadClient.model_validate(x) for x in raw_current]

    # Resolve string tag labels → integer IDs using the post-reconcile all_tags list.
    label_resolved = _resolve_download_client_tag_labels(derived.download_clients, all_tags)
    label_resolved = _resolve_qbit_credentials_from_env(label_resolved)
    desired_dcs = [_ensure_managed_tag_in_desired(dc, managed_tag_id) for dc in label_resolved]

    plan = reconcile(
        current=current_dcs,
        desired=desired_dcs,
        match_key="name",
        prune=instance.download_clients.prune,
        managed_tag_id=managed_tag_id,
        force_prune=instance.download_clients.prune,   # NEW — D-01 full prune of catch-all DC id=1
    )

    actions_taken += _execute(client, DOWNLOAD_CLIENT_PATH, plan, dry_run)

    # Step 7: Notifications.
    log.info("step_begin", step="notifications", step_index=7)
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

    # Step 8: host_config (D-03-04 opt-in; singleton).
    log.info("step_begin", step="host_config", step_index=8)
    _reconcile_host_config(client, instance.host_config, dry_run)

    # Step 9: Series tags — MUST run AFTER download_clients (D-05-ORDER-01).
    # Tagged series route to already-configured download clients.
    log.info("step_begin", step="series_tags", step_index=9)
    actions_taken += _reconcile_series_tags(client, instance.series_tags, all_tags, dry_run)

    # Step 10: Content tags — MUST run AFTER series_tags (D-05-ORDER-01 mirror).
    # Genre-keyword-driven post-import retagger (D-06-RETAG-01).
    log.info("step_begin", step="content_tags", step_index=10)
    actions_taken += _reconcile_content_tags(client, instance.content_routing, all_tags, dry_run)

    return SonarrResult(
        plan=plan,
        actions_taken=actions_taken,
        managed_tag_id=managed_tag_id,
    )
