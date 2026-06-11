# Phase 33: configarr.yml generation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-05
**Phase:** 33-configarr-yml-generation
**Areas discussed:** Source des défs de profil, Nommage profils & split instance, CF + scoring par profil, Frontière généré / pass-through

---

## Source des défs de profil

### Où vivent les corps QP complets ?
| Option | Description | Selected |
|--------|-------------|----------|
| Bloc profile_definitions intent | Opérateur écrit chaque profil 1× ; generate expanse | ✓ |
| Templates built-in arrconf | Corps QP en dur (code Python) ; rebuild pour changer | |
| Pass-through verbatim | Blocs QP configarr complets dans intent ; profile devient décoratif | |

**User's choice:** Bloc profile_definitions intent

### Granularité (par nom vs par kind) ?
| Option | Description | Selected |
|--------|-------------|----------|
| 1× par nom, appliqué aux 2 | general/family/anime définis 1×, émis sonarr ET radarr | ✓ |
| Par (profil × kind) | general-series / general-movies séparés ; double l'édition | |
| 1× par nom + override kind | Déf de base + overrides par kind ; schéma plus complexe | |

**User's choice:** 1× par nom, appliqué aux 2
**Notes:** Risque divergence qualities séries/films (Remux-1080p films) noté — rester dans le sous-ensemble commun, déjà prouvé sûr par la config prod actuelle.

### Expression de Family ?
| Option | Description | Selected |
|--------|-------------|----------|
| Déf indépendante complète | family écrit en entier même si == general aujourd'hui | ✓ |
| Alias clone_of: general | DRY, 1 endroit à changer ; ajoute résolution d'alias | |

**User's choice:** Déf indépendante complète

---

## Nommage profils & split instance

### Réconcilier noms intent (general/family/anime) vs live (MULTi.VF/Anime/Family) ?
| Option | Description | Selected |
|--------|-------------|----------|
| Garder MULTi.VF/Anime/Family | category.profile renommé vers ces clés ; zéro migration live | ✓ |
| Adopter general/family/anime | Noms intent deviennent live ; réassignation manuelle de tous les médias | |
| Alias display ≠ clé | category.profile garde general/... + champ configarr_name émis | |

**User's choice:** Garder MULTi.VF/Anime/Family
**Notes:** Évite d'orpheliner les assignations de profils des médias prod. Routing kind→instance (series→sonarr, movies→radarr) inféré, pas demandé explicitement.

---

## CF + scoring par profil

### Comment déclarer custom_formats + scores (cas VOSTFR) ?
| Option | Description | Selected |
|--------|-------------|----------|
| Liste CF par profile_definition | custom_formats: [{trash_id\|name, score}] ; assign_scores_to ce profil | ✓ |
| Liste CF globale + matrice scores | CFs 1× + scores par profil en matrice ; schéma complexe | |
| Pass-through sortie picker P27 | Bloc picker verbatim ; pas de génération depuis l'intent | |

**User's choice:** Liste CF par profile_definition
**Notes:** TRaSH CFs par trash_id (catalogue baké P27), CF locaux par nom.

---

## Frontière généré / pass-through

### Qu'est-ce qui est généré ?
| Option | Description | Selected |
|--------|-------------|----------|
| Seuls QP + custom_formats | Reste (urls, customFormatDefinitions, base_url, media_naming, quality_definition, templates/includes) pass-through | ✓ |
| QP + CF + quality_definition | Aussi quality_definition par profil ; élargit le scope | |
| QP + CF + customFormatDefinitions | Aussi CF locaux ; plus simple de les laisser pass-through | |

**User's choice:** Seuls QP + custom_formats

### Où vit le squelette pass-through + merge ?
| Option | Description | Selected |
|--------|-------------|----------|
| Bloc intent.configarr dédié | Squelette complet dans intent.yml ; generate injecte QP+CF par instance | ✓ |
| Fichier pass-through séparé | configarr-passthrough.yml référencé ; casse "intent = seul fichier" | |
| Squelette fixe générateur | Squelette en code ; media_naming/quality_definition deviennent code | |

**User's choice:** Bloc intent.configarr dédié

---

## Claude's Discretion

- Structure pydantic exacte des modèles `profile_definitions` / `intent.configarr` (réutiliser `ConfigarrRootConfig`).
- Forme exacte du merge + déterminisme (pattern `_sort_dict` / `_ARRCONF_HEADER` de Phase 32).
- Règle de routing fine (union des profils référencés par kind — D-33-05).

## Deferred Ideas

- Migration de noms general/family/anime → live (rejetée ; refactor cosmétique futur possible).
- Génération de quality_definition / customFormatDefinitions par profil (hors scope ; phase future possible).
- UI d'édition profile_definitions / picker intégré → Phase 34.
