---
phase: 10-categories-6-app-propagation
plan: 10-C-qbit-wiring-fp
type: execute
wave: 2
depends_on:
  - 10-A-generators-categories
  - 10-B-merge-with-manual
files_modified:
  - tools/arrconf/arrconf/reconcilers/qbittorrent.py
  - tools/arrconf/arrconf/__main__.py
  - tools/arrconf/tests/test_idempotence_fp.py
  - tools/arrconf/tests/test_qbittorrent_categories.py
  - charts/arr-stack/values.yaml
autonomous: true
requirements:
  - REQ-categories-qbit-propagation
  - REQ-idempotence-fp-fix
requirements_addressed:
  - REQ-categories-qbit-propagation (wiring side)
  - REQ-idempotence-fp-fix (FP #1 — qBit categories allowlist)
tags:
  - python
  - reconciler-wiring
  - qbittorrent
  - fp-fix
  - chart-pin-cobump

must_haves:
  truths:
    - "`tools/arrconf/arrconf/reconcilers/qbittorrent.py` declares a module-level `QBIT_CATEGORY_MANAGED_FIELDS: frozenset[str] = frozenset({\"name\", \"savePath\"})` constant."
    - "`_fetch_current_categories` filters each cluster GET dict to `QBIT_CATEGORY_MANAGED_FIELDS` BEFORE `Category.model_validate` (FP fix #1; B2 allowlist per RESEARCH.md verdict)."
    - "`tools/arrconf/arrconf/__main__.py` qBit branch (lines ~195-243) pre-merges categories via `generate_qbit_categories(root)` + `merge_with_manual(instance.categories.items, generated, app=\"qbit\", resource=\"categories\")` BEFORE the `reconcile_qbittorrent` call. Same pre-merge applied in `diff` and `dump` command handlers (Pitfall 5)."
    - "`tools/arrconf/tests/test_idempotence_fp.py::test_qbit_category_fp_fix` asserts: cluster GET returning extra fields (download_path, ratio_limit, etc.) yields a plan where every action is `Action.NO_OP` (no spurious UPDATE)."
    - "`tools/arrconf/tests/test_qbittorrent_categories.py::test_categories_wiring_10_entries` asserts: when `cfg.categories` has 10 entries and `instance.categories.items` is empty, the reconciler receives all 10 Categories-derived qBit categories via the pre-merge path."
    - "`charts/arr-stack/values.yaml` line ~451: `arrconf.image.tag` bumped from `\"0.5.3\"` to `\"0.6.0\"` IN THE SAME COMMIT as the arrconf code changes (D-05 chart-pin co-bump pattern). The `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` annotation on line 449 is preserved."
    - "Full Phase 9 regression test (`tests/test_phase9_no_regression.py`) continues to pass — proves D-13 invariant survives the pre-merge code path when categories[] is present but flat sections are also present (manual override wins, plan output unchanged)."
  artifacts:
    - path: "tools/arrconf/arrconf/reconcilers/qbittorrent.py"
      provides: "FP fix #1 via B2 allowlist filter in _fetch_current_categories"
      contains: "QBIT_CATEGORY_MANAGED_FIELDS"
    - path: "tools/arrconf/arrconf/__main__.py"
      provides: "qBit pre-merge dispatch (apply + diff + dump branches)"
      contains: "from arrconf.generators.categories import generate_qbit_categories"
    - path: "tools/arrconf/tests/test_idempotence_fp.py"
      provides: "FP fix #1 regression test"
      min_lines: 60
    - path: "tools/arrconf/tests/test_qbittorrent_categories.py"
      provides: "Categories→qBit wiring smoke test (10 entries)"
      min_lines: 60
    - path: "charts/arr-stack/values.yaml"
      provides: "arrconf.image.tag bumped to 0.6.0 (chart-pin co-bump per D-05)"
      contains: "tag: \"0.6.0\""
  key_links:
    - from: "tools/arrconf/arrconf/__main__.py"
      to: "tools/arrconf/arrconf/generators/categories.py"
      via: "from arrconf.generators.categories import generate_qbit_categories"
      pattern: "from arrconf\\.generators\\.categories import"
    - from: "tools/arrconf/arrconf/__main__.py"
      to: "tools/arrconf/arrconf/reconcilers/_shared.py"
      via: "from arrconf.reconcilers._shared import merge_with_manual"
      pattern: "merge_with_manual"
    - from: "tools/arrconf/arrconf/reconcilers/qbittorrent.py"
      to: "qBit cluster GET response"
      via: "QBIT_CATEGORY_MANAGED_FIELDS filter before model_validate"
      pattern: "QBIT_CATEGORY_MANAGED_FIELDS"
---

<objective>
Wire the qBit reconciler to consume Categories-derived qBit categories via the pre-merge mechanism in `__main__.py`, AND fix the qBit idempotence false-positive #1 by filtering cluster GET responses to the managed-field allowlist.

Purpose: Closes REQ-categories-qbit-propagation (wiring half) and REQ-idempotence-fp-fix (FP #1). Sets the chart-pin co-bump rhythm for Phase 10: every Wave 2 commit that touches `tools/arrconf/**` ships with the matching `values.yaml#arrconf.image.tag` bump in the same commit (D-05).

Output: Single atomic commit bundling arrconf code + `values.yaml` tag bump from `0.5.3` to `0.6.0` (FIRST Phase-10 release — major step from Phase 9-D's `0.5.3` pilot).
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
@CLAUDE.md

@tools/arrconf/arrconf/reconcilers/qbittorrent.py
@tools/arrconf/arrconf/__main__.py
@tools/arrconf/arrconf/resources/qbittorrent/category.py
@tools/arrconf/tests/fixtures/qbittorrent/categories.json
@charts/arr-stack/values.yaml

<interfaces>
<!-- Plan 10-A output (Wave 1) — consumed here. -->
```python
# arrconf/generators/categories.py
def generate_qbit_categories(cfg: RootConfig) -> list[QbitCategory]: ...
```

<!-- Plan 10-B output (Wave 1) — consumed here. -->
```python
# arrconf/reconcilers/_shared.py
def merge_with_manual(
    manual_items: list[Any], generated_items: list[Any], *, app: str, resource: str
) -> list[Any]: ...
```

<!-- qBit Category model state (read-only). -->
```python
# arrconf/resources/qbittorrent/category.py
class Category(BaseModel):
    model_config = ConfigDict(extra="allow")  # <-- FP #1 root cause
    name: str
    savePath: str = Field(default="")
```

<!-- Existing qBit reconciler entry point (sonar `_fetch_current_categories`). -->
```python
# arrconf/reconcilers/qbittorrent.py:76-85
def _fetch_current_categories(client: QbittorrentClient) -> list[Category]:
    raw = client.get(CATEGORIES_PATH)
    return [Category.model_validate(v) for v in raw.values()]
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 10-C-01: Add QBIT_CATEGORY_MANAGED_FIELDS allowlist + filter cluster GET (FP fix #1)</name>
  <files>tools/arrconf/arrconf/reconcilers/qbittorrent.py, tools/arrconf/tests/test_idempotence_fp.py</files>
  <read_first>
    - tools/arrconf/arrconf/reconcilers/qbittorrent.py lines 1-90 (current _fetch_current_categories)
    - tools/arrconf/arrconf/resources/qbittorrent/category.py (extra="allow" model)
    - tools/arrconf/arrconf/reconcilers/jellyfin.py lines 56-67 (SERVER_CONFIG_ALLOWLIST precedent — pattern to mirror)
    - tools/arrconf/tests/fixtures/qbittorrent/categories.json (real GET shape — the source of the FP)
    - 10-RESEARCH.md §"FP #1: qBit Categories"
    - 10-PATTERNS.md §"`tools/arrconf/arrconf/reconcilers/qbittorrent.py` — FP fix #1 + categories wiring"
  </read_first>
  <behavior>
    - Test 1: Given a cluster categories GET dict containing extra fields (`download_path: None`, `ratio_limit: -2`, `seeding_time_limit: -2`, etc.) AND a desired list with matching `(name, savePath)`, the reconcile plan emits all `Action.NO_OP` (no UPDATE).
    - Test 2: Pre-fix behavior (sanity): without the allowlist, the same fixture would produce UPDATE actions due to extra-field round-trip. (Already proven empirically in Phase 5 SC#5 deviation — referenced for context only; no need to write this test.)
    - Test 3: After fix, the `_fetch_current_categories` return value only carries `name` + `savePath` fields (no extras).
  </behavior>
  <action>
1. **Add the allowlist constant** to `tools/arrconf/arrconf/reconcilers/qbittorrent.py` immediately after the `# API paths` block (around line 51, before the `Result type` section):

```python
# B2 allowlist: fields arrconf manages on qBit Category (D-04b FP fix #1).
# Why a frozenset and not Model.model_fields.keys() (B1)?
# Category uses extra="allow" — cluster GET responses carry download_path,
# ratio_limit, inactive_seeding_time_limit, seeding_time_limit,
# share_limit_action (verified in tests/fixtures/qbittorrent/categories.json).
# Those extra keys round-trip via __pydantic_extra__ and cause spurious
# UPDATE plans on every run (FP #1). Filter the cluster dict to the managed
# fields BEFORE Category.model_validate() so the comparator sees a clean view.
QBIT_CATEGORY_MANAGED_FIELDS: frozenset[str] = frozenset({"name", "savePath"})
```

2. **Modify `_fetch_current_categories`** (lines 76-85) to filter:

```python
def _fetch_current_categories(client: QbittorrentClient) -> list[Category]:
    """GET /api/v2/torrents/categories and normalize dict response to list.

    qBit returns a dict keyed by category name:
        {"sonarr-tv": {"name": "sonarr-tv", "savePath": "/data/series"}, ...}

    qBit 5.1+ adds extra keys (download_path, ratio_limit, seeding_time_limit,
    share_limit_action) — Category model is extra="allow" so they round-trip
    through model_dump and cause FP #1 (Phase 5 SC#5 deviation, 14 update events).
    Filter to QBIT_CATEGORY_MANAGED_FIELDS BEFORE model_validate (D-04b B2 fix).
    """
    raw = client.get(CATEGORIES_PATH)
    return [
        Category.model_validate({k: v for k, v in obj.items() if k in QBIT_CATEGORY_MANAGED_FIELDS})
        for obj in raw.values()
    ]
```

3. **Create the regression test** `tools/arrconf/tests/test_idempotence_fp.py`. This file will accumulate FP #2 (10-H) + FP #3 (10-F) regression tests — start with just the qBit test here:

```python
"""Phase 10 idempotence FP regression tests (REQ-idempotence-fp-fix).

Each FP fix gets one focused test asserting that cluster GET responses with
extra (server-side) fields no longer cause spurious UPDATE plans.

Coverage:
- test_qbit_category_fp_fix (FP #1 — Plan 10-C) ← THIS TASK
- test_seerr_user_fp_fix    (FP #3 — Plan 10-F, to be added)
- test_prowlarr_app_fp_fix  (FP #2 — Plan 10-H, to be added)
"""

from __future__ import annotations

from arrconf.differ import Action, reconcile
from arrconf.reconcilers.qbittorrent import (
    QBIT_CATEGORY_MANAGED_FIELDS,
    _fetch_current_categories,
)
from arrconf.resources.qbittorrent.category import Category


class _StubClient:
    """Minimal QbittorrentClient stand-in for unit testing _fetch_current_categories."""

    def __init__(self, raw: dict[str, dict[str, object]]) -> None:
        self._raw = raw

    def get(self, _path: str) -> dict[str, dict[str, object]]:
        return self._raw


def test_qbit_category_managed_fields_constant() -> None:
    """QBIT_CATEGORY_MANAGED_FIELDS exposes exactly the 2 managed keys."""
    assert QBIT_CATEGORY_MANAGED_FIELDS == frozenset({"name", "savePath"})


def test_qbit_category_fp_fix_no_op_on_extras() -> None:
    """FP #1: cluster returns extra fields; differ should emit only NO_OP.

    Pre-fix: download_path/ratio_limit/etc. roundtripped via extra='allow'
    caused spurious UPDATE on every reconcile run.
    """
    cluster_with_extras = {
        "series-zoe": {
            "name": "series-zoe",
            "savePath": "/data/torrents/series-zoe",
            "download_path": None,
            "inactive_seeding_time_limit": -2,
            "ratio_limit": -2,
            "seeding_time_limit": -2,
            "share_limit_action": "Default",
        },
        "films": {
            "name": "films",
            "savePath": "/data/torrents/films",
            "download_path": None,
            "ratio_limit": -2,
        },
    }
    stub = _StubClient(cluster_with_extras)
    current = _fetch_current_categories(stub)  # type: ignore[arg-type]

    # Filtered models must have no extra keys in their model_dump output:
    for c in current:
        dumped = c.model_dump()
        for forbidden_key in ("download_path", "ratio_limit", "seeding_time_limit", "share_limit_action", "inactive_seeding_time_limit"):
            assert forbidden_key not in dumped, f"FP #1 leak: {forbidden_key} still in cluster-derived model after filter"

    desired = [
        Category(name="series-zoe", savePath="/data/torrents/series-zoe"),
        Category(name="films", savePath="/data/torrents/films"),
    ]
    plan = reconcile(current=current, desired=desired, match_key="name", prune=False)

    # The full SC#2 dispositive: all-NO_OP plan when cluster == desired (modulo extras).
    assert plan, "reconcile returned empty plan — fixture mismatch with 2 desired entries"
    for p in plan:
        assert p.action == Action.NO_OP, (
            f"FP #1 NOT FIXED: plan action {p.action} for {p.name} "
            f"(diff_fields={p.diff_fields}). Expected NO_OP."
        )
```

Run:
- `cd tools/arrconf && uv run pytest tests/test_idempotence_fp.py -x -v`
- `cd tools/arrconf && uv run ruff check arrconf/reconcilers/qbittorrent.py tests/test_idempotence_fp.py`
- `cd tools/arrconf && uv run ruff format --check arrconf/reconcilers/qbittorrent.py tests/test_idempotence_fp.py`
- `cd tools/arrconf && uv run mypy arrconf/reconcilers/qbittorrent.py tests/test_idempotence_fp.py`
- Run the FULL test suite to confirm no regression: `cd tools/arrconf && uv run pytest -x`
  </action>
  <verify>
    <automated>cd tools/arrconf && uv run pytest tests/test_idempotence_fp.py -x -v &amp;&amp; uv run ruff check arrconf/reconcilers/qbittorrent.py tests/test_idempotence_fp.py &amp;&amp; uv run ruff format --check arrconf/reconcilers/qbittorrent.py tests/test_idempotence_fp.py &amp;&amp; uv run mypy arrconf/reconcilers/qbittorrent.py tests/test_idempotence_fp.py &amp;&amp; uv run pytest -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep "QBIT_CATEGORY_MANAGED_FIELDS: frozenset\[str\]" tools/arrconf/arrconf/reconcilers/qbittorrent.py` exits 0
    - `grep -A 2 "def _fetch_current_categories" tools/arrconf/arrconf/reconcilers/qbittorrent.py | grep "QBIT_CATEGORY_MANAGED_FIELDS"` exits 0 (allowlist used in body)
    - `test -f tools/arrconf/tests/test_idempotence_fp.py` exits 0
    - `grep "def test_qbit_category_fp_fix_no_op_on_extras" tools/arrconf/tests/test_idempotence_fp.py` exits 0
    - The verify command exits 0 (new tests pass + full suite stays green)
  </acceptance_criteria>
  <done>FP #1 fixed; B2 allowlist constant added; regression test passes; full pytest suite stays green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 10-C-02: Pre-merge qBit categories in __main__.py (apply + diff + dump)</name>
  <files>tools/arrconf/arrconf/__main__.py, tools/arrconf/tests/test_qbittorrent_categories.py</files>
  <read_first>
    - tools/arrconf/arrconf/__main__.py (full file — locate qBit branch in apply, diff, dump)
    - tools/arrconf/arrconf/generators/categories.py (Plan 10-A output — function signatures)
    - tools/arrconf/arrconf/reconcilers/_shared.py (Plan 10-B output — merge_with_manual signature)
    - 10-PATTERNS.md §"`tools/arrconf/arrconf/__main__.py` — pre-merge injection point"
    - 10-RESEARCH.md §"Pattern 3: __main__.py injection point" + §"Pitfall 5: __main__.py diff and dump commands need the same pre-merge"
  </read_first>
  <behavior>
    - Test 1: With `cfg.categories = [10 production entries]` and `instance.categories.items = []` (manual empty), the reconciler receives 10 Categories-derived qBit categories.
    - Test 2: With non-empty `instance.categories.items` (manual override), the reconciler receives the manual items unchanged (generated skipped).
    - Test 3: Same pre-merge applies in the `dump` command path (verified via shared helper call site — not a separate test, code review item).
  </behavior>
  <action>
1. **Locate the qBit branch in `apply`** (`tools/arrconf/arrconf/__main__.py` lines ~195-243).

2. **Add imports at the top of the file** (near other arrconf imports — preserve alphabetical order):

```python
from arrconf.generators.categories import generate_qbit_categories
from arrconf.reconcilers._shared import merge_with_manual
```

3. **Inject pre-merge in the qBit `apply` branch.** AFTER `qbit_instance = root.qbittorrent["main"]` (currently line ~217) and BEFORE `qbit_client = QbittorrentClient(...)`, insert:

```python
            # Phase 10 pre-merge (D-01/D-02): Categories→qBit categories.
            # When instance.categories.items is empty, use Categories-derived
            # list. When non-empty, manual section wins entirely (merge_with_manual).
            qbit_generated = generate_qbit_categories(root)
            qbit_instance.categories.items = merge_with_manual(
                qbit_instance.categories.items,
                qbit_generated,
                app="qbittorrent",
                resource="categories",
            )
```

4. **Locate the qBit branch in `dump`** (likely lines ~330-380 — search for `qbittorrent` in dump section). Same pre-merge logic applies if dump touches the categories section. **If `dump` doesn't dump qBit categories today**, no action is needed there — confirm by reading `arrconf/dump.py` for qBit category emission. Document the verification in the SUMMARY.

5. **Locate the qBit branch in `diff`** (similar pattern). Apply the same pre-merge per Pitfall 5 (`diff` must use the same merged shape as `apply` to avoid drift between them).

6. **Create the wiring test** `tools/arrconf/tests/test_qbittorrent_categories.py`:

```python
"""Phase 10 wiring test: Categories→qBit categories via merge_with_manual.

Validates the integration between:
- arrconf.generators.categories.generate_qbit_categories
- arrconf.reconcilers._shared.merge_with_manual
- arrconf.reconcilers.qbittorrent._reconcile_categories

NOT a __main__.py end-to-end test — just verifies the merge contract delivers
the right list to the reconciler input slot.
"""

from __future__ import annotations

from arrconf.config import RootConfig
from arrconf.generators.categories import generate_qbit_categories
from arrconf.reconcilers._shared import merge_with_manual
from arrconf.resources.qbittorrent.category import Category


# Production fixture (same 10-category set as test_generators_categories.py).
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


def test_categories_wiring_10_entries() -> None:
    """When manual is empty + 10 categories declared → reconciler sees 10 entries."""
    cfg = RootConfig.model_validate({"categories": PRODUCTION_CATEGORIES})
    generated = generate_qbit_categories(cfg)
    merged = merge_with_manual([], generated, app="qbittorrent", resource="categories")
    assert len(merged) == 10
    names = {c.name for c in merged}
    assert "series-zoe" in names
    assert "films" in names


def test_manual_override_wins() -> None:
    """When manual is non-empty → generated is skipped entirely (D-02)."""
    cfg = RootConfig.model_validate({"categories": PRODUCTION_CATEGORIES})
    generated = generate_qbit_categories(cfg)
    manual = [Category(name="sonarr-tv", savePath="/data/series")]
    merged = merge_with_manual(manual, generated, app="qbittorrent", resource="categories")
    assert len(merged) == 1
    assert merged[0].name == "sonarr-tv"


def test_savepath_format() -> None:
    """Generated qBit savePath uses /data/torrents/<name> not <c.base_path>."""
    cfg = RootConfig.model_validate({"categories": PRODUCTION_CATEGORIES})
    generated = generate_qbit_categories(cfg)
    zoe = next(c for c in generated if c.name == "series-zoe")
    assert zoe.savePath == "/data/torrents/series-zoe"
```

Run:
- `cd tools/arrconf && uv run pytest tests/test_qbittorrent_categories.py -x -v`
- `cd tools/arrconf && uv run ruff check arrconf/__main__.py tests/test_qbittorrent_categories.py`
- `cd tools/arrconf && uv run ruff format --check arrconf/__main__.py tests/test_qbittorrent_categories.py`
- `cd tools/arrconf && uv run mypy arrconf/__main__.py tests/test_qbittorrent_categories.py`
- `cd tools/arrconf && uv run pytest -x`  (full suite — confirm Phase 9 no-regression test stays green)
  </action>
  <verify>
    <automated>cd tools/arrconf && uv run pytest tests/test_qbittorrent_categories.py tests/test_phase9_no_regression.py -x -v &amp;&amp; uv run ruff check arrconf/__main__.py tests/test_qbittorrent_categories.py &amp;&amp; uv run ruff format --check arrconf/__main__.py tests/test_qbittorrent_categories.py &amp;&amp; uv run mypy arrconf/__main__.py tests/test_qbittorrent_categories.py &amp;&amp; uv run pytest -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep "from arrconf.generators.categories import generate_qbit_categories" tools/arrconf/arrconf/__main__.py` exits 0
    - `grep "from arrconf.reconcilers._shared import merge_with_manual" tools/arrconf/arrconf/__main__.py` exits 0
    - `grep -c "merge_with_manual" tools/arrconf/arrconf/__main__.py` ≥ 1
    - `grep -c "app=\"qbittorrent\", resource=\"categories\"" tools/arrconf/arrconf/__main__.py` ≥ 1
    - `grep -c 'generate_qbit_categories' tools/arrconf/arrconf/__main__.py` ≥ 2  (Pitfall 5: apply branch + diff branch BOTH call the generator; if `dump` does not emit qBit categories, document in <action> with reasoning — otherwise extend the count to ≥ 3)
    - `test -f tools/arrconf/tests/test_qbittorrent_categories.py` exits 0
    - `grep -c "^def test_" tools/arrconf/tests/test_qbittorrent_categories.py` ≥ 3
    - `cd tools/arrconf && uv run pytest tests/test_phase9_no_regression.py -x` exits 0 (D-13 no-regression preserved)
    - The verify command exits 0 (all tests pass + lint + format + mypy + full suite green)
  </acceptance_criteria>
  <done>qBit pre-merge wired in __main__.py; wiring tests pass; Phase 9 no-regression intact.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 10-C-03: Chart-pin co-bump — values.yaml arrconf.image.tag 0.5.3 → 0.6.0</name>
  <files>charts/arr-stack/values.yaml</files>
  <read_first>
    - charts/arr-stack/values.yaml lines 440-460 (current arrconf image block — bump target)
    - CLAUDE.md §"Annotations Renovate (CRITIQUE)" (must preserve the `# renovate: image=...` comment)
    - 10-CONTEXT.md §"Chart-pin pre-bump pattern documentation surface (D-05)"
    - .planning/STATE.md §"Phase 7 deviations + follow-ups" CF-07-1 (D-07-CHART-PIN-LOOP context)
  </read_first>
  <behavior>
    - The tag string on the `arrconf` chart block transitions from `"0.5.3"` to `"0.6.0"`.
    - The Renovate annotation `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` is preserved directly above the `repository:` line (no blank line in between).
    - No other values.yaml content is modified.
  </behavior>
  <action>
1. Open `charts/arr-stack/values.yaml`. Locate the arrconf block around line 449-451:

```yaml
          image:
            # renovate: image=ghcr.io/tom333/arr-stack-arrconf
            repository: ghcr.io/tom333/arr-stack-arrconf
            tag: "0.5.3"
            pullPolicy: IfNotPresent
```

2. Change ONLY the `tag` value from `"0.5.3"` to `"0.6.0"` — this is the first Phase 10 release (minor bump from 0.5.x). All other Phase 10 plans (10-D, 10-E, 10-F, 10-G, 10-H, 10-J) ship patch bumps `0.6.1`, `0.6.2`, etc.

3. **DO NOT modify** the renovate annotation comment or the `repository:` line.

4. Run helm lint to confirm the chart still passes:
- `helm lint charts/arr-stack/` (requires the multi-alias workaround per CLAUDE.md if running outside CI; in CI the workflow handles it)
- If `helm lint` is not available in the executor environment, fall back to a YAML parse check:
  `python -c "import yaml; yaml.safe_load(open('charts/arr-stack/values.yaml'))"`

5. **CRITICAL — this task's commit must bundle the changes from Task 10-C-01 + Task 10-C-02 + this values.yaml edit into a SINGLE commit per D-05.**
  </action>
  <verify>
    <automated>grep -E '^\s+tag: "0\.6\.0"' charts/arr-stack/values.yaml &amp;&amp; grep -B 1 "repository: ghcr.io/tom333/arr-stack-arrconf" charts/arr-stack/values.yaml | grep "renovate: image=ghcr.io/tom333/arr-stack-arrconf" &amp;&amp; python3 -c "import yaml; yaml.safe_load(open('charts/arr-stack/values.yaml'))"</automated>
  </verify>
  <acceptance_criteria>
    - `grep 'tag: "0\.6\.0"' charts/arr-stack/values.yaml` exits 0
    - `grep 'tag: "0\.5\.3"' charts/arr-stack/values.yaml` returns empty (0.5.3 line gone for arrconf — other charts may still reference unrelated 0.5.3 values)
    - `grep -c "# renovate: image=ghcr.io/tom333/arr-stack-arrconf" charts/arr-stack/values.yaml` ≥ 1 (annotation preserved)
    - `python3 -c "import yaml; yaml.safe_load(open('charts/arr-stack/values.yaml'))"` exits 0 (YAML is still valid)
    - When the executor finalizes the plan, the resulting `git show HEAD --stat` MUST list BOTH `tools/arrconf/...` files AND `charts/arr-stack/values.yaml` in the same commit (chart-pin co-bump per D-05).
  </acceptance_criteria>
  <done>arrconf.image.tag bumped 0.5.3→0.6.0 in values.yaml; renovate annotation preserved; YAML valid; commit bundles arrconf code + values.yaml together.</done>
</task>

</tasks>

<verification>
End-to-end check (must run after all 3 tasks land):
```bash
cd tools/arrconf && uv run pytest -x
git show HEAD --stat   # MUST list tools/arrconf/**/*.py + charts/arr-stack/values.yaml
```

The chart-pin co-bump invariant: a single commit MUST contain both the arrconf code change AND the values.yaml tag bump. Reviewer rejects splits.
</verification>

<success_criteria>
- QBIT_CATEGORY_MANAGED_FIELDS allowlist added; FP fix #1 regression test passes.
- qBit pre-merge wired in `__main__.py` apply (and diff/dump if applicable per Pitfall 5).
- `tests/test_qbittorrent_categories.py` proves Categories→qBit flows 10 entries when manual is empty.
- `tests/test_phase9_no_regression.py` still passes (D-13 invariant preserved by override merge).
- `charts/arr-stack/values.yaml` arrconf.image.tag: 0.5.3 → 0.6.0; renovate annotation preserved.
- Single atomic commit per D-05 (chart-pin co-bump).
- All lints + mypy clean.
</success_criteria>

<output>
After completion, create `.planning/phases/10-categories-6-app-propagation/10-C-qbit-wiring-fp-SUMMARY.md` documenting:
- Tasks executed with commit SHA (a single SHA covering all 3 tasks — chart-pin co-bump)
- Test count + pass status
- D-05 chart-pin co-bump dispositive evidence: `git show <SHA> --stat` listing both arrconf code and values.yaml in the same commit
- Note for downstream Wave 2 plans: each subsequent Wave 2 plan (10-D, 10-E, 10-F, 10-G, 10-H) bumps the tag to 0.6.1, 0.6.2, etc.
- Confirmation that `_fetch_current_categories` now filters via the allowlist BEFORE model_validate
- Confirmation that diff + dump command branches got the same pre-merge treatment (Pitfall 5)
</output>
