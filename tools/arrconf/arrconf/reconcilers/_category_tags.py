"""Per-category title tagging — deterministic download-client routing.

Assigns each Sonarr/Radarr item EXACTLY its Category tag (the tag whose label
equals ``cat.name``), resolved by the longest matching ``base_path`` prefix
against the item's root folder. Read-only tag resolution (GET /tag); only
/series and /movie item resources are written (PUT editor). Frontier-safe: no
quality-profile/custom-format DEFINITION is ever touched.

Decision D-1 (applyTags="replace"): the editor write REPLACES all tags with exactly
``[category_tag_id]``. This is deliberate — a title then shares a routing tag
only with its own Category's download client, so routing is deterministic.
Consequence: any other tag on the item is stripped, including the Seerr
``1-moi`` user tag, ``arrconf-managed``, legacy ``tv``/``anime``/``family``, and
manual operator tags. Accepted: routing correctness outweighs preserving
incidental tags. If an operator tag must survive, switch to a
compute-desired-then-add/remove diff instead of "set".
"""

from __future__ import annotations

import structlog

from arrconf.client_base import ArrApiClient
from arrconf.exceptions import ConfigError
from arrconf.resources.categories import Category

log = structlog.get_logger()

TAG_PATH = "/tag"


def _match_target(path: str, base_to_target: dict[str, int]) -> int | None:
    """Longest matching base_path prefix wins (handles nested category dirs)."""
    best: tuple[int, int] | None = None  # (prefix_len, target)
    for base, tid in base_to_target.items():
        if path == base or path.startswith(base + "/"):
            if best is None or len(base) > best[0]:
                best = (len(base), tid)
    return None if best is None else best[1]


def reconcile_category_tags(
    client: ArrApiClient,
    categories: list[Category],
    *,
    item_path: str,
    editor_path: str,
    ids_key: str,
    dry_run: bool,
) -> list[str]:
    """Set each item's tags to exactly its category tag. Returns action strings.

    item_path: "/movie" (Radarr) or "/series" (Sonarr)
    editor_path: "/movie/editor" or "/series/editor"
    ids_key: "movieIds" or "seriesIds"
    """
    if not categories:
        return []

    # Read-only label->id resolution. Tags are created by the earlier tags
    # reconcile step; here we assume present and fail loudly if not.
    tag_by_label: dict[str, int] = {t["label"]: t["id"] for t in client.get(TAG_PATH)}

    base_to_tag: dict[str, int] = {}
    for cat in categories:
        if cat.name not in tag_by_label:
            raise ConfigError(f"category tag '{cat.name}' not found in /tag (create it first)")
        base_to_tag[cat.base_path.rstrip("/")] = tag_by_label[cat.name]

    items = client.get(item_path)

    # Group ids needing a retag by target category tag id.
    groups: dict[int, list[int]] = {}
    actions: list[str] = []
    for it in items:
        path = it.get("path") or it.get("rootFolderPath") or ""
        target = _match_target(path, base_to_tag)
        if target is None:
            continue  # not under a known category
        if set(it.get("tags", [])) == {target}:
            continue  # already carries exactly its category tag -> no-op
        groups.setdefault(target, []).append(it["id"])

    for tag_id, ids in groups.items():
        actions.append(f"set tag={tag_id} on {len(ids)} item(s)")
        if not dry_run:
            client._request(
                "PUT",
                editor_path,
                json={ids_key: ids, "tags": [tag_id], "applyTags": "replace"},
            )
            log.info("category_tag_assigned", tag_id=tag_id, count=len(ids))

    return actions
