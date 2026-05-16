"""Radarr reconciler — Phase 5 scope (D-05-SPLIT-02, D-05-PATHMAP-01, D-05-MIG-01).

Covers: download_clients + indexers + notifications + root_folders +
host_config (opt-in gated, D-03-04) + tags (movies/anime/family, D-05-SPLIT-02) +
remote_path_mappings (composite-key DELETE+ADD, D-05-PATHMAP-01) +
movie_tags (retroactive default-tag via bulk editor, D-05-MIG-01) +
content_tags (genre-keyword-driven post-import retagger, Phase 6, D-06-RETAG-01).

Topological order (D-05-ORDER-01 mirror — regression-tested in test_reconcile_order_radarr):

1. Ensure the ``arrconf-managed`` tag exists (D-02 / REQ-managed-tag).
2. Reconcile ``tags`` (movies, anime, family) — MUST precede download_clients
   so tag IDs exist for label→id resolution.
3. Reconcile ``indexers`` (list resource, match by ``name``).
4. Reconcile ``root_folders`` (list resource, match by ``path`` — Pitfall 1).
5. Reconcile ``remote_path_mappings`` (composite-key DELETE+ADD — no PUT endpoint;
   D-05-PATHMAP-01).
6. Reconcile ``download_clients`` with managed-tag protection
   (D-04 / D-09 / T-01-04) and label→id resolution for tags.
7. Reconcile ``notifications`` (list resource, match by ``name``).
8. Reconcile ``host_config`` (singleton, opt-in via section.enable — D-03-04).
9. Reconcile ``movie_tags`` — MUST run AFTER download_clients (D-05-ORDER-01)
   to ensure tagged movies route to already-configured download clients.
10. Reconcile ``content_tags`` — MUST run AFTER movie_tags (D-06-RETAG-01).
    Genre-keyword-driven post-import retagger layers per-genre tags on top of
    the bulk-tagged baseline.

Rationale for ordering mirrors Sonarr's (sonarr.py D-05-ORDER-01 docstring).
movie_tags last before content_tags — the bulk editor touches REAL movie
collection (D-05-MIG-01). content_tags layers on top (D-06-RETAG-01).

Critical schema divergence from Sonarr (RESEARCH lines 220–231):
- PUT /movie/editor uses ``movieIds`` (NOT ``seriesIds``)
- PUT /movie/editor uses ``addImportExclusion`` (NOT ``addImportListExclusion``)
Both divergences are regression-tested in test_movie_editor.py.

Implementation note: This file intentionally mirrors the Sonarr reconciler
verbatim with the appropriate client and movie-specific names substituted.
Shared helpers (_reconcile_remote_path_mappings, _resolve_download_client_tag_labels)
are imported from arrconf.reconcilers._shared (Plan 06 extraction — byte-equivalent).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog
from pydantic import BaseModel

from arrconf.client_base import RadarrClient
from arrconf.config import (
    ContentRoutingSection,
    HostConfigSection,
    MovieTagsSection,
    RadarrInstance,
    TagsSection,
)
from arrconf.differ import (
    Action,
    PlannedAction,
    diff_models,
    merge_fields_for_put,
    reconcile,
)
from arrconf.exceptions import ReconcileError
from arrconf.reconcilers._shared import (
    _reconcile_remote_path_mappings,
    _resolve_download_client_tag_labels,
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
TAG_PATH = "/tag"
DOWNLOAD_CLIENT_PATH = "/downloadclient"
INDEXER_PATH = "/indexer"
NOTIFICATION_PATH = "/notification"
ROOT_FOLDER_PATH = "/rootfolder"
HOST_CONFIG_PATH = "/config/host"
MOVIE_PATH = "/movie"
MOVIE_EDITOR_PATH = "/movie/editor"


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


def _reconcile_tags(
    client: RadarrClient,
    section: TagsSection,
    dry_run: bool,
) -> list[Tag]:
    """Reconcile the operator-declared tags (e.g. movies, anime, family).

    Mirror of sonarr._reconcile_tags. Returns the post-reconcile tag list with
    IDs populated — downstream callers (label→id resolver, movie_tags) consume
    this list instead of issuing a second GET /tag call (D-05-ORDER-01 efficiency).

    Uses _reconcile_list_resource (match_key="label") for the diff/execute loop.
    After the reconcile, re-fetches the tag list to capture server-assigned IDs
    for any newly POSTed tags (the POST response body carries the new id, but
    _reconcile_list_resource does not return individual response bodies).
    """
    raw_current = client.get(TAG_PATH)
    desired_tags = [Tag(label=item.label) for item in section.items]
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
    )
    # Re-fetch to get server-assigned IDs for any newly created tags.
    # In dry_run mode, no tags were actually created so the GET returns the
    # same list as before; callers must tolerate potentially-missing IDs.
    raw_after = client.get(TAG_PATH)
    return [Tag.model_validate(t) for t in raw_after]


def _reconcile_movie_tags(
    client: RadarrClient,
    section: MovieTagsSection,
    all_tags: list[Tag],
    dry_run: bool,
) -> list[str]:
    """Retroactively tag untagged movies with the default tag (D-05-MIG-01 Radarr mirror).

    Runs AFTER download_clients (D-05-ORDER-01) so movie tag routing goes to
    already-configured download clients. Uses PUT /api/v3/movie/editor with
    applyTags="add" so existing operator tags on movies are NEVER removed (R-02).

    Pitfall 5: editor returns HTTP 202 Accepted — raise_for_status() accepts
    2xx already.

    Critical body invariants (T-05-CONTENT threat mitigation):
    - applyTags="add" (never "replace" or "remove")
    - moveFiles=False  (must NOT trigger file moves)
    - deleteFiles=False (must NOT delete files)

    Radarr schema divergence from Sonarr (RESEARCH lines 220–231):
    - Body field ``movieIds`` (NOT ``seriesIds`` — field name differs)
    - Body field ``addImportExclusion: False`` (NOT ``addImportListExclusion`` —
      Radarr's MovieEditorResource.cs uses the singular form without "List")

    Default tag is ``"movies"`` per D-05-SPLIT-02 (Radarr convention: matches
    the qBittorrent category name ``radarr-movies``).
    """
    if not section.enable:
        log.info("movie_tags_reconcile_skipped")
        return []

    raw_movies = client.get(MOVIE_PATH)
    untagged_ids = [m["id"] for m in raw_movies if not m.get("tags")]
    if not untagged_ids:
        log.info("movie_tags_no_op")
        return []

    # Resolve the default_tag label → id only when there is actual work to do.
    # Deferring until here avoids raising on misconfiguration when the cluster is
    # already fully tagged (idempotent runs in sync state stay error-free).
    default_tag = next((t for t in all_tags if t.label == section.default_tag), None)
    if default_tag is None or default_tag.id is None:
        raise ReconcileError(
            f"movie_tags: default tag '{section.default_tag}' not found — "
            "declare it in instance.tags.items so it is reconciled first (D-05-ORDER-01)"
        )

    if dry_run:
        log.info("dry_run_skip", resource="movie_tags", count=len(untagged_ids))
        return [f"movie_tags:dry_run:{len(untagged_ids)}"]

    body = {
        "movieIds": untagged_ids,
        "tags": [default_tag.id],
        "applyTags": "add",
        "moveFiles": False,
        "deleteFiles": False,
        "addImportExclusion": False,
    }
    # Use _request directly — client.put() requires (path, id, json) signature with
    # a numeric id parameter, but the editor endpoint is PUT /movie/editor (no id).
    client._request("PUT", MOVIE_EDITOR_PATH, json=body)
    log.info("movie_tags_applied", count=len(untagged_ids), tag_id=default_tag.id)
    return [f"movie_tags:applied:{len(untagged_ids)}"]


def _reconcile_content_tags(
    client: RadarrClient,
    section: ContentRoutingSection,
    all_tags: list[Tag],
    dry_run: bool,
) -> list[str]:
    """Step 10 mirror for Radarr (Phase 6, D-06-RETAG-01).

    Runs AFTER movie_tags (D-05-MIG-01) so the bulk-tagged baseline ('movies' tag)
    is already in place. content_tags then layers per-genre tags ('family')
    on top.

    Radarr-specific schema divergence from Sonarr:
    - Body field ``movieIds`` (NOT ``seriesIds``)
    - Body field ``addImportExclusion: False`` (NOT ``addImportListExclusion`` —
      Radarr's MovieEditorResource.cs uses the singular form, matches Phase 5
      _reconcile_movie_tags pattern)

    Plan 06-06 chart YAML configures Radarr with ``family`` rule ONLY — NO ``anime``
    rule (Pitfall 5: TMDB has no 'Anime' genre; 'Animation' would catch
    Pixar/Disney). This reconciler code is generic (it would handle an anime
    rule if one were declared), but the operator is expected NOT to declare one.

    Matching algorithm:
      For each rule in section.rules:
        - resolve rule.tag label -> integer tag_id (via all_tags); fail loudly if missing
        - GET /movie; filter to items whose genres[].lower() contains any
          rule.keywords[].lower() substring AND don't already have tag_id in tags[]
        - If non-empty: PUT /movie/editor with movieIds=matched, tags=[tag_id],
          applyTags='add' (T-05-CONTENT — never replace operator tags)

    Idempotent: items already carrying the rule's tag are filtered out before
    the editor PUT body is built. Second run = no_op (SC#5 mirror).

    Critical body invariants (T-05-CONTENT threat mitigation):
    - applyTags='add' (never 'replace' or 'remove')
    - moveFiles=False  (must NOT trigger file moves)
    - deleteFiles=False (must NOT delete files)
    - addImportExclusion=False (Radarr-specific — singular form, not 'addImportListExclusion')
    """
    if not section.enable:
        log.info("content_tags_reconcile_skipped")
        return []

    if not section.rules:
        log.info("content_tags_no_rules")
        return []

    raw_movies = client.get(MOVIE_PATH)
    actions: list[str] = []

    for rule in section.rules:
        rule_tag = next((t for t in all_tags if t.label == rule.tag), None)
        if rule_tag is None or rule_tag.id is None:
            raise ReconcileError(
                f"content_tags: rule.tag '{rule.tag}' not found in instance.tags.items — "
                "declare it so it is reconciled first (D-05-ORDER-01 mirror)"
            )

        keyword_lc = [kw.lower() for kw in rule.keywords]
        matching_ids: list[int] = []
        for m in raw_movies:
            genres_lc = [g.lower() for g in m.get("genres", [])]
            # Case-insensitive substring intersection:
            if not any(kw in g for kw in keyword_lc for g in genres_lc):
                continue
            # Idempotent skip — already carries the tag:
            if rule_tag.id in m.get("tags", []):
                continue
            matching_ids.append(m["id"])

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
            "movieIds": matching_ids,
            "tags": [rule_tag.id],
            "applyTags": "add",
            "moveFiles": False,
            "deleteFiles": False,
            "addImportExclusion": False,
        }
        client._request("PUT", MOVIE_EDITOR_PATH, json=body)
        log.info(
            "content_tags_applied",
            rule_tag=rule.tag,
            tag_id=rule_tag.id,
            count=len(matching_ids),
        )
        actions.append(f"content_tags:{rule.tag}:applied:{len(matching_ids)}")

    return actions


def reconcile_radarr(
    client: RadarrClient,
    instance: RadarrInstance,
    dry_run: bool,
) -> RadarrResult:
    """Reconcile a Radarr instance (Phase 5 — D-05-SPLIT-02 full scope).

    Topological order (D-05-ORDER-01 mirror — regression-tested in test_reconcile_order_radarr):
    managed-tag → tags → indexers → root_folders → remote_path_mappings →
    download_clients → notifications → host_config → movie_tags → content_tags.

    step_begin log events carry step_index for ordering regression tests.
    """
    # Step 1: Ensure the arrconf-managed tag.
    log.info("step_begin", step="managed_tag", step_index=1)
    managed_tag = _ensure_managed_tag(client, dry_run)
    # WR-04 (Phase 3 code review): use the defensive sentinel CONSISTENTLY everywhere.
    # Pre-fix, the sentinel was only applied to _ensure_managed_tag_in_desired and
    # raw managed_tag.id was passed to reconcile() / _reconcile_list_resource(),
    # so the defensive fallback only protected one call site. Mirror of Sonarr fix.
    managed_tag_id = managed_tag.id if managed_tag.id is not None else DRY_RUN_TAG_SENTINEL_ID
    actions_taken: list[str] = []

    # Step 2: Reconcile operator-declared tags (movies, anime, family).
    # MUST precede download_clients so IDs are available for label→id resolution.
    log.info("step_begin", step="tags", step_index=2)
    all_tags = _reconcile_tags(client, instance.tags, dry_run)

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
        instance.root_folders.items,
        match_key="path",
        prune=instance.root_folders.prune,
        managed_tag_id=None,
        dry_run=dry_run,
    )

    # Step 5: Remote path mappings (composite-key DELETE+ADD; D-05-PATHMAP-01).
    log.info("step_begin", step="remote_path_mappings", step_index=5)
    actions_taken += _reconcile_remote_path_mappings(
        client,
        instance.remote_path_mappings.items,
        prune=instance.remote_path_mappings.prune,
        dry_run=dry_run,
    )

    # Step 6: Download clients (original Phase 1 — managed-tag-stamped + label-resolved).
    # MUST run AFTER tags (step 2) so resolved IDs exist.
    log.info("step_begin", step="download_clients", step_index=6)
    raw_current = client.get(DOWNLOAD_CLIENT_PATH)
    current_dcs = [DownloadClient.model_validate(x) for x in raw_current]

    # Resolve string tag labels → integer IDs using the post-reconcile all_tags list.
    label_resolved = _resolve_download_client_tag_labels(
        instance.download_clients.items, all_tags, app_name="Radarr"
    )
    desired_dcs = [_ensure_managed_tag_in_desired(dc, managed_tag_id) for dc in label_resolved]

    dc_plan = reconcile(
        current=current_dcs,
        desired=desired_dcs,
        match_key="name",
        prune=instance.download_clients.prune,
        managed_tag_id=managed_tag_id,
    )
    actions_taken += _execute(client, DOWNLOAD_CLIENT_PATH, dc_plan, dry_run)

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

    # Step 9: Movie tags — MUST run AFTER download_clients (D-05-ORDER-01).
    # Tagged movies route to already-configured download clients.
    log.info("step_begin", step="movie_tags", step_index=9)
    actions_taken += _reconcile_movie_tags(client, instance.movie_tags, all_tags, dry_run)

    # Step 10: Content tags — MUST run AFTER movie_tags (D-05-ORDER-01 mirror).
    # Genre-keyword-driven post-import retagger (D-06-RETAG-01).
    log.info("step_begin", step="content_tags", step_index=10)
    actions_taken += _reconcile_content_tags(client, instance.content_routing, all_tags, dry_run)

    return RadarrResult(
        plan=dc_plan,
        actions_taken=actions_taken,
        managed_tag_id=managed_tag_id,
    )
