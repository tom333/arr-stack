# Phase 10: Categories → 6-app propagation - Pattern Map

**Mapped:** 2026-05-19
**Files analyzed:** 17 new/modified files
**Analogs found:** 17 / 17

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tools/arrconf/arrconf/generators/__init__.py` | utility/init | — | any `arrconf/resources/__init__.py` | exact (empty re-export) |
| `tools/arrconf/arrconf/generators/categories.py` | generator/utility | transform (cfg → resource lists) | `tools/arrconf/arrconf/differ.py` | role-match (pure functions over pydantic models) |
| `tools/arrconf/arrconf/reconcilers/_shared.py` (extend) | utility | transform | `tools/arrconf/arrconf/reconcilers/_shared.py` itself | exact (same file, additive) |
| `tools/arrconf/arrconf/__main__.py` (extend) | entrypoint | request-response | `tools/arrconf/arrconf/__main__.py` itself | exact |
| `tools/arrconf/arrconf/reconcilers/qbittorrent.py` (extend) | reconciler | CRUD + transform | `tools/arrconf/arrconf/reconcilers/qbittorrent.py` itself | exact |
| `tools/arrconf/arrconf/reconcilers/sonarr.py` (extend) | reconciler | CRUD | `tools/arrconf/arrconf/reconcilers/sonarr.py` itself | exact |
| `tools/arrconf/arrconf/reconcilers/radarr.py` (extend) | reconciler | CRUD | `tools/arrconf/arrconf/reconcilers/radarr.py` itself | exact |
| `tools/arrconf/arrconf/reconcilers/seerr.py` (extend) | reconciler | CRUD + transform | `tools/arrconf/arrconf/reconcilers/seerr.py` itself | exact |
| `tools/arrconf/arrconf/reconcilers/jellyfin.py` (extend) | reconciler | CRUD | `tools/arrconf/arrconf/reconcilers/jellyfin.py` itself | exact |
| `tools/arrconf/arrconf/reconcilers/prowlarr.py` (extend) | reconciler | CRUD | `tools/arrconf/arrconf/reconcilers/prowlarr.py` + jellyfin.py | role-match (FP fix only) |
| `tools/arrconf/tests/test_generators_categories.py` | test | transform | `tools/arrconf/tests/test_categories.py` | role-match |
| `tools/arrconf/tests/test_merge_with_manual.py` | test | transform | `tools/arrconf/tests/test_differ.py` | role-match |
| `tools/arrconf/tests/test_idempotence_fp.py` | test | CRUD no-op | `tools/arrconf/tests/test_reconcilers_qbittorrent.py` (SC#5) | role-match |
| `tools/arrconf/tests/test_seerr_animetags.py` | test | CRUD | `tools/arrconf/tests/test_reconcilers_seerr.py` | role-match |
| `tools/arrconf/tests/test_jellyfin_categories.py` | test | CRUD | `tools/arrconf/tests/test_reconcilers_jellyfin.py` | role-match |
| `tools/arrconf/tests/test_phase10_idempotence_sweep.py` | test | multi-app sweep | `tools/arrconf/tests/test_phase9_no_regression.py` | exact |
| `tools/arrconf/tests/_arrconf_helpers.py` | test utility | multi-app dry-run | `tools/arrconf/tests/_phase9_helpers.py` | exact (rename+generalize) |
| `charts/arr-stack/values.yaml` (tag bump only) | config | — | `charts/arr-stack/values.yaml` lines 449-451 | exact |
| `CLAUDE.md` (doc extension) | doc | — | `CLAUDE.md` "Conventions développement" section | exact (additive) |
| `/home/moi/.claude/agents/gsd-executor.md` (1-line rule) | doc | — | existing conventions block | additive |
| `.planning/REQUIREMENTS.md` (wording fix) | doc | — | existing REQ-categories-qbit-propagation entry | additive |

---

## Pattern Assignments

### `tools/arrconf/arrconf/generators/categories.py` (generator, transform)

**Analog:** `tools/arrconf/arrconf/differ.py` — pure functions over pydantic models, no I/O

**Imports pattern** (`differ.py` lines 1-18):
```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import structlog
from pydantic import BaseModel

