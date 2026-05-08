# before-phase-2-2026-05-08

Re-snapshot avant déploiement Phase 2 (ADR-6 / D-30 #1).
Captured: 2026-05-08
Scope: 6 apps (sonarr, radarr, prowlarr, qbittorrent, seerr, jellyfin) — identique à `baseline-2026-05-07/`.

## Pourquoi ce snapshot

Anchor pré-déploiement pour Phase 2 (cluster validation). Wave 3 (PR1 dry-run) compare
`diff -rq sonarr/` entre cette baseline et `post-phase2-pr1-<date>/sonarr/` — résultat attendu = 0
(success criterion #3 : aucune écriture pendant le dry-run).

Wave 4 (PR2 apply mode) vérifie ensuite que `sonarr/tag.json` gagne l'entrée `arrconf-managed`
entre cette baseline et `post-phase2-pr2-<date>/sonarr/tag.json` (success criterion #4).

Si `diff -r` vs `baseline-2026-05-07/` montre 0 changement, le re-snapshot est fonctionnellement
identique — on le commit quand même comme l'anchor explicite "before Phase 2" (ADR-6).

## Audit anti-leak

Pattern jq Phase 0 (00-03-SUMMARY.md §Task 4) appliqué : 19 fichiers redactés
(apiKey / password forms-auth / Prowlarr passkey indexer). Re-audit final = 0 leak.
