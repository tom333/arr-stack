# Decisions (ADRs)

Extracted from `spec.md` §11. Each entry below is a separate locked decision (the source SPEC declares them all `LOCKED` — they predate ingestion and are out-of-scope for re-litigation by downstream phases). Higher precedence than any SPEC/PRD/DOC content. Conflicts against any of these = BLOCKER.

---

## ADR-1 — Script Python custom plutôt que Buildarr/Terraform/Flemmarr

- source: /home/moi/projets/perso/arr-stack/spec.md (§11 ADR-1)
- status: LOCKED
- scope: arrconf — choix d'outil de réconciliation
- decision: Développer un script Python custom (inspiré de Flemmarr en lecture). Pas Buildarr (maintenance en dérive, pas de Seerr), pas Terraform (providers immatures qBit/Seerr, GitHub Actions ne peut pas atteindre le cluster privé, state lourd), pas Flemmarr tel quel (on veut maîtriser et étendre).
- consequences:
  - Maintenance par l'auteur (pas de communauté)
  - Tests cruciaux pour éviter les régressions API
  - Pattern reproductible si nouvelle app à intégrer
  - Stack imposée : Python 3.13 + httpx + pydantic v2 + ruyaml (cf C10)

---

## ADR-2 — Helm dependencies sur app-template (Option A)

- source: /home/moi/projets/perso/arr-stack/spec.md (§11 ADR-2)
- status: LOCKED
- scope: charts/arr-stack — structure de l'umbrella chart
- decision: Utiliser `dependencies:` dans `Chart.yaml` pointant sur `bjw-s/app-template`, avec un alias par service. Rejette Option B (sub-charts locaux dupliqués).
- consequences:
  - Pas de duplication de code Helm
  - Renovate suit naturellement la version d'app-template via `helmv3`
  - Multiples alias du même chart — syntaxe à valider en Phase 4
  - Si bjw-s casse, impact transverse sur tous les services

---

## ADR-3 — Image arrconf hébergée sur GHCR public

- source: /home/moi/projets/perso/arr-stack/spec.md (§11 ADR-3)
- status: LOCKED
- scope: arrconf — distribution de l'image
- decision: Image publiée sur `ghcr.io/tom333/arr-stack-arrconf` en visibilité publique. Rejette `localhost:32000` (build local manuel, pas de CI, pas reproductible).
- consequences:
  - Cluster pull anonyme (pas de imagePullSecret)
  - GitHub Actions push avec GITHUB_TOKEN
  - Renovate suit GHCR
  - Aucun secret embarqué dans l'image

---

## ADR-4 — Repo séparé plutôt qu'extension de my-kluster

- source: /home/moi/projets/perso/arr-stack/spec.md (§11 ADR-4)
- status: LOCKED
- scope: gouvernance — emplacement du code
- decision: Repo dédié `github.com/tom333/arr-stack`, distinct de `my-kluster`. Une seule ArgoCD Application dans my-kluster pull ce repo (`charts/arr-stack/`).
- consequences:
  - 2 cycles de PR pour certains changements
  - Effort de découpage initial (~1 journée)
  - Documentation cross-repo nécessaire (CLAUDE.md des deux repos)
  - Versionnement atomique : un release = `Sonarr@X + Radarr@Y + arrconf@Z + configarr@W`

---

## ADR-5 — configarr conservé pour son scope (frontière dure arrconf/configarr)

- source: /home/moi/projets/perso/arr-stack/spec.md (§11 ADR-5, §6.2 frontière, §10 Q5)
- status: LOCKED
- scope: arrconf reconcilers — endpoints qu'arrconf NE doit PAS toucher
- decision: configarr reste seul propriétaire de : quality_profiles, custom_formats, quality_definitions, media_naming. arrconf NE touche PAS à ces ressources (refus explicite côté reconcilers — `ScopeViolationError` si appelé).
- consequences:
  - Deux outils à maintenir avec scopes orthogonaux
  - Le code arrconf doit avoir une garde explicite (raise si tentative d'écrire ces endpoints)
  - Si configarr s'arrête un jour, l'auteur réabsorbera son scope dans arrconf (changement futur de scope nécessitera un nouvel ADR explicite — cf CLAUDE.md "ne pas faire")
- frontière complète (qui possède quoi) — voir constraints.md "Frontière arrconf/configarr"

---

## ADR-6 — Snapshot baseline avant toute écriture

- source: /home/moi/projets/perso/arr-stack/spec.md (§11 ADR-6, §6.5)
- status: LOCKED
- scope: workflow — discipline de protection contre les casses silencieuses
- decision: Workflow snapshot obligatoire en 4 niveaux :
  1. **Phase 0** : script Bash standalone `tools/snapshot/snapshot.sh` qui dump raw JSON de toutes les APIs (read-only, indépendant d'arrconf).
  2. **Phase 1** : `arrconf dump` exporte le même état au format YAML arrconf, seedé dans `examples/baseline-<app>.yml`.
  3. **Phase 2** : déploie arrconf en cluster avec `ARRCONF_DRY_RUN=true` au premier run; bascule en apply seulement après validation des logs.
  4. **Phases 3-7** : chaque phase touchant une nouvelle app commence par un re-snapshot (`snapshots/before-phase-N-<date>/`).
- consequences:
  - Tous les snapshots restent dans Git (lossless, pas de secret, ~quelques MB) — NE PAS ignorer dans `.gitignore`
  - Phase 0 dédiée à du Bash standalone (peu de Python) — décalage de 0.5 journée du POC arrconf
  - Discipline à tenir : re-snapshot AVANT chaque phase de scope nouveau
  - Permet `diff` forensic à n'importe quel moment

---

## ADR-7 — Single instance Sonarr/Radarr + tags (pas multi-instance)

- source: /home/moi/projets/perso/arr-stack/spec.md (§11 ADR-7)
- status: LOCKED
- scope: architecture Sonarr/Radarr/qBittorrent — modèle d'instance et routing
- decision: 1 seule instance Sonarr et 1 seule Radarr, différenciation tv/anime/family via :
  - 3 tags Sonarr/Radarr : `tv`, `anime`, `family`
  - 3 root folders par instance (`/media/series`, `/media/anime`, `/media/family` côté Sonarr; équivalents côté Radarr)
  - 3 download clients qBittorrent par instance, chacun lié à un tag (mécanisme natif Sonarr/Radarr — champ `tags:` sur les download clients)
  - 6 catégories qBit avec save_paths distincts (`sonarr-{tv,anime,family}` + `radarr-{movies,anime,family}`)
  - 3 quality profiles par instance côté configarr (MULTi.VF / Anime / Family) avec scoring adapté
- consequences:
  - Volumétrie homelab modérée : la BDD SQLite Sonarr unique tient sans problème
  - 1 pod / 1 PVC / 1 ingress / 1 API key par app vs 3-6 pods en multi-instance
  - YAMLs simples (un seul bloc `sonarr.main` et `radarr.main`)
  - Single point of failure sur la BDD (atténué par snapshots arrconf et backups Sonarr natifs)
  - Indexers Prowlarr poussés à l'instance unique, ciblage anime-only via tags Prowlarr (à vérifier en Phase 3)
  - Routing Seerr → tag dépend de Q10 (open question, fallback documenté)
- alternative rejetée: multi-instance (sonarr-tv/anime/family + radarr-movies/anime/family) — coût ressource ×3 et complexité GitOps significative pour bénéfice d'isolation marginal en homelab. À reconsidérer uniquement si BDD unique sature ou si Q10 conclut que Seerr ne peut pas router par tag.