log = structlog.get_logger()
```

**Module-level dataclass container pattern** (mirror `differ.py` `PlannedAction` dataclass, lines 62-70):
```python
@dataclass
class PlannedAction[T: BaseModel]:
    """A single planned reconciliation step."""
    action: Action
    name: str
    current: T | None
    desired: T | None
    diff_fields: list[str]
```
For Phase 10 generators, the analogous containers are `SonarrDerived` / `RadarrDerived` dataclasses — same `@dataclass` + typed fields pattern. No `field(default_factory=list)` needed (always fully populated by the generator).

**Pure-function body pattern** (mirror `differ.py` `reconcile()` lines 237-286):
```python
def reconcile[T: BaseModel](
    current: list[T],
    desired: list[T],
    *,
    match_key: str = "name",
    prune: bool = False,
    managed_tag_id: int | None = None,
) -> list[PlannedAction[T]]:
    """Run the generic reconcile algorithm."""
    # ... pure data transformation, no I/O, no client calls
```
The generator follows the same contract: accept typed inputs from `RootConfig`, return typed outputs, no I/O. Use `from __future__ import annotations` at top.

**Import pattern from config** (`config.py` lines 18-22):
```python
from arrconf.resources.categories import Category as MediaCategory
from arrconf.resources.qbittorrent.category import Category
from arrconf.resources.sonarr.download_client import DownloadClient
from arrconf.resources.sonarr.remote_path_mapping import RemotePathMapping
from arrconf.resources.sonarr.root_folder import RootFolder
```
The generator imports: `RootConfig` from `arrconf.config`, `Category as MediaCategory` from `arrconf.resources.categories`, and each resource model from its resource subpackage. `TYPE_CHECKING` guard for `RootConfig` is fine (it's a pure input type).

**Key invariant: qBit savePath vs base_path** (confirmed via `resources/qbittorrent/category.py` + RESEARCH.md Pitfall 3):
- `QbitCategory.savePath = f"/data/torrents/{c.name}"` — NOT `c.base_path` (`/media/<name>`)
- `c.base_path` is used for Sonarr/Radarr `root_folder.path` and Jellyfin `library.paths`

**Key invariant: TagItem not Tag** (confirmed via `config.py` lines 123-132, `sonarr.py` line 285):
```python
class TagItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(description="Tag label (e.g. 'tv', 'anime', 'family').")
```
Generator must produce `TagItem(label=c.name)` objects for `instance.tags.items`, NOT `Tag` objects (which carry a server-assigned `id`). The reconciler extracts `.label` from `TagItem` at `sonarr.py:285`.

---

### `tools/arrconf/arrconf/reconcilers/_shared.py` — `merge_with_manual()` addition

**Analog:** `_shared.py` lines 103-145 (`_resolve_download_client_tag_labels`) — same module, same cross-reconciler helper style

**Existing helper pattern** (`_shared.py` lines 103-145):
```python
def _resolve_download_client_tag_labels(
    items: list[Any],
    all_tags: list[Tag],
    app_name: str = "Sonarr/Radarr",
) -> list[Any]:
    """Resolve label-based tags in DownloadClient.tag_labels to integer IDs.
    ...
    Shared between Sonarr and Radarr — byte-equivalent implementation (PATTERNS
    line 391). The ``app_name`` parameter is used only in the error message for
    operator-facing clarity.
    """
    label_to_id: dict[str, int] = {}
    for t in all_tags:
        if t.id is not None:
            label_to_id[t.label] = t.id
    ...
```

**New `merge_with_manual()` follows identical shape:**
- Module-level `log = structlog.get_logger()` already present at line 24
- `structlog` already imported at line 15
- Returns a plain `list[Any]` (same as existing helpers)
- Docstring explains D-02 contract, references CONTEXT.md decision
- Log event key: `"merge_decision"` with structured fields `app=`, `resource=`, `source=`, `n=`, `generated_skipped=` (optional)

**Structlog pattern from existing code** (`_shared.py` lines 66-70):
```python
log.info("dry_run_skip", action="add", resource="rpm", key=str(k))
```
Mirror exact key style for `merge_decision`:
```python
log.info("merge_decision", app=app, resource=resource, source="categories", n=len(generated_items))
```

---

### `tools/arrconf/arrconf/__main__.py` — pre-merge injection point

**Analog:** `__main__.py` itself, Sonarr branch lines 122-143

**Existing per-app branch pattern** (lines 122-143):
```python
if "sonarr" in targets and "main" in root.sonarr:
    instance = root.sonarr["main"]
    if not settings.sonarr_api_key:
        log.error("missing_api_key", app="sonarr", env_var="SONARR_API_KEY")
        raise typer.Exit(code=2)
    api_key = settings.sonarr_api_key.get_secret_value()
    try:
        client = SonarrClient(base_url=instance.base_url, api_key=api_key)
        result = reconcile_sonarr(client, instance, dry_run=dry_run or settings.arrconf_dry_run)
        ...
    except (ApiClientError, ReconcileError) as e:
        log.error("app_failed", app="sonarr", error=str(e))
        failures.append("sonarr")
