---
phase: 16-jellyfin-categories-as-libs
plan: A
type: execute
wave: 1
depends_on: []
autonomous: false
requirements:
  - REQ-jellyfin-categories-as-libs
files_modified:
  - snapshots/before-phase-16-2026-05-24/jellyfin/
  - tools/arrconf/arrconf/generators/categories.py
  - tools/arrconf/arrconf/reconcilers/jellyfin.py
  - tools/arrconf/arrconf/config.py
  - tools/arrconf/tests/test_jellyfin_categories.py
  - tools/arrconf/tests/test_reconcilers_jellyfin.py
  - tools/arrconf/tests/fixtures/jellyfin/library_virtualfolders_post_phase16.json
  - schemas/arrconf-schema.json
  - charts/arr-stack/values.yaml
  - .planning/phases/16-jellyfin-categories-as-libs/16-HUMAN-UAT.md
tags:
  - jellyfin
  - reconciler
  - categories
  - generator
must_haves:
  truths:
    - "`generate_jellyfin_libraries(cfg)` returns exactly 10 `JellyfinLibrary` entries for the 10-category production fixture (1 per `categories[]`)."
    - "Each generated library has `name == categories[i].display`, `collection_type` mapped from `kind` (`series → tvshows`, `movies → movies`), and `paths == [categories[i].base_path]` (single PathInfo per lib)."
    - "`_reconcile_libraries()` POSTs `/Library/VirtualFolders` ONLY when the desired lib's `name` is NOT in the pre-fetched cluster snapshot (Pitfall 16-1 guard) — re-running the reconciler against a post-cutover cluster emits 0 `library_created` actions."
    - "When `section.prune == True`, the reconciler DELETEs PathInfos present in cluster but not in desired set, and DELETEs cluster libs not in desired set; `NotFoundError` on lib DELETE is caught and logged as `library_already_absent` (Pitfall 16-2)."
    - "When `section.prune == False` (default), the reconciler NEVER calls DELETE on either `/Library/VirtualFolders` or `/Library/VirtualFolders/Paths`."
    - "Live Jellyfin web UI on `https://jellyfin.tgu.ovh/` shows 10 top-level libraries (1 per Category) post-cutover."
    - "Operator can flip `jellyfin.libraries.prune: true → false` in a follow-up PR and the reconciler converges to a no-op."
  artifacts:
    - path: "snapshots/before-phase-16-2026-05-24/jellyfin/"
      provides: "ADR-6 pre-cutover baseline (Jellyfin libs + system config) captured BEFORE any code merge"
    - path: "tools/arrconf/arrconf/generators/categories.py"
      provides: "Refactored `generate_jellyfin_libraries()` — returns 10 libs (1/Category) instead of 2 super-libs"
      contains: "_KIND_TO_COLLECTION_TYPE"
    - path: "tools/arrconf/arrconf/reconcilers/jellyfin.py"
      provides: "Extended `_reconcile_libraries()` + `_create_library()` + `_prune_library_paths()` + `_prune_libraries()`"
      contains: "_create_library"
    - path: "tools/arrconf/arrconf/config.py"
      provides: "Updated `JellyfinLibrariesSection.prune` docstring (D-07-LIB-01 reversed → D-16-PRUNE-01)"
    - path: "tools/arrconf/tests/test_jellyfin_categories.py"
      provides: "Rewritten generator tests covering 10-lib emission (5 tvshows + 5 movies, names match `display`)"
    - path: "tools/arrconf/tests/test_reconcilers_jellyfin.py"
      provides: "8 new reconciler tests covering CREATE, idempotence shim, prune-gated DELETE Path / DELETE Lib, 404 tolerance, dry_run"
    - path: "tools/arrconf/tests/fixtures/jellyfin/library_virtualfolders_post_phase16.json"
      provides: "10-lib post-cutover GET fixture for prune & idempotence tests"
    - path: "schemas/arrconf-schema.json"
      provides: "Regenerated JSON schema after JellyfinLibrariesSection docstring change"
    - path: "charts/arr-stack/values.yaml"
      provides: "arrconf.image.tag co-bumped 0.7.0 → 0.8.0 (D-05 release pin co-bump)"
      contains: "0.8.0"
    - path: ".planning/phases/16-jellyfin-categories-as-libs/16-HUMAN-UAT.md"
      provides: "4-5 UAT scenarios for operator close-out (web UI count, watched-state, prune flip, JellyCon carry-forward, optional legacy paths sweep)"
  key_links:
    - from: "tools/arrconf/arrconf/generators/categories.py::generate_jellyfin_libraries"
      to: "categories[].display + .kind + .base_path"
      via: "list comprehension over cfg.categories"
      pattern: "JellyfinLibrary\\(name=c\\.display"
    - from: "tools/arrconf/arrconf/reconcilers/jellyfin.py::_reconcile_libraries"
      to: "_create_library / _prune_library_paths / _prune_libraries helpers"
      via: "match-by-Name against pre-fetched cluster snapshot"
      pattern: "if cluster_lib is None"
    - from: "tools/arrconf/arrconf/reconcilers/jellyfin.py::_create_library"
      to: "POST /Library/VirtualFolders"
      via: "httpx params={name, collectionType, paths, refreshLibrary=false}, json={}"
      pattern: "LIBRARY_VIRTUALFOLDERS_PATH"
    - from: "tools/arrconf/arrconf/reconcilers/jellyfin.py::_prune_libraries"
      to: "DELETE /Library/VirtualFolders"
      via: "try/except NotFoundError → log library_already_absent"
      pattern: "NotFoundError"
    - from: "charts/arr-stack/values.yaml#arrconf.image.tag"
      to: "tools/arrconf/** code changes"
      via: "same-commit co-bump (CLAUDE.md release pin pattern)"
      pattern: "tag: \"0\\.8\\.0\""
---

<objective>
**Phase 16 — Jellyfin Categories-as-libs.** Refactor `generate_jellyfin_libraries()` to emit 10 `VirtualFolder` libs (one per `categories[]` entry) instead of the 2 super-libs `Séries` + `Films`. Extend `_reconcile_libraries()` to own the full library lifecycle (CREATE missing libs, prune-gated DELETE PathInfo, prune-gated DELETE Lib with 404 tolerance). Reverse D-07-LIB-01 — the `prune:` flag in `jellyfin.libraries` becomes effective again. Co-bump the arrconf image tag `0.7.0 → 0.8.0` in the same commit.

**Purpose:** Make the 10 Categories natively visible in every Jellyfin client (web, Swiftfin, JellyCon on the LibreELEC salon mini-PC), aligned with the Categories first-class vision (v0.3.0 shipped, v0.5.0 closes the Jellyfin gap).

**Output:**
- 1 ADR-6 snapshot baseline (`snapshots/before-phase-16-2026-05-24/jellyfin/`)
- 4 Python files modified (`generators/categories.py`, `reconcilers/jellyfin.py`, `config.py` docstring, `__main__.py` if any wiring touched — verify scope unchanged)
- 2 test files rewritten + 1 new fixture
- 1 regenerated JSON schema
- 1 chart values bump (`0.7.0 → 0.8.0`)
- 1 HUMAN-UAT runbook with 5 scenarios

All work lives in a **single plan 16-A** per CONTEXT.md "Open Items for Plan Phase" — surface is ~150 LOC across 4 production files, no waterfall needed.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/16-jellyfin-categories-as-libs/16-CONTEXT.md
@.planning/phases/16-jellyfin-categories-as-libs/16-RESEARCH.md
@CLAUDE.md

<!-- Pinned code references — executor MUST read before touching anything -->
@tools/arrconf/arrconf/generators/categories.py
@tools/arrconf/arrconf/reconcilers/jellyfin.py
@tools/arrconf/arrconf/resources/jellyfin/library.py
@tools/arrconf/arrconf/config.py
@tools/arrconf/arrconf/exceptions.py
@tools/arrconf/tests/test_reconcilers_jellyfin.py
@tools/arrconf/tests/test_jellyfin_categories.py
@charts/arr-stack/files/arrconf.yml
@charts/arr-stack/values.yaml

<interfaces>
<!-- Extracted from codebase 2026-05-24 — executor uses these directly, no exploration needed. -->

From tools/arrconf/arrconf/resources/jellyfin/library.py:
```python
class PathInfo(BaseModel):
    model_config = ConfigDict(extra="allow")
    Path: str

class JellyfinLibrary(BaseModel):
    """Match by Name. paths = PathInfos[].Path desired set."""
    model_config = ConfigDict(extra="allow")
    name: str
    collection_type: str  # "tvshows" | "movies"
    paths: list[str] = Field(default_factory=list)
```

From tools/arrconf/arrconf/resources/categories.py (Category model is the generator input — see RESEARCH.md):
```python
# Category attributes used by generator:
#   c.name      str        e.g. "series-emilie"   → filesystem dir name /media/<name>
#   c.kind      str        "series" | "movies"
#   c.profile   str        "general" | "anime" | "family"
#   c.display   str        e.g. "Séries - Émilie" → JellyfinLibrary.name (D-16-LIB-NAME-01)
#   c.base_path str        e.g. "/media/series-emilie"
```

From tools/arrconf/arrconf/config.py (existing — JellyfinLibrariesSection):
```python
class JellyfinLibrariesSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enable: bool = Field(default=True, ...)
    prune: bool = Field(default=False, description="Opt-in deletion (D-04). MUST be False in Phase 7 (D-07-LIB-01).")
    # → docstring + field description need D-16-PRUNE-01 update (Task 4)
```

From tools/arrconf/arrconf/exceptions.py:
```python
class ApiClientError(Exception): ...
class NotFoundError(ApiClientError): ...   # raised by ArrApiClient._request on 4xx-404
```

From tools/arrconf/arrconf/reconcilers/jellyfin.py (existing constants — REUSE):
```python
LIBRARY_VIRTUALFOLDERS_PATH = "/Library/VirtualFolders"
LIBRARY_PATHS_PATH = "/Library/VirtualFolders/Paths"
```

From tools/arrconf/arrconf/client_base.py (JellyfinClient):
```python
# client.get(path) → returns parsed JSON
# client._request(method, path, params=..., json=...) → raises NotFoundError on 404
# httpx serializes params={"paths": ["/a", "/b"]} as ?paths=/a&paths=/b (verified — RESEARCH.md A2)
# httpx auto-encodes UTF-8 lib names (Séries → S%C3%A9ries) — RESEARCH.md verified
```

From tools/arrconf/tests/test_reconcilers_jellyfin.py (existing helpers — REUSE):
```python
JELLYFIN_BASE = "http://jellyfin.test:8096"
def _make_client() -> JellyfinClient: ...
def _make_instance(**overrides: Any) -> JellyfinInstance: ...
def _library_fixture() -> list[dict[str, Any]]: ...   # 2 libs, 1 path each
def _users_fixture() -> list[dict[str, Any]]: ...
def _user_moi_full_fixture() -> dict[str, Any]: ...
def _mock_all_gets(...) -> None: ...                  # mounts respx GETs for all 4 reconcile steps
_DEFAULT_LIBRARIES = [JellyfinLibrary("Séries", ...), JellyfinLibrary("Films", ...)]   # PHASE 7 SHAPE — needs review per test
```
</interfaces>
</context>

<warnings>
<!-- These are the four CRITICAL things this plan must protect against. -->

**Pitfall 16-1 (CRITIQUE):** POST `/Library/VirtualFolders` is NOT idempotent. Jellyfin SILENTLY appends `2`, `3` suffix on duplicate names — HTTP 204 returned, no error. Verified live 2026-05-24 (RESEARCH.md §POST evidence). Reconciler MUST GET cluster libs FIRST, match-by-Name, skip POST if match exists. The unit test `test_library_create_skipped_when_name_already_exists` (Task 6) is the contract — if it doesn't exist, Phase 16 is broken.

**Pitfall 16-2:** DELETE `/Library/VirtualFolders` returns HTTP 404 if the lib doesn't exist (unlike DELETE Paths which is silent 204). The reconciler MUST wrap the DELETE in `try/except NotFoundError` → log `library_already_absent`. Test `test_library_prune_lib_tolerates_404` is the contract.

**Pitfall 16-4 (operator gate, not code):** Watched-state preservation depends on operator having done the v0.2.0 → v0.3.0 filesystem migration (CLAUDE.md "Filesystem migration v0.2.0 → v0.3.0"). Items under `/media/anime`, `/media/family`, `/media/films-anime`, `/media/films-family` that are NOT migrated to v0.3.0 buckets become orphaned post-cutover. Documented as HUMAN-UAT scenario in Task 9, NOT a code fix.

**Live cluster state surprise:** Jellyfin is currently on v0.2.0 LIBRARY layout (Séries: 3 paths `/media/series + /media/anime + /media/family`; Films: 3 paths `/media/films + /media/films-anime + /media/films-family`). The 4 legacy v0.2.0 dirs still exist on NFS alongside the 10 v0.3.0 dirs (RESEARCH.md §Live Cluster State). Phase 16 cutover with `prune: true` will reshape `Séries` from 3 paths to 1 path and `Films` similarly. Watched-state risk bounded per Pitfall 16-4.

**Release pin co-bump (CLAUDE.md "Release pin co-bump pattern"):** ANY commit modifying `tools/arrconf/**` MUST bump `charts/arr-stack/values.yaml#arrconf.image.tag` in the SAME commit. Minor bump `0.7.0 → 0.8.0` (new feature). Failure → ImagePullBackOff post-merge (Phase 10 historical bug `12c05da`). Task 8 is the gate.

