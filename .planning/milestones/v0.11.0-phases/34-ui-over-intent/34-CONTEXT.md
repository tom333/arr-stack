# Phase 34: UI over intent - Context

**Gathered:** 2026-06-07
**Status:** Ready for planning

<domain>
## Phase Boundary

`arrconf-ui` pivote pour faire de `intent.yml` la **seule source éditable**.
Aujourd'hui l'UI édite directement `arrconf.yml` + `configarr.yml` via des
formulaires schema-mirror — or depuis les Phases 32/33 ces deux fichiers sont
GÉNÉRÉS depuis `intent.yml`, donc l'UI édite des fichiers générés (stale).
Cette phase corrige ça : l'opérateur édite `intent.yml`, le picker TRaSH/QP
(v0.9.0) se rebranche sur le flux intent, et un panneau diff montre la
matérialisation générée (`arrconf.yml` + `configarr.yml`) avant commit.

**En scope :** formulaire d'édition `intent.yml` unique ; retrait des
formulaires d'édition legacy `arrconf.yml`/`configarr.yml` (réduits à
read-only inspect) ; ré-ancrage du picker CF/QP sur `profile_definitions` ;
panneau diff de la sortie générée ; save = écrit intent + régénère les deux
fichiers.

**Hors scope :** modification des générateurs eux-mêmes (Phases 32/33, figés) ;
toute application live de config (reste `arrconf apply`/configarr/ArgoCD) ;
co-bump `arrconf.image.tag` (phase touche `tools/arrconf-ui/**` uniquement —
l'image cluster arrconf n'est PAS modifiée).
</domain>

<decisions>
## Implementation Decisions

### Source du diff généré (UI-04)
- **D-34-01:** Le backend **importe les générateurs** `generate_arrconf_yml` +
  `generate_configarr_yml` depuis `arrconf.generators` directement. `arrconf`
  est **déjà une dépendance editable** d'`arrconf-ui` (`pyproject.toml`:
  `arrconf = {path="../arrconf", editable=true}` — fournit déjà
  `RootConfig`/`load_config`). Sortie byte-identique à `arrconf generate` par
  construction → SC#3/SC#4 satisfaits trivialement. (Rejeté : subprocess
  `arrconf generate` = complexité temp-dir/env sans gain vu la dep editable ;
  réimplémentation = double-source, drift.)
- **D-34-02:** Le panneau diff compare **new-generated (depuis intent édité) vs
  current on-disk generated**, rendu en **diff texte unifié** (ligne-à-ligne
  YAML) des fichiers générés. Trivial depuis la sortie string des générateurs ;
  montre les bytes exacts qui seront commités — "materialization preview"
  honnête. (Rejeté : réutiliser le differ sémantique field-level — abstrait le
  contenu exact du fichier ; toggle des deux — YAGNI.)

### Construction du formulaire intent (UI-01)
- **D-34-03:** **Schema-mirror baseline + sections spéciales.** Réutiliser la
  machinerie D-13 schema-driven existante via un nouveau `/api/intent/schema`
  alimenté par `IntentConfig.model_json_schema()` (CLI `intent-schema-gen`
  existe déjà) → auto-forms pour `categories`/`sagas`/`apps`/`tools`. Deux
  sections résistent aux auto-forms et sont spécial-casées :
  `profile_definitions` → picker TRaSH (D-34-05) ; `configarr` → bloc raw/opaque
  (pass-through verbatim, Phase 33 D-33-07/08). (Rejeté : pure schema-mirror —
  profile_definitions + configarr rendent mal ; hand-crafted total — diverge du
  pattern établi, plus de maintenance.)

