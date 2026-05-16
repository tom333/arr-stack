---
phase: "06"
plan: "05"
subsystem: "arrconf/reconcilers"
tags: ["content-routing", "sonarr", "radarr", "genre-tagging", "idempotence", "D-06-RETAG-01"]
dependency_graph:
  requires: ["06-02"]  # ContentRoutingSection + ContentRoutingRule types
  provides: ["_reconcile_content_tags in sonarr + radarr (step 10)"]
  affects: ["06-06"]   # chart YAML wires the keyword rules
tech_stack:
  added: []
  patterns:
    - "Genre-keyword case-insensitive substring matching against item.genres[]"
    - "Idempotent tag filtering: skip items already carrying the rule's tag"
    - "Multi-rule fan-out: one PUT per rule, series can receive multiple tags"
key_files:
  created:
    - tools/arrconf/tests/test_content_tags.py
  modified:
    - tools/arrconf/arrconf/reconcilers/sonarr.py
    - tools/arrconf/arrconf/reconcilers/radarr.py
    - tools/arrconf/tests/test_reconcilers_sonarr.py
    - tools/arrconf/tests/test_reconcilers_radarr.py
decisions:
  - "content_tags runs as step 10 (LAST) after series_tags/movie_tags per D-05-ORDER-01 mirror"
  - "Radarr body uses movieIds + addImportExclusion:False (singular, Phase 5 divergence mirror)"
  - "No anime rule on Radarr (Pitfall 5: TMDB Animation catches Pixar/Disney)"
metrics:
  duration: "~30 minutes"
  completed: "2026-05-16T01:17:02Z"
  tasks_completed: 2
  files_modified: 5
---

# Phase 06 Plan 05: content_tags Sonarr + Radarr Reconcilers Summary

Genre-keyword-driven post-import retagger (_reconcile_content_tags) added to both Sonarr and Radarr reconcilers as step 10 — idempotent, T-05-CONTENT-safe, multi-rule capable.

## What Was Built

### Task 5.1: Implement _reconcile_content_tags + extend step-order regression tests

Added `_reconcile_content_tags(client, section, all_tags, dry_run)` to both:
- `tools/arrconf/arrconf/reconcilers/sonarr.py` — wired as step 10 after series_tags
- `tools/arrconf/arrconf/reconcilers/radarr.py` — wired as step 10 after movie_tags

Matching algorithm:
- For each rule in `section.rules`: resolve `rule.tag` → integer ID via `all_tags` (ReconcileError if missing)
- GET /series (or /movie); filter by case-insensitive substring of genre keywords
- Idempotent skip: items already carrying the rule's tag are excluded from editor PUT body
- PUT to /series/editor (or /movie/editor) with `applyTags="add"`, `moveFiles=False`, `deleteFiles=False`
- Radarr-specific: `movieIds` (not `seriesIds`) + `addImportExclusion=False` (not `addImportListExclusion`)

Both step-order regression tests (`test_reconcile_order` / `test_reconcile_order_radarr`) were extended to include `"content_tags"` as the final canonical step.

LOC delta: ~90 LOC added to sonarr.py, ~95 LOC added to radarr.py.

### Task 5.2: Create test_content_tags.py

Created `tools/arrconf/tests/test_content_tags.py` with 21 respx tests:

**Sonarr tests (11):**
1. `test_sonarr_family_match_tags_series_with_family_genre` — family keyword match → editor PUT
2. `test_sonarr_anime_match_tags_series_with_anime_genre` — anime keyword match
3. `test_sonarr_no_genre_match_skips` — no match → 0 PUTs
4. `test_sonarr_already_tagged_is_idempotent_noop` — already tagged → 0 PUTs (idempotence)
5. `test_sonarr_multi_tag_family_plus_anime_coexist` — genres=[Family,Anime] → 2 PUTs
6. `test_sonarr_case_insensitive_genre_match` — lowercase genre matches
7. `test_sonarr_animation_does_not_match_family` — Pitfall 5: 'Animation' NOT in family
8. `test_content_routing_disabled_skips` — enable=False → no GET
9. `test_unknown_rule_tag_raises_ReconcileError` — missing tag → ReconcileError
10. `test_sonarr_dry_run_skips_put` — dry_run=True → no PUT
11. `test_sonarr_enabled_with_no_rules_is_noop` — enable=True, rules=[] → no GET

**Radarr tests (9):**
1. `test_radarr_family_match_tags_movie_with_family_genre` — movieIds + addImportExclusion
2. `test_radarr_no_anime_rule_by_convention` — RadarrInstance default has empty rules
3. `test_radarr_movie_editor_body_has_addImportExclusion` — schema divergence regression
4. `test_radarr_already_tagged_movie_is_noop` — idempotence
5. `test_radarr_no_genre_match_noop` — no match → 0 PUTs
6. `test_radarr_content_routing_disabled_skips` — enable=False → no GET
7. `test_radarr_enabled_with_no_rules_is_noop` — enable=True, rules=[] → no GET
8. `test_radarr_unknown_rule_tag_raises_ReconcileError` — missing tag → ReconcileError
9. `test_radarr_dry_run_skips_put` — dry_run=True → no PUT

**Static assertions (1):**
- `test_sonarr_no_anime_rule_default_empty` — SonarrInstance default has empty content_routing

## Coverage Results

- `_reconcile_content_tags` in sonarr.py (lines 367-456): **100% coverage**
- `_reconcile_content_tags` in radarr.py (lines 353-452): **100% coverage**
- Total tests in test_content_tags.py: **21 passed**
- Full test suite: **201 passed** (no regressions)

## Step-Order Regression Tests

`test_reconcile_order` (sonarr) and `test_reconcile_order_radarr` were SUCCESSFULLY extended to assert `"content_tags"` as step 10 in the canonical_order list. Both pass.

## Deviations from Plan

None. The plan was executed exactly as written.

- ContentRoutingSection imported correctly in both reconcilers
- Pitfall 5 enforced: 'Animation' keyword NOT used in family rules (test asserts this)
- Radarr convention: NO anime rule by default (test asserts `content_routing.rules == []`)
- applyTags='add' used in all editor PUT bodies (T-05-CONTENT preserved)

## Self-Check

## Self-Check: PASSED

- FOUND: tools/arrconf/arrconf/reconcilers/sonarr.py
- FOUND: tools/arrconf/arrconf/reconcilers/radarr.py
- FOUND: tools/arrconf/tests/test_content_tags.py
- FOUND: commit 67c6c18 (Task 5.1 — reconciler implementation)
- FOUND: commit 7f43e12 (Task 5.2 — test file)
- 21 tests pass in test_content_tags.py
- 201 total tests pass (no regressions)
- ruff + mypy clean on all modified files
