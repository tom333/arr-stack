---
phase: 10-categories-6-app-propagation
plan: 10-D-sonarr-wiring
type: execute
wave: 2
depends_on:
  - 10-A-generators-categories
  - 10-B-merge-with-manual
files_modified:
  - tools/arrconf/arrconf/__main__.py
  - tools/arrconf/tests/test_sonarr_categories.py
  - charts/arr-stack/values.yaml
autonomous: true
requirements:
  - REQ-categories-sonarr-propagation
requirements_addressed:
  - REQ-categories-sonarr-propagation (wiring side)
tags:
  - python
  - reconciler-wiring
  - sonarr
  - chart-pin-cobump

must_haves:
  truths:
    - "`tools/arrconf/arrconf/__main__.py` Sonarr branch (lines 122-143) pre-merges via `generate_sonarr_resources(root)` + 4 `merge_with_manual` calls (tags, root_folders, download_clients, remote_path_mappings) BEFORE `reconcile_sonarr` call. Same pre-merge in `diff` and `dump` Sonarr handlers (Pitfall 5)."
    - "When `instance.tags.items == []` and `cfg.categories` has 5 series entries, the reconciler receives 5 `TagItem(label=c.name)` objects."
    - "When `instance.root_folders.items == []`, the reconciler receives 5 `RootFolder(path=c.base_path)` entries."
    - "When `instance.download_clients.items == []`, the reconciler receives 5 `DownloadClient` entries with proper tag_labels + `tvCategory` fields."
    - "When `instance.remote_path_mappings.items == []`, the reconciler receives 5 RPMs with trailing-slash paths."
    - "Manual override path (per resource) still works: setting `instance.tags.items` to a non-empty list bypasses Categories-derived tags for that resource only."
    - "`tools/arrconf/tests/test_sonarr_categories.py` proves all 5 wiring outcomes + the per-resource manual override."
    - "Phase 9 no-regression test (`tests/test_phase9_no_regression.py`) continues to pass."
    - "`charts/arr-stack/values.yaml` arrconf.image.tag bumped 0.6.0 → 0.6.1 in the SAME commit as the arrconf code changes (D-05 chart-pin co-bump)."
  artifacts:
    - path: "tools/arrconf/arrconf/__main__.py"
      provides: "Sonarr pre-merge dispatch (apply + diff + dump branches)"
      contains: "from arrconf.generators.categories import generate_sonarr_resources"
    - path: "tools/arrconf/tests/test_sonarr_categories.py"
      provides: "5×4 Sonarr wiring tests + manual override per-resource"
      min_lines: 100
    - path: "charts/arr-stack/values.yaml"
      provides: "arrconf.image.tag bumped to 0.6.1"
      contains: "tag: \"0.6.1\""
  key_links:
    - from: "tools/arrconf/arrconf/__main__.py"
      to: "tools/arrconf/arrconf/generators/categories.py"
      via: "from arrconf.generators.categories import generate_sonarr_resources"
      pattern: "generate_sonarr_resources"
    - from: "tools/arrconf/arrconf/__main__.py"
      to: "instance.{tags,root_folders,download_clients,remote_path_mappings}.items"
      via: "4 in-place mutations after merge_with_manual"
      pattern: "instance\\.(tags|root_folders|download_clients|remote_path_mappings)\\.items ="
---

<objective>
Wire the Sonarr reconciler to consume Categories-derived `SonarrDerived` (from Plan 10-A) via the pre-merge mechanism in `__main__.py`. Four resources per Sonarr instance: tags, root_folders, download_clients, remote_path_mappings — each gets its own `merge_with_manual` call so the operator can override one resource without losing the others.

Purpose: Closes REQ-categories-sonarr-propagation. Reconciler signature unchanged; all pre-merging happens in `__main__.py`. Bundled with chart-pin co-bump 0.6.0 → 0.6.1 per D-05.

