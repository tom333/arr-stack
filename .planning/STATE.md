---
gsd_state_version: 1.0
milestone: v0.5.0
milestone_name: Jellyfin Categories-as-libs + CI/UX hardening
status: planning
stopped_at: ""
last_updated: "2026-05-24T00:00:00.000Z"
last_activity: 2026-05-24 -- Milestone v0.5.0 started
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: `.planning/PROJECT.md`

**Core value:** Aucune intervention UI nécessaire pour configurer Sonarr/Radarr/Prowlarr/qBittorrent/Seerr/Jellyfin après bootstrap — tout passe par PR et se matérialise en cluster en < 1 h.

**Current focus:** Refactor Jellyfin pour exposer les 10 Categories comme libs top-level (visibilité Kodi/JellyCon), restaurer la CI sur arrconf-ui, fixer le qBit POST credentials fallback.

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-05-24 — Milestone v0.5.0 started

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

Plus milestone-specific decisions to be added during phase planning.

### Blockers/Concerns

None. v0.5.0 anchor is an internal refactor with no external dependency.

### Pending Todos

None at milestone open. To be populated during phase discussion.

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

- Approve roadmap (this session) → `/gsd-discuss-phase [N]` to gather phase context, then `/gsd-plan-phase [N]`, then `/gsd-execute-phase [N]`.
