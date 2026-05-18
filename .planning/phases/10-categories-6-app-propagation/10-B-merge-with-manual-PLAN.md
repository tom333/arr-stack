---
phase: 10-categories-6-app-propagation
plan: 10-B-merge-with-manual
type: execute
wave: 1
depends_on: []
files_modified:
  - tools/arrconf/arrconf/reconcilers/_shared.py
  - tools/arrconf/tests/test_merge_with_manual.py
autonomous: false
requirements:
  - REQ-categories-qbit-propagation
  - REQ-categories-sonarr-propagation
  - REQ-categories-radarr-propagation
  - REQ-categories-seerr-routing
  - REQ-categories-jellyfin-paths
requirements_addressed:
  - REQ-categories-* (merge contract — common to all 5 propagation REQs)
tags:
  - python
  - shared-helper
  - merge
  - override-toggle

must_haves:
  truths:
    - "A new public function `merge_with_manual(manual_items, generated_items, *, app, resource)` exists in `tools/arrconf/arrconf/reconcilers/_shared.py` (D-02 per-resource toggle)."
    - "Behaviour A: `manual_items` non-empty → function returns `manual_items` unchanged and emits a structlog event `merge_decision` with `source=\"manual\"`, `n=len(manual_items)`, `generated_skipped=len(generated_items)`."
    - "Behaviour B: `manual_items` empty → function returns `generated_items` and emits `merge_decision` with `source=\"categories\"`, `n=len(generated_items)`."
    - "Both empty → returns `[]` (empty list); log emits `source=\"categories\"`, `n=0`."
    - "Signature is keyword-only for `app` and `resource` (forces explicit naming at call sites)."
    - "Before Wave 2 opens, the operator has run `tools/snapshot/snapshot.sh --output snapshots/before-phase-10-$(date +%F)/` and committed the snapshot directory to git (ADR-6 baseline safety net for any cluster-touch test in Wave 2)."
    - "Unit tests in `tests/test_merge_with_manual.py` cover the three D-02 cases (manual-wins, generated-wins, both-empty) plus log event structure verification."
  artifacts:
    - path: "tools/arrconf/arrconf/reconcilers/_shared.py"
      provides: "Adds `merge_with_manual()` next to existing `_resolve_download_client_tag_labels()` and `_reconcile_remote_path_mappings()`."
      contains: "def merge_with_manual"
    - path: "tools/arrconf/tests/test_merge_with_manual.py"
      provides: "Three test cases per D-02 contract + log event capture."
      min_lines: 80
  key_links:
    - from: "tools/arrconf/arrconf/reconcilers/_shared.py"
      to: "structlog (already imported)"
      via: "log.info(\"merge_decision\", ...) — same logger as existing helpers"
      pattern: "log\\.info\\(\"merge_decision\""
    - from: "Wave 2 plans (10-C..10-G) and 10-F"
      to: "tools/arrconf/arrconf/reconcilers/_shared.py"
      via: "from arrconf.reconcilers._shared import merge_with_manual"
      pattern: "from arrconf\\.reconcilers\\._shared import merge_with_manual"
---

<objective>
Add the per-resource override toggle helper that bridges Categories-derived resources (from Plan 10-A) with the manual YAML sections (v0.2.0 flat sections). This is the D-02 contract: "manual non-empty wins entirely, manual empty → use generated".

Purpose: Wave 2 plans (10-C..10-G) all consume this helper. The function lives in `reconcilers/_shared.py` next to the existing cross-reconciler helpers — same style, same logger, same docstring convention.

Output: A new public function with explicit D-02 contract + 3 unit tests covering the toggle's behaviour + log event shape.

