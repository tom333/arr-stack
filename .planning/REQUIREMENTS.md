# Requirements — Milestone v0.8.0

**Milestone:** v0.8.0 Categories cleanup — v0.2.0 legacy migration close-out
**Status:** Active (planned)
**Started:** 2026-05-25

## Goal

Fermer la migration v0.2.0 → v0.3.0 Categories qui a été partiellement appliquée. La v0.3.0 (Phase 9-11) a introduit `categories[]` first-class et créé les `/media/<category>/` dirs côté Jellyfin volume. La Phase 16 v0.5.0 a refait Jellyfin pour exposer 10 libs Category-driven. **Mais** :

1. Les root_folders legacy de Radarr/Sonarr (`/media/films`, `/media/films-anime`, `/media/films-family`, `/media/series`, `/media/anime`, `/media/family`) n'ont jamais été nettoyés
2. Les tags legacy (`movies`, `family`, `films`, `anime`) coexistent avec les Categories tags (`films-enfants`, `series-zoe`, etc.)
3. Le DC catch-all `qBittorrent` (no tags, priority=1) intercepte tous les nouveaux torrents avant que les DCs Categories puissent matcher
4. Les films/séries déjà importés dans `arr-stack` pointent vers les legacy paths au lieu des Categories

Surfacé via "La Planète des Alphas" stuck sur `/media/films-family` (2026-05-25 — torrent abandonné par les seeders mais aussi mauvaise route). Symétrique au fix Sonarr RPM 400 d'hier (debug session `sonarr-rpm-400-categories`) qui avait créé les `/data/torrents/<cat>/` manquants côté qBittorrent volume. v0.8.0 fait l'équivalent côté metadata Radarr/Sonarr + filesystem migration côté NFS.

## v0.8.0 Requirements

### Audit

- [ ] **CAT-CLEANUP-01** (REQ-categories-cleanup-audit) — Inventaire exhaustif des items qui pointent vers les legacy v0.2.0 paths/tags. Pour chaque app : (a) Radarr movies sur legacy `rootFolderPath` (compteur + liste), (b) Sonarr series sur legacy `rootFolderPath` (idem), (c) qBit torrents en cours avec save_path legacy (`/data/torrents/{complete,series,anime,family,films,films-anime,films-family}/`), (d) liste exhaustive des tags Radarr/Sonarr legacy vs Categories, (e) Mapping `legacy_path → Category` cible déterminé par la table CLAUDE.md "Filesystem migration v0.2.0 → v0.3.0" (à valider/raffiner), (f) Mapping `legacy_tag → Category_tag` (par exemple `family` → `films-enfants` OU `series-garcons` selon kind), (g) Décisions explicit par item ambigu (auto-mappable vs operator-judgment). Livrable : `.planning/phases/20-categories-cleanup-audit/20-AUDIT.md` consommé par CAT-CLEANUP-02.

### Migration

- [ ] **CAT-CLEANUP-02** (REQ-categories-cleanup-migration) — Migration physique + métadonnées. (a) Snapshot ADR-6 pre-migration (tools/snapshot/snapshot.sh sur Sonarr/Radarr/qBit/Jellyfin), (b) Filesystem `mv` via `kubectl exec` dans Jellyfin pod : `/media/films/<film>` → `/media/films-enfants/<film>` etc. selon mapping CAT-CLEANUP-01, (c) qBit-side renames si torrents en cours sur legacy save_path (`POST /api/v2/torrents/setLocation`), (d) Radarr API mutations : pour chaque movie sur legacy `rootFolderPath`, PUT le movie avec `rootFolderPath` Category + `path` Category + tags Category. Idem Sonarr séries. (e) Triggered Radarr/Sonarr re-scan post-migration (`POST /api/v3/command RefreshMovie/RefreshSeries`) pour qu'ils détectent les fichiers à leur nouvel emplacement, (f) Jellyfin library refresh (`POST /Library/Refresh`), (g) Snapshot ADR-6 post-migration + diff vs pre. Cluster reste fonctionnel pendant la migration (pas de downtime).

### arrconf prune legacy

