---
phase: 10-categories-6-app-propagation
plan: 10-G-jellyfin-wiring
type: execute
wave: 2
depends_on:
  - 10-A-generators-categories
  - 10-B-merge-with-manual
files_modified:
  - tools/arrconf/arrconf/__main__.py
  - tools/arrconf/tests/test_jellyfin_categories.py
  - charts/arr-stack/values.yaml
autonomous: true
requirements:
  - REQ-categories-jellyfin-paths
requirements_addressed:
  - REQ-categories-jellyfin-paths (wiring side)
tags:
  - python
  - reconciler-wiring
  - jellyfin
  - chart-pin-cobump

must_haves:
  truths:
    - "`tools/arrconf/arrconf/__main__.py` Jellyfin branch (lines ~271-296) pre-merges via `generate_jellyfin_libraries(root)` + `merge_with_manual` on `jellyfin_instance.libraries.items` BEFORE `reconcile_jellyfin` call."
    - "When `jellyfin_instance.libraries.items == []` and `cfg.categories` has 5 series + 5 movies, the reconciler receives exactly 2 `JellyfinLibrary` objects: `Séries` with 5 paths (kind=series base_paths) and `Films` with 5 paths (kind=movies base_paths)."
    - "Manual override works: `jellyfin_instance.libraries.items` non-empty in YAML → reconciler sees manual list unchanged."
    - "`tools/arrconf/tests/test_jellyfin_categories.py` proves both happy path + manual override + existing Pitfall 2 set-membership shim continues to apply (paths already present in cluster → no_op)."
    - "Existing Jellyfin tests (`tests/test_reconcilers_jellyfin.py`) continue to pass."
    - "Phase 9 no-regression test still passes."
    - "`charts/arr-stack/values.yaml` arrconf.image.tag bumped 0.6.3 → 0.6.4 in the SAME commit (D-05 chart-pin co-bump)."
  artifacts:
    - path: "tools/arrconf/arrconf/__main__.py"
      provides: "Jellyfin pre-merge dispatch (apply + diff + dump)"
      contains: "generate_jellyfin_libraries"
    - path: "tools/arrconf/tests/test_jellyfin_categories.py"
      provides: "Jellyfin wiring tests (2 libraries, 5 paths each, manual override)"
      min_lines: 80
    - path: "charts/arr-stack/values.yaml"
      provides: "arrconf.image.tag bumped to 0.6.4"
      contains: "tag: \"0.6.4\""
  key_links:
    - from: "tools/arrconf/arrconf/__main__.py"
      to: "tools/arrconf/arrconf/generators/categories.py"
      via: "from arrconf.generators.categories import generate_jellyfin_libraries"
      pattern: "generate_jellyfin_libraries"
    - from: "tools/arrconf/arrconf/__main__.py"
      to: "jellyfin_instance.libraries.items"
      via: "in-place mutation after merge_with_manual"
      pattern: "jellyfin_instance\\.libraries\\.items ="
---

