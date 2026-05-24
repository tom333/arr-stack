---
gsd_state_version: 1.0
milestone: v0.5.0
milestone_name: Jellyfin Categories-as-libs + CI/UX hardening
status: Phase 18 shipped — c4ccc0d pushed to main, auto-tag v0.12.1 pending
last_updated: "2026-05-24T08:09:30.211Z"
last_activity: 2026-05-24 -- Phase 18 shipped (15 commits, chart pin 0.10.0 → 0.12.1)
progress:
  total_phases: 7
  completed_phases: 2
  total_plans: 3
  completed_plans: 2
  percent: 67
---

# Project State

## Project Reference

See: `.planning/PROJECT.md`

**Core value:** Aucune intervention UI nécessaire pour configurer Sonarr/Radarr/Prowlarr/qBittorrent/Seerr/Jellyfin après bootstrap — tout passe par PR et se matérialise en cluster en < 1 h.

**Current focus:** Phase 18 — qbit-post-credentials-fallback

## Current Position

Phase: 18 (qbit-post-credentials-fallback) — EXECUTING
Plan: 1 of 1
Status: Phase 18 shipped — c4ccc0d pushed to main, auto-tag v0.12.1 pending
Last activity: 2026-05-24 -- Phase 18 shipped (15 commits, chart pin 0.10.0 → 0.12.1)

<details>
<summary>Previous: Phase 16 CLOSED 2026-05-24 (3 SC validated live, 10 libs visible in Jellyfin web UI)</summary>

Plan 16-A merged into main, follow-up SC#2 (prune flip) + SC#3 (prune re-lock) shipped. Live cluster: 10 libs, each with single Category path. Legacy v0.2.0 paths pruned (12 removed). arrconf.yml has prune: false re-locked.

</details>

### Known follow-up (NOT Phase 16 scope)

- **Sonarr `remote_path_mappings` HTTP 400** — pre-existing bug blocks full-cron runs since at least 7h before Phase 16. arrconf step 5 (sonarr) crashes → jellyfin (step 1 of jellyfin reconciler) never runs in cron context. Phase 16 was validated via manual `--apps jellyfin` job overrides. To unblock the cron, a separate fix is needed (likely a data-shape regression in `_reconcile_remote_path_mappings` or a Sonarr API behavioral change). Scope candidate for a v0.5.x or v0.6.x bugfix phase.

### Phase 16 close-out checklist (operator)

1. Push `main` to origin (triggers auto-tag CI → v0.8.3 patch bump + arrconf image `:0.8.0` build on GHCR).
2. Wait for Renovate PR on `my-kluster` bumping `targetRevision` to the new arr-stack tag, merge it.
3. ArgoCD sync → new chart deployed, new arrconf image rolled out.
4. Optionally open a follow-up PR on arr-stack: flip `jellyfin.libraries.prune: true` in `charts/arr-stack/files/arrconf.yml` for the cutover (auto-prunes legacy Séries+Films libs).
5. Run HUMAN-UAT scenarios from `.planning/phases/16-jellyfin-categories-as-libs/16-HUMAN-UAT.md` :
   - Scenario 1 (mandatory) — Jellyfin web UI shows 10 libs
   - Scenario 2 (mandatory) — Watched state preserved on ≥ 3 series after reshape
   - Scenario 3 (mandatory) — Flip `prune: false` post-cutover to lock the state
   - Scenario 4 (carry-forward, non-blocking) — JellyCon on LibreELEC top-level shows 10 libs
   - Scenario 5 (optional) — Legacy v0.2.0 paths zombie sweep

## Accumulated Context

### Decisions

Quick reference to 7 LOCKED ADRs (full text in `PROJECT.md` `<decisions>` block):

- **ADR-1** Script Python custom (vs Buildarr/Terraform/Flemmarr)
- **ADR-2** Helm dependencies sur app-template (Option A)
- **ADR-3** Image arrconf sur GHCR public
- **ADR-4** Repo séparé (vs extension my-kluster)
- **ADR-5** configarr conservé (frontière dure quality_profiles/custom_formats/quality_definitions/media_naming)
- **ADR-6** Snapshot baseline avant toute écriture
- **ADR-7** Single instance Sonarr/Radarr + tags (pas multi-instance)
- **ADR-8** arrconf trusted controller — `?forceSave=true` PUT bypass (scoped to *arr v3, NOT qBit/Jellyfin)

Plus milestone-specific decisions to be added during phase planning. Phase 16 must explicitly address D-07-LIB-01 (reverse or adapt the `prune: false` hardcoded on jellyfin.libraries).

### Blockers/Concerns

None. v0.5.0 anchor (Phase 16) is an internal refactor with no external dependency.

### Pending Todos

None at roadmap-ready. To be populated during `/gsd-discuss-phase 16`.

## Deferred Items

Items carried from v0.3.0 / v0.4.0 close — not in v0.5.0 scope, may be re-evaluated for v0.6.0:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| uat_gap | phase-09 initContainer NFS uid=1000 cluster-time write test (09-HUMAN-UAT.md, 2 open scenarios) | partial — code correct, runtime UAT pending | v0.3.0 close (2026-05-22) |
| verification_gap | phase-09 VERIFICATION status human_needed (UAT-driven) | human_needed | v0.3.0 close (2026-05-22) |
| verification_gap | phase-10 VERIFICATION status human_needed (SC#1 cluster materialization + SC#3 TVDB-anime live routing) | human_needed | v0.3.0 close (2026-05-22) |
| infra_gap | SuggestArr ingress + auto-submit (currently port-forward + manual approval) | deferred | v0.4.0 close (2026-05-23) |
| infra_gap | arrconf-ui distribution (currently runs from source via `uv run`) | deferred | v0.4.0 close (2026-05-23) |
| upgrade_check | D-07-PLAYLIST-MGMT-NULL re-verify on Jellyfin 11.x upgrade | watch-only | v0.3.0 close (2026-05-22) |

## Operator Next Steps

- `/gsd-discuss-phase 16` to gather Phase 16 (Jellyfin Categories-as-libs) context — surface D-07-LIB-01 decision, prune policy, JellyCon UAT scope.
- Then `/gsd-plan-phase 16` → `/gsd-execute-phase 16`.
- Phases 17 (arrconf-ui CI) and 18 (qBit POST credentials) follow sequentially after Phase 16.