**ADR-5 frontière:** Phase 16 touches ONLY `_reconcile_libraries()` + `generate_jellyfin_libraries()`. Do NOT touch `_reconcile_users()`, `_reconcile_server_config()`, `_reconcile_plugins()`. Do NOT touch ANY *arr v3 endpoint (`/api/v3/qualityprofile`, `/api/v3/customformat`, `/api/v3/qualitydefinition`, `/api/v3/mediamanagement`). The existing negative test `test_jellyfin_does_not_call_arr_v3_quality_endpoints` (line 1004) must remain green.

**Snapshot ADR-6:** `tools/snapshot/snapshot.sh --apps jellyfin --output snapshots/before-phase-16-2026-05-24/` MUST run BEFORE any code is committed AND be committed itself (Task 1). Failure to snapshot is a CLAUDE.md "ne pas tester un nouveau reconciler en cluster sans avoir snapshot la baseline d'abord" violation.
</warnings>

<tasks>

<task type="auto">
  <name>Task 1: ADR-6 pre-cutover snapshot baseline</name>
  <files>snapshots/before-phase-16-2026-05-24/jellyfin/ (created)</files>
  <read_first>
    - CLAUDE.md § "Workflow snapshot (CRITIQUE — à respecter avant tout test risqué)"
    - .planning/phases/16-jellyfin-categories-as-libs/16-RESEARCH.md § "Live Cluster State" (current cluster state expectations)
    - tools/snapshot/snapshot.sh (verify script exists and accepts `--apps jellyfin --output PATH`)
  </read_first>
  <action>
    Run the raw snapshot capture (ADR-6) BEFORE any code modification. The snapshot freezes the pre-Phase-16 Jellyfin state for forensic diff post-cutover.

    Execute exactly:
    ```bash
    cd /data/projets/perso/arr-stack
    mkdir -p snapshots/before-phase-16-2026-05-24/jellyfin/
    tools/snapshot/snapshot.sh --apps jellyfin --output snapshots/before-phase-16-2026-05-24/
    ```

    Expected output: a directory `snapshots/before-phase-16-2026-05-24/jellyfin/` containing at minimum:
    - `library_virtualfolders.json` — current 2-super-libs shape with multi-path PathInfos
    - `system_configuration.json` (if snapshot.sh captures it for jellyfin)
    - `users.json` (likewise — keep as-is, scope of Phase 16 is libraries only but full snapshot is fine)

    If `tools/snapshot/snapshot.sh` is not runnable from CI/agent context (requires `kubectl` + port-forward + `JELLYFIN_API_KEY` from sealed-secret), the task MUST be flagged as `checkpoint:human-action` deferred to the operator BEFORE merge. Document this in 16-SUMMARY.md.

    If the snapshot succeeds, `git add snapshots/before-phase-16-2026-05-24/` and stage for the SAME commit as code changes (or a preceding commit on the same branch). Snapshots are versioned per CLAUDE.md "Ne pas ignorer `snapshots/` dans `.gitignore`."

    Do NOT modify the snapshot directory after capture — it is the immutable baseline.
  </action>
  <verify>
    <automated>test -d /data/projets/perso/arr-stack/snapshots/before-phase-16-2026-05-24/jellyfin/ && find /data/projets/perso/arr-stack/snapshots/before-phase-16-2026-05-24/jellyfin/ -name '*.json' -size +0 | wc -l | grep -qv '^0$'</automated>
  </verify>
  <acceptance_criteria>
    - `snapshots/before-phase-16-2026-05-24/jellyfin/` exists as a directory under the repo root
    - At least one non-empty `.json` file exists in that directory
    - `snapshots/before-phase-16-2026-05-24/jellyfin/library_virtualfolders.json` contains the current 2-super-libs (Séries + Films) shape with multi-path PathInfos (sanity-check by `jq 'length == 2' library_virtualfolders.json` returning `true`)
    - The directory is staged for git commit (`git status` shows untracked or staged entries under `snapshots/before-phase-16-2026-05-24/`)
    - If snapshot.sh requires operator-only access (kubectl + sealed-secret API key), the task is marked deferred-to-operator and the operator is the one who commits this directory before merging the PR
  </acceptance_criteria>
  <done>Pre-cutover baseline snapshot captured and either committed or staged for the merge PR. CLAUDE.md ADR-6 discipline satisfied.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Rewrite `generate_jellyfin_libraries()` — 10 libs from 10 Categories (Pattern 5)</name>
  <files>tools/arrconf/arrconf/generators/categories.py (modify lines 192-202 — full function replacement)</files>
  <read_first>
    - tools/arrconf/arrconf/generators/categories.py (current implementation lines 192-202 returning 2 super-libs)
    - .planning/phases/16-jellyfin-categories-as-libs/16-RESEARCH.md § "Pattern 5: Refactored `generate_jellyfin_libraries()`" (lines 542-569 — copy-paste-ready code)
    - .planning/phases/16-jellyfin-categories-as-libs/16-CONTEXT.md § "D-16-LIB-NAME-01" + "D-16-COLLECTIONTYPE-01"
    - tools/arrconf/arrconf/resources/jellyfin/library.py (JellyfinLibrary signature)
  </read_first>
  <behavior>
    - Test 1 (`test_generate_jellyfin_libraries_ten_libs`): with the 10-category PRODUCTION_CATEGORIES fixture, the generator returns exactly 10 `JellyfinLibrary` entries.
    - Test 2 (`test_generate_jellyfin_libraries_collection_type_mapping`): the 5 entries with `kind: "series"` produce `collection_type == "tvshows"`; the 5 entries with `kind: "movies"` produce `collection_type == "movies"`.
    - Test 3 (`test_generate_jellyfin_libraries_names_match_display`): every generated lib's `.name` equals the corresponding `categories[i].display` field (verbatim, including UTF-8 chars like `Séries - Émilie`, `Séries - Zoé`, `Films - Animation Enfants`).
    - Test 4 (`test_generate_jellyfin_libraries_paths_single_per_lib`): every generated lib has `len(paths) == 1` and `paths[0] == categories[i].base_path` (e.g. `/media/series-emilie`).
    - Test 5 (`test_generate_jellyfin_libraries_order_follows_categories`): the order of returned libs matches the order of `cfg.categories` (deterministic for tests and operator-readability).
    - Test 6 (`test_generate_jellyfin_libraries_empty_cfg`): when `cfg.categories == []`, the generator returns `[]` (replaces the legacy "always returns 2 empty libs" behavior — see Task 5 for the test cleanup).
  </behavior>
  <action>
    Replace lines 192-202 of `tools/arrconf/arrconf/generators/categories.py` with the Pattern 5 implementation from `16-RESEARCH.md`. EXACT replacement:

    ```python
    # D-16-COLLECTIONTYPE-01: same mapping as Phase 7 (unchanged from old impl).
    _KIND_TO_COLLECTION_TYPE: Final[dict[str, str]] = {
        "series": "tvshows",
        "movies": "movies",
    }


    def generate_jellyfin_libraries(cfg: RootConfig) -> list[JellyfinLibrary]:
        """REQ-jellyfin-categories-as-libs: 10 libs, one per Category (D-16-LIB-CREATE-01).

        Phase 16 reverses Phase 7's 2-super-libs design (`Séries`/`Films` with multi-path
        PathInfos). Each Category now becomes its own JellyfinLibrary with:
          - name           = c.display       (D-16-LIB-NAME-01 — UI-facing label)
          - collection_type = kind→type map  (D-16-COLLECTIONTYPE-01 — unchanged)
          - paths          = [c.base_path]   (single PathInfo per lib)

        Order of output follows ``cfg.categories`` order — deterministic for tests
        and operator readability of the resulting JSON.

        Returns empty list when ``cfg.categories`` is empty (no implicit super-libs).
        """
        return [
            JellyfinLibrary(
                name=c.display,
                collection_type=_KIND_TO_COLLECTION_TYPE[c.kind],
                paths=[c.base_path],
            )
            for c in cfg.categories
        ]
    ```

    The `_KIND_TO_COLLECTION_TYPE` constant goes at module level (after the existing constants section around line 27-35). The function replaces the current lines 192-202.

    **Do NOT change** the surrounding generators (`generate_qbit_categories`, `generate_sonarr_resources`, `generate_radarr_resources`, `generate_anime_tag_labels`) — they are out of scope.

    **Do NOT touch** the `JellyfinLibrary` pydantic model itself — its current shape (`name`, `collection_type`, `paths`) is compatible with the new generator. The semantic of `name` shifts from "hardcoded super-lib label" to "Category display label" — document in the JellyfinLibrary docstring if helpful (optional polish, NOT required).

    After the code change, immediately update `tools/arrconf/tests/test_jellyfin_categories.py` per Task 5 so that the test suite remains green. The test rewrite is split into its own task because it's a substantial rewrite (143 LOC current → ~120 LOC new).
  </action>
  <verify>
    <automated>cd /data/projets/perso/arr-stack/tools/arrconf && grep -q '_KIND_TO_COLLECTION_TYPE' arrconf/generators/categories.py && grep -q 'name=c\.display' arrconf/generators/categories.py && ! grep -q 'name="Séries", collection_type="tvshows", paths=series_paths' arrconf/generators/categories.py</automated>
  </verify>
  <acceptance_criteria>
    - `tools/arrconf/arrconf/generators/categories.py` contains the constant `_KIND_TO_COLLECTION_TYPE: Final[dict[str, str]] = {"series": "tvshows", "movies": "movies"}` at module level
    - `generate_jellyfin_libraries` signature unchanged: `def generate_jellyfin_libraries(cfg: RootConfig) -> list[JellyfinLibrary]:`
    - Function body is a single list comprehension over `cfg.categories`
    - Each iterator step constructs `JellyfinLibrary(name=c.display, collection_type=_KIND_TO_COLLECTION_TYPE[c.kind], paths=[c.base_path])`
    - The old multi-path super-lib code (`series_paths = [c.base_path for c in cfg.categories if c.kind == "series"]` and the 2-element return list with hardcoded `"Séries"` / `"Films"` names) is COMPLETELY removed
    - `grep -c "name=\"Séries\"\\|name=\"Films\"" tools/arrconf/arrconf/generators/categories.py` returns 0 (no hardcoded super-lib names remaining)
    - Module imports (`JellyfinLibrary`, `RootConfig`) unchanged — `Final` import added if not already present (`from typing import Final` already at line 18 — verify, add if missing)
  </acceptance_criteria>
  <done>Generator produces 10 libs from a 10-Category fixture; existing surrounding generators untouched; no hardcoded super-lib names left.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Extend `_reconcile_libraries()` — CREATE + prune-gated DELETE Path + DELETE Lib (Pattern 4)</name>
  <files>tools/arrconf/arrconf/reconcilers/jellyfin.py (modify lines 107-181 — replace `_reconcile_libraries` body, add 3 helpers)</files>
  <read_first>
    - tools/arrconf/arrconf/reconcilers/jellyfin.py (current `_reconcile_libraries` lines 107-181 + module-level constants lines 1-69)
    - .planning/phases/16-jellyfin-categories-as-libs/16-RESEARCH.md § "Pattern 1" (lines 352-386 — `_create_library` body)
    - .planning/phases/16-jellyfin-categories-as-libs/16-RESEARCH.md § "Pattern 2" (lines 388-438 — `_prune_library_paths` body)
    - .planning/phases/16-jellyfin-categories-as-libs/16-RESEARCH.md § "Pattern 3" (lines 440-487 — `_prune_libraries` body)
    - .planning/phases/16-jellyfin-categories-as-libs/16-RESEARCH.md § "Pattern 4" (lines 489-539 — full `_reconcile_libraries` skeleton)
    - .planning/phases/16-jellyfin-categories-as-libs/16-RESEARCH.md § "Pitfall 16-1" + "Pitfall 16-2" (the two CRITIQUE pitfalls)
    - tools/arrconf/arrconf/exceptions.py (`NotFoundError` import path)
  </read_first>
  <behavior>
    - Test 1 (`test_library_create_uses_query_params_and_empty_body`): given desired_libs=[lib not in cluster], `_reconcile_libraries` calls POST `/Library/VirtualFolders` exactly once with query params `name=<display>&collectionType=<type>&paths=<base_path>&refreshLibrary=false` and JSON body `{}`.
    - Test 2 (`test_library_create_skipped_when_name_already_exists`): given desired_lib `Séries` matches a cluster lib `Séries` (case-sensitive on Name), `_reconcile_libraries` does NOT call POST `/Library/VirtualFolders` (only the existing path-add branch may fire if PathInfos differ). Pitfall 16-1 guard.
    - Test 3 (`test_library_prune_paths_removes_excess`): given `section.prune=True` + cluster lib has paths `[/media/series, /media/anime, /media/family]` + desired lib has paths `[/media/series]`, reconciler DELETEs `/Library/VirtualFolders/Paths?name=Séries&path=/media/anime&...` AND `?path=/media/family&...` (2 DELETE calls, deterministic sorted order).
    - Test 4 (`test_library_prune_paths_disabled_when_prune_false`): given `section.prune=False` + same path mismatch as Test 3, reconciler issues ZERO DELETE calls on `/Library/VirtualFolders/Paths`.
    - Test 5 (`test_library_prune_lib_removes_orphans`): given `section.prune=True` + cluster has lib `ManualLib` (not in desired set) + desired has 10 libs, reconciler DELETEs `/Library/VirtualFolders?name=ManualLib&refreshLibrary=false`.
    - Test 6 (`test_library_prune_lib_tolerates_404`): given `section.prune=True` + reconciler about to DELETE a lib + respx mocked to return 404 → reconciler does NOT raise, logs `library_already_absent`, continues with remaining libs. Pitfall 16-2 guard.
    - Test 7 (`test_library_prune_lib_disabled_when_prune_false`): given `section.prune=False` + cluster has orphan lib `ManualLib`, reconciler issues ZERO DELETE calls on `/Library/VirtualFolders`.
    - Test 8 (`test_jellyfin_create_and_prune_dry_run`): given `dry_run=True`, reconciler issues ZERO write requests (no POST `/Library/VirtualFolders`, no DELETE on either endpoint) but logs `dry_run_skip` events with the planned actions. Returned action list contains `library_create:dry_run:*` / `library_path_pruned:dry_run:*` / `library_pruned:dry_run:*` entries.
  </behavior>
  <action>
    Rewrite `_reconcile_libraries` in `tools/arrconf/arrconf/reconcilers/jellyfin.py` to own the full library lifecycle. The refactor introduces 3 new module-private helpers and reuses the existing Phase 7 "ADD missing paths" branch as `_add_missing_paths()` (extract from current body, function-ize for cleanliness).

    **Step 3.1 — Add NotFoundError import at top:**
    ```python
    from arrconf.exceptions import NotFoundError
    ```
    (Place alongside the existing `arrconf.config` imports around line 38-44.)

    **Step 3.2 — Add `_create_library` helper (after the `SERVER_CONFIG_ALLOWLIST` constants block, ~line 70):**

    Copy the Pattern 1 code from `16-RESEARCH.md` lines 352-386 verbatim:
    ```python
    def _create_library(
        client: JellyfinClient,
        desired_lib: JellyfinLibrary,
        dry_run: bool,
    ) -> str | None:
        """Create a new Jellyfin VirtualFolder via POST /Library/VirtualFolders.

        Single-call create-with-paths: paths array is in the QUERY STRING (not body).
        Body is empty AddVirtualFolderDto ({}) — LibraryOptions is nullable per OpenAPI 10.11.9.

        Phase 16 (D-16-LIB-CREATE-01). Idempotence shim — caller MUST verify Name absence
        in cluster snapshot BEFORE invoking (Pitfall 16-1: POST duplicates with suffix).
        """
        if dry_run:
            log.info(
                "dry_run_skip",
                resource="library_create",
                name=desired_lib.name,
                collection_type=desired_lib.collection_type,
                paths=desired_lib.paths,
            )
            return f"library_create:dry_run:{desired_lib.name}"

        client._request(
            "POST",
            LIBRARY_VIRTUALFOLDERS_PATH,
            params={
                "name": desired_lib.name,
                "collectionType": desired_lib.collection_type,
                "paths": desired_lib.paths,    # httpx repeats key for list values (A2)
                "refreshLibrary": "false",
            },
            json={},  # AddVirtualFolderDto with LibraryOptions=null
        )
        log.info(
            "library_created",
            name=desired_lib.name,
            collection_type=desired_lib.collection_type,
            paths=desired_lib.paths,
        )
        return f"library_created:{desired_lib.name}"
    ```

    **Step 3.3 — Extract `_add_missing_paths` helper from current `_reconcile_libraries` body:**

    Lift the existing path-add inner loop (current lines 146-179) into a function with this signature and behavior unchanged (Phase 7 carry-forward):
    ```python
    def _add_missing_paths(
        client: JellyfinClient,
        desired_lib: JellyfinLibrary,
        cluster_lib: dict[str, Any],
        dry_run: bool,
    ) -> list[str]:
        """Add desired paths absent from cluster_lib (Phase 7 Pitfall 2 idempotence shim).

        Pitfall 8: PathInfos is the source of truth, NEVER Locations (stale projection).
        """
        library_options = cluster_lib.get("LibraryOptions") or {}
        path_infos = library_options.get("PathInfos") or []
        existing_paths: set[str] = {p.get("Path") for p in path_infos if p.get("Path")}
        actions: list[str] = []

        for path in desired_lib.paths:
            if path in existing_paths:
                log.info("library_path_already_present", name=desired_lib.name, path=path)
                continue

            if dry_run:
                log.info("dry_run_skip", resource="library_path", name=desired_lib.name, path=path)
                actions.append(f"library_path:dry_run:{desired_lib.name}:{path}")
                continue

            client._request(
                "POST",
                LIBRARY_PATHS_PATH,
                params={"refreshLibrary": "false"},
                json={"Name": desired_lib.name, "Path": path, "PathInfo": {"Path": path}},
            )
            log.info("library_path_added", name=desired_lib.name, path=path)
            actions.append(f"library_path:added:{desired_lib.name}:{path}")

        return actions
    ```

    **Step 3.4 — Add `_prune_library_paths` helper (Pattern 2 from RESEARCH lines 388-438):**

    ```python
    def _prune_library_paths(
        client: JellyfinClient,
        desired_lib: JellyfinLibrary,
        cluster_lib: dict[str, Any],
        section: JellyfinLibrariesSection,
        dry_run: bool,
    ) -> list[str]:
        """Remove paths present in cluster but NOT in desired set (D-16-PATH-DELETE-01).

        Gated by section.prune (D-16-PRUNE-01). When prune=False (default), no-op.
        Pitfall 8 carry-forward: diff PathInfos, NEVER Locations.
        """
        if not section.prune:
            return []

        desired_paths: set[str] = set(desired_lib.paths)
        path_infos = (cluster_lib.get("LibraryOptions") or {}).get("PathInfos") or []
        cluster_paths: set[str] = {p.get("Path") for p in path_infos if p.get("Path")}
        excess: set[str] = cluster_paths - desired_paths
        actions: list[str] = []

        for path in sorted(excess):  # deterministic for tests
            if dry_run:
                log.info(
                    "dry_run_skip",
                    resource="library_path_delete",
                    name=desired_lib.name,
                    path=path,
                )
                actions.append(f"library_path_pruned:dry_run:{desired_lib.name}:{path}")
                continue

            client._request(
                "DELETE",
                LIBRARY_PATHS_PATH,
                params={
                    "name": desired_lib.name,
                    "path": path,
                    "refreshLibrary": "false",
                },
            )
            log.info("library_path_pruned", name=desired_lib.name, path=path)
            actions.append(f"library_path_pruned:{desired_lib.name}:{path}")

        return actions
    ```

    **Step 3.5 — Add `_prune_libraries` helper (Pattern 3 from RESEARCH lines 440-487):**

    ```python
    def _prune_libraries(
        client: JellyfinClient,
        current_libraries: list[dict[str, Any]],
        desired_libraries: list[JellyfinLibrary],
        section: JellyfinLibrariesSection,
        dry_run: bool,
    ) -> list[str]:
        """Remove cluster libs NOT in the desired set (D-16-PRUNE-01).

        Gated by section.prune. When prune=False (default), no-op.
        Pitfall 16-2: DELETE returns 404 on missing lib — wrap in NotFoundError tolerance.
        Filesystem is NEVER touched (verified live 2026-05-24 — RESEARCH §POST/DELETE probe).
        """
        if not section.prune:
            return []

        desired_names: set[str] = {lib.name for lib in desired_libraries}
        actions: list[str] = []

        for cluster_lib in current_libraries:
            cluster_name = cluster_lib.get("Name")
            if not cluster_name or cluster_name in desired_names:
                continue

            if dry_run:
                log.info("dry_run_skip", resource="library_delete", name=cluster_name)
                actions.append(f"library_pruned:dry_run:{cluster_name}")
                continue

            try:
                client._request(
                    "DELETE",
                    LIBRARY_VIRTUALFOLDERS_PATH,
                    params={"name": cluster_name, "refreshLibrary": "false"},
                )
                log.info("library_pruned", name=cluster_name)
                actions.append(f"library_pruned:{cluster_name}")
            except NotFoundError:
                # Pitfall 16-2: 404 — lib already gone (concurrent operator action). No-op.
                log.info("library_already_absent", name=cluster_name)

        return actions
    ```

    **Step 3.6 — Rewrite `_reconcile_libraries` body (Pattern 4 from RESEARCH lines 489-539):**

    Replace the existing body (current lines 107-181, EXCEPT the function signature) with:

    ```python
    def _reconcile_libraries(
        client: JellyfinClient,
        section: JellyfinLibrariesSection,
        desired_libraries: list[JellyfinLibrary],
        dry_run: bool,
    ) -> list[str]:
        """Reconcile Jellyfin libraries — Phase 16 full lifecycle (D-16-*).

        Order within run:
          1. GET cluster snapshot once
          2. For each desired lib:
             a. if not in cluster → CREATE (POST /Library/VirtualFolders with all paths)
             b. if in cluster → ADD missing paths (Phase 7 Pitfall 2 idempotence shim)
             c. if section.prune → DELETE excess paths (D-16-PATH-DELETE-01)
          3. If section.prune → DELETE cluster libs not in desired set (D-16-PRUNE-01)

        Pitfall 16-1 (CRITIQUE): POST /Library/VirtualFolders is NOT idempotent —
        Jellyfin silently appends `Name2`/`Name3` on duplicate Names. Match-by-Name
        from the pre-fetched snapshot is the ONLY mitigation.
        """
        if not section.enable:
            log.info("libraries_reconcile_skipped")
            return []

        log.info("step_begin", step="libraries", step_index=1)
        current_libraries: list[dict[str, Any]] = client.get(LIBRARY_VIRTUALFOLDERS_PATH)
        by_name: dict[str, dict[str, Any]] = {
            lib["Name"]: lib for lib in current_libraries if lib.get("Name")
        }
        actions: list[str] = []

        for desired_lib in desired_libraries:
            cluster_lib = by_name.get(desired_lib.name)

            if cluster_lib is None:
                # Pitfall 16-1: must verify absence by Name BEFORE POST or Jellyfin duplicates with suffix.
                action = _create_library(client, desired_lib, dry_run)
                if action:
                    actions.append(action)
                continue

            # Existing lib → add missing paths (Phase 7 pattern, extracted to helper).
            actions += _add_missing_paths(client, desired_lib, cluster_lib, dry_run)

            # Prune excess paths (Phase 16 new behavior, prune-gated).
            actions += _prune_library_paths(client, desired_lib, cluster_lib, section, dry_run)

        # Phase 16: prune entire libs not in desired set (D-16-PRUNE-01).
        actions += _prune_libraries(client, current_libraries, desired_libraries, section, dry_run)

        return actions
    ```

    **Step 3.7 — Update module docstring (line 1-28):** Reflect Phase 16 ownership of CREATE + DELETE Path + DELETE Lib. Specifically remove the lines that say "Reconciler NEVER creates new libraries" and "libraries.prune = False (D-07-LIB-01) → reconciler NEVER DELETEs paths." Replace with:
    ```
    1. libraries → POST /Library/VirtualFolders + POST /Library/VirtualFolders/Paths
       + DELETE /Library/VirtualFolders/Paths + DELETE /Library/VirtualFolders
       (Phase 16 D-16-LIB-CREATE-01 + D-16-PRUNE-01 + D-16-PATH-DELETE-01.
        Pitfall 16-1 mitigation: match-by-Name pre-check before POST CREATE.
        Pitfall 16-2 mitigation: NotFoundError tolerance on DELETE Lib.)
    ```
    Update the "Hardcoded protections:" section to remove the `libraries.prune = False` line (the new state is opt-in via YAML).

    **Do NOT touch** `_reconcile_users`, `_reconcile_server_config`, `_reconcile_plugins`, `reconcile_jellyfin` (top-level), or any non-library code path. ADR-5 frontière + Phase 16 scope.

    Run `cd tools/arrconf && uv run ruff format arrconf/reconcilers/jellyfin.py` after the change to keep formatting consistent.
  </action>
  <verify>
    <automated>cd /data/projets/perso/arr-stack/tools/arrconf && grep -q 'def _create_library(' arrconf/reconcilers/jellyfin.py && grep -q 'def _prune_library_paths(' arrconf/reconcilers/jellyfin.py && grep -q 'def _prune_libraries(' arrconf/reconcilers/jellyfin.py && grep -q 'def _add_missing_paths(' arrconf/reconcilers/jellyfin.py && grep -q 'from arrconf.exceptions import NotFoundError' arrconf/reconcilers/jellyfin.py && grep -q 'except NotFoundError' arrconf/reconcilers/jellyfin.py && ! grep -q 'library_missing_skip' arrconf/reconcilers/jellyfin.py</automated>
  </verify>
  <acceptance_criteria>
    - File contains all four helper functions: `_create_library`, `_add_missing_paths`, `_prune_library_paths`, `_prune_libraries`
    - File imports `NotFoundError` from `arrconf.exceptions`
    - `_prune_libraries` body contains `except NotFoundError` and a `log.info("library_already_absent", ...)` call
    - The old `library_missing_skip` warning is REMOVED (no longer reachable — CREATE handles the case)
    - The old `D-07-LIB-01` reference to "reconciler NEVER creates" / "NEVER DELETEs paths" is removed from the module docstring
    - `_reconcile_libraries` signature unchanged: `(client, section, desired_libraries, dry_run) -> list[str]`
    - `_reconcile_libraries` body starts with `if not section.enable: return []` then `log.info("step_begin", step="libraries", step_index=1)` then `current_libraries = client.get(LIBRARY_VIRTUALFOLDERS_PATH)`
    - `_reconcile_libraries` calls `_create_library` ONLY when `by_name.get(desired_lib.name) is None` (Pitfall 16-1 guard)
    - `_create_library` issues exactly one HTTP write per call: `POST` to `LIBRARY_VIRTUALFOLDERS_PATH` with `params={"name", "collectionType", "paths", "refreshLibrary"}` and `json={}`
    - `_prune_library_paths` short-circuits and returns `[]` when `not section.prune`
    - `_prune_libraries` short-circuits and returns `[]` when `not section.prune`
    - `_prune_libraries` iterates `current_libraries` (the cluster snapshot, NOT desired) and deletes those whose `Name` is not in `desired_names`
    - All three new prune helpers handle `dry_run=True` by appending a `*:dry_run:*` marker to actions and NOT issuing HTTP writes
    - File contains zero references to deprecated phrases (`library_missing_skip`, "Operator must create the library via Jellyfin UI Dashboard")
  </acceptance_criteria>
  <done>Reconciler owns the full library lifecycle; Pitfall 16-1 + 16-2 mitigations in place; existing Phase 7 path-add behavior preserved verbatim via the `_add_missing_paths` helper.</done>
