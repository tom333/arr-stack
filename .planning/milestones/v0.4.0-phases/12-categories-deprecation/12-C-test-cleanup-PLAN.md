---
phase: 12-categories-deprecation
plan: C
type: execute
wave: 2
depends_on: [A]
files_modified:
  - tools/arrconf/tests/test_sonarr_categories.py
  - tools/arrconf/tests/test_radarr_categories.py
  - tools/arrconf/tests/test_qbittorrent_categories.py
  - tools/arrconf/tests/test_jellyfin_categories.py
  - tools/arrconf/tests/test_seerr_animetags.py
  - tools/arrconf/tests/test_phase10_idempotence_sweep.py
  - tools/arrconf/tests/conftest.py
autonomous: true
requirements:
  - REQ-categories-deprecation
mode: standard

must_haves:
  truths:
    - "7 manual-override variant tests deleted across 5 per-app test files (D-07)"
    - "`test_sweep_manual_override_path` deleted from `test_phase10_idempotence_sweep.py` (D-08)"
    - "`test_sweep_categories_derived_path` renamed to `test_sweep` with updated SC#3-dispositive docstring (D-08)"
    - "~8 `*_wiring_empty_manual` tests renamed to `*_wiring` (D-09)"
    - "No test asserts on `merge_decision` structlog event (deferred ideas #5 verified)"
    - "conftest.py fixtures audited per D-10; unreferenced ones deleted; `production_cfg` is NOT in conftest.py (lives inline in test_phase10_idempotence_sweep.py — leave it alone, per D-10 explicit carve-out)"
    - "Pytest run is fully green WITHOUT the `-k` filter that Plan A used (Plan C removes the need for the filter)"
  artifacts:
    - path: "tools/arrconf/tests/test_phase10_idempotence_sweep.py"
      provides: "Single test_sweep function — sole SC#3 dispositive"
      excludes: "test_sweep_manual_override_path"
    - path: "tools/arrconf/tests/test_sonarr_categories.py"
      provides: "Renamed *_wiring tests; no override variants"
      excludes: "test_sonarr_per_resource_override_tags_only|test_sonarr_per_resource_override_rpm_only"
    - path: "tools/arrconf/tests/test_radarr_categories.py"
      excludes: "test_radarr_per_resource_override_tags_only"
    - path: "tools/arrconf/tests/test_qbittorrent_categories.py"
      excludes: "test_manual_override_wins"
    - path: "tools/arrconf/tests/test_jellyfin_categories.py"
      excludes: "test_jellyfin_manual_override_wins"
    - path: "tools/arrconf/tests/test_seerr_animetags.py"
      excludes: "test_animetags_merge_manual_wins|test_animetags_merge_empty_manual_uses_generated"
  key_links:
    - from: "tests/test_phase10_idempotence_sweep.py::test_sweep"
      to: "production_cfg fixture (defined inline in same file at line 86)"
      via: "pytest fixture wiring"
      pattern: "production_cfg"
---

<objective>
Prune all manual-path tests from the test suite per D-07/D-08/D-09. Rename the surviving sweep test to `test_sweep` and elevate its docstring to SC#3-dispositive status. Verify no test asserts on the now-removed `merge_decision` structlog event. Audit `conftest.py` and delete fixtures with zero live references.

Purpose: After Plan C, `pytest tests/` runs green with NO `-k` filter — the test suite reflects the post-deprecation reality where Categories-derived is the only path.

Output: 7 deleted tests, 1 renamed test + updated docstring, ~8 renamed wiring tests, conftest.py possibly slimmer; full pytest green.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/12-categories-deprecation/12-CONTEXT.md
@CLAUDE.md
@tools/arrconf/tests/test_phase10_idempotence_sweep.py
@tools/arrconf/tests/test_sonarr_categories.py
@tools/arrconf/tests/test_radarr_categories.py
@tools/arrconf/tests/test_qbittorrent_categories.py
@tools/arrconf/tests/test_jellyfin_categories.py
@tools/arrconf/tests/test_seerr_animetags.py
@tools/arrconf/tests/conftest.py
@.planning/phases/12-categories-deprecation/12-A-reconciler-refactor-SUMMARY.md

<interfaces>
<!-- Tests to DELETE (D-07 + D-08 — exact 8 names verified via grep on current main) -->

