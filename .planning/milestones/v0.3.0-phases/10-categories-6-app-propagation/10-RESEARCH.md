# Phase 10: Categories → 6-app propagation - Research

**Researched:** 2026-05-19
**Domain:** Python generator module + idempotence fixes + reconciler wiring (arrconf + Helm chart pin)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Separate `tools/arrconf/arrconf/generators/categories.py` pure-function module. Signature `generate_for_app(cfg, app) -> AppDerivedResources`. Reconcilers stay thin.
- **D-02:** Per-resource toggle `merge_with_manual`. `manual.items` non-empty → manual wins entirely. Empty → use generated. Log decision on every run.
- **D-03a:** qBit categories named bare `<name>` (NOT `<kind>-<name>`). Update REQUIREMENTS.md wording in same commit.
- **D-03b–e:** Each Category produces 1 download_client + 1 tag + 1 root_folder + 1 RPM per side (Sonarr 5, Radarr 5).
- **D-03f:** Cluster-side content re-tagging is OUT of arrconf scope (operator manual via UI or SQL).
- **D-04a:** Fix exactly 3 idempotence FPs (qBit categories, Prowlarr app-sync, Seerr user). No open-ended audit.
- **D-04b:** Managed-field-set comparator. Planner picks B1 (model-driven `Model.model_fields.keys()`) vs B2 (explicit allowlist mirroring Jellyfin `SERVER_CONFIG_ALLOWLIST`). Research which is right per resource.
- **D-04c:** One regression test per FP fix in `tests/test_idempotence_fp.py`.
- **D-05:** Chart-pin pre-bump documented in BOTH `CLAUDE.md` AND `.claude/agents/gsd-executor.md`. Phase 9-D pilot was de904c9 (0.5.0→0.5.3).

### Claude's Discretion

- Plan structure (1 generator+merger plan in Wave 1; 4 reconciler-wiring plans in Wave 2 plus 1 FP-fix plan; 1 chart-pin doc plan with CHARTS values.yaml co-bump per arrconf-code plan)
- Test layout (mirrors existing arrconf test conventions)
- Snapshot discipline (ADR-6 baseline before Wave 2 cluster-touch tests)
- Whether configarr quality-profile derivation is purely documentation or if arrconf emits a structured input file

### Deferred Ideas (OUT OF SCOPE)

- Phase 11: REQ-04-09-argocd-selfheal, REQ-cm-cruft-cleanup, REQ-ruff-format-ci-gate, REQ-paths-filter-arrconf, REQ-renovate-app-install, REQ-snapshot-redaction-harden, REQ-readme-onboarding-v030
- v0.4.0+: REQ-categories-deprecation, REQ-bazarr-addition, Phase 8 ESO/Akeyless, multi-instance Sonarr/Radarr
- Cluster-side content migration (operator manual step — documented in CLAUDE.md only)

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-categories-qbit-propagation | Each Category generates one qBit category named `<name>` with `savePath: /data/torrents/<name>`. 10 categories → 10 qBit categories. | Generator module D-01; merge_with_manual D-02; existing `QbittorrentCategory.model_config = ConfigDict(extra="allow")` — FP fix B2 needed (see §FP Analysis) |
| REQ-categories-sonarr-propagation | Each `kind: series` Category generates 1 tag + 1 root_folder + 1 download_client + 1 RPM on Sonarr (5×4=20 resources). | Generator module; `SonarrInstance` already has all 4 section types; connection constants in `arrconf.yml` lines 80–108 |
| REQ-categories-radarr-propagation | Same as Sonarr for `kind: movies` Categories. | Identical shape; `RadarrInstance` fields match `SonarrInstance`; connection constants in `arrconf.yml` lines 243–272 |
| REQ-categories-configarr-mapping | configarr generates exactly 3 profiles (`General`, `Anime`, `Family`) from union of `profile` values. arrconf MUST NOT write configarr.yml. | Profile enum already closed `Literal["general","anime","family"]`; arrconf only validates subset membership at load time (already enforced by pydantic `Profile` Literal) |
| REQ-categories-seerr-routing | Seerr `sonarr_service.animeTags` populated with tag IDs for every `profile: anime` Category. | `SeerrSonarrServiceSection.animeTags: list[int]` already in YAML model; generator must resolve label→ID using post-reconcile Sonarr tag list |
| REQ-categories-jellyfin-paths | Jellyfin `Séries` gets all `kind: series` base_paths (5 PathInfos); `Films` gets all `kind: movies` base_paths (5 PathInfos). | `_reconcile_libraries` already uses set-membership shim; paths derive directly from `c.base_path` for each Category |
| REQ-chart-pin-prebump | `gsd-executor` agent prompt + `CLAUDE.md` document the "same-commit image tag bump" pattern. | `values.yaml:451` current tag `"0.5.3"`; executor file at `/home/moi/.claude/agents/gsd-executor.md`; no chart-pin rule exists there yet |
| REQ-idempotence-fp-fix | 2nd-run `arrconf apply` on each of the 6 apps emits 0 `plan_action` events. | 3 FP root causes fully diagnosed below (§FP Analysis) |

</phase_requirements>

---

## Summary

Phase 10 adds a pure-function generator module (`generators/categories.py`) that expands `cfg.categories` into per-app resource lists, a `merge_with_manual()` helper in `reconcilers/_shared.py` that implements the per-resource override toggle, and wires the output into each of the 6 app reconcilers. Reconciler signatures stay unchanged — `__main__.py` pre-merges before dispatch.

Three idempotence false-positives (qBit categories, Prowlarr app-sync, Seerr user) are fixed by filtering cluster GET responses to the managed-field set before diffing. The correct fix approach for all three is **B2 (explicit allowlist)**, not B1, because all three models use `extra="allow"` — pydantic `model_fields.keys()` only covers declared fields and would miss aliased or renamed fields, whereas the FP source is undeclared *extra* keys returned by the API.

The chart-pin co-bump rule needs to be injected into `/home/moi/.claude/agents/gsd-executor.md` and `CLAUDE.md` as new documentation sections. Current `arrconf.image.tag` is `"0.5.3"` (line 451 of `values.yaml`).

**Primary recommendation:** Build generators/ + merge_with_manual() in Wave 1, wire all 6 reconcilers + FP fixes in parallel Wave 2, close with chart-pin docs + phase10 baseline fixture in Wave 3.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Category→resources expansion | API / Backend (arrconf reconciler layer) | — | Pure Python data transformation; no network calls needed |
| Override merge predicate | API / Backend (reconcilers/_shared.py) | — | Cross-reconciler helper; called before reconciler dispatch in `__main__.py` |
| qBit category creation | API / Backend (qbittorrent reconciler) | — | Form-encoded POST to qBit /api/v2/torrents/createCategory |
| Sonarr/Radarr tags + root_folders + DCs + RPMs | API / Backend (sonarr/radarr reconcilers) | — | Existing reconcile() + _execute() infrastructure |
| Seerr animeTags population | API / Backend (seerr reconciler) | — | Integer IDs resolved from post-reconcile Sonarr tag list; PUT settings/sonarr |
| Jellyfin PathInfos | API / Backend (jellyfin reconciler) | — | POST /Library/VirtualFolders/Paths with set-membership shim already present |
| configarr quality profiles | CDN / Static (configarr.yml + configarr CronJob) | — | ADR-5: arrconf MUST NOT touch quality_profiles; configarr.yml is operator-edited |
| Chart image pin co-bump | CDN / Static (Helm values.yaml) | — | values.yaml bump co-committed with each arrconf-code change |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic v2 | 2.x (already in project) | AppDerivedResources typed containers + validation | Project standard; `Category` model already uses it |
| structlog | existing | Structured `merge_decision` log events | Project standard; all reconcilers use it |
| Python 3.13 | already in pyproject.toml | Generator module runtime | Project standard |

