# Phase 1: arrconf POC + JSON Schema - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-07
**Phase:** 1-arrconf-poc-json-schema
**Mode:** default (interactif, batched questions)
**Areas discussed:** Open questions Q4-Q8, Python tooling (CLI + pkg manager), Test fixtures source, Périmètre schéma pydantic Sonarr

---

## Open Questions Q4-Q8 (4 mini-décisions)

### Q4 — Stratégie de release pour arrconf

| Option | Description | Selected |
|--------|-------------|----------|
| Tags manuels v1 | Tag git semver `vX.Y.Z` créé manuellement après merge. CI build l'image avec `:vX.Y.Z` + `:latest`. Pas d'outil de release auto. Adapté au scope homelab single-user. | ✓ |
| release-please tout de suite | GitHub Action `release-please` génère PRs de release auto depuis conventional commits. Plus de discipline, plus de complexité setup. | |

**User's choice:** Tags manuels v1
**Notes:** Migration vers release-please possible plus tard si la friction le justifie. Cohérent avec scope minimaliste.

---

### Q6 — Tag `arrconf-managed` sur les ressources

| Option | Description | Selected |
|--------|-------------|----------|
| `arrconf-managed` + protect-from-prune | Toute ressource créée/modifiée par arrconf reçoit le tag `arrconf-managed`. Le tag lui-même est réconcilié. Seules les ressources avec ce tag peuvent être prune. | ✓ |
| Autre nom de tag | Ex. `managed-by-gitops`, `arrstack`, etc. Même sémantique mais nom différent. | |
| Pas de tag (filtre uniquement par diff) | Toute ressource du YAML appartient à arrconf. Plus simple mais perd l'info "manuelle vs gérée". Risque prune accidentel. | |

**User's choice:** `arrconf-managed` + protect-from-prune
**Notes:** Sémantique sécurisée — protège les ressources créées manuellement par l'utilisateur. Cohérent avec REQ-managed-tag.

---

### Q7 — Versions des APIs *arr supportées

| Option | Description | Selected |
|--------|-------------|----------|
| v4+ only / version courante uniquement | Sonarr `/api/v3/`, Radarr `/api/v3/`, Prowlarr `/api/v1/`, Seerr v1, Jellyfin 10.11+. Pas de couches de compat. | ✓ |
| Multi-version avec adapters | Couche d'abstraction par version (`reconcilers/sonarr/v3.py`, `v4.py`) si breaking change futur. | |

**User's choice:** v4+ only / version courante uniquement
**Notes:** Surdimensionnement multi-version rejeté pour homelab single-user. Si breaking change : Renovate alerte, adaptation ad hoc.

---

### Q8 — Comportement par défaut du `prune`

| Option | Description | Selected |
|--------|-------------|----------|
| `prune: false` par défaut, opt-in par section | Si une ressource cluster n'est pas dans le YAML : log warning, ne supprime pas. L'utilisateur active `prune: true` section par section. | ✓ |
| `prune: true` global (mode strict) | Le YAML est la source de vérité absolue. Toute ressource hors-YAML supprimée. Plus pur GitOps mais risque destructeur. | |

**User's choice:** `prune: false` par défaut, opt-in par section
**Notes:** Sécurise les premiers déploiements. Combiné avec D-02 (`arrconf-managed` tag) : seules les ressources taggées peuvent être prune même avec `prune: true`.

---

## Python tooling : CLI framework + package manager

### CLI framework

| Option | Description | Selected |
|--------|-------------|----------|
| argparse stdlib | Zéro dépendance externe. Suffisant pour 4 sous-commandes simples. Plus de boilerplate. | |
| click | Standard de facto Python. Décorateurs propres. Auto-generated help. Mieux pour 5-10+ commandes. | |
| typer | Basé sur click + type hints (auteur de FastAPI). Très court à écrire, types Python = flags. Excellent fit avec pydantic v2. | ✓ |