- [x] **CAT-CLEANUP-03** (REQ-categories-cleanup-arrconf-prune) — arrconf reconciler étendu pour empêcher le drift de revenir. (a) Nouveau `prune: true` filtré aux Categories sur Sonarr/Radarr `root_folders` step : tout `rootFolderPath` qui n'est PAS dans `categories[]` + pas dans une allowlist explicite est purgé au prochain apply. (b) Idem sur Sonarr/Radarr `tags` step : tags legacy purgés sauf si explicitement listés dans `arrconf-managed` allowlist. (c) Décision sur DC catch-all `qBittorrent` (id=1, no tags) : soit prune complet, soit re-tagger avec un fallback tag `unsorted` (priority=50 → ne match que si aucun Category DC ne match d'abord). Choix à faire pendant `/gsd-discuss-phase 22`. (d) Pydantic validation refuse les `rootFolderPath` qui ne sont pas dans `categories[]` paths — fail-fast si l'opérateur essaye d'ajouter un legacy path dans `arrconf.yml`. (e) Triade Python green, respx tests pour chaque prune step. (f) Co-bump chart-pin 0.14.x → 0.15.0 (minor, c'est une feature cleanup).

### UAT dispositif

- [x] **CAT-CLEANUP-04** (REQ-categories-cleanup-uat) — Dispositive end-to-end verification post-migration. SC#1 : Radarr `/api/v3/rootfolder` ne retourne QUE les Categories paths — les 2 legacy `films-anime`, `films-family` absents (`films` = Category valide par défaut, PAS legacy). SC#2 : Sonarr idem — legacy `anime`, `family` absents (`series` = Category valide). SC#3 : Trigger un nouveau Seerr request kids → vérifier que le film atterrit dans `/media/films-enfants/`, qBit category `films-enfants`, save_path `/data/torrents/films-enfants/`, et que c'est le DC `qBittorrent - Films - Enfants` qui a accepté le torrent (pas le DC catch-all `qBittorrent`). SC#4 : Second `arrconf apply` post-cleanup emits 0 plan_action sur root_folders/tags/download_clients pour sonarr+radarr (idempotence préservée). SC#5 : Jellyfin web UI montre toujours 10 libs avec content (pas de lib vide post-migration). Livrable : `23-HUMAN-UAT.md` runbook + result tracking.

## Future Requirements

Deferred to v0.9.0+ (carry-forward from earlier milestones, refined post v0.8.0 scope):

- REQ-suggestarr-ingress — SuggestArr ingress + auto-submit
- REQ-config-ui-multi-config — configarr.yml editing in arrconf-ui (ADR-5 frontière re-check needed)
- REQ-auto-tag-rescue-automation — chart-pin co-bump rescue automation
- REQ-arrconf-dry-run-pr-gate — GHA job running `arrconf apply --dry-run` on PRs
- REQ-jellyfin-native-subtitles — activate Open Subtitles plugin Jellyfin (continuité v0.7.0)
- REQ-jellyfin-skip-intro — Jellyfin 10.10+ chapter markers + skip intro
- REQ-radarr-sonarr-lists — TMDb/Trakt list auto-import
- REQ-radarr-sonarr-release-profiles — preferred/required/ignored keywords per tag
- HUMAN-UAT frontmatter standardization

Out of scope (per v0.7.0 decision):
- REQ-bazarr-addition / REQ-lidarr-addition / REQ-whisparr-addition / REQ-readarr-addition
- REQ-config-ui-git-integration (arrconf-ui reste local-only per operator decision)
- REQ-arrconf-ui-distribution (idem)

## Out of Scope (v0.8.0)

### Scope discipline (explicit)

- **Aucune nouvelle Category** — v0.8.0 ne touche pas `categories[]`. Si l'opérateur veut ajouter une Category, c'est un autre milestone.
- **Aucun nouveau reconciler step** — pas d'ajout d'app, pas de nouveau resource type. Que des prune steps sur du existant.
- **Aucun re-import historique** — les watch states / dates d'ajout des items migrés sont préservés best-effort. Si Jellyfin perd le watch state d'un item dans le `mv`, on accepte (single-user, kids regardent en boucle).
- **Pas de UI Jellyfin cleanup** — déjà fait Phase 16 v0.5.0. v0.8.0 ne touche pas la lib config Jellyfin (seulement re-scan).
- **Pas de qBit categories rename** — les Categories qBit (`films-enfants`, `series-zoe`, etc.) sont déjà bonnes depuis Phase 10 v0.3.0. Seuls les save_paths legacy peuvent rester à nettoyer.
- **Pas de Prowlarr / Seerr cleanup** — ces apps n'ont pas de legacy v0.2.0 state (Prowlarr proxie just les indexers, Seerr suit les Sonarr/Radarr profiles).

### Reasoning

C'est une **migration cleanup**, pas une feature. Le scope est délimité par "ce que v0.3.0 aurait dû livrer mais n'a livré qu'à moitié à cause du compromis single-user". Scope creep (e.g., "tant qu'on est dedans, ajoutons un new Category" ou "refactorons les tags") défait le propos.

## Risk register

| Risk | Mitigation |
|------|------------|
| **Filesystem `mv` détruit le watch state Jellyfin** | Snapshot ADR-6 pre-migration + restore procedure documentée. Jellyfin re-scan post-migration regenerate les hashes. Single-user accepts best-effort. |
| **Radarr/Sonarr API mutation casse les libs (e.g., movie disappears)** | API mutations sont individual per-item (pas de batch destructive). Si une mutation échoue, on s'arrête et on snapshot pour forensics. Phase 21 = operator-driven step-by-step, pas full auto. |
| **DC catch-all prune casse des téléchargements en cours** | Phase 22 audit qui torrents tournent encore avant prune. Migration des torrents en cours via `setLocation` côté qBit avant de prune le DC. |
| **arrconf reconciler bug supprime trop de stuff au prochain apply** | Triade Python + respx tests pour chaque prune step. `--dry-run` obligatoire avant first cluster apply. Snapshot ADR-6 pre-apply. |
| **Migration prend plus que 1j et bloque le download pipeline** | Migration faite app-par-app, downtime minimal. qBit reste opérationnel pendant les renames Radarr/Sonarr. |

## Traceability

| REQ-ID | Description | Phase | Status |
|--------|-------------|-------|--------|
| CAT-CLEANUP-01 | Audit legacy items/tags/paths | 20 | Planned |
| CAT-CLEANUP-02 | Filesystem + metadata migration | 21 | Planned |
| CAT-CLEANUP-03 | arrconf reconciler prune extensions | 22 | Planned |
| CAT-CLEANUP-04 | UAT dispositive end-to-end | 23 | Planned |

---
*Last updated: 2026-05-25 — v0.8.0 roadmap created (4 phases mapped 1-to-1 to 4 requirements; coverage 100%)*