Output: Single atomic commit bundling `__main__.py` pre-merge wiring + 5×4 wiring tests + values.yaml tag bump.
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
@.planning/phases/10-categories-6-app-propagation/10-B-merge-with-manual-PLAN.md
@.planning/phases/10-categories-6-app-propagation/10-C-qbit-wiring-fp-PLAN.md
@CLAUDE.md

@tools/arrconf/arrconf/__main__.py
@tools/arrconf/arrconf/config.py
@tools/arrconf/arrconf/reconcilers/sonarr.py
@charts/arr-stack/values.yaml

<interfaces>
<!-- Plan 10-A output — consumed here -->
```python
# arrconf/generators/categories.py
@dataclass
class SonarrDerived:
    tags: list[TagItem]
    root_folders: list[RootFolder]
    download_clients: list[DownloadClient]
    remote_path_mappings: list[RemotePathMapping]

def generate_sonarr_resources(cfg: RootConfig) -> SonarrDerived: ...
```

<!-- SonarrInstance shape (read-only, from config.py:325-355) -->
```python
class SonarrInstance(BaseModel):
    base_url: str
    download_clients: DownloadClientsSection
    host_config: HostConfigSection
    indexers: IndexersSection
    notifications: NotificationsSection
    remote_path_mappings: RemotePathMappingsSection   # .items: list[RemotePathMapping]
    root_folders: RootFoldersSection                  # .items: list[RootFolder]
    series_tags: SeriesTagsSection
    tags: TagsSection                                  # .items: list[TagItem]
    content_routing: ContentRoutingSection
```

<!-- Plan 10-C 10-C-02 pattern to mirror — pre-merge in __main__.py Sonarr branch -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 10-D-01: Pre-merge Sonarr 4 resources in __main__.py (apply + diff + dump)</name>
  <files>tools/arrconf/arrconf/__main__.py, tools/arrconf/tests/test_sonarr_categories.py</files>
  <read_first>
    - tools/arrconf/arrconf/__main__.py lines 122-143 (current Sonarr apply branch)
    - tools/arrconf/arrconf/__main__.py (full file — locate Sonarr branch in `diff` and `dump` commands too)
    - tools/arrconf/arrconf/generators/categories.py (Plan 10-A output — generate_sonarr_resources signature)
    - tools/arrconf/arrconf/reconcilers/_shared.py (Plan 10-B output — merge_with_manual)
    - tools/arrconf/arrconf/reconcilers/sonarr.py (read-only — confirm reconcile_sonarr signature unchanged)
    - tools/arrconf/arrconf/config.py lines 134-160, 320-360 (TagsSection, RemotePathMappingsSection, SonarrInstance shape)
    - 10-RESEARCH.md §"Pattern 3: __main__.py injection point" + §"Pitfall 5"
    - 10-PATTERNS.md §"sonarr.py + radarr.py — generator wiring"
  </read_first>
  <behavior>
    - Test 1 (tags): With `cfg.categories` having 5 series + 5 movies AND `instance.tags.items = []` → after pre-merge, `instance.tags.items` has 5 `TagItem(label=c.name)` with labels `["series", "series-emilie", "series-thomas", "series-garcons", "series-zoe"]`.
    - Test 2 (root_folders): Same scenario, `instance.root_folders.items` has 5 `RootFolder` entries with `path` = each series category's `/media/<name>`.
    - Test 3 (download_clients): Same, 5 `DownloadClient` entries with `implementation="QBittorrent"`, `configContract="QBittorrentSettings"`, `tag_labels=[c.name]`.
    - Test 4 (remote_path_mappings): Same, 5 `RemotePathMapping` entries with trailing slashes.
    - Test 5 (per-resource override): If `instance.tags.items` is non-empty BUT `instance.root_folders.items = []`, the tags resource keeps the manual list AND root_folders gets the generated 5 entries (per-resource toggle).
    - Test 6 (no-regression): Phase 9's `test_phase9_no_regression` continues to pass with the new pre-merge code path (D-13 invariant: when manual sections are non-empty, generated is skipped → plan output unchanged).
  </behavior>
  <action>
