---
phase: 12-categories-deprecation
plan: A
type: execute
wave: 1
depends_on: []
files_modified:
  - tools/arrconf/arrconf/reconcilers/_shared.py
  - tools/arrconf/arrconf/__main__.py
  - tools/arrconf/arrconf/reconcilers/sonarr.py
  - tools/arrconf/arrconf/reconcilers/radarr.py
  - tools/arrconf/arrconf/reconcilers/qbittorrent.py
  - tools/arrconf/arrconf/reconcilers/jellyfin.py
  - tools/arrconf/arrconf/reconcilers/seerr.py
  - tools/arrconf/tests/test_merge_with_manual.py
  - charts/arr-stack/values.yaml
autonomous: true
requirements:
  - REQ-categories-deprecation
mode: standard

must_haves:
  truths:
    - "`merge_with_manual` function is removed from `_shared.py` (D-01, D-04, D-06)"
    - "All 22 callsites of `merge_with_manual(` in `__main__.py` are gone, replaced by direct passes of generator output (D-04)"
    - "`reconcile_sonarr` / `reconcile_radarr` accept a `*Derived` dataclass parameter (D-03)"
    - "`reconcile_qbittorrent` accepts a `list[QbitCategory]` parameter (D-03)"
    - "`reconcile_jellyfin` accepts a `list[JellyfinLibrary]` parameter (D-03)"
    - "`reconcile_seerr` accepts a resolved `animeTags: list[int]` parameter (D-03)"
    - "`_resolve_anime_tag_labels` survives — `_shared.py` still exports it"
    - "`test_merge_with_manual.py` is deleted (D-06)"
    - "Triade Python passes: `uv run ruff format --check . && uv run ruff check . && uv run mypy .` from `tools/arrconf/` (CLAUDE.md)"
    - "`charts/arr-stack/values.yaml#arrconf.image.tag` co-bumped 0.6.7 → 0.7.0 in this plan's commit (D-15, CLAUDE.md co-bump rule)"
  artifacts:
    - path: "tools/arrconf/arrconf/reconcilers/_shared.py"
      provides: "Survives without merge_with_manual; still exports _reconcile_remote_path_mappings + _resolve_download_client_tag_labels"
      excludes: "merge_with_manual"
    - path: "tools/arrconf/arrconf/__main__.py"
      provides: "apply + diff branches call generators directly and pass Derived/list to reconcilers"
      excludes: "merge_with_manual"
    - path: "tools/arrconf/arrconf/reconcilers/sonarr.py"
      provides: "reconcile_sonarr accepting derived: SonarrDerived"
    - path: "tools/arrconf/arrconf/reconcilers/radarr.py"
      provides: "reconcile_radarr accepting derived: RadarrDerived"
    - path: "tools/arrconf/arrconf/reconcilers/qbittorrent.py"
      provides: "reconcile_qbittorrent accepting categories: list[QbitCategory]"
    - path: "tools/arrconf/arrconf/reconcilers/jellyfin.py"
      provides: "reconcile_jellyfin accepting libraries: list[JellyfinLibrary]"
    - path: "tools/arrconf/arrconf/reconcilers/seerr.py"
      provides: "reconcile_seerr accepting animeTags: list[int]"
    - path: "charts/arr-stack/values.yaml"
      provides: "arrconf.image.tag = 0.7.0"
  key_links:
    - from: "arrconf/__main__.py apply branch (sonarr)"
      to: "arrconf/reconcilers/sonarr.py::reconcile_sonarr"
      via: "Pass generate_sonarr_resources(root) → derived param"
      pattern: "reconcile_sonarr\\(.*derived="
    - from: "arrconf/__main__.py diff branch"
      to: "arrconf/reconcilers/sonarr.py"
      via: "Same derived dataclass — eliminates Pitfall 5 false-drift"
      pattern: "generate_sonarr_resources\\(root\\)"
---

