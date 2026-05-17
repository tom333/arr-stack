---
phase: 05-reconciler-qbittorrent-split-tv-anime-family
plan: "04"
subsystem: arrconf/reconcilers
tags: [qbittorrent, reconciler, cookie-auth, categories, preferences, phase-5]
dependency_graph:
  requires: ["05-02", "05-03"]
  provides: ["QbittorrentClient", "reconcile_qbittorrent", "diff_qbittorrent"]
  affects: ["arrconf.__main__", "arrconf.diff_cmd"]
tech_stack:
  added: []
  patterns:
    - "sibling-class auth (QbittorrentClient is NOT a subclass of ArrApiClient)"
    - "dict-to-list normalization for qBit categories GET response"
    - "PRUNE_PROTECTED override for tag-free resources"
    - "json.dumps for boolean-typed setPreferences form body (Pitfall 4)"
key_files:
  created:
    - tools/arrconf/arrconf/reconcilers/qbittorrent.py
    - tools/arrconf/tests/test_reconcilers_qbittorrent.py
  modified:
    - tools/arrconf/arrconf/client_base.py
    - tools/arrconf/arrconf/diff_cmd.py
    - tools/arrconf/pyproject.toml
decisions:
  - "QbittorrentClient is a sibling class (NOT subclass) of ArrApiClient — auth lifecycle diverges too much (login POST + cookie vs static X-Api-Key)"
  - "PRUNE_PROTECTED override: differ.reconcile() emits PRUNE_PROTECTED when managed_tag_id=None + prune=True. For qBit categories (no managed-tag concept, R-05), the reconciler overrides PRUNE_PROTECTED to execute removeCategories when prune=True (operator opt-in trust boundary)"
  - "N802 per-file-ignore added to tests/** in pyproject.toml — test names mirror API names (AuthError, savePath) per plan acceptance criteria"
metrics:
  duration: "~35 minutes"
  completed: "2026-05-14"
  tasks: 3
  files: 5
---

# Phase 05 Plan 04: qBittorrent Client + Reconciler Summary

**One-liner:** QbittorrentClient (POST /auth/login cookie auth + Referer header) + reconcile_qbittorrent (categories dict normalization + preferences allowlist diff) with 12 respx tests covering all threat mitigations.

## What Was Built

### Task 4.1 — QbittorrentClient class (client_base.py)

Full cookie-auth client appended to `client_base.py` as a sibling class to `ArrApiClient` (NOT a subclass — Q1 resolution). Key properties:

- Constructor performs `POST /api/v2/auth/login` with form-encoded credentials + `Referer: <base_url>` header (Pitfall 1 / T-05-AUTH).
- Extracts `SID` cookie; raises `AuthError` on HTTP != 200, body != `"Ok."`, or missing SID.
- Builds long-lived `httpx.Client` with `cookies={"SID": sid}` + `Referer` header.
- `get()`: returns JSON or text based on content-type; raises `AuthError` on 403.
- `post_form()`: form-encoded POST; raises `AuthError` on 403, `ApiClientError` on 409.
- Context manager (`__enter__`/`__exit__`) — mirrors `ArrApiClient` pattern.
- Password NEVER appears in log lines or exception messages (T-05-AUTH mitigation).

### Task 4.2 — reconcile_qbittorrent + diff_qbittorrent

**New file `tools/arrconf/arrconf/reconcilers/qbittorrent.py`:**

- `_fetch_current_categories(client)`: GET `/torrents/categories` → normalizes qBit's dict-keyed response to `list[Category]` via `model_validate`.
- `_reconcile_categories(client, items, prune, dry_run)`: Uses `differ.reconcile(match_key="name", managed_tag_id=None)`. Key deviation: handles `PRUNE_PROTECTED` actions explicitly — when `prune=True`, executes `removeCategories` (no managed-tag gate needed for qBit, R-05). When `prune=False`, logs `prune_skip` (R-04 mitigation).
- `_reconcile_preferences(client, section, dry_run)`: Opt-in (default disabled). GET `/app/preferences`, scalar-dict diff against the 4-key allowlist. Applies via `json.dumps(diffs)` — Pitfall 4 (JSON-typed booleans, not Python str).
- `reconcile_qbittorrent(client, instance, dry_run)`: Orchestrates categories → preferences. Returns `QbittorrentResult(plan=..., actions_taken=...)`. Plan populated even in dry-run (diff CLI gate pattern).

**Updated `diff_cmd.py`:** Replaced Plan 02 stub with real `diff_qbittorrent` — mirrors `diff_prowlarr` pattern (gates on `result.plan`, not `actions_taken`; returns 3 on drift).

### Task 4.3 — test_reconcilers_qbittorrent.py (12 tests)

All 12 mandatory tests from the plan acceptance criteria, all green:

