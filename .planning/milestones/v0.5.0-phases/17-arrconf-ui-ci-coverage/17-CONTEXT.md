# Phase 17 — arrconf-ui CI coverage — CONTEXT

**Phase:** 17
**Name:** arrconf-ui CI coverage
**Milestone:** v0.5.0
**Status:** Context gathered, ready for `/gsd-plan-phase 17`
**Date:** 2026-05-24

## Domain

Restaurer la couverture CI sur `tools/arrconf-ui/**` qui était hors path-filter depuis v0.4.0 (dette CI assumée pour ship rapide). Phase 17 étend `tests.yml` avec 2 nouveaux jobs (backend Python + frontend Svelte) et laisse `chart-lint.yml` strictement inchangé — c'est ce dernier point qui satisfait SC#3 (un PR touchant uniquement `tools/arrconf-ui/**` ne déclenche PAS l'auto-tag).

Pure dette technique : aucun changement de code applicatif (`tools/arrconf/**` ou `tools/arrconf-ui/**`) attendu. Le seul artefact modifié sera `.github/workflows/tests.yml` + une section README documentant le matrix CI.

## Decisions

### D-17-WORKFLOW-01 — 2 nouveaux jobs dans tests.yml (pas de nouveau fichier)

**Décidé :** Ajouter `arrconf-ui-backend` + `arrconf-ui-frontend` comme deux jobs supplémentaires dans `.github/workflows/tests.yml`. Path-filter du workflow étendu pour inclure `tools/arrconf-ui/**`. Pas de nouveau workflow file séparé.

**Conséquences :**
- Workflow file unique pour tous les tests code-side du repo (cohérent avec la structure actuelle où `test` couvre arrconf). Moins de fichiers à maintenir, plus simple à raisonner.
- Les 3 jobs (`test`, `arrconf-ui-backend`, `arrconf-ui-frontend`) tournent en parallèle indépendants — chacun avec son `setup-uv` ou `setup-node`, son working-directory.
- Path filter du workflow devient une union : déclenche sur ANY de `tools/arrconf/**`, `schemas/**`, `examples/**`, `tools/arrconf-ui/**`, `.github/workflows/tests.yml`. Les 3 jobs tournent toujours ensemble — pas de gating per-path interne au workflow (simpler).

### D-17-FRONTEND-01 — Frontend job = npm ci + check + build + typecheck

**Décidé :** Le job `arrconf-ui-frontend` exécute :
1. `npm ci` (deterministic install depuis package-lock.json)
2. `npm run check` (svelte-check — combine type check Svelte components + TS)
3. `npm run typecheck` (`tsc --noEmit` — couche TS pure pour les fichiers `.ts` non-Svelte)
4. `npm run build` (Vite build, vérifie que le bundle compile clean)