</task>

<task type="auto">
  <name>Task 4: Update `JellyfinLibrariesSection.prune` docstring + regen JSON schema</name>
  <files>tools/arrconf/arrconf/config.py (modify lines 519-535), schemas/arrconf-schema.json (regenerated)</files>
  <read_first>
    - tools/arrconf/arrconf/config.py (current `JellyfinLibrariesSection` lines 519-535)
    - .planning/phases/16-jellyfin-categories-as-libs/16-CONTEXT.md § "D-16-PRUNE-01"
    - schemas/arrconf-schema.json (current shape — note `JellyfinLibrariesSection` entry)
  </read_first>
  <action>
    The `JellyfinLibrariesSection.prune` field already exists with `default=False` — code-wise, no field add/remove is needed. ONLY the docstrings need to reflect D-07-LIB-01 → D-16-PRUNE-01 reversal so future maintainers know the contract changed.

    **Step 4.1 — Update class docstring (line 520-528):**

    Replace:
    ```
    """Jellyfin libraries section — enable + prune (D-07-LIB-01); items derived from categories.

    Scope per D-07-LIB-02: name + collection_type + paths only. LibraryOptions
    sub-fields stay operator-managed.

    prune: FALSE hardcoded — D-07-LIB-01 explicitly disallows automatic DELETE
    of paths from cluster libraries (Pitfall 3 — DELETE removes ALL matching
    entries; reconciler refuses to ever DELETE in Phase 7).
    """
    ```

    With:
    ```
    """Jellyfin libraries section — enable + prune (D-16-PRUNE-01); items derived from categories.

    Scope per D-07-LIB-02: name + collection_type + paths only. LibraryOptions
    sub-fields stay operator-managed.

    prune: opt-in per section (D-16-PRUNE-01 — reverses D-07-LIB-01 hardcoded false).
    When True, the reconciler DELETEs PathInfos present in cluster but not in desired
    (D-16-PATH-DELETE-01) AND DELETEs entire libs not in desired set. Operator-driven
    flag — flip to True for the cutover PR, back to False after UAT to avoid drift on
    user-added libs. NotFoundError on DELETE Lib is tolerated (Pitfall 16-2).
    """
    ```

    **Step 4.2 — Update field description (lines 532-535):**

    Replace:
    ```python
    prune: bool = Field(
        default=False,
        description="Opt-in deletion (D-04). MUST be False in Phase 7 (D-07-LIB-01).",
    )
    ```

    With:
    ```python
    prune: bool = Field(
        default=False,
        description=(
            "Opt-in deletion (D-16-PRUNE-01 — Phase 16 reverses D-07-LIB-01). "
            "When True, reconciler DELETEs excess PathInfos and orphaned libs. "
            "Flip True only during cutover PR; reset to False post-UAT."
        ),
    )
    ```

    **Step 4.3 — Regenerate JSON schema:**

    ```bash
    cd /data/projets/perso/arr-stack/tools/arrconf
    uv run arrconf schema-gen --output ../../schemas/arrconf-schema.json
    ```

    The output file `schemas/arrconf-schema.json` should contain the updated `prune` description string under the JellyfinLibrariesSection definition. If `arrconf schema-gen` CLI is not available, the executor must locate the equivalent generator (per CLAUDE.md "schemas/arrconf-schema.json — généré par `arrconf schema-gen`") and invoke it. If neither approach works, document the gap in the SUMMARY for follow-up.

    **Do NOT touch** any other field, model, or section in `config.py`. Phase 16 scope is `JellyfinLibrariesSection` only.

    **Do NOT change** `default=False` — the chart's `charts/arr-stack/files/arrconf.yml` keeps `jellyfin.libraries.prune: false` by default. The operator flips manually during cutover (HUMAN-UAT scenario 3, Task 9).
  </action>
  <verify>
    <automated>cd /data/projets/perso/arr-stack && grep -q 'D-16-PRUNE-01' tools/arrconf/arrconf/config.py && grep -q 'D-16-PRUNE-01' schemas/arrconf-schema.json && ! grep -q 'MUST be False in Phase 7 (D-07-LIB-01)' tools/arrconf/arrconf/config.py</automated>
  </verify>
  <acceptance_criteria>
    - `tools/arrconf/arrconf/config.py` `JellyfinLibrariesSection` class docstring mentions `D-16-PRUNE-01` and `D-16-PATH-DELETE-01`
    - `tools/arrconf/arrconf/config.py` `prune` field description mentions `D-16-PRUNE-01` and no longer says "MUST be False in Phase 7"
    - The `prune` field default value is still `False` (operator opts in via YAML at cutover time)
    - `schemas/arrconf-schema.json` regenerated — contains the updated `prune` description string under JellyfinLibrariesSection (`grep -c "D-16-PRUNE-01" schemas/arrconf-schema.json` returns ≥ 1)
    - No other pydantic models in `config.py` modified
    - Existing tests that instantiate `JellyfinLibrariesSection()` with default `prune=False` (or `prune=True` explicitly) still construct without validation errors (covered by full test suite Task 7)
  </acceptance_criteria>
  <done>Pydantic docstring reflects D-16-PRUNE-01; JSON schema regenerated; default behavior unchanged (`prune=False`).</done>
