---
gsd_state_version: 1.0
milestone: v0.6.0
milestone_name: arrconf observability — 4xx body logging
status: planning
last_updated: "2026-05-24T11:00:00.000Z"
last_activity: 2026-05-24
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 1
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: `.planning/PROJECT.md`

**Core value:** Aucune intervention UI nécessaire pour configurer Sonarr/Radarr/Prowlarr/qBittorrent/Seerr/Jellyfin après bootstrap — tout passe par PR et se matérialise en cluster en < 1 h.

**Current focus:** Phase 19 — arrconf observability — 4xx body logging

## Current Position

Phase: 19 — arrconf observability — 4xx body logging (not started)
Plan: — (Phase 19-A TBD; 1 plan expected in Wave 1)
Status: Ready to plan (roadmap defined, requirements mapped)
Last activity: 2026-05-24 — v0.6.0 roadmap created (Phase 19, OBS-01 mapped, coverage 1/1)

Progress: [          ] 0% (0/1 phases, 0/1 plans)

### Phase 19 success criteria (from ROADMAP.md)

1. On any 4xx HTTP response in `_request`, a structured log event (e.g. `client_4xx`) is emitted containing client name, HTTP method, request path, status code, and `response.text[:500]` excerpt — respx test asserts excerpt presence.
2. Triade Python green: `cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy arrconf && uv run pytest -q` exits 0; CI `tests.yml` gates pass on push.
3. Chart-pin co-bump `0.12.1 → 0.13.0` in the same commit per CLAUDE.md "Release pin co-bump pattern"; Renovate annotation preserved verbatim.

## Accumulated Context

### Decisions

Quick reference to 8 LOCKED ADRs (full text in `PROJECT.md` `<decisions>` block):

- **ADR-1** Script Python custom (vs Buildarr/Terraform/Flemmarr)
- **ADR-2** Helm dependencies sur app-template (Option A)
- **ADR-3** Image arrconf sur GHCR public
- **ADR-4** Repo séparé (vs extension my-kluster)
- **ADR-5** configarr conservé (frontière dure quality_profiles/custom_formats/quality_definitions/media_naming)
- **ADR-6** Snapshot baseline avant toute écriture
- **ADR-7** Single instance Sonarr/Radarr + tags (pas multi-instance)
- **ADR-8** arrconf trusted controller — `?forceSave=true` PUT bypass (scoped to *arr v3, NOT qBit/Jellyfin)

Phase 19 decisions to be captured during `/gsd-discuss-phase 19` (anticipated: structured-log event-name choice, body-excerpt cap value reaffirmation, distinct event name vs reuse of an existing log event).

### Blockers/Concerns

None. Phase 19 is a localized 2-3 line change to `client_base.py` with no external dependency. The only release-train consideration is the chart-pin co-bump (well-rehearsed pattern from v0.3.0–v0.5.0).

### Pending Todos

None at roadmap-ready. To be populated during `/gsd-discuss-phase 19` → `/gsd-plan-phase 19`.

## Deferred Items

Items carried from v0.3.0 / v0.4.0 / v0.5.0 close — not in v0.6.0 scope, may be re-evaluated for v0.7.0+:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| uat_gap | phase-09 initContainer NFS uid=1000 cluster-time write test (09-HUMAN-UAT.md, 2 open scenarios) | partial — code correct, runtime UAT pending | v0.3.0 close (2026-05-22) |
| verification_gap | phase-09 VERIFICATION status human_needed (UAT-driven) | human_needed | v0.3.0 close (2026-05-22) |
| verification_gap | phase-10 VERIFICATION status human_needed (SC#1 cluster materialization + SC#3 TVDB-anime live routing) | human_needed | v0.3.0 close (2026-05-22) |
| infra_gap | SuggestArr ingress + auto-submit (currently port-forward + manual approval) | deferred | v0.4.0 close (2026-05-23) |
| infra_gap | arrconf-ui distribution (currently runs from source via `uv run`) | deferred | v0.4.0 close (2026-05-23) |
| upgrade_check | D-07-PLAYLIST-MGMT-NULL re-verify on Jellyfin 11.x upgrade | watch-only | v0.3.0 close (2026-05-22) |
| process | HUMAN-UAT frontmatter standardization (audit-open parser compat) | deferred | v0.5.0 close (2026-05-24) |

## Operator Next Steps

- `/gsd-discuss-phase 19` — finalize structured-log event name + excerpt cap before planning
- `/gsd-plan-phase 19` — emit Phase 19-A (single plan, Wave 1)
- `/gsd-execute-phase 19` — apply 4xx logging + respx test + Triade Python + chart co-bump in one commit