**User's choice:** typer
**Notes:** Cohérent avec la stack pydantic v2 déjà en place. DX moderne. Ajoute 2 deps (typer + click).

---

### Package manager

| Option | Description | Selected |
|--------|-------------|----------|
| uv | Moderne ultra-rapide (Astral, même éditeur que ruff). Lockfile auto. Build Docker rapide via `uv sync`. | ✓ |
| pip + pyproject.toml | Setup classique avec `pip install -e .`. Pas de lockfile. Plus standard mais plus lent. | |
| poetry | Gestion dep + lockfile mature mais plus lent que uv et plus de magie. | |

**User's choice:** uv
**Notes:** Cohérent avec ruff (même éditeur Astral) déjà dans la stack. CLAUDE.md mentionne déjà `uv sync` dans le workflow local — confirmation.

---

## Test fixtures : source de vérité

| Option | Description | Selected |
|--------|-------------|----------|
| Hybride : baseline Phase 0 sanitisée comme seed + hand-write pour cas limites | Happy path = copie redacted de `snapshots/`. Cas limites (delete, prune-skip, errors 401/500) = hand-written. | ✓ |
| Tout depuis baseline Phase 0 sanitisée | Single source absolue. Difficile de tester des cas que l'instance réelle ne présente pas. | |
| Tout hand-written | Plus de contrôle, mais risque de divergence avec la vraie API. | |

**User's choice:** Hybride
**Notes:** Tire parti du baseline Phase 0 déjà committé et redacted. Évite duplication. Cas limites ciblés pour la coverage.

---

## Périmètre du schéma pydantic Sonarr

| Option | Description | Selected |
|--------|-------------|----------|
| Hybride : full pour download_client + stubs `ScopeViolationError` pour le reste | `download_client` complet (~25 fields v3). Stubs pour `indexer/notification/root_folder/tag/host_config` (NotImplementedError + TODO Phase 3) + 4 endpoints frontière (`ScopeViolationError`). | ✓ |
| Minimal : juste download_client (~5-8 fields) | Uniquement les fields strictement nécessaires pour reconcilier. Code court. Phase 3 devra revisiter. | |
| Full : tous les fields download_client de Sonarr v3 | ~25 fields exhaustifs. Pas de stubs pour les autres resources. Frontière configarr ajoutée plus tard. | |

**User's choice:** Hybride
**Notes:** Minimise re-architecture en Phase 3 + ancre la frontière configarr immédiatement (ADR-5 codé en dur dès Phase 1).

---

## Claude's Discretion

Items laissés au planner / executor / researcher (notés dans CONTEXT.md) :
- Structure exacte de `differ.py` (fonction unique vs class)
- Format précis des logs structlog (champs ajoutés, processeurs)
- Convention de naming pour les tests
- Choix entre `pydantic-settings` vs lecture manuelle des env vars
- Pre-commit hooks dans le repo (deferred)
- Politique exacte retry httpx (3 retries / exponential backoff — à confirmer en research)

---

## Deferred Ideas

Aucune idée hors scope mentionnée durant la discussion (les 4 zones grises sélectionnées sont restées dans le scope Phase 1). Les "Deferred Ideas" listées dans CONTEXT.md sont des reports planifiés vers les phases ultérieures (Phase 2/3/4/post-MVP), pas des dérives de scope discutées ici.

---

## Process Notes

- **Mode :** default (sans `--auto`, `--all`, `--batch`, `--text`, `--analyze`).
- **Optimisation :** questions batched par paquet de 4 dans 2 calls AskUserQuestion (au lieu des 8 turns single-question habituels). Justifié par les questions binaires/triplets simples.
- **Toutes les options "Recommandé" choisies par l'utilisateur** sur Q4/Q6/Q7/Q8 + uv + Hybride x2. Seule `typer` est non-marquée recommandée mais cohérente avec la stack.
