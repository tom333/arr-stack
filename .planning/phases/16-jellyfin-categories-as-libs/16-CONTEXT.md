# Phase 16 — Jellyfin Categories-as-libs — CONTEXT

**Phase:** 16
**Name:** Jellyfin Categories-as-libs
**Milestone:** v0.5.0
**Status:** Context gathered, ready for `/gsd-plan-phase 16`
**Date:** 2026-05-24

## Domain

Refactor le générateur Jellyfin (`tools/arrconf/arrconf/generators/categories.py::generate_jellyfin_libraries()`) pour émettre **10 `JellyfinLibrary` entries** — une par `categories[]` — au lieu des 2 super-libs `Séries` + `Films` actuelles. Étendre le reconciler Jellyfin (`tools/arrconf/arrconf/reconcilers/jellyfin.py::_reconcile_libraries()`) pour qu'il **crée les libs manquantes** (jusqu'ici délégué à l'opérateur via UI). Reverse D-07-LIB-01 (`prune: false` hardcoded) → opt-in `prune` piloté par YAML, comme tous les autres reconcilers. Cutover idempotent : le YAML existant a déjà `display` pour chaque category, donc pas de migration de config opérateur.

Driver utilisateur : visibilité native des 10 Categories dans tous les clients Jellyfin (web UI, Swiftfin sur Apple TV, JellyCon sur le mini-PC LibreELEC du salon), au lieu d'avoir 2 super-libs qui aplatissent l'organisation.

## Decisions

### D-16-LIB-CREATE-01 — arrconf devient propriétaire du cycle de vie complet des libs

**Décidé :** Le reconciler Jellyfin POST `/Library/VirtualFolders` pour créer les libs manquantes depuis l'output du générateur. arrconf gère désormais création + paths (au lieu de paths-only).

**Conséquences :**
- Phase 16 introduit un nouvel endpoint dans le client Jellyfin (POST `/Library/VirtualFolders`). Body shape à pinner par le researcher (probable : `?name=<Name>&collectionType=<type>&paths=<json-array>&refreshLibrary=false` plus possiblement `libraryOptions` JSON body). Pitfall : Jellyfin l'envoie historiquement en query params, pas JSON body.
- Le `library_missing_skip` warning du reconciler actuel (jellyfin.py L136-143) devient mort code → à supprimer ou à transformer en `library_create` action.
- Plus de bootstrap manuel UI nécessaire pour onboarder une nouvelle Category. C'est cohérent avec l'esprit Categories first-class.

### D-16-LIB-NAME-01 — Nom affiché des libs = `categories[].display`