```

**Injection point** — between `instance = root.sonarr["main"]` and `client = SonarrClient(...)`:
```python
# Phase 10 pre-merge (D-01/D-02): mutate instance sections in-place before reconciler call
from arrconf.generators.categories import generate_sonarr_resources  # noqa: PLC0415
from arrconf.reconcilers._shared import merge_with_manual  # noqa: PLC0415
derived = generate_sonarr_resources(root)
instance.tags.items = merge_with_manual(
    instance.tags.items, [TagItem(label=t.label) for t in derived.tags],
    app="sonarr", resource="tags",
)
```
The `noqa: PLC0415` comment is already the convention for lazy imports inside command handlers (see lines 212-214 for the qBittorrent lazy-import pattern). For Phase 10, generators can be eager top-level imports (no stub risk) — no `noqa` needed unless planner prefers lazy.

**Apply to all three commands** (`apply`, `diff`, `dump`) — Pitfall 5 from RESEARCH.md: same pre-merge must happen in all three handlers or `diff` will show false drift.

**Seerr animeTags special case** — after `reconcile_sonarr()` returns, BEFORE `reconcile_seerr()`:
```python
# Resolve anime label→ID from post-reconcile Sonarr tag list
sonarr_all_tags = client.get("/api/v3/tag")  # second GET, idempotent + cheap
anime_labels = generate_anime_tag_labels(root)
seerr_instance.sonarr_service.animeTags = [
    t["id"] for t in sonarr_all_tags if t["label"] in anime_labels
]
```
Apply `merge_with_manual` toggle: if `seerr_instance.sonarr_service.animeTags` was non-empty in YAML, skip the override (manual wins per D-02).

---

### `tools/arrconf/arrconf/reconcilers/qbittorrent.py` — FP fix #1 + categories wiring

**Analog:** `jellyfin.py` lines 56-103 (`SERVER_CONFIG_ALLOWLIST` + `_server_config_equivalent`)

**B2 allowlist pattern** (`jellyfin.py` lines 56-67):
```python
# The 7 PascalCase keys in /System/Configuration that arrconf manages (D-07-CONFIG-01).
SERVER_CONFIG_ALLOWLIST: tuple[str, ...] = (
    "UICulture",
    "MetadataCountryCode",
    "PreferredMetadataLanguage",
    "ActivityLogRetentionDays",
    "LogFileRetentionDays",
    "ServerName",
    "PluginRepositories",
)

# Pitfall 5 — non-actionable plugin states (Active or Restart-pending = no-op).
_ACTIVE_PLUGIN_STATUSES: frozenset[str] = frozenset({"Active", "Restart"})
```

**For qBit FP fix** — add adjacent to `_fetch_current_categories` (after `REMOVE_CATEGORIES_PATH` constant, before line 76):
```python
# B2 allowlist: fields arrconf manages on qBit Category (D-04b, FP fix #1).
# extra="allow" on Category means GET returns download_path, ratio_limit etc.
# Filter to managed fields BEFORE model_validate to prevent spurious UPDATEs.
QBIT_CATEGORY_MANAGED_FIELDS: frozenset[str] = frozenset({"name", "savePath"})
```

**Fix location** — `_fetch_current_categories` (`qbittorrent.py` lines 76-85):
```python
def _fetch_current_categories(client: QbittorrentClient) -> list[Category]:
    raw = client.get(CATEGORIES_PATH)
    return [Category.model_validate(v) for v in raw.values()]
    # BECOMES:
    return [
        Category.model_validate({k: v for k, v in obj.items() if k in QBIT_CATEGORY_MANAGED_FIELDS})
        for obj in raw.values()
    ]
