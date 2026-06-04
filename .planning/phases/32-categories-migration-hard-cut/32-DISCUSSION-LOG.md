# Phase 32: Categories migration (hard cut) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-03
**Phase:** 32-categories-migration-hard-cut
**Areas discussed:** Static config location, Routing rules, Output format, Todo fold

---

## Static config location (crux)

| Option | Description | Selected |
|--------|-------------|----------|
| intent.yml absorbe tout | `categories:` + bloc `apps:` pass-through ; generate compose → arrconf.yml complet ; 1 fichier hand-edited | ✓ |
| Fichier base séparé | categories → intent.yml ; config statique dans arrconf-base.yml ; generate merge ; 2 fichiers | |
| Modéliser la config statique | champs pydantic typés (pas pass-through) ; verbeux/risqué | |

**User's choice:** intent.yml absorbe tout
**Notes:** Vraie couche d'intention, un seul fichier hand-edited. Pass-through verbatim de la config app (YAGNI sur la modélisation typée vu config stable).

---

## Routing rules (content_routing / series_tags / movie_tags)

| Option | Description | Selected |
|--------|-------------|----------|
| Restés statiques pass-through | keywords family/anime = jugement opérateur non-dérivable ; verbatim dans apps ; KISS | ✓ |
| Dérivés des categories | dériver depuis profils/kinds ; couplage fort, fragile | |

**User's choice:** Restés statiques pass-through
**Notes:** Pitfall 5 (keywords conservateurs) reste du jugement opérateur, pas de mapping 1:1 sur categories.

---

## Output format (arrconf.yml généré, SC#4)

| Option | Description | Selected |
|--------|-------------|----------|
| YAML déterministe machine-order | dump trié stable, header `# GENERATED`, byte-reproductible, pas de commentaires préservés | ✓ |
| Préserver structure/commentaires humains | garder ordre+commentaires actuels ; plus dur à rendre byte-reproductible | |

**User's choice:** YAML déterministe machine-order
**Notes:** Doc vit dans intent.yml ; arrconf.yml read-only → commentaires sans valeur.

---

## Todo fold

| Option | Description | Selected |
|--------|-------------|----------|
| Ne pas folder | tâche ops manuelle (filesystem), sans rapport avec refactor code | ✓ |
| Folder dans Phase 32 | inclure migration filesystem ; scope différent | |

**User's choice:** Ne pas folder
**Notes:** `migrer-mediatheque-existante` reste en pending, hors phase.

## Claude's Discretion

- Forme exacte du schéma `apps:` dans intent.yml (nom du bloc, nesting).
- Mécanisme de compose (déplacer le merge runtime→generate-time ou réutiliser).
- Migration de la garde CI `generate-idempotence` pour couvrir arrconf.yml.

## Deferred Ideas

- Génération configarr.yml → Phase 33.
- UI sur intent → Phase 34.
- Modélisation pydantic typée de la config app → non retenu, reconsidérer si besoin réel.
