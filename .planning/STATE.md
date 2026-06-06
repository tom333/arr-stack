---
gsd_state_version: 1.0
milestone: v0.11.0
milestone_name: Couche d'intention (tranche 2)
status: ready_to_plan
last_updated: "2026-06-06T09:53:11.323Z"
last_activity: 2026-06-06 -- Phase 33 execution started
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 4
  completed_plans: 2
  percent: 67
---

# Project State

## Project Reference

See: `.planning/PROJECT.md`

**Core value:** Aucune intervention UI nécessaire pour configurer Sonarr/Radarr/Prowlarr/qBittorrent/Seerr/Jellyfin après bootstrap — tout passe par PR et se matérialise en cluster en < 1 h.

**Current focus:** Phase 33 — configarr-yml-generation

## Current Position

Phase: 34
Plan: Not started
Status: Ready to plan
Last activity: 2026-06-06

```
Progress: [          ] 0% (0/3 phases)
```

## Accumulated Context

### Decisions

Quick reference to 10 LOCKED ADRs (full text in `PROJECT.md` `<decisions>` block):

- **ADR-1** Script Python custom (vs Buildarr/Terraform/Flemmarr) — tient
- **ADR-2** Helm dependencies sur app-template (Option A)
- **ADR-3** Image arrconf sur GHCR public
- **ADR-4** Repo séparé (vs extension my-kluster)
- **ADR-5** configarr conservé (frontière dure quality_profiles/custom_formats/quality_definitions/media_naming) — étendu par v0.10.0 ADR-10 : la couche intention se place AU-DESSUS ; configarr reste seul appliqueur TRaSH ; `ScopeViolationError` intact et **critique pour Phase 33 (CFGARR)**
- **ADR-6** Snapshot baseline avant toute écriture
- **ADR-7** Single instance Sonarr/Radarr + tags (pas multi-instance)
- **ADR-8** arrconf trusted controller — `?forceSave=true` PUT bypass (scoped to *arr v3)
- **ADR-9** Jellyfin plugin reconciler install-capable (two-run model)
- **ADR-10** Couche d'intention + frontière "absorber vs déployer" (Phase 28) — étendu par v0.11.0 tranche 2 : `generate` absorbe categories[] + configarr.yml CF/QP ; modèle G1 (local + committé) inchangé

### v0.11.0 Roadmap Decisions (2026-06-04)

- **Phase ordering:** Phase 32 (CATMIG hard cut) est le prérequis bloquant des deux suivantes : Phase 33 (CFGARR) requiert que `categories[]` soit dans `intent.yml` pour pouvoir générer les profils par catégorie ; Phase 34 (UI) requiert le schéma intent complet (categories + configarr blocks) pour devenir le seul éditeur cohérent. Ordre forcé : 32 → 33 → 34.
- **Co-bump constraint Phase 32:** CATMIG étend le schéma `IntentConfig` (absorption `categories[]`) + les générateurs dans `tools/arrconf/**` → co-bump `charts/arr-stack/values.yaml#arrconf.image.tag` REQUIS.
- **Co-bump constraint Phase 33:** CFGARR ajoute un nouveau générateur `generators/configarr.py` dans `tools/arrconf/**` → co-bump REQUIS.
- **No co-bump Phase 34:** UI-over-intent touche uniquement `tools/arrconf-ui/**` (FastAPI backend + Svelte frontend) — l'image cluster arrconf n'est pas modifiée → PAS de co-bump.
- **ADR-5 guard Phase 33 (CRITIQUE):** `generate` n'écrit qu'un fichier `configarr.yml` — arrconf ne doit jamais appeler les APIs `quality_profiles`/`custom_formats` (ScopeViolationError intact). Succès critère obligatoire.
- **Hard cut CATMIG:** Pas de double-source ni de période de deprecation-warning (opérateur unique). `arrconf.yml` passe directement de hand-edited à 100% généré. Le guide CI idempotence (`generate --check` + `git diff --exit-code`) est étendu pour couvrir `arrconf.yml` en Phase 32 et `configarr.yml` en Phase 33.
- **Réutilisation Phase 27 catalogue TRaSH:** le catalogue TRaSH baké au build (SHAs pinnés, zéro HTTP runtime) livré en Phase 27 est directement réutilisable pour le générateur CF en Phase 33. Pas de rebuild du catalogue.
- **Build-on-existing:** `arrconf generate` CLI + `--check` mode (Phase 28), générateurs purs dans `generators/`, garde CI `generate-idempotence` dans `tests.yml` — tout est en place, Phase 32 et 33 étendent l'existant.

