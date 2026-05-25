# Phase 20: Categories cleanup audit - Context

**Gathered:** 2026-05-25
**Status:** Ready for planning

<domain>
## Phase Boundary

**What this phase delivers** : Un livrable `20-AUDIT.md` exhaustif qui inventorie tout l'état legacy v0.2.0 résiduel dans la stack (Radarr movies + Sonarr series sur legacy root_folders, qBit torrents sur legacy save_paths, tags legacy, DC catch-all + Seerr animeTags routing + Jellyfin libs alignment), et qui résout **up-front** chaque mapping ambigu legacy → Category. Le 20-AUDIT.md devient le plan déterministe de migration que Phase 21 va exécuter step-by-step sans poser de question.

**Phase 20 est READ-ONLY** côté cluster — aucune mutation Radarr/Sonarr/qBit/Jellyfin API. Seules les écritures sont la production de `20-AUDIT.md` et son édition opérateur côté repo.

**Scope étendu (4 audits supplémentaires aux SC ROADMAP)** :
1. Radarr/Sonarr `download_clients` audit + décision sur le DC catch-all `qBittorrent` (id=1, no tags) — prune ou re-tag fallback
2. qBit categories validation (sanity check post-debug-session sonarr-rpm-400-categories d'hier)
3. Seerr `animeTags` routing audit (vérifier que ça résoud vers Categories tags et pas legacy `anime` id=3)
4. Jellyfin libraries Categories alignment validation (sanity check post-Phase 16 v0.5.0)

</domain>

<decisions>
## Implementation Decisions

### Format du livrable

- **20-AUDIT.md = Markdown narratif + YAML appendix structuré**
- Markdown : sections par app, tableaux par catégorie d'item (chacun avec colonnes `id`, `current_path/tag/save_path`, `target_category_path/tag/save_path`, `action`, `notes`)
- YAML appendix : mappings as data, parseable par Phase 21 plan/execute si besoin
- **Why** : best of both — humain-readable pour review opérateur, programmatic-friendly pour automation potentielle dans Phase 21

### Mapping resolution timing

- **Tous les mappings ambigus résolus up-front dans Phase 20**
- Phase 21 exécute sans poser de question — déterministe
- Operator-driven dans Phase 20 (cf. Operator interaction ci-dessous)
- **Why** : approche high-trust/low-automation cohérente avec le projet (CLAUDE.md §Idempotence, v0.3.0 migration runbook, v0.5.0 mkdir runbook). Phase 21 plus risqué (filesystem mv + API mutations) — minimiser les surprises mid-execution.

### Operator interaction shape (decisions ambiguës)

- **Pre-filled Markdown table operator edits in VS Code**
- Phase 20 génère un brouillon `20-AUDIT.md` avec colonne `target_category` pré-remplie selon best-guess :
  - `/media/films-family` → `/media/films-enfants` (auto-mapped per CLAUDE.md filesystem table)
  - `/media/films` (default bucket) → `/media/films` (no-op, default)
  - `/media/films` (operator-judged "récent") → `/media/nouveaux-films` (operator-decision needed, pre-filled `?`)
  - `/media/series` (default bucket) → `/media/series` (no-op, default)
  - `/media/series` (operator-judged "Émilie/Thomas/Garçons/Zoé") → `/media/series-emilie|thomas|garcons|zoe` (operator-decision needed, pre-filled `?`)
  - Etc.
- Op opérateur ouvre `20-AUDIT.md` dans VS Code, remplit les cellules `?` via Find/Replace ou édition directe
- Phase 20 finalize step verify no `?` cells remaining pre-commit (sed/grep gate)
- **Why** : bulk-friendly pour ~20-50 items, VS Code-friendly, pas de TUI custom à écrire (arrconf audit --interactive deferred to v0.9.0+), pas d'enfer AskUserQuestion×N

### Plan structure

- **Phase 20 = 1 plan holistique (20-A)**
- Pas de split en sub-plans (20-A/20-B/...) parce que l'audit est interconnecté (DC decision dépend de quels tags existent, qui dépendent de quels root_folders existent, etc.)
- Effort estimé révisé : **~1 jour plein** (vs "half-day" initial dans ROADMAP, à cause du scope étendu)
- **Why** : un audit est une vue unifiée du système ; le splitter en sub-plans crée des dépendances artificielles entre eux. Garde Phase 20 = 1 plan single-shot.

### Scope étendu — 4 audits supplémentaires (tous inclus)

Au-delà des SC ROADMAP (root_folders + tags + qBit save_paths) :

1. **DCs audit** : lister tous les `download_clients` Radarr/Sonarr ; pour chaque DC, ses `tags` + `priority` + `categoryName`. Identifier le DC catch-all (no tags) et autres DCs problématiques. **Décision attendue (à capturer dans 20-AUDIT.md, pas à exécuter)** : prune le catch-all (laisse seulement les Categories DCs) OU re-tag avec fallback tag `unsorted` priority=50.

2. **qBit categories validation** : lister toutes les categories qBit + leur `save_path`. Vérifier que chaque save_path = `/data/torrents/<category>/` (post-fix yesterday should be OK).

3. **Seerr animeTags routing** : lire `seerr.sonarr_service.animeTags` (clusterGET via Seerr API), résoudre les tag IDs vers les noms, vérifier qu'aucun n'est legacy `anime` (id=3) — devrait être Categories tags `series-zoe`/`series-garcons`/etc.

4. **Jellyfin libraries alignment** : lister les 10 libs Jellyfin via API ; pour chaque lib, ses `PathInfos` ; vérifier que chaque path = `/media/<category>/` exact (post-Phase 16 v0.5.0 should be OK).

### Read-only constraint (no cluster mutation)

- Phase 20 NE fait AUCUN write sur Radarr/Sonarr/qBit/Seerr/Jellyfin API
- Toutes les writes ADR-6 snapshot + mutations API sont **différées à Phase 21**
- Seules les écritures Phase 20 :
  - `.planning/phases/20-categories-cleanup-audit/20-AUDIT.md`
  - Commits + push

### Snapshot discipline

- Phase 20 = read-only → **pas de snapshot mandatory** (ADR-6 dit "avant toute écriture")
- Phase 21 (writes) sera responsable du snapshot pre/post — c'est sa préoccupation
- Optionnellement : opérateur peut décider de faire un snapshot baseline au démarrage Phase 20 pour avoir un "absolute zero" reference avant la chaîne v0.8.0. À sa discrétion.

### Claude's Discretion

Items non-couverts explicitement, à la discrétion de Claude pendant l'implémentation :

- Tri/ordre des items dans les tableaux 20-AUDIT.md (probablement par app puis par root_folder ou category)
- Niveau de détail du YAML appendix (verbose all-fields vs minimal-actionable)
- Code structure du audit script (probablement un nouveau verbe `arrconf audit` OU un script ad-hoc dans `tools/scripts/`)
- Si pre-existing test pattern (respx) est utilisé pour ce code
- Logging level pendant l'audit (INFO par default, DEBUG si verbose flag)

</decisions>

<specifics>
## Specific Ideas

### Filesystem migration mapping (baseline from CLAUDE.md)

La table CLAUDE.md "Filesystem migration: v0.2.0 flat → v0.3.0 Categories" est le baseline déterministe. Phase 20 valide cette table contre l'état réel cluster :

| v0.2.0 dir | v0.3.0 dir(s) | Auto-mappable ? |
|------------|---------------|------------------|
| `/media/series` | `/media/series` default + selective `mv` → series-emilie/thomas/garcons | NO — operator decision per item |
| `/media/anime` | `/media/series-zoe` (bulk move) | YES — auto-map |
| `/media/family` | `/media/series-garcons` (rename wholesale) | YES — auto-map |
| `/media/films` | `/media/films` default + selective `mv` → nouveaux-films | NO — operator decision per item |
| `/media/films-anime` | split Ghibli → series-zoe + films-zoe ; Disney/Pixar → films-animation-enfants | NO — operator decision per item |
| `/media/films-family` | `/media/films-enfants` (rename wholesale) | YES — auto-map |

### Sample data structure for 20-AUDIT.md

**Markdown section per app:**

```markdown
## Radarr

### Movies on legacy rootFolderPath (12 items)

| id | title | current_rootFolder | target_rootFolder | current_tags | target_tags | action | notes |
|----|-------|--------------------|--------------------|--------------|--------------|--------|-------|
| 11 | Les Alphas (2013) | /media/films | /media/films-enfants | [2, 4] | [7] | move + retag | family content per title |
| 17 | Inception (2010) | /media/films | ? | [2] | ? | TBD | operator decision: keep on films default OR move to nouveaux-films ? |
| ... |

### Download clients

| id | name | current_tags | current_priority | proposed_action | proposed_priority | proposed_tags |
|----|------|--------------|-------------------|-----------------|---------------------|----------------|
| 1 | qBittorrent | [] | 1 | prune OR re-tag | 50 | [unsorted] |
| 2 | qBittorrent - Movies | [2] | 1 | prune (legacy tag) | — | — |
| ... |
```

**YAML appendix:**

```yaml
audit_version: 1
generated_at: 2026-05-25T...
radarr:
  movies_to_migrate:
    - id: 11
      title: "Les Alphas (2013)"
      from:
        rootFolderPath: /media/films
        tags: [2, 4]
      to:
        rootFolderPath: /media/films-enfants
        tags: [7]
  download_clients:
    - id: 1
      name: qBittorrent
      decision: prune  # or "fallback" with proposed_priority + proposed_tags
sonarr: { ... }
qbittorrent:
  in_flight_torrents_to_relocate: [...]
seerr:
  animetags_route_check: OK  # or LEGACY_TAG_FOUND
jellyfin:
  libraries_pathinfo_check: OK  # or DRIFT_DETECTED
mapping_tables:
  legacy_path_to_category: { ... }
  legacy_tag_to_category: { ... }
```

### Verification gates pre-commit

Phase 20 finalize step verify (sed/grep):

- Aucune cellule `?` ou `TBD` non-résolue dans le Markdown
- YAML appendix parse OK (pas de syntax error)
- Tous les `to.rootFolderPath` du YAML existent dans `categories[]` paths de `arrconf.yml`
- Tous les `to.tags` du YAML existent dans Radarr/Sonarr tags API (les Categories tags doivent déjà exister)

</specifics>

<canonical_refs>
## Canonical References

Downstream agents (planner, executor) MUST read these :

### Project-level

- **`./CLAUDE.md`** §"Filesystem migration: v0.2.0 flat → v0.3.0 Categories" — baseline mapping table avec les décisions opérateur déjà documentées (anime → series-zoe wholesale, family → series-garcons, etc.)
- **`./CLAUDE.md`** §"Frontière arrconf / configarr" — table qui app gère quoi (confirme que tags + root_folders + download_clients sont arrconf scope)
- **`./CLAUDE.md`** §"Ce que tu NE dois PAS faire" — règles de discipline (snapshot avant test risqué = ADR-6, pas de prune par défaut, etc.)

### Phase-level

- **`.planning/REQUIREMENTS.md`** — CAT-CLEANUP-01 spec (cette phase)
- **`.planning/ROADMAP.md`** Phase 20 section — 4 SC déterminantes + dependencies
- **`.planning/MILESTONES.md`** v0.5.0 entry §"Side-quest unblock: Sonarr RPM 400 debug" — contexte du fix d'hier qui a créé les `/data/torrents/<cat>/` côté qBit (Phase 21 fera l'équivalent côté Radarr/Sonarr metadata)
- **`.planning/MILESTONES.md`** v0.5.0 entry Phase 16 — Jellyfin Categories-as-libs (10 libs déjà migrées, Phase 20 valide alignment)
- **`.planning/MILESTONES.md`** v0.7.0 entry — Media stack scope closure (9 apps fermées, Phase 20 sait qu'aucune app additionnelle n'arrive)

