# Phase 33: configarr.yml generation - Context

**Gathered:** 2026-06-05
**Status:** Ready for planning

<domain>
## Phase Boundary

`arrconf generate` émet les sections `quality_profiles` + `custom_formats` de
`charts/arr-stack/files/configarr.yml` à partir de l'intent, par profil de
catégorie. Tout le reste de configarr.yml (urls, `customFormatDefinitions`,
`base_url`/`api_key`, `media_naming`, `quality_definition`, `templates`,
`includes`, refs Recyclarr) est **pass-through verbatim** depuis un bloc dédié
`intent.configarr`. ADR-5 reste préservé par construction : `generate` n'écrit
qu'un fichier, n'appelle jamais les APIs `quality_profiles`/`custom_formats`,
et `configarr` reste le seul appliqueur TRaSH.

**En scope :** générateur pur `intent → configarr.yml`, bloc `profile_definitions`
+ bloc `intent.configarr` pass-through dans le schéma intent, garde CI
`generate-idempotence` étendue à configarr.yml, co-bump `arrconf.image.tag`.

**Hors scope :** UI sur intent (Phase 34) ; toute application live de profils
(reste configarr/ArgoCD) ; génération de `media_naming`/`quality_definition`/
`customFormatDefinitions` (pass-through).
</domain>

<decisions>
## Implementation Decisions

### Source des définitions de profil
- **D-33-01:** Les corps QP complets vivent dans un **bloc `profile_definitions`
  dédié de `intent.yml`** (nouveau champ du schéma `IntentConfig`). L'opérateur
  écrit chaque profil unique une fois ; `generate` expanse en un QP configarr par
  définition. `intent.yml` reste le seul fichier hand-edited. (Rejeté : templates
  built-in en code Python → rebuild image pour changer un profil ; pass-through
  verbatim → annule la génération par catégorie.)
- **D-33-02:** Une `profile_definition` est définie **1× par nom**, éligible aux
  **deux** instances. Pas de définition par (profil × kind). KISS, cohérent avec
  l'état actuel (3 profils structurellement identiques sonarr/radarr).
  - **Contrainte (pour research) :** les corps de profil doivent rester dans le
    sous-ensemble commun de noms de qualités Sonarr ∩ Radarr (ex. `Remux-1080p`
    existe côté films mais pas séries). Déjà prouvé sûr par la config prod
    actuelle (mêmes 3 profils des 2 côtés, en service).
- **D-33-03:** `Family` est écrit comme une **définition indépendante complète**,
  même s'il est aujourd'hui byte-équivalent à `MULTi.VF` (D-05-FAM-01). Pas
  d'alias `clone_of`. Modèle mental simple, divergence future (règles enfants)
  triviale, zéro logique de résolution d'alias.

### Nommage des profils & routing instance
- **D-33-04:** Les noms de profils **restent `MULTi.VF` / `Anime` / `Family`**
  (clés de `profile_definitions` = noms émis dans configarr = noms des QP live
  Sonarr/Radarr). `category.profile` est renommé `general→MULTi.VF`,
  `family→Family`, `anime→Anime` dans `intent.yml` lors de cette phase. **Zéro
  migration live** : les QP existants gardent leur nom, aucun média n'est
  réassigné. (Rejeté : adopter general/family/anime → configarr crée de nouveaux
  profils → réassignation manuelle de tous les médias Sonarr/Radarr.)
- **D-33-05:** Routing : une `profile_definition` est émise dans une instance
  quand **≥1 catégorie de ce kind** la référence — `kind=series → sonarr`,
  `kind=movies → radarr`. Pas de profils morts émis. (Inféré pendant discuss,
  pas un choix utilisateur explicite — le planner peut affiner la règle exacte.)

### Custom formats + scoring par profil
- **D-33-06:** Chaque `profile_definition` porte une liste
  `custom_formats: [{trash_id|name, score}]`. `generate` émet les `custom_formats`
  configarr avec `assign_scores_to` ciblant ce profil. Calque le modèle natif
  `assign_scores_to` de configarr et gère naturellement le cas VOSTFR (même CF,
  scores différents par profil : MULTi.VF -10000, Anime +50, Family -10000).
  (Rejeté : liste globale + matrice de scores → schéma plus complexe à éditer.)
  - **Pour research :** CF TRaSH référencés par `trash_id` depuis le catalogue
    baké en Phase 27 ; CF locaux référencés par nom (définis dans le
    `customFormatDefinitions` pass-through).

### Frontière généré / pass-through
- **D-33-07:** **Seuls `quality_profiles` + `custom_formats` (par instance) sont
  générés.** Tout le reste est **pass-through verbatim** : `trashGuideUrl`,
  `recyclarrConfigUrl`, `customFormatDefinitions` (CF locaux), `base_url`/
  `api_key`, `media_naming`, `quality_definition` (caps MB/min hand-tunés),
  `templates`, `includes`. Calque exact de SC#2. (Rejeté : générer aussi
  `quality_definition` ou `customFormatDefinitions` → élargit le scope, ces
  sections sont hand-tunées globalement par instance, pas dérivées du profil.)
- **D-33-08:** Le squelette pass-through vit dans un **bloc `configarr:` dédié de
  `intent.yml`** (top-level configarr + sections non-générées par instance).
  `generate` injecte `quality_profiles` + `custom_formats` dans chaque instance
  du squelette. Fichier unique → `intent.yml` reste la seule source hand-edited.
  (Rejeté : fichier pass-through séparé → casse l'invariant "intent.yml = seul
  fichier hand-edited" ; squelette fixe en code → media_naming/quality_definition
  deviennent du code, rebuild pour changer.)

