---
gsd_state_version: 1.0
milestone: v0.8.0
milestone_name: Categories cleanup — v0.2.0 legacy migration close-out
status: planning
last_updated: "2026-05-25T08:00:00.000Z"
last_activity: 2026-05-25
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 5
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: `.planning/PROJECT.md`

**Core value:** Aucune intervention UI nécessaire pour configurer Sonarr/Radarr/Prowlarr/qBittorrent/Seerr/Jellyfin après bootstrap — tout passe par PR et se matérialise en cluster en < 1 h.

**Current focus:** Phase 20 — Categories cleanup audit (legacy v0.2.0 items/tags/paths inventory)

## Current Position

Phase: 20 — Categories cleanup audit (Not started, ready for `/gsd-discuss-phase 20`)
Plan: —
Status: Roadmap created; Phase 20 next
Last activity: 2026-05-25 — v0.8.0 ROADMAP created (4 phases mapped 1-to-1 to 4 requirements, 100% coverage)

### Phase 20 success criteria (from ROADMAP.md)

1. `.planning/phases/20-categories-cleanup-audit/20-AUDIT.md` exists and lists every Radarr movie + Sonarr series whose `rootFolderPath` is a legacy v0.2.0 path, with target Category path resolved per item.
2. Audit captures every qBit torrent whose `save_path` starts with a legacy `/data/torrents/<legacy>/` segment, with target Category save_path resolved.
3. Audit enumerates every Radarr/Sonarr tag that is legacy (`movies`, `family`, `films`, `anime`) vs Category, with proposed prune/rename action per tag.
4. `legacy_path → Category` and `legacy_tag → Category_tag` mapping tables are committed and validated against CLAUDE.md "Filesystem migration v0.2.0 → v0.3.0" reference table.

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

v0.8.0 decisions to be captured during `/gsd-discuss-phase 20` → `22` (anticipated: ambiguous-item mapping rules in Phase 20; DC catch-all `qBittorrent` disposition in Phase 22 — prune vs `unsorted` low-priority fallback).

### Blockers/Concerns

None as of roadmap-ready. Risk register documented in `.planning/REQUIREMENTS.md` — primary destructive concerns (`mv` watch state, API mutation regressions, DC prune cutting in-flight torrents, over-prune at apply) are gated by ADR-6 snapshots + per-item operator-driven execution + Triade Python + `--dry-run` discipline.

### Pending Todos

None at roadmap-ready. To be populated during `/gsd-discuss-phase 20` → `/gsd-plan-phase 20`.

## Deferred Items

Items carried from v0.3.0 / v0.4.0 / v0.5.0 close — not in v0.8.0 scope, may be re-evaluated for v0.9.0+:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| uat_gap | phase-09 initContainer NFS uid=1000 cluster-time write test (09-HUMAN-UAT.md, 2 open scenarios) | partial — code correct, runtime UAT pending | v0.3.0 close (2026-05-22) |
| verification_gap | phase-09 VERIFICATION status human_needed (UAT-driven) | human_needed | v0.3.0 close (2026-05-22) |
| verification_gap | phase-10 VERIFICATION status human_needed (SC#1 cluster materialization + SC#3 TVDB-anime live routing) | human_needed | v0.3.0 close (2026-05-22) |
| infra_gap | SuggestArr ingress + auto-submit (currently port-forward + manual approval) | deferred | v0.4.0 close (2026-05-23) |
| infra_gap | arrconf-ui distribution (currently runs from source via `uv run`) | deferred | v0.4.0 close (2026-05-23) |
| upgrade_check | D-07-PLAYLIST-MGMT-NULL re-verify on Jellyfin 11.x upgrade | watch-only | v0.3.0 close (2026-05-22) |
| process | HUMAN-UAT frontmatter standardization (audit-open parser compat) | deferred | v0.5.0 close (2026-05-24) |

## Quick Tasks Completed

| Quick ID | Description | Date | Commit | Tests |
|----------|-------------|------|--------|-------|
| 260525-bj5 | client_base.py 4xx response.text[:500] logging (OBS-01) + respx test + chart co-bump 0.12.1 → 0.14.0 | 2026-05-25 | 9726d81 | 416 pass (+5 new) |

## Operator Next Steps

- `/gsd-discuss-phase 20` — resolve ambiguous `legacy → Category` mapping rules before audit execution
- `/gsd-plan-phase 20` — break audit into executable steps (API queries, mapping tables, doc output)
- `/gsd-execute-phase 20` — produce `20-AUDIT.md`