1. **Add imports in `tools/arrconf/arrconf/__main__.py`** alongside the imports added in Plan 10-C (alphabetical order):

```python
from arrconf.generators.categories import (
    generate_qbit_categories,         # already added in Plan 10-C
    generate_sonarr_resources,        # new in this plan
)
```

(If Plan 10-C used a single `from arrconf.generators.categories import generate_qbit_categories` line, extend it to a multi-name import block. Re-run `ruff check --fix` to sort imports alphabetically.)

2. **Inject pre-merge in the Sonarr `apply` branch** (`__main__.py` line ~123, AFTER `instance = root.sonarr["main"]` and BEFORE `client = SonarrClient(...)`):

```python
        # Phase 10 pre-merge (D-01/D-02): Categories→Sonarr 4 resources.
        # Each resource has its own merge_with_manual toggle so the operator
        # can override one resource (e.g. tags) without losing the others.
        sonarr_derived = generate_sonarr_resources(root)
        instance.tags.items = merge_with_manual(
            instance.tags.items, sonarr_derived.tags,
            app="sonarr", resource="tags",
        )
        instance.root_folders.items = merge_with_manual(
            instance.root_folders.items, sonarr_derived.root_folders,
            app="sonarr", resource="root_folders",
        )
        instance.download_clients.items = merge_with_manual(
            instance.download_clients.items, sonarr_derived.download_clients,
            app="sonarr", resource="download_clients",
        )
        instance.remote_path_mappings.items = merge_with_manual(
            instance.remote_path_mappings.items, sonarr_derived.remote_path_mappings,
            app="sonarr", resource="remote_path_mappings",
        )
```

3. **Apply identical pre-merge in the Sonarr branches of `diff` and `dump`** (Pitfall 5). Read the existing Sonarr branches in those commands first; mirror the exact 4-call sequence.

4. **Create the wiring test** `tools/arrconf/tests/test_sonarr_categories.py`:

```python
"""Phase 10 wiring test: Categories→Sonarr 4 resources via merge_with_manual.

Validates that generate_sonarr_resources + merge_with_manual deliver the right
items to the 4 Sonarr resource slots (tags, root_folders, download_clients,
remote_path_mappings) under both "manual empty" and "manual non-empty" toggles.

NOT an HTTP integration test — pure data-flow verification.
"""

from __future__ import annotations

from arrconf.config import RootConfig, TagItem
from arrconf.generators.categories import generate_sonarr_resources
from arrconf.reconcilers._shared import merge_with_manual
from arrconf.resources.sonarr.remote_path_mapping import RemotePathMapping
from arrconf.resources.sonarr.root_folder import RootFolder


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


def test_sonarr_tags_wiring_empty_manual() -> None:
    cfg = _build_cfg()
    derived = generate_sonarr_resources(cfg)
    merged = merge_with_manual([], derived.tags, app="sonarr", resource="tags")
    assert len(merged) == 5
    assert [t.label for t in merged] == ["series", "series-emilie", "series-thomas", "series-garcons", "series-zoe"]


def test_sonarr_root_folders_wiring_empty_manual() -> None:
    cfg = _build_cfg()
    derived = generate_sonarr_resources(cfg)
    merged = merge_with_manual([], derived.root_folders, app="sonarr", resource="root_folders")
    assert len(merged) == 5
    assert [rf.path for rf in merged] == ["/media/series", "/media/series-emilie", "/media/series-thomas", "/media/series-garcons", "/media/series-zoe"]


def test_sonarr_download_clients_wiring_empty_manual() -> None:
    cfg = _build_cfg()
    derived = generate_sonarr_resources(cfg)
    merged = merge_with_manual([], derived.download_clients, app="sonarr", resource="download_clients")
    assert len(merged) == 5
    for dc in merged:
        assert dc.implementation == "QBittorrent"
        assert dc.configContract == "QBittorrentSettings"
        assert len(dc.tag_labels) == 1


def test_sonarr_rpm_wiring_empty_manual() -> None:
    cfg = _build_cfg()
    derived = generate_sonarr_resources(cfg)
    merged = merge_with_manual([], derived.remote_path_mappings, app="sonarr", resource="remote_path_mappings")
    assert len(merged) == 5
    for rpm in merged:
        assert rpm.remotePath.endswith("/")
        assert rpm.localPath.endswith("/")
        assert rpm.host == "qbittorrent.selfhost.svc.cluster.local"


def test_sonarr_per_resource_override_tags_only() -> None:
    """Manual tags + empty root_folders → tags survives manual, root_folders gets Categories."""
    cfg = _build_cfg()
    derived = generate_sonarr_resources(cfg)
    manual_tags = [TagItem(label="tv"), TagItem(label="anime"), TagItem(label="family")]
    merged_tags = merge_with_manual(manual_tags, derived.tags, app="sonarr", resource="tags")
    merged_rf = merge_with_manual([], derived.root_folders, app="sonarr", resource="root_folders")
    assert len(merged_tags) == 3  # manual wins
    assert [t.label for t in merged_tags] == ["tv", "anime", "family"]
    assert len(merged_rf) == 5  # generated wins (root_folders manual was empty)


def test_sonarr_per_resource_override_rpm_only() -> None:
    """Manual RPM + empty download_clients → RPM keeps manual, DCs get Categories."""
    cfg = _build_cfg()
    derived = generate_sonarr_resources(cfg)
    manual_rpm = [RemotePathMapping(host="x", remotePath="/legacy/", localPath="/data/legacy/")]
    merged_rpm = merge_with_manual(manual_rpm, derived.remote_path_mappings, app="sonarr", resource="remote_path_mappings")
    merged_dc = merge_with_manual([], derived.download_clients, app="sonarr", resource="download_clients")
    assert len(merged_rpm) == 1
    assert merged_rpm[0].remotePath == "/legacy/"
    assert len(merged_dc) == 5
```