<objective>
Wire the Jellyfin reconciler to consume Categories-derived `JellyfinLibrary` objects (from Plan 10-A's `generate_jellyfin_libraries`) via the pre-merge mechanism in `__main__.py`. Produces 2 super-libraries (`Séries` + `Films`) with 5 paths each — the operator no longer needs to maintain library path lists by hand.

Purpose: Closes REQ-categories-jellyfin-paths. The existing `_reconcile_libraries` set-membership shim (Pitfall 2 — Phase 7) is unchanged — it correctly handles already-present paths regardless of whether they came from manual YAML or Categories.

Output: Single atomic commit with `__main__.py` pre-merge wiring + wiring tests + values.yaml tag bump 0.6.3 → 0.6.4 (D-05).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/10-categories-6-app-propagation/10-CONTEXT.md
@.planning/phases/10-categories-6-app-propagation/10-RESEARCH.md
@.planning/phases/10-categories-6-app-propagation/10-PATTERNS.md
@.planning/phases/10-categories-6-app-propagation/10-A-generators-categories-PLAN.md

@tools/arrconf/arrconf/__main__.py
@tools/arrconf/arrconf/reconcilers/jellyfin.py
@tools/arrconf/arrconf/resources/jellyfin/library.py
@tools/arrconf/arrconf/config.py
@charts/arr-stack/values.yaml

<interfaces>
<!-- Plan 10-A output — consumed here -->
```python
# arrconf/generators/categories.py
def generate_jellyfin_libraries(cfg: RootConfig) -> list[JellyfinLibrary]:
    """Returns 2 entries: 'Séries' (tvshows, kind=series base_paths) + 'Films' (movies, kind=movies base_paths)."""
```

<!-- JellyfinLibrariesSection holds .items: list[JellyfinLibrary] -->
<!-- _reconcile_libraries idempotence shim already at jellyfin.py:106-176 — read-only here -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 10-G-01: Pre-merge Jellyfin libraries in __main__.py (apply + diff + dump)</name>
  <files>tools/arrconf/arrconf/__main__.py, tools/arrconf/tests/test_jellyfin_categories.py</files>
  <read_first>
    - tools/arrconf/arrconf/__main__.py lines 271-296 (current Jellyfin apply branch)
    - tools/arrconf/arrconf/__main__.py (Jellyfin in `diff` + `dump` commands)
    - tools/arrconf/arrconf/generators/categories.py (generate_jellyfin_libraries signature)
    - tools/arrconf/arrconf/reconcilers/jellyfin.py lines 106-176 (_reconcile_libraries — read-only)
    - tools/arrconf/arrconf/resources/jellyfin/library.py (JellyfinLibrary fields)
    - 10-PATTERNS.md §"jellyfin.py — PathInfos wiring"
    - 10-RESEARCH.md §"Pattern 6: Jellyfin library paths"
  </read_first>
  <behavior>
    - Test 1: cfg with 5 series + 5 movies + empty manual → reconciler receives 2 JellyfinLibrary with `name="Séries"` (5 paths) and `name="Films"` (5 paths).
    - Test 2: Library order is `[Séries, Films]` (matches generator output).
    - Test 3: Manual override (non-empty `jellyfin_instance.libraries.items`) → reconciler sees manual list unchanged.
    - Test 4: existing `_reconcile_libraries` set-membership shim (Pitfall 2) continues to work — if cluster already has 5 series paths, no POST is issued for those paths.
    - Test 5: Phase 9 no-regression test stays green.
  </behavior>
  <action>
1. **Extend imports in `__main__.py`**:

```python
from arrconf.generators.categories import (
    generate_anime_tag_labels,
    generate_jellyfin_libraries,       # new in this plan
    generate_qbit_categories,
    generate_radarr_resources,
    generate_sonarr_resources,
)
```

2. **Inject pre-merge in the Jellyfin `apply` branch** (after `jellyfin_instance = root.jellyfin["main"]`, before `jellyfin_client = JellyfinClient(...)`):

```python
            # Phase 10 pre-merge (D-01/D-02): Categories→Jellyfin 2 super-libraries.
            # 'Séries' = kind=series base_paths (5); 'Films' = kind=movies base_paths (5).
            # Existing _reconcile_libraries set-membership shim (Pitfall 2) handles
            # the path-already-present case correctly — no change to reconciler needed.
            jellyfin_generated = generate_jellyfin_libraries(root)
            jellyfin_instance.libraries.items = merge_with_manual(
                jellyfin_instance.libraries.items,
                jellyfin_generated,
                app="jellyfin",
                resource="libraries",
            )
```

3. **Apply identical pre-merge in the Jellyfin branches of `diff` and `dump`** (Pitfall 5).

4. **Create the wiring test** `tools/arrconf/tests/test_jellyfin_categories.py`:

```python
"""Phase 10 wiring test: Categories→Jellyfin 2 super-libraries (REQ-categories-jellyfin-paths)."""

from __future__ import annotations

from arrconf.config import RootConfig
from arrconf.generators.categories import generate_jellyfin_libraries
from arrconf.reconcilers._shared import merge_with_manual
from arrconf.resources.jellyfin import JellyfinLibrary


PRODUCTION_CATEGORIES = [
    {"name": "films", "kind": "movies", "profile": "general", "display": "Films", "base_path": "/media/films"},
    {"name": "nouveaux-films", "kind": "movies", "profile": "general", "display": "Films - Nouveaux", "base_path": "/media/nouveaux-films"},
    {"name": "films-enfants", "kind": "movies", "profile": "family", "display": "Films - Enfants", "base_path": "/media/films-enfants"},
    {"name": "films-animation-enfants", "kind": "movies", "profile": "family", "display": "Films - Animation Enfants", "base_path": "/media/films-animation-enfants"},
    {"name": "films-zoe", "kind": "movies", "profile": "anime", "display": "Films - Zoé", "base_path": "/media/films-zoe"},
    {"name": "series", "kind": "series", "profile": "general", "display": "Séries", "base_path": "/media/series"},
    {"name": "series-emilie", "kind": "series", "profile": "general", "display": "Séries - Émilie", "base_path": "/media/series-emilie"},
    {"name": "series-thomas", "kind": "series", "profile": "general", "display": "Séries - Thomas", "base_path": "/media/series-thomas"},
    {"name": "series-garcons", "kind": "series", "profile": "family", "display": "Séries - Garçons", "base_path": "/media/series-garcons"},
    {"name": "series-zoe", "kind": "series", "profile": "anime", "display": "Séries - Zoé", "base_path": "/media/series-zoe"},
]


def _build_cfg() -> RootConfig:
    return RootConfig.model_validate({"categories": PRODUCTION_CATEGORIES})


def test_jellyfin_libraries_wiring_empty_manual() -> None:
    """5+5 → 2 libraries with 5 paths each."""
    cfg = _build_cfg()
    generated = generate_jellyfin_libraries(cfg)
    merged = merge_with_manual([], generated, app="jellyfin", resource="libraries")
    assert len(merged) == 2
    series_lib = next(lib for lib in merged if lib.name == "Séries")
    films_lib = next(lib for lib in merged if lib.name == "Films")
    assert len(series_lib.paths) == 5
    assert len(films_lib.paths) == 5
    assert series_lib.collection_type == "tvshows"
    assert films_lib.collection_type == "movies"


def test_jellyfin_libraries_path_content() -> None:
    cfg = _build_cfg()
    generated = generate_jellyfin_libraries(cfg)
    merged = merge_with_manual([], generated, app="jellyfin", resource="libraries")
    series_lib = next(lib for lib in merged if lib.name == "Séries")
    films_lib = next(lib for lib in merged if lib.name == "Films")
    assert "/media/series-zoe" in series_lib.paths
    assert "/media/films-zoe" in films_lib.paths
    # Cross-check that series base_paths don't leak into Films and vice versa:
    for p in series_lib.paths:
        assert not p.startswith("/media/films")
    for p in films_lib.paths:
        assert p.startswith("/media/films") or p.startswith("/media/nouveaux-films")


def test_jellyfin_manual_override_wins() -> None:
    """D-02: manual non-empty preserves operator's library list."""
    cfg = _build_cfg()
    generated = generate_jellyfin_libraries(cfg)
    manual = [JellyfinLibrary(name="Movies-Old", collection_type="movies", paths=["/media/legacy"])]
    merged = merge_with_manual(manual, generated, app="jellyfin", resource="libraries")
    assert len(merged) == 1
    assert merged[0].name == "Movies-Old"


def test_jellyfin_no_categories_returns_two_empty_libraries() -> None:
    """Generator always returns 2 libraries; when cfg is empty they have no paths.

    The reconciler's _reconcile_libraries will simply skip them
    (library_missing_skip warning if cluster doesn't have them, or no-op if it does).
    """
    cfg_empty = RootConfig()
    generated = generate_jellyfin_libraries(cfg_empty)
    assert len(generated) == 2
    assert generated[0].paths == []
    assert generated[1].paths == []


def test_jellyfin_only_series_no_movies() -> None:
    """Films library has empty paths when cfg has only series categories."""
    cfg = RootConfig.model_validate({
        "categories": [c for c in PRODUCTION_CATEGORIES if c["kind"] == "series"]
    })
    generated = generate_jellyfin_libraries(cfg)
    series_lib = next(lib for lib in generated if lib.name == "Séries")
    films_lib = next(lib for lib in generated if lib.name == "Films")
    assert len(series_lib.paths) == 5
    assert films_lib.paths == []
```

5. Run:
- `cd tools/arrconf && uv run pytest tests/test_jellyfin_categories.py tests/test_reconcilers_jellyfin.py tests/test_phase9_no_regression.py -x -v`
- `cd tools/arrconf && uv run ruff check arrconf/__main__.py tests/test_jellyfin_categories.py`
- `cd tools/arrconf && uv run ruff format --check arrconf/__main__.py tests/test_jellyfin_categories.py`
- `cd tools/arrconf && uv run mypy arrconf/__main__.py tests/test_jellyfin_categories.py`
- `cd tools/arrconf && uv run pytest -x`
  </action>
  <verify>
    <automated>cd tools/arrconf && uv run pytest tests/test_jellyfin_categories.py tests/test_reconcilers_jellyfin.py tests/test_phase9_no_regression.py -x -v &amp;&amp; uv run ruff check arrconf/__main__.py tests/test_jellyfin_categories.py &amp;&amp; uv run ruff format --check arrconf/__main__.py tests/test_jellyfin_categories.py &amp;&amp; uv run mypy arrconf/__main__.py tests/test_jellyfin_categories.py &amp;&amp; uv run pytest -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep "generate_jellyfin_libraries" tools/arrconf/arrconf/__main__.py` exits 0
    - `grep "app=\"jellyfin\", resource=\"libraries\"" tools/arrconf/arrconf/__main__.py` exits 0
    - `grep -c 'generate_jellyfin_libraries' tools/arrconf/arrconf/__main__.py` ≥ 2  (Pitfall 5: apply branch + diff branch BOTH call the generator; dump branch documented in <action> if not applicable. The generator name matches Plan 10-A's frozen export `generate_jellyfin_libraries`.)
    - `test -f tools/arrconf/tests/test_jellyfin_categories.py` exits 0
    - `grep -c "^def test_" tools/arrconf/tests/test_jellyfin_categories.py` ≥ 5
    - The verify command exits 0 (all tests pass + full suite green + Phase 9 no-regression intact)
  </acceptance_criteria>
  <done>Jellyfin pre-merge wired; 5 wiring tests pass; existing Jellyfin tests stay green; Phase 9 no-regression intact.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 10-G-02: Chart-pin co-bump — values.yaml arrconf.image.tag 0.6.3 → 0.6.4</name>
  <files>charts/arr-stack/values.yaml</files>
  <read_first>
    - charts/arr-stack/values.yaml lines 440-460
    - 10-F-seerr-animetags-fp-PLAN.md (precedent: bumped 0.6.2 → 0.6.3)
  </read_first>
  <behavior>Tag transitions `"0.6.3"` → `"0.6.4"`. Renovate annotation preserved.</behavior>
  <action>
1. Bump arrconf tag in `charts/arr-stack/values.yaml` from `"0.6.3"` to `"0.6.4"`.
2. Preserve renovate annotation.
3. Commit bundles Task 10-G-01 + this values.yaml edit (D-05).
  </action>
  <verify>
    <automated>grep -E '^\s+tag: "0\.6\.4"' charts/arr-stack/values.yaml &amp;&amp; grep -B 1 "repository: ghcr.io/tom333/arr-stack-arrconf" charts/arr-stack/values.yaml | grep "renovate: image=ghcr.io/tom333/arr-stack-arrconf" &amp;&amp; python3 -c "import yaml; yaml.safe_load(open('charts/arr-stack/values.yaml'))"</automated>
  </verify>
  <acceptance_criteria>
    - `grep 'tag: "0\.6\.4"' charts/arr-stack/values.yaml` exits 0
    - `git show HEAD --stat` lists `tools/arrconf/arrconf/__main__.py`, `tools/arrconf/tests/test_jellyfin_categories.py`, AND `charts/arr-stack/values.yaml` in the same commit.
  </acceptance_criteria>
  <done>Tag bumped 0.6.3 → 0.6.4; atomic commit with arrconf code.</done>
</task>

</tasks>

<verification>
```bash
cd tools/arrconf && uv run pytest -x
git show HEAD --stat
```
</verification>

<success_criteria>
- Jellyfin pre-merge wired in `__main__.py`.
- 5 wiring tests pass.
- Existing Jellyfin tests stay green.
- Phase 9 no-regression preserved.
- values.yaml arrconf.image.tag: 0.6.3 → 0.6.4.
- Single atomic commit per D-05.
- Lints + mypy clean.
</success_criteria>

<output>
After completion, create `.planning/phases/10-categories-6-app-propagation/10-G-jellyfin-wiring-SUMMARY.md` with:
- Commit SHA covering Task 10-G-01 + Task 10-G-02
- 5 test count + pass status
- Pointer to Plan 10-H (Prowlarr FP fix #2) as the final Wave 2 plan
</output>