```

**Categories wiring in `reconcile_qbittorrent`** — pre-merge happens in `__main__.py` before the call. The reconciler itself at `qbittorrent.py` receives already-merged `instance.categories.items`. No change to `reconcile_qbittorrent` signature.

---

### `tools/arrconf/arrconf/reconcilers/sonarr.py` + `radarr.py` — generator wiring

**Analog:** Existing sonarr resource reconcile steps (`sonarr.py` lines 270-301 for `_reconcile_tags`):
```python
def _reconcile_tags(
    client: SonarrClient,
    section: TagsSection,
    dry_run: bool,
) -> list[Tag]:
    raw_current = client.get(TAG_PATH)
    desired_tags = [Tag(label=item.label) for item in section.items]
    _reconcile_list_resource(
        client, TAG_PATH, raw_current, Tag, desired_tags,
        match_key="label", prune=section.prune, managed_tag_id=None, dry_run=dry_run,
    )
    raw_after = client.get(TAG_PATH)
    return [Tag.model_validate(t) for t in raw_after]
```

No signature change needed. Phase 10 wiring is entirely in `__main__.py` pre-merge. The reconciler receives `instance` with `tags.items`, `root_folders.items`, `download_clients.items`, `remote_path_mappings.items` already merged (Categories-derived or manual, depending on D-02 toggle).

Radarr is byte-equivalent to Sonarr for Phase 10 wiring (same pattern, same 4 resource types, different `kind` filter in generator: `kind == "movies"` instead of `kind == "series"`).

---

### `tools/arrconf/arrconf/reconcilers/seerr.py` — animeTags + FP fix #3

**Analog:** `seerr.py` lines 97-105 (`_payloads_equivalent`) + lines 108-168 (`_reconcile_settings_sonarr`)

**Existing idempotence diff pattern** (`seerr.py` lines 97-105):
```python
def _payloads_equivalent(current: dict[str, Any], desired: dict[str, Any]) -> bool:
    """Idempotence diff: True iff `current` matches `desired` on every key in `desired`.

    Extra keys in `current` (e.g. server-computed activeProfileName,
    server-managed timestamps) are IGNORED — we only care that the desired
    subset is already satisfied.
    """
    return all(current.get(k) == v for k, v in desired.items())
```

**FP fix #3 — Seerr user allowlist** — add before `_reconcile_admin_user` (wherever it lives in seerr.py):
```python
# B2 allowlist: writable fields on SeerrUser (D-04b, FP fix #3).
# extra="allow" on SeerrUser means GET returns server-managed fields not in model_dump().
# Filter current dict BEFORE _payloads_equivalent to avoid spurious UPDATEs.
SEERR_USER_MANAGED_FIELDS: frozenset[str] = frozenset({
    "displayName", "permissions",
    "movieQuotaDays", "movieQuotaLimit",
    "tvQuotaDays", "tvQuotaLimit",
})
```

Usage at the comparison call site (mirrors Jellyfin's `_server_config_equivalent` pattern):
```python
cluster_filtered = {k: v for k, v in admin_current.items() if k in SEERR_USER_MANAGED_FIELDS}
if _payloads_equivalent(cluster_filtered, put_body):
    log.info("user_no_op")
    return []
```

**animeTags wiring** — `animeTags` is populated in `__main__.py` before `reconcile_seerr()` call (Option A from RESEARCH.md §Pattern 5). The `_reconcile_settings_sonarr` function at `seerr.py:108` is already the callsite that consumes `desired_section.animeTags` — no signature change needed there. The operator empties `sonarr_service.animeTags: []` in arrconf.yml to activate Categories-derived routing (merge_with_manual toggle per D-02).

---

### `tools/arrconf/arrconf/reconcilers/jellyfin.py` — PathInfos wiring

**Analog:** `jellyfin.py` lines 106-176 (`_reconcile_libraries`) — same function being extended

**Existing library idempotence shim** (`jellyfin.py` lines 141-149):
```python
# Pitfall 8: PathInfos is the source of truth, NEVER Locations (stale display projection).
library_options = cluster_lib.get("LibraryOptions") or {}
path_infos = library_options.get("PathInfos") or []
existing_paths: set[str] = {p.get("Path") for p in path_infos if p.get("Path")}

for path in desired_lib.paths:
    if path in existing_paths:
        log.info("library_path_already_present", name=desired_lib.name, path=path)
        continue  # Pitfall 2 idempotence shim — no-op for already-present paths
