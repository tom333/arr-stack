# Phase 17 — arrconf-ui CI coverage — DISCUSSION LOG

**Date :** 2026-05-24
**Mode :** discuss (default)
**Workflow :** `/gsd-discuss-phase 17`

## Codebase scout

- `.github/workflows/tests.yml` : path-filter `tools/arrconf/**` + `schemas/**` + `examples/**` ; 1 job `test` qui couvre arrconf (setup-uv + triad + pytest --cov-fail-under=70 implicite).
- `.github/workflows/chart-lint.yml` : path-filter `charts/**` + `tools/arrconf/**` + `examples/values-prod.yaml` + `renovate.json` + `tools/scripts/**`. **N'inclut pas `tools/arrconf-ui/**`.** Job `tag` `needs: lint` + `if: github.event_name == 'push' && github.ref == 'refs/heads/main'` → auto-tag uniquement quand le workflow tourne (donc quand un path-listed change).
- `tools/arrconf-ui/pyproject.toml` : sibling editable `arrconf = { path = "../arrconf", editable = true }` ; deps `fastapi`, `uvicorn`, `typer`, `pydantic`, `ruyaml`, `structlog` ; dev `pytest`, `pytest-cov`, `httpx`, `ruff`, `mypy`.
- `tools/arrconf-ui/web/package.json` : Svelte 5 + Vite 6 + svelte-check 4 + tsc 5.6. Scripts disponibles : `dev`, `build`, `preview`, `check` (svelte-check), `typecheck` (`tsc --noEmit`).
- `tools/arrconf-ui/tests/` : 5 fichiers test (`test_app_endpoints.py`, `test_cli.py`, `test_diff.py`, `test_io_roundtrip.py`, `test_locator.py`) + `conftest.py`.

Finding clé : `chart-lint.yml` path-filter exclut déjà `tools/arrconf-ui/**` → SC#3 (no auto-tag on UI-only PR) est acquise architecturalement sans aucun code à ajouter. La seule chose à faire est de NE PAS toucher à `chart-lint.yml`.

## Gray areas identifiées (4)

1. **Structure workflow** — Étendre `tests.yml` (job(s) ajouté(s)) vs créer `arrconf-ui-tests.yml` séparé ?
2. **Frontend job content** — Minimum REQ (npm ci + check + build) vs ajouter `npm run typecheck` (tsc --noEmit pur) ?
3. **Coverage threshold** — Mirror arrconf `--cov-fail-under=70` ou pas de seuil ?
4. **Node version source** — Hardcoded `node-version: '22'` ou `.nvmrc` + `node-version-file` ?

## Décisions

### Q1 — Structure workflow

**Options présentées :**
- 2 jobs dans `tests.yml` existant (Recommandé)
- Nouveau `arrconf-ui-tests.yml` dédié

**Choix opérateur :** 2 jobs dans `tests.yml`.

**Notes :** Workflow file unique pour tous les tests code-side. Lecture/maintenance plus simple. Path-filter de `tests.yml` étend en union à `tools/arrconf-ui/**`.

### Q2 — Frontend job content

**Options présentées :**
- Minimum REQ : `npm ci + check + build` (Recommandé)
- + `tsc --noEmit` (`npm run typecheck`)

**Choix opérateur :** + tsc --noEmit (full quad : `npm ci + check + typecheck + build`).

**Notes :** `svelte-check` couvre les `.svelte` mais PAS les fichiers `.ts` purs (`theme.ts`, `i18n/fr.ts`, `api.ts`, etc.). Un `tsc --noEmit` séparé attrape les régressions TS dans ce code-là. Coût négligeable (~3-5s par run).

### Q3 — Coverage threshold

**Options présentées :**
- Pas de threshold (Recommandé)
- `--cov-fail-under=70` (miroir arrconf)

**Choix opérateur :** Pas de threshold.

**Notes :** UI backend = glue FastAPI + ruyaml + Typer CLI. Seuil 70% forcerait des tests artificiels sur du code orchestration peu testable (uvicorn startup, signal handlers). Knob trivial à ajouter plus tard si besoin.

### Q4 — Node version source

**Options présentées :**
- Hardcoded `node-version: '22'` (Recommandé)
- `.nvmrc` + `node-version-file`

**Choix opérateur :** Hardcoded `'22'`.

**Notes :** Simple, lisible dans le workflow, suit la LTS. Single-line change si Node 24 devient LTS. Pas de fichier supplémentaire à versionner.

## Deferred ideas

- **`.nvmrc` pour devs locaux** — option Q4 non retenue. Pourrait être ajouté plus tard si > 1 dev contribue à arrconf-ui.
- **Coverage threshold sur backend** — option Q3 non retenue. Re-évaluer si arrconf-ui devient un projet "sérieux" avec multi-contributeurs.
- **Workflow file dédié** — option Q1 non retenue. Re-évaluer si tests.yml devient trop touffu (>5 jobs).

## Scope creep redirected

Aucun. Discussion strictement focalisée sur CI structure.

## Outcome

CONTEXT.md écrit avec 5 D-decisions locked (D-17-WORKFLOW-01, D-17-FRONTEND-01, D-17-COVERAGE-01, D-17-NODE-01, D-17-NO-CHART-LINT-CHANGE) + 3 research items light + 5 HUMAN-UAT scenarios provisionnels.

Plan-phase doit produire 1 plan unique 17-A, ~3-5 tasks (spot-check local baseline + patch tests.yml + README + checkpoint). Pas de phase recherche externe. Pas de snapshot. Pas de co-bump. CI-only change.
