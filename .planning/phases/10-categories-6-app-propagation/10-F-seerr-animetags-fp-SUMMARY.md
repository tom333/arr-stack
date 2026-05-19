---
phase: 10-categories-6-app-propagation
plan: 10-F-seerr-animetags-fp
subsystem: arrconf
tags:
  - python
  - reconciler-wiring
  - seerr
  - animetags
  - fp-fix
  - chart-pin-cobump
dependency_graph:
  requires:
    - 10-A-generators-categories (generate_anime_tag_labels)
    - 10-B-merge-with-manual (merge_with_manual)
    - 10-D-sonarr-wiring (reconcile_sonarr runs before animeTags resolution)
  provides:
    - SEERR_USER_MANAGED_FIELDS allowlist (FP fix #3)
    - _resolve_seerr_anime_tag_ids helper in __main__.py
    - Seerr animeTags 4-step resolution chain (apply + diff branches)
  affects:
    - tools/arrconf/arrconf/reconcilers/seerr.py
    - tools/arrconf/arrconf/__main__.py
    - charts/arr-stack/values.yaml
tech_stack:
  added: []
  patterns:
    - B2 allowlist frozenset pattern (mirrors jellyfin.py SERVER_CONFIG_ALLOWLIST)
    - Post-reconcile tag resolution via second GET /api/v3/tag
    - Pitfall 5 consistency: same animeTags pre-merge in apply AND diff branches
key_files:
  created:
    - tools/arrconf/tests/test_seerr_animetags.py
    - .planning/phases/10-categories-6-app-propagation/deferred-items.md
  modified:
    - tools/arrconf/arrconf/reconcilers/seerr.py
    - tools/arrconf/arrconf/__main__.py
    - tools/arrconf/tests/test_idempotence_fp.py
    - charts/arr-stack/values.yaml
decisions:
  - SEERR_USER_MANAGED_FIELDS frozenset with 6 writable fields (displayName, permissions, movieQuotaDays, movieQuotaLimit, tvQuotaDays, tvQuotaLimit) mirrors jellyfin.py B2 allowlist pattern
  - kind==series filter applied INSIDE _resolve_seerr_anime_tag_ids (NOT in generate_anime_tag_labels) because Radarr animeTags does not exist on the Seerr API
  - animeTags resolution reconstructs SonarrClient for a second GET after reconcile_sonarr — cheap and idempotent per RESEARCH Pattern 5 Option A
  - Missing label warning (not error) to handle D-02 transition step where tags are created in same run
  - Chart-pin co-bump 0.6.2 → 0.6.3 bundled in same commit as animeTags + FP fix code (D-05)
metrics:
  duration: 45min
  completed_date: 2026-05-20
  tasks_completed: 3
  tasks_total: 3
  files_changed: 6
---

# Phase 10 Plan F: Seerr animeTags + FP Fix #3 Summary

**One-liner:** Seerr animeTags 4-step post-Sonarr resolution chain + FP fix #3 via SEERR_USER_MANAGED_FIELDS allowlist filtering spurious UPDATEs from server-side extras.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 10-F-01 | FP fix #3 — SEERR_USER_MANAGED_FIELDS + _reconcile_user filter | 3c10271 | seerr.py, test_idempotence_fp.py |
| 10-F-02 | animeTags 4-step resolution chain in __main__.py | f4f6560 | __main__.py, test_seerr_animetags.py |
| 10-F-03 | Chart-pin co-bump 0.6.2 → 0.6.3 | f4f6560 | charts/arr-stack/values.yaml |

*Tasks 10-F-02 and 10-F-03 are bundled in a single atomic commit per D-05 chart-pin co-bump rule.*

---

## What Was Built

### FP Fix #3 — SEERR_USER_MANAGED_FIELDS (Task 10-F-01)

Added `SEERR_USER_MANAGED_FIELDS: frozenset[str]` constant to `tools/arrconf/arrconf/reconcilers/seerr.py` with the 6 writable fields on `SeerrUser`. Modified `_reconcile_user` to build `cluster_filtered = {k: v for k, v in admin_current.items() if k in SEERR_USER_MANAGED_FIELDS}` BEFORE calling `_payloads_equivalent`, eliminating spurious UPDATE actions on every reconcile run.

Root cause: `SeerrUser` uses `extra="allow"`, so cluster GET responses carrying server-side fields (`requestCount`, `warnings`, `settings`, `avatar*`, timestamps) leaked through `admin_current` and were compared against `put_body` which only had the 6 managed fields. Every run saw "extra" keys in current that weren't in desired, triggering false inequality → spurious PUT.

Pattern: mirrors `jellyfin.py`'s `SERVER_CONFIG_ALLOWLIST` approach (B2 pattern from RESEARCH.md).

### animeTags 4-Step Resolution Chain (Task 10-F-02)

Added `_resolve_seerr_anime_tag_ids(root, sonarr_client, log)` helper to `tools/arrconf/arrconf/__main__.py`:

1. Calls `generate_anime_tag_labels(root)` to get ALL anime-profile category names
2. Filters to `kind == "series"` (Seerr.sonarr_service.animeTags is Sonarr-side routing only; Radarr has no animeTags field per RESEARCH §Pattern 5)
3. Issues `sonarr_client.get("/tag")` — a second GET to Sonarr post-reconcile (cheap, idempotent)
4. Maps labels → integer IDs; logs warning for unresolved labels (doesn't raise — D-02 transition step)

Wired in **apply** Seerr branch (after `reconcile_sonarr` completes) and in **diff** Seerr branch (Pitfall 5: same pre-merge shape for consistency between commands). A `merge_with_manual` call governs the final value: non-empty YAML `animeTags` wins; empty YAML activates Categories-derived resolved IDs.

### Chart-Pin Co-Bump (Task 10-F-03)

Bumped `charts/arr-stack/values.yaml` `arrconf.image.tag` from `"0.6.2"` to `"0.6.3"`. Renovate annotation `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` preserved.

---

## Test Coverage

| Test File | Tests Added | What They Prove |
|-----------|-------------|-----------------|
| `test_idempotence_fp.py` | +2 (test_seerr_user_managed_fields_constant, test_seerr_user_fp_fix_no_op_on_extras) | FP #3: cluster GET with extras returns no UPDATE when writable fields match |
| `test_seerr_animetags.py` | 6 new tests | 4-step chain happy path; no-anime-cats; missing-label warns; manual-wins; empty-manual-uses-generated |

Total new tests: **8**. All passing. Phase 9 no-regression preserved.

---

## D-06-Q10-01 Closure Note

The animeTags resolution chain is now testable end-to-end:
- The **automated half** is closed: `test_seerr_animetags.py` proves the chain populates `seerr_instance.sonarr_service.animeTags` with the correct Sonarr integer tag IDs.
- The **HUMAN-UAT half (SC#3 live-cluster)** remains open: a live TVDB-anime request submitted in the Seerr UI must route to the correct Sonarr anime-profile category (`series-zoe`). This requires post-merge ArgoCD sync + manual test.

**Human-UAT item added to 10-VALIDATION.md "Manual-Only Verifications" table** (see below).

---

## Operator Follow-Up Action

Production `charts/arr-stack/files/arrconf.yml` currently has `animeTags: [3]` (non-empty manual override at line 445). This means the Categories-derived resolution will be **skipped** (`merge_with_manual` returns `[3]` when manual is non-empty). To activate Categories-derived anime routing:

1. Edit `charts/arr-stack/files/arrconf.yml`, section `seerr.main.sonarr_service`:
   ```yaml
   animeTags: []   # or remove entirely — empty triggers Categories-derived resolution
   ```
2. Commit and push to trigger a new release tag.
3. After ArgoCD sync, the next arrconf CronJob run will resolve `series-zoe` Sonarr tag ID and populate `animeTags` in the Seerr settings/sonarr PUT body automatically.

This is a **content-side commit** separate from this plan's code changes, to be done by the operator when ready to switch to Categories-derived routing.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing feature] respx assert_all_called=False in test_animetags_resolution_no_anime_categories**
- **Found during:** Task 10-F-02 GREEN phase
- **Issue:** Test registers a GET /tag route to assert it was NOT called, but respx default `assert_all_called=True` failed the test because the registered route was never called
- **Fix:** Added `assert_all_called=False` to the respx.mock context for that specific test
- **Files modified:** tools/arrconf/tests/test_seerr_animetags.py

**2. [Rule 1 - Bug] generate_anime_tag_labels unused import + type annotation fix**
- **Found during:** Task 10-F-02 lint phase
- **Issue:** (a) `generate_anime_tag_labels` was imported but not used directly (helper had inline filter); (b) `int(match["id"])` with `list[dict[str, object]]` caused mypy error
- **Fix:** (a) Changed helper to explicitly call `generate_anime_tag_labels(root)` then filter `kind=="series"`, making the import used and documenting the two-step process; (b) Changed to `list[dict[str, Any]]` type annotation
- **Files modified:** tools/arrconf/arrconf/__main__.py

### Out-of-Scope Pre-Existing Issues (Deferred)

**1. test_merge_with_manual.py::test_log_event_manual_wins — test ordering sensitivity**
- **Status:** Pre-existing; fails in full suite, passes in isolation
- **Cause:** `configure_structlog_capture` fixture mutates global structlog state; structlog-using tests before it leave state in incompatible shape
- **Logged to:** `.planning/phases/10-categories-6-app-propagation/deferred-items.md`
- **Impact:** Non-blocking; does not affect production code paths

---

## SC#3 Verification Split

Per Plan 10-F executor_notes Warning #5:

- **AUTOMATED (this plan — CLOSED):** `animeTags: list[int]` is populated correctly in the Seerr settings/sonarr payload. Proven by `test_seerr_animetags.py` (6 tests, all green).
- **HUMAN-UAT (post-merge — OPEN):** Live TVDB-anime request submitted in Seerr UI must route to `series-zoe` Sonarr category. Requires post-merge ArgoCD sync + manual Seerr UI test. Listed in 10-VALIDATION.md Manual-Only Verifications table.

---

## Threat Flags

None. No new network endpoints, auth paths, or schema changes at trust boundaries introduced. The second `GET /api/v3/tag` call reuses the existing `SonarrClient` with the same auth token, on the existing Sonarr host.

---

## Known Stubs

None. All data paths are wired. The `animeTags: [3]` manual override in `arrconf.yml` is an intentional operator override (not a stub) — documented in the Operator Follow-Up section above.

---

## Self-Check

**Commits:**
- `git log --oneline | grep "3c10271"` → found: `feat(10-F): add SEERR_USER_MANAGED_FIELDS allowlist + FP fix #3...`
- `git log --oneline | grep "f4f6560"` → found: `feat(10-F): animeTags 4-step resolution chain in __main__.py + chart-pin 0.6.3`

**Files:**
- `tools/arrconf/arrconf/reconcilers/seerr.py` — contains `SEERR_USER_MANAGED_FIELDS` and `cluster_filtered`
- `tools/arrconf/arrconf/__main__.py` — contains `_resolve_seerr_anime_tag_ids`, `generate_anime_tag_labels`, 2× `_resolve_seerr_anime_tag_ids` call sites
- `tools/arrconf/tests/test_seerr_animetags.py` — 6 tests
- `tools/arrconf/tests/test_idempotence_fp.py` — 4 tests total (2 existing + 2 new)
- `charts/arr-stack/values.yaml` — `tag: "0.6.3"`

## Self-Check: PASSED

---

## Next Plan

**Plan 10-G** — `10-G-jellyfin-wiring-PLAN.md`: Wire Categories-derived Jellyfin libraries into `__main__.py` apply + diff branches. Mirrors the Sonarr/Radarr pattern with `generate_jellyfin_libraries(root)`.
