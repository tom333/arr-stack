---
phase: 12-categories-deprecation
plan: D
type: SUMMARY
status: partial
tasks_complete:
  - D.1
tasks_pending:
  - D.2
date: 2026-05-22
---

# Plan 12-D Summary (partial) — docs done, snapshot pending operator

## Task D.1 — CLAUDE.md deprecation section ✅

Added `## v0.3.0 → v0.4.0 deprecation` at H2 between `### Accumulated-bumps escape hatch` and `## Conventions Helm — umbrella chart`.

Content covers the 4 D-11 facts:

1. **Pourquoi ce changement** — `merge_with_manual` + flat `*.items` retired; generators in `arrconf/generators/categories.py` are the sole source.
2. **Sections supprimées** — verbatim list of the 11 YAML paths deleted from `arrconf.yml` (matches Plan B's edit).
3. **Erreur attendue** — the literal ValidationError block from `12-B-pydantic-yaml-schema-SUMMARY.md#Captured-D-13-ValidationError`. References the dispositive test `tools/arrconf/tests/test_config_validation.py::test_load_config_rejects_legacy_items_field`.
4. **Fix one-shot** — 5-step operator runbook (verify branch → diff local YAML → delete `items:` blocks → re-test dry-run → commit/push).

The `**État actuel**` line at the top of CLAUDE.md was also updated to reflect Phase 12 completion.

Commit: see git log for `docs(12-D): add v0.3.0 → v0.4.0 deprecation section to CLAUDE.md (D-11)`.

## Task D.2 — Pre-merge cluster snapshot ⏳ PENDING OPERATOR

This task is `type="checkpoint:human-action"` with `gate="blocking"`. It requires:

- kubectl port-forward to each app in the live cluster (sonarr, radarr, prowlarr, qbittorrent, seerr, jellyfin),
- `SONARR_API_KEY` / `RADARR_API_KEY` / `PROWLARR_API_KEY` / `JELLYFIN_API_KEY` / `SEERR_API_KEY` / `QBT_USER` / `QBT_PASS` exported in the operator's shell,
- A working tree (or `git stash` / `git worktree` isolation) representing the cluster's currently deployed code, so the captured `arrconf apply --dry-run` log reflects the v0.3.0 reconciler — NOT the v0.4.0 code that's already committed locally.

### Recommended runbook for the operator

The plan's escape hatch (a separate worktree pinned to a pre-Plan-A commit) is the cleanest path now that Plan A/B/C are merged on `main`:

```bash
cd /data/projets/perso/arr-stack
# Anchor commit: last commit before Plan A's first task lands.
PRE_A=$(git rev-list --max-parents=1 --reverse main | head -20 | tail -1)  # adjust as needed
git log --oneline ${PRE_A} -1   # confirm it predates "refactor(12-A)" commits

git worktree add /tmp/arr-stack-pre-12 ${PRE_A}
cd /tmp/arr-stack-pre-12/tools/arrconf

# Establish port-forwards in another shell:
#   kubectl -n selfhost port-forward svc/sonarr 8989:8989 &
#   kubectl -n selfhost port-forward svc/radarr 7878:7878 &
#   kubectl -n selfhost port-forward svc/prowlarr 9696:9696 &
#   kubectl -n selfhost port-forward svc/qbittorrent 8080:8080 &
#   kubectl -n selfhost port-forward svc/jellyfin 8096:8096 &
#   kubectl -n selfhost port-forward svc/seerr 5055:5055 &

# Export secrets in this shell (values from sealed-secret decrypts; never commit).
export SONARR_API_KEY=...
export RADARR_API_KEY=...
export PROWLARR_API_KEY=...
export JELLYFIN_API_KEY=...
export SEERR_API_KEY=...
export QBT_USER=...
export QBT_PASS=...

DATE=$(date +%F)
tools/snapshot/snapshot.sh --output snapshots/before-phase-12-${DATE}/

# Operator captures the dry-run plan output for SC#5 comparison.
uv run arrconf apply --dry-run --log-level INFO > snapshots/before-phase-12-${DATE}/dry-run-plan-actions-v030.log 2>&1

# Sanity: confirm no credentials leaked past snapshot.sh redaction.
grep -rniE "(api[-_]?key|password|passkey|token).*:.*[a-zA-Z0-9]{16,}" snapshots/before-phase-12-${DATE}/ || echo "REDACTION CLEAN"

# Bring the snapshot back to main and commit:
cp -r snapshots/before-phase-12-${DATE}/ /data/projets/perso/arr-stack/snapshots/
cd /data/projets/perso/arr-stack
git add snapshots/before-phase-12-${DATE}/
git commit -m "snapshot(12): capture pre-merge v0.3.0 cluster state (D-14, ADR-6)"

# Cleanup worktree:
git worktree remove --force /tmp/arr-stack-pre-12
```

The recorded `dry-run-plan-actions-v030.log` is consumed by Plan E's SC#5 diff against the post-merge `dry-run-plan-actions-v040.log`.

## SC#5 dispositive — what this snapshot anchors

Phase 12 requires both:
- **SC#3** — Plan C's `test_sweep` (in-CI dispositive) ✅ — verified by `cd tools/arrconf && uv run pytest tests/test_phase10_idempotence_sweep.py::test_sweep`.
- **SC#5** — live-cluster diff between pre-merge (this snapshot) and post-merge (Plan E's after-snapshot). The two logs must come from different code versions running against the cluster at different image states — that's what makes the diff a true v0.3.0-vs-v0.4.0 measurement, not a tautological same-code self-diff.

## Status

| Acceptance criterion | Status |
|---|---|
| `## v0.3.0 → v0.4.0 deprecation` section added | ✅ |
| 11 verbatim YAML paths cited | ✅ |
| D-13 ValidationError block (verbatim from Plan B SUMMARY) | ✅ |
| Cross-reference to `test_load_config_rejects_legacy_items_field` | ✅ |
| `merge_with_manual` mentioned in deprecation context | ✅ |
| `arrconf/generators/categories.py` mentioned | ✅ |
| `<PASTE-VERBATIM…>` placeholder replaced (no template leakage) | ✅ |
| `snapshots/before-phase-12-YYYY-MM-DD/` captured | ⏳ operator |
| Snapshot redaction sanity check | ⏳ operator |
| Snapshot committed to git | ⏳ operator |

## Handoff to Plan E

Plan E (Wave 4) is entirely operator-driven: post-PR merge → ArgoCD picks up image `:0.7.0` → operator captures after-snapshot from a post-merge working tree → diff against this baseline → 12-HUMAN-UAT.md and 12-VERIFICATION.md written. The orchestrator halts after this partial SUMMARY.