This plan is PURE PYTHON — no I/O, no reconciler changes, no chart-pin bump (the chart-pin co-bump per D-05 lands with Plan 10-C since this plan's output is also dead until Wave 2 wires it).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/phases/10-categories-6-app-propagation/10-CONTEXT.md
@.planning/phases/10-categories-6-app-propagation/10-RESEARCH.md
@.planning/phases/10-categories-6-app-propagation/10-PATTERNS.md
@.planning/phases/10-categories-6-app-propagation/10-VALIDATION.md

@tools/arrconf/arrconf/reconcilers/_shared.py

<interfaces>
<!-- Existing structure of _shared.py (read the full file before editing). -->

Current public API in `_shared.py`:
```python
REMOTE_PATH_MAPPING_PATH = "/remotepathmapping"
TAG_PATH = "/tag"
log = structlog.get_logger()

def _reconcile_remote_path_mappings(client, items, prune, dry_run) -> list[str]: ...
def _resolve_download_client_tag_labels(items, all_tags, app_name="Sonarr/Radarr") -> list[Any]: ...
```

Existing structlog event pattern (lines 66-70):
```python
log.info("dry_run_skip", action="add", resource="rpm", key=str(k))
```

New `merge_with_manual` follows identical style.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 10-B-01: Add merge_with_manual() helper to _shared.py</name>
  <files>tools/arrconf/arrconf/reconcilers/_shared.py</files>
  <read_first>
    - tools/arrconf/arrconf/reconcilers/_shared.py (full file — match the existing docstring + log-event conventions)
    - 10-RESEARCH.md §"Pattern 2: merge_with_manual() in _shared.py" (lines 275-316)
    - 10-PATTERNS.md §"`tools/arrconf/arrconf/reconcilers/_shared.py` — `merge_with_manual()` addition"
    - 10-CONTEXT.md §"Override merge semantics (D-02)"
  </read_first>
  <behavior>
    - Test 1: `merge_with_manual(["a", "b"], ["x", "y", "z"], app="sonarr", resource="tags")` returns `["a", "b"]` and log captures `source="manual"`, `n=2`, `generated_skipped=3`.
    - Test 2: `merge_with_manual([], ["x", "y", "z"], app="sonarr", resource="tags")` returns `["x", "y", "z"]` and log captures `source="categories"`, `n=3`.
    - Test 3: `merge_with_manual([], [], app="qbit", resource="categories")` returns `[]` and log captures `source="categories"`, `n=0`.
  </behavior>
  <action>
Open `tools/arrconf/arrconf/reconcilers/_shared.py`. The current file ends at line 145 (`return resolved`). Append a new helper at the end of the file, BEFORE any trailing blank line:

```python


def merge_with_manual(
    manual_items: list[Any],
    generated_items: list[Any],
    *,
    app: str,
    resource: str,
) -> list[Any]:
    """Per-resource toggle bridging Categories-derived resources with manual YAML (D-02).

    Phase 10 contract: when an operator has declared resources manually in the
    v0.2.0 flat section (``manual_items`` non-empty), arrconf uses the manual
    list verbatim and SKIPS the Categories-generated list entirely. When the
    manual list is empty, the Categories-derived list takes effect. There is
    no item-level merging — the toggle is per-resource (e.g. one toggle for
    ``sonarr.tags``, one for ``sonarr.root_folders``, etc.).

    Operator escape hatch: declare the full resource list manually to opt out
    of Categories-driven generation for that one resource. The transition layer
    is planned for removal in v0.4.0+ (REQ-categories-deprecation).

    Args:
        manual_items: the v0.2.0 ``instance.<section>.items`` list.
        generated_items: the Categories-derived list from
            ``arrconf.generators.categories``.
        app: app name for the log event (e.g. ``"sonarr"``, ``"qbit"``).
        resource: resource name for the log event (e.g. ``"tags"``,
            ``"root_folders"``, ``"download_clients"``).

    Returns:
        The list that should be passed to the reconciler. Caller assigns it
        back to ``instance.<section>.items`` before reconciler dispatch.

    Log events:
        - ``merge_decision`` with ``source="manual"``, ``n=len(manual_items)``,
          ``generated_skipped=len(generated_items)`` when manual wins.
        - ``merge_decision`` with ``source="categories"``,
          ``n=len(generated_items)`` when generated wins.

    Shared across all 6 reconciler pre-merge callsites (D-02). Called from
    ``arrconf.__main__`` per-app branches before reconciler dispatch.
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

Run lints:
- `cd tools/arrconf && uv run ruff check arrconf/reconcilers/_shared.py`
- `cd tools/arrconf && uv run ruff format --check arrconf/reconcilers/_shared.py`
- `cd tools/arrconf && uv run mypy arrconf/reconcilers/_shared.py`
  </action>
  <verify>
    <automated>cd tools/arrconf && uv run ruff check arrconf/reconcilers/_shared.py &amp;&amp; uv run ruff format --check arrconf/reconcilers/_shared.py &amp;&amp; uv run mypy arrconf/reconcilers/_shared.py &amp;&amp; uv run python -c "from arrconf.reconcilers._shared import merge_with_manual; assert merge_with_manual([], ['a'], app='x', resource='y') == ['a']; assert merge_with_manual(['m'], ['a'], app='x', resource='y') == ['m']; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep "^def merge_with_manual" tools/arrconf/arrconf/reconcilers/_shared.py` exits 0
    - `grep -c "merge_decision" tools/arrconf/arrconf/reconcilers/_shared.py` ≥ 2 (two log.info calls)
    - `grep "source=\"manual\"\|source=\"categories\"" tools/arrconf/arrconf/reconcilers/_shared.py | wc -l` ≥ 2
    - `grep "generated_skipped" tools/arrconf/arrconf/reconcilers/_shared.py` exits 0
    - The verify command exits 0 (ruff + format + mypy + smoke import + 2 behavioural assertions pass)
  </acceptance_criteria>
  <done>merge_with_manual() is implemented in _shared.py with D-02 semantics + 2 structlog event variants; lint + format + mypy pass; smoke import works.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 10-B-02: Unit tests for merge_with_manual() — 3 D-02 cases</name>
  <files>tools/arrconf/tests/test_merge_with_manual.py</files>
  <read_first>
    - tools/arrconf/arrconf/reconcilers/_shared.py (the merge_with_manual function from Task 10-B-01)
    - tools/arrconf/tests/test_differ.py (existing unit-test style for pure functions)
    - 10-PATTERNS.md §"test_merge_with_manual.py"
    - 10-VALIDATION.md §"Per-Task Verification Map" row 10-B-01
  </read_first>
  <behavior>
    - Test 1: Manual wins — `merge_with_manual([1, 2, 3], [10, 20], app="sonarr", resource="tags")` returns `[1, 2, 3]`.
    - Test 2: Generated wins — `merge_with_manual([], [10, 20], app="sonarr", resource="tags")` returns `[10, 20]`.
    - Test 3: Both empty — `merge_with_manual([], [], app="qbit", resource="categories")` returns `[]`.
    - Test 4: Log event captures `source="manual"` + `generated_skipped` when manual wins.
    - Test 5: Log event captures `source="categories"` + `n` matches generated len when generated wins.
    - Test 6: Function signature enforces keyword-only `app` and `resource` — `merge_with_manual([], [], "sonarr", "tags")` raises TypeError.
  </behavior>
  <action>
Create `tools/arrconf/tests/test_merge_with_manual.py`:

```python
"""Unit tests for arrconf.reconcilers._shared.merge_with_manual (D-02).

Three behavioural cases covering the per-resource toggle:
- manual non-empty → manual wins, generated skipped
- manual empty → generated wins
- both empty → empty list returned (edge case)
"""

from __future__ import annotations

import logging

import pytest
import structlog

from arrconf.reconcilers._shared import merge_with_manual


@pytest.fixture(autouse=True)
def configure_structlog_capture(caplog: pytest.LogCaptureFixture) -> None:
    """Route structlog output through the standard logger so caplog can capture it.

    Note: structlog in the arrconf project is wired in arrconf.logging.configure_logging().
    For tests we keep the default ProcessorFormatter pass-through so log records carry
    the structured kv pairs as attributes on the LogRecord (structlog ≥ 23).
    """
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.KeyValueRenderer(key_order=["event"]),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )
    caplog.set_level(logging.INFO)


def test_manual_non_empty_wins() -> None:
    """D-02 Behaviour A: manual list survives, generated discarded."""
    result = merge_with_manual([1, 2, 3], [10, 20, 30, 40], app="sonarr", resource="tags")
    assert result == [1, 2, 3]


def test_manual_empty_uses_generated() -> None:
    """D-02 Behaviour B: empty manual → Categories-derived list takes effect."""
    result = merge_with_manual([], [10, 20, 30], app="sonarr", resource="root_folders")
    assert result == [10, 20, 30]


def test_both_empty_returns_empty() -> None:
    """Edge case: nothing to merge → empty list."""
    result = merge_with_manual([], [], app="qbit", resource="categories")
    assert result == []


def test_log_event_manual_wins(caplog: pytest.LogCaptureFixture) -> None:
    """Manual-wins emits source='manual', n=<manual len>, generated_skipped=<generated len>."""
    merge_with_manual(["a", "b"], ["x", "y", "z"], app="sonarr", resource="download_clients")
    matching = [r for r in caplog.records if "merge_decision" in r.getMessage()]
    assert matching, f"merge_decision event not logged; got records: {[r.getMessage() for r in caplog.records]}"
    msg = matching[-1].getMessage()
    assert "source=manual" in msg
    assert "n=2" in msg
    assert "generated_skipped=3" in msg


def test_log_event_generated_wins(caplog: pytest.LogCaptureFixture) -> None:
    """Generated-wins emits source='categories', n=<generated len>."""
    merge_with_manual([], ["x", "y", "z"], app="sonarr", resource="tags")
    matching = [r for r in caplog.records if "merge_decision" in r.getMessage()]
    assert matching, f"merge_decision event not logged; got records: {[r.getMessage() for r in caplog.records]}"
    msg = matching[-1].getMessage()
    assert "source=categories" in msg
    assert "n=3" in msg


def test_app_and_resource_are_keyword_only() -> None:
    """Signature enforces explicit keyword usage to prevent ambiguous call sites."""
    with pytest.raises(TypeError):
        merge_with_manual([], [], "sonarr", "tags")  # type: ignore[misc]
```

Run:
- `cd tools/arrconf && uv run pytest tests/test_merge_with_manual.py -x -v`
- `cd tools/arrconf && uv run ruff check tests/test_merge_with_manual.py`
- `cd tools/arrconf && uv run ruff format --check tests/test_merge_with_manual.py`
- `cd tools/arrconf && uv run mypy tests/test_merge_with_manual.py`
  </action>
  <verify>
    <automated>cd tools/arrconf && uv run pytest tests/test_merge_with_manual.py -x -v &amp;&amp; uv run ruff check tests/test_merge_with_manual.py &amp;&amp; uv run ruff format --check tests/test_merge_with_manual.py &amp;&amp; uv run mypy tests/test_merge_with_manual.py</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tools/arrconf/tests/test_merge_with_manual.py` exits 0
    - `grep -c "^def test_" tools/arrconf/tests/test_merge_with_manual.py` ≥ 6
    - `grep "test_manual_non_empty_wins\|test_manual_empty_uses_generated\|test_both_empty_returns_empty" tools/arrconf/tests/test_merge_with_manual.py | wc -l` == 3
    - The verify command exits 0 (all 6 tests pass + ruff + format + mypy clean)
  </acceptance_criteria>
  <done>6 unit tests pass exercising the D-02 toggle's behaviour, log events, and signature; ruff + format + mypy clean.</done>
</task>

<task id="10-B-03" type="checkpoint:human-action" autonomous="false">
  <name>Task 10-B-03: ADR-6 baseline snapshot before Wave 2 (operator)</name>
  <files>snapshots/before-phase-10-YYYY-MM-DD/ (operator creates via tools/snapshot/snapshot.sh; date varies)</files>
  <read_first>
    - CLAUDE.md §"Workflow snapshot (CRITIQUE — à respecter avant tout test risqué)"
    - spec.md §11 ADR-6
    - tools/snapshot/snapshot.sh (verify it exists and is executable)
  </read_first>
  <action>
    BEFORE Wave 2 starts: capture a pre-phase-10 cluster snapshot per ADR-6.

    This is an OPERATOR step (requires cluster API keys + reachable cluster — port-forward or in-cluster):
    - Required env vars: SONARR_API_KEY, RADARR_API_KEY, PROWLARR_API_KEY, QBT_USER+QBT_PASS, SEERR_API_KEY, JELLYFIN_API_KEY

    Steps:

    ```bash
    tools/snapshot/snapshot.sh --output snapshots/before-phase-10-$(date +%F)/

    git add snapshots/before-phase-10-*/
    git commit -m "snapshot(pre-phase-10): baseline before Categories wiring"
    ```

    This is the project's safety net before any cluster-touch test in Wave 2 (Plans 10-C..10-H).
    The autonomous executor of Plan 10-B CANNOT perform this step (no cluster keys, no cluster reachability).
    The task pauses; operator runs the snapshot + commit; operator confirms; Wave 2 may then proceed.
  </action>
  <verify>
    <automated>ls snapshots/before-phase-10-*/ 2>/dev/null | head -1 &amp;&amp; git log --oneline -10 | grep -F "snapshot(pre-phase-10): baseline before Categories wiring"</automated>
  </verify>
  <acceptance_criteria>
    - `ls snapshots/before-phase-10-*/` lists at least 1 directory (snapshot captured)
    - `git log --oneline -10 | grep -F "snapshot(pre-phase-10): baseline before Categories wiring"` exits 0 (snapshot commit recorded)
    - The snapshot directory contains JSON files from at least 6 apps (sonarr, radarr, prowlarr, qbittorrent, seerr, jellyfin)
  </acceptance_criteria>
  <resume-signal>Operator confirms "snapshot captured and committed" — Wave 2 may then proceed</resume-signal>
  <done>Pre-phase-10 ADR-6 baseline snapshot captured + committed; Wave 2 plans (10-C..10-H) can now run cluster-touching tests safely.</done>
</task>

</tasks>

<verification>
Single end-to-end check after both tasks:
```bash
cd tools/arrconf && uv run pytest tests/test_merge_with_manual.py tests/test_generators_categories.py -v
```

Wave 1 (Plans 10-A + 10-B) ends with both modules importable from any reconciler. Wave 2 wiring depends on this.
</verification>

<success_criteria>
- `merge_with_manual()` exists in `tools/arrconf/arrconf/reconcilers/_shared.py` with keyword-only `app` + `resource` parameters.
- D-02 contract proven by 6 unit tests (manual-wins / generated-wins / both-empty / log events / signature).
- ruff + ruff format --check + mypy strict all green on touched files.
- No changes to any reconciler file or any other arrconf module. No values.yaml co-bump in this plan (deferred to Plan 10-C per D-05 batching).
</success_criteria>

<output>
After completion, create `.planning/phases/10-categories-6-app-propagation/10-B-merge-with-manual-SUMMARY.md` documenting:
- Tasks executed with commit SHAs
- 6 test count + pass status
- Pointer to Wave 2 plans (10-C..10-G) that import and call this helper
- Note that 10-B does NOT bump charts/arr-stack/values.yaml — the first chart-pin co-bump is bundled with Plan 10-C (first reconciler-wiring plan).

**Snapshot discipline (ADR-6):** This plan ships pure-Python helpers — no cluster writes possible. A Phase 10 baseline snapshot is NOT required to land Plan 10-B itself. However, before Wave 2 (10-C..10-H) opens, the operator MUST run `tools/snapshot/snapshot.sh --output snapshots/before-phase-10-$(date +%F)/` AND commit the output. This is a one-shot HUMAN-runnable command — operator action, NOT a task in this plan (would require cluster API keys not available to autonomous executors). Reference this requirement in this plan's SUMMARY and in the Wave 2 plans.
</output>