1. `tools/arrconf/tests/test_sonarr_categories.py`:
   - `test_sonarr_per_resource_override_tags_only` (line 157)
   - `test_sonarr_per_resource_override_rpm_only` (line 174)
2. `tools/arrconf/tests/test_radarr_categories.py`:
   - `test_radarr_per_resource_override_tags_only` (line 160)
3. `tools/arrconf/tests/test_qbittorrent_categories.py`:
   - `test_manual_override_wins` (line 105)
4. `tools/arrconf/tests/test_jellyfin_categories.py`:
   - `test_jellyfin_manual_override_wins` (line 117)
5. `tools/arrconf/tests/test_seerr_animetags.py`:
   - `test_animetags_merge_manual_wins` (line 178)
   - `test_animetags_merge_empty_manual_uses_generated` (line 188)
6. `tools/arrconf/tests/test_phase10_idempotence_sweep.py`:
   - `test_sweep_manual_override_path` (line 165)

Total: **8 test functions to delete** (CONTEXT D-07 says 7 + D-08 says 1 = 8 — verify the final count matches).

<!-- Tests to RENAME (D-08 + D-09) -->

D-08 rename:
- `test_phase10_idempotence_sweep.py::test_sweep_categories_derived_path` → `test_sweep`. Update docstring per `<docstring>` block below.

D-09 renames (`*_wiring_empty_manual` → `*_wiring`):
- `test_sonarr_categories.py::test_sonarr_tags_wiring_empty_manual` → `test_sonarr_tags_wiring`
- `test_sonarr_categories.py::test_sonarr_root_folders_wiring_empty_manual` → `test_sonarr_root_folders_wiring`
- `test_sonarr_categories.py::test_sonarr_download_clients_wiring_empty_manual` → `test_sonarr_download_clients_wiring`
- `test_sonarr_categories.py::test_sonarr_rpm_wiring_empty_manual` → `test_sonarr_rpm_wiring`
- `test_radarr_categories.py::test_radarr_tags_wiring_empty_manual` → `test_radarr_tags_wiring`
- `test_radarr_categories.py::test_radarr_root_folders_wiring_empty_manual` → `test_radarr_root_folders_wiring`
- `test_radarr_categories.py::test_radarr_rpm_wiring_empty_manual` → `test_radarr_rpm_wiring`
- `test_jellyfin_categories.py::test_jellyfin_libraries_wiring_empty_manual` → `test_jellyfin_libraries_wiring`

Total: **8 renames** (the precise count CONTEXT D-09 mentions as "~8" — verified).

Note: `test_radarr_download_clients_have_movieCategory` (test_radarr_categories.py line 124) is NOT a `_wiring_empty_manual` test and stays as-is. CONTEXT mentions "3 wiring" renames for radarr but grep shows only 2 matching the pattern — D-09 wording is approximate, the rule is mechanical: every `_wiring_empty_manual` becomes `_wiring`.

<!-- New test_sweep docstring (replace existing test_sweep_categories_derived_path docstring) -->