### Disposition des formulaires legacy (UI-02)
- **D-34-04:** **Retirer les formulaires d'édition + endpoints PUT** de
  `arrconf.yml` et `configarr.yml`. Garder les **GET en read-only inspectors**
  alimentant le panneau diff/matérialisation uniquement. `ConfigError` si
  l'opérateur tente d'éditer un fichier généré. Honore le hard-cut (pas
  d'édition de fichier généré) tout en préservant la vue "sortie générée".
  Conséquence : le bloc `intent.configarr` est édité via la section opaque du
  formulaire intent (D-34-03), PAS via des formulaires configarr repurposés.
  (Rejeté : full removal des GET — perd la vue structurée pour le diff ;
  repurpose des forms configarr sur intent.configarr — édition structurée d'un
  bloc opaque pass-through, risque drift.)

### Ré-ancrage du picker TRaSH (UI-03)
- **D-34-05:** **Picker par profil**, à l'intérieur de l'éditeur de chaque
  `profile_definitions[name]`. Sélectionner des CFs ajoute des lignes
  `{trash_id, score}` dans la liste `custom_formats` de ce profil (calque exact
  du schéma Phase 33 D-33-06) ; sélection QP/recyclarr alimente le corps du
  profil. Les endpoints `/api/trash/*` existants (v0.9.0) sont **réutilisés
  tels quels** (catalogue lu par kind) — seul le point de montage frontend
  bouge. (Rejeté : picker global avec sélecteur de profil cible — indirection
  + locality faible ; browse-only + saisie manuelle — contredit "intégré au
  flux d'édition" de UI-03.)

### Sémantique de sauvegarde (SC#4)
- **D-34-06:** **Save écrit `intent.yml` ET régénère les deux fichiers.** Le
  save persiste intent.yml puis lance les générateurs importés pour (ré)écrire
  `arrconf.yml` + `configarr.yml` sur disque — le même appel qui a produit le
  diff preview. Disque cohérent, garde CI `generate-idempotence` verte,
  diff-affiché == fichiers-écrits (SC#4 par construction). (Rejeté : save intent
  only — fichiers générés stale sur disque jusqu'à un `generate` séparé, garde
  CI échoue ; générés git-ignorés — contredit le pattern établi, ils sont
  commités + gardés en CI.)

### Claude's Discretion
- Structure exacte des composants Svelte (découpage, réutilisation de
  `SectionDoc`/`DiffPanel`).
- Approche/lib de rendu du diff texte unifié côté frontend.
- Nommage exact des nouveaux endpoints (`/api/intent`, `/api/intent/schema`,
  `/api/intent/diff`, `/api/intent/generate` ou save combiné) — cohérent avec
  les conventions `app.py` existantes.
- Forme exacte des erreurs (`ConfigError` → HTTP status) sur tentative
  d'édition d'un fichier généré.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope + requirements
- `.planning/ROADMAP.md` §"Phase 34: UI over intent" — goal, success criteria 1-4, UI hint=yes, no-co-bump note.
- `.planning/REQUIREMENTS.md` — UI-01..04 traçabilité.

### Frontière / invariants (Phases 32-33, à préserver)
- `.planning/phases/33-configarr-yml-generation/33-CONTEXT.md` — D-33-06 (custom_formats par profile_definition: `{trash_id|name, score}`), D-33-07/08 (configarr pass-through verbatim opaque dans `intent.configarr`).
- `.planning/phases/32-categories-migration-hard-cut/32-CONTEXT.md` — hard-cut, intent.yml = seule source hand-edited.
- `spec.md` §11 (ADR-5) + `CLAUDE.md` §"Frontière arrconf / configarr" — configarr seul appliqueur TRaSH ; arrconf-ui ne dial JAMAIS une API quality_profiles/custom_formats.

### Backend arrconf-ui (à modifier)
- `tools/arrconf-ui/arrconf_ui/app.py` — endpoints actuels : `/api/config` (GET/PUT arrconf.yml), `/api/diff`, `/api/schema`, `/api/configarr/config` (GET/PUT), `/api/configarr/diff`, `/api/configarr/schema`, `/api/trash/{custom-formats,quality-profiles,recyclarr-templates}`. Point d'injection des nouveaux endpoints intent + retrait des PUT legacy.
- `tools/arrconf-ui/pyproject.toml` — `arrconf` déjà dep editable (clé pour D-34-01).
- `tools/arrconf-ui/arrconf_ui/diff.py` + `configarr_diff.py` — differs sémantiques existants (référence ; D-34-02 préfère un diff texte des fichiers générés).
- `tools/arrconf-ui/arrconf_ui/io.py` + `locator.py` — I/O fichiers + résolution de chemins.

### Générateurs arrconf (à importer, NE PAS modifier)
- `tools/arrconf/arrconf/generators/intent.py` — `generate_arrconf_yml`, `sort_dict`.
- `tools/arrconf/arrconf/generators/configarr.py` — `generate_configarr_yml` (Phase 33).
- `tools/arrconf/arrconf/__main__.py` `generate()` — référence du comportement à reproduire (intent → arrconf.yml + configarr.yml + qbit_manage).
- `tools/arrconf/arrconf/schema_gen.py` `write_intent_schema` + `IntentConfig.model_json_schema()` — source du schéma pour `/api/intent/schema`.
- `tools/arrconf/arrconf/intent_config.py` — `IntentConfig` (categories, sagas, apps, tools, profile_definitions, configarr).

### Frontend arrconf-ui (à modifier)
- `tools/arrconf-ui/web/src/App.svelte` (266 lignes) — forms actuels arrconf+configarr, `DiffPanel`, `diffCount`, `confirmSave`, switching tabs avec garde unsaved-diff.
- `tools/arrconf-ui/web/src/{api.ts,schema.ts,types.ts,constants.ts}` — couche API + schema-driven forms.

### CI
- `.github/workflows/tests.yml` — garde `generate-idempotence` (D-34-06 doit la garder verte) ; jobs `arrconf-ui-backend` (triade) + `arrconf-ui-frontend`.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- D-13 schema-driven form machinery (`/api/schema` → `SectionDoc` + `schema.ts`)
  — réutilisable tel quel pour intent via `/api/intent/schema`.
- `DiffPanel` Svelte + `confirmSave` flow + `diffCount` chip — déjà en place,
  à rebrancher sur le diff intent→généré.
- Endpoints `/api/trash/*` (v0.9.0) — réutilisés sans changement (lecture
  catalogue baké par kind).
- `arrconf` editable dep — import direct de `RootConfig`/`load_config` déjà
  fait ; étendre à `generate_arrconf_yml`/`generate_configarr_yml` +
  `IntentConfig`/`load_intent`/`write_intent_schema`.

### Established Patterns
- Garde CI `generate-idempotence` (`generate --check` + `git diff --exit-code`)
  — D-34-06 (save régénère) la maintient verte.
- ADR-5 : arrconf-ui n'a JAMAIS appelé une API *arr (base_url stocké/echoé
  verbatim, jamais dialé — voir commentaire SC#3 dans app.py). À préserver.
- `extra="forbid"` sur `IntentConfig` — le formulaire ne doit produire que des
  champs valides du schéma.

### Integration Points
- `app.py` : ajouter `/api/intent` (GET/PUT/save) + `/api/intent/schema` +
  `/api/intent/diff` (ou diff intégré au save preview) ; retirer les PUT
  `/api/config` + `/api/configarr/config`, réduire leurs GET en read-only.
- Save backend : `load_intent` → écrire intent.yml → `generate_*` → écrire
  arrconf.yml + configarr.yml (mêmes chemins que la CLI).
- Frontend : monter le picker dans l'éditeur `profile_definitions`.
</code_context>

<specifics>
## Specific Ideas

- Cas pivot du picker : `profile_definitions[name].custom_formats` accepte
  `{trash_id, score}` (calque D-33-06) ; le picker écrit des références
  trash_id, PAS des corps CF expansés (le catalogue baké sert au picker
  uniquement, cf. Phase 33).
- Le diff texte unifié doit montrer arrconf.yml ET configarr.yml (deux fichiers
  générés), idéalement séparés/labellisés.
- `intent.configarr` édité comme bloc raw/opaque (pas de form structuré) — c'est
  du pass-through verbatim.
</specifics>

<deferred>
## Deferred Ideas

- UI-SPEC formel : la phase a `UI hint=yes`. Envisager `/gsd-ui-phase 34` pour
  un contrat de design visuel avant le plan (next-step, pas un blocage).
- Édition structurée du bloc `configarr` pass-through (au-delà du raw editor) —
  future si l'opérateur en exprime le besoin.

### Reviewed Todos (not folded)
- "Migrer médiathèque existante vers buckets Categories v0.3.0"
  (`.planning/todos/pending/2026-05-27-...`, score 0.6) — tâche ops/filesystem
  (déplacement de fichiers média), sans rapport avec l'édition UI de l'intent.
  Reste un runbook opérateur indépendant.

</deferred>

---

*Phase: 34-ui-over-intent*
*Context gathered: 2026-06-07*
