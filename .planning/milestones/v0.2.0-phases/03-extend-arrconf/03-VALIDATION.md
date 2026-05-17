---
phase: "03"
slug: extend-arrconf
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-11
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `tools/arrconf/pyproject.toml` |
| **Quick run command** | `cd tools/arrconf && pytest tests/ -q` |
| **Full suite command** | `cd tools/arrconf && ruff check && mypy . && pytest tests/ -v --cov=arrconf` |
| **Estimated runtime** | ~5–10 seconds (68 tests baseline) |

---

## Sampling Rate

- **After every task commit:** Run `cd tools/arrconf && pytest tests/ -q`
- **After every plan wave:** Run `cd tools/arrconf && ruff check && mypy . && pytest tests/ -v --cov=arrconf`
- **Before `/gsd-verify-work`:** Full suite must be green; JSON Schema must match generated output
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|--------|
| WR-01 fix (differ.py) | 01 | 1 | REQ-configarr-coexistence | — | apiKey+token fields omitted from PUT body when empty | unit | `pytest tests/test_differ.py -q` | ⬜ pending |
| ScopeViolationError Radarr | 01 | 1 | REQ-configarr-coexistence | — | quality_profiles rejected pre-network | unit | `pytest tests/test_reconcilers_radarr.py -q` | ⬜ pending |
| Sonarr indexer reconcile | 02 | 1 | REQ-app-coverage | — | credential apiKey field omitted on empty, pass-through on rotation | unit | `pytest tests/test_reconcilers_sonarr.py -k indexer -q` | ⬜ pending |
| Sonarr notification reconcile | 02 | 1 | REQ-app-coverage | — | credential fields omitted, no-op on unchanged | unit | `pytest tests/test_reconcilers_sonarr.py -k notification -q` | ⬜ pending |
| Sonarr root_folder reconcile | 02 | 1 | REQ-app-coverage | — | match by path, DELETE+ADD on path change | unit | `pytest tests/test_reconcilers_sonarr.py -k root_folder -q` | ⬜ pending |
| Sonarr host_config (opt-in) | 02 | 1 | REQ-app-coverage | — | skip if enable:false; apiKey excluded from PUT | unit | `pytest tests/test_reconcilers_sonarr.py -k host_config -q` | ⬜ pending |
| Radarr reconciler | 03 | 2 | REQ-app-coverage | — | full parity with Sonarr; forceSave inherited | unit | `pytest tests/test_reconcilers_radarr.py -q` | ⬜ pending |
| Prowlarr app sync | 04 | 2 | REQ-app-coverage | — | apiKey field omitted via merge_fields_for_put after WR-01 fix | unit | `pytest tests/test_reconcilers_prowlarr.py -q` | ⬜ pending |
| config.py expansion | 05 | 1 | REQ-app-coverage | — | RootConfig validates radarr/prowlarr blocks | unit | `pytest tests/test_config.py -q` | ⬜ pending |
| JSON Schema regeneration | last | last | REQ-app-coverage | — | schema-gen output matches committed schema | unit | `cd tools/arrconf && python -m arrconf schema-gen --check` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_reconcilers_radarr.py` — stubs for RadarrClient reconcile tests
- [ ] `tests/test_reconcilers_prowlarr.py` — stubs for ProwlarrClient app sync tests
- [ ] `tests/fixtures/radarr_*.json` — fixture files from live snapshots (indexer, notification, rootfolder, config_host, downloadclient)
- [ ] `tests/fixtures/prowlarr_applications.json` — fixture from live snapshot

*Existing `tests/test_reconcilers_sonarr.py`, `tests/test_differ.py`, `tests/conftest.py` infrastructure carries over unchanged.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Snapshot baseline before cluster write | ADR-6 | Requires live cluster access | Run `tools/snapshot/snapshot.sh --output snapshots/before-phase-3-$(date +%F)/` before first Radarr/Prowlarr apply |
| Prowlarr app sync round-trip | REQ-app-coverage | Requires Prowlarr + Sonarr running | `arrconf apply --apps prowlarr --dry-run`, then without dry-run; `arrconf apply --apps prowlarr --dry-run` again → must show 0 actions |
| Idempotence on all new resource types | REQ-app-coverage success criterion 2 | Requires cluster | `arrconf apply --dry-run` after first apply → all reconcilers must show 0 actions |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