### v0.9.0 Phase 27 Decisions (carry-forward)

- **QP field mapping confirmed (27-04):** `upgrade.until_quality == TRaSH cutoff`, `qualities[]` reflects `items[allowed!=false]` in baked Feb-2026 order
- **Recyclarr picker write-freeze locked:** RecyclarrReferencePicker = clipboard-only, zero `include:` insertion

### Blockers/Concerns

None blocking — roadmap defined (3 phases, 11 requirements, 100% coverage). Next: plan Phase 32 via `/gsd-plan-phase 32`.

### Pending Todos

- `2026-05-27-migrer-mediatheque-existante-vers-buckets-categories-v0-3-0` (area: ops) — migration filesystem média v0.2.0→v0.3.0 pas encore exécutée ⇒ 3 libs Jellyfin vides (Films, Films-Animation-Enfants, Séries-Émilie). Runbook dans CLAUDE.md. Tâche opérateur manuelle, hors v0.11.0.

## Deferred Items

Items carried from v0.3.0 / v0.4.0 / v0.5.0 close — not in v0.11.0 scope:

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

### Acknowledged at v0.10.0 close (2026-05-31)

7 items acknowledged and deferred at milestone close (audit verdict `tech_debt`, no blockers):

| Category | Item | Status |
|----------|------|--------|
| verification_gap | phase-30 30-VERIFICATION.md human_needed — runtime cluster observation (pod Running, initContainer token resolution) | human_needed — code 3/3 SC verified, artifact-only debt |
| verification_gap | phase-31 31-VERIFICATION.md human_needed — runtime CronJob run observation (share_limits applied, categories untouched) | human_needed — code 3/3 SC verified, artifact-only debt |
| uat_gap | phase-31 31-HUMAN-UAT.md — 2 pending live scenarios | partial — code complete, operator UAT pending |
| code_warning | `generate_qbit_manage` absent from `generators/__init__.__all__` (sibling `generate_cross_seed` exported) | 1-line fix, cosmetic public-API asymmetry; direct import works |
| code_warning | `__main__.py:617` `failures.append("jellyfin_sagas")` should be `"sonarr_saga_tags"` (SAGAS-04 label) | 1-line fix, exit code unaffected (truthiness check) |
| infra_warning | cross-seed ConfigMap and PVC both named `cross-seed-config` (valid K8s, diagnostic ambiguity) | documented in 30-OPERATOR-RUNBOOK.md |
| todo | 2026-05-27-migrer-mediatheque-existante-vers-buckets-categories-v0-3-0 (ops) | pending — manual operator task (runbook in CLAUDE.md, carry-forward since v0.3.0) |

> Note: quick_task `260527-jfk` (autoTMM) reported `missing` by audit-open is artifact-frontmatter debt only — work DONE in commit df280f8 (carry-forward from v0.8.0/v0.9.0).

## Quick Tasks Completed

| Quick ID | Description | Date | Commit | Tests |
|----------|-------------|------|--------|-------|
| 260525-bj5 | client_base.py 4xx response.text[:500] logging (OBS-01) + respx test + chart co-bump 0.12.1 → 0.14.0 | 2026-05-25 | 9726d81 | 416 pass (+5 new) |
| 260527-jfk | enable qBit autoTMM reconcile (preferences.enable+auto_tmm+category_changed) in arrconf.yml — Phase 23 SC#3 save_path fix ; no image co-bump (ConfigMap-only) | 2026-05-27 | df280f8 | config parse OK (no Python change) |

## Operator Next Steps

- Plan Phase 32 via `/gsd-plan-phase 32`