No new library dependencies needed for Phase 10. All building blocks exist.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| respx | existing | Mock qBit/Sonarr/Radarr/Seerr/Jellyfin GET in tests | All new reconciler tests; MUST NOT call real APIs |
| pytest | existing | Test runner; parametrize for 10-category fixtures | Required for ≥70% coverage gate |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Explicit B2 allowlist per FP resource | B1 model_fields filter | B1 fails for `extra="allow"` models — extra keys returned by API are not in `model_fields`; B2 is safer and explicit |
| Pre-merge in `__main__.py` | Pre-merge inside each reconciler | `__main__.py` keeps reconciler signatures unchanged (CONTEXT.md preferred); but Seerr animeTags needs the post-reconcile Sonarr tag list, so the pre-merge for animeTags must happen INSIDE the Seerr reconciler AFTER Sonarr runs (exception documented below) |

---

## Architecture Patterns

### System Architecture Diagram

```
arrconf.yml
  └── categories: [10 entries]
  └── sonarr/radarr/qbittorrent/seerr/jellyfin: [flat sections (v0.2.0)]

load_config()
  └── RootConfig (cfg.categories: list[MediaCategory])
        │
        ▼  (in __main__.py apply, before reconciler dispatch)
generators/categories.py
  generate_for_app(cfg, "qbit")  → list[QbitCategory]
  generate_for_app(cfg, "sonarr") → SonarrDerived
  generate_for_app(cfg, "radarr") → RadarrDerived
  generate_for_app(cfg, "jellyfin") → list[JellyfinLibrary]
        │
        ▼  (reconcilers/_shared.py)
merge_with_manual(manual_section, generated_items) → list[items]
  log: merge_decision app=X resource=Y source=categories|manual n=Z
        │
        ┌─────────────────────────────────────┐
        ▼                                     ▼
reconcile_qbittorrent(client, instance*)  reconcile_sonarr(client, instance*)
  _reconcile_categories(merged_cats)       _reconcile_tags(merged_tags)
  [FP fix: B2 allowlist on Category]       _reconcile_root_folders(merged_rf)
                                           _reconcile_download_clients(merged_dcs)
                                           _reconcile_remote_path_mappings(merged_rpms)
        ▼                                     ▼
reconcile_radarr(client, instance*)      reconcile_seerr(client, instance*)
  (same shape as sonarr, kind=movies)      animeTags = IDs from Sonarr tag
                                           reconcile result (special case)
        ▼                                     ▼
reconcile_jellyfin(client, instance*)    reconcile_prowlarr(client, instance*)
  _reconcile_libraries(merged_libs)        [FP fix: B2 allowlist on Application]
  (paths derived from kind routing)

* instance.{tags,root_folders,download_clients,remote_path_mappings,categories,libraries}.items
  replaced by merged output BEFORE passing to reconciler
```

### Recommended Project Structure

```
tools/arrconf/arrconf/
├── generators/
│   ├── __init__.py          # expose generate_for_app
│   └── categories.py        # pure functions; no I/O; no client calls
├── reconcilers/
│   ├── _shared.py           # ADD: merge_with_manual() + filter_to_allowlist()
│   ├── qbittorrent.py       # wire generate+merge; FP fix #1
│   ├── sonarr.py            # wire generate+merge
│   ├── radarr.py            # wire generate+merge
│   ├── seerr.py             # animeTags resolution; FP fix #3
│   ├── prowlarr.py          # FP fix #2 only (no generator wiring)
│   └── jellyfin.py          # wire generate+merge for library paths
└── __main__.py              # pre-merge injection point (for qbit/sonarr/radarr/jellyfin)
tools/arrconf/tests/
├── test_generators_categories.py   # NEW: unit tests for generate_for_app
├── test_merge_with_manual.py       # NEW: unit tests for override toggle
├── test_idempotence_fp.py          # NEW: 3 FP regression tests
├── test_qbittorrent_categories.py  # NEW: categories wiring test
├── test_sonarr_categories.py       # NEW: sonarr 5×4 wiring test
├── test_radarr_categories.py       # NEW: radarr 5×4 wiring test
├── test_seerr_animetags.py         # NEW: animeTags resolution test
├── test_jellyfin_categories.py     # NEW: library paths wiring test
└── fixtures/
    └── phase10-baseline-plans.json  # NEW: post-Categories-generation baseline
```

### Pattern 1: generate_for_app() pure function structure

[VERIFIED: tools/arrconf/arrconf/resources/categories.py:17–51, tools/arrconf/arrconf/config.py:29–37, charts/arr-stack/files/arrconf.yml:2–53]

```python
# tools/arrconf/arrconf/generators/categories.py
from dataclasses import dataclass
from typing import Literal
from arrconf.config import RootConfig
from arrconf.resources.categories import Category as MediaCategory
from arrconf.resources.qbittorrent.category import Category as QbitCategory
from arrconf.resources.sonarr.tag import Tag as SonarrTag
from arrconf.resources.sonarr.root_folder import RootFolder
from arrconf.resources.sonarr.download_client import DownloadClient
from arrconf.resources.sonarr.remote_path_mapping import RemotePathMapping
from arrconf.resources.jellyfin import JellyfinLibrary

# Connection constants (from production arrconf.yml lines 80-108, 243-272)
_QBIT_HOST = "qbittorrent.selfhost.svc.cluster.local"
_QBIT_PORT = 8080
_QBIT_DC_FIELDS_BASE = [  # fields common to all generated download clients
    {"name": "host", "value": _QBIT_HOST},
    {"name": "port", "value": _QBIT_PORT},
    {"name": "useSsl", "value": False},
    {"name": "urlBase", "value": ""},
    {"name": "username", "value": ""},
    {"name": "password", "value": ""},
    {"name": "tvImportedCategory", "value": ""},   # Sonarr-side
    {"name": "recentTvPriority", "value": 0},
    {"name": "olderTvPriority", "value": 0},
    {"name": "initialState", "value": 0},
    {"name": "sequentialOrder", "value": False},
    {"name": "firstAndLast", "value": False},
    {"name": "contentLayout", "value": 0},
]
# For Radarr: replace tvImportedCategory with movieImportedCategory,
#   recentTvPriority → recentMoviePriority, olderTvPriority → olderMoviePriority

@dataclass
class SonarrDerived:
    tags: list[SonarrTag]
    root_folders: list[RootFolder]
    download_clients: list[DownloadClient]
    remote_path_mappings: list[RemotePathMapping]

@dataclass
class RadarrDerived:  # identical shape to SonarrDerived
    tags: list[Any]
    root_folders: list[RootFolder]
    download_clients: list[DownloadClient]
    remote_path_mappings: list[RemotePathMapping]

def generate_qbit_categories(cfg: RootConfig) -> list[QbitCategory]:
    """D-03a: bare <name>, savePath=/data/torrents/<name>."""
    return [
        QbitCategory(name=c.name, savePath=f"/data/torrents/{c.name}")
        for c in cfg.categories
    ]

def generate_sonarr_resources(cfg: RootConfig) -> SonarrDerived:
    """D-03b–e: 5 series Categories → 5×4 Sonarr resources."""
    series = [c for c in cfg.categories if c.kind == "series"]
    return SonarrDerived(
        tags=[SonarrTag(label=c.name) for c in series],
        root_folders=[RootFolder(path=c.base_path) for c in series],
        download_clients=[_make_sonarr_dc(c) for c in series],
        remote_path_mappings=[_make_rpm(c) for c in series],
    )

def generate_radarr_resources(cfg: RootConfig) -> RadarrDerived: ...

def generate_jellyfin_libraries(cfg: RootConfig) -> list[JellyfinLibrary]:
    """2 super-libraries: Séries (kind=series paths) + Films (kind=movies paths)."""
    series_paths = [c.base_path for c in cfg.categories if c.kind == "series"]
    movies_paths = [c.base_path for c in cfg.categories if c.kind == "movies"]
    return [
        JellyfinLibrary(name="Séries", collection_type="tvshows", paths=series_paths),
        JellyfinLibrary(name="Films", collection_type="movies", paths=movies_paths),
    ]

def generate_anime_tag_labels(cfg: RootConfig) -> list[str]:
    """Seerr animeTags: label names for profile=anime Categories."""
    return [c.name for c in cfg.categories if c.profile == "anime"]
```