<docstring>
"""Phase 12 SC#3 dispositive — idempotence sweep on Categories-derived path.

This is the SOLE sweep test post-Phase-12: `merge_with_manual` is gone, the
transition layer is dead code, and the generators in `arrconf.generators.categories`
are the only source of truth for the 12 generator-derived resources (sonarr/radarr
tags+root_folders+download_clients+remote_path_mappings, qbit categories, jellyfin
libraries, seerr animeTags).

Run twice against `production_cfg` (10 categories — 5 series + 5 movies):
- Round 1 produces the initial plan.
- Round 2 must be byte-identical to round 1.
- Round 2 must emit 0 UPDATE/DELETE actions (any such action would prove a FP-style
  false mutation in the differ comparators).

Proves the 3 v0.3.0 FP fixes survived deprecation:
- FP #1 (qBit): `generate_qbit_categories` emits 10 entries; allowlist comparator
  filters cluster-side extras.
- FP #2 (Prowlarr Application): allowlist filters cluster extras.
- FP #3 (Seerr user): allowlist filters cluster extras.

ADD actions ARE expected (test fixtures use v0.2.0 cluster state; new Categories
resources like series-emilie/films-zoe don't yet exist in fixtures).
PRUNE-SKIP actions are healthy (prune=false default).

If this test fails, Phase 12 cannot close (D-17 — SC#3 + SC#5 both required for
VERIFICATION PASSED).
"""
</docstring>
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task C.1: Delete 8 manual-path tests; rename test_sweep_categories_derived_path → test_sweep; rename 8 `*_wiring_empty_manual` tests</name>
  <files>
    tools/arrconf/tests/test_sonarr_categories.py,
    tools/arrconf/tests/test_radarr_categories.py,
    tools/arrconf/tests/test_qbittorrent_categories.py,
    tools/arrconf/tests/test_jellyfin_categories.py,
    tools/arrconf/tests/test_seerr_animetags.py,
    tools/arrconf/tests/test_phase10_idempotence_sweep.py
  </files>
  <read_first>
    - Each of the 6 test files in full (the line numbers above are from current main; verify with `grep -n "^def test_" <file>` before editing — the executor must not delete the wrong test by relying on stale line numbers)
    - tools/arrconf/arrconf/generators/categories.py (the generator surface — referenced by every test_sweep assertion)
  </read_first>
  <action>
    Apply the changes per the EXACT lists in `<interfaces>`:

    **(1) Delete 8 test functions:**
    For each file in `<interfaces>` section 1-6, locate the named test function via `grep -n "^def <name>" <file>` and delete the entire function body including its docstring + any decorators directly above it. After deleting, ensure no orphan imports remain (e.g. if the deleted test was the sole user of `merge_with_manual`, remove the import — but Plan A already removed all `merge_with_manual` imports source-side, so test imports may already be broken; just remove `from arrconf.reconcilers._shared import merge_with_manual` lines from any test file that has them).

    The 8 functions to delete (verified against current state):
    | File | Function name |
    |---|---|
    | test_sonarr_categories.py | test_sonarr_per_resource_override_tags_only |
    | test_sonarr_categories.py | test_sonarr_per_resource_override_rpm_only |
    | test_radarr_categories.py | test_radarr_per_resource_override_tags_only |
    | test_qbittorrent_categories.py | test_manual_override_wins |
    | test_jellyfin_categories.py | test_jellyfin_manual_override_wins |
    | test_seerr_animetags.py | test_animetags_merge_manual_wins |
    | test_seerr_animetags.py | test_animetags_merge_empty_manual_uses_generated |
    | test_phase10_idempotence_sweep.py | test_sweep_manual_override_path |

    **(2) Rename `test_sweep_categories_derived_path` → `test_sweep` in `test_phase10_idempotence_sweep.py`:**
    Locate line 127, change the `def test_sweep_categories_derived_path(...)` line to `def test_sweep(...)`. Replace the docstring (currently lines ~128-142) with the docstring in the `<docstring>` block above. Keep the function body unchanged.

    **(3) Rename 8 `*_wiring_empty_manual` tests:**
    For each rename listed in `<interfaces>` D-09 section, replace the function name only. Body stays unchanged. (The test bodies already exercise the "empty manual" path — that is now the ONLY path, so the name simplification is purely cosmetic.)

    **(4) Remove the `_empty_fp_affected_sections` helper from `test_phase10_idempotence_sweep.py` IF it is no longer called:**
    The helper (defined around line ~80-125 in current state) is invoked by `test_sweep_categories_derived_path` to empty out the 5 FP-affected manual sections. After Plan C, since Plan B has already deleted the `items` fields from the pydantic models, `production_cfg` no longer carries flat manual entries — the YAML loaded by `production_cfg` IS already the Categories-only shape. The helper becomes dead code. Verify with `grep -c "_empty_fp_affected_sections" tools/arrconf/tests/test_phase10_idempotence_sweep.py` — if the only reference is the def itself + a previous body use inside the now-renamed `test_sweep`, delete BOTH the helper definition AND the call from `test_sweep`. The new `test_sweep` body should call `dry_run_all_apps(production_cfg)` twice directly without the empty-helper wrapping.

    **(5) Verify no test references `merge_decision` event (deferred ideas #5):**
    Run `grep -rn "merge_decision" tools/arrconf/tests/` — must return zero results. If any reference exists, delete the assertion (it's targeting a now-extinct structlog event).
  </action>
  <verify>
    <automated>
      cd /data/projets/perso/arr-stack && \
      ! grep -rn "test_sonarr_per_resource_override_tags_only\|test_sonarr_per_resource_override_rpm_only\|test_radarr_per_resource_override_tags_only\|test_manual_override_wins\|test_jellyfin_manual_override_wins\|test_animetags_merge_manual_wins\|test_animetags_merge_empty_manual_uses_generated\|test_sweep_manual_override_path\|test_sweep_categories_derived_path" tools/arrconf/tests/ ; \
      grep -q "^def test_sweep(" tools/arrconf/tests/test_phase10_idempotence_sweep.py ; \
      ! grep -rn "_wiring_empty_manual" tools/arrconf/tests/ ; \
      grep -q "^def test_sonarr_tags_wiring(" tools/arrconf/tests/test_sonarr_categories.py ; \
      grep -q "^def test_radarr_tags_wiring(" tools/arrconf/tests/test_radarr_categories.py ; \
      grep -q "^def test_jellyfin_libraries_wiring(" tools/arrconf/tests/test_jellyfin_categories.py ; \
      ! grep -rn "merge_decision" tools/arrconf/tests/ ; \
      ! grep -rn "merge_with_manual" tools/arrconf/tests/ ; \
      cd tools/arrconf && uv run pytest tests/ --tb=short -x && echo "PYTEST GREEN" ; \
      uv run ruff format --check . && uv run ruff check . && uv run mypy . && echo "TRIADE OK"
    </automated>
  </verify>
  <acceptance_criteria>
    - `grep -rn "test_sonarr_per_resource_override_tags_only" tools/arrconf/tests/` returns 0 matches
    - `grep -rn "test_sonarr_per_resource_override_rpm_only" tools/arrconf/tests/` returns 0 matches
    - `grep -rn "test_radarr_per_resource_override_tags_only" tools/arrconf/tests/` returns 0 matches
    - `grep -rn "test_manual_override_wins" tools/arrconf/tests/` returns 0 matches
    - `grep -rn "test_jellyfin_manual_override_wins" tools/arrconf/tests/` returns 0 matches
    - `grep -rn "test_animetags_merge_manual_wins\|test_animetags_merge_empty_manual_uses_generated" tools/arrconf/tests/` returns 0 matches
    - `grep -rn "test_sweep_manual_override_path\|test_sweep_categories_derived_path" tools/arrconf/tests/` returns 0 matches
    - `grep -c "^def test_sweep(" tools/arrconf/tests/test_phase10_idempotence_sweep.py` returns 1
    - `grep -rn "_wiring_empty_manual" tools/arrconf/tests/` returns 0 matches
    - `grep -rn "merge_decision" tools/arrconf/tests/` returns 0 matches
    - `grep -rn "merge_with_manual" tools/arrconf/tests/` returns 0 matches
    - `grep -q "SC#3 dispositive" tools/arrconf/tests/test_phase10_idempotence_sweep.py` exits 0 (new docstring landed)
    - `cd tools/arrconf && uv run pytest tests/ --tb=short -x` exits 0 (full pytest WITHOUT `-k` filter)
    - `cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy .` exits 0
  </acceptance_criteria>
  <done>8 manual-path tests deleted; 1 sweep test renamed with new docstring; 8 wiring tests renamed; no orphan references to `merge_with_manual` / `merge_decision`; full pytest green without filter; Triade Python green.</done>
</task>

<task type="auto">
  <name>Task C.2: Audit conftest.py fixtures, delete unreferenced ones</name>
  <files>tools/arrconf/tests/conftest.py</files>
  <read_first>
    - tools/arrconf/tests/conftest.py (full file — 314 lines, 27 fixtures listed earlier)
    - Run a grep audit BEFORE deleting anything (see action)
  </read_first>
  <action>
    Audit each fixture in `conftest.py` per D-10. For each fixture name (the names following `@pytest.fixture` + `def`), run:

    ```bash
    grep -rn "<fixture-name>" tools/arrconf/tests/ | grep -v conftest.py
    ```

    If the grep returns ZERO matches (no test consumes the fixture), delete the fixture function block. If it returns 1+ matches, the fixture is live — keep it.

    **Important caveats:**
    - `configure_structlog_capture` (line 22, autouse=True) — DO NOT delete. It's the structlog test-capture wiring used implicitly by every test that uses `caplog`. Check its decorator — if `@pytest.fixture(autouse=True)` is present, keep regardless.
    - Some fixtures are pulled in by name only at parametrize time; the grep above catches that.
    - `production_cfg` is NOT in conftest.py (defined inline in test_phase10_idempotence_sweep.py line 86) — do not look for it here.

    Build the audit table mechanically. Delete only fixtures where the grep returns 0 hits OUTSIDE conftest.py. Examples likely to be unreferenced after Plan A+B+C1 land:
    - Any fixture referenced ONLY by the deleted manual-path tests (e.g. fixtures that mocked the "manual section non-empty" cluster state)

    If unsure for a given fixture, KEEP IT — the bias is "delete confidently or skip". Better to leave a live fixture in place than break a downstream test.

    After deletions, run the Triade Python triad to confirm no orphan imports remain.
  </action>
  <verify>
    <automated>
      cd /data/projets/perso/arr-stack && \
      cd tools/arrconf && uv run pytest tests/ --tb=short -x && echo "PYTEST GREEN" ; \
      uv run ruff format --check . && uv run ruff check . && uv run mypy . && echo "TRIADE OK" ; \
      uv run python -c "import tests.conftest; print('IMPORT OK')"
    </automated>
  </verify>
  <acceptance_criteria>
    - `cd tools/arrconf && uv run pytest tests/ --tb=short -x` exits 0 (full green pytest)
    - `cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy .` exits 0
    - `grep -q "@pytest.fixture(autouse=True)" tools/arrconf/tests/conftest.py` exits 0 (autouse fixture survived if present in original)
    - No fixture whose grep audit showed 1+ external references was deleted (mechanical rule: delete only if grep returns 0)
  </acceptance_criteria>
  <done>conftest.py is slimmer (or unchanged if all fixtures still referenced); pytest stays green; no orphan imports.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Test suite → CI | Tests are the safety net catching reconciler regressions before release. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-12C-01 | Tampering | test_sweep dispositive | mitigate | The renamed `test_sweep` is the SOLE SC#3 dispositive — its docstring explicitly states the failure-mode contract (no UPDATE/DELETE on round 2). D-17 makes this test load-bearing. |
| T-12C-02 | Information Disclosure | conftest fixture deletion | accept | Fixtures contain mocked API responses (no real secrets — they ship pre-sanitized per CLAUDE.md "Fixtures réalistes" rule). Deletion of unused fixtures reduces audit surface. |
| T-12C-03 | Denial of Service | pytest collection breakage | mitigate | Acceptance criteria require `pytest --tb=short -x` to exit 0 with no `-k` filter; collection errors fail this gate. |
| T-12C-04 | Tampering | renamed test function names | mitigate | All renames are pure cosmetic (function names) — bodies untouched. The CI run is the proof that behavior didn't drift. |
| T-12C-05 | Repudiation | git blame on deleted tests | accept | Deleted tests' history survives in git log; future investigations can `git log --all --diff-filter=D -- '*test_merge_with_manual*'` to recover removed assertions. |
</threat_model>

<verification>
- `cd tools/arrconf && uv run pytest tests/ --tb=short -x` exits 0 (full green, no `-k` filter)
- `grep -rn "merge_with_manual\|merge_decision\|_wiring_empty_manual" tools/arrconf/tests/` returns 0 matches
- `cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy .` exits 0
</verification>

<success_criteria>
- SC#3 (`test_sweep_manual_override_path` removed; `test_sweep_categories_derived_path` renamed to `test_sweep` as sole dispositive) — SATISFIED.
- D-06, D-07, D-08, D-09, D-10 all closed in this plan.
</success_criteria>

<output>
After completion, create `.planning/phases/12-categories-deprecation/12-C-test-cleanup-SUMMARY.md` documenting:
- The exact list of 8 deleted tests (file + function name)
- The exact list of 8 renamed tests (old → new)
- Confirmation that `test_sweep` carries the new SC#3-dispositive docstring (grep for `SC#3 dispositive`)
- Number of fixtures deleted from conftest.py (if any) and the grep-audit table showing why each was unreferenced
- Confirmation that `pytest tests/ -x` is green without `-k` filter
</output>