5. Run all checks:
- `cd tools/arrconf && uv run pytest tests/test_sonarr_categories.py tests/test_phase9_no_regression.py -x -v`
- `cd tools/arrconf && uv run ruff check arrconf/__main__.py tests/test_sonarr_categories.py`
- `cd tools/arrconf && uv run ruff format --check arrconf/__main__.py tests/test_sonarr_categories.py`
- `cd tools/arrconf && uv run mypy arrconf/__main__.py tests/test_sonarr_categories.py`
- `cd tools/arrconf && uv run pytest -x`  (full suite)
  </action>
  <verify>
    <automated>cd tools/arrconf && uv run pytest tests/test_sonarr_categories.py tests/test_phase9_no_regression.py -x -v &amp;&amp; uv run ruff check arrconf/__main__.py tests/test_sonarr_categories.py &amp;&amp; uv run ruff format --check arrconf/__main__.py tests/test_sonarr_categories.py &amp;&amp; uv run mypy arrconf/__main__.py tests/test_sonarr_categories.py &amp;&amp; uv run pytest -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep "generate_sonarr_resources" tools/arrconf/arrconf/__main__.py` exits 0
    - `grep -c "app=\"sonarr\"" tools/arrconf/arrconf/__main__.py` ≥ 4  (4 merge_with_manual calls for the 4 resources)
    - `grep -c "resource=\"tags\"\|resource=\"root_folders\"\|resource=\"download_clients\"\|resource=\"remote_path_mappings\"" tools/arrconf/arrconf/__main__.py` ≥ 4
    - `test -f tools/arrconf/tests/test_sonarr_categories.py` exits 0
    - `grep -c "^def test_" tools/arrconf/tests/test_sonarr_categories.py` ≥ 6
    - The verify command exits 0 (all tests pass + full suite green + Phase 9 no-regression intact)
  </acceptance_criteria>
  <done>Sonarr pre-merge wired for all 4 resources; per-resource override toggle proven; Phase 9 no-regression intact.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 10-D-02: Chart-pin co-bump — values.yaml arrconf.image.tag 0.6.0 → 0.6.1</name>
  <files>charts/arr-stack/values.yaml</files>
  <read_first>
    - charts/arr-stack/values.yaml lines 440-460 (current arrconf image block — Plan 10-C bumped to 0.6.0)
    - CLAUDE.md §"Annotations Renovate (CRITIQUE)"
    - 10-C-qbit-wiring-fp-PLAN.md (precedent: Plan 10-C bumped 0.5.3 → 0.6.0)
  </read_first>
  <behavior>
    - Tag string transitions from `"0.6.0"` to `"0.6.1"` (patch bump after 10-C's minor bump).
    - Renovate annotation preserved exactly as is.
  </behavior>
  <action>
1. Open `charts/arr-stack/values.yaml`. Locate the arrconf image block. The tag should currently be `"0.6.0"` (set by Plan 10-C). Bump to `"0.6.1"`.

2. Do NOT modify the renovate annotation or any other field.

3. **Commit must bundle this values.yaml edit with Task 10-D-01's __main__.py changes** in the same atomic commit (D-05).

4. Smoke check: `python3 -c "import yaml; yaml.safe_load(open('charts/arr-stack/values.yaml'))"` exits 0.
  </action>
  <verify>
    <automated>grep -E '^\s+tag: "0\.6\.1"' charts/arr-stack/values.yaml &amp;&amp; ! grep -E '^\s+tag: "0\.6\.0"' charts/arr-stack/values.yaml &amp;&amp; grep -B 1 "repository: ghcr.io/tom333/arr-stack-arrconf" charts/arr-stack/values.yaml | grep "renovate: image=ghcr.io/tom333/arr-stack-arrconf" &amp;&amp; python3 -c "import yaml; yaml.safe_load(open('charts/arr-stack/values.yaml'))"</automated>
  </verify>
  <acceptance_criteria>
    - `grep 'tag: "0\.6\.1"' charts/arr-stack/values.yaml` exits 0
    - `grep 'tag: "0\.6\.0"' charts/arr-stack/values.yaml` returns empty (no arrconf line at 0.6.0; unrelated charts may legitimately reference other 0.6.0 if any — verify the arrconf-specific block specifically)
    - `grep -c "# renovate: image=ghcr.io/tom333/arr-stack-arrconf" charts/arr-stack/values.yaml` ≥ 1
    - YAML still parses cleanly
    - Final `git show HEAD --stat` lists BOTH `tools/arrconf/arrconf/__main__.py` AND `charts/arr-stack/values.yaml` in the SAME commit.
  </acceptance_criteria>
  <done>arrconf.image.tag bumped 0.6.0 → 0.6.1; commit bundles arrconf code + values.yaml.</done>
</task>

</tasks>

<verification>
End-to-end:
```bash
cd tools/arrconf && uv run pytest -x
git show HEAD --stat   # MUST list both arrconf code and values.yaml
```
</verification>

<success_criteria>
- Sonarr pre-merge wired for 4 resources in `__main__.py` apply + diff + dump.
- `tests/test_sonarr_categories.py` 6 tests pass.
- Phase 9 no-regression preserved.
- `charts/arr-stack/values.yaml` arrconf.image.tag: 0.6.0 → 0.6.1, renovate annotation preserved.
- Single atomic commit (D-05 chart-pin co-bump).
- All lints + mypy clean.
</success_criteria>

<output>
After completion, create `.planning/phases/10-categories-6-app-propagation/10-D-sonarr-wiring-SUMMARY.md` documenting:
- Single commit SHA covering Task 10-D-01 + Task 10-D-02
- 6 test count + pass status
- Confirmation that pre-merge was applied in apply + diff + dump (or that dump doesn't dump Sonarr in a way that needs pre-merge — document the verification)
- Pointer to Plan 10-E (Radarr — byte-equivalent shape) as the next Wave 2 plan
</output>
