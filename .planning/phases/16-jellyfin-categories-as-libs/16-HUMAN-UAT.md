# Phase 16 — Jellyfin Categories-as-libs — HUMAN UAT

**Phase:** 16
**Status:** in_progress (mandatory scenarios pending operator close-out)
**Date:** 2026-05-24

## Context

Phase 16 ships the refactor of `generate_jellyfin_libraries()` (10 libs, 1 per Category) and the extension of `_reconcile_libraries()` (CREATE + prune-gated DELETE). The code-side gates (Tasks 1-8) cover unit-test correctness and chart pin co-bump. The cutover itself — running `arrconf apply` against the live cluster after `helm upgrade` — requires the operator to validate live behavior because the cutover changes the visible Jellyfin lib structure that real users (the operator's family) interact with.

**Pre-merge gate (operator-driven, before opening the PR):**

- **G1 — Filesystem migration.** Operator must confirm the v0.2.0 → v0.3.0 filesystem migration runbook (CLAUDE.md § "Filesystem migration v0.2.0 → v0.3.0") has been executed, OR explicitly accept the watched-state loss for items currently under `/media/anime`, `/media/family`, `/media/films-anime`, `/media/films-family`. Without this confirmation, do not flip `prune: true`. The arrconf code change works either way, but the operator UX outcome depends on this.

## Scenarios

### Scenario 1 (MANDATORY for close) — Jellyfin web UI shows 10 libs post-cutover

**Given** the operator has merged the Phase 16 PR (chart-pin `0.7.0 → 0.8.0`) and ArgoCD has synced.
**Given** the operator has set `jellyfin.libraries.prune: true` in `charts/arr-stack/files/arrconf.yml` for the cutover PR (separate from the code PR or the same — operator choice).
**When** the operator opens https://jellyfin.tgu.ovh/ in a browser and logs in.
**Then** the Home page shows exactly **10 top-level libraries** with these names:
  1. `Séries`
  2. `Séries - Émilie`
  3. `Séries - Thomas`
  4. `Séries - Garçons`
  5. `Séries - Zoé`
  6. `Films`
  7. `Nouveaux Films`
  8. `Films - Enfants`
  9. `Films - Animation Enfants`
  10. `Films - Zoé`
**Then** clicking each lib shows the content from `/media/<name>` (e.g. `Séries - Zoé` shows the items from `/media/series-zoe`).
**Status:** Pending operator close-out

### Scenario 2 (MANDATORY for close) — Watched-state survives on ≥ 3 series at preserved paths

**Given** pre-cutover, the operator has noted 3 known-watched series in `/media/series` (paths that survive the reshape).
**When** the operator browses each of these 3 series in their new lib (`Séries`) post-cutover.
**Then** episodes that were watched pre-cutover still show as watched (Jellyfin UI dot indicator + "Resume from Xm" prompt).
**Then** if any series shows lost watched state, the operator notes it in this file under "Watched-state losses" below for follow-up.

**Watched-state losses (operator records here):**
- (none yet)

**Status:** Pending operator close-out

### Scenario 3 (MANDATORY for close) — Operator flips `prune: false` after UAT

**Given** Scenarios 1 and 2 have passed.
**When** the operator opens a follow-up PR setting `jellyfin.libraries.prune: false` in `charts/arr-stack/files/arrconf.yml`.
**When** the PR is merged and ArgoCD syncs.
**Then** the next `arrconf apply` cycle (visible via `kubectl logs -n selfhost <arrconf-cronjob-pod>`) emits 0 `library_pruned` and 0 `library_path_pruned` events (the section is prune-gated false, no DELETE writes).
**Then** any future user-added lib in the Jellyfin Dashboard (operator clicking "Add Media Library") survives the next reconcile (was the original v0.5.0 hardening goal — preserve operator's ad-hoc UI work).
**Status:** Pending operator close-out

### Scenario 4 (CARRY-FORWARD, NON-BLOCKING) — JellyCon LibreELEC top-level browse shows 10 libs

**Given** the operator has installed JellyCon on the LibreELEC salon mini-PC (planning is operator-driven, not part of arr-stack code).
**When** the operator opens JellyCon, signs in to the Jellyfin server, and navigates to the top-level browse view.
**Then** the same 10 libs from Scenario 1 appear, each browsable as a folder.
**Status:** CARRY-FORWARD (per D-16-JELLYCON-UAT-01 — non-blocking for Phase 16 close; operator may exercise post-merge as JellyCon install lands)

### Scenario 5 (OPTIONAL) — Legacy v0.2.0 paths zombie sweep

**Given** the operator either DID the filesystem migration before Phase 16 OR explicitly accepts the watched-state loss for unmigrated items.
**When** the operator runs `kubectl exec -n selfhost deployment/jellyfin -- ls -la /media/anime /media/family /media/films-anime /media/films-family`.
**Then** if any of these directories are non-empty, the operator decides per directory:
  - Migrate the content to a v0.3.0 bucket per CLAUDE.md "Filesystem migration" runbook, then re-trigger Jellyfin rescan.
  - Accept the items will disappear from Jellyfin (already happened post-cutover; files remain on NFS but no lib references them).
  - Optionally `rm -rf` the empty legacy dirs once vacated.
**Then** the operator may close this scenario as "done" (clean) or "deferred" (will revisit later).
**Status:** Optional — operator's discretion

## Close-out

Phase 16 is considered CLOSED when:
- Scenarios 1, 2, 3 are marked Passed by the operator (above)
- Scenario 4 is marked CARRY-FORWARD acceptable per D-16-JELLYCON-UAT-01
- Scenario 5 is marked Optional (acceptable as deferred)

Operator close-out command: edit this file to update statuses, then update `.planning/STATE.md` Phase 16 status to `complete`.