| Test | Invariant |
|------|-----------|
| `test_login_with_referer_header` | Pitfall 1 — Referer header on login POST |
| `test_login_failure_raises_AuthError` | T-05-AUTH — password not in error message |
| `test_login_missing_sid_cookie_raises_AuthError` | T-05-AUTH — SID required |
| `test_add_new_category` | Pitfall 3 — explicit savePath in createCategory body |
| `test_create_six_categories_with_correct_savepaths` | SC#2 unit signal — 6 categories + D-05-PATHS-01 |
| `test_update_category_when_savePath_changes` | UPDATE path — editCategory, zero create/remove |
| `test_idempotent_no_op` | SC#5 unit signal — zero writes when in sync |
| `test_prune_false_keeps_unmanaged_categories` | R-04 — cleanuparr-unlinked survives |
| `test_prune_true_removes_unmanaged_categories` | Operator opt-in prune path |
| `test_preferences_skipped_when_disabled` | Opt-in default OFF — no GET /app/preferences |
| `test_preferences_diff_uses_json_boolean_not_quoted` | Pitfall 4 — JSON-typed booleans |
| `test_preferences_no_op_when_in_sync` | SC#5 preferences variant |

**Coverage on `arrconf.reconcilers.qbittorrent`:** 79% (gate: 70%). Overall suite: 82%, 155 tests passing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] PRUNE_PROTECTED override for tag-free resources**
- **Found during:** Task 4.3 — `test_prune_true_removes_unmanaged_categories` failed (expected 3 `removeCategories` calls, got 0).
- **Root cause:** `differ.reconcile()` emits `PRUNE_PROTECTED` (not `DELETE`) when `managed_tag_id=None` + `prune=True` — the managed-tag guard fires unconditionally. For qBit categories (no managed-tag concept, R-05), this means `prune=True` silently never deletes.
- **Fix:** Added explicit handling for `Action.PRUNE_PROTECTED` in `_reconcile_categories`: when `prune=True`, execute `removeCategories` directly (the operator's explicit opt-in is the trust boundary, no tag check needed for qBit). When `prune=False`, emit `prune_skip` (same as `PRUNE_SKIP`). Documented in code comment.
- **Files modified:** `tools/arrconf/arrconf/reconcilers/qbittorrent.py`
- **Commit:** `29ae131`

**2. [Rule 2 - Missing functionality] ruff N802 per-file-ignore for tests/**
- **Found during:** Task 4.3 — ruff N802 blocked on test function names with camelCase (e.g. `test_login_failure_raises_AuthError`, `test_update_category_when_savePath_changes`) required by plan acceptance criteria.
- **Fix:** Added `N802` to `tests/**` per-file-ignores in `pyproject.toml` (N802 = function name should be lowercase; test names mirror API names per plan spec).
- **Files modified:** `tools/arrconf/pyproject.toml`
- **Commit:** `29ae131`

**3. [Rule 3 - Blocking] Removed obsolete mypy override from pyproject.toml**
- **Found during:** Task 4.1 — Plan 02 added `[[tool.mypy.overrides]] module = ["arrconf.reconcilers.qbittorrent"] ignore_missing_imports = true` anticipating Plan 04. Now that the module exists, the override is obsolete and `warn_unused_ignores = true` would flag it.
- **Fix:** Removed the override. mypy passes cleanly on all 39 source files.
- **Commit:** `29ae131`

## ADR-5 Frontière Verification

```
grep -E '/api/v3/(qualityprofile|customformat|qualitydefinition|mediamanagement)' \
  tools/arrconf/arrconf/reconcilers/qbittorrent.py | wc -l
→ 0
```

The qBittorrent reconciler contains zero references to configarr-owned quality endpoints. ADR-5 frontière maintained.

## Class Hierarchy Confirmation

```
ArrApiClient (base)
  └─ _ArrV3Client (forceSave PUT)
       ├─ SonarrClient
       ├─ RadarrClient
       └─ ProwlarrClient
QbittorrentClient (sibling — NOT subclass of ArrApiClient)
```

Q1 resolution confirmed: `QbittorrentClient` is a sibling class. The auth lifecycle (runtime POST login → SID cookie) diverges too much from the static X-Api-Key pattern to justify subclassing.

## Known Stubs

None — all new code is fully implemented and wired. The Plan 02 stubs (`QbittorrentClient(raise NotImplementedError)` and `diff_qbittorrent(raise NotImplementedError)`) are replaced with real implementations.

## Threat Flags

No new network endpoints, auth paths, or schema changes beyond what the plan's threat model covers.

## Self-Check: PASSED

- `tools/arrconf/arrconf/reconcilers/qbittorrent.py` — exists, 12 functions verified
- `tools/arrconf/tests/test_reconcilers_qbittorrent.py` — exists, 12 tests verified
- `tools/arrconf/arrconf/client_base.py` — QbittorrentClient class present
- `tools/arrconf/arrconf/diff_cmd.py` — diff_qbittorrent implemented (not stub)
- Commits verified: `78147ea`, `1263336`, `29ae131`
- Full CI gate: ruff + ruff format + mypy arrconf + pytest (155 tests) — all green