### Debug session — analogous fix

- **`.planning/debug/resolved/sonarr-rpm-400-categories.md`** — Side-quest fix d'hier qui a créé les `/data/torrents/<cat>/` manquants côté qBittorrent volume (8 `mkdir -p`). v0.8.0 fait l'équivalent metadata + filesystem côté NFS. Lire pour comprendre la posture "high-trust low-automation runbook" qui s'applique aussi à Phase 21.

### State

- **`.planning/STATE.md`** — current milestone v0.8.0, Phase 20 not started, no prior CONTEXT
- **`.planning/PROJECT.md`** — Current Milestone v0.8.0 section + carry-forward backlog v0.9.0+

### v0.3.0 / v0.4.0 historical context

- **`.planning/milestones/v0.3.0-phases/09-categories-data-model-chart-initcontainer/09-CONTEXT.md`** — Categories first-class introduction context (decisions D-09-* sur le shape de `categories[]`)
- **`.planning/milestones/v0.3.0-phases/10-categories-6-app-propagation/10-CONTEXT.md`** — Categories propagation decisions across 6 apps
- **`.planning/milestones/v0.4.0-phases/12-*/*-CONTEXT.md`** — Categories deprecation (retrait `merge_with_manual`) decisions

### Cluster state baselines (read-only refs)

