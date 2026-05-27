---
phase: 23-uat-dispositive-end-to-end-verification
plan: "01"
subsystem: operator-runbook
tags: [uat, runbook, adr-6-snapshot, categories-cleanup, dc-routing, idempotence, jellyfin-libs, sc-verification]
dependency_graph:
  requires: [22-RUNBOOK, live-cleanup-executed, "arrconf-image-0.15.0-deployed"]
  provides: [23-HUMAN-UAT, dispositive-routing-proof, sc1-4-verified-live, adr-6-pre-post-snapshots]
  affects: [v0.8.0-milestone-close, CAT-CLEANUP-04]
tech_stack:
  added: []
  patterns: [adr-6-snapshot-before-after, operator-driven-uat, per-sc-result-table]
key_files:
  created:
    - .planning/phases/23-uat-dispositive-end-to-end-verification/23-HUMAN-UAT.md
    - snapshots/before-phase23-uat-2026-05-27/
    - snapshots/after-phase23-uat-2026-05-27/
    - .planning/todos/pending/2026-05-27-activer-qbit-autotmm-via-arrconf-preferences-allowlist.md
    - .planning/todos/pending/2026-05-27-migrer-mediatheque-existante-vers-buckets-categories-v0-3-0.md
  modified: []
decisions:
  - "SC#1/SC#2 PASS live — Radarr+Sonarr /api/v3/rootfolder = 10 Category paths total, zéro legacy (films-anime/films-family/anime/family absents), defaults films+series présents. Re-confirme les deletes Phase 22 contre l'API live."
  - "SC#3 PASS (routage dispositif) — nouvelle requête Seerr 'Spy Kids 3-D' routée via le DC per-Category 'qBittorrent - Films - Enfants' + category=films-enfants ; le catch-all id=1 supprimé en Phase 22 n'a PAS été ressuscité. C'est la preuve centrale de CAT-CLEANUP-04."
  - "SC#3 save_path = /data/complete (≠ /data/torrents/films-enfants) car qBit auto_tmm_enabled=false + category_changed_tmm_enabled=false. Orthogonal au cleanup (gap config qBit préexistant, arrconf preferences.enable=false). Reporté au todo activer-qbit-autotmm-via-arrconf-preferences-allowlist."
  - "SC#4 PASS — arrconf apply non-dry-run ×2 : root_folders/tags/download_clients = 0 plan_action sonarr+radarr les 2 runs. RUN 1 a 1 content_tags_applied (tag family sur le film SC#3, convergence attendue hors périmètre SC#4) ; RUN 2 no-op total → idempotent."
  - "SC#5 PARTIAL (7/10 libs) — 10 libs Jellyfin énumérées (structure OK) mais Films/Films-Animation-Enfants/Séries-Émilie à ItemCount 0 : migration filesystem média v0.2.0→v0.3.0 pas encore exécutée (opérateur confirmé). Pas un bug arrconf ni régression cleanup. Décision opérateur 2026-05-27 : clôturer v0.8.0, SC#5 partial-deferred → todo migrer-mediatheque-existante-vers-buckets-categories-v0-3-0."
  - "ADR-6 — pre+post snapshots commités ; diff borné : artefacts SC#3 (qbit torrents_info, seerr request, prowlarr indexerstats) + bruit session/freeSpace. Paths root_folder radarr+sonarr IDENTIQUES pre/post → zéro drift de config."
requirements-completed: [CAT-CLEANUP-04]
metrics:
  completed: "2026-05-27"
  tasks_completed: 2
  files_created: 5
---

# Phase 23: UAT dispositive end-to-end — Summary

**UAT live my-kluster (arrconf :0.15.0) prouvant le cleanup Categories v0.8.0 : roots legacy absents, routage Seerr→qBit via le DC per-Category (pas le catch-all), apply non-dry-run idempotent ×2, 10 libs Jellyfin structurées — clôt CAT-CLEANUP-04.**

## Performance