<objective>
Strip the v0.2.0 transition layer from arrconf's Python core. Delete `merge_with_manual` and its 22 callsites; refactor the 5 reconciler entry points to receive generator output directly via dataclass / list parameters (D-03); delete the unit-test file targeting the removed function; co-bump the chart's arrconf image tag in the SAME commit to honor the "Release pin co-bump pattern" (CLAUDE.md).

Purpose: After this plan, the apply/diff code paths funnel the categories generators' output straight into reconcilers — no toggle, no per-resource override. `_shared.py` shrinks to one helper (`_resolve_anime_tag_labels`, kept).

Output: 7 modified Python files + values.yaml bumped + 1 deleted test file. Triade Python passes locally; no test references `merge_with_manual` (the file deletion plus the import removal ensures `pytest` collection still passes).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/12-categories-deprecation/12-CONTEXT.md
@CLAUDE.md
@tools/arrconf/arrconf/__main__.py
@tools/arrconf/arrconf/reconcilers/_shared.py
@tools/arrconf/arrconf/generators/categories.py
@tools/arrconf/arrconf/reconcilers/sonarr.py
@tools/arrconf/arrconf/reconcilers/radarr.py
@tools/arrconf/arrconf/reconcilers/qbittorrent.py
@tools/arrconf/arrconf/reconcilers/jellyfin.py
@tools/arrconf/arrconf/reconcilers/seerr.py

<interfaces>
<!-- Load-bearing types from generators/categories.py — executor uses these as the contract -->

From tools/arrconf/arrconf/generators/categories.py:
```python
@dataclass
class SonarrDerived:
    tags: list[TagItem]
    root_folders: list[RootFolder]
    download_clients: list[DownloadClient]
    remote_path_mappings: list[RemotePathMapping]

@dataclass
class RadarrDerived:
    tags: list[TagItem]
    root_folders: list[RootFolder]
    download_clients: list[DownloadClient]
    remote_path_mappings: list[RemotePathMapping]

# Pure functions (no I/O):
def generate_qbit_categories(root: RootConfig) -> list[QbitCategory]: ...
def generate_sonarr_resources(root: RootConfig) -> SonarrDerived: ...
def generate_radarr_resources(root: RootConfig) -> RadarrDerived: ...
def generate_jellyfin_libraries(root: RootConfig) -> list[JellyfinLibrary]: ...
def generate_anime_tag_labels(root: RootConfig) -> list[str]: ...
```

From tools/arrconf/arrconf/reconcilers/_shared.py (keep):
```python
def _reconcile_remote_path_mappings(client, items, prune, dry_run) -> list[str]: ...
def _resolve_download_client_tag_labels(items, all_tags, app_name="Sonarr/Radarr") -> list: ...
```

Reconciler entry-point signatures POST-refactor (D-03 — copy verbatim):
```python
# sonarr.py
def reconcile_sonarr(
    client: SonarrClient,
    instance: SonarrInstance,
    derived: SonarrDerived,
    *,
    dry_run: bool,
) -> SonarrResult: ...

# radarr.py
def reconcile_radarr(
    client: RadarrClient,
    instance: RadarrInstance,
    derived: RadarrDerived,
    *,
    dry_run: bool,
) -> RadarrResult: ...

# qbittorrent.py
def reconcile_qbittorrent(
    client: QbittorrentClient,
    instance: QbittorrentInstance,
    categories: list[Category],   # arrconf.resources.qbittorrent.category.Category
    *,
    dry_run: bool,
) -> QbittorrentResult: ...

# jellyfin.py
def reconcile_jellyfin(
    client: JellyfinClient,
    instance: JellyfinInstance,
    libraries: list[JellyfinLibrary],
    *,
    dry_run: bool,
) -> JellyfinResult: ...

# seerr.py
def reconcile_seerr(
    client: SeerrClient,
    instance: SeerrInstance,
    anime_tags: list[int],
    *,
    dry_run: bool,
) -> SeerrResult: ...
```