- **`snapshots/baseline-2026-05-22/`** ou plus récent — état pre-v0.5.0 sur les 6 apps. Phase 20 audit cluster current state, peut comparer avec ce baseline pour drift detection (out of scope strict mais nice-to-have).

</canonical_refs>

<deferred>
## Deferred Ideas

Items mentionnés / surfacés pendant la discussion mais hors scope Phase 20 :

- **`arrconf audit --interactive` CLI subcommand** — Nouveau verbe arrconf pour TUI/CLI interactive audit. Plus de DX pour audits futurs mais ajoute du code non-scope Phase 20. → Defer à v0.9.0+ si l'expérience Phase 20 montre que les Markdown-edit en VS Code n'est pas idéal.
- **Snapshot drift detection** — comparer cluster current state vs committed `snapshots/baseline-*/` pour identifier où ça a dérivé. Nice-to-have analytic, hors scope strict de Phase 20. → Defer.
- **Automated migration script** — Phase 21 fait operator-driven step-by-step. Si on en a marre, un futur "arrconf migrate-categories --from=v0.2.0 --to=v0.3.0" pourrait automatiser. → Defer v0.9.0+ (probable jamais — usage uniquement one-shot).
- **Compensation pour les watch states perdus** — Si le `mv` Phase 21 perd les watch states Jellyfin, une étape de re-import depuis backup pourrait restaurer. → Accepted as best-effort per single-user homelab discipline.

Ces items vont dans le `.planning/PROJECT.md` v0.9.0+ carry-forward si l'opérateur veut les tracker.

</deferred>

<scope_creep>
## Scope Creep — explicitly redirected

Aucun scope creep n'a été tenté pendant la discussion. Le user a maintenu la discipline scope cleanup-only (cf. v0.7.0 scope closure decision + REQUIREMENTS.md "Reasoning" section). Si pendant Phase 20 audit l'opérateur découvre des items qui pourraient être renommés / réorganisés différemment, capturer comme deferred ideas — ne PAS les inclure dans le migration plan Phase 20→21.

</scope_creep>

---

*Last updated: 2026-05-25 — Phase 20 context captured, ready for /gsd-plan-phase 20*
