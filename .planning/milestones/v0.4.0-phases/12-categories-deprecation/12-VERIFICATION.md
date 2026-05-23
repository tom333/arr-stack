---
phase: 12-categories-deprecation
type: VERIFICATION
status: PASSED
verified_at: 2026-05-22
verifier: orchestrator + operator (Thomas Guyader)
---

# Phase 12 — Verification report

## Phase goal recap

Retire the v0.2.0 transition layer in arrconf: delete `merge_with_manual()`, remove the 11 flat `*.items` blocks from `arrconf.yml`, prune the manual-path sweep tests. The Categories generators in `arrconf/generators/categories.py` become the sole source for the 11 generator-derived resources.

## Success criteria

### SC#1 — `merge_with_manual()` removed ✅

`tools/arrconf/arrconf/reconcilers/_shared.py` no longer defines `merge_with_manual`. All 22 callsites in `__main__.py` and the 5 reconcilers were updated to consume `*Derived` dataclasses directly (Plan A, commits `5dd19a5` + `c7f95f1`). The dedicated unit-test file `tests/test_merge_with_manual.py` was deleted in the same commit.

### SC#2 — Flat YAML sections deleted ✅

11 paths confirmed absent from `charts/arr-stack/files/arrconf.yml` (Plan B, commits `2fbfa62` WIP + `827e5cd` completion):

```
sonarr.main.tags.items
sonarr.main.root_folders.items
sonarr.main.download_clients.items
sonarr.main.remote_path_mappings.items
radarr.main.tags.items
radarr.main.root_folders.items
radarr.main.download_clients.items
radarr.main.remote_path_mappings.items
qbittorrent.main.categories.items
seerr.main.sonarr_service.animeTags
jellyfin.main.libraries.items
```

Pydantic `extra="forbid"` enforces this — `tests/test_config_validation.py::test_load_config_rejects_legacy_items_field` exercises the failure path with `type='extra_forbidden'`.

`schemas/arrconf-schema.json` regenerated; the committed schema matches a fresh `arrconf schema-gen` output byte-for-byte (`test_schema_committed_matches_regen` PASSES).

### SC#3 — Categories-derived sweep is the sole SC#3 dispositive ✅

`tools/arrconf/tests/test_phase10_idempotence_sweep.py` no longer contains `test_sweep_manual_override_path` (deleted by Plan C, commit `e875e2b`). The surviving test is `test_sweep` (renamed from `test_sweep_categories_derived_path`), elevated to SC#3-dispositive status. CI: PASSED (371 tests green).

### SC#4 — CLAUDE.md deprecation section present ✅

`## v0.3.0 → v0.4.0 deprecation` added at H2 between `### Accumulated-bumps escape hatch` and `## Conventions Helm — umbrella chart` (Plan D Task D.1, commit `a786182`). Contains:

- The 4 D-11 contents (Pourquoi, Sections supprimées, Erreur attendue, Fix one-shot).
- The verbatim D-13 ValidationError block (no template placeholder leakage).
- Cross-reference to `test_load_config_rejects_legacy_items_field`.

### SC#5 — Live-cluster dispositive diff ✅

See `12-HUMAN-UAT.md` for the full scenario breakdown. Summary:

- Pre-merge snapshot `snapshots/before-phase-12-2026-05-22/` captured against the v0.3.0 cluster (image `:0.6.7`) from a worktree pinned to `b371ace` (last pre-Plan-A commit). 85 files, redaction audit clean. Commit `e99334d`.
- Post-merge snapshot `snapshots/after-phase-12-2026-05-22/` captured against the v0.4.0 cluster (image `:0.7.0`) from main HEAD. 85 files, redaction audit clean. Commit `e1edff7`.
- **JSON diff:** 9 files differ, ALL runtime telemetry (uptime, scheduled-task timestamps, plugin update-check timestamps, bandwidth counters). **ZERO config-state divergence** — no `tag.json`, `downloadclient.json`, `rootfolder.json`, `category.json`, `library_virtualfolders.json` differ.
- **Cross-version dry-run log diff:** v030 has 11 `merge_decision` events (proving v0.3.0 code path was alive); v040 has 0 (proving `merge_with_manual` deleted). The 70-line growth in v040 is the categories-derived ADD plan_actions becoming visible — expected.
- **Transitional sonarr/radarr `app_failed`:** the cluster still has v0.2.0 tags. The next real CronJob apply will create the categories-derived tags first; step 6 will then resolve cleanly. NOT a Phase 12 regression.

## Triad + tests

- `cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy .` — green; 43 mypy errors (all pre-existing untyped-test baseline, ≤ Plan A's 47).
- `cd tools/arrconf && uv run pytest -q` — **371 passed, 0 failed.**

## Image + chart release

- `ghcr.io/tom333/arr-stack-arrconf:0.7.0` published (auto-tag chain triggered by Phase 12 PR merge).
- `charts/arr-stack/values.yaml#arrconf.image.tag = "0.7.0"` (co-bumped by Plan A per CLAUDE.md "Release pin co-bump pattern").
- ArgoCD has pulled `:0.7.0` into the `arrconf` CronJob (confirmed via `kubectl get cronjob arrconf -o jsonpath='{.spec.jobTemplate.spec.template.spec.containers[0].image}'`).

## Outcome

**Phase 12 VERIFICATION: PASSED.** All 5 success criteria satisfied. D-17 contract (SC#3 + SC#5 both required) holds.

## Follow-ups for next phase

1. **First real apply on `:0.7.0`** — wait for the next CronJob run (or manually trigger it via `kubectl create job --from=cronjob/arrconf arrconf-manual-`). This will create the 5+5 categories-derived tags + 5+5 RFs + 5+5 DCs + 5+5 RPMs + 10 qBit categories + 8 jellyfin library_paths. After this, a follow-up dry-run will be drift-free.

2. **Three-test workflow papercut (PR #17):** `chart-lint.yml` has a hardcoded `app-template-5.0.0.tgz` filename in the multi-alias vendor step. Renovate's app-template 5.0.1 bump can't merge until this is fixed (`app-template-*.tgz` glob). Low-priority — does not affect Phase 12 outcome.

3. **Tag spillover from Renovate merges:** `v0.8.0` and `v0.8.1` were created as side-effects of merging the cleanuparr and jellyfin patch bumps after Phase 12. Image content is identical to `v0.7.0`. my-kluster Renovate may propose bumping to `v0.8.1` — operator may accept (no functional change) or pin to `v0.7.0`.

4. **Python 3.14 PR (#21)** still open. Major Python release; needs operator changelog review per CLAUDE.md guidance.
