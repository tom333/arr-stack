"""Per-category quality-profile assignment (frontier-safe).

Assigns each movie/series the configarr quality profile mapped to its category's
``profile`` keyword. Resolution is read-only (GET /qualityprofile); only /movie and
/series item resources are written (PUT editor). NO quality-profile DEFINITION is
written -- ADR-5 / ScopeViolationError boundary is respected by construction.

Policy: only items currently on a NON-managed (stock) profile are reassigned, so a
deliberate manual choice among the managed profiles (MULTi.VF/Anime/Family) is kept.
"""

from __future__ import annotations

import structlog

from arrconf.client_base import ArrApiClient
from arrconf.exceptions import ConfigError
from arrconf.resources.categories import Category

log = structlog.get_logger()

QUALITY_PROFILE_PATH = "/qualityprofile"


def _match_target(path: str, base_to_target: dict[str, int]) -> int | None:
    """Longest matching base_path prefix wins (handles nested category dirs)."""
    best: tuple[int, int] | None = None  # (prefix_len, target)
    for base, tid in base_to_target.items():
        if path == base or path.startswith(base + "/"):
            if best is None or len(base) > best[0]:
                best = (len(base), tid)
    return None if best is None else best[1]


def reconcile_category_profiles(
    client: ArrApiClient,
    categories: list[Category],
    category_quality_profiles: dict[str, str],
    *,
    item_path: str,
    editor_path: str,
    ids_key: str,
    dry_run: bool,
) -> list[str]:
    """Assign each item the QP of its category. Returns human-readable action strings.

    item_path: "/movie" (Radarr) or "/series" (Sonarr)
    editor_path: "/movie/editor" or "/series/editor"
    ids_key: "movieIds" or "seriesIds"
    """
    if not categories:
        return []

    # Read-only name->id resolution (ADR-5 safe).
    qp_by_name: dict[str, int] = {qp["name"]: qp["id"] for qp in client.get(QUALITY_PROFILE_PATH)}

    # base_path -> target profile id, plus the set of managed ids.
    base_to_target: dict[str, int] = {}
    managed_ids: set[int] = set()
    for cat in categories:
        name = category_quality_profiles.get(cat.profile)
        if name is None:
            continue  # category profile keyword not mapped -> leave its items alone
        if name not in qp_by_name:
            raise ConfigError(
                f"quality profile '{name}' (for category profile '{cat.profile}') not found"
            )
        tid = qp_by_name[name]
        base_to_target[cat.base_path.rstrip("/")] = tid
        managed_ids.add(tid)

    items = client.get(item_path)

    # Group ids needing reassignment by target profile id.
    groups: dict[int, list[int]] = {}
    actions: list[str] = []
    for it in items:
        path = it.get("path") or it.get("rootFolderPath") or ""
        target = _match_target(path, base_to_target)
        if target is None:
            continue  # not under a known category
        current = it.get("qualityProfileId")
        if current in managed_ids:
            continue  # already on a managed profile -> respect manual choice
        if current == target:
            continue  # no-op
        groups.setdefault(target, []).append(it["id"])

    for tid, ids in groups.items():
        actions.append(f"set qualityProfileId={tid} on {len(ids)} item(s)")
        if not dry_run:
            # Editor endpoint takes no id (body carries movieIds/seriesIds); client.put()
            # requires a numeric id, so use _request directly (mirrors _reconcile_movie_tags).
            client._request("PUT", editor_path, json={ids_key: ids, "qualityProfileId": tid})
            log.info("category_profile_assigned", profile_id=tid, count=len(ids))

    return actions