Reconciler internals (UNCHANGED in this plan — only the entry-point reads the new param instead of `instance.<section>.items`):
- sonarr.py — internal helpers `_reconcile_tags`, `_reconcile_list_resource`, `_reconcile_host_config`, `_reconcile_series_tags`, `_reconcile_content_tags` keep their existing signatures
- Same for radarr/qbittorrent/jellyfin/seerr — only the public entry-point param shifts
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task A.1: Refactor reconciler entry-point signatures to accept generator output</name>
  <files>
    tools/arrconf/arrconf/reconcilers/sonarr.py,
    tools/arrconf/arrconf/reconcilers/radarr.py,
    tools/arrconf/arrconf/reconcilers/qbittorrent.py,
    tools/arrconf/arrconf/reconcilers/jellyfin.py,
    tools/arrconf/arrconf/reconcilers/seerr.py
  </files>
  <read_first>
    - tools/arrconf/arrconf/reconcilers/sonarr.py (full file — entry point line 459, body uses `instance.tags.items`, `instance.root_folders.items`, `instance.download_clients.items`, `instance.remote_path_mappings.items` — must redirect to `derived.tags`, `derived.root_folders`, etc.)
    - tools/arrconf/arrconf/reconcilers/radarr.py (entry point line 455, same pattern as sonarr)
    - tools/arrconf/arrconf/reconcilers/qbittorrent.py (entry point line 260, uses `instance.categories.items` → switch to `categories` param)
    - tools/arrconf/arrconf/reconcilers/jellyfin.py (entry point line 369, uses `instance.libraries.items` → switch to `libraries` param)
    - tools/arrconf/arrconf/reconcilers/seerr.py (entry point line 342, uses `instance.sonarr_service.animeTags` → switch to `anime_tags` param assigned onto `instance.sonarr_service.animeTags` at the top of the function body so existing internal logic is unchanged)
    - tools/arrconf/arrconf/generators/categories.py (definitive `SonarrDerived` / `RadarrDerived` dataclasses to import)
  </read_first>
  <action>
    Apply the 5 signature changes EXACTLY as listed in the `<interfaces>` block above. For each reconciler:

    1. **sonarr.py** — change `def reconcile_sonarr(client, instance, dry_run)` to `def reconcile_sonarr(client, instance, derived: SonarrDerived, *, dry_run)`. Add `from arrconf.generators.categories import SonarrDerived` at top. Inside the function body, locate every read of `instance.tags.items`, `instance.root_folders.items`, `instance.download_clients.items`, `instance.remote_path_mappings.items` and replace with `derived.tags`, `derived.root_folders`, `derived.download_clients`, `derived.remote_path_mappings` respectively. Do NOT modify internal helpers (`_reconcile_tags`, etc.) — only the lookups in `reconcile_sonarr`'s own body. **Approach guidance:** the simplest mechanical refactor is to assign `instance.tags.items = derived.tags` (etc.) at the top of the function body, so the internal helpers that still read `instance.<section>.items` continue to work without modification. This is a temporary intra-function shim; Plan B will remove the `.items` attribute from the pydantic model.

    2. **radarr.py** — identical pattern with `RadarrDerived` import.

    3. **qbittorrent.py** — change to `def reconcile_qbittorrent(client, instance, categories: list[Category], *, dry_run)`. `Category` is `arrconf.resources.qbittorrent.category.Category` (already imported in the file — verify). Inside the body, assign `instance.categories.items = categories` at the top so existing reads continue to work.

    4. **jellyfin.py** — change to `def reconcile_jellyfin(client, instance, libraries: list[JellyfinLibrary], *, dry_run)`. Assign `instance.libraries.items = libraries` at top.

    5. **seerr.py** — change to `def reconcile_seerr(client, instance, anime_tags: list[int], *, dry_run)`. Assign `instance.sonarr_service.animeTags = anime_tags` at top so the existing `_reconcile_sonarr_service` logic works unchanged.

    The mechanical-shim pattern (`instance.<section>.items = <param>` at the top of every reconciler) is INTENTIONAL: it minimises the diff in Plan A while letting Plan B remove the `.items` field cleanly once both refactors land. This is NOT a v1 — it is the final design (D-03 reads "Reconciler entry points take the generator output as a single dataclass parameter").
  </action>
  <verify>
    <automated>
      cd tools/arrconf && uv run python -c "from arrconf.reconcilers.sonarr import reconcile_sonarr; from arrconf.reconcilers.radarr import reconcile_radarr; from arrconf.reconcilers.qbittorrent import reconcile_qbittorrent; from arrconf.reconcilers.jellyfin import reconcile_jellyfin; from arrconf.reconcilers.seerr import reconcile_seerr; import inspect; sigs = {'sonarr': inspect.signature(reconcile_sonarr), 'radarr': inspect.signature(reconcile_radarr), 'qbit': inspect.signature(reconcile_qbittorrent), 'jellyfin': inspect.signature(reconcile_jellyfin), 'seerr': inspect.signature(reconcile_seerr)}; assert 'derived' in sigs['sonarr'].parameters, sigs['sonarr']; assert 'derived' in sigs['radarr'].parameters, sigs['radarr']; assert 'categories' in sigs['qbit'].parameters, sigs['qbit']; assert 'libraries' in sigs['jellyfin'].parameters, sigs['jellyfin']; assert 'anime_tags' in sigs['seerr'].parameters, sigs['seerr']; print('OK')"
    </automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "derived: SonarrDerived" tools/arrconf/arrconf/reconcilers/sonarr.py` exits 0
    - `grep -q "derived: RadarrDerived" tools/arrconf/arrconf/reconcilers/radarr.py` exits 0
    - `grep -q "categories: list\[Category\]" tools/arrconf/arrconf/reconcilers/qbittorrent.py` exits 0
    - `grep -q "libraries: list\[JellyfinLibrary\]" tools/arrconf/arrconf/reconcilers/jellyfin.py` exits 0
    - `grep -q "anime_tags: list\[int\]" tools/arrconf/arrconf/reconcilers/seerr.py` exits 0
    - `grep -q "from arrconf.generators.categories import SonarrDerived" tools/arrconf/arrconf/reconcilers/sonarr.py` exits 0
    - `grep -q "from arrconf.generators.categories import RadarrDerived" tools/arrconf/arrconf/reconcilers/radarr.py` exits 0
    - The python sanity-import command in `<verify>` prints `OK` and exits 0
  </acceptance_criteria>
  <done>5 reconciler entry-point signatures match D-03 verbatim; existing internal helpers are unchanged; the file imports the right dataclass.</done>
</task>

<task type="auto">
  <name>Task A.2: Delete `merge_with_manual`, simplify __main__.py, delete its test file, co-bump values.yaml</name>
  <files>
    tools/arrconf/arrconf/reconcilers/_shared.py,
    tools/arrconf/arrconf/__main__.py,
    tools/arrconf/tests/test_merge_with_manual.py,
    charts/arr-stack/values.yaml
  </files>
  <read_first>
    - tools/arrconf/arrconf/reconcilers/_shared.py (full file — `merge_with_manual` lives at lines 148-208; everything else stays)
    - tools/arrconf/arrconf/__main__.py (full file — 22 `merge_with_manual(` callsites distributed as: apply=lines 192/198/204/210/245/251/257/263/343/398/441 (11 callsites); diff=lines 551/557/563/569/598/604/610/616/672/716/740 (11 callsites). The `from arrconf.reconcilers._shared import merge_with_manual` line at line 36 must also be deleted)
    - tools/arrconf/tests/test_merge_with_manual.py (the file you are about to delete — read once to confirm it tests ONLY the removed function; do not skip this step)
    - CLAUDE.md §"Release pin co-bump pattern" (executor must understand the co-bump rule lives in THIS plan because it is the first/only code-touching commit of the phase)
    - charts/arr-stack/values.yaml (locate `arrconf:` block — `image: { repository: ghcr.io/tom333/arr-stack-arrconf, tag: "0.6.7" }`)
  </read_first>
  <action>
    Four file operations in this single task:

    **(1) Delete `merge_with_manual` from `_shared.py`:**
    Remove lines 148-208 (the `def merge_with_manual(...)` block — verify range with `grep -n "^def merge_with_manual" tools/arrconf/arrconf/reconcilers/_shared.py` before editing). Keep `_reconcile_remote_path_mappings` and `_resolve_download_client_tag_labels`. The `import structlog` and `log = structlog.get_logger()` at the top of the file stay (they are still used by `_reconcile_remote_path_mappings`).

    **(2) Delete the import and rewrite the 22 callsites in `__main__.py`:**
    a. Delete line 36: `from arrconf.reconcilers._shared import merge_with_manual`.
    b. In the **apply** function (`def apply` starting at line 166), replace each of the 11 callsite-blocks. The pattern transformation is:

    **Sonarr apply (currently lines 188-215) — replace this block:**
    ```python
            sonarr_derived = generate_sonarr_resources(root)
            instance.tags.items = merge_with_manual(
                instance.tags.items, sonarr_derived.tags, app="sonarr", resource="tags",
            )
            instance.root_folders.items = merge_with_manual(
                instance.root_folders.items, sonarr_derived.root_folders, app="sonarr", resource="root_folders",
            )
            instance.download_clients.items = merge_with_manual(
                instance.download_clients.items, sonarr_derived.download_clients, app="sonarr", resource="download_clients",
            )
            instance.remote_path_mappings.items = merge_with_manual(
                instance.remote_path_mappings.items, sonarr_derived.remote_path_mappings, app="sonarr", resource="remote_path_mappings",
            )
    ```
    **with:**
    ```python
            sonarr_derived = generate_sonarr_resources(root)
    ```
    and update the reconcile_sonarr call (currently at line 225) from `reconcile_sonarr(client, instance, dry_run=...)` to `reconcile_sonarr(client, instance, sonarr_derived, dry_run=...)`.

    **Radarr apply (currently lines 240-268) — replace similarly:**
    ```python
            radarr_derived = generate_radarr_resources(root)
    ```
    and update the reconcile_radarr call to pass `radarr_derived` as the third positional arg.

    **qBittorrent apply (currently lines 339-348) — replace the merge_with_manual block with:**
    ```python
            qbit_generated = generate_qbit_categories(root)
    ```
    and update reconcile_qbittorrent call to `reconcile_qbittorrent(qbit_client, qbit_instance, qbit_generated, dry_run=...)`.

    **Seerr apply (currently lines 397-403) — replace the merge_with_manual block with a direct assignment:**
    ```python
                resolved_anime_ids = _resolve_seerr_anime_tag_ids(root, sonarr_for_resolution, log)
    ```
    and update the reconcile_seerr call to `reconcile_seerr(seerr_client, seerr_instance, resolved_anime_ids, dry_run=...)`. (The `else:` branch that logs `seerr_animetags_resolution_skipped` stays; on that path, pass `resolved_anime_ids = []` to `reconcile_seerr`.)

    **Jellyfin apply (currently lines 440-446) — replace with:**
    ```python
            jellyfin_generated = generate_jellyfin_libraries(root)
    ```
    and update reconcile_jellyfin call to pass `jellyfin_generated` as 3rd arg.

    c. In the **diff** function (`def diff` starting at line 532), apply the same 6 transformations to the mirror branches (sonarr lines 549-574, radarr lines 597-621, qbit lines 671-677, seerr lines 706-721, jellyfin lines 739-745). The diff branches do NOT call the reconcilers — they call `diff_sonarr(client, root)`, `diff_radarr(client, root)`, etc. Those `diff_*` helpers currently rely on `instance.<section>.items` being pre-merged. After this refactor, the diff helpers must receive the derived inputs too — **but Pitfall 5 (same merged shape in apply and diff) is now structurally guaranteed because the generators are deterministic and called the same way in both branches**. To preserve the contract without touching `diff_cmd.py`, the diff branches keep a temporary one-line shim that assigns the generator output onto the instance attributes (mirroring the in-function shim the reconcilers will do):

    ```python
    # sonarr diff branch
    sonarr_diff_derived = generate_sonarr_resources(root)
    instance.tags.items = sonarr_diff_derived.tags
    instance.root_folders.items = sonarr_diff_derived.root_folders
    instance.download_clients.items = sonarr_diff_derived.download_clients
    instance.remote_path_mappings.items = sonarr_diff_derived.remote_path_mappings
    ```
    (Same pattern for radarr, qbit, jellyfin diff branches; seerr diff branch assigns `seerr_diff_instance.sonarr_service.animeTags = diff_resolved_anime_ids` directly.)

    This shim survives until Plan B removes the `.items` field — at which point `diff_cmd.py` will need a parallel refactor. **Within Plan A, the shim is acceptable because Plan B is the dependent wave-2 plan that will remove the `.items` attribute and refactor `diff_cmd.py` to accept the Derived dataclasses.** Note in a code comment: `# Plan A shim — Plan B removes the `.items` attribute and refactors diff_cmd.py`.

    **(3) Delete `tools/arrconf/tests/test_merge_with_manual.py` entirely** (`rm tools/arrconf/tests/test_merge_with_manual.py`). The file contains 6 tests all targeting the removed function: `test_manual_non_empty_wins`, `test_manual_empty_uses_generated`, `test_both_empty_returns_empty`, `test_log_event_manual_wins`, `test_log_event_generated_wins`, `test_app_and_resource_are_keyword_only`. They cannot survive deletion of `merge_with_manual` itself.

    **(4) Co-bump `charts/arr-stack/values.yaml`:**
    Change `tag: "0.6.7"` to `tag: "0.7.0"` under the `arrconf.image:` block (locate via the renovate annotation comment `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` — do NOT remove the annotation). Per CLAUDE.md §"Release pin co-bump pattern": this co-bump MUST be in the same commit as the arrconf code change. Minor bump because the reconciler internal-API signature changes (first such change of v0.4.0 per D-15).

    All four operations land in this single task because the co-bump rule from CLAUDE.md mandates same-commit colocation; splitting them would silently break the rule even if Plan D were committed in the same wave.
  </action>
  <verify>
    <automated>
      cd /data/projets/perso/arr-stack && \
      grep -q "^def merge_with_manual" tools/arrconf/arrconf/reconcilers/_shared.py && exit 1 ; \
      grep -cE "merge_with_manual\(" tools/arrconf/arrconf/__main__.py | grep -qE '^0$' || exit 2 ; \
      grep -q "from arrconf.reconcilers._shared import merge_with_manual" tools/arrconf/arrconf/__main__.py && exit 3 ; \
      test ! -f tools/arrconf/tests/test_merge_with_manual.py || exit 4 ; \
      grep -E '^\s+tag: "0\.7\.0"' charts/arr-stack/values.yaml | head -1 | grep -q '0.7.0' || exit 5 ; \
      cd tools/arrconf && uv run python -c "import arrconf.__main__; import arrconf.reconcilers._shared as s; assert not hasattr(s, 'merge_with_manual'), 'merge_with_manual still present'; print('OK')" && \
      uv run ruff format --check . && uv run ruff check . && uv run mypy . && echo "TRIADE OK"
    </automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "^def merge_with_manual" tools/arrconf/arrconf/reconcilers/_shared.py` returns 0
    - `grep -cE "merge_with_manual\(" tools/arrconf/arrconf/__main__.py` returns 0
    - `grep -q "from arrconf.reconcilers._shared import merge_with_manual" tools/arrconf/arrconf/__main__.py` exits 1 (no match)
    - `test ! -f tools/arrconf/tests/test_merge_with_manual.py` exits 0 (file is gone)
    - `grep -q "_resolve_anime_tag_labels\|_reconcile_remote_path_mappings\|_resolve_download_client_tag_labels" tools/arrconf/arrconf/reconcilers/_shared.py` exits 0 (other helpers survive)
    - `yq '.arrconf.image.tag' charts/arr-stack/values.yaml` returns `0.7.0` (with or without surrounding quotes)
    - `grep -q "# renovate: image=ghcr.io/tom333/arr-stack-arrconf" charts/arr-stack/values.yaml` exits 0 (annotation preserved per CLAUDE.md)
    - `cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy .` exits 0 (full Triade Python)
    - The full automated verify block in `<verify>` prints `TRIADE OK` as its final line
  </acceptance_criteria>
  <done>`merge_with_manual` is dead code purged from the codebase; `__main__.py` passes generator output directly into reconcilers; the unit-test file targeting the removed function is deleted; values.yaml is co-bumped; Triade Python green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| YAML → pydantic load_config | Operator-edited YAML crosses into in-memory model. Schema validation is the trust gate. |
| arrconf → *arr REST APIs | arrconf is a trusted controller (ADR-8) — payloads cross via httpx with API-key auth. |
| CronJob env → arrconf process | SealedSecret-injected API keys (SONARR_API_KEY, RADARR_API_KEY, JELLYFIN_API_KEY, SEERR_API_KEY, QBT_USER, QBT_PASS). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-12A-01 | Tampering | reconcile_sonarr (new signature) | mitigate | Pydantic strict mode on `SonarrDerived` (already a `@dataclass`, type-checked by mypy). No untrusted input crosses the boundary — `generate_sonarr_resources` is pure-function over the already-validated `RootConfig`. |
| T-12A-02 | Information Disclosure | log output in __main__ | accept | The deletion of `merge_with_manual` removes the `merge_decision` structlog event. No secrets were logged via that event (it only logged source name + count). No log-shape contract preserved (D-CONTEXT.md "Claude's Discretion" + CONTEXT §"Specifics"). |
| T-12A-03 | Denial of Service | apply loop (6 apps) | accept | Refactor is signature-only; no new I/O, no extra GETs. Performance characteristics identical to v0.3.0 (validated empirically by SC#5 in Plan E). |
| T-12A-04 | Elevation of Privilege | values.yaml co-bump path | mitigate | The bump 0.6.7 → 0.7.0 is patch-level chart-pin only. ArgoCD pulls the image with anonymous pull from GHCR public (ADR-3); the image itself runs USER 1000:1000 (Dockerfile). No new capabilities required. |
| T-12A-05 | Repudiation | git commit history | mitigate | Co-bump + code change land in the SAME commit (CLAUDE.md "Release pin co-bump pattern"); auditor can correlate image-tag → code change via single SHA. |
</threat_model>

<verification>
- `cd tools/arrconf && uv run pytest tests/ -k "not (sweep_manual_override_path or per_resource_override_tags_only or per_resource_override_rpm_only or manual_override_wins or animetags_merge_manual_wins or animetags_merge_empty_manual_uses_generated)" --tb=short -x` exits 0
  - The `-k` filter excludes the manual-path tests that Plans B and C will delete formally; this temporary exclusion lets Plan A's verification pass while leaving the test files untouched until those plans run.
- `cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy .` exits 0
- `grep -c "merge_with_manual" tools/arrconf/arrconf/` (recursive grep over the source tree) returns 0
- `grep -c "merge_with_manual" tools/arrconf/tests/` returns matches ONLY in tests Plan C will clean up (test_phase10_idempotence_sweep.py docstring + test names + override variants). Those references are NOT executed by the filtered pytest above.
</verification>

<success_criteria>
- SC#1 (`merge_with_manual` removed + callsites simplified) — SATISFIED structurally by this plan.
- SC#5 path enabled — `arrconf apply --dry-run` against a fixture-mocked cluster now uses the generator-direct code path with no behavioural change vs v0.3.0 (Plan E validates against live cluster).
- Co-bump rule honored — values.yaml + code in same commit (CLAUDE.md).
</success_criteria>

<output>
After completion, create `.planning/phases/12-categories-deprecation/12-A-reconciler-refactor-SUMMARY.md` documenting:
- The actual final callsite count (verify with `grep -cE "merge_with_manual\(" tools/arrconf/arrconf/__main__.py` post-edit — must be 0)
- The Plan A intra-function shim approach (`instance.<section>.items = derived.<field>` at the top of each reconciler) and why it stays until Plan B removes the `.items` field
- Confirmation Triade Python is green
- Confirmation values.yaml tag is `0.7.0` and renovate annotation survived
</output>