- **Completed:** 2026-05-27
- **Tasks:** 2/2 (Task 1 auto + Task 2 checkpoint human-action)
- **Files created:** 5 (runbook + 2 snapshots + 2 todos de suivi)

## Accomplishments

- `23-HUMAN-UAT.md` — runbook opérateur FR (7 Étapes, 5 SC, exact jq/curl, table Résultats, Troubleshooting, Rollback), mirroring 22-RUNBOOK.
- UAT exécuté en live par l'opérateur : **SC#1-4 PASS**, **SC#5 PARTIAL (7/10)**.
- Preuve dispositive SC#3 : grab kids-film routé via `qBittorrent - Films - Enfants` (catch-all id=1 NON ressuscité).
- Idempotence SC#4 confirmée : apply ×2, RUN 2 no-op total.
- 2 findings hors-scope capturés en todos (qBit autoTMM, migration média disque).
- ADR-6 pre+post snapshots commités, diff borné, zéro drift de config.

## Task Commits

1. **Task 1: Author 23-HUMAN-UAT.md runbook** — scaffold `35efb07`, fix CLI `e6b6162`, fill résultats `a8ec564`
2. **Task 2: Operator UAT execution** — pré-snapshot `c9534f4`, post-snapshot `301e9c3`, résultats `a8ec564`

Todos de suivi : `73cf338` (qBit autoTMM) + `a8ec564` (migration média).

## Résultats SC (live)

| SC | Verdict | Preuve |
|----|---------|--------|
| SC#1 Radarr roots | ✅ PASS | 5 roots Categories, legacy `any`→false, `/media/films`→true |
| SC#2 Sonarr roots | ✅ PASS | 5 roots Categories, legacy `any`→false, `/media/series`→true |
| SC#3 routage DC | ✅ PASS | Spy Kids 3-D → DC `qBittorrent - Films - Enfants`, category films-enfants (save_path→todo) |
| SC#4 apply ×2 | ✅ PASS | 0 plan_action root_folders/tags/DC les 2 runs ; RUN 2 no-op total (idempotent) |
| SC#5 Jellyfin libs | ⚠️ PARTIAL 7/10 | 10 libs structurées ; 3 vides (migration média pending → todo) |

## Decisions Made

Voir frontmatter `decisions`. Synthèse : le cleanup config v0.8.0 (CAT-CLEANUP-04) est **prouvé durable** par SC#1-4 + la structure des 10 libs. Deux gaps orthogonaux (qBit autoTMM save_path, migration média disque) sont réels mais hors scope v0.8.0 et capturés en todos. Décision opérateur : clôturer v0.8.0 avec SC#5 partial-deferred.

## Deviations from Plan

- **Runbook CLI fix** — `arrconf apply --log-level` était au mauvais rang (option globale, pas de sous-commande). Corrigé dans le runbook (`e6b6162`) — fix de la doc-deliverable, dans le scope Task 1.
- **SC#3/SC#5 findings** — deux écarts découverts en exécution (qBit autoTMM, migration média), tous deux orthogonaux au cleanup, capturés en todos plutôt que fixés (chart/ops change = hors scope UAT).

Aucune dérive de scope code/chart : Phase 23 reste UAT pure (1 doc + snapshots + todos).

## Issues Encountered

- cwd drift orchestrateur (cd tools/arrconf de SC#4 persistant) — résolu en requêtant depuis la racine.
- Word-splitting zsh sur les noms de libs Jellyfin (espaces) — résolu via `while IFS=$'\t' read`.
- `${!v}` bash indirect non supporté en zsh — résolu via `eval`/`${(P)v}`.

## Next Phase Readiness

- **v0.8.0 prêt à ship** : CAT-CLEANUP-04 fermé, cleanup config prouvé durable.
- Suivi v0.9.0+ : 2 todos (qBit autoTMM `preferences.enable`, migration média filesystem).
- Avant ship : `/gsd-complete-milestone` pour archiver v0.8.0.

---
*Phase: 23-uat-dispositive-end-to-end-verification*
*Completed: 2026-05-27*
