---
gsd_state_version: 1.0
milestone: v0.10.0
milestone_name: Couche d'intention (tranche 1)
status: planning
last_updated: "2026-05-31T06:33:37.967Z"
last_activity: 2026-05-31 -- Phase 30 cross-seed complete
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 13
  completed_plans: 13
  percent: 100
---

# Project State

## Project Reference

See: `.planning/PROJECT.md`

**Core value:** Aucune intervention UI nécessaire pour configurer Sonarr/Radarr/Prowlarr/qBittorrent/Seerr/Jellyfin après bootstrap — tout passe par PR et se matérialise en cluster en < 1 h.

**Current focus:** Phase 31 — qbit_manage

## Current Position

Phase: 31 (qbit_manage) — Ready to plan
Plan: Not started
Status: Ready to plan
Last activity: 2026-05-31 -- Phase 30 cross-seed complete

```
[Phase 28] [Phase 29] [Phase 30] [Phase 31]
  ███████    ███████    ███████    ░░░░░░░    75 % complete (3/4 phases, 13/13 plans)
```

## Accumulated Context

### Decisions

Quick reference to 9 LOCKED ADRs (full text in `PROJECT.md` `<decisions>` block):

- **ADR-1** Script Python custom (vs Buildarr/Terraform/Flemmarr) — tient pour v0.10.0
- **ADR-2** Helm dependencies sur app-template (Option A)
- **ADR-3** Image arrconf sur GHCR public
- **ADR-4** Repo séparé (vs extension my-kluster)
- **ADR-5** configarr conservé (frontière dure quality_profiles/custom_formats/quality_definitions/media_naming) — étendu par v0.10.0 : la couche intention se place AU-DESSUS d'arrconf ET configarr ; configarr reste seul appliqueur TRaSH
- **ADR-6** Snapshot baseline avant toute écriture — CRITIQUE Phase 29 (sagas touche Radarr/Jellyfin live)
- **ADR-7** Single instance Sonarr/Radarr + tags (pas multi-instance)
- **ADR-8** arrconf trusted controller — `?forceSave=true` PUT bypass (scoped to *arr v3)
- **ADR-9** Jellyfin plugin reconciler install-capable (two-run model) — réutilisé Phase 29 pour tmdbboxsets

**ADR-nouveau (à rédiger Phase 28):** couche d'intention + frontière "absorber vs déployer" (extension ADR-5).

### v0.10.0 Roadmap Decisions (2026-05-31)

