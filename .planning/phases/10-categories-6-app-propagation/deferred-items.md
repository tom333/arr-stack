---
phase: 10-categories-6-app-propagation
updated: 2026-05-20
---

# Deferred Items — Phase 10

## Out-of-scope pre-existing failures (do NOT fix in Phase 10)

### D-10-MERGE-LOG-FP — test_log_event_manual_wins ordering sensitivity

**Discovered:** Plan 10-F execution, Task 10-F-02
**File:** `tools/arrconf/tests/test_merge_with_manual.py::test_log_event_manual_wins`
**Status:** Pre-existing — fails when run after structlog-touching tests in full suite; passes in isolation
**Root cause:** `configure_structlog_capture` fixture in test_merge_with_manual.py calls `structlog.configure()` globally but prior tests that use structlog leave the global state in a different shape. The fixture's `cache_logger_on_first_use=False` doesn't fully prevent the state bleed when tests run in pytest's default collection order.
**Impact:** Non-blocking (test passes in isolation; does not affect any production code path)
**Suggested fix:** Add `structlog.reset_defaults()` at the start of `configure_structlog_capture`, or use `structlog.testing.capture_logs()` context manager instead of caplog-based approach.
**Deferred to:** Post-Phase-10 housekeeping (low priority, test-infra issue only)