**Décidé :** `JellyfinLibrary.name` (qui sert d'identifiant de matching + de label affiché côté Jellyfin) prend la valeur de `categories[].display`. Exemples concrets depuis l'arrconf.yml live : `Séries`, `Séries - Émilie`, `Séries - Thomas`, `Séries - Garçons`, `Séries - Zoé`, `Films`, `Nouveaux Films`, `Films - Enfants`, `Films - Animation Enfants`, `Films - Zoé`.

**Conséquences :**
- Le `categories[].name` (technique : `series-zoe`, `films-enfants`, etc.) reste l'identifiant de path filesystem (`/media/<name>`). Aucun changement filesystem.
- Coïncidence opérationnelle : `categories[0]` (name=`series`, display=`Séries`) et `categories[5]` (name=`films`, display=`Films`) ont des `display` identiques aux 2 super-libs legacy actuels (`Séries`, `Films`). Cela rend le cutover **élégant** — voir D-16-PRUNE-01 ci-dessous.

### D-16-PRUNE-01 — Reverse D-07-LIB-01 : prune opt-in via YAML

**Décidé :** Le flag `prune:` de la section `jellyfin.libraries` dans `arrconf.yml` devient effectif (au lieu d'être ignoré). Le hardcoded `prune: false` du reconciler (Phase 7 D-07-LIB-01) saute. Comportement aligné avec qBit/Sonarr/Radarr/Prowlarr (opt-in par section).

**Conséquences :**
- Migration cutover, scénario nominal :
  1. Opérateur PR sur arr-stack avec `jellyfin.libraries.prune: true` + image bump 0.7.0→0.8.0.
  2. ArgoCD sync → CronJob arrconf tourne contre cluster :
     - **Création** : 8 nouvelles libs (`Séries - Émilie`, `Séries - Thomas`, `Séries - Garçons`, `Séries - Zoé`, `Nouveaux Films`, `Films - Enfants`, `Films - Animation Enfants`, `Films - Zoé`) via POST `/Library/VirtualFolders`.
     - **Reshape** : les 2 libs legacy `Séries` et `Films` matchent par nom les nouvelles `Séries` (cat `series`) et `Films` (cat `films`). Leurs PathInfos passent de 5 paths chacune à 1 path chacune (`/media/series`, `/media/films`). Nécessite un DELETE de PathInfo — voir items recherche.
     - **Prune libs** : si d'autres libs hors-output existent (créées manuellement à des fins de test), prune=true les supprime. Pas de side-effect attendu sur le cluster actuel (juste `Séries` + `Films`).
  3. Opérateur remet `prune: false` dans `arrconf.yml` (PR séparé) une fois le cutover validé en UAT.
- Side-effect honnête : la protection des libs user-added saute pendant la fenêtre prune=true. C'est OK en homelab single-tenant — opérateur est conscient avant d'activer le flag.

### D-16-PATH-DELETE-01 — Endpoint DELETE PathInfo à wirer

**Décidé :** Le reconciler doit gagner la capacité de **supprimer un PathInfo d'une lib existante** pour permettre le reshape des libs `Séries` et `Films` legacy (5 paths → 1 path). Aujourd'hui le reconciler ne fait que POST add (Phase 7 D-07-LIB-01 ban explicite des DELETEs).

**Conséquences :**
- Endpoint Jellyfin à pinner par le researcher : probable `DELETE /Library/VirtualFolders/Paths?name=<Name>&path=<URL-encoded-path>` (cf doc OpenAPI Jellyfin 10.11.x).
- Le DELETE de PathInfo est **gated par `prune: true`** au niveau de la section `jellyfin.libraries` (cohérent avec D-16-PRUNE-01). Quand prune=false (default), arrconf n'enlève jamais de paths — il ne fait qu'ajouter, comme aujourd'hui.
- À noter : Pitfall 8 (PathInfos = source de vérité, pas Locations) reste valable — diff path-side se fait toujours sur PathInfos.

### D-16-JELLYCON-UAT-01 — JellyCon UAT carry-forward

**Décidé :** Phase 16 close-out valide uniquement la visibilité des 10 libs dans **Jellyfin web UI**. La validation JellyCon sur LibreELEC est documentée en scenario dans `16-HUMAN-UAT.md` mais **non-bloquante** pour fermer la Phase. Sera cochée plus tard par l'opérateur quand JellyCon sera installé (planification opérateur, hors arr-stack).

### D-16-COLLECTIONTYPE-01 — Mapping `kind` → `CollectionType` inchangé

**Pré-décidé Phase 7, repris tel quel :** `categories[].kind == "series"` → `CollectionType = "tvshows"`. `categories[].kind == "movies"` → `CollectionType = "movies"`. Aucun changement.

## Code Context

### Files to modify (probable scope)

- **`tools/arrconf/arrconf/generators/categories.py`** (line 192-202) — `generate_jellyfin_libraries()` boucle sur `cfg.categories` pour émettre un `JellyfinLibrary` par Category, avec `name=cat.display` + `collection_type` mappé depuis `cat.kind` + `paths=[cat.base_path]`.
- **`tools/arrconf/arrconf/reconcilers/jellyfin.py`** (line 107-180+) — `_reconcile_libraries()` étendu pour :
  - POST `/Library/VirtualFolders` pour les libs absentes (au lieu du `library_missing_skip`).
  - DELETE de PathInfo en surplus si `section.prune == True` (au lieu de tout préserver).
  - DELETE de lib entière si `section.prune == True` et lib hors-output (au lieu de hardcoded false).
- **`tools/arrconf/arrconf/resources/jellyfin/library.py`** (line 25-37) — `JellyfinLibrary` model probablement inchangé. Le `name` field aura juste une nouvelle sémantique (= `display` du Category source). Documenter dans le docstring.
- **`charts/arr-stack/files/arrconf.yml`** — la section `jellyfin.libraries.prune` reste à `false` par défaut. L'opérateur fait le flip `true` puis `false` en deux PRs successifs lors du cutover.
- **`charts/arr-stack/values.yaml`** — `arrconf.image.tag` co-bump `0.7.0 → 0.8.0`.

### Tests to add/update

- Unit tests générateur : 1 fixture YAML 10-Category → assert 10 `JellyfinLibrary` produites, 5 `tvshows` + 5 `movies`, names matchent les `display` strings exacts.
- Unit tests reconciler (respx-mocked) :
  - Création d'une lib absente → POST `/Library/VirtualFolders` avec body correct.
  - Add path à lib existante (path absent) → POST `/Library/VirtualFolders/Paths` (chemin actuel).
  - Path already present → `library_path_already_present` (idempotence — comportement actuel).
  - Lib hors-output + `prune: true` → DELETE lib entière.
  - Path en surplus + `prune: true` → DELETE PathInfo.
  - `prune: false` → aucune suppression (preserve comportement legacy par défaut).

### Existing patterns to reuse

- **Match-by-name + idempotence shim Pitfall 2** : pattern existant (jellyfin.py L130-153). À preserver verbatim pour les libs in-output.
- **Pre-merge `*Derived` dataclass dispatch** (Phase 12-A) : le générateur retourne `list[JellyfinLibrary]`, le reconciler le reçoit en paramètre. Pattern déjà en place — pas d'ajout de signature.
- **Chart-pin co-bump** (CLAUDE.md "Release pin co-bump pattern") : `arrconf.image.tag` co-bumped dans le même commit que le code Python touchant `tools/arrconf/**`. Minor bump 0.7.0 → 0.8.0 (nouvelle feature, pas bugfix).

## Canonical Refs

- [`.planning/ROADMAP.md`](../../ROADMAP.md) — Phase 16 entry (SC#1-5)
- [`.planning/REQUIREMENTS.md`](../../REQUIREMENTS.md) — REQ-jellyfin-categories-as-libs
- [`.planning/PROJECT.md`](../../PROJECT.md) — Current Milestone section + ADR-7 (single instance + tags)
- [`CLAUDE.md`](../../../CLAUDE.md) — "Release pin co-bump pattern" + "Frontière arrconf/configarr" tableau (jellyfin.libraries owned by arrconf)
- [`tools/arrconf/arrconf/generators/categories.py`](../../../tools/arrconf/arrconf/generators/categories.py) — current `generate_jellyfin_libraries()` line 192
- [`tools/arrconf/arrconf/reconcilers/jellyfin.py`](../../../tools/arrconf/arrconf/reconcilers/jellyfin.py) — current `_reconcile_libraries()` line 107
- [`tools/arrconf/arrconf/resources/jellyfin/library.py`](../../../tools/arrconf/arrconf/resources/jellyfin/library.py) — `JellyfinLibrary` + `PathInfo` models
- [`tools/arrconf/arrconf/resources/categories.py`](../../../tools/arrconf/arrconf/resources/categories.py) — `Category` model (`name`, `kind`, `profile`, `display`, `base_path`)
- [`charts/arr-stack/files/arrconf.yml`](../../../charts/arr-stack/files/arrconf.yml) — `categories:` block (10 entries) + `jellyfin.libraries.prune` flag
- [`.planning/milestones/v0.3.0-phases/09-categories-data-model-chart-initcontainer/`](../../milestones/v0.3.0-phases/09-categories-data-model-chart-initcontainer/) — Phase 9 historical Categories data model context
- [`.planning/milestones/v0.2.0-phases/07-reconciler-jellyfin/`](../../milestones/v0.2.0-phases/07-reconciler-jellyfin/) — Phase 7 historical Jellyfin reconciler context (D-07-LIB-01 / D-07-LIB-02 origin)
- Project memory: `project_v050_jellyfin_categories_pivot.md` (decision rationale)
- Project memory: `project_categories_vision.md` (Categories first-class vision)

## Research Items (for `gsd-phase-researcher`)

1. **Jellyfin POST `/Library/VirtualFolders` request shape** — Jellyfin 10.11.x OpenAPI spec. Concrètement : sont-ce des query params (`?name=&collectionType=&paths=&refreshLibrary=false`) ou JSON body (`{Name, CollectionType, Paths[], LibraryOptions}`) ? Pitfall : la doc varie entre v10.10 et v10.11. Pinner depuis le swagger live de notre instance (`http://jellyfin.selfhost.svc.cluster.local:8096/api-docs/swagger`) si nécessaire.
2. **Jellyfin DELETE PathInfo** — endpoint exact. Hypothèse : `DELETE /Library/VirtualFolders/Paths?name=<Name>&path=<encoded>`. Vérifier la sémantique : supprime un path d'une lib SANS détruire la lib elle-même.
3. **Jellyfin DELETE lib entière** — endpoint exact. Hypothèse : `DELETE /Library/VirtualFolders?name=<Name>&refreshLibrary=false`. Vérifier que cela ne déclenche pas de file-deletion (on garde les fichiers sur NFS quoi qu'il arrive).
4. **Watched state survival pendant cutover** — Quand `Séries` perd 4 paths (qui partent vers de nouvelles libs `Séries - Émilie`, etc.), Jellyfin considère-t-il les items comme "removed" + "added" (perte du watched state) ou comme "moved" (préservé) ? Jellyfin matche les items par `ProviderIds` (TVDB/TMDB) → en théorie watched state survit. À confirmer dans la research.

## Deferred Ideas

- **REQ-jellyfin-collections** (Collections auto-générées par Category) — initialement option B dans la discussion Kodi du 2026-05-24. Skippée car REQ-jellyfin-categories-as-libs résout déjà le besoin visibilité. Si Phase 16 livre clean, cette REQ devient surplus définitif. Sinon, à re-évaluer post-Phase-16.
- **Library Options per-Category** (preferred metadata language, type options, realtime monitor) — D-07-LIB-02 a explicitement scopé OUT ces fields pour préserver le contrôle UI opérateur. Inchangé en v0.5.0 ; libs créées avec defaults Jellyfin pour `LibraryOptions`. Si l'opérateur veut tuner finement, c'est via Jellyfin UI.
- **Idempotence dispositive SC#5-style** (post-merge live cluster sweep) — Non requis ce milestone (cf ROADMAP). La SC#2 "second `arrconf apply` emits 0 plan_action" suffit pour Phase 16. Pas de plan dispositive séparé.

## Open Items for Plan Phase

- [ ] Plan structure : 1 wave avec 2-3 plans (generator + reconciler + tests/docs) vs 2-3 waves séquentielles. Recommandation : un seul plan **16-A** (refactor groupé : generator + reconciler + tests + co-bump + snapshot before/after) — la surface est petite (4 fichiers à toucher, ~150 LOC), pas de waterfall nécessaire.
- [ ] Pré-cutover snapshot baseline obligatoire (CLAUDE.md "Workflow snapshot (CRITIQUE)") : `tools/snapshot/snapshot.sh --apps jellyfin --output snapshots/before-phase-16-2026-05-24/` AVANT le merge PR. Capture la shape actuelle des libs (Séries 5 paths + Films 5 paths).
- [ ] HUMAN-UAT scenarios à rédiger pendant plan-phase :
  1. Jellyfin web UI montre 10 libs (mandatory close).
  2. Watched state préservé sur ≥ 3 séries après cutover (mandatory close).
  3. JellyCon LibreELEC top-level browse montre 10 libs (carry-forward, non-bloquant).
  4. Opérateur remet `prune: false` post-cutover (mandatory close — évite drift sur libs ajoutées manuellement plus tard).

## Locked Boundaries

- ❌ **Pas de migration filesystem** — les 10 `/media/<name>` existent depuis Phase 9.
- ❌ **Pas de modification de la frontière arrconf/configarr** — quality_profiles/custom_formats/quality_definitions/media_naming intouchés (ADR-5).
- ❌ **Pas de Jellyfin Collections** — explicitly out of scope (deferred to v0.6.0 si nécessaire).
- ❌ **Pas de touche au reconciler `_reconcile_users()` ni `_reconcile_server_config()` ni `_reconcile_plugins()`** — uniquement `_reconcile_libraries()`.
- ❌ **Pas de migration auto du watched state** — comportement par défaut Jellyfin (match par ProviderIds) assumé suffisant. Si UAT révèle des pertes, c'est un follow-up post-Phase-16.

## Open Questions

Aucune restante après les 4 AskUserQuestion résolues. Le researcher pinnera les 4 items Research listés ci-dessus pendant `/gsd-plan-phase 16`.
