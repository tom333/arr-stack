---
phase: 10-categories-6-app-propagation
plan: 10-E-radarr-wiring
type: execute
wave: 2
depends_on:
  - 10-A-generators-categories
  - 10-B-merge-with-manual
files_modified:
  - tools/arrconf/arrconf/__main__.py
  - tools/arrconf/tests/test_radarr_categories.py
  - charts/arr-stack/values.yaml
autonomous: true
requirements:
  - REQ-categories-radarr-propagation
requirements_addressed:
  - REQ-categories-radarr-propagation (wiring side)
tags:
  - python
  - reconciler-wiring
  - radarr
  - chart-pin-cobump

must_haves:
  truths:
    - "`tools/arrconf/arrconf/__main__.py` Radarr branch (lines ~146-166) pre-merges via `generate_radarr_resources(root)` + 4 `merge_with_manual` calls (tags, root_folders, download_clients, remote_path_mappings) BEFORE `reconcile_radarr` call. Same pre-merge in `diff` and `dump` Radarr handlers."
    - "When `radarr_instance.tags.items == []` and `cfg.categories` has 5 movies entries, the reconciler receives 5 `TagItem(label=c.name)` objects with labels `[\"films\", \"nouveaux-films\", \"films-enfants\", \"films-animation-enfants\", \"films-zoe\"]`."
    - "When `radarr_instance.download_clients.items == []`, the reconciler receives 5 DCs with `movieCategory` FieldKVs (NOT `tvCategory`)."
    - "Per-resource override (D-02) works for all 4 Radarr resources individually."
    - "`tools/arrconf/tests/test_radarr_categories.py` proves 5×4 wiring + per-resource manual override."
    - "Phase 9 no-regression test still passes."
    - "`charts/arr-stack/values.yaml` arrconf.image.tag bumped 0.6.1 → 0.6.2 in the SAME commit (D-05 chart-pin co-bump)."
  artifacts:
    - path: "tools/arrconf/arrconf/__main__.py"
      provides: "Radarr pre-merge dispatch (apply + diff + dump)"
      contains: "generate_radarr_resources"
    - path: "tools/arrconf/tests/test_radarr_categories.py"
      provides: "5×4 Radarr wiring tests + manual override per-resource"
      min_lines: 100
    - path: "charts/arr-stack/values.yaml"
      provides: "arrconf.image.tag bumped to 0.6.2"
      contains: "tag: \"0.6.2\""
  key_links:
    - from: "tools/arrconf/arrconf/__main__.py"
      to: "tools/arrconf/arrconf/generators/categories.py"
      via: "from arrconf.generators.categories import generate_radarr_resources"
      pattern: "generate_radarr_resources"
    - from: "tools/arrconf/arrconf/__main__.py"
      to: "radarr_instance.{tags,root_folders,download_clients,remote_path_mappings}.items"
      via: "4 in-place mutations after merge_with_manual"
      pattern: "radarr_instance\\.(tags|root_folders|download_clients|remote_path_mappings)\\.items ="
---

<objective>
Wire the Radarr reconciler to consume Categories-derived `RadarrDerived` (from Plan 10-A) via the pre-merge mechanism in `__main__.py`. Byte-equivalent shape to Plan 10-D (Sonarr) — same 4 resources, different `kind` filter (`kind == "movies"`), different DC field name (`movieCategory` vs `tvCategory`).

Purpose: Closes REQ-categories-radarr-propagation. Reconciler signature unchanged. Bundled with chart-pin co-bump 0.6.1 → 0.6.2 per D-05.

Output: Single atomic commit bundling `__main__.py` pre-merge wiring + 5×4 Radarr wiring tests + values.yaml tag bump.
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
@.planning/phases/10-categories-6-app-propagation/10-D-sonarr-wiring-PLAN.md
@CLAUDE.md

@tools/arrconf/arrconf/__main__.py
@tools/arrconf/arrconf/reconcilers/radarr.py
@charts/arr-stack/values.yaml