```

No change needed to `_reconcile_libraries` itself. Phase 10 wiring happens in `__main__.py`: pre-merge replaces `jellyfin_instance.libraries.items` with the 2 Categories-derived `JellyfinLibrary` objects (or leaves the manual items in place per D-02 toggle). The existing set-membership idempotence shim handles the `existing_paths` check correctly for both manual and Categories-derived paths.

**SERVER_CONFIG_ALLOWLIST shape** (lines 56-64) is the canonical B2 allowlist precedent:
```python
SERVER_CONFIG_ALLOWLIST: tuple[str, ...] = (
    "UICulture",
    ...
    "PluginRepositories",
)
```
The `frozenset[str]` variant (used for FP fixes #1-#3) is a minor variation — `frozenset` supports O(1) `in` checks, `tuple` does not matter for 7 entries. Use `frozenset[str]` for the FP allowlists (consistent with `_ACTIVE_PLUGIN_STATUSES: frozenset[str]` at line 67).

---

### `tools/arrconf/arrconf/reconcilers/prowlarr.py` — FP fix #2

**Analog:** `jellyfin.py` `SERVER_CONFIG_ALLOWLIST` pattern (lines 56-67) + `prowlarr.py` lines 182-193

**Existing Prowlarr reconcile callsite** (`prowlarr.py` lines 175-194):
```python
desired_apps: list[Application] = [
    _build_desired_application(entry, prowlarr_base_url=instance.base_url)
    for entry in instance.apps.items
]

raw_current = client.get(APPLICATIONS_PATH)
current_apps = [Application.model_validate(x) for x in raw_current]

plan = reconcile(
    current=current_apps,
    desired=desired_apps,
    match_key="name",
    prune=instance.apps.prune,
    managed_tag_id=None,
)
```

**FP fix #2 pattern** — before `Application.model_validate(x)`, filter `x` to managed top-level keys:
```python
PROWLARR_APP_MANAGED_FIELDS: frozenset[str] = frozenset({
    "name", "enable", "implementation", "configContract",
    "syncLevel", "fields", "tags",
})

# Line 183 becomes:
current_apps = [
    Application.model_validate({k: v for k, v in x.items() if k in PROWLARR_APP_MANAGED_FIELDS})
    for x in raw_current
]
```

**Executor note:** Verify `resources/prowlarr/application.py` model config (`extra="allow"` vs `extra="forbid"`) before implementing — RESEARCH.md Pitfall 4 flags this as unconfirmed. If `extra="forbid"`, the FP has a different root cause (nested `fields[]` FieldKV subobject extra keys) and the fix may need to be on `FieldKV.model_validate()` instead.

---

## Shared Patterns

### B2 Allowlist (FP fixes #1, #2, #3)
**Source:** `tools/arrconf/arrconf/reconcilers/jellyfin.py` lines 56-67 (`SERVER_CONFIG_ALLOWLIST`)
**Apply to:** `qbittorrent.py` (FP #1), `prowlarr.py` (FP #2), `seerr.py` (FP #3)

Pattern: module-level `frozenset[str]` constant named `<APP>_<RESOURCE>_MANAGED_FIELDS`, placed adjacent to the reconcile function that uses it. Filter cluster GET dict to the allowlist BEFORE `Model.model_validate()` (for FP #1 and #2) or BEFORE `_payloads_equivalent()` (for FP #3).

```python
QBIT_CATEGORY_MANAGED_FIELDS: frozenset[str] = frozenset({"name", "savePath"})

# Usage:
current = [
    Category.model_validate({k: v for k, v in obj.items() if k in QBIT_CATEGORY_MANAGED_FIELDS})
    for obj in raw.values()
]
```

### Structlog merge_decision event
**Source:** `tools/arrconf/arrconf/reconcilers/_shared.py` lines 15-24 (logger setup)
**Apply to:** all `merge_with_manual()` callsites (in `_shared.py` itself)

```python
log = structlog.get_logger()  # already at _shared.py:24

# New merge_decision event shape (D-02 requirement):
log.info("merge_decision", app=app, resource=resource, source="categories", n=len(generated_items))
# or:
log.info("merge_decision", app=app, resource=resource, source="manual",
         n=len(manual_items), generated_skipped=len(generated_items))
