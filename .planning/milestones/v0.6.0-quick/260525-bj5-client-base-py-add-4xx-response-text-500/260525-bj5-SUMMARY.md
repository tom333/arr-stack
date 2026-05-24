---
phase: 260525-bj5
plan: 01
subsystem: arrconf
tags: [observability, structlog, OBS-01, co-bump, v0.6.0]
requires:
  - tools/arrconf/arrconf/client_base.py (pre-OBS-01, line 78/79 insertion point)
  - tools/arrconf/arrconf/exceptions.py (AuthError, NotFoundError, ServerError)
  - structlog.testing.capture_logs (established pattern, sonarr test:1126)
provides:
  - client_4xx structlog WARN event with body_excerpt = response.text[:500]
  - symmetric observability for 4xx body content (parity with 5xx text[:200])
  - chart pin 0.13.0 unblocking v0.6.0 image release
affects:
  - ArrApiClient subclasses (Sonarr/Radarr/Prowlarr/Seerr/Jellyfin) — gain
    automatic 4xx body logging at zero per-reconciler cost
tech-stack:
  added: []
  patterns:
    - structlog WARN one-shot before raise_for_status() (observational only)
    - co-bump per CLAUDE.md release-pin pattern (Python + chart pin in same commit)
key-files:
  created:
    - tools/arrconf/tests/test_client_base_4xx_logging.py
  modified:
    - tools/arrconf/arrconf/client_base.py
    - charts/arr-stack/values.yaml
decisions:
  - "No new typed exception: keep httpx.HTTPStatusError for non-401/404 4xx (smallest possible change; preserves contract for any caller that catches HTTPStatusError)"
  - "Minor bump 0.12.1 → 0.13.0 (not patch): new observability feature per v0.6.0 milestone target in STATE.md SC#3"
  - "Event name = client_4xx (symmetric to a hypothetical future client_5xx if ServerError is ever refactored; matches OBS-01 wording)"
metrics:
  duration: "~6 min"
  completed_date: "2026-05-25"
  files_changed: 3
  lines_added: 91
  lines_removed: 1
  commits: 1
  tests_added: 5
  tests_passing: 415 (1 skipped, pre-existing)
---

# Phase 260525-bj5 Plan 01: 4xx Body Logging in ArrApiClient Summary

One-liner: structlog WARN `client_4xx` emits `response.text[:500]` for any non-401/404 4xx in `ArrApiClient._request`, closing the v0.5.0 PathExistsValidator observability gap. Single atomic commit including chart pin co-bump `0.12.1 → 0.13.0`.

## Tasks Executed

| Task | Name                                                                                    | Type     | Status | Commit  |
| ---- | --------------------------------------------------------------------------------------- | -------- | ------ | ------- |
| 1    | Add client_4xx structured-log warning in ArrApiClient._request + respx test (5 tests)   | auto+tdd | DONE   | 9726d81 |
| 2    | Co-bump chart pin 0.12.1 → 0.13.0 + run Triade Python                                   | auto     | DONE   | 9726d81 |