**Conséquences :**
- 4 étapes vs 3 du REQ original — couche `tsc --noEmit` en bonus parce que svelte-check ne couvre QUE les composants `.svelte` (les fichiers `.ts` purs comme `i18n/fr.ts` ou `theme.ts` n'y passent pas).
- Temps job estimé : `npm ci` ~10-30s (cache GitHub Actions accélère), check ~5s, typecheck ~3s, build ~5s. Total <1min.
- Une régression `.ts` pure (qui aujourd'hui ne casse svelte-check ni vite build dans certains cas) sera attrapée.

### D-17-COVERAGE-01 — Pas de coverage threshold sur arrconf-ui backend

**Décidé :** Le job `arrconf-ui-backend` exécute `uv run pytest -q` SANS `--cov-fail-under`. Le triad complet (ruff format + ruff check + mypy + pytest) est exécuté, mais sans seuil de coverage minimum.

**Conséquences :**
- Diverge consciemment de arrconf (qui a `--cov-fail-under=70`). Justification : arrconf-ui backend = glue FastAPI + ruyaml round-trip + Typer CLI. Tests d'intégration HTTP couvrent l'essentiel ; un seuil de 70% forcerait à écrire des tests artificiels pour des paths d'orchestration peu testables (e.g., uvicorn startup).
- Si l'opérateur veut un seuil plus tard, c'est un knob trivial à ajouter au job. Pas de blocker.

### D-17-NODE-01 — Hardcoded node-version: '22' dans setup-node

**Décidé :** `actions/setup-node@v6` avec `node-version: '22'` en dur dans `tests.yml`. Pas de `.nvmrc`.

**Conséquences :**
- Node 22 = LTS active mai 2026 (Active LTS jusqu'à octobre 2026). Aligné avec ce que Vite 6 + Svelte 5 supportent officiellement.
- Si Node 24 devient LTS, c'est un single-line change dans le workflow. Pas de fichier supplémentaire à versionner.
- Devs locaux qui veulent matcher CI tapent `nvm use 22` à la main (acceptable pour single-tenant homelab).

### D-17-NO-CHART-LINT-CHANGE — `chart-lint.yml` strictement non-modifié

**Décidé :** Le path-filter de `chart-lint.yml` n'est PAS étendu à `tools/arrconf-ui/**`. Aucune ligne touchée dans `chart-lint.yml`.

**Conséquences :**
- Un PR touchant UNIQUEMENT `tools/arrconf-ui/**` ne déclenche PAS le workflow `chart-lint` → ne déclenche PAS le job `tag` (qui crée l'auto-tag) → satisfait SC#3 de Phase 17 sans aucun code ni guard explicite.
- Architectural property : la séparation arr-stack chart releases (déclenchées par `tools/arrconf/**` + `charts/**`) vs arrconf-ui releases (pas de release semver, runs from source) est codifiée par le path-filter de `chart-lint`.
- Si un futur changement de scope veut tagger arr-stack chart sur des changements UI, c'est une décision séparée à prendre dans une autre phase.

## Code Context

### Files to modify (probable scope)

- **`.github/workflows/tests.yml`** :
  - Étendre `on.push.paths` + `on.pull_request.paths` à inclure `tools/arrconf-ui/**`
  - Ajouter job `arrconf-ui-backend` (working-directory `tools/arrconf-ui`) :
    - `actions/setup-uv@latest`
    - `uv sync` (sibling editable `arrconf` doit s'installer correctement via uv source path)
    - `uv run ruff format --check .`
    - `uv run ruff check .`
    - `uv run mypy .`
    - `uv run pytest -q`
  - Ajouter job `arrconf-ui-frontend` (working-directory `tools/arrconf-ui/web`) :
    - `actions/setup-node@v6` avec `node-version: '22'` + `cache: 'npm'` + `cache-dependency-path: tools/arrconf-ui/web/package-lock.json`
    - `npm ci`
    - `npm run check`
    - `npm run typecheck`
    - `npm run build`
- **`README.md`** :
  - Ajouter une section "CI matrix" ou étendre la section existante mentionnant `tests.yml` couvre désormais arrconf + arrconf-ui (backend + frontend).

### Files explicitly NOT to modify

- `.github/workflows/chart-lint.yml` (D-17-NO-CHART-LINT-CHANGE — préserve la propriété "UI-only PR ≠ auto-tag")
- `.github/workflows/arrconf-image.yml` (UI n'est pas dans l'image arrconf — pas d'impact sur GHCR build)
- Aucun fichier sous `tools/arrconf/**` ni `tools/arrconf-ui/**` (CI-only change)

### Existing patterns to reuse

- **Job structure mirror arrconf-ui-backend → arrconf `test` job** : `setup-uv` + `uv sync` + triad ruff/mypy + pytest. Step names alignés pour cohérence.
- **No chart-pin co-bump** : Phase 17 ne touche PAS `tools/arrconf/**`, donc aucun bump de `charts/arr-stack/values.yaml#arrconf.image.tag`. CLAUDE.md "Release pin co-bump pattern" explicitly excludes ce type de change.

## Canonical Refs

- [`.planning/ROADMAP.md`](../../ROADMAP.md) — Phase 17 entry (SC#1-5)
- [`.planning/REQUIREMENTS.md`](../../REQUIREMENTS.md) — REQ-arrconf-ui-ci
- [`.planning/PROJECT.md`](../../PROJECT.md) — Current Milestone v0.5.0
- [`CLAUDE.md`](../../../CLAUDE.md) — section "Release pin co-bump pattern" (explicitly excludes CI-only changes)
- [`.github/workflows/tests.yml`](../../../.github/workflows/tests.yml) — workflow à étendre
- [`.github/workflows/chart-lint.yml`](../../../.github/workflows/chart-lint.yml) — workflow à PRÉSERVER intact (D-17-NO-CHART-LINT-CHANGE)
- [`tools/arrconf-ui/pyproject.toml`](../../../tools/arrconf-ui/pyproject.toml) — Python toolchain (uv + ruff + mypy + pytest)
- [`tools/arrconf-ui/web/package.json`](../../../tools/arrconf-ui/web/package.json) — Frontend toolchain (npm + svelte-check + tsc + vite)
- [`README.md`](../../../README.md) — opérateur onboarding, doit mentionner le matrix CI

## Research Items (light — Phase 17 needs little research)

1. **`uv sync` from `tools/arrconf-ui/` with editable sibling `arrconf` — does it work in GitHub Actions runner ?** Hypothèse : oui, uv lit `[tool.uv.sources] arrconf = { path = "../arrconf", editable = true }` et installe en mode editable. La sibling existe dans le checkout. À confirmer en exécution (Plan task spécifique).
2. **`actions/setup-node@v6` cache strategy** — `cache: 'npm'` + `cache-dependency-path: tools/arrconf-ui/web/package-lock.json` est-il la bonne syntaxe pour cibler un lock file dans un sous-dossier ? Doc officielle setup-node confirme syntaxe.
3. **Que retourne `npm run check` vs `npm run typecheck` sur la codebase actuelle ?** Spot-check local avant CI pour valider 0 erreur baseline. Si erreurs existantes, Phase 17 doit décider : (a) fix en parallèle, (b) ajouter pragma ignore, (c) accepter et défer.

## Plan Structure Proposed

Single plan **17-A** (1 wave, ~3-5 tasks). Surface très petite :
1. Local spot-check baseline (triad + frontend commands all green)
2. Patch `tests.yml` — extend paths + add backend job + add frontend job
3. Update README.md CI matrix section
4. Verify locally that the workflow file syntax parses (`act` or similar — optional)
5. Operator checkpoint : open PR sur arr-stack, vérifier les 2 nouveaux jobs apparaissent + green sur le PR lui-même (SC#4)

Pas de phase recherche externe nécessaire. Pas de snapshot (CI-only). Pas de co-bump.

## HUMAN-UAT Scenarios (provisional)

- **SC#1** — Un PR touchant `tools/arrconf-ui/arrconf_ui/*.py` montre le job `arrconf-ui-backend` qui run le triad complet (green ou red according to code). Validé sur le PR shippant Phase 17 lui-même.
- **SC#2** — Un PR touchant `tools/arrconf-ui/web/src/*.svelte` montre le job `arrconf-ui-frontend` qui run `npm ci + check + typecheck + build`. Validé sur le PR shippant Phase 17.
- **SC#3** — Un PR touchant UNIQUEMENT `tools/arrconf-ui/**` (rien d'autre) ne déclenche PAS `chart-lint.yml` → pas de tag créé après merge. Vérifier via `gh run list --workflow=chart-lint.yml` après merge — aucun run pour ce PR. Validé soit sur le PR Phase 17 (qui touche `.github/workflows/tests.yml` aussi donc compte), soit sur un PR follow-up qui touche QUE arrconf-ui.
- **SC#4** — Le PR shippant Phase 17 montre les nouveaux jobs green sur le tab Checks GitHub.
- **SC#5** — README.md "CI matrix" section décrit clairement les 3 jobs + leurs trigger paths.

## Locked Boundaries

- ❌ **Pas de co-bump `arrconf.image.tag`** — CI-only change.
- ❌ **Pas de modification de `chart-lint.yml`** — préserve SC#3 architecturalement.
- ❌ **Pas de modification de code applicatif** — `tools/arrconf-ui/**` Python ou Svelte non touché.
- ❌ **Pas d'auto-fix des erreurs si baseline triad/build a des warnings/errors** — décision séparée si découverte (Plan task 1).
- ❌ **Pas de phase recherche externe via gsd-phase-researcher** — surface trop petite + research items adressables par spot-check local.

## Open Questions

Aucune restante. Plan-phase peut démarrer directement.