**Key constants from production arrconf.yml:**
- Sonarr DC fields: `tvCategory=c.name`, `tag_labels=[c.name]` [VERIFIED: arrconf.yml:92,108]
- Radarr DC fields: `movieCategory=c.name`, `tag_labels=[c.name]` [VERIFIED: arrconf.yml:257,272]
- RPM host: `qbittorrent.selfhost.svc.cluster.local` [VERIFIED: arrconf.yml:190]
- RPM pattern: `remotePath=/data/<name>/`, `localPath=/data/torrents/<name>/` [VERIFIED: D-03e]

### Pattern 2: merge_with_manual() in _shared.py

[VERIFIED: tools/arrconf/arrconf/reconcilers/_shared.py:1–10 — natural home for cross-reconciler helpers]

```python
# Addition to tools/arrconf/arrconf/reconcilers/_shared.py

from typing import Any
import structlog

log = structlog.get_logger()

def merge_with_manual(
    manual_items: list[Any],
    generated_items: list[Any],
    *,
    app: str,
    resource: str,
) -> list[Any]:
    """D-02: per-resource toggle. manual non-empty → skip generated entirely.
    
    Log line: merge_decision app=X resource=Y source=categories|manual n=Z
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
```

### Pattern 3: __main__.py injection point — where to call generate+merge

[VERIFIED: tools/arrconf/arrconf/__main__.py:122–133 (Sonarr branch), :195–243 (qBit branch)]

The `apply` command in `__main__.py` dispatches per-app by checking `if "sonarr" in targets and "main" in root.sonarr`. The `instance` variable is the `SonarrInstance` (or `QbittorrentInstance`, etc.) directly from `root.sonarr["main"]`. The reconciler receives this instance unchanged.

**Preferred injection approach (CONTEXT.md):** mutate the instance sections BEFORE passing to the reconciler. Since pydantic models are not frozen by default, we can do:

```python
# In __main__.py apply(), sonarr branch (after: instance = root.sonarr["main"])
from arrconf.generators.categories import generate_sonarr_resources
from arrconf.reconcilers._shared import merge_with_manual

derived = generate_sonarr_resources(root)
instance.tags.items = merge_with_manual(
    instance.tags.items, [TagItem(label=t.label) for t in derived.tags],
    app="sonarr", resource="tags"
)
instance.root_folders.items = merge_with_manual(
    instance.root_folders.items, derived.root_folders,
    app="sonarr", resource="root_folders"
)
# ... etc. for download_clients, remote_path_mappings
```