Both tasks landed in a single atomic commit per CLAUDE.md "Release pin co-bump pattern" — non-negotiable for tools/arrconf/** changes (the chart-lint.yml auto-tag would otherwise produce a release-cycle race).

## Exact Diff

### `tools/arrconf/arrconf/client_base.py` (+9 / -0)

Insertion between line 78 (`NotFoundError` raise) and line 79 (5xx `ServerError` check):

```python
if 400 <= response.status_code < 500:
    log.warning(
        "client_4xx",
        client=self.name,
        method=method,
        path=path,
        status_code=response.status_code,
        body_excerpt=response.text[:500],
    )
```

The block is observational only — `raise_for_status()` still runs after, preserving `httpx.HTTPStatusError` propagation. 401 and 404 short-circuit BEFORE the block, so they keep their dedicated typed exceptions (`AuthError`, `NotFoundError`) and do NOT trigger `client_4xx`. The 5xx `ServerError` block on line 80 is unchanged (`text[:200]` is intentional for exception-message brevity; the new 4xx path uses `text[:500]` per OBS-01).

### `tools/arrconf/tests/test_client_base_4xx_logging.py` (new file, 82 lines, 5 tests)

| Test                                                       | Assertion                                                                |
| ---------------------------------------------------------- | ------------------------------------------------------------------------ |
| `test_4xx_emits_client_4xx_warning_with_body_excerpt`      | 400 + JSON body → 1 `client_4xx` event with body_excerpt=verbatim + HTTPStatusError raised |
| `test_4xx_body_excerpt_truncated_at_500_chars`             | 422 + 600-char body → body_excerpt length = 500, no truncation marker     |
| `test_401_short_circuits_to_autherror_no_4xx_log`          | 401 → AuthError raised, ZERO `client_4xx` events                          |
| `test_404_short_circuits_to_notfounderror_no_4xx_log`      | 404 → NotFoundError raised, ZERO `client_4xx` events                      |
| `test_5xx_path_unchanged_no_4xx_log`                       | 500 → ServerError raised (after tenacity retries), ZERO `client_4xx` events |

All 5 use `@respx.mock` + `structlog.testing.capture_logs()` (established pattern from `test_reconcilers_sonarr.py:1126`). No real API calls; no fixtures touched.

### `charts/arr-stack/values.yaml` (+1 / -1)

```diff
            # renovate: image=ghcr.io/tom333/arr-stack-arrconf
            repository: ghcr.io/tom333/arr-stack-arrconf
-           tag: "0.12.1"
+           tag: "0.13.0"
            pullPolicy: IfNotPresent
```

Renovate annotation preserved verbatim above `repository:`. Quote style preserved (`"0.13.0"` matches existing `"0.12.1"`).

## structlog Event Payload Shape

```python
{
    "event": "client_4xx",
    "log_level": "warning",       # structlog default for log.warning
    "client": "sonarr",            # = self.name (SonarrClient / RadarrClient / etc.)
    "method": "POST",              # HTTP verb passed to _request
    "path": "/rootfolder",         # endpoint path passed to _request
    "status_code": 400,            # int — 400, 402, 403, 405-499
    "body_excerpt": "...",         # response.text[:500] — verbatim, no truncation marker
}
```

This is symmetric to a hypothetical future `client_5xx` (not introduced now; `ServerError` keeps `text[:200]` in the exception message — different concern: brevity in exception text vs. observability in log event).

## Triade Python Output (final state, post-co-bump)

```
$ cd tools/arrconf
$ uv run ruff format --check .
93 files already formatted

$ uv run ruff check .
All checks passed!

$ uv run mypy arrconf
Success: no issues found in 55 source files

$ uv run pytest -q
======================= 415 passed, 1 skipped in 24.60s ========================
```

Coverage gate (`--cov-fail-under=70` on `arrconf.differ`, `arrconf.reconcilers.{sonarr,radarr,prowlarr}`) still passes — the new file adds tests against `client_base` (not currently in the coverage source set), so existing coverage figures are untouched.

## Deviations from Plan

None. The plan executed exactly as written:
- TDD RED produced 2 failing 4xx-emit tests + 3 already-passing regression tests (401/404/500 short-circuit was already correct).
- TDD GREEN added the 9-line block at the exact insertion point specified.
- Triade Python required one `ruff format` on the new test file (long respx call), then all 4 steps green.
- Co-bump line 451 `0.12.1` → `0.13.0`, Renovate annotation untouched.
- Single atomic commit `9726d81` includes all 3 files.

No deviation rules (1-4) triggered. No authentication gates. No checkpoints (plan was fully autonomous).

## Self-Check: PASSED

- `tools/arrconf/arrconf/client_base.py` — FOUND (9-line block at lines 79-87)
- `tools/arrconf/tests/test_client_base_4xx_logging.py` — FOUND (82 lines, 5 tests, all passing)
- `charts/arr-stack/values.yaml` line 451 — FOUND `tag: "0.13.0"`, Renovate annotation intact at line 449
- Commit `9726d81` — FOUND on `worktree-agent-ad26a5bc5614d6562` branch (`git log --oneline -1` confirms)

## Success Criteria Status

- [x] `_request` emits single `client_4xx` structlog warning for HTTP 400-499 (excl. 401/404)
- [x] `raise_for_status()` still raises `httpx.HTTPStatusError` AFTER the warning
- [x] 5xx ServerError path unchanged (line 80 with `text[:200]` intact)
- [x] 5 new tests pass
- [x] `charts/arr-stack/values.yaml` tag = `"0.13.0"`
- [x] Renovate annotation preserved verbatim
- [x] Triade Python exits 0 (ruff format --check + ruff check + mypy + pytest)
- [x] Coverage ≥ 70%
- [x] Single atomic commit

## Final Image Tag

`ghcr.io/tom333/arr-stack-arrconf:0.13.0` (chart pin set; CI auto-tag will create `v0.13.0` on push to `main`).
