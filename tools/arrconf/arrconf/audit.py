"""Phase 20 — Read-only audit of v0.2.0 legacy state across the arrconf stack.

Produces .planning/phases/20-categories-cleanup-audit/20-AUDIT.md: a Markdown
narrative + fenced YAML appendix that Phase 21 consumes mechanically. The module
issues only client.get(...) calls — NEVER post/put/delete/post_form. Re-runnable;
read-only. See 20-RESEARCH.md §Pattern 5 for the output schema and Pattern 6
for the verify gate.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import structlog
from ruyaml import YAML

from arrconf.client_base import (
    JellyfinClient,
    QbittorrentClient,
    RadarrClient,
    SeerrClient,
    SonarrClient,
)
from arrconf.config import RootConfig
from arrconf.settings import Settings

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Canonical sets — v0.2.0 legacy detection constants
# ---------------------------------------------------------------------------

LEGACY_PATHS_HARD: Final[frozenset[str]] = frozenset(
    {
        "/media/anime",  # → /media/series-zoe (auto-map per CLAUDE.md)
        "/media/family",  # → /media/series-garcons (auto-map per CLAUDE.md)
        "/media/films-anime",  # → split: operator-decision (Ghibli vs Disney/Pixar)
        "/media/films-family",  # → /media/films-enfants (auto-map per CLAUDE.md)
    }
)

AMBIGUOUS_PATHS: Final[frozenset[str]] = frozenset(
    {
        "/media/series",  # Category default — may need selective split
        "/media/films",  # Category default — may need selective split
    }
)

LEGACY_TAGS_HARD: Final[frozenset[str]] = frozenset(
    {
        "anime",  # → series-zoe (series side) or operator (movie side)
        "family",  # → series-garcons (series) OR films-enfants (movies)
        "films",  # legacy default tag, no Category equivalent
        "movies",  # legacy default tag, no Category equivalent
    }
)

# Auto-mapping dicts (CLAUDE.md §"Filesystem migration v0.2.0 → v0.3.0" verbatim)
AUTO_PATH_MAPPING: Final[dict[str, str]] = {
    "/media/anime": "/media/series-zoe",
    "/media/family": "/media/series-garcons",
    "/media/films-family": "/media/films-enfants",
}

# Tag mapping is split per kind — Sonarr `family` → series-garcons, Radarr `family` → films-enfants
# (RESEARCH.md Pitfall 2)
AUTO_TAG_MAPPING_SERIES: Final[dict[str, str]] = {
    "anime": "series-zoe",
    "family": "series-garcons",
}
AUTO_TAG_MAPPING_MOVIES: Final[dict[str, str]] = {
    "family": "films-enfants",
    # "anime" on Radarr is operator-decision (Ghibli vs Disney — not auto-mappable)
}

OPERATOR_DECISION_PATHS: Final[frozenset[str]] = frozenset(
    {
        "/media/films-anime",  # split: Ghibli → films-zoe; Disney/Pixar → films-animation-enfants
        "/media/series",  # default OR selective split to series-emilie/thomas/garcons/zoe
        "/media/films",  # default OR selective split to nouveaux-films
    }
)

# Legacy qBit save_path prefixes (RESEARCH.md Pitfall 1 — qBit-side paths)
LEGACY_QBIT_SAVE_PATHS: Final[frozenset[str]] = frozenset(
    {
        "/data/anime",
        "/data/family",
        "/data/films-anime",
        "/data/films-family",
        "/data/complete",  # legacy pre-Categories catch-all
    }
)

# Secret field names that must NEVER appear in audit output
_SECRET_FIELD_NAMES: Final[frozenset[str]] = frozenset(
    {"apiKey", "password", "token", "webhookUrl", "sessionKey"}
)


# ---------------------------------------------------------------------------
# Pure-function predicates — testable in isolation
# ---------------------------------------------------------------------------


def _norm_path(p: str) -> str:
    """Strip trailing slash for consistent comparison (RESEARCH.md Pitfall 7)."""
    return (p or "").rstrip("/")


def is_legacy_path(p: str, category_paths: set[str]) -> bool:
    """Return True if the path is v0.2.0 legacy (not a known Category path).

    A path is legacy if it is in LEGACY_PATHS_HARD OR it is not a known
    Category base_path. AMBIGUOUS_PATHS (series, films) are considered as
    potential-legacy (operator must decide per item).
    """
    n = _norm_path(p)
    if n in LEGACY_PATHS_HARD:
        return True
    return n not in category_paths


def is_ambiguous_path(p: str) -> bool:
    """Return True if the path requires operator-decision mapping."""
    return _norm_path(p) in OPERATOR_DECISION_PATHS


def is_legacy_tag(label: str) -> bool:
    """Return True if the tag label is a v0.2.0 legacy tag."""
    return label in LEGACY_TAGS_HARD


# ---------------------------------------------------------------------------
# Per-app audit functions (each issues only GETs, returns YAML-shape dict)
# ---------------------------------------------------------------------------


def audit_radarr(client: RadarrClient, root: RootConfig) -> dict[str, Any]:
    """Audit Radarr movies + tags + DCs. Returns the per-app YAML dict shape.

    Issues only GET requests — never mutates cluster state.
    """
    movies: list[dict[str, Any]] = client.get("/movie")
    tags: list[dict[str, Any]] = client.get("/tag")
    dcs: list[dict[str, Any]] = client.get("/downloadclient")

    tag_id_to_label: dict[int, str] = {t["id"]: t["label"] for t in tags}
    category_paths = {c.base_path for c in root.categories}

    legacy_movie_rows: list[dict[str, Any]] = []
    for m in movies:
        rfp = _norm_path(m.get("rootFolderPath", ""))
        # Skip movies already on a Category path that is not an operator-decision path
        if rfp in category_paths and rfp not in OPERATOR_DECISION_PATHS:
            continue
        auto_target = AUTO_PATH_MAPPING.get(rfp)
        current_tag_ids: list[int] = m.get("tags", [])
        legacy_movie_rows.append(
            {
                "id": m["id"],
                "title": m["title"],
                "current_rootFolder": rfp,
                "current_path": m.get("path", ""),
                "current_tags": current_tag_ids,
                "current_tag_labels": [
                    tag_id_to_label.get(t, f"<unknown:{t}>") for t in current_tag_ids
                ],
                "genres": m.get("genres", []),
                "is_legacy": rfp in LEGACY_PATHS_HARD,
                "auto_target_rootFolder": auto_target,  # None → operator decision
            }
        )

    legacy_tag_rows: list[dict[str, Any]] = [
        {
            "id": t["id"],
            "label": t["label"],
            "proposed_action": "prune" if is_legacy_tag(t["label"]) else "keep",
            "target_label": AUTO_TAG_MAPPING_MOVIES.get(t["label"]),
        }
        for t in tags
    ]

    dc_rows: list[dict[str, Any]] = [
        {
            "id": dc["id"],
            "name": dc["name"],
            "tags": dc.get("tags", []),
            "tag_labels": [tag_id_to_label.get(t, f"<unknown:{t}>") for t in dc.get("tags", [])],
            "priority": dc.get("priority"),
            "proposed_action": "PENDING_PHASE_22",
        }
        for dc in dcs
    ]

    log.info(
        "audit_radarr_complete",
        legacy_movies=len(legacy_movie_rows),
        tags_total=len(legacy_tag_rows),
        dcs_total=len(dc_rows),
    )

    return {
        "movies_to_migrate": legacy_movie_rows,
        "tags": legacy_tag_rows,
        "download_clients": dc_rows,
    }


def audit_sonarr(client: SonarrClient, root: RootConfig) -> dict[str, Any]:
    """Audit Sonarr series + tags + DCs. Returns the per-app YAML dict shape.

    Issues only GET requests — never mutates cluster state.
    """
    series: list[dict[str, Any]] = client.get("/series")
    tags: list[dict[str, Any]] = client.get("/tag")
    dcs: list[dict[str, Any]] = client.get("/downloadclient")

    tag_id_to_label: dict[int, str] = {t["id"]: t["label"] for t in tags}
    category_paths = {c.base_path for c in root.categories}

    legacy_series_rows: list[dict[str, Any]] = []
    for s in series:
        rfp = _norm_path(s.get("rootFolderPath", ""))
        # Skip series already on a Category path that is not an operator-decision path
        if rfp in category_paths and rfp not in OPERATOR_DECISION_PATHS:
            continue
        auto_target = AUTO_PATH_MAPPING.get(rfp)
        current_tag_ids: list[int] = s.get("tags", [])
        legacy_series_rows.append(
            {
                "id": s["id"],
                "title": s["title"],
                "current_rootFolder": rfp,
                "current_path": s.get("path", ""),
                "current_tags": current_tag_ids,
                "current_tag_labels": [
                    tag_id_to_label.get(t, f"<unknown:{t}>") for t in current_tag_ids
                ],
                "genres": s.get("genres", []),
                "is_legacy": rfp in LEGACY_PATHS_HARD,
                "auto_target_rootFolder": auto_target,  # None → operator decision
            }
        )

    legacy_tag_rows: list[dict[str, Any]] = [
        {
            "id": t["id"],
            "label": t["label"],
            "proposed_action": "prune" if is_legacy_tag(t["label"]) else "keep",
            "target_label": AUTO_TAG_MAPPING_SERIES.get(t["label"]),
        }
        for t in tags
    ]

    dc_rows: list[dict[str, Any]] = [
        {
            "id": dc["id"],
            "name": dc["name"],
            "tags": dc.get("tags", []),
            "tag_labels": [tag_id_to_label.get(t, f"<unknown:{t}>") for t in dc.get("tags", [])],
            "priority": dc.get("priority"),
            "proposed_action": "PENDING_PHASE_22",
        }
        for dc in dcs
    ]

    log.info(
        "audit_sonarr_complete",
        legacy_series=len(legacy_series_rows),
        tags_total=len(legacy_tag_rows),
        dcs_total=len(dc_rows),
    )

    return {
        "series_to_migrate": legacy_series_rows,
        "tags": legacy_tag_rows,
        "download_clients": dc_rows,
    }


def audit_qbittorrent(client: QbittorrentClient, root: RootConfig) -> dict[str, Any]:
    """Audit qBit torrents save_paths and categories alignment. Read-only.

    Issues only GET requests — never mutates cluster state.
    """
    torrents: list[dict[str, Any]] = client.get("/torrents/info")
    raw_cats: dict[str, Any] = client.get("/torrents/categories")

    # Valid qBit-side save paths (qBit sees /data/<name>, not /data/torrents/<name> — Pitfall 1)
    valid_qbit_save_paths = {f"/data/{c.name}" for c in root.categories}

    legacy_torrents: list[dict[str, Any]] = []
    for t in torrents:
        sp = _norm_path(t.get("save_path", ""))
        if sp in valid_qbit_save_paths:
            continue
        # Legacy: derive auto target from category mapping if possible
        # Map /data/X → /data/Y by checking if /media/X is in AUTO_PATH_MAPPING
        media_path = f"/media/{sp[len('/data/') :]}" if sp.startswith("/data/") else None
        target_media = AUTO_PATH_MAPPING.get(media_path or "") if media_path else None
        auto_target_save_path = f"/data/{target_media[len('/media/') :]}" if target_media else None
        name_raw = str(t.get("name", ""))
        legacy_torrents.append(
            {
                "hash": t.get("hash", ""),
                "name": name_raw[:80],  # truncate for Markdown row safety
                "category": t.get("category", ""),
                "save_path": sp,
                "state": t.get("state", ""),
                "auto_target_save_path": auto_target_save_path,
            }
        )

    # Categories sanity check (post-debug-session expectation: all aligned)
    categories_validation: str | dict[str, Any] = "OK"
    drift: list[dict[str, Any]] = []
    category_names = {c.name for c in root.categories}
    for cat_name, obj in raw_cats.items():
        if cat_name not in category_names:
            continue  # not a managed category — skip
        expected = f"/data/torrents/{cat_name}"
        actual = _norm_path(obj.get("savePath", "") if isinstance(obj, dict) else "")
        if actual != expected:
            drift.append(
                {
                    "name": cat_name,
                    "current_savePath": actual,
                    "expected_savePath": expected,
                }
            )
    if drift:
        categories_validation = {"status": "DRIFT", "drift": drift}

    log.info(
        "audit_qbittorrent_complete",
        legacy_torrents=len(legacy_torrents),
        categories_drift=len(drift),
    )

    return {
        "torrents_to_relocate": legacy_torrents,
        "categories_validation": categories_validation,
    }


def audit_seerr(seerr: SeerrClient, sonarr: SonarrClient, root: RootConfig) -> dict[str, Any]:
    """Audit Seerr animeTags routing. Read-only.

    Requires Sonarr GET /tag to resolve animeTags IDs → labels (RESEARCH.md Pitfall 3).
    Issues only GET requests — never mutates cluster state.
    """
    sonarr_services: list[dict[str, Any]] = seerr.get("/settings/sonarr")
    sonarr_tags: list[dict[str, Any]] = sonarr.get("/tag")

    tag_id_to_label: dict[int, str] = {t["id"]: t["label"] for t in sonarr_tags}

    # Anime-profile series Category names → target animetag candidates
    anime_series_names = {
        c.name for c in root.categories if c.profile == "anime" and c.kind == "series"
    }
    label_to_id: dict[str, int] = {t["label"]: t["id"] for t in sonarr_tags}
    proposed_anime_ids: list[int] = [
        label_to_id[name] for name in anime_series_names if name in label_to_id
    ]

    services_audit: list[dict[str, Any]] = []
    for svc in sonarr_services:
        anime_tag_ids: list[int] = svc.get("animeTags", []) or []
        resolved_labels = [tag_id_to_label.get(tid, f"<unknown:{tid}>") for tid in anime_tag_ids]
        has_legacy = any(is_legacy_tag(label) for label in resolved_labels)
        services_audit.append(
            {
                "service_name": svc.get("name", ""),
                "is_default": svc.get("isDefault", False),
                "animetags_ids": anime_tag_ids,
                "animetags_labels": resolved_labels,
                "animetags_legacy": has_legacy,
                "animetags_proposed_ids": proposed_anime_ids,
            }
        )

    any_legacy = any(s["animetags_legacy"] for s in services_audit)

    log.info(
        "audit_seerr_complete",
        services=len(services_audit),
        animetags_legacy=any_legacy,
    )

    return {
        "services": services_audit,
        "animetags_legacy": any_legacy,
        "animetags_proposed_ids": proposed_anime_ids,
    }


def audit_jellyfin(client: JellyfinClient, root: RootConfig) -> dict[str, Any]:
    """Audit Jellyfin library alignment with Category base_paths. Read-only.

    Issues only GET requests — never mutates cluster state.
    """
    libs: list[dict[str, Any]] = client.get("/Library/VirtualFolders")

    category_paths = {c.base_path for c in root.categories}
    # Also accept paths with trailing slash (Pitfall 7)
    category_paths_norm = {_norm_path(p) for p in category_paths}

    drift: list[dict[str, Any]] = []
    libs_audit: list[dict[str, Any]] = []

    for lib in libs:
        path_infos = (lib.get("LibraryOptions") or {}).get("PathInfos") or []
        lib_paths = [_norm_path(p.get("Path", "")) for p in path_infos if p.get("Path")]
        aligned = all(p in category_paths_norm for p in lib_paths)
        libs_audit.append(
            {
                "name": lib.get("Name", ""),
                "collection_type": lib.get("CollectionType", ""),
                "paths": lib_paths,
                "aligned": aligned,
            }
        )
        if not aligned:
            for lp in lib_paths:
                if lp not in category_paths_norm:
                    drift.append(
                        {
                            "library": lib.get("Name", ""),
                            "path": lp,
                            "expected": "one of " + str(sorted(category_paths_norm)),
                        }
                    )

    libraries_alignment: str | dict[str, Any] = "OK" if not drift else {"drift": drift}

    log.info(
        "audit_jellyfin_complete",
        libs_total=len(libs_audit),
        drift_count=len(drift),
    )

    return {
        "libraries": libs_audit,
        "libraries_alignment": libraries_alignment,
    }


# ---------------------------------------------------------------------------
# Markdown rendering helpers
# ---------------------------------------------------------------------------


def _render_table(headers: list[str], rows: list[list[Any]]) -> str:
    """Emit a GFM table. Escape pipes and newlines in cell content (RESEARCH.md §Security)."""

    def cell(c: Any) -> str:
        s = str(c) if c is not None else ""
        return s.replace("|", "\\|").replace("\n", " ")

    sep = "|" + "|".join(["---"] * len(headers)) + "|"
    head = "|" + "|".join(headers) + "|"
    body = ["|" + "|".join(cell(c) for c in row) + "|" for row in rows]
    return "\n".join([head, sep, *body])


def _render_markdown(state: dict[str, Any], root: RootConfig) -> str:
    """Render the full 20-AUDIT.md Markdown narrative from the collected state dict."""
    lines: list[str] = []

    ts = state.get("generated_at", "")
    lines.append("# 20-AUDIT — Categories cleanup audit")
    lines.append("")
    lines.append(f"**Generated:** {ts} by `arrconf audit`")
    lines.append(
        "**Operator:** Edit cells marked `?` then re-run `arrconf audit-verify` before commit."
    )
    lines.append("")

    # Mapping reference table
    lines.append("## Mapping reference (CLAUDE.md filesystem table)")
    lines.append("")
    mapping_rows: list[list[Any]] = [
        ["`/media/anime`", "`/media/series-zoe`", "YES"],
        ["`/media/family`", "`/media/series-garcons`", "YES"],
        ["`/media/films-family`", "`/media/films-enfants`", "YES"],
        ["`/media/films-anime`", "split (operator)", "NO"],
        ["`/media/series` (selective)", "series-emilie/thomas/garcons/zoe", "NO"],
        ["`/media/films` (selective)", "nouveaux-films", "NO"],
    ]
    lines.append(_render_table(["v0.2.0 legacy", "v0.3.0 Category", "Auto"], mapping_rows))
    lines.append("")

    # Radarr section
    radarr_state = state.get("radarr", {})
    lines.append("## Radarr")
    lines.append("")

    movies = radarr_state.get("movies_to_migrate", [])
    lines.append(f"### Movies on legacy rootFolderPath ({len(movies)} items)")
    lines.append("")
    movie_rows: list[list[Any]] = []
    for m in movies:
        target = m.get("auto_target_rootFolder") or "?"
        target_tags = "?"
        notes = "auto" if m.get("auto_target_rootFolder") else "operator decision"
        if m.get("auto_target_rootFolder"):
            action = "move_and_retag" if m.get("current_tags") else "move_only"
        else:
            action = "TBD"
        movie_rows.append(
            [
                m["id"],
                m["title"],
                m["current_rootFolder"],
                target,
                str(m.get("current_tags", [])),
                target_tags,
                action,
                notes,
            ]
        )
    lines.append(
        _render_table(
            [
                "id",
                "title",
                "current_rootFolder",
                "target_rootFolder",
                "current_tags",
                "target_tags",
                "action",
                "notes",
            ],
            movie_rows,
        )
    )
    lines.append("")

    radarr_tags = radarr_state.get("tags", [])
    lines.append(f"### Radarr Tags ({len(radarr_tags)} items)")
    lines.append("")
    tag_rows: list[list[Any]] = []
    for t in radarr_tags:
        target_lbl = t.get("target_label") or ("—" if t.get("proposed_action") == "prune" else "")
        tag_rows.append([t["id"], t["label"], t["proposed_action"], target_lbl or "—"])
    lines.append(_render_table(["id", "label", "proposed_action", "target_label"], tag_rows))
    lines.append("")

    radarr_dcs = radarr_state.get("download_clients", [])
    lines.append(f"### Radarr Download clients ({len(radarr_dcs)} items)")
    lines.append("")
    dc_rows: list[list[Any]] = []
    for dc in radarr_dcs:
        dc_rows.append(
            [
                dc["id"],
                dc["name"],
                str(dc.get("tags", [])),
                dc.get("priority", ""),
                dc["proposed_action"],
            ]
        )
    lines.append(
        _render_table(
            ["id", "name", "current_tags", "current_priority", "proposed_action"],
            dc_rows,
        )
    )
    lines.append("")

    # Sonarr section
    sonarr_state = state.get("sonarr", {})
    lines.append("## Sonarr")
    lines.append("")

    series_list = sonarr_state.get("series_to_migrate", [])
    lines.append(f"### Series on legacy rootFolderPath ({len(series_list)} items)")
    lines.append("")
    series_rows: list[list[Any]] = []
    for s in series_list:
        target = s.get("auto_target_rootFolder") or "?"
        target_tags = "?"
        notes = "auto" if s.get("auto_target_rootFolder") else "operator decision"
        if s.get("auto_target_rootFolder"):
            action = "move_and_retag" if s.get("current_tags") else "move_only"
        else:
            action = "TBD"
        series_rows.append(
            [
                s["id"],
                s["title"],
                s["current_rootFolder"],
                target,
                str(s.get("current_tags", [])),
                target_tags,
                action,
                notes,
            ]
        )
    lines.append(
        _render_table(
            [
                "id",
                "title",
                "current_rootFolder",
                "target_rootFolder",
                "current_tags",
                "target_tags",
                "action",
                "notes",
            ],
            series_rows,
        )
    )
    lines.append("")

    sonarr_tags = sonarr_state.get("tags", [])
    lines.append(f"### Sonarr Tags ({len(sonarr_tags)} items)")
    lines.append("")
    stag_rows: list[list[Any]] = []
    for t in sonarr_tags:
        target_lbl = t.get("target_label") or ("—" if t.get("proposed_action") == "prune" else "")
        stag_rows.append([t["id"], t["label"], t["proposed_action"], target_lbl or "—"])
    lines.append(_render_table(["id", "label", "proposed_action", "target_label"], stag_rows))
    lines.append("")

    sonarr_dcs = sonarr_state.get("download_clients", [])
    lines.append(f"### Sonarr Download clients ({len(sonarr_dcs)} items)")
    lines.append("")
    sdc_rows: list[list[Any]] = []
    for dc in sonarr_dcs:
        sdc_rows.append(
            [
                dc["id"],
                dc["name"],
                str(dc.get("tags", [])),
                dc.get("priority", ""),
                dc["proposed_action"],
            ]
        )
    lines.append(
        _render_table(
            ["id", "name", "current_tags", "current_priority", "proposed_action"],
            sdc_rows,
        )
    )
    lines.append("")

    # qBittorrent section
    qbit_state = state.get("qbittorrent", {})
    lines.append("## qBittorrent")
    lines.append("")

    cats_val = qbit_state.get("categories_validation", "OK")
    if cats_val == "OK":
        lines.append("### Categories validation: OK")
    else:
        drift_items = cats_val.get("drift", []) if isinstance(cats_val, dict) else []
        lines.append(f"### Categories validation: DRIFT ({len(drift_items)} items)")
        lines.append("")
        drift_rows: list[list[Any]] = [
            [d["name"], d["current_savePath"], d["expected_savePath"]] for d in drift_items
        ]
        lines.append(
            _render_table(
                ["name", "current_savePath", "expected_savePath (/data/torrents/<name>)"],
                drift_rows,
            )
        )
    lines.append("")

    torrents = qbit_state.get("torrents_to_relocate", [])
    lines.append(f"### In-flight torrents on legacy save_path ({len(torrents)} items)")
    lines.append("")
    torrent_rows: list[list[Any]] = []
    for t in torrents:
        target_sp = t.get("auto_target_save_path") or "?"
        torrent_rows.append(
            [
                t["hash"][:12] + "...",
                t["name"],
                t["category"],
                t["save_path"],
                t["state"],
                target_sp,
            ]
        )
    lines.append(
        _render_table(
            ["hash", "name (truncated)", "category", "save_path", "state", "target_save_path"],
            torrent_rows,
        )
    )
    lines.append("")

    # Seerr section
    seerr_state = state.get("seerr", {})
    lines.append("## Seerr")
    lines.append("")
    lines.append("### animeTags routing")
    lines.append("")
    seerr_rows: list[list[Any]] = []
    for svc in seerr_state.get("services", []):
        legacy_flag = "YES" if svc.get("animetags_legacy") else "NO"
        seerr_rows.append(
            [
                svc.get("service_name", ""),
                "YES" if svc.get("is_default") else "NO",
                str(svc.get("animetags_ids", [])),
                str(svc.get("animetags_labels", [])),
                legacy_flag,
                str(svc.get("animetags_proposed_ids", [])),
            ]
        )
    lines.append(
        _render_table(
            [
                "service",
                "isDefault",
                "animeTags (IDs)",
                "resolved labels",
                "legacy?",
                "target_animeTags (IDs)",
            ],
            seerr_rows,
        )
    )
    lines.append("")

    # Jellyfin section
    jellyfin_state = state.get("jellyfin", {})
    lines.append("## Jellyfin")
    lines.append("")
    lines.append("### Libraries Categories alignment")
    lines.append("")
    jf_rows: list[list[Any]] = []
    for lib in jellyfin_state.get("libraries", []):
        aligned_str = "YES" if lib.get("aligned") else "NO — drift"
        jf_rows.append(
            [
                lib.get("name", ""),
                lib.get("collection_type", ""),
                str(lib.get("paths", [])),
                aligned_str,
            ]
        )
    lines.append(
        _render_table(
            ["Name", "CollectionType", "PathInfos", "aligned with Category?"],
            jf_rows,
        )
    )
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Security: assert no secrets leaked into state dict
# ---------------------------------------------------------------------------


def _assert_no_secrets(state: dict[str, Any]) -> None:
    """Walk the state dict recursively and raise if any forbidden field name appears.

    Defensive guard at the end of run_audit (T-20-01 in the threat model).
    """

    def _walk(obj: Any, path: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in _SECRET_FIELD_NAMES:
                    raise ValueError(
                        f"Secret field '{k}' found in audit state at path '{path}.{k}'. "
                        "Audit output must never carry API keys, passwords, or tokens."
                    )
                _walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _walk(item, f"{path}[{i}]")

    _walk(state)


# ---------------------------------------------------------------------------
# run_audit — top-level orchestrator
# ---------------------------------------------------------------------------


def run_audit(
    root: RootConfig,
    settings: Settings,
    output_path: Path,
    targets: set[str],
) -> None:
    """Orchestrate per-app audit GETs and emit 20-AUDIT.md.

    Constructs clients for each target app, calls audit_* functions, aggregates
    results into the YAML appendix dict, and writes the Markdown + YAML appendix
    to output_path.
    """
    state: dict[str, Any] = {
        "audit_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "phase": 20,
    }

    if "radarr" in targets and "main" in root.radarr:
        instance = root.radarr["main"]
        assert settings.radarr_api_key is not None
        radarr_client = RadarrClient(
            base_url=instance.base_url,
            api_key=settings.radarr_api_key.get_secret_value(),
        )
        state["radarr"] = audit_radarr(radarr_client, root)
    else:
        state["radarr"] = {}

    if "sonarr" in targets and "main" in root.sonarr:
        instance_sonarr = root.sonarr["main"]
        assert settings.sonarr_api_key is not None
        sonarr_client = SonarrClient(
            base_url=instance_sonarr.base_url,
            api_key=settings.sonarr_api_key.get_secret_value(),
        )
        state["sonarr"] = audit_sonarr(sonarr_client, root)
    else:
        state["sonarr"] = {}

    if "qbittorrent" in targets and "main" in root.qbittorrent:
        instance_qbit = root.qbittorrent["main"]
        assert settings.qbt_user is not None and settings.qbt_pass is not None
        qbit_client = QbittorrentClient(
            base_url=instance_qbit.base_url,
            username=settings.qbt_user.get_secret_value(),
            password=settings.qbt_pass.get_secret_value(),
        )
        state["qbittorrent"] = audit_qbittorrent(qbit_client, root)
    else:
        state["qbittorrent"] = {}

    if (
        "seerr" in targets
        and "sonarr" in targets
        and "main" in root.seerr
        and "main" in root.sonarr
    ):
        # Seerr audit requires both Seerr AND Sonarr clients (Pitfall 3)
        instance_seerr = root.seerr["main"]
        assert settings.seerr_api_key is not None
        seerr_client = SeerrClient(
            base_url=instance_seerr.base_url,
            api_key=settings.seerr_api_key.get_secret_value(),
        )
        # Reuse sonarr_client if already constructed; otherwise build a new one
        if "sonarr" in targets and "main" in root.sonarr and settings.sonarr_api_key:
            instance_sonarr_for_seerr = root.sonarr["main"]
            sonarr_for_seerr = SonarrClient(
                base_url=instance_sonarr_for_seerr.base_url,
                api_key=settings.sonarr_api_key.get_secret_value(),
            )
        else:
            sonarr_for_seerr = None
        if sonarr_for_seerr is not None:
            state["seerr"] = audit_seerr(seerr_client, sonarr_for_seerr, root)
    else:
        state["seerr"] = {}

    if "jellyfin" in targets and "main" in root.jellyfin:
        instance_jf = root.jellyfin["main"]
        assert settings.jellyfin_api_key is not None
        jellyfin_client = JellyfinClient(
            base_url=instance_jf.base_url,
            api_key=settings.jellyfin_api_key.get_secret_value(),
        )
        state["jellyfin"] = audit_jellyfin(jellyfin_client, root)
    else:
        state["jellyfin"] = {}

    state["mapping_tables"] = {
        "legacy_path_to_category": dict(AUTO_PATH_MAPPING),
        "legacy_tag_to_category_series": dict(AUTO_TAG_MAPPING_SERIES),
        "legacy_tag_to_category_movies": dict(AUTO_TAG_MAPPING_MOVIES),
    }

    # Security: assert no secrets in the collected state (T-20-01)
    _assert_no_secrets(state)

    yaml = YAML(typ="safe")
    yaml.default_flow_style = False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = _render_markdown(state, root)
    with output_path.open("w", encoding="utf-8") as f:
        f.write(markdown)
        f.write("\n\n## Mapping appendix (parsed by Phase 21)\n\n```yaml\n")
        yaml.dump(state, f)
        f.write("```\n")

    log.info("run_audit_complete", output=str(output_path))


# ---------------------------------------------------------------------------
# verify_audit — pre-commit gate
# ---------------------------------------------------------------------------


def verify_audit(
    input_path: Path,
    root: RootConfig,
    sonarr: SonarrClient | None,
    radarr: RadarrClient | None,
) -> int:
    """Pre-commit verification gate for 20-AUDIT.md. Returns 0 on pass, 1 on failure.

    Gate 1: no `?` or `TBD` cells remaining in Markdown tables.
    Gate 2: YAML appendix block is present and parses without error.
    Gate 3: every to.rootFolderPath in the appendix is a known Category base_path.
    Gate 4: (only if clients non-None) every to.tags label exists in live Sonarr/Radarr /tag.
    """
    text = input_path.read_text(encoding="utf-8")

    # Gate 1: no unresolved operator cells
    if re.search(r"\|\s*\?\s*\|", text) or re.search(r"\|\s*TBD\s*\|", text):
        log.error("audit_unresolved_cells", input=str(input_path))
        return 1

    # Gate 2: YAML appendix parses
    yaml_block = re.search(r"```yaml\n(.*?)\n```", text, re.DOTALL)
    if not yaml_block:
        log.error("audit_missing_yaml_appendix", input=str(input_path))
        return 1

    yaml = YAML(typ="safe")
    try:
        appendix: dict[str, Any] = yaml.load(yaml_block.group(1)) or {}
    except Exception as exc:
        log.error("audit_yaml_parse_error", input=str(input_path), error=str(exc))
        return 1

    # Gate 3: all to.rootFolderPath ∈ categories[*].base_path
    valid_paths = {c.base_path for c in root.categories}
    for movie in appendix.get("radarr", {}).get("movies_to_migrate", []):
        target = (movie.get("to") or {}).get("rootFolderPath", "")
        if target and target not in valid_paths:
            log.error(
                "audit_invalid_target_path",
                item_id=movie.get("id"),
                target=target,
                valid=sorted(valid_paths),
            )
            return 1
    for series in appendix.get("sonarr", {}).get("series_to_migrate", []):
        target = (series.get("to") or {}).get("rootFolderPath", "")
        if target and target not in valid_paths:
            log.error(
                "audit_invalid_target_path",
                item_id=series.get("id"),
                target=target,
                valid=sorted(valid_paths),
            )
            return 1

    # Gate 4: live tag re-GET (only when clients are available)
    if radarr is not None:
        radarr_tags_raw: list[dict[str, Any]] = radarr.get("/tag")
        radarr_labels = {t["label"] for t in radarr_tags_raw}
        for movie in appendix.get("radarr", {}).get("movies_to_migrate", []):
            for tag_label in (movie.get("to") or {}).get("tags", []):
                if tag_label not in radarr_labels:
                    log.error(
                        "audit_target_tag_missing",
                        app="radarr",
                        tag=tag_label,
                        available=sorted(radarr_labels),
                    )
                    return 1

    if sonarr is not None:
        sonarr_tags_raw: list[dict[str, Any]] = sonarr.get("/tag")
        sonarr_labels = {t["label"] for t in sonarr_tags_raw}
        for series in appendix.get("sonarr", {}).get("series_to_migrate", []):
            for tag_label in (series.get("to") or {}).get("tags", []):
                if tag_label not in sonarr_labels:
                    log.error(
                        "audit_target_tag_missing",
                        app="sonarr",
                        tag=tag_label,
                        available=sorted(sonarr_labels),
                    )
                    return 1

    return 0