### Claude's Discretion
- Structure pydantic exacte des modèles `profile_definitions` / `intent.configarr`
  (réutiliser ou s'inspirer de `ConfigarrRootConfig` de `tools/arrconf-ui/`).
- Forme exacte du merge (injection des blocs générés dans le squelette
  pass-through) et déterminisme (réutiliser le pattern `_sort_dict` /
  `_ARRCONF_HEADER` de Phase 32).
- Règle de routing fine (D-33-05) : union des profils référencés par kind.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Frontière arrconf / configarr (ADR-5 — verrou central)
- `spec.md` §11 (ADR-5) — configarr seul propriétaire de quality_profiles /
  custom_formats / quality_definitions / media_naming ; arrconf n'y touche jamais.
- `CLAUDE.md` §"Frontière arrconf / configarr" — tableau de propriété + règle
  `ScopeViolationError` à préserver.

### Source-of-truth configarr actuel (à régénérer, ne pas casser)
- `charts/arr-stack/files/configarr.yml` — état actuel hand-edited (459 lignes) :
  3 QP/instance (MULTi.VF/Anime/Family), customFormatDefinitions, quality_definition
  caps MB/min, media_naming, VOSTFR scoré -10000/+50/-10000.
- `tools/arrconf/tests/test_configarr_three_profiles.py` — invariants chart-side
  (3 profils/instance, Family clone de MULTi.VF byte-équivalent, scores VOSTFR
  par profil). Ces tests devront être mis à jour pour refléter la génération.

### Catalogue TRaSH + picker (Phase 27, à réutiliser)
- `tools/arrconf-ui/arrconf_ui/configarr_config.py` — `ConfigarrRootConfig`
  pydantic (QualityProfile, QualityGroup, Upgrade, ResetUnmatchedScores...) —
  modèle de référence pour le schéma généré.
- Catalogue TRaSH baké en Phase 27 (SHAs pinnés, zéro HTTP runtime) — source des
  `trash_id` pour `custom_formats`. (Localiser le module exact pendant research.)

### Pattern générateur (Phase 32, à étendre)
- `tools/arrconf/arrconf/generators/intent.py` — `generate_arrconf_yml`,
  `_sort_dict`, `_ARRCONF_HEADER` (déterminisme par construction, header GENERATED).
- `tools/arrconf/arrconf/__main__.py` `generate()` — point d'injection du nouvel
  émetteur configarr (à côté de l'émission arrconf.yml).
- `.github/workflows/tests.yml` — garde `generate-idempotence` à étendre pour
  couvrir `configarr.yml`.

### Requirements
- `.planning/REQUIREMENTS.md` CFGARR-01..04 — critères de traçabilité.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `generators/intent.py` (`generate_arrconf_yml`, `_sort_dict`, `_ARRCONF_HEADER`) :
  pattern exact à dupliquer pour `generate_configarr_yml` (pure fn, sorted keys,
  header GENERATED, byte-reproductible).
- `ConfigarrRootConfig` + sous-modèles dans `tools/arrconf-ui/arrconf_ui/configarr_config.py`
  (QualityProfile, QualityGroup, Upgrade, ResetUnmatchedScores, QualityDefinition,
  MediaNaming) — schéma déjà modélisé, réutilisable côté arrconf pour valider la
  sortie / typer `profile_definitions`.
- Catalogue TRaSH baké Phase 27 — résolution `trash_id → CF`.

### Established Patterns
- `IntentConfig` (`intent_config.py`) `extra="forbid"` — les nouveaux blocs
  `profile_definitions` + `configarr` y sont ajoutés comme champs typés.
- Garde CI `generate-idempotence` (`generate --check` + `git diff --exit-code`)
  déjà en place pour arrconf.yml — étendre à configarr.yml.
- Co-bump rule (`CLAUDE.md`) : phase touche `tools/arrconf/**` → bump
  `charts/arr-stack/values.yaml#arrconf.image.tag` dans le même commit.

### Integration Points
- `arrconf generate` (`__main__.py`) : ajouter l'émission `configarr.yml` à côté
  de `arrconf.yml`, lisant `intent_cfg.profile_definitions` + `intent_cfg.configarr`.
- `charts/arr-stack/files/intent.yml` : ajouter les blocs `profile_definitions` +
  `configarr` (lift du configarr.yml hand-edited actuel) ; renommer
  `category.profile` general/family/anime → MULTi.VF/Family/Anime.
- `charts/arr-stack/files/configarr.yml` devient GENERATED read-only.
</code_context>

<specifics>
## Specific Ideas

- Cas test pivot : VOSTFR = même custom format, scores par profil divergents
  (MULTi.VF -10000, Anime +50, Family -10000) — le schéma `custom_formats` par
  `profile_definition` doit le rendre exprimable nativement (assign_scores_to).
- Hard cut comme Phase 32 : pas de double-source, `configarr.yml` passe
  directement de hand-edited à 100% généré read-only (opérateur unique).
</specifics>

<deferred>
## Deferred Ideas

- Migration de noms general/family/anime → noms live (rejetée D-33-04 ; resterait
  envisageable comme refactor cosmétique futur si l'opérateur accepte la
  réassignation manuelle des médias).
- Génération de `quality_definition` / `customFormatDefinitions` par profil
  (hors scope D-33-07 ; pourrait être une phase future si l'opérateur veut des
  caps MB/min par profil plutôt que par instance).
- UI d'édition de `profile_definitions` / picker CF intégré → Phase 34 (UI over
  intent).
</deferred>

---

*Phase: 33-configarr-yml-generation*
*Context gathered: 2026-06-05*