- **Phase ordering:** Phase 28 (generate foundation) est le prérequis bloquant de toutes les autres. Phases 29, 30, 31 sont indépendantes entre elles une fois Phase 28 complète — elles peuvent être planifiées/exécutées dans cet ordre logique (complexité décroissante : sagas = plus risqué, cross-seed et qbit_manage = chart-only, pas de co-bump arrconf image).
- **Co-bump constraint Phase 28:** `arrconf generate` est du code Python dans `tools/arrconf/**` → MUST co-bump `charts/arr-stack/values.yaml#arrconf.image.tag` dans le même commit.
- **Co-bump constraint Phase 29:** nouveau reconciler Radarr Collections = code Python → MUST co-bump arrconf image tag.
- **No co-bump Phases 30-31:** cross-seed et qbit_manage = Helm aliases + ConfigMaps uniquement (générateurs purs dans arrconf, mais pas de nouveau reconciler) — si les générateurs sont dans `tools/arrconf/**`, co-bump REQUIS. À clarifier en discuss-phase : si `arrconf generate` code est dans Phase 28 et les générateurs cross-seed/qbit_manage sont ajoutés dans Phase 28, Phases 30-31 n'ajoutent que le Helm. Sinon co-bump si nouvel arrconf code.
- **ADR-6 Phase 29:** snapshot raw obligatoire AVANT le premier test live cluster sagas (nouveau reconciler Radarr Collections + plugin Jellyfin).
- **5 questions ouvertes design §6** à résoudre en discuss-phase avant Phase 28 : schéma `intent.yml`, sagas séries validation, cross-seed migration + linkDirs, ratio policy qbit_manage, `arrconf generate` CLI guard.
- **Phase 30 cross-seed (livré 2026-05-31, 3/3 plans):** tokens env distincts dans `intent.yml`/`config.js` (pas de `PLACEHOLDER` partagé) ; `${QBT_USER}` (pas `admin` hard-codé) ; 12e alias `app-template` avec initContainer Node.js (pas busybox+envsubst) faisant la substitution secret → emptyDir, advancedMounts pour éviter PVC shadowing (Pitfall 1) ; probes `tcpSocket` 2468 (pas d'endpoint health no-auth) ; `values.schema.json` étendu (`cross-seed` additionalProperties:true) ; CI renovate threshold 10→12. Patch bump arrconf `:0.19.1` (token-emission fix). Pas de nouveau reconciler arrconf → Helm-only au-delà du générateur.

### v0.9.0 Phase 27 Decisions (carry-forward)

- **QP field mapping confirmed (27-04):** `upgrade.until_quality == TRaSH cutoff`, `qualities[]` reflects `items[allowed!=false]` in baked Feb-2026 order
- **Recyclarr picker write-freeze locked:** RecyclarrReferencePicker = clipboard-only, zero `include:` insertion

### Blockers/Concerns

None blocking. Notes for Phase 28 planning:

- **5 open design questions** (design §6) must be resolved in discuss-phase before Phase 28 coding — especially `intent.yml` schema cohabitation with `categories[]` (same file or separate?) and the `arrconf generate` CLI guard mechanism.
- **Phase 29 medium-confidence items**: exact Radarr `/api/v3/collection` PUT parameter format (GET-match tmdbId confirmed in design sources) ; `tmdbboxsets` plugin GUID/version to pin for ADR-9 install model.
- **Phase 30 cross-seed migration** — RESOLVED: consolidated as 12th Helm alias; teardown of out-of-stack instance + optional `config.db` history migration documented in `30-OPERATOR-RUNBOOK.md`. dedicated PVC = no data loss on rollback.

### Pending Todos

- `2026-05-27-migrer-mediatheque-existante-vers-buckets-categories-v0-3-0` (area: ops) — migration filesystem média v0.2.0→v0.3.0 pas encore exécutée ⇒ 3 libs Jellyfin vides (Films, Films-Animation-Enfants, Séries-Émilie). Runbook dans CLAUDE.md. Tâche opérateur manuelle, hors v0.10.0.

## Deferred Items

Items carried from v0.3.0 / v0.4.0 / v0.5.0 close — not in v0.10.0 scope:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| uat_gap | phase-09 initContainer NFS uid=1000 cluster-time write test (09-HUMAN-UAT.md, 2 open scenarios) | partial — code correct, runtime UAT pending | v0.3.0 close (2026-05-22) |
| verification_gap | phase-09 VERIFICATION status human_needed (UAT-driven) | human_needed | v0.3.0 close (2026-05-22) |
| verification_gap | phase-10 VERIFICATION status human_needed (SC#1 cluster materialization + SC#3 TVDB-anime live routing) | human_needed | v0.3.0 close (2026-05-22) |
| infra_gap | SuggestArr ingress + auto-submit (currently port-forward + manual approval) | deferred | v0.4.0 close (2026-05-23) |
| upgrade_check | D-07-PLAYLIST-MGMT-NULL re-verify on Jellyfin 11.x upgrade | watch-only | v0.3.0 close (2026-05-22) |

### Acknowledged at v0.8.0 close (2026-05-27)

| Category | Item | Status |
|----------|------|--------|
| verification_gap | phase-21 VERIFICATION human_needed (live file-present + qBit re-hash + Jellyfin ItemCount; cluster torn down) | human_needed — mechanism PASS-WITH-CONCERNS |
| verification_gap | phase-22 NO VERIFICATION.md (deliverable cross-verified by P23 + integration checker) | accepted — process gap |
| coverage_gap | phase-22 force_prune=true DELETE path never exercised live (surgical direct-API deletes used) | re-verify before prune:true in arrconf.yml |
| migration_gap | phase-21 10 records missing-on-disk (disk drift); DB Category-anchored, files absent | operator follow-up (re-download/remove) |
| uat_gap | phase-23 SC#5 — 3 Jellyfin libs empty pending media filesystem migration | partial-deferred, operator-accepted |
| todo | 2026-05-27-migrer-mediatheque-existante-vers-buckets-categories-v0-3-0 (ops) | pending — manual operator task |
| quick_task | 260527-jfk autoTMM reconcile (artifact status `missing`) | DONE (commit df280f8) — artifact frontmatter only |
| uat_gap+verification_gap | phase-09 + phase-10 carry-forward (NFS write test, TVDB-anime routing) | non-blocking — see table above |

### Acknowledged at v0.9.0 close (2026-05-31)

| Category | Item | Status |
|----------|------|--------|
| uat_gap | phase-27 27-HUMAN-UAT.md — 2 pending scenarios (QP collision normalization, QP live-save mapping) | partial — code complete, operator UAT pending |
| verification_gap | phase-27 27-VERIFICATION.md human_needed (UAT-driven) | human_needed — code complete |
| quick_task | 260527-jfk autoTMM reconcile (artifact status `missing`) | DONE (commit df280f8) — artifact frontmatter only (carry-forward from v0.8.0) |
| todo | 2026-05-27-migrer-mediatheque-existante-vers-buckets-categories-v0-3-0 (ops) | pending — manual operator task (runbook in CLAUDE.md) |
| seed | SEED-002-stack-tools-evaluation | resolved by v0.10.0 design §4 — autobrr deferred, Tdarr/FileFlows rejected non-OSS, decluttarr rejected |

## Quick Tasks Completed

| Quick ID | Description | Date | Commit | Tests |
|----------|-------------|------|--------|-------|
| 260525-bj5 | client_base.py 4xx response.text[:500] logging (OBS-01) + respx test + chart co-bump 0.12.1 → 0.14.0 | 2026-05-25 | 9726d81 | 416 pass (+5 new) |
| 260527-jfk | enable qBit autoTMM reconcile (preferences.enable+auto_tmm+category_changed) in arrconf.yml — Phase 23 SC#3 save_path fix ; no image co-bump (ConfigMap-only) | 2026-05-27 | df280f8 | config parse OK (no Python change) |

## Operator Next Steps

- Run `/gsd-plan-phase 31` to plan Phase 31 (qbit_manage) — last phase of v0.10.0 tranche 1
- Phase 30 cross-seed runtime pre-reqs (before next ArgoCD sync): create `cross-seed-config` PVC + `mkdir -p /media/data/torrents/cross-seed` on node + confirm `arrconf-env` carries `PROWLARR_API_KEY`/`QBT_USER`/`QBT_PASS` (see `30-OPERATOR-RUNBOOK.md`)
- `30-VERIFICATION.md` flagged human_needed — functionally closed by UAT 4/4 PASS (artifact-only debt)