```

### Cross-reconciler helper module style
**Source:** `tools/arrconf/arrconf/reconcilers/_shared.py` (entire file, 146 lines)
**Apply to:** `merge_with_manual()` new function in same file

Docstring convention (lines 30-52): start with the D-XX decision reference, explain the contract, note "Shared between X and Y — byte-equivalent implementation (PATTERNS line N)." For `merge_with_manual()`, say "Shared across all 6 reconciler pre-merge callsites (D-02)."

### Per-app dispatch branch in `__main__.py`
**Source:** `tools/arrconf/arrconf/__main__.py` lines 122-143 (Sonarr branch)
**Apply to:** all 6 app branches for pre-merge injection

Injection slot: after `instance = root.<app>["main"]`, before `client = <App>Client(...)`. No exception handling changes needed — `merge_with_manual()` is pure Python and cannot raise `ApiClientError`.

### Test file structure
**Source:** `tools/arrconf/tests/test_reconcilers_qbittorrent.py` lines 1-60
**Apply to:** all new `test_*.py` files

```python
"""<description> — Phase 10 scope.

Key invariants verified:
- ...
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from arrconf.<module> import <function>

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "<app>"
```

---

## Test-Specific Pattern Assignments

### `tools/arrconf/tests/test_generators_categories.py`

**Analog:** `tools/arrconf/tests/test_categories.py` (pydantic model unit tests, no HTTP)

No respx needed — generator is pure Python. Test pattern:
```python
def test_generate_qbit_categories_10_entries():
    cfg = RootConfig(categories=[...])  # 10 Category objects
    result = generate_qbit_categories(cfg)
    assert len(result) == 10
    assert result[0].name == "series"
    assert result[0].savePath == "/data/torrents/series"

def test_generate_sonarr_resources_5_series():
    cfg = RootConfig(categories=[...])  # 5 series + 5 movies
    result = generate_sonarr_resources(cfg)
    assert len(result.tags) == 5
    assert len(result.root_folders) == 5
    assert len(result.download_clients) == 5
    assert len(result.remote_path_mappings) == 5
```

### `tools/arrconf/tests/test_merge_with_manual.py`

**Analog:** `tools/arrconf/tests/test_differ.py` (unit tests for pure diff function)

Three cases per D-02 contract:
1. Manual non-empty → returns manual items unchanged, logs `source=manual`
2. Manual empty → returns generated items, logs `source=categories`
3. Both empty → returns empty list (edge case)

### `tools/arrconf/tests/test_idempotence_fp.py`

**Analog:** `tools/arrconf/tests/test_reconcilers_qbittorrent.py` SC#5 invariant (lines 1-14 + SC#5 comment)

Test structure per FP (3 tests total):
```python
def test_qbit_category_fp_fix():
    """FP #1: cluster returns extra fields; differ should emit NO_OP."""
    cluster_with_extras = {
        "series-zoe": {
            "name": "series-zoe",
            "savePath": "/data/torrents/series-zoe",
            "download_path": None,      # extra field from qBit 5.1+
            "ratio_limit": -2,
            "seeding_time_limit": -2,
        }
    }
    # Mock GET /torrents/categories to return cluster_with_extras
    # Mock any PUT/POST to fail (should not be called)
    # Assert plan has all NO_OP entries