</task>

<task type="auto" tdd="true">
  <name>Task 5: Rewrite `test_jellyfin_categories.py` — 10-lib generator tests</name>
  <files>tools/arrconf/tests/test_jellyfin_categories.py (rewrite)</files>
  <read_first>
    - tools/arrconf/tests/test_jellyfin_categories.py (current 143 LOC — 5 tests covering 2-super-libs behavior)
    - tools/arrconf/arrconf/generators/categories.py (post-Task-2 — the 10-lib generator)
    - .planning/phases/16-jellyfin-categories-as-libs/16-RESEARCH.md § "Phase Requirements → Test Map" (lines 902-923 — full test enumeration)
    - charts/arr-stack/files/arrconf.yml (lines 1-53 — production 10-category list, source of fixture truth)
  </read_first>
  <behavior>
    See Task 2 `<behavior>` block — 6 tests covering:
    1. 10-lib emission count
    2. `kind → collection_type` mapping (5 tvshows + 5 movies)
    3. Names match `display` field
    4. Single path per lib
    5. Order follows `cfg.categories` order
    6. Empty cfg → empty list
  </behavior>
  <action>
    Rewrite `tools/arrconf/tests/test_jellyfin_categories.py` from scratch. Preserve the existing `PRODUCTION_CATEGORIES` fixture data block (it matches `charts/arr-stack/files/arrconf.yml` lines 1-53 verbatim) and the `_build_cfg()` helper. Replace the 5 existing tests with 6 new tests reflecting the new 10-lib generator contract.

    Full file content:

    ```python
    """Phase 16 wiring test: Categories → 10 Jellyfin libs (REQ-jellyfin-categories-as-libs).

    Phase 16 (D-16-LIB-CREATE-01 + D-16-LIB-NAME-01 + D-16-COLLECTIONTYPE-01) replaces
    the Phase 7 / Phase 10 ``2 super-libs (Séries, Films) with multi-path PathInfos``
    design. Each Category in ``cfg.categories`` becomes its own JellyfinLibrary with
    a single PathInfo /media/<name>.

    Fixture mirrors the production ``charts/arr-stack/files/arrconf.yml`` 10-category list.
    """

    from __future__ import annotations

    from arrconf.config import RootConfig
    from arrconf.generators.categories import generate_jellyfin_libraries

    PRODUCTION_CATEGORIES = [
        {"name": "series", "kind": "series", "profile": "general",
         "display": "Séries", "base_path": "/media/series"},
        {"name": "series-emilie", "kind": "series", "profile": "general",
         "display": "Séries - Émilie", "base_path": "/media/series-emilie"},
        {"name": "series-thomas", "kind": "series", "profile": "general",
         "display": "Séries - Thomas", "base_path": "/media/series-thomas"},
        {"name": "series-garcons", "kind": "series", "profile": "family",
         "display": "Séries - Garçons", "base_path": "/media/series-garcons"},
        {"name": "series-zoe", "kind": "series", "profile": "anime",
         "display": "Séries - Zoé", "base_path": "/media/series-zoe"},
        {"name": "films", "kind": "movies", "profile": "general",
         "display": "Films", "base_path": "/media/films"},
        {"name": "nouveaux-films", "kind": "movies", "profile": "general",
         "display": "Nouveaux Films", "base_path": "/media/nouveaux-films"},
        {"name": "films-enfants", "kind": "movies", "profile": "family",
         "display": "Films - Enfants", "base_path": "/media/films-enfants"},
        {"name": "films-animation-enfants", "kind": "movies", "profile": "family",
         "display": "Films - Animation Enfants", "base_path": "/media/films-animation-enfants"},
        {"name": "films-zoe", "kind": "movies", "profile": "anime",
         "display": "Films - Zoé", "base_path": "/media/films-zoe"},
    ]


    def _build_cfg() -> RootConfig:
        return RootConfig.model_validate({"categories": PRODUCTION_CATEGORIES})


    def test_generate_jellyfin_libraries_ten_libs() -> None:
        """REQ-jellyfin-categories-as-libs: 10 categories → 10 JellyfinLibrary entries."""
        cfg = _build_cfg()
        libs = generate_jellyfin_libraries(cfg)
        assert len(libs) == 10


    def test_generate_jellyfin_libraries_collection_type_mapping() -> None:
        """D-16-COLLECTIONTYPE-01: kind='series' → tvshows, kind='movies' → movies."""
        cfg = _build_cfg()
        libs = generate_jellyfin_libraries(cfg)

        series_libs = [lib for lib in libs if lib.collection_type == "tvshows"]
        movies_libs = [lib for lib in libs if lib.collection_type == "movies"]
        assert len(series_libs) == 5
        assert len(movies_libs) == 5

        # Cross-check pairing: kind matches collection_type position-by-position.
        for cat, lib in zip(PRODUCTION_CATEGORIES, libs, strict=True):
            expected = "tvshows" if cat["kind"] == "series" else "movies"
            assert lib.collection_type == expected, (
                f"Category {cat['name']!r} (kind={cat['kind']!r}) → "
                f"expected collection_type={expected!r}, got {lib.collection_type!r}"
            )


    def test_generate_jellyfin_libraries_names_match_display() -> None:
        """D-16-LIB-NAME-01: lib.name = categories[].display (UTF-8 verbatim)."""
        cfg = _build_cfg()
        libs = generate_jellyfin_libraries(cfg)

        expected_names = [c["display"] for c in PRODUCTION_CATEGORIES]
        actual_names = [lib.name for lib in libs]
        assert actual_names == expected_names

        # Explicit UTF-8 spot-checks (guard against accidental normalization).
        assert "Séries - Émilie" in actual_names
        assert "Séries - Zoé" in actual_names
        assert "Films - Animation Enfants" in actual_names


    def test_generate_jellyfin_libraries_paths_single_per_lib() -> None:
        """Each lib has exactly 1 PathInfo: /media/<categories[].name>."""
        cfg = _build_cfg()
        libs = generate_jellyfin_libraries(cfg)

        for cat, lib in zip(PRODUCTION_CATEGORIES, libs, strict=True):
            assert len(lib.paths) == 1
            assert lib.paths[0] == cat["base_path"]
            assert lib.paths[0] == f"/media/{cat['name']}"


    def test_generate_jellyfin_libraries_order_follows_categories() -> None:
        """Generator preserves cfg.categories ordering (deterministic for tests + ops)."""
        cfg = _build_cfg()
        libs = generate_jellyfin_libraries(cfg)

        for cat, lib in zip(PRODUCTION_CATEGORIES, libs, strict=True):
            assert lib.name == cat["display"]


    def test_generate_jellyfin_libraries_empty_cfg() -> None:
        """Empty cfg.categories → empty list (no implicit super-libs — Phase 16 reversal)."""
        cfg_empty = RootConfig()
        libs = generate_jellyfin_libraries(cfg_empty)
        assert libs == []
    ```

    **Do NOT preserve** the old tests:
    - `test_jellyfin_libraries_wiring` (asserted 2 libs, obsolete)
    - `test_jellyfin_libraries_path_content` (asserted multi-path super-libs, obsolete)
    - `test_jellyfin_no_categories_returns_two_empty_libraries` (asserted always-2-libs, Phase 16 reverses this)
    - `test_jellyfin_only_series_no_movies` (asserted 2-lib shape with empty Films, obsolete)
    - `test_jellyfin_libraries_order` (asserted `[Séries, Films]` order, obsolete)

    Replace ENTIRELY. Run `cd tools/arrconf && uv run pytest tests/test_jellyfin_categories.py -x` after writing to verify the 6 new tests pass against the Task 2 generator.
  </action>
  <verify>
    <automated>cd /data/projets/perso/arr-stack/tools/arrconf && uv run pytest tests/test_jellyfin_categories.py -x -q 2>&1 | tail -5 | grep -E '6 passed|^=+ 6 passed'</automated>
  </verify>
  <acceptance_criteria>
    - File contains exactly 6 top-level `def test_*` functions
    - Test names: `test_generate_jellyfin_libraries_ten_libs`, `test_generate_jellyfin_libraries_collection_type_mapping`, `test_generate_jellyfin_libraries_names_match_display`, `test_generate_jellyfin_libraries_paths_single_per_lib`, `test_generate_jellyfin_libraries_order_follows_categories`, `test_generate_jellyfin_libraries_empty_cfg`
    - File does NOT contain references to the old 2-lib expectations: `grep -c "len(generated) == 2" tools/arrconf/tests/test_jellyfin_categories.py` returns 0
    - File does NOT contain `name="Séries"` / `name="Films"` as assertion targets (the 10-lib fixture references `display` field strings)
    - `cd tools/arrconf && uv run pytest tests/test_jellyfin_categories.py -v` reports 6 passed, 0 failed
    - PRODUCTION_CATEGORIES list has exactly 10 entries (verifiable: `python -c "from tools.arrconf.tests.test_jellyfin_categories import PRODUCTION_CATEGORIES; assert len(PRODUCTION_CATEGORIES) == 10"` returns 0)
  </acceptance_criteria>
  <done>Generator test file rewritten with 6 tests reflecting the 10-lib contract; all pass; no legacy 2-lib assertions remain.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 6: Extend `test_reconcilers_jellyfin.py` — 8 new tests for lifecycle (CREATE + prune + 404 + dry_run) + add post-cutover fixture</name>
  <files>tools/arrconf/tests/test_reconcilers_jellyfin.py (append 8 new tests), tools/arrconf/tests/fixtures/jellyfin/library_virtualfolders_post_phase16.json (new file)</files>
  <read_first>
    - tools/arrconf/tests/test_reconcilers_jellyfin.py (full file — 1044 LOC; especially lines 1-247 for helpers + lines 320-435 for `test_libraries_path_idempotent_pitfall2` and `test_libraries_set_membership_uses_pathinfos_not_locations_pitfall8` patterns to mirror)
    - tools/arrconf/tests/fixtures/jellyfin/library_virtualfolders.json (existing 2-lib fixture — clone shape for the new 10-lib post-cutover fixture)
    - tools/arrconf/arrconf/reconcilers/jellyfin.py (post-Task-3 — the rewritten reconciler)
    - .planning/phases/16-jellyfin-categories-as-libs/16-RESEARCH.md § "GET `/Library/VirtualFolders` response (post-Phase-16 expected, fixture target)" (lines 727-761) — fixture JSON shape
    - .planning/phases/16-jellyfin-categories-as-libs/16-RESEARCH.md § "Phase Requirements → Test Map" (lines 902-923 — full test names)
  </read_first>
  <behavior>
    See Task 3 `<behavior>` block — 8 tests covering CREATE happy path, Pitfall 16-1 guard, prune-paths on/off, prune-libs on/off, Pitfall 16-2 (404 tolerance), dry_run guard.
  </behavior>
  <action>
    **Step 6.1 — Create `tools/arrconf/tests/fixtures/jellyfin/library_virtualfolders_post_phase16.json`:**

    Write a JSON file containing 10 JellyfinLibrary objects in the shape used by GET `/Library/VirtualFolders`. Use the structure from `16-RESEARCH.md` lines 727-761. Each lib has `Name`, `ItemId` (unique fake UUID), `CollectionType`, `Locations`, `LibraryOptions.PathInfos`, `RefreshStatus`. The 10 names + paths follow `PRODUCTION_CATEGORIES`. Sample entry:

    ```json
    [
      {
        "Name": "Séries",
        "ItemId": "10000000000000000000000000000001",
        "CollectionType": "tvshows",
        "Locations": ["/media/series"],
        "LibraryOptions": {"PathInfos": [{"Path": "/media/series"}]},
        "RefreshStatus": "Idle"
      },
      {
        "Name": "Séries - Émilie",
        "ItemId": "10000000000000000000000000000002",
        "CollectionType": "tvshows",
        "Locations": ["/media/series-emilie"],
        "LibraryOptions": {"PathInfos": [{"Path": "/media/series-emilie"}]},
        "RefreshStatus": "Idle"
      },
      ... (8 more entries — see PRODUCTION_CATEGORIES from Task 5 + RESEARCH §727-761 for full template)
    ]
    ```

    All 10 entries — names in this exact order: `Séries`, `Séries - Émilie`, `Séries - Thomas`, `Séries - Garçons`, `Séries - Zoé`, `Films`, `Nouveaux Films`, `Films - Enfants`, `Films - Animation Enfants`, `Films - Zoé`. CollectionType: first 5 = `tvshows`, last 5 = `movies`. ItemIds: sequential fake UUIDs `1000…0001` through `1000…0010` (32-char hex strings).

    **Step 6.2 — Add 8 new tests to `test_reconcilers_jellyfin.py`** (append at end of file or interleaved with existing library tests; the executor's preference). Each test follows the existing `respx.mock` + `_make_client()` + `_make_instance()` pattern from the file.

    Helper to add near the top (after `_library_fixture`):

    ```python
    def _ten_lib_desired() -> list[JellyfinLibrary]:
        """Post-Phase-16 desired state — 10 libs (5 tvshows + 5 movies, 1 path each)."""
        return [
            JellyfinLibrary(name="Séries", collection_type="tvshows", paths=["/media/series"]),
            JellyfinLibrary(name="Séries - Émilie", collection_type="tvshows", paths=["/media/series-emilie"]),
            JellyfinLibrary(name="Séries - Thomas", collection_type="tvshows", paths=["/media/series-thomas"]),
            JellyfinLibrary(name="Séries - Garçons", collection_type="tvshows", paths=["/media/series-garcons"]),
            JellyfinLibrary(name="Séries - Zoé", collection_type="tvshows", paths=["/media/series-zoe"]),
            JellyfinLibrary(name="Films", collection_type="movies", paths=["/media/films"]),
            JellyfinLibrary(name="Nouveaux Films", collection_type="movies", paths=["/media/nouveaux-films"]),
            JellyfinLibrary(name="Films - Enfants", collection_type="movies", paths=["/media/films-enfants"]),
            JellyfinLibrary(name="Films - Animation Enfants", collection_type="movies", paths=["/media/films-animation-enfants"]),
            JellyfinLibrary(name="Films - Zoé", collection_type="movies", paths=["/media/films-zoe"]),
        ]


    def _legacy_2_lib_cluster_fixture() -> list[dict[str, Any]]:
        """Pre-cutover cluster GET: 2 super-libs with multi-path PathInfos."""
        return [
            {
                "Name": "Séries",
                "ItemId": "d565273fd114d77bdf349a2896867069",
                "CollectionType": "tvshows",
                "Locations": ["/media/series", "/media/anime", "/media/family"],
                "LibraryOptions": {"PathInfos": [
                    {"Path": "/media/series"},
                    {"Path": "/media/anime"},
                    {"Path": "/media/family"},
                ]},
            },
            {
                "Name": "Films",
                "ItemId": "db4c1708cbb5dd1676284a40f2950aba",
                "CollectionType": "movies",
                "Locations": ["/media/films", "/media/films-anime", "/media/films-family"],
                "LibraryOptions": {"PathInfos": [
                    {"Path": "/media/films"},
                    {"Path": "/media/films-anime"},
                    {"Path": "/media/films-family"},
                ]},
            },
        ]
    ```

    The 8 tests (use the existing test style — `@respx.mock` decorator, `respx.get(...)`, `respx.post(...)`, `respx.delete(...)`, `client.get(...)` to verify call count via `respx_mock.calls` if needed):

    ```python
    @respx.mock
    def test_library_create_uses_query_params_and_empty_body() -> None:
        """Pattern 1: POST /Library/VirtualFolders with query params + body={}."""
        # GET returns empty cluster (no libs exist).
        respx.get(f"{JELLYFIN_BASE}/Library/VirtualFolders").mock(return_value=httpx.Response(200, json=[]))
        post_route = respx.post(f"{JELLYFIN_BASE}/Library/VirtualFolders").mock(return_value=httpx.Response(204))

        client = _make_client()
        section = JellyfinLibrariesSection(enable=True, prune=False)
        desired = [JellyfinLibrary(name="Séries - Émilie", collection_type="tvshows", paths=["/media/series-emilie"])]

        from arrconf.reconcilers.jellyfin import _reconcile_libraries
        actions = _reconcile_libraries(client, section, desired, dry_run=False)

        assert post_route.called is True
        assert post_route.call_count == 1
        # Inspect the captured request — query params must match.
        request = post_route.calls.last.request
        assert request.url.params["name"] == "Séries - Émilie"
        assert request.url.params["collectionType"] == "tvshows"
        assert request.url.params["paths"] == "/media/series-emilie"
        assert request.url.params["refreshLibrary"] == "false"
        # Body must be empty JSON {}
        assert json.loads(request.content) == {}
        assert any("library_created:Séries - Émilie" in a for a in actions)


    @respx.mock
    def test_library_create_skipped_when_name_already_exists() -> None:
        """Pitfall 16-1: POST not idempotent — match by Name in pre-fetched snapshot."""
        # Cluster already has a lib named Séries (matches desired).
        cluster_fixture = [{
            "Name": "Séries",
            "ItemId": "d565273f...",
            "CollectionType": "tvshows",
            "Locations": ["/media/series"],
            "LibraryOptions": {"PathInfos": [{"Path": "/media/series"}]},
        }]
        respx.get(f"{JELLYFIN_BASE}/Library/VirtualFolders").mock(return_value=httpx.Response(200, json=cluster_fixture))
        post_route = respx.post(f"{JELLYFIN_BASE}/Library/VirtualFolders").mock(return_value=httpx.Response(204))

        client = _make_client()
        section = JellyfinLibrariesSection(enable=True, prune=False)
        desired = [JellyfinLibrary(name="Séries", collection_type="tvshows", paths=["/media/series"])]

        from arrconf.reconcilers.jellyfin import _reconcile_libraries
        actions = _reconcile_libraries(client, section, desired, dry_run=False)

        # CRITICAL: no CREATE call must fire.
        assert post_route.called is False
        # And no "library_created" in actions (the existing path is already there, so no path-add either).
        assert all("library_created" not in a for a in actions)


    @respx.mock
    def test_library_prune_paths_removes_excess() -> None:
        """D-16-PATH-DELETE-01: prune=True → DELETE /Library/VirtualFolders/Paths for excess."""
        # Cluster: legacy Séries with 3 paths. Desired: Séries with 1 path.
        respx.get(f"{JELLYFIN_BASE}/Library/VirtualFolders").mock(
            return_value=httpx.Response(200, json=_legacy_2_lib_cluster_fixture()),
        )
        delete_route = respx.delete(f"{JELLYFIN_BASE}/Library/VirtualFolders/Paths").mock(return_value=httpx.Response(204))

        client = _make_client()
        section = JellyfinLibrariesSection(enable=True, prune=True)
        desired = [
            JellyfinLibrary(name="Séries", collection_type="tvshows", paths=["/media/series"]),
            JellyfinLibrary(name="Films", collection_type="movies", paths=["/media/films"]),
        ]

        from arrconf.reconcilers.jellyfin import _reconcile_libraries
        actions = _reconcile_libraries(client, section, desired, dry_run=False)

        # Séries: prune /media/anime + /media/family (2 calls)
        # Films:  prune /media/films-anime + /media/films-family (2 calls)
        # Total: 4 DELETE Paths.
        assert delete_route.call_count == 4
        # Verify sorted deterministic order — for Séries, /media/anime sorts before /media/family.
        séries_calls = [c for c in delete_route.calls if c.request.url.params.get("name") == "Séries"]
        séries_paths_deleted = [c.request.url.params["path"] for c in séries_calls]
        assert séries_paths_deleted == sorted(séries_paths_deleted)


    @respx.mock
    def test_library_prune_paths_disabled_when_prune_false() -> None:
        """D-16-PRUNE-01: prune=False → reconciler does NOT issue DELETE Paths."""
        respx.get(f"{JELLYFIN_BASE}/Library/VirtualFolders").mock(
            return_value=httpx.Response(200, json=_legacy_2_lib_cluster_fixture()),
        )
        delete_paths_route = respx.delete(f"{JELLYFIN_BASE}/Library/VirtualFolders/Paths").mock(return_value=httpx.Response(204))
        delete_lib_route = respx.delete(f"{JELLYFIN_BASE}/Library/VirtualFolders").mock(return_value=httpx.Response(204))

        client = _make_client()
        section = JellyfinLibrariesSection(enable=True, prune=False)
        desired = [
            JellyfinLibrary(name="Séries", collection_type="tvshows", paths=["/media/series"]),
            JellyfinLibrary(name="Films", collection_type="movies", paths=["/media/films"]),
        ]

        from arrconf.reconcilers.jellyfin import _reconcile_libraries
        _reconcile_libraries(client, section, desired, dry_run=False)

        assert delete_paths_route.called is False
        assert delete_lib_route.called is False


    @respx.mock
    def test_library_prune_lib_removes_orphans() -> None:
        """D-16-PRUNE-01: prune=True → DELETE /Library/VirtualFolders for orphan libs."""
        # Cluster has 'ManualLib' which is NOT in the desired set.
        cluster_fixture = _legacy_2_lib_cluster_fixture() + [{
            "Name": "ManualLib",
            "ItemId": "manuallib-uuid",
            "CollectionType": "tvshows",
            "Locations": ["/media/manual"],
            "LibraryOptions": {"PathInfos": [{"Path": "/media/manual"}]},
        }]
        respx.get(f"{JELLYFIN_BASE}/Library/VirtualFolders").mock(return_value=httpx.Response(200, json=cluster_fixture))
        delete_route = respx.delete(f"{JELLYFIN_BASE}/Library/VirtualFolders").mock(return_value=httpx.Response(204))
        # Allow path-delete + path-add side-channels (not under test here)
        respx.delete(f"{JELLYFIN_BASE}/Library/VirtualFolders/Paths").mock(return_value=httpx.Response(204))
        respx.post(f"{JELLYFIN_BASE}/Library/VirtualFolders").mock(return_value=httpx.Response(204))
        respx.post(f"{JELLYFIN_BASE}/Library/VirtualFolders/Paths").mock(return_value=httpx.Response(204))

        client = _make_client()
        section = JellyfinLibrariesSection(enable=True, prune=True)
        desired = [
            JellyfinLibrary(name="Séries", collection_type="tvshows", paths=["/media/series"]),
            JellyfinLibrary(name="Films", collection_type="movies", paths=["/media/films"]),
        ]

        from arrconf.reconcilers.jellyfin import _reconcile_libraries
        actions = _reconcile_libraries(client, section, desired, dry_run=False)

        # Verify the DELETE Lib call fired ONCE for ManualLib (not for Séries or Films).
        delete_targets = [c.request.url.params.get("name") for c in delete_route.calls]
        assert delete_targets == ["ManualLib"]
        assert any("library_pruned:ManualLib" in a for a in actions)


    @respx.mock
    def test_library_prune_lib_tolerates_404() -> None:
        """Pitfall 16-2: DELETE /Library/VirtualFolders 404 → log library_already_absent, no raise."""
        cluster_fixture = _legacy_2_lib_cluster_fixture() + [{
            "Name": "GhostLib",
            "ItemId": "ghost-uuid",
            "CollectionType": "tvshows",
            "Locations": ["/media/ghost"],
            "LibraryOptions": {"PathInfos": [{"Path": "/media/ghost"}]},
        }]
        respx.get(f"{JELLYFIN_BASE}/Library/VirtualFolders").mock(return_value=httpx.Response(200, json=cluster_fixture))
        respx.delete(f"{JELLYFIN_BASE}/Library/VirtualFolders").mock(return_value=httpx.Response(404, text="Error processing request."))
        respx.delete(f"{JELLYFIN_BASE}/Library/VirtualFolders/Paths").mock(return_value=httpx.Response(204))
        respx.post(f"{JELLYFIN_BASE}/Library/VirtualFolders").mock(return_value=httpx.Response(204))
        respx.post(f"{JELLYFIN_BASE}/Library/VirtualFolders/Paths").mock(return_value=httpx.Response(204))

        client = _make_client()
        section = JellyfinLibrariesSection(enable=True, prune=True)
        desired = [
            JellyfinLibrary(name="Séries", collection_type="tvshows", paths=["/media/series"]),
            JellyfinLibrary(name="Films", collection_type="movies", paths=["/media/films"]),
        ]

        from arrconf.reconcilers.jellyfin import _reconcile_libraries
        # MUST NOT raise NotFoundError.
        actions = _reconcile_libraries(client, section, desired, dry_run=False)
        # And no "library_pruned:GhostLib" action emitted (since the DELETE 404'd).
        assert all("library_pruned:GhostLib" not in a for a in actions)


    @respx.mock
    def test_library_prune_lib_disabled_when_prune_false() -> None:
        """D-16-PRUNE-01: prune=False → no DELETE Lib calls even if orphans exist."""
        cluster_fixture = _legacy_2_lib_cluster_fixture() + [{
            "Name": "ManualLib",
            "ItemId": "ml-uuid",
            "CollectionType": "tvshows",
            "Locations": [],
            "LibraryOptions": {"PathInfos": []},
        }]
        respx.get(f"{JELLYFIN_BASE}/Library/VirtualFolders").mock(return_value=httpx.Response(200, json=cluster_fixture))
        delete_lib_route = respx.delete(f"{JELLYFIN_BASE}/Library/VirtualFolders").mock(return_value=httpx.Response(204))

        client = _make_client()
        section = JellyfinLibrariesSection(enable=True, prune=False)
        desired = [
            JellyfinLibrary(name="Séries", collection_type="tvshows", paths=["/media/series"]),
            JellyfinLibrary(name="Films", collection_type="movies", paths=["/media/films"]),
        ]

        from arrconf.reconcilers.jellyfin import _reconcile_libraries
        _reconcile_libraries(client, section, desired, dry_run=False)
        assert delete_lib_route.called is False


    @respx.mock
    def test_jellyfin_create_and_prune_dry_run() -> None:
        """dry_run=True → zero HTTP writes (CREATE / DELETE Path / DELETE Lib) — only dry_run_skip logs."""
        respx.get(f"{JELLYFIN_BASE}/Library/VirtualFolders").mock(
            return_value=httpx.Response(200, json=_legacy_2_lib_cluster_fixture()),
        )
        post_create = respx.post(f"{JELLYFIN_BASE}/Library/VirtualFolders").mock(return_value=httpx.Response(204))
        post_add_path = respx.post(f"{JELLYFIN_BASE}/Library/VirtualFolders/Paths").mock(return_value=httpx.Response(204))
        delete_path = respx.delete(f"{JELLYFIN_BASE}/Library/VirtualFolders/Paths").mock(return_value=httpx.Response(204))
        delete_lib = respx.delete(f"{JELLYFIN_BASE}/Library/VirtualFolders").mock(return_value=httpx.Response(204))

        client = _make_client()
        section = JellyfinLibrariesSection(enable=True, prune=True)
        desired = _ten_lib_desired()

        from arrconf.reconcilers.jellyfin import _reconcile_libraries
        actions = _reconcile_libraries(client, section, desired, dry_run=True)

        # No HTTP writes — only the initial GET fired.
        assert post_create.called is False
        assert post_add_path.called is False
        assert delete_path.called is False
        assert delete_lib.called is False

        # dry_run markers present in actions.
        assert any("library_create:dry_run:" in a for a in actions)
        # 8 new libs would be created (10 desired - 2 cluster present).
        create_dry_runs = [a for a in actions if "library_create:dry_run:" in a]
        assert len(create_dry_runs) == 8
    ```

    **Step 6.3 — Verify the Phase 7 carry-forward tests still pass:**

    The existing `test_libraries_path_idempotent_pitfall2` (line 320) and `test_libraries_set_membership_uses_pathinfos_not_locations_pitfall8` (line 376) use `_DEFAULT_LIBRARIES` (2-lib shape). After the Task 3 reconciler rewrite, these tests should still pass because the path-add branch (`_add_missing_paths`) is the Phase 7 logic verbatim. Confirm by running the full file: `cd tools/arrconf && uv run pytest tests/test_reconcilers_jellyfin.py -x`.

    If any Phase 7 test fails due to a subtle refactor side-effect, fix the refactor in Task 3 (the executor of Task 3 may need to re-run); do NOT delete or weaken the Phase 7 tests.

    Also confirm `test_reconcile_jellyfin_step_order_invariant` (line 866) and `test_jellyfin_does_not_call_arr_v3_quality_endpoints` (line 1004) remain green — these are scope-boundary tests that must NOT regress.
  </action>
  <verify>
    <automated>cd /data/projets/perso/arr-stack/tools/arrconf && test -f tests/fixtures/jellyfin/library_virtualfolders_post_phase16.json && python -c "import json; d=json.load(open('tests/fixtures/jellyfin/library_virtualfolders_post_phase16.json')); assert len(d)==10, f'expected 10 libs, got {len(d)}'; assert sum(1 for x in d if x['CollectionType']=='tvshows')==5; assert sum(1 for x in d if x['CollectionType']=='movies')==5" && uv run pytest tests/test_reconcilers_jellyfin.py -x -q 2>&1 | tail -3</automated>
  </verify>
  <acceptance_criteria>
    - `tools/arrconf/tests/fixtures/jellyfin/library_virtualfolders_post_phase16.json` exists, is valid JSON, contains an array of exactly 10 lib entries
    - The fixture has 5 entries with `"CollectionType": "tvshows"` and 5 with `"CollectionType": "movies"`
    - The fixture Names exactly match `["Séries", "Séries - Émilie", "Séries - Thomas", "Séries - Garçons", "Séries - Zoé", "Films", "Nouveaux Films", "Films - Enfants", "Films - Animation Enfants", "Films - Zoé"]` in this order
    - `tools/arrconf/tests/test_reconcilers_jellyfin.py` contains the 8 new test functions (verifiable: `grep -c "def test_library_create\\|def test_library_prune\\|def test_jellyfin_create_and_prune_dry_run" tools/arrconf/tests/test_reconcilers_jellyfin.py` returns ≥ 8)
    - Helper functions `_ten_lib_desired` and `_legacy_2_lib_cluster_fixture` are defined in the test file
    - `cd tools/arrconf && uv run pytest tests/test_reconcilers_jellyfin.py -v 2>&1 | grep -E "passed|failed"` reports `0 failed` and the total passed count is ≥ 22 (14 Phase 7 + 8 new)
    - The existing test `test_libraries_path_idempotent_pitfall2` still passes (Phase 7 carry-forward verified)
    - The existing test `test_jellyfin_does_not_call_arr_v3_quality_endpoints` still passes (ADR-5 frontière intact)
    - The existing test `test_reconcile_jellyfin_step_order_invariant` still passes (D-07-ORDER-01 carry-forward)
  </acceptance_criteria>
  <done>8 new reconciler tests added; new 10-lib fixture added; full jellyfin reconciler test file green; Phase 7 tests carry forward unchanged.</done>
</task>

<task type="auto">
  <name>Task 7: Triad gate — `uv run ruff format --check . && uv run ruff check . && uv run mypy .` + full pytest suite</name>
  <files>(verification-only; no file modification)</files>
  <read_first>
    - CLAUDE.md § "Code style" (triad enforcement rule)
    - tools/arrconf/pyproject.toml (mypy strict config)
  </read_first>
  <action>
    Run the full Python triad + pytest suite from `tools/arrconf/`. This is the EXACT same gate as CI (`.github/workflows/tests.yml`). If any step fails, the executor MUST fix and re-run; do not commit code that breaks the triad.

    ```bash
    cd /data/projets/perso/arr-stack/tools/arrconf
    uv run ruff format --check .
    uv run ruff check .
    uv run mypy .
    uv run pytest --cov=arrconf --cov-fail-under=70
    ```

    Expected outcomes:
    - `ruff format --check`: zero diffs (run `uv run ruff format .` to fix)
    - `ruff check`: zero violations (fix any new lint issues introduced by the refactor — usually unused imports or line length)
    - `mypy .`: zero errors (the new helpers `_create_library`, `_prune_library_paths`, `_prune_libraries`, `_add_missing_paths` all have full type annotations per Pattern 1-4)
    - `pytest --cov=arrconf --cov-fail-under=70`: all 384+ tests green (Phase 12 baseline) + new tests from Tasks 5 & 6 → total ≥ 384 + (6 generator - 5 deleted) + 8 reconciler = ~393 tests; coverage on `reconcilers/jellyfin.py` ≥ 70% per `pyproject.toml` config

    If `mypy` complains about `client._request(...)` (the helper invokes a name-mangled private method — Phase 7 carry-forward), the executor must verify the existing pattern in `_reconcile_libraries` uses the same call, and apply the same `# type: ignore[...]` only if it was already used in Phase 7 code. Otherwise mypy should be silent.

    If pytest fails on a Phase 7 test that isn't in scope (e.g. a Seerr or Sonarr test broke due to a side-effect of `config.py` schema regeneration), the executor must diagnose and patch — Phase 16 cannot ship with regressions outside its scope.
  </action>
  <verify>
    <automated>cd /data/projets/perso/arr-stack/tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy . && uv run pytest --cov=arrconf --cov-fail-under=70 -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - `uv run ruff format --check .` exits 0 with no diff output
    - `uv run ruff check .` exits 0 with no violations
    - `uv run mypy .` exits 0 with `Success: no issues found`
    - `uv run pytest --cov=arrconf --cov-fail-under=70` exits 0
    - Coverage line for `reconcilers/jellyfin.py` is ≥ 70% (CLAUDE.md REQ-test-coverage)
    - Coverage line for `generators/categories.py` is ≥ 70% (already ≥ 70% from Phase 10 — Phase 16 doesn't reduce it)
    - Total passed test count is ≥ 384 (Phase 12 baseline) + net new from Tasks 5 & 6 (i.e. ≥ ~393)
    - The output banner shows no `XFAIL`, no `XPASS`, no `ERROR` lines
  </acceptance_criteria>
  <done>Python triad green; full test suite green with coverage ≥ 70%; no regressions outside Phase 16 scope.</done>
</task>

<task type="auto">
  <name>Task 8: Chart-pin co-bump — `arrconf.image.tag: 0.7.0 → 0.8.0` in `charts/arr-stack/values.yaml`</name>
  <files>charts/arr-stack/values.yaml (modify line 451)</files>
  <read_first>
    - CLAUDE.md § "Release pin co-bump pattern" (CRITICAL — full section)
    - CLAUDE.md § "Accumulated-bumps escape hatch" (in case the operator has accumulated bumps — Phase 16 should not)
    - charts/arr-stack/values.yaml (current `arrconf.image.tag` at line 451 = `"0.7.0"`)
  </read_first>
  <action>
    Co-bump the arrconf image tag in `charts/arr-stack/values.yaml` from `"0.7.0"` to `"0.8.0"` (minor bump — Phase 16 ships a new feature: Categories-as-libs). This change MUST land in the SAME git commit as the `tools/arrconf/**` modifications from Tasks 2-6.

    **Exact edit:** Locate line 451 (or nearby — the file may shift), which currently reads:
    ```yaml
    arrconf:
      ...
      image:
        # renovate: image=ghcr.io/tom333/arr-stack-arrconf
        repository: ghcr.io/tom333/arr-stack-arrconf
        tag: "0.7.0"
    ```

    Change ONLY the `tag:` value to `"0.8.0"`. Do NOT touch:
    - The `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` annotation (CLAUDE.md "Ne pas supprimer l'annotation `# renovate: image=...`" — Renovate breaks without it)
    - The `repository:` value
    - Any other image tag in the file (sonarr, radarr, jellyfin, etc.)
    - The chart's own `Chart.yaml#version` (only the umbrella chart maintainer bumps this — Phase 16 lives on top of `chart v0.8.x`; the executor does NOT need to touch `Chart.yaml` unless the conventional release flow requires it; verify by reading `.planning/ROADMAP.md` Phase 16 entry which says "Chart version bumps accordingly per existing convention" — if the executor finds that the existing convention is to NOT touch Chart.yaml here, leave it; if convention IS to bump, bump consistently)

    **Why minor bump (not patch):** Phase 16 introduces a NEW capability (the reconciler now CREATEs libs, which it previously did not). Per CLAUDE.md "minor bump" definition: "nouveau reconciler ou nouvelle feature" — adding CREATE + DELETE branches to an existing reconciler is a new feature. SemVer 0.7.0 → 0.8.0 (not 0.7.1).

    **Critical invariant from CLAUDE.md:** "lorsqu'un commit modifie des fichiers sous `tools/arrconf/**` (code Python, Dockerfile, pyproject.toml), il doit **également** bumper `charts/arr-stack/values.yaml#arrconf.image.tag` dans **le même commit**."

    The executor MUST verify all `tools/arrconf/**` edits from Tasks 2-6 and this `charts/arr-stack/values.yaml` edit are staged together for ONE commit. If the workflow forces multiple commits (e.g. one per task), the FINAL commit on the branch before PR open MUST include the co-bump if any preceding commit on the branch touched `tools/arrconf/**`.

    **Renovate annotation grep guard:** After the edit, verify the annotation line is still on the line immediately above `repository:`:
    ```bash
    grep -B 1 'repository: ghcr.io/tom333/arr-stack-arrconf' charts/arr-stack/values.yaml | head -2
    # Expected: '# renovate: image=ghcr.io/tom333/arr-stack-arrconf' on the line above
    ```
  </action>
  <verify>
    <automated>grep -c '^            tag: "0.8.0"$' /data/projets/perso/arr-stack/charts/arr-stack/values.yaml | grep -qv '^0$' && grep -c '^            tag: "0.7.0"$' /data/projets/perso/arr-stack/charts/arr-stack/values.yaml | grep -q '^0$' && grep -B 1 'repository: ghcr.io/tom333/arr-stack-arrconf' /data/projets/perso/arr-stack/charts/arr-stack/values.yaml | grep -q 'renovate: image=ghcr.io/tom333/arr-stack-arrconf'</automated>
  </verify>
  <acceptance_criteria>
    - `charts/arr-stack/values.yaml` contains the exact line `            tag: "0.8.0"` under the `arrconf.image` block
    - The previous `            tag: "0.7.0"` line under `arrconf.image` is GONE
    - The line immediately above `repository: ghcr.io/tom333/arr-stack-arrconf` is `            # renovate: image=ghcr.io/tom333/arr-stack-arrconf` (annotation intact)
    - No other `tag:` line in `values.yaml` was modified (verifiable: `git diff charts/arr-stack/values.yaml | grep '^[+-]            tag:' | wc -l` returns 2 — one `-` for the old, one `+` for the new)
    - The `tools/arrconf/**` changes from Tasks 2-6 are staged or committed alongside this `charts/arr-stack/values.yaml` change (verifiable: `git status` shows both `tools/arrconf/` files and `charts/arr-stack/values.yaml` in the same staging area)
  </acceptance_criteria>
  <done>arrconf image tag co-bumped 0.7.0 → 0.8.0 alongside the Python code changes; Renovate annotation preserved; CLAUDE.md "Release pin co-bump pattern" satisfied.</done>
</task>

<task type="auto">
  <name>Task 9: Write `16-HUMAN-UAT.md` — 5 operator scenarios (3 mandatory + 1 carry-forward + 1 optional)</name>
  <files>.planning/phases/16-jellyfin-categories-as-libs/16-HUMAN-UAT.md (new file)</files>
  <read_first>
    - .planning/phases/16-jellyfin-categories-as-libs/16-RESEARCH.md § "Watched-State Risk Analysis" (lines 614-654)
    - .planning/phases/16-jellyfin-categories-as-libs/16-RESEARCH.md § "Open Questions" (lines 853-867)
    - .planning/phases/16-jellyfin-categories-as-libs/16-CONTEXT.md § "Open Items for Plan Phase" (UAT scenarios)
    - CLAUDE.md § "Filesystem migration v0.2.0 → v0.3.0" (the operator gate that prevents Pitfall 16-4)
    - .planning/phases/15-local-config-ui/15-B-HUMAN-UAT.md (example HUMAN-UAT format from a recent phase, if present)
  </read_first>
  <action>
    Create `.planning/phases/16-jellyfin-categories-as-libs/16-HUMAN-UAT.md` with the 5 operator scenarios. Follow the existing project convention: front-matter (phase + close-state), short context preamble, then numbered scenarios with `Given / When / Then / Status` blocks.

    Template content (executor: adapt prose voice to match the rest of `.planning/phases/*/15-B-HUMAN-UAT.md` if such a file exists for tone consistency):

    ```markdown
    # Phase 16 — Jellyfin Categories-as-libs — HUMAN UAT

    **Phase:** 16
    **Status:** in_progress (mandatory scenarios pending operator close-out)
    **Date:** 2026-05-24

    ## Context

    Phase 16 ships the refactor of `generate_jellyfin_libraries()` (10 libs, 1 per Category) and the extension of `_reconcile_libraries()` (CREATE + prune-gated DELETE). The code-side gates (Tasks 1-8) cover unit-test correctness and chart pin co-bump. The cutover itself — running `arrconf apply` against the live cluster after `helm upgrade` — requires the operator to validate live behavior because the cutover changes the visible Jellyfin lib structure that real users (the operator's family) interact with.

    **Pre-merge gate (operator-driven, before opening the PR):**

    - **G1 — Filesystem migration.** Operator must confirm the v0.2.0 → v0.3.0 filesystem migration runbook (CLAUDE.md § "Filesystem migration") has been executed, OR explicitly accept the watched-state loss for items currently under `/media/anime`, `/media/family`, `/media/films-anime`, `/media/films-family`. Without this confirmation, do not flip `prune: true`. The arrconf code change works either way, but the operator UX outcome depends on this.

    ## Scenarios

    ### Scenario 1 (MANDATORY for close) — Jellyfin web UI shows 10 libs post-cutover

    **Given** the operator has merged the Phase 16 PR (chart-pin `0.7.0 → 0.8.0`) and ArgoCD has synced.
    **Given** the operator has set `jellyfin.libraries.prune: true` in `charts/arr-stack/files/arrconf.yml` for the cutover PR (separate from the code PR or the same — operator choice).
    **When** the operator opens https://jellyfin.tgu.ovh/ in a browser and logs in.
    **Then** the Home page shows exactly **10 top-level libraries** with these names:
      1. `Séries`
      2. `Séries - Émilie`
      3. `Séries - Thomas`
      4. `Séries - Garçons`
      5. `Séries - Zoé`
      6. `Films`
      7. `Nouveaux Films`
      8. `Films - Enfants`
      9. `Films - Animation Enfants`
      10. `Films - Zoé`
    **Then** clicking each lib shows the content from `/media/<name>` (e.g. `Séries - Zoé` shows the items from `/media/series-zoe`).
    **Status:** ⏳ Pending operator close-out

    ### Scenario 2 (MANDATORY for close) — Watched-state survives on ≥ 3 series at preserved paths

    **Given** pre-cutover, the operator has noted 3 known-watched series in `/media/series` (paths that survive the reshape).
    **When** the operator browses each of these 3 series in their new lib (`Séries`) post-cutover.
    **Then** episodes that were watched pre-cutover still show as ✓ watched (Jellyfin UI dot indicator + "Resume from Xm" prompt).
    **Then** if any series shows lost watched state, the operator notes it in this file under "Watched-state losses" below for follow-up.

    **Watched-state losses (operator records here):**
    - (none yet)

    **Status:** ⏳ Pending operator close-out

    ### Scenario 3 (MANDATORY for close) — Operator flips `prune: false` after UAT

    **Given** Scenarios 1 and 2 have passed.
    **When** the operator opens a follow-up PR setting `jellyfin.libraries.prune: false` in `charts/arr-stack/files/arrconf.yml`.
    **When** the PR is merged and ArgoCD syncs.
    **Then** the next `arrconf apply` cycle (visible via `kubectl logs -n selfhost <arrconf-cronjob-pod>`) emits 0 `library_pruned` and 0 `library_path_pruned` events (the section is prune-gated false, no DELETE writes).
    **Then** any future user-added lib in the Jellyfin Dashboard (operator clicking "Add Media Library") survives the next reconcile (was the original v0.5.0 hardening goal — preserve operator's ad-hoc UI work).
    **Status:** ⏳ Pending operator close-out

    ### Scenario 4 (CARRY-FORWARD, NON-BLOCKING) — JellyCon LibreELEC top-level browse shows 10 libs

    **Given** the operator has installed JellyCon on the LibreELEC salon mini-PC (planning is operator-driven, not part of arr-stack code).
    **When** the operator opens JellyCon, signs in to the Jellyfin server, and navigates to the top-level browse view.
    **Then** the same 10 libs from Scenario 1 appear, each browsable as a folder.
    **Status:** ⏭ CARRY-FORWARD (per D-16-JELLYCON-UAT-01 — non-blocking for Phase 16 close; operator may exercise post-merge as JellyCon install lands)

    ### Scenario 5 (OPTIONAL) — Legacy v0.2.0 paths zombie sweep

    **Given** the operator either DID the filesystem migration before Phase 16 OR explicitly accepts the watched-state loss for unmigrated items.
    **When** the operator runs `kubectl exec -n selfhost deployment/jellyfin -- ls -la /media/anime /media/family /media/films-anime /media/films-family`.
    **Then** if any of these directories are non-empty, the operator decides per directory:
      - Migrate the content to a v0.3.0 bucket per CLAUDE.md "Filesystem migration" runbook, then re-trigger Jellyfin rescan.
      - Accept the items will disappear from Jellyfin (already happened post-cutover; files remain on NFS but no lib references them).
      - Optionally `rm -rf` the empty legacy dirs once vacated.
    **Then** the operator may close this scenario as "done" (clean) or "deferred" (will revisit later).
    **Status:** ☐ Optional — operator's discretion

    ## Close-out

    Phase 16 is considered CLOSED when:
    - Scenarios 1, 2, 3 are marked ✅ Passed by the operator (above)
    - Scenario 4 is marked ⏭ Carry-forward (acceptable per D-16-JELLYCON-UAT-01)
    - Scenario 5 is marked ☐ Optional (acceptable as deferred)

    Operator close-out command: edit this file to update statuses, then update `.planning/STATE.md` Phase 16 status to `complete`.
    ```

    **Do NOT** mark any scenario ✅ Passed in this initial write — they are all pending operator exercise. The executor's job is to create the document; the operator's job is to close it during/after the cutover.

    **Adapt** the URL `https://jellyfin.tgu.ovh/` if the operator's actual URL is different — check `charts/arr-stack/values.yaml` for the `jellyfin` ingress host, or fall back to `http://jellyfin.selfhost.svc.cluster.local:8096` for in-cluster access.
  </action>
  <verify>
    <automated>test -f /data/projets/perso/arr-stack/.planning/phases/16-jellyfin-categories-as-libs/16-HUMAN-UAT.md && grep -c '^### Scenario' /data/projets/perso/arr-stack/.planning/phases/16-jellyfin-categories-as-libs/16-HUMAN-UAT.md | grep -q '^5$' && grep -q 'MANDATORY for close' /data/projets/perso/arr-stack/.planning/phases/16-jellyfin-categories-as-libs/16-HUMAN-UAT.md && grep -q 'CARRY-FORWARD' /data/projets/perso/arr-stack/.planning/phases/16-jellyfin-categories-as-libs/16-HUMAN-UAT.md && grep -q 'D-16-JELLYCON-UAT-01' /data/projets/perso/arr-stack/.planning/phases/16-jellyfin-categories-as-libs/16-HUMAN-UAT.md</automated>
  </verify>
  <acceptance_criteria>
    - File `.planning/phases/16-jellyfin-categories-as-libs/16-HUMAN-UAT.md` exists
    - Contains exactly 5 `### Scenario` headers
    - Scenarios 1, 2, 3 contain the marker `MANDATORY for close`
    - Scenario 4 contains the marker `CARRY-FORWARD` and references `D-16-JELLYCON-UAT-01`
    - Scenario 5 contains the marker `OPTIONAL`
    - File references the 10 specific lib names verbatim (`Séries`, `Séries - Émilie`, ..., `Films - Zoé`)
    - File references the filesystem migration pre-gate (CLAUDE.md "Filesystem migration v0.2.0 → v0.3.0")
    - File contains a "Close-out" section explaining the close criteria
    - No scenario is pre-marked ✅ Passed (all are pending operator exercise)
  </acceptance_criteria>
  <done>HUMAN-UAT runbook created with 5 scenarios covering all operator close-out paths (mandatory web UI + watched-state + prune flip; carry-forward JellyCon; optional zombie sweep).</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 10: Operator checkpoint — Snapshot baseline + Triad green + Co-bump committed</name>
  <what-built>
    Tasks 1-9 deliver: ADR-6 pre-cutover snapshot, refactored generator (10 libs from 10 categories), extended reconciler (CREATE + prune-gated DELETE Path + DELETE Lib with 404 tolerance), updated pydantic docstring + regenerated JSON schema, rewritten generator tests (6 tests), extended reconciler tests (8 new tests + 1 new fixture), Python triad green, image tag co-bumped `0.7.0 → 0.8.0`, HUMAN-UAT runbook.

    What's NOT in this task: the actual cutover (helm upgrade, operator flipping `prune: true`, browser check of 10 libs in Jellyfin web UI). That happens after the operator merges this PR. The cutover validation is in `16-HUMAN-UAT.md` (Task 9) and is OPERATOR-driven, not executor-driven.
  </what-built>
  <how-to-verify>
    1. Confirm snapshot baseline exists and is committed:
       ```bash
       cd /data/projets/perso/arr-stack
       ls -la snapshots/before-phase-16-2026-05-24/jellyfin/
       git status snapshots/before-phase-16-2026-05-24/
       # Expected: at least one .json file in the dir + git status shows it staged/committed
       ```

    2. Confirm code triad + tests green:
       ```bash
       cd /data/projets/perso/arr-stack/tools/arrconf
       uv run ruff format --check . && uv run ruff check . && uv run mypy . && uv run pytest --cov=arrconf --cov-fail-under=70 -q
       # Expected: exit 0, all gates pass
       ```

    3. Confirm chart pin co-bumped + Renovate annotation preserved:
       ```bash
       cd /data/projets/perso/arr-stack
       grep -B 1 'repository: ghcr.io/tom333/arr-stack-arrconf' charts/arr-stack/values.yaml
       # Expected: shows the # renovate: ... annotation above the repository: line
       grep -A 2 '^    arrconf:' charts/arr-stack/values.yaml | grep 'tag:'
       # Expected: tag: "0.8.0"
       ```

    4. Confirm code-side artifacts cohere:
       ```bash
       cd /data/projets/perso/arr-stack
       # Generator no longer has hardcoded super-libs
       grep -c 'name="Séries"\|name="Films"' tools/arrconf/arrconf/generators/categories.py
       # Expected: 0
       # Reconciler has the new helpers
       grep -c 'def _create_library\|def _prune_library_paths\|def _prune_libraries' tools/arrconf/arrconf/reconcilers/jellyfin.py
       # Expected: 3
       # HUMAN-UAT runbook ready for operator
       wc -l .planning/phases/16-jellyfin-categories-as-libs/16-HUMAN-UAT.md
       # Expected: > 50 lines
       ```

    5. Confirm git working tree is clean (or the operator's deliberate staging):
       ```bash
       cd /data/projets/perso/arr-stack
       git status
       # Expected: modified tools/arrconf/{generators/categories.py, reconcilers/jellyfin.py, config.py}, modified tests, new fixture, modified schemas/arrconf-schema.json, modified charts/arr-stack/values.yaml, new .planning/phases/16-jellyfin-categories-as-libs/16-HUMAN-UAT.md, new snapshots/before-phase-16-2026-05-24/ — ALL grouped into one or two coherent commits
       ```

    If all 5 checks pass, the operator can proceed to:
    - Open the PR on `arr-stack` repo
    - Wait for CI green (chart-lint + tests + arrconf-image build)
    - Merge → auto-tag fires → image `:0.8.0` builds
    - Wait for Renovate PR on `my-kluster` to bump `targetRevision`
    - Merge `my-kluster` PR → ArgoCD sync deploys
    - Optionally open follow-up PR with `jellyfin.libraries.prune: true` for the cutover
    - Open browser to https://jellyfin.tgu.ovh/ → expect 10 libs (Scenario 1)
    - Exercise Scenarios 2-5 of `16-HUMAN-UAT.md`
    - Open final follow-up PR with `prune: false` to lock in the post-cutover state (Scenario 3)
  </how-to-verify>
  <resume-signal>
    Type "approved" once all 5 verification checks pass and the code is ready to commit/PR.
    OR describe blocking issues (e.g. "snapshot.sh failed — port-forward broken", "mypy errors in reconcilers/jellyfin.py line N", "Renovate annotation accidentally deleted").
  </resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| arrconf CronJob pod → Jellyfin REST API (in-cluster HTTP) | New write surface: POST + DELETE on `/Library/VirtualFolders` and `/Library/VirtualFolders/Paths`. Previously Phase 7 only POSTed `/Library/VirtualFolders/Paths`. |
| Operator-edited `arrconf.yml` (ConfigMap) → arrconf parsing | `jellyfin.libraries.prune` becomes opt-in via YAML (was hardcoded). Operator must understand the semantics. |
| Jellyfin lib state → end-user clients (web/Swiftfin/JellyCon) | Reshape happens in production. Watched-state DB may lose entries (Pitfall 16-4 — bounded by operator's pre-Phase-16 filesystem migration). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-16-01 | Tampering | `_reconcile_libraries` CREATE branch | mitigate | Pitfall 16-1 mitigation: match-by-Name pre-check against the pre-fetched cluster snapshot before POST `/Library/VirtualFolders`. Unit test `test_library_create_skipped_when_name_already_exists` enforces the contract. Without this guard, Jellyfin silently appends `2`, `3` suffixes — duplicated libs visible to end-user clients. |
| T-16-02 | Denial of Service (operational) | `_prune_libraries` DELETE branch | mitigate | Pitfall 16-2 mitigation: wrap DELETE `/Library/VirtualFolders` in try/except `NotFoundError` → log `library_already_absent`, continue with remaining libs. Without this guard, the first 404 aborts the entire `arrconf apply` run, leaving the cluster partially reshaped. Unit test `test_library_prune_lib_tolerates_404` enforces. |
| T-16-03 | Tampering | Operator-added libs during `prune: true` window | accept | Honest side-effect of D-16-PRUNE-01: when operator flips `prune: true` for the cutover PR, ANY lib not in `desired_libraries` (incl. operator's ad-hoc UI-added libs) gets deleted. Mitigated organizationally via HUMAN-UAT Scenario 3 (operator flips `prune: false` post-cutover). Single-tenant homelab — acceptable risk window. |
| T-16-04 | Information Disclosure (data loss) | Jellyfin `UserDatas` watched-state DB across cutover | accept (operator-gated) | Pitfall 16-4: items under unmigrated legacy paths (`/media/anime`, `/media/family`, `/media/films-anime`, `/media/films-family`) lose watched state after the lib reshape. arrconf does NOT touch `library.db` (CLAUDE.md frontière — arrconf never opens Jellyfin's SQLite). Mitigated organizationally via HUMAN-UAT pre-merge gate G1 (operator confirms filesystem migration done). |
| T-16-05 | Tampering | Image tag drift between code + chart values | mitigate | CLAUDE.md "Release pin co-bump pattern": Task 8 enforces same-commit bump of `charts/arr-stack/values.yaml#arrconf.image.tag` `0.7.0 → 0.8.0` alongside `tools/arrconf/**` changes. Without this, the new arrconf image is built but the chart still pulls `:0.7.0` → cluster runs old code while YAML expects new behavior. Phase 10 historical bug `12c05da` is the precedent. |
| T-16-06 | Elevation of Privilege | arrconf gaining new DELETE capability | mitigate | DELETE Lib + DELETE Path are BOTH gated by `section.prune == True`. Default is `prune: false`. Operator must explicitly opt-in for the cutover, then flip back. ADR-5 frontière unchanged — no new endpoints outside the Jellyfin Library REST surface. |
| T-16-07 | Information Disclosure | API key in JellyfinClient | mitigate | Carry-forward Phase 7 Pitfall 9 mitigation: MediaBrowser Token header preferred over `?api_key=` query param. Not touched in Phase 16. |
</threat_model>

<verification>
## Phase 16 verification gates

**Code-side (Tasks 1-8):**
1. `cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy . && uv run pytest --cov=arrconf --cov-fail-under=70` — all gates exit 0
2. Total test count ≥ 384 (Phase 12 baseline) + net new (~9-10) = ~393+
3. `reconcilers/jellyfin.py` coverage ≥ 70%
4. `charts/arr-stack/values.yaml` shows `tag: "0.8.0"` for arrconf with Renovate annotation intact
5. ADR-6 snapshot at `snapshots/before-phase-16-2026-05-24/jellyfin/` exists and is committed

**Cluster-side (Task 10 + post-merge operator UAT, see 16-HUMAN-UAT.md):**
6. After `helm upgrade` + operator flips `prune: true`, Jellyfin web UI shows 10 libs (Scenario 1)
7. 3 known-watched series at `/media/series` paths retain watched state post-cutover (Scenario 2)
8. Operator flips `prune: false` in follow-up PR; next `arrconf apply` emits 0 prune actions (Scenario 3)
9. SC#2 dispositive: a second `arrconf apply --dry-run --apps jellyfin` against the post-cutover cluster emits 0 `library_*` plan_actions
</verification>

<success_criteria>
Phase 16 is complete when ALL of the following are true:

- [ ] **SC#1 (ROADMAP)** — `helm upgrade` deploys image `:0.8.0`; Jellyfin web UI shows 10 top-level libs (1 per Category); each lib's `kind` matches the Category's `kind` field; each lib's single PathInfo is `/media/<name>`. Verified by operator (HUMAN-UAT Scenario 1).
- [ ] **SC#2 (ROADMAP)** — `arrconf apply` is idempotent post-cutover: a second run emits 0 `plan_action` events on `jellyfin.libraries`. D-07-LIB-01 hardcoded `prune: false` is reversed (D-16-PRUNE-01 — opt-in via YAML). Verified by Task 7 unit test green AND operator cluster-side spot check (HUMAN-UAT, dispositive after merge).
- [ ] **SC#3 (ROADMAP)** — Unit tests cover the 10-lib layout: `test_generate_jellyfin_libraries_*` (6 tests, Task 5) + `test_library_create_*` and `test_library_prune_*` (8 tests, Task 6). `categories[].kind → CollectionType` mapping asserted (`tvshows` / `movies`). The Phase 12 sweep test continues to pass.
- [ ] **SC#4 (ROADMAP)** — `charts/arr-stack/values.yaml#arrconf.image.tag` bumped from `0.7.0` to `0.8.0` (minor — Task 8). Renovate annotation preserved verbatim above `repository:`. Chart `version:` in `Chart.yaml` bumped per existing convention if/as required by the umbrella chart maintainer.
- [ ] **SC#5 (ROADMAP)** — Operator UAT (HUMAN-UAT, Task 9) confirms ≥ Scenario 1 (web UI 10 libs) + Scenario 2 (watched-state on 3 preserved series) + Scenario 3 (`prune: false` flip + 0-drift verification). Scenario 4 (JellyCon LibreELEC) is documented but non-blocking per D-16-JELLYCON-UAT-01. Scenario 5 (legacy paths sweep) is optional.

Additionally:

- [ ] ADR-6 snapshot baseline captured pre-cutover (Task 1) and committed to `snapshots/before-phase-16-2026-05-24/jellyfin/`
- [ ] Python triad green (`ruff format --check`, `ruff check`, `mypy`) — Task 7
- [ ] Pytest suite green with coverage ≥ 70% — Task 7
- [ ] ADR-5 frontière intact: existing `test_jellyfin_does_not_call_arr_v3_quality_endpoints` still green
- [ ] D-07-ORDER-01 step order intact: existing `test_reconcile_jellyfin_step_order_invariant` still green
- [ ] Pitfall 16-1 + 16-2 mitigations in code with dedicated unit tests
- [ ] HUMAN-UAT runbook ready for operator close-out (Task 9)
</success_criteria>

<output>
After completion, create `.planning/phases/16-jellyfin-categories-as-libs/16-A-SUMMARY.md` with:

- Phase 16 plan A objectives + status (closed / open / deferred per scenario)
- Files touched (with line-count deltas)
- Tests added (names + count)
- Pitfalls mitigated in code (Pitfall 16-1 match-by-Name, Pitfall 16-2 NotFoundError, Pitfall 16-3 single-GET discipline, Pitfall 16-4 documented operator gate)
- Chart-pin bump confirmed `0.7.0 → 0.8.0` with annotation preserved
- ADR-6 snapshot path
- Open HUMAN-UAT scenarios + close criteria
- Carry-forward items into v0.6.0+ backlog (if any emerged during execution)
- Cost (rough token usage if available)
</output>
