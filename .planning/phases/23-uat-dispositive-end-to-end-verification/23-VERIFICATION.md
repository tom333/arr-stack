---
phase: 23-uat-dispositive-end-to-end-verification
verified: 2026-05-27
status: verified
score: 4/5
overrides_applied: 0
verification_method: operator-driven-live-uat
requirements_verified: [CAT-CLEANUP-04]
deferred_criteria: [SC#5]
verification_note: |
  Phase 23 est une UAT dispositive opérateur-exécutée contre le cluster live
  my-kluster (arrconf :0.15.0). Vérification = exécution réelle du runbook
  23-HUMAN-UAT.md par l'opérateur, pas une analyse de code. Décision opérateur
  2026-05-27 : clôturer v0.8.0 avec SC#5 partial-deferred.
---

# Phase 23 Verification — UAT dispositive end-to-end

**Verdict : 4/5 SC PASS, SC#5 PARTIAL-deferred. CAT-CLEANUP-04 fermé. Cleanup config v0.8.0 prouvé durable en live.**

## Goal

Prouver en live que le cleanup Categories des Phases 21-22 tient : roots legacy
absents des APIs *arr, routage Seerr→qBit via le DC per-Category (pas le catch-all
supprimé), apply non-dry-run idempotent, libs Jellyfin Category câblées.

## Success Criteria

| SC | Must-have | Verdict | Evidence (live) |
|----|-----------|---------|-----------------|
| SC#1 | Radarr roots : legacy absents, /media/films présent | ✅ PASS | 5 roots Categories ; `any(films-anime|films-family)`→false ; `any(/media/films)`→true |
| SC#2 | Sonarr roots : legacy absents, /media/series présent | ✅ PASS | 5 roots Categories ; `any(anime|family)`→false ; `any(/media/series)`→true |
| SC#3 | Seerr kids-film → DC per-Category (pas catch-all) | ✅ PASS | Spy Kids 3-D : Radarr `downloadClient="qBittorrent - Films - Enfants"`, qBit `category=films-enfants` ; catch-all id=1 NON ressuscité. (save_path=/data/complete → todo, orthogonal) |
| SC#4 | apply non-dry-run ×2 → 0 plan_action root_folders/tags/DC | ✅ PASS | RUN 1+2 : 0 action sur les 3 ressources, sonarr+radarr. RUN 1 : 1 content_tags family (film SC#3, hors périmètre). RUN 2 : no-op total → idempotent |
| SC#5 | 10 libs Jellyfin ItemCount > 0 | ⚠️ PARTIAL (7/10) | 10 libs énumérées (structure OK) ; Films/Films-Animation-Enfants/Séries-Émilie = 0 |

## SC#5 Disposition (deferred — accepted)

Les 3 libs vides résultent de la **migration filesystem média v0.2.0→v0.3.0
non encore exécutée** (opérateur confirmé : « pas encore migré la médiathèque
existante »). C'est :
- PAS un bug arrconf (10 libs créées + câblées correctement)
- PAS une régression du cleanup (aucune lib vidée par le cleanup)
- une tâche opérateur manuelle séparée, hors scope v0.8.0 (cleanup config)

Décision opérateur 2026-05-27 : clôturer v0.8.0, SC#5 partial-deferred.
Reporté au todo `2026-05-27-migrer-mediatheque-existante-vers-buckets-categories-v0-3-0`.

## ADR-6 Forensics

- `snapshots/before-phase23-uat-2026-05-27/` (commit `c9534f4`) + `snapshots/after-phase23-uat-2026-05-27/` (commit `301e9c3`) — 6 apps, secrets auto-redactés.
- Diff borné : artefacts SC#3 (qbit torrents_info, seerr request, prowlarr indexerstats) + bruit session/freeSpace.
- **Paths root_folder radarr+sonarr IDENTIQUES pre/post → zéro drift de config.**

## Deferred / Follow-up Items

1. `activer-qbit-autotmm-via-arrconf-preferences-allowlist` — qBit autoTMM off ⇒ save_path SC#3 = /data/complete. Fix = `preferences.enable: true`. Chart change, hors v0.8.0.
2. `migrer-mediatheque-existante-vers-buckets-categories-v0-3-0` — migration média disque pending ⇒ SC#5 partial. Runbook dans CLAUDE.md. Tâche ops manuelle.

## Conclusion

Le but de la phase — prouver la durabilité du cleanup config Categories — est
**atteint** : SC#1-4 PASS en live + structure des 10 libs Jellyfin correcte.
CAT-CLEANUP-04 fermé. SC#5 partial-deferred par décision opérateur (gap = migration
média, orthogonal au cleanup). v0.8.0 prêt à ship.