```

### `tools/arrconf/tests/test_phase10_idempotence_sweep.py` (SC#2 regression)

**Analog:** `tools/arrconf/tests/test_phase9_no_regression.py` (lines 1-60, entire structure)

```python
"""SC#2 dispositive pytest: Phase 10 2nd-run idempotence sweep.

Strategy:
  1. Load arrconf.yml (with Categories populated, flat sections still present).
  2. Run dry_run_all_apps(cfg) once → baseline plans (first run).
  3. Feed first-run output back as the "cluster state" fixtures.
  4. Run dry_run_all_apps(cfg) again → assert all actions are NO_OP.

Passes iff second run emits 0 plan_action events across all 6 apps.
"""
from tests._arrconf_helpers import dry_run_all_apps  # renamed from _phase9_helpers
```

### `tools/arrconf/tests/_arrconf_helpers.py`

**Analog:** `tools/arrconf/tests/_phase9_helpers.py` (full file — exact copy renamed)

The rename is additive. Keep `_phase9_helpers.py` as-is for backward compatibility (test_phase9_no_regression.py imports from it). `_arrconf_helpers.py` is a generalization that accepts an optional `fixture_set` parameter or a config-driven fixture loader. Mirror `dry_run_all_apps()` signature: `(cfg: RootConfig) -> dict[str, Any]`.

The respx route registration helpers (`_register_sonarr_routes`, `_register_qbittorrent_routes`, etc.) at lines 217-390 are the main extension points for Phase 10 — new fixtures for 5-tag / 5-rootfolder era replace the 3-tag era fixtures.

---

## Chart-Pin Co-Bump Pattern

### `charts/arr-stack/values.yaml` lines 449-451

**Analog:** git commit de904c9 (Phase 9-D pilot: `0.5.0 → 0.5.3` co-bump)

Current tag location:
```yaml
          image:
            # renovate: image=ghcr.io/tom333/arr-stack-arrconf   # line 449 — MUST NOT be removed
            repository: ghcr.io/tom333/arr-stack-arrconf          # line 450
            tag: "0.5.3"                                          # line 451 — bump target
```

Rule (D-05): when any `tools/arrconf/**` file is modified in a commit, also stage `values.yaml` line 451 with the incremented semver. The auto-tag chain in `chart-lint.yml` creates the matching git tag post-merge.

### `CLAUDE.md` — new "Release pin co-bump pattern" section

**Analog:** existing "Release" section in CLAUDE.md (~lines under "Workflow de développement")

Add as a new `###` subsection under "Conventions développement — arrconf":

Content formula: "Whenever a reconciler or arrconf-code change ships, bump `charts/arr-stack/values.yaml#arrconf.image.tag` to the expected new semver in the SAME commit. The post-merge auto-tag chain (`chart-lint.yml`) produces a chart whose pinned image matches the auto-created tag → 1 `my-kluster` `targetRevision` bump per phase (closes D-07-CHART-PIN-LOOP). Pilot: commit `de904c9` bumped `0.5.0 → 0.5.3`."

### `/home/moi/.claude/agents/gsd-executor.md` — one-line convention injection

**Analog:** existing conventions block in `gsd-executor.md` (check the file for the exact section heading before inserting)

One-line rule to inject: "When modifying `tools/arrconf/**`, also stage `charts/arr-stack/values.yaml` `arrconf.image.tag` (line ~451) incremented by one patch version in the same commit. See CLAUDE.md 'Release pin co-bump pattern'."

---

## No Analog Found

All files have close analogs. No entries in this section.

---

## Files With No Structural Change (doc/config only)

| File | Change Type | Source of Truth |
|------|-------------|-----------------|
| `.planning/REQUIREMENTS.md` | 1-line wording fix: `"<kind>-<name>"` → `"<name>"` in REQ-categories-qbit-propagation | D-03a (CONTEXT.md) |
| `tools/arrconf/tests/fixtures/phase10-baseline-plans.json` | Generated artifact | run `dry_run_all_apps(cfg)` post-Phase-10-wiring |

---

## Metadata

**Analog search scope:** `tools/arrconf/arrconf/`, `tools/arrconf/tests/`, `charts/arr-stack/`, `/home/moi/.claude/agents/`
**Files scanned:** 12 source files read directly
**Pattern extraction date:** 2026-05-19

**Critical B2 vs B1 verdict:** Use B2 (explicit `frozenset[str]` allowlist) for all 3 FP fixes. All 3 affected models (`qbittorrent/category.py:20`, `seerr/user.py:17`, prowlarr Application — verify) use `extra="allow"`. `Model.model_fields.keys()` (B1) does NOT capture keys stored via `extra="allow"` — those extra keys are the FP source. B2 is the Jellyfin-proven precedent.

**TagItem vs Tag pitfall:** Generator produces `TagItem(label=c.name)` (config model), NOT `Tag` (resource model with `id`). Reconciler's `_reconcile_tags()` at `sonarr.py:285` does `Tag(label=item.label) for item in section.items` — it handles the conversion internally.

**Seerr animeTags exception to pre-merge-in-caller rule:** animeTags requires post-Sonarr-reconcile integer IDs. Resolve in `__main__.py` AFTER `reconcile_sonarr()` returns, BEFORE `reconcile_seerr()` is called, by issuing a second `GET /tag` on the Sonarr client.