<interfaces>
<!-- Plan 10-A output — consumed here -->
```python
# arrconf/generators/categories.py
@dataclass
class RadarrDerived:
    tags: list[TagItem]
    root_folders: list[RootFolder]
    download_clients: list[DownloadClient]
    remote_path_mappings: list[RemotePathMapping]

def generate_radarr_resources(cfg: RootConfig) -> RadarrDerived: ...
```

<!-- RadarrInstance has identical section list to SonarrInstance per Phase 3 D-03-01 -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 10-E-01: Pre-merge Radarr 4 resources in __main__.py (apply + diff + dump)</name>
  <files>tools/arrconf/arrconf/__main__.py, tools/arrconf/tests/test_radarr_categories.py</files>
  <read_first>
    - tools/arrconf/arrconf/__main__.py lines 146-166 (current Radarr apply branch — mirror Sonarr pattern from Plan 10-D)
    - tools/arrconf/arrconf/__main__.py (Radarr in `diff` + `dump` commands)
    - tools/arrconf/arrconf/generators/categories.py (generate_radarr_resources signature)
    - tools/arrconf/arrconf/reconcilers/radarr.py (read-only — confirm reconciler signature unchanged)
    - .planning/phases/10-categories-6-app-propagation/10-D-sonarr-wiring-PLAN.md (mirror this plan's structure)
    - 10-RESEARCH.md §"Pattern 3: __main__.py injection point" + §"Pitfall 5"
  </read_first>
  <behavior>
    - Test 1: 5 movies categories produce 5 `TagItem(label=c.name)` after pre-merge with empty manual.
    - Test 2: 5 RootFolder with `path = c.base_path` (e.g. `/media/films`, `/media/films-zoe`).
    - Test 3: 5 DownloadClient with `movieCategory` FieldKV (NOT `tvCategory`).
    - Test 4: 5 RPM with trailing slashes.
    - Test 5: Per-resource override (manual tags + empty rest → tags survives, others get Categories-derived).
    - Test 6: Phase 9 no-regression test still passes.
  </behavior>
  <action>
1. **Extend the existing `arrconf.generators.categories` import** in `__main__.py` to include `generate_radarr_resources`:

```python
from arrconf.generators.categories import (
    generate_qbit_categories,
    generate_radarr_resources,        # new in this plan
    generate_sonarr_resources,
)
```

2. **Inject pre-merge in the Radarr `apply` branch** (after `radarr_instance = root.radarr["main"]`, before `radarr_client = RadarrClient(...)`):

```python
        # Phase 10 pre-merge (D-01/D-02): Categories→Radarr 4 resources.
        # Mirror of Sonarr pre-merge (Plan 10-D) — kind="movies" filter in generator.
        radarr_derived = generate_radarr_resources(root)
        radarr_instance.tags.items = merge_with_manual(
            radarr_instance.tags.items, radarr_derived.tags,
            app="radarr", resource="tags",
        )
        radarr_instance.root_folders.items = merge_with_manual(
            radarr_instance.root_folders.items, radarr_derived.root_folders,
            app="radarr", resource="root_folders",
        )
        radarr_instance.download_clients.items = merge_with_manual(
            radarr_instance.download_clients.items, radarr_derived.download_clients,
            app="radarr", resource="download_clients",
        )
        radarr_instance.remote_path_mappings.items = merge_with_manual(
            radarr_instance.remote_path_mappings.items, radarr_derived.remote_path_mappings,
            app="radarr", resource="remote_path_mappings",
        )
```

3. **Apply identical pre-merge in the Radarr branches of `diff` and `dump`** (Pitfall 5).

4. **Create the wiring test** `tools/arrconf/tests/test_radarr_categories.py` — mirror of `test_sonarr_categories.py` with Radarr-specific assertions:

```python
"""Phase 10 wiring test: Categories→Radarr 4 resources (mirror of Sonarr test)."""

from __future__ import annotations

from arrconf.config import RootConfig, TagItem
from arrconf.generators.categories import generate_radarr_resources
from arrconf.reconcilers._shared import merge_with_manual
from arrconf.resources.sonarr.remote_path_mapping import RemotePathMapping


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


def test_radarr_tags_wiring_empty_manual() -> None:
    cfg = _build_cfg()
    derived = generate_radarr_resources(cfg)
    merged = merge_with_manual([], derived.tags, app="radarr", resource="tags")
    assert len(merged) == 5
    assert [t.label for t in merged] == ["films", "nouveaux-films", "films-enfants", "films-animation-enfants", "films-zoe"]


def test_radarr_root_folders_wiring_empty_manual() -> None:
    cfg = _build_cfg()
    derived = generate_radarr_resources(cfg)
    merged = merge_with_manual([], derived.root_folders, app="radarr", resource="root_folders")
    assert len(merged) == 5
    assert [rf.path for rf in merged] == ["/media/films", "/media/nouveaux-films", "/media/films-enfants", "/media/films-animation-enfants", "/media/films-zoe"]


def test_radarr_download_clients_have_movieCategory() -> None:
    """D-03b Radarr-side: movieCategory FieldKV, NOT tvCategory."""
    cfg = _build_cfg()
    derived = generate_radarr_resources(cfg)
    merged = merge_with_manual([], derived.download_clients, app="radarr", resource="download_clients")
    assert len(merged) == 5
    for dc in merged:
        movie_cat = next((f for f in dc.fields if f.name == "movieCategory"), None)
        tv_cat = next((f for f in dc.fields if f.name == "tvCategory"), None)
        assert movie_cat is not None, f"DC {dc.name} missing movieCategory FieldKV"
        assert tv_cat is None, f"DC {dc.name} unexpectedly has tvCategory FieldKV (should be Radarr-side)"


def test_radarr_rpm_wiring_empty_manual() -> None:
    cfg = _build_cfg()
    derived = generate_radarr_resources(cfg)
    merged = merge_with_manual([], derived.remote_path_mappings, app="radarr", resource="remote_path_mappings")
    assert len(merged) == 5
    for rpm in merged:
        assert rpm.remotePath.endswith("/")
        assert rpm.localPath.endswith("/")


def test_radarr_per_resource_override_tags_only() -> None:
    cfg = _build_cfg()
    derived = generate_radarr_resources(cfg)
    manual_tags = [TagItem(label="movies"), TagItem(label="anime"), TagItem(label="family")]
    merged_tags = merge_with_manual(manual_tags, derived.tags, app="radarr", resource="tags")
    merged_rf = merge_with_manual([], derived.root_folders, app="radarr", resource="root_folders")
    assert [t.label for t in merged_tags] == ["movies", "anime", "family"]
    assert len(merged_rf) == 5


def test_radarr_no_movies_in_cfg() -> None:
    """If cfg has only series categories, Radarr derived containers are all empty."""
    cfg = RootConfig.model_validate({"categories": [c for c in PRODUCTION_CATEGORIES if c["kind"] == "series"]})
    derived = generate_radarr_resources(cfg)
    assert derived.tags == []
    assert derived.root_folders == []
    assert derived.download_clients == []
    assert derived.remote_path_mappings == []
```

5. Run:
- `cd tools/arrconf && uv run pytest tests/test_radarr_categories.py tests/test_phase9_no_regression.py -x -v`
- `cd tools/arrconf && uv run ruff check arrconf/__main__.py tests/test_radarr_categories.py`
- `cd tools/arrconf && uv run ruff format --check arrconf/__main__.py tests/test_radarr_categories.py`
- `cd tools/arrconf && uv run mypy arrconf/__main__.py tests/test_radarr_categories.py`
- `cd tools/arrconf && uv run pytest -x`  (full suite)
  </action>
  <verify>
    <automated>cd tools/arrconf && uv run pytest tests/test_radarr_categories.py tests/test_phase9_no_regression.py -x -v &amp;&amp; uv run ruff check arrconf/__main__.py tests/test_radarr_categories.py &amp;&amp; uv run ruff format --check arrconf/__main__.py tests/test_radarr_categories.py &amp;&amp; uv run mypy arrconf/__main__.py tests/test_radarr_categories.py &amp;&amp; uv run pytest -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep "generate_radarr_resources" tools/arrconf/arrconf/__main__.py` exits 0
    - `grep -c "app=\"radarr\"" tools/arrconf/arrconf/__main__.py` ≥ 4
    - `test -f tools/arrconf/tests/test_radarr_categories.py` exits 0
    - `grep -c "^def test_" tools/arrconf/tests/test_radarr_categories.py` ≥ 6
    - The verify command exits 0 (all tests pass + full suite green)
  </acceptance_criteria>
  <done>Radarr pre-merge wired for all 4 resources; per-resource override toggle proven; Phase 9 no-regression intact.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 10-E-02: Chart-pin co-bump — values.yaml arrconf.image.tag 0.6.1 → 0.6.2</name>
  <files>charts/arr-stack/values.yaml</files>
  <read_first>
    - charts/arr-stack/values.yaml lines 440-460
    - 10-D-sonarr-wiring-PLAN.md (precedent: bumped 0.6.0 → 0.6.1)
  </read_first>
  <behavior>Tag transitions from `"0.6.1"` to `"0.6.2"`. Renovate annotation preserved.</behavior>
  <action>
1. Bump the arrconf tag in `charts/arr-stack/values.yaml` from `"0.6.1"` to `"0.6.2"`.
2. Preserve the renovate annotation.
3. Smoke check YAML validity.
4. Commit must bundle this with Task 10-E-01's arrconf code changes (D-05).
  </action>
  <verify>
    <automated>grep -E '^\s+tag: "0\.6\.2"' charts/arr-stack/values.yaml &amp;&amp; ! grep -E '^\s+tag: "0\.6\.1"' charts/arr-stack/values.yaml &amp;&amp; grep -B 1 "repository: ghcr.io/tom333/arr-stack-arrconf" charts/arr-stack/values.yaml | grep "renovate: image=ghcr.io/tom333/arr-stack-arrconf" &amp;&amp; python3 -c "import yaml; yaml.safe_load(open('charts/arr-stack/values.yaml'))"</automated>
  </verify>
  <acceptance_criteria>
    - `grep 'tag: "0\.6\.2"' charts/arr-stack/values.yaml` exits 0
    - The arrconf 0.6.1 line is gone (other charts at unrelated 0.6.1 values are fine)
    - `git show HEAD --stat` lists BOTH `tools/arrconf/arrconf/__main__.py` AND `charts/arr-stack/values.yaml` in the same commit.
  </acceptance_criteria>
  <done>Tag bumped 0.6.1 → 0.6.2; atomic commit with arrconf code.</done>
</task>

</tasks>

<verification>
```bash
cd tools/arrconf && uv run pytest -x
git show HEAD --stat
```
</verification>

<success_criteria>
- Radarr pre-merge wired for 4 resources in `__main__.py`.
- 6 wiring tests pass.
- Phase 9 no-regression preserved.
- values.yaml arrconf.image.tag: 0.6.1 → 0.6.2.
- Single atomic commit per D-05.
- Lints + mypy clean.
</success_criteria>

<output>
After completion, create `.planning/phases/10-categories-6-app-propagation/10-E-radarr-wiring-SUMMARY.md` documenting:
- Commit SHA covering Task 10-E-01 + Task 10-E-02
- 6 test count + pass status
- Pointer to Plan 10-F (Seerr — animeTags routing + FP fix #3) as the next Wave 2 plan
</output>