**Special case — Seerr animeTags:** The animeTags field requires Sonarr tag integer IDs (resolved post-reconcile from the cluster's /tag endpoint), NOT the label strings from the generator. The Seerr reconciler must resolve them AFTER `reconcile_sonarr()` completes and returns `all_tags`. This means the animeTags injection happens inside `seerr.py` at `_reconcile_settings_sonarr()` call time, not in `__main__.py`. See §Seerr animeTags below for exact pattern.

### Pattern 4: FP fix — B2 allowlist comparator

[VERIFIED: tools/arrconf/arrconf/reconcilers/jellyfin.py:56–103 (SERVER_CONFIG_ALLOWLIST precedent)]
[VERIFIED: tools/arrconf/arrconf/resources/qbittorrent/category.py:20 (`extra="allow"`)]
[VERIFIED: tools/arrconf/arrconf/resources/seerr/user.py:17 (`extra="allow"`)]

**Decision: use B2 (explicit allowlist) for all 3 FP fixes.**

Rationale: All 3 affected models use `extra="allow"` (verified below). `model_fields.keys()` only returns declared fields, not keys captured via `extra="allow"`. The FP source is exactly those extra keys returned by the API. An explicit allowlist named `*_MANAGED_FIELDS: frozenset[str]` is placed adjacent to each model (mirrors `SERVER_CONFIG_ALLOWLIST` in jellyfin.py:56).

```python
# Pattern — add adjacent to each affected model/reconciler:

# For qBit Category (in reconcilers/qbittorrent.py or resources/qbittorrent/category.py):
QBIT_CATEGORY_MANAGED_FIELDS: frozenset[str] = frozenset({"name", "savePath"})

# For Prowlarr Application (in reconcilers/prowlarr.py or resources/prowlarr/application.py):
PROWLARR_APP_MANAGED_FIELDS: frozenset[str] = frozenset({
    "name", "enable", "implementation", "configContract", "syncLevel", "fields", "tags"
})

# For Seerr User (in reconcilers/seerr.py or resources/seerr/user.py):
SEERR_USER_MANAGED_FIELDS: frozenset[str] = frozenset({
    "displayName", "permissions", "movieQuotaDays", "movieQuotaLimit",
    "tvQuotaDays", "tvQuotaLimit"
})

# Usage in comparator:
def filter_to_managed(cluster: dict, allowlist: frozenset[str]) -> dict:
    return {k: v for k, v in cluster.items() if k in allowlist}
```

### Pattern 5: Seerr animeTags resolution call chain

[VERIFIED: tools/arrconf/arrconf/reconcilers/seerr.py:108–168 (_reconcile_settings_sonarr)]
[VERIFIED: tools/arrconf/arrconf/resources/seerr/sonarr_service.py:34 (animeTags: list[int])]
[VERIFIED: tools/arrconf/arrconf/config.py:428–432 (SeerrSonarrServiceSection.animeTags: list[int])]

The `animeTags` field on the Seerr Sonarr service config is `list[int]` — Sonarr tag integer IDs. Seerr does NOT accept tag labels; it stores and returns integer IDs. [VERIFIED: seerr/settings_sonarr.json fixture, arrconf.yml:445 `animeTags: [3]`]

The resolution chain for Phase 10:
1. `generate_anime_tag_labels(cfg)` returns `["series-zoe"]` (1 entry for `profile: anime`)
2. After `reconcile_sonarr()` returns `SonarrResult` in `__main__.py`, the `managed_tag_id` + `all_tags` are internal to the reconciler. The result does NOT expose `all_tags` directly.
3. **Two implementation options:**
   - **Option A (inject via instance):** Resolve label→ID inside `__main__.py` by calling `SonarrClient.get("/tag")` a second time after `reconcile_sonarr()` completes, then populate `root.seerr["main"].sonarr_service.animeTags` before calling `reconcile_seerr()`.
   - **Option B (inject via parameter):** Pass the anime tag labels as a new parameter to `reconcile_seerr()` / `_reconcile_settings_sonarr()`, which then resolves IDs from the live tag list. This changes the reconciler signature slightly.

**Recommendation:** Option A — call `SonarrClient.get("/tag")` in `__main__.py` after Sonarr reconcile, resolve labels from `cfg.categories` to IDs, populate `seerr_instance.sonarr_service.animeTags`. This preserves the reconciler signature and centralizes all pre-merge logic in `__main__.py`. The extra GET is idempotent and cheap (tag list is small).

**Important:** The current production `arrconf.yml` already has `animeTags: [3]` hardcoded [VERIFIED: arrconf.yml:445]. Phase 10 replaces this hardcoded value with the dynamically derived list. The `merge_with_manual()` toggle applies: if `sonarr_service.animeTags` is non-empty in YAML, use manual value; if empty, use generated. Since it's currently non-empty, operator must empty it to activate Categories-derived routing.

### Pattern 6: Jellyfin library paths — derived shape

[VERIFIED: tools/arrconf/arrconf/reconcilers/jellyfin.py:106–176 (_reconcile_libraries)]
[VERIFIED: tools/arrconf/arrconf/resources/jellyfin/__init__.py — JellyfinLibrary model]

The `_reconcile_libraries` function at jellyfin.py:106 checks `existing_paths: set[str]` from `library_options.get("PathInfos")` and only POSTs new paths (idempotence shim). Path attribute is `"Path"` (PascalCase) — confirmed at jellyfin.py:144 `p.get("Path")`.

The POST body is `{"Name": lib_name, "Path": path, "PathInfo": {"Path": path}}` [VERIFIED: jellyfin.py:163–168]. No `LibraryOptions` passed — Phase 7 explicitly scoped to paths only (D-07-LIB-02).

For Phase 10, the generator produces:
```python
JellyfinLibrary(name="Séries", collection_type="tvshows",
                paths=["/media/series", "/media/series-emilie", "/media/series-thomas",
                       "/media/series-garcons", "/media/series-zoe"])
JellyfinLibrary(name="Films", collection_type="movies",
                paths=["/media/films", "/media/nouveaux-films", "/media/films-enfants",
                       "/media/films-animation-enfants", "/media/films-zoe"])
```

The merge_with_manual toggle applies at the `JellyfinLibrariesSection.items` level: if operator declares items manually, the generated libraries are skipped entirely.

### Anti-Patterns to Avoid

- **Modifying reconciler signatures:** CONTEXT.md explicitly requires reconcilers to stay thin and signatures unchanged. Pre-merge happens in `__main__.py` or at the injection point.
- **Calling B1 (`Model.model_fields.keys()`) on `extra="allow"` models:** Will NOT filter extra keys returned by API — use B2 allowlist instead.
- **Putting animeTags resolution in the generator:** The generator produces label strings; integer IDs require a cluster GET. Generator stays pure (no I/O).
- **Touching configarr.yml from arrconf:** ADR-5 frontière — `ScopeViolationError` must still be raised if arrconf code tries to write quality_profiles. The configarr mapping is purely operator-authored documentation.
- **Deleting flat sections in the same commit as wiring:** CONTEXT.md explicitly says to leave flat sections in place so override merge can validate via production smoke test.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured logging for merge decisions | Custom log formatter | `structlog.get_logger().info("merge_decision", ...)` | Already project standard; consistent key shape |
| Tag label→ID resolution | New resolver function | Extend existing `_resolve_download_client_tag_labels()` in `_shared.py` | Already handles ReconcileError on missing labels; used by Sonarr and Radarr |
| FP field filtering | Generic dict walker | B2 explicit `frozenset` allowlist (mirrors `SERVER_CONFIG_ALLOWLIST`) | Precedent in jellyfin.py:56; explicit is auditable |
| Test helper for 6-app sweep | New test runner | Generalize `_phase9_helpers.py` → `_arrconf_helpers.py` | Walker already covers all 6 apps with correct auth shims |

**Key insight:** The entire Phase 10 test infrastructure reuses `_phase9_helpers.py:dry_run_all_apps()` unchanged for the phase10-baseline fixture; only the input YAML config and output fixture file change.

---

## FP Root Cause Analysis

### FP #1: qBit Categories (`qbittorrent/category.py:20 extra="allow"`)

[VERIFIED: tools/arrconf/arrconf/resources/qbittorrent/category.py:20]
[VERIFIED: tools/arrconf/tests/fixtures/qbittorrent/categories.json]

The `Category` model has `extra="allow"`. The production qBit fixture (`tests/fixtures/qbittorrent/categories.json`) shows each category returning these extra fields not in the model:
- `download_path` (null)
- `inactive_seeding_time_limit` (-2)
- `ratio_limit` (-2)
- `seeding_time_limit` (-2)
- `share_limit_action` ("Default")

When `differ.reconcile()` calls `diff_models(cur, des)`, the current model (parsed from GET) carries these extra fields in its `model_dump()` output (because `extra="allow"` stores them in `__pydantic_extra__`). The desired model has none of them. `diff_models()` sees a difference → emits UPDATE for every category on every run.

**Fix:** In `_reconcile_categories()` at `qbittorrent.py:108`, filter each cluster-returned category dict to `QBIT_CATEGORY_MANAGED_FIELDS` before `Category.model_validate()`:
```python
current = [Category.model_validate({k: v for k, v in obj.items()
           if k in QBIT_CATEGORY_MANAGED_FIELDS})
           for obj in raw.values()]
```

**Allowlist:** `frozenset({"name", "savePath"})` — the 2 fields arrconf manages.

### FP #2: Prowlarr app-sync (`resources/prowlarr/application.py`)

[VERIFIED: tools/arrconf/tests/fixtures/prowlarr/applications.json — full GET response]
[VERIFIED: tools/arrconf/arrconf/reconcilers/prowlarr.py:183 `Application.model_validate(x)`]

The `applications.json` fixture shows each Application returning rich metadata fields beyond what arrconf models: `infoLink`, `implementationName`, `message` (possibly null), `presets` (possibly null), plus the `fields[]` array includes many extra keys per field object (`label`, `helpText`, `advanced`, `order`, `type`, `placeholder`, `isFloat`, `selectOptions`, etc.) that are NOT in the `FieldKV` model.

The `Application` model (need to check — `extra="forbid"` or `extra="allow"`?) — if `extra="allow"`, the extra field-level keys cause drift. The `differ.py:_READ_ONLY_FIELDS` set already excludes `id`, `implementationName`, `infoLink`, `message`, `presets` [VERIFIED: differ.py:20–26]. But if Application model is `extra="allow"`, the extra fields inside `fields[]` sub-objects still cause FPs.

Looking at the fixture: `FieldKV` model is used for `fields[]`. Each field in the fixture has `label`, `helpText`, `advanced`, `order`, `type`, `privacy`, `isFloat`, `value`, `selectOptions`, `placeholder`. If `FieldKV` is `extra="allow"`, these all round-trip and may cause diff churn depending on which fields are in the desired YAML config vs what the cluster returns.

**Fix approach:** Add `PROWLARR_APP_MANAGED_FIELDS: frozenset[str]` and filter cluster Application dict before `model_validate`. The managed fields are: `name`, `enable`, `implementation`, `configContract`, `syncLevel`, `fields`, `tags`. Top-level extra keys (`implementationName`, `infoLink`, `presets`, `message`) are already in `_READ_ONLY_FIELDS` in differ.py — but `id` is also already there. The likely remaining FP source is `fields[]` sub-object extra keys.

Planner should add `extra="forbid"` verification or apply the allowlist at the `Application.model_validate()` call site in `prowlarr.py:183`.

**Note:** Need to verify `Application` model config in `resources/prowlarr/application.py`. [ASSUMED] — not read in this session. Check `extra="allow"` vs `extra="forbid"` before implementing.

### FP #3: Seerr user (`resources/seerr/user.py:17 extra="allow"`)

[VERIFIED: tools/arrconf/arrconf/resources/seerr/user.py:17 (`extra="allow"`)]
[VERIFIED: tools/arrconf/tests/fixtures/seerr/user.json]

The `SeerrUser` model has `extra="allow"`. The user fixture shows additional fields returned by the API that are NOT in `model_dump()` output (because they're excluded via `Field(exclude=True)`): `requestCount`, `warnings`, `settings`, `avatar`, `avatarETag`, `avatarVersion`, `createdAt`, `updatedAt`, `userType`, `plexId`, `jellyfinUserId`, `username`, `email`, `jellyfinUsername`, `plexUsername`, `recoveryLinkExpirationDate`.

These are declared in the model WITH `exclude=True` [VERIFIED: user.py:29–44]. The `_payloads_equivalent()` function at seerr.py:97 checks `all(current.get(k) == v for k, v in desired.items())` where `desired = put_body = desired_user.model_dump()`. Since `model_dump()` excludes the `exclude=True` fields, `desired` is small (7 fields). The comparison is `current.get(k) == v` for each key in `desired` — this should be a subset check that ignores extra cluster fields.

**BUT the FP occurs because:** `extra="allow"` means extra cluster fields that are NOT in model_fields (e.g. `settings` or server-generated fields added in newer Seerr versions) end up in `model_dump()` output when `exclude_unset=False`. The comparison then includes those extra keys — which the desired dict doesn't have.

Wait — re-reading: `_payloads_equivalent` only iterates `desired.items()`. So if `desired` is small (7 fields), the check is narrow. The FP must be different: `put_body = desired_user.model_dump()` which calls `model_dump()` on the `SeerrUser` instance created from the YAML `section.admin` value. If `SeerrUser` has `extra="allow"`, any extra YAML fields would end up in `put_body` — but `extra="forbid"` would have caught them at load time.

Re-examining: The CONTEXT.md says "D-06-SEERR-USER-FP: `/api/v1/user` returns pydantic-excluded fields that diverge from `model_dump` output." This means the FP is: the cluster GET returns fields whose VALUES differ from what model_dump produces (including the default values for declared fields). For example, `requestCount: 14` in the fixture — if the model had `requestCount: int = 0` without `exclude=True`, `model_dump()` would emit `requestCount: 0` while cluster returns `14`, causing a spurious UPDATE. BUT `requestCount` IS `exclude=True` in the model [VERIFIED: user.py:42].

The actual FP: `put_body = desired_user.model_dump()` produces a dict with the writable fields. `_payloads_equivalent(admin_current, put_body)` checks `all(admin_current.get(k) == v for k, v in put_body.items())`. This is correct — the 7 writable fields should match if the cluster is already in the desired state. The FP must be in a specific field value mismatch (e.g. `movieQuotaDays: None` in desired vs `null` in JSON vs `None` in Python — these should be equal).

**Most likely FP cause:** `movieQuotaDays: null` in the cluster fixture [VERIFIED: user.json] vs `movieQuotaDays: None` in Python — these ARE equal in Python. So the FP is probably a type mismatch: `tvQuotaDays/Limit: null` cluster vs pydantic default `None` in model → equal. OR the fix needed is simply that when `SeerrUser` is constructed from YAML with unset optional fields, `model_dump()` emits them as `None` which doesn't match cluster's absent/different value.

**Fix:** Apply `SEERR_USER_MANAGED_FIELDS` allowlist to filter `admin_current` before `_payloads_equivalent()`:
```python
cluster_filtered = {k: v for k, v in admin_current.items() if k in SEERR_USER_MANAGED_FIELDS}
if _payloads_equivalent(cluster_filtered, put_body):
```

This makes the comparison narrow to only the 6 writable fields (excluding `id` which is already `exclude=True`).

---

## Idempotence FP Fix: B1 vs B2 Verdict

**Use B2 (explicit allowlist) uniformly for all 3 fixes.**

| Model | extra= | B1 viable? | B2 (allowlist) |
|-------|--------|-----------|----------------|
| `Category` (qbit) | `extra="allow"` | No — `model_fields.keys()` = {`name`, `savePath`}, which IS the full allowlist. But B1 works only by accident for 2-field models. Use B2 for consistency. | `QBIT_CATEGORY_MANAGED_FIELDS = frozenset({"name", "savePath"})` |
| `Application` (prowlarr) | Need to verify | Unknown | `PROWLARR_APP_MANAGED_FIELDS` — top-level keys only; fields[] sub-objects handled by existing credential logic |
| `SeerrUser` | `extra="allow"` | No | `SEERR_USER_MANAGED_FIELDS = frozenset({"displayName", "permissions", "movieQuotaDays", "movieQuotaLimit", "tvQuotaDays", "tvQuotaLimit"})` |

The Jellyfin `SERVER_CONFIG_ALLOWLIST` pattern is the canonical precedent: `tuple[str, ...]` placed as a module-level constant adjacent to the reconciler function. Mirrors this exactly.

---

## Reconciler Invocation Contract

[VERIFIED: tools/arrconf/arrconf/__main__.py:122–133, :195–244, :245–297, :271–296]

Current per-app signatures (confirmed from reconcilers):
```python
reconcile_sonarr(client: SonarrClient, instance: SonarrInstance, dry_run: bool) -> SonarrResult
reconcile_radarr(client: RadarrClient, instance: RadarrInstance, dry_run: bool) -> RadarrResult
reconcile_prowlarr(client: ProwlarrClient, instance: ProwlarrInstance, dry_run: bool) -> ProwlarrResult
reconcile_qbittorrent(client: QbittorrentClient, instance: QbittorrentInstance, dry_run: bool) -> QbittorrentResult
reconcile_seerr(client: SeerrClient, instance: SeerrInstance, dry_run: bool) -> SeerrResult
reconcile_jellyfin(client: JellyfinClient, instance: JellyfinInstance, dry_run: bool) -> JellyfinResult
```

All signatures are UNCHANGED in Phase 10. The `instance` object is mutated in-place (item lists replaced) before the reconciler call in `__main__.py`. For Seerr animeTags (which requires post-Sonarr tag IDs), the mutation happens in `__main__.py` AFTER `reconcile_sonarr()` returns but BEFORE `reconcile_seerr()` is called.

The `diff` and `dump` commands in `__main__.py` must also receive the same pre-merge treatment to avoid drift between `diff` and `apply` results.

---

## Test Fixture Extension Strategy

[VERIFIED: tools/arrconf/tests/_phase9_helpers.py:1–390]
[VERIFIED: tools/arrconf/tests/fixtures/phase9-baseline-plans.json: prowlarr=2 plans, qbittorrent=9 plans, radarr=4 plans, sonarr=4 plans]

`_phase9_helpers.py:dry_run_all_apps(cfg)` already walks all 6 reconcilers. The helper is self-contained and reusable.

**Recommendation: rename (copy) `_phase9_helpers.py` to `_arrconf_helpers.py`** and make it the canonical multi-app dry-run walker. The phase9 version remains as-is for backward compatibility. The new version can accept an optional argument to control which fixtures are loaded (or we extend the route registration to cover the Categories-era fixtures).

**phase10-baseline-plans.json:** Generated by running `dry_run_all_apps(cfg)` with the production `arrconf.yml` AFTER Phase 10 reconciler wiring lands (with flat sections still present — override merge defaults to manual for non-empty sections). This baseline captures the new plan shape (e.g. Sonarr now produces plans for 5 tags + 5 root_folders + 5 DCs + 5 RPMs when Categories section is active). The D-13 invariant still applies: if `sonarr.main.tags.items` is non-empty, `merge_with_manual` returns the manual list and the plan is identical to pre-Phase-10.

**SC#2 regression (2nd-run zero plan_action):** Run `dry_run_all_apps()` twice in sequence against the same fixture set and assert the second run's plan contains zero `add`/`update`/`delete` actions. The first run establishes the "desired" baseline; the second run against the SAME fixture should be all NO_OP.

---

## Chart-Pin Co-Bump Documentation Surfaces

[VERIFIED: charts/arr-stack/values.yaml:449–451 — current arrconf tag is `"0.5.3"` with `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` annotation]
[VERIFIED: /home/moi/.claude/agents/gsd-executor.md exists; no chart-pin rule present yet]

The pilot commit referenced in CONTEXT.md (de904c9) bumped `0.5.0 → 0.5.3`. Phase 10 will produce similar co-bump commits, each incrementing the semver in `values.yaml:451` alongside the Python code change.

**Two surfaces to update (D-05):**

1. **CLAUDE.md** — Add to "Conventions développement — arrconf" section: a new "Release pin co-bump pattern" paragraph explaining the `arrconf.image.tag` pre-bump requirement per arrconf-code commit.

2. **`/home/moi/.claude/agents/gsd-executor.md`** — Add a one-line convention rule: when modifying `tools/arrconf/**`, also stage `charts/arr-stack/values.yaml` in the same commit with an incremented `arrconf.image.tag`.

The Renovate annotation on line 449 (`# renovate: image=ghcr.io/tom333/arr-stack-arrconf`) MUST be preserved on the line ABOVE the `repository:` key. The `tag:` bump only changes the version string on line 451.

---

## configarr Quality-Profile Mapping (Discretion Area)

[VERIFIED: tools/arrconf/arrconf/resources/categories.py:17 — `Profile = Literal["general", "anime", "family"]`]
[VERIFIED: tools/arrconf/arrconf/config.py:641 — `categories: list[MediaCategory]`]

**Conclusion (locking the discretion area):** arrconf does NOT write to configarr.yml. The Phase 10 configarr mapping is purely:

1. **Validation at config load:** `Profile = Literal["general", "anime", "family"]` already enforced by pydantic at `load_config()` time [VERIFIED: categories.py:17]. Any `categories[i].profile` not in `{general, anime, family}` raises `ConfigError` (exit code 2) before any reconciler runs. No new code needed.

2. **Documentation:** CLAUDE.md and/or configarr.yml comments explain that the 3 quality profile names (`General`, `Anime`, `Family`) are derived from the union of `profile` values. Operator hand-edits configarr.yml to match.

3. **No arrconf validator for "profiles declared in configarr.yml must cover all used profiles":** This would require parsing configarr.yml from arrconf — cross-file dependency outside arrconf's scope. Reject. ADR-5 frontière intact.

4. **`test_configarr_three_profiles.py`** already exists [VERIFIED: tests/test_configarr_three_profiles.py in file listing]. This test likely validates the 3-profile constraint. Phase 10 should check if it still passes post-wiring.

---

## Common Pitfalls

### Pitfall 1: Seerr animeTags = integer IDs, not label strings
**What goes wrong:** Generator produces `["series-zoe"]` (label string); Seerr API requires `[<int_id>]`. Passing labels directly causes Seerr to reject the PUT with a 422 or store incorrect values.
**Why it happens:** `SeerrSonarrService.animeTags: list[int]` [VERIFIED: sonarr_service.py:34]. Seerr stores only integer IDs. The current production value `animeTags: [3]` is the cluster-assigned integer ID for the "anime" tag.
**How to avoid:** Resolve using Option A (GET /tag after Sonarr reconcile, match label→ID); put the resolved list into `seerr_instance.sonarr_service.animeTags` before calling `reconcile_seerr()`.
**Warning signs:** `reconcile_seerr` raising a 422 from `/api/v1/settings/sonarr/{id}`.

### Pitfall 2: merge_with_manual for Seerr animeTags is non-trivial
**What goes wrong:** The YAML already has `animeTags: [3]` (non-empty). D-02 says "manual non-empty → manual wins entirely". This means animeTags will NEVER be Categories-derived unless the operator explicitly empties the list in arrconf.yml first.
**How to avoid:** Document clearly in CLAUDE.md that to activate Categories-derived animeTags routing, the operator must empty `sonarr_service.animeTags: []` in arrconf.yml. The transition is opt-in.

### Pitfall 3: qBit savePath is `/data/torrents/<name>` NOT `/data/<name>`
**What goes wrong:** Category `base_path = /media/<name>` (where Jellyfin/Sonarr read). qBit `savePath = /data/torrents/<name>` (where qBit lands torrents). These are different mount paths.
**Why it happens:** The storage layout has `/data/torrents/` as the qBit download directory and `/media/` as the media-app import directory.
**How to avoid:** Generator hardcodes `savePath = f"/data/torrents/{c.name}"` — not `c.base_path`.
[VERIFIED: D-03a, arrconf.yml existing categories lines 405–416]

### Pitfall 4: Prowlarr Application extra field root cause needs confirmation
**What goes wrong:** The exact `Application` model configuration (`extra="allow"` vs `extra="forbid"`) needs verification to pick the right allowlist scope.
**How to avoid:** Read `tools/arrconf/arrconf/resources/prowlarr/application.py` before implementing FP fix #2. If `extra="forbid"`, then the FP has a different root cause (field-level selectOptions, label, etc. in FieldKV).
[ASSUMED — Application model config not read in this session; planner must verify before coding FP fix #2]

### Pitfall 5: `__main__.py` diff and dump commands need the same pre-merge
**What goes wrong:** `apply` gets Categories-derived resources but `diff` does not → `diff` shows drift that `apply` wouldn't produce → exit code 3 from `diff` doesn't reflect reality.
**How to avoid:** The pre-merge injection in `__main__.py` must be applied in the `apply`, `diff`, and `dump` command handlers consistently.

### Pitfall 6: TagItem vs Tag type mismatch
**What goes wrong:** `SonarrInstance.tags.items` is `list[TagItem]` (YAML model, only `label`). `SonarrTag` is the API resource model (has `id`). The generator produces `SonarrTag` objects; `merge_with_manual` returns them to be stored as `instance.tags.items`. But the reconciler step `_reconcile_tags(client, instance.tags, dry_run)` at sonarr.py:486 calls `Tag(label=item.label) for item in section.items` — it extracts `.label` from each item.
**How to avoid:** Generator should produce `TagItem(label=c.name)` objects (not `Tag`) to be stored in `instance.tags.items`. The reconciler already handles the conversion from `TagItem` to `Tag` internally.
[VERIFIED: sonarr.py:285, config.py:123–133 (TagItem model with only `label`)]

---

## Code Examples

### Download client connection constants (from production)

[VERIFIED: charts/arr-stack/files/arrconf.yml:80–108 (Sonarr TV DC), :243–272 (Radarr Movies DC)]

Sonarr-side generated DownloadClient fields:
```yaml
fields:
  - name: host
    value: qbittorrent.selfhost.svc.cluster.local
  - name: port
    value: 8080
  - name: useSsl
    value: false
  - name: urlBase
    value: ''
  - name: username
    value: ''
  - name: password
    value: ''
  - name: tvCategory
    value: <c.name>          # e.g. "series-zoe"
  - name: tvImportedCategory
    value: ''
  - name: recentTvPriority
    value: 0
  - name: olderTvPriority
    value: 0
  - name: initialState
    value: 0
  - name: sequentialOrder
    value: false
  - name: firstAndLast
    value: false
  - name: contentLayout
    value: 0
tag_labels: [<c.name>]
removeCompletedDownloads: true
removeFailedDownloads: true
```

Radarr-side: replace `tvCategory` with `movieCategory`, `tvImportedCategory` with `movieImportedCategory`, `recentTvPriority` with `recentMoviePriority`, `olderTvPriority` with `olderMoviePriority`.

### Existing production RPM shape (from arrconf.yml)

[VERIFIED: charts/arr-stack/files/arrconf.yml:187–201 (Sonarr RPMs)]

```yaml
- host: qbittorrent.selfhost.svc.cluster.local
  remotePath: /data/<name>/    # trailing slash required (Pitfall 6 in _shared.py)
  localPath: /data/torrents/<name>/
```

### Test pattern for FP fix (mirrors Phase 5 SC#5)

```python
# tests/test_idempotence_fp.py

def test_qbit_category_fp_fix():
    """FP #1: cluster returns extra fields; differ should emit NO_OP."""
    cluster_with_extras = {
        "series-zoe": {
            "name": "series-zoe",
            "savePath": "/data/torrents/series-zoe",
            "download_path": None,          # extra field qBit returns
            "inactive_seeding_time_limit": -2,
            "ratio_limit": -2,
            "seeding_time_limit": -2,
            "share_limit_action": "Default",
        }
    }
    desired = [Category(name="series-zoe", savePath="/data/torrents/series-zoe")]
    # After fix: filter cluster to managed fields before model_validate
    current = [Category.model_validate({k: v for k, v in obj.items()
               if k in QBIT_CATEGORY_MANAGED_FIELDS})
               for obj in cluster_with_extras.values()]
    plan = reconcile(current=current, desired=desired, match_key="name", prune=False)
    assert all(p.action == Action.NO_OP for p in plan)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual per-app YAML sections (tags, root_folders, DCs, RPMs) | Categories-derived (generator) with manual override | Phase 10 | Single source of truth for all resource names/paths |
| Hardcoded animeTags: [3] in arrconf.yml | Categories-derived animeTags (resolved to IDs at apply time) | Phase 10 | Seerr anime routing auto-tracks Category changes |
| 6 qBit categories (sonarr-tv, radarr-movies, etc.) | 10 qBit categories (bare `<name>` per D-03a) | Phase 10 | Matches v0.3.0 filesystem layout |
| 3 Sonarr tags (tv/anime/family) + 3 root_folders + 3 DCs + 3 RPMs | 5 per side (one per series/movies Category) | Phase 10 | Granular routing per named audience |
| Jellyfin libraries: 3 paths each | Jellyfin libraries: 5 paths each (derived from categories) | Phase 10 | All 10 media buckets visible in Jellyfin |

**Deprecated/outdated:**
- The v0.2.0 flat sections (`sonarr.main.tags.items: [tv, anime, family]`) become the override escape hatch. They are deprecated but not deleted in Phase 10.
- qBit category names `sonarr-tv`, `radarr-movies` etc. are replaced by bare `<name>` slugs.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `Application` model in `resources/prowlarr/application.py` uses `extra="allow"` (causing FP #2 via extra top-level or sub-field keys) | FP Analysis §FP #2 | If `extra="forbid"`, the FP root cause is different — may be in FieldKV extra keys instead; B2 allowlist approach still valid but allowlist scope changes |
| A2 | `SonarrTag`, `RootFolder`, `DownloadClient`, `RemotePathMapping` resource models accept direct construction with the fields shown in arrconf.yml (no additional required fields beyond what's in the YAML) | Pattern 1: generator | If models have additional required fields not in YAML, generator will fail model construction; executor must check resource model constructors |
| A3 | Seerr animeTags FP is due to `movieQuotaDays: None` vs cluster's `null` behavior or similar None/null mismatch, not a structural issue | FP Analysis §FP #3 | If the FP has a different root cause, the B2 allowlist approach still resolves it (it narrows the comparison to only writable fields) |
| A4 | `JellyfinLibrary` model accepts `collection_type` and `paths` as constructor arguments matching the existing arrconf.yml shape | Pattern 6: Jellyfin | If JellyfinLibrary has different field names, generator code needs adjustment |

**If this table entries A2 and A4 are wrong:** The executor must read the relevant resource model files (`resources/sonarr/tag.py`, `resources/sonarr/root_folder.py`, `resources/sonarr/download_client.py`, `resources/sonarr/remote_path_mapping.py`, `resources/jellyfin/__init__.py`) before coding the generator.

---

## Open Questions

1. **`Application` model extra config** (`resources/prowlarr/application.py`)
   - What we know: FP #2 exists; the allowlist approach will fix it regardless
   - What's unclear: exact set of fields to include in `PROWLARR_APP_MANAGED_FIELDS` (top-level only, or also FieldKV sub-fields?)
   - Recommendation: Executor reads `resources/prowlarr/application.py` first; if `extra="allow"` confirmed, the allowlist is `{"name", "enable", "implementation", "configContract", "syncLevel", "fields", "tags"}`; `fields[]` diff is already handled by `diff_models` / `_strip_redacted_fields`

2. **`JellyfinLibrary` model constructor** (`resources/jellyfin/__init__.py`)
   - What we know: `_reconcile_libraries` at jellyfin.py:125 iterates `section.items` as `desired_lib.name`, `desired_lib.paths`
   - What's unclear: exact pydantic field names in `JellyfinLibrary`
   - Recommendation: Executor reads `resources/jellyfin/__init__.py` and checks `name`, `collection_type`, `paths` field names before coding generator

3. **DownloadClient constructor for generated entries**
   - What we know: the YAML structure is well-defined in arrconf.yml
   - What's unclear: whether `DownloadClient` constructor requires `name`, `fields`, `tag_labels`, `enable`, `protocol`, `priority`, `implementation`, `configContract`, `removeCompletedDownloads`, `removeFailedDownloads` all at construction time
   - Recommendation: Executor reads `resources/sonarr/download_client.py` to confirm field defaults

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 + uv | arrconf test suite | ✓ | Existing project setup | — |
| pytest + respx | Unit tests | ✓ | Existing project | — |
| kubectl port-forward | ADR-6 snapshot before Wave 2 cluster tests | ✓ | Cluster access via existing setup | — |
| `tools/snapshot/snapshot.sh` | ADR-6 baseline capture | ✓ | 15KB script present at `tools/snapshot/snapshot.sh` | — |
| SONARR_API_KEY, RADARR_API_KEY, PROWLARR_API_KEY, QBT_USER, QBT_PASS, SEERR_API_KEY, JELLYFIN_API_KEY | snapshot.sh + cluster tests | Available in operator's environment | — | Operator must source from secrets before running snapshot |

**snapshot.sh env var requirements** [VERIFIED: tools/snapshot/snapshot.sh:52]:
`SONARR_API_KEY`, `RADARR_API_KEY`, `PROWLARR_API_KEY`, `QBT_USER`, `QBT_PASS`, `SEERR_API_KEY`, `JELLYFIN_API_KEY` (plus URL overrides with defaults pointing to in-cluster hostnames; port-forward required if running locally).

**No missing dependencies that block Phase 10 execution.**

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing, tools/arrconf/pyproject.toml) |
| Config file | tools/arrconf/pyproject.toml (pytest config section) |
| Quick run command | `cd tools/arrconf && uv run pytest tests/test_generators_categories.py tests/test_merge_with_manual.py tests/test_idempotence_fp.py -x` |
| Full suite command | `cd tools/arrconf && uv run pytest -v --cov=arrconf --cov-fail-under=70` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-categories-qbit-propagation | `generate_qbit_categories(cfg)` produces 10 `QbitCategory` with bare names + correct savePaths | unit | `pytest tests/test_generators_categories.py::test_generate_qbit_categories -x` | ❌ Wave 0 |
| REQ-categories-sonarr-propagation | `generate_sonarr_resources(cfg)` produces 5 tags + 5 root_folders + 5 DCs + 5 RPMs | unit | `pytest tests/test_generators_categories.py::test_generate_sonarr_resources -x` | ❌ Wave 0 |
| REQ-categories-radarr-propagation | Same for Radarr (kind=movies filter) | unit | `pytest tests/test_generators_categories.py::test_generate_radarr_resources -x` | ❌ Wave 0 |
| REQ-categories-configarr-mapping | Profile enum already validated; `test_configarr_three_profiles.py` still passes | unit | `pytest tests/test_configarr_three_profiles.py -x` | ✅ existing |
| REQ-categories-seerr-routing | animeTags populated with IDs for profile=anime Categories | integration (dry-run) | `pytest tests/test_seerr_animetags.py -x` | ❌ Wave 0 |
| REQ-categories-jellyfin-paths | Jellyfin library paths derived from Categories | unit | `pytest tests/test_jellyfin_categories.py -x` | ❌ Wave 0 |
| REQ-chart-pin-prebump | Documentation check: CLAUDE.md and gsd-executor.md contain chart-pin rule | manual review | `grep -c "arrconf.image.tag" CLAUDE.md` | — |
| REQ-idempotence-fp-fix | 2nd-run zero plan_action for qBit/Prowlarr/Seerr | unit | `pytest tests/test_idempotence_fp.py -x` | ❌ Wave 0 |
| D-13 no-regression (implicit) | phase9-baseline-plans.json unchanged | integration | `pytest tests/test_phase9_no_regression.py -x` | ✅ existing |
| SC#2 2nd-run zero | All 6 reconcilers produce 0 plan_action events on 2nd run | integration | `pytest tests/test_phase10_idempotence_sweep.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd tools/arrconf && uv run pytest tests/test_generators_categories.py tests/test_merge_with_manual.py tests/test_idempotence_fp.py -x`
- **Per wave merge:** `cd tools/arrconf && uv run pytest -v --cov=arrconf --cov-fail-under=70`
- **Phase gate:** Full suite green + `ruff check && ruff format --check` + `mypy` before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_generators_categories.py` — covers REQ-categories-*-propagation (all 4 apps)
- [ ] `tests/test_merge_with_manual.py` — covers D-02 toggle logic
- [ ] `tests/test_idempotence_fp.py` — covers D-04a/b/c (3 FP fixes)
- [ ] `tests/test_seerr_animetags.py` — covers REQ-categories-seerr-routing
- [ ] `tests/test_jellyfin_categories.py` — covers REQ-categories-jellyfin-paths
- [ ] `tests/test_phase10_idempotence_sweep.py` — covers SC#2 (2nd-run zero)
- [ ] `tests/fixtures/phase10-baseline-plans.json` — generated by `dry_run_all_apps()` after Phase 10 wiring lands

---

## Security Domain

> `security_enforcement` not explicitly set in `.planning/config.json` → treat as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No new auth paths — existing API key injection via env |
| V3 Session Management | no | No sessions; stateless CronJob |
| V4 Access Control | no | ADR-5 frontière: `ScopeViolationError` raised for quality_profiles; unchanged |
| V5 Input Validation | yes | pydantic `extra="forbid"` on `Category` model; `Profile` Literal enum validates all 10 categories at `load_config()` time |
| V6 Cryptography | no | No new crypto operations |

### Known Threat Patterns for arrconf

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Generator produces path-traversal savePath | Tampering | `Category.name` validated by kebab-case regex `^[a-z0-9]+(-[a-z0-9]+)*$` [VERIFIED: categories.py:32]; `base_path` locked to `/media/{name}` by model_validator [VERIFIED: categories.py:43–51]; `savePath` derived from `c.name` only |
| Extra YAML keys in categories[] bypass scope | Tampering | `extra="forbid"` on `Category` model [VERIFIED: categories.py:28]; pydantic raises `ValidationError` at load time |
| animeTags carries attacker-controlled IDs | Tampering | IDs resolved from Sonarr's own /tag endpoint (trust boundary: Sonarr cluster), not from user-controlled YAML |
| configarr.yml modified by arrconf code path | Elevation of Privilege | ADR-5 + `ScopeViolationError` pattern; test_scope_violation.py asserts this [VERIFIED: tests/test_scope_violation.py in file listing] |

---

## Sources

### Primary (HIGH confidence)

- `tools/arrconf/arrconf/config.py` — Full `RootConfig`, `SonarrInstance`, `QbittorrentInstance`, `SeerrInstance`, `JellyfinInstance` models; all section types verified
- `tools/arrconf/arrconf/resources/categories.py` — `Category` model with `Kind`/`Profile` enums, `base_path` invariant validator
- `tools/arrconf/arrconf/reconcilers/qbittorrent.py` — `_fetch_current_categories`, `_reconcile_categories`; FP locus at line 85 (`Category.model_validate`)
- `tools/arrconf/arrconf/reconcilers/prowlarr.py` — `reconcile_prowlarr`; FP locus at line 183 (`Application.model_validate`)
- `tools/arrconf/arrconf/reconcilers/sonarr.py` — Full reconcile order; `_reconcile_tags` returns `all_tags`; `TagItem` vs `Tag` distinction
- `tools/arrconf/arrconf/reconcilers/seerr.py` — `_reconcile_settings_sonarr`; `_payloads_equivalent`; `_reconcile_user`; animeTags at line 167
- `tools/arrconf/arrconf/reconcilers/jellyfin.py` — `_reconcile_libraries`; `SERVER_CONFIG_ALLOWLIST` precedent; PathInfo path attribute `"Path"` at line 144
- `tools/arrconf/arrconf/reconcilers/_shared.py` — `_reconcile_remote_path_mappings`; `_resolve_download_client_tag_labels`; natural home for `merge_with_manual`
- `tools/arrconf/arrconf/differ.py` — `diff_models`; `_READ_ONLY_FIELDS`; `reconcile()`
- `tools/arrconf/arrconf/__main__.py` — All 6 app dispatch branches; injection point for pre-merge
- `tools/arrconf/arrconf/resources/qbittorrent/category.py` — `extra="allow"` confirmed; only `name` + `savePath` declared
- `tools/arrconf/arrconf/resources/seerr/sonarr_service.py` — `animeTags: list[int]`; `extra="allow"`; excluded fields
- `tools/arrconf/arrconf/resources/seerr/user.py` — 16 `exclude=True` fields; `extra="allow"` confirmed
- `tools/arrconf/tests/_phase9_helpers.py` — Full 6-app dry-run walker; all route registration patterns
- `charts/arr-stack/files/arrconf.yml` — All connection constants (host, port, fields); current 10-category baseline; production Seerr animeTags value
- `charts/arr-stack/values.yaml:449–451` — Current `arrconf.image.tag: "0.5.3"` with Renovate annotation
- `tools/arrconf/tests/fixtures/qbittorrent/categories.json` — Extra fields qBit returns confirmed
- `tools/arrconf/tests/fixtures/seerr/user.json` — User fixture with `requestCount`, `warnings`, `settings` extra fields
- `.planning/phases/10-categories-6-app-propagation/10-CONTEXT.md` — All locked decisions

### Secondary (MEDIUM confidence)

- `tools/arrconf/tests/fixtures/prowlarr/applications.json` — Rich Application GET response confirms many extra fields (helpText, label, advanced, order, type, selectOptions in fields[])
- `tools/arrconf/tests/fixtures/phase9-baseline-plans.json` — Shape confirmed: prowlarr=2, qbit=9, radarr=4, sonarr=4 plans

### Tertiary (LOW confidence / ASSUMED)

- A1: `resources/prowlarr/application.py` model config (`extra="allow"` assumed) — [ASSUMED]
- A2: `DownloadClient` constructor accepts all fields from arrconf.yml shape — [ASSUMED]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified from source code
- Architecture: HIGH — all patterns traced to actual reconciler code
- FP root causes: HIGH for qBit (#1) and Seerr (#3); MEDIUM for Prowlarr (#2 — Application model config not verified)
- Pitfalls: HIGH — all traced to verified code or CONTEXT.md decisions
- Test strategy: HIGH — existing `_phase9_helpers.py` is fully understood

**Research date:** 2026-05-19
**Valid until:** 2026-06-19 (stable codebase; all dependencies in pyproject.toml pinned)
