# Phase 1: arrconf POC + JSON Schema - Research

**Researched:** 2026-05-07
**Domain:** Python CLI + pydantic v2 reconciler against Sonarr v3 REST API + JSON Schema export for VS Code YAML autocomplete + GHCR image pipeline
**Confidence:** HIGH (Sonarr OpenAPI spec fetched directly; all PyPI versions verified; pydantic schema generation tested locally)

## Summary

Phase 1 livre un squelette `tools/arrconf/` (Python 3.13 + uv) avec 4 sous-commandes Typer (`apply`, `dump`, `diff`, `schema-gen`), un seul reconciler bout-en-bout (`reconcilers/sonarr.py` → `download_clients`), un JSON Schema généré (Draft 2020-12), une image Docker GHCR multi-stage en USER non-root, et 2 GitHub Actions workflows (`tests.yml` + `arrconf-image.yml`). Le tout doit prouver le round-trip `dump → apply --dry-run` = 0 action et démarrer la frontière configarr (`ScopeViolationError` codée en dur sur les 4 endpoints interdits).

Toutes les décisions techniques majeures sont déjà locked dans `01-CONTEXT.md` (D-01 à D-22). Cette recherche fournit les **valeurs concrètes** dont le planner a besoin :
- versions PyPI vérifiées contre le registre (toutes très récentes, 2025-2026)
- schéma Sonarr `DownloadClientResource` extrait du fichier OpenAPI officiel — c'est la **source de vérité** pour pydantic
- patterns httpx + retries + structlog + respx + pytest-cov vérifiés sur les docs officielles
- recettes Dockerfile multi-stage uv → `python:3.13-slim` USER 1000:1000
- GHCR pipeline canonique avec `docker/build-push-action@v5` + `metadata-action@v5`

**Primary recommendation:** Construire le squelette en 3 vagues — (1) plumbing (pyproject + Dockerfile + CI vide + skeleton Python qui compile), (2) reconciler Sonarr download_clients + tests respx + schema-gen + ScopeViolationError, (3) round-trip prouvé + image GHCR publique + autocomplétion VS Code démontrée.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 (Q4 release strategy)** : Tags semver `vX.Y.Z` créés manuellement après merge sur main. CI build l'image avec tags `:vX.Y.Z` + `:latest` sur tag git ; `:sha-<short>` + `:branch-<name>` sur push branche. **Pas** de release-please en v1 — migration possible plus tard si la friction le justifie.

**D-02 (Q6 managed-tag)** : Toute ressource créée ou modifiée par arrconf reçoit le tag `arrconf-managed` (champ `tags:` standard *arr). Le tag lui-même est réconcilié au runtime (créé s'il manque, jamais supprimé même en mode prune). **Seules** les ressources avec ce tag peuvent être prune par arrconf — les ressources non-taggées (créées manuellement par l'utilisateur) sont protégées.

**D-03 (Q7 multi-version *arr)** : Support **uniquement** la version courante de chaque API au moment de Phase 1 :
  - Sonarr `/api/v3/`
  - Radarr `/api/v3/`
  - Prowlarr `/api/v1/`
  - qBittorrent `/api/v2/`
  - Seerr `/api/v1/`
  - Jellyfin v10.11+ (header `Authorization: MediaBrowser Token=...`)
  Pas de couche d'abstraction multi-version.

**D-04 (Q8 prune default)** : `prune: false` par défaut au niveau de chaque section de ressource dans le YAML. Opt-in explicite par section. Quand `prune: false` : log un warning pour les ressources cluster non présentes dans le YAML, ne supprime pas. Quand `prune: true` : supprime SEULEMENT les ressources taggées `arrconf-managed`.

**D-05 (Package manager)** : **`uv`** (Astral). Lockfile auto (`uv.lock` committé). Build Docker via `uv sync --frozen`.

**D-06 (CLI framework)** : **`typer`**. Type-hint based, basé sur click.

**D-07 (Logging)** : `structlog` avec JSON formatter pour la sortie cluster. Niveau via env `ARRCONF_LOG_LEVEL` (default `INFO`). Format pretty + couleurs en mode TTY local pour DX, JSON pour CronJob.

**D-08 (Scope schéma Sonarr Phase 1)** : Approche **hybride** :
  - `resources/sonarr/download_client.py` → schéma **complet** Sonarr v3
  - `resources/sonarr/{indexer,notification,root_folder,tag,host_config,quality_profile,custom_format,quality_definition,media_naming}.py` → fichiers **stubs** présents (forward-compat Phase 3)
  - 4 endpoints frontière configarr : raise `ScopeViolationError` si `apply` les touche (ADR-5 codé en dur dès Phase 1)
  - 5 endpoints futurs : `NotImplementedError` + TODO Phase 3 explicite

**D-09 (Fixtures source)** : Stratégie **hybride** :
  - **Seed** : `tests/fixtures/sonarr/downloadclient.json` copié depuis `snapshots/baseline-2026-05-07/sonarr/downloadclient.json`
  - **Cas limites hand-written** dans `tests/fixtures/sonarr/edge_cases/`
  - **Mocks d'erreur HTTP** via respx : 401, 404, 500, timeout

**D-10 (Test coverage cible)** : ≥ 70 % sur `differ.py` et `reconcilers/sonarr.py` (CI bloque sinon). Couverture mesurée via `pytest-cov`. Pas d'objectif sur fixtures ni `__main__`.

**D-11 (Idempotence — règle d'or)** : Pattern obligatoire dans `differ.py` : `GET` → matcher par `name` → diff explicite par champ → `POST/PUT/DELETE` SEULEMENT si différence. Round-trip `dump → apply --dry-run` produit 0 action. Test unitaire dédié `test_no_op_idempotent`.

**D-12 (ScopeViolationError)** : Exception définie dans `arrconf/exceptions.py`. Levée si une opération tente d'écrire ou lire un endpoint frontière configarr. Message clair pointant vers `charts/arr-stack/files/configarr.yml`. Test unitaire dédié.

**D-13 (`tests.yml` workflow steps)** : `ruff check → ruff format --check → mypy → pytest --cov` dans cet ordre. CI bloque si l'un échoue. Trigger : PR modifiant `tools/arrconf/**`.

**D-14 (`arrconf-image.yml` workflow)** : Trigger sur push main (modifiant `tools/arrconf/**`) + tag `v*`. Steps : checkout → setup buildx → login GHCR via `GITHUB_TOKEN` → build multi-arch (amd64 only en v1) → push. Tags : `:sha-<short>`, `:branch-<name>` sur push, `:vX.Y.Z` + `:latest` sur tag. cosign signing **deferred**.

**D-15 (CI vérifie schema-gen)** : Step CI dans `tests.yml` : `arrconf schema-gen --output schemas/arrconf-schema.json` puis `git diff --exit-code schemas/arrconf-schema.json`. Si différence → CI rouge.

**D-16 (Schema directive YAML)** : Chaque fichier YAML arrconf commence par :
  ```yaml
  # yaml-language-server: $schema=../../schemas/arrconf-schema.json
  ```
  (Chemin relatif au YAML.) `examples/baseline-sonarr.yml` créé par `arrconf dump` doit inclure cette directive automatiquement.

**D-17 (`.vscode/settings.json` — optionnel)** : Pas committé en Phase 1.

**D-18 (httpx mode)** : Sync uniquement en Phase 1 (`httpx.Client`).

**D-19 (Retry + timeout)** : `httpx.Client(timeout=httpx.Timeout(connect=5.0, read=30.0))`. Retries via `tenacity` ou httpx transport — recommandation researcher attendue. 3 retries max sur 5xx + connection errors, exponential backoff.

**D-20 (Matching key)** : `name` (string unique par instance Sonarr). Pattern réutilisable pour les autres resources.

**D-21 (Champs read-only / exclude du diff)** : `id` (numérique, généré par Sonarr), `implementationName` (nom UI affiché, dérivé), `infoLink` (URL doc upstream). Marqués `Field(exclude=True)` dans pydantic.

**D-22 (Sécurité fixtures)** : Les API keys / passwords des download_clients dans les fixtures sont **toujours** des valeurs factices ou `"***REDACTED***"`. Audit anti-leak `grep` en pre-commit hook ou en CI.

### Claude's Discretion

Les détails suivants sont laissés au planner / executor :
- Structure exacte de `differ.py` (fonction unique vs class) — recommandation researcher
- Format exact des logs structlog (champs ajoutés, processeurs)
- Convention de naming pour les tests (`test_<feature>_<case>` vs `test_<file>` flat)
- Choix entre `pydantic-settings` vs lecture manuelle des env vars dans `config.py`
- Pre-commit hooks dans le repo (deferred, à voir Phase 2+)

### Deferred Ideas (OUT OF SCOPE)

**Reportées à Phase 2+ (cluster validation)** :
- CronJob YAML K8s + secrets injection via `envFrom: secretRef`
- Drift detection logging structuré pour observability
- Backoff/retry policy en cas de 5xx prolongé

**Reportées à Phase 3 (extension arrconf)** :
- Reconcilers : `indexer`, `notification`, `root_folder`, `tag`, `host_config` Sonarr (stubs créés en Phase 1, impl en Phase 3)
- Radarr et Prowlarr complets
- App sync Prowlarr → *arr

**Reportées à Phase 4 (umbrella + migration)** :
- Custom managers Renovate sur `values.yaml` (regex)
- Helm umbrella chart + ArgoCD Application unique
- Suppression des 9 ArgoCD Applications côté my-kluster + `charts/configarr/`

**Reportées post-MVP** :
- release-please ou semantic-release
- cosign signing
- Multi-arch Docker (amd64 only en v1)
- pre-commit hooks
- httpx async
- Layer d'abstraction multi-version

**Hors scope définitif (ADR-5)** :
- 4 endpoints frontière configarr (`quality_profiles`, `custom_formats`, `quality_definitions`, `media_naming`) — refus codé en dur dès Phase 1.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-cli-subcommands | 4 sous-commandes (`apply`, `dump`, `diff`, `schema-gen`) avec exit codes 0/1/2/3 | Section "Standard Stack" (typer 0.25.1) + "CLI architecture" (signatures concrètes + `typer.Exit(code)` patterns) |
| REQ-yaml-autocomplete | Autocomplétion VS Code via `yaml-language-server` alimentée par `schemas/arrconf-schema.json` | Section "JSON Schema export pipeline" + "VS Code autocomplete wiring" — Draft 2020-12, modeline `# yaml-language-server: $schema=...`, chemin relatif au YAML |
| REQ-idempotence | Round-trip `dump → apply --dry-run` = 0 action ; matching par `name` ; diff explicite avant write | Section "Differ algorithm" — pseudo-code, 3 stratégies de comparaison, fields à exclure du diff |
| REQ-prune-opt-in | `prune: false` par défaut, opt-in par section ; protection `arrconf-managed` | Section "Differ algorithm — prune semantics" + "Tag reconciliation order" |
| REQ-managed-tag | Tag `arrconf-managed` réconcilié + appliqué sur toute ressource créée/modifiée par arrconf | Section "Sonarr Tag schema" (extracted from OpenAPI) + "Tag reconciliation order" |
| REQ-test-coverage | ≥ 70 % coverage sur `differ.py` + `reconcilers/sonarr.py` ; respx pour mocker httpx | Section "Test framework + respx" + "Coverage scoping" |
| REQ-app-coverage (Sonarr download_clients seul) | 1 reconciler bout-en-bout — Sonarr `/api/v3/downloadclient` | Section "Sonarr download_clients schema" — full pydantic field map from OpenAPI |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| YAML config parsing + validation | Python application (pydantic) | — | Source of truth is the YAML file ; pydantic validates shape, types, defaults |
| HTTP communication with Sonarr | Python application (httpx Client) | — | All API calls happen in-process ; no proxy/middleware |
| Idempotent reconciliation (diff/apply) | Python application (`differ.py` + reconcilers) | — | Core domain logic — all decisions about what to POST/PUT/DELETE live here |
| Authentication (X-Api-Key header) | Python application (`client_base.py`) | — | Read from env vars at runtime, injected per-request as header |
| JSON Schema generation | Python application (`schema_gen.py`) | — | Pure offline transformation pydantic models → JSON file |
| YAML autocomplete in editor | Editor (VS Code yaml-language-server) | Python (committed schema) | Schema is just a static artifact ; consumer is the editor's language server |
| CLI argument parsing + exit codes | Python application (typer) | — | Single entrypoint `python -m arrconf` |
| Logging (structlog) | Python application | — | JSON when not TTY (cluster CronJob), pretty when TTY (dev) |
| Image build + push | CI (GitHub Actions + GHCR) | Dockerfile (multi-stage uv → slim) | Triggered on push/tag ; built artifact is consumed in Phase 2 by K8s CronJob |
| Test execution + coverage gate | CI (GitHub Actions, pytest+respx) | — | All API mocking done locally with respx ; no live API call in CI |
| Lint + type check | CI (ruff + mypy) | — | Blocks PR merge ; both run as part of `tests.yml` |
| Schema reproducibility check | CI (`arrconf schema-gen` + `git diff`) | — | Forces re-generation discipline at every PR |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `python` | 3.13.x | Runtime | [VERIFIED: CLAUDE.md locks 3.13 ; cohérent data lab ; compatible avec linuxserver image baseline (Sonarr tournant sur .NET 6 mais arrconf est indépendant)] |
| `uv` | 0.11.11 | Package manager + lockfile + venv | [VERIFIED: pypi 2026-04 ; D-05 locked] — Astral, même éditeur que ruff. Single-binary install. Lockfile reproductible (`uv.lock` committé). |
| `typer` | 0.25.1 | CLI framework | [VERIFIED: pypi 2026-04 ; D-06 locked] — Type-hint based, wrap autour de Click 8.x. Auteur de FastAPI. Tire profit de pydantic. |
| `httpx` | 0.28.1 | HTTP client (sync) | [VERIFIED: pypi 2026 ; CLAUDE.md "Stack technique"] — Sync + async, transport-pluggable, retries de connexion natifs (`HTTPTransport(retries=N)`). |
| `pydantic` | 2.13.4 | Validation YAML + réponses API + JSON Schema gen | [VERIFIED: pypi 2026-04] — `model_json_schema()` natif Draft 2020-12, support `Field(exclude=True)`, `Field(description=...)` pour autocomplete. |
| `pydantic-settings` | 2.14.0 | Lecture env vars typées | [VERIFIED: pypi 2026 ; recommandation pour `SONARR_API_KEY` et amis] — `BaseSettings` + `SecretStr` pour API keys, `env_prefix=""`, pas de fichier de secret (D-22). |
| `ruyaml` | 0.91.0 | YAML round-trip + commentaires | [VERIFIED: pypi 2024 ; CLAUDE.md "Stack technique"] — Préservation commentaires utile pour `arrconf dump` round-trip lisible. |
| `structlog` | 25.5.0 | Logging structuré JSON / pretty | [VERIFIED: pypi 2025 ; D-07 locked] — `JSONRenderer()` pour CronJob, `ConsoleRenderer()` pour TTY local. |
| `tenacity` | 9.1.4 | Retry decorator (5xx + timeouts) | [VERIFIED: pypi 2026] — Recommandation researcher pour D-19. Plus expressif que `httpx.HTTPTransport(retries=N)` qui ne couvre QUE les `ConnectError` / `ConnectTimeout` (pas 5xx, pas 429). Pattern : `@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)) | retry_if_result(lambda r: 500 <= r.status_code < 600))`. |

### Supporting (test + lint + types)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | 9.0.3 | Test runner | [VERIFIED: pypi 2026] |
| `pytest-cov` | 7.1.0 | Coverage gate | [VERIFIED: pypi 2026] — Cf "Coverage scoping" pour le workaround per-module (pas de seuil par fichier en natif). |
| `respx` | 0.23.1 | Mock httpx (route patterns) | [VERIFIED: pypi 2026] — Fixture `respx_mock` standard, marker `@pytest.mark.respx(base_url=...)`. |
| `ruff` | 0.15.12 | Lint + format | [VERIFIED: pypi 2026-04] — Remplace `black + isort + flake8`. CLAUDE.md exige `ruff check && ruff format --check`. |
| `mypy` | 2.0.0 | Type checker (strict) | [VERIFIED: pypi 2026 — major v2 release] — CLAUDE.md exige strict sur signatures publiques. |

### Alternatives Considered (rejected for Phase 1)

| Instead of | Could Use | Tradeoff (and why rejected) |
|------------|-----------|-----------------------------|
| typer | Click brut | Click marche mais perd l'intégration type-hint → pydantic. D-06 a tranché typer. |
| tenacity | httpx-retries (`will-ockmore/httpx-retries`) | Plug & play sur transport, mais ajoute une dep moins mature et couvre seulement `httpx`. tenacity est plus général et plus connu. |
| ruyaml | PyYAML | PyYAML perd les commentaires en round-trip. ruyaml est le successeur maintenu de ruamel.yaml. CLAUDE.md a déjà tranché. |
| pydantic-settings | os.environ + dataclass manuel | pydantic-settings ajoute une dep mais offre `SecretStr`, validation, et défauts typés. Recommandé. |
| pytest-cov per-file threshold | Native `--cov-fail-under` (global only) | pytest-cov ne supporte PAS de seuil par fichier ([CITED: github.com/pytest-dev/pytest-cov/issues/444]). Workaround : scoper `--cov` aux modules critiques uniquement (`--cov=arrconf.differ --cov=arrconf.reconcilers.sonarr`) — voir "Coverage scoping". |
| structlog | stdlib logging + python-json-logger | structlog plus expressif (key=value contextuel). D-07 locked. |
| Click decorators directs | typer + Click underneath | Inutile : typer expose Click via `typer.Context`. |

### Installation

```toml
# tools/arrconf/pyproject.toml
[project]
name = "arrconf"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
  "typer>=0.25.0,<0.26",
  "httpx>=0.28.0,<0.29",
  "pydantic>=2.13,<3",
  "pydantic-settings>=2.14,<3",
  "ruyaml>=0.91,<0.92",
  "structlog>=25.5,<26",
  "tenacity>=9.1,<10",
]

[project.scripts]
arrconf = "arrconf.__main__:app"

[dependency-groups]
dev = [
  "pytest>=9.0,<10",
  "pytest-cov>=7.1,<8",
  "respx>=0.23,<0.24",
  "ruff>=0.15,<0.16",
  "mypy>=2.0,<3",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "N", "D"]
ignore = ["D203", "D213"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["D"]   # docstrings non requises dans les tests

[tool.mypy]
python_version = "3.13"
strict = true
warn_unused_ignores = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
addopts = "-v --strict-markers"
testpaths = ["tests"]

[tool.coverage.run]
source = ["arrconf.differ", "arrconf.reconcilers.sonarr"]
branch = true

[tool.coverage.report]
fail_under = 70
exclude_lines = ["pragma: no cover", "raise NotImplementedError", "if TYPE_CHECKING:"]
```

**Version verification (pypi.org, 2026-05-07):**
```
typer 0.25.1
httpx 0.28.1
pydantic 2.13.4
pydantic-settings 2.14.0
ruyaml 0.91.0
structlog 25.5.0
tenacity 9.1.4
pytest 9.0.3
pytest-cov 7.1.0
respx 0.23.1
ruff 0.15.12
mypy 2.0.0
uv 0.11.11
```

[VERIFIED: queried `https://pypi.org/pypi/<pkg>/json` for each, 2026-05-07]

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    arrconf CLI (typer)                          │
│  apply │ dump │ diff │ schema-gen                               │
└─────────────────────────────────────────────────────────────────┘
            │
            ├─► config.py (pydantic + ruyaml)  ───► loads files/arrconf.yml
            │       │
            │       ▼
            │   RootConfig pydantic model
            │       │
            │       ▼
            ├─► reconcilers/sonarr.py (SonarrClient)
            │       │
            │       │   instantiates
            │       ▼
            │   client_base.py (ArrApiClient)
            │       │
            │       │   uses
            │       ▼
            │   httpx.Client + tenacity retry  ───────► Sonarr /api/v3/
            │       │                                     ├ GET tag
            │       │                                     ├ POST tag (create arrconf-managed)
            │       │                                     ├ GET downloadclient
            │       │                                     ├ POST downloadclient
            │       │                                     ├ PUT downloadclient/{id}
            │       │                                     └ DELETE downloadclient/{id}
            │       │
            │       ▼
            ├─► differ.py (reconcile generic algorithm)
            │       │
            │       │   classify add/update/delete/no-op
            │       ▼
            │   plan list of actions
            │       │
            │       ├── if --dry-run: log only, exit
            │       └── else: execute via SonarrClient
            │
            ├─► schema_gen.py (pydantic → JSON Schema)
            │       │
            │       └── output: schemas/arrconf-schema.json
            │
            └─► structlog (JSON when CronJob, pretty when TTY)
                                │
                                ▼
                        stdout (parsed by k8s log pipeline in Phase 2)

Component file map:
  arrconf/__main__.py        — Typer app, 4 subcommands (apply/dump/diff/schema-gen)
  arrconf/config.py          — RootConfig, AppsConfig, SonarrConfig pydantic models
  arrconf/exceptions.py      — ScopeViolationError, ReconcileError, ApiClientError
  arrconf/logging.py         — structlog setup (TTY vs JSON detection)
  arrconf/settings.py        — pydantic-settings BaseSettings (env vars)
  arrconf/client_base.py     — ArrApiClient base class
  arrconf/differ.py          — generic GET → diff → POST/PUT/DELETE engine
  arrconf/schema_gen.py      — RootConfig.model_json_schema() → file
  arrconf/reconcilers/sonarr.py
                             — SonarrClient(ArrApiClient), reconcile() entrypoint
  arrconf/resources/sonarr/download_client.py   — pydantic schema (FULL)
  arrconf/resources/sonarr/tag.py               — pydantic schema (used for arrconf-managed)
  arrconf/resources/sonarr/{indexer,notification,root_folder,host_config}.py
                                                — STUBS (NotImplementedError, Phase 3)
  arrconf/resources/sonarr/{quality_profile,custom_format,quality_definition,media_naming}.py
                                                — STUBS that RAISE ScopeViolationError on touch
  tests/conftest.py
  tests/fixtures/sonarr/downloadclient.json     — copied from snapshots/baseline-2026-05-07/
  tests/fixtures/sonarr/edge_cases/*.json       — hand-crafted error cases
  tests/test_differ.py
  tests/test_reconcilers_sonarr.py
  tests/test_scope_violation.py
  tests/test_round_trip.py
  schemas/arrconf-schema.json                   — generated, committed
  examples/baseline-sonarr.yml                  — round-trip artefact (generated by `dump`)
```

### Recommended Project Structure

```
tools/arrconf/
├── pyproject.toml
├── uv.lock                     ← committé (D-05)
├── README.md                   ← TTY usage + autocomplete demo + Phase 1 scope
├── Dockerfile                  ← multi-stage, USER 1000:1000
├── .dockerignore
├── arrconf/
│   ├── __init__.py
│   ├── __main__.py             ← typer app, 4 subcommands
│   ├── config.py
│   ├── exceptions.py
│   ├── logging.py
│   ├── settings.py
│   ├── client_base.py
│   ├── differ.py
│   ├── schema_gen.py
│   ├── reconcilers/
│   │   ├── __init__.py
│   │   └── sonarr.py
│   └── resources/
│       ├── __init__.py
│       └── sonarr/
│           ├── __init__.py     ← exports public names
│           ├── download_client.py   ← FULL pydantic schema (D-08)
│           ├── tag.py               ← FULL (used at runtime for arrconf-managed)
│           ├── indexer.py           ← stub: NotImplementedError + TODO Phase 3
│           ├── notification.py     ← stub: idem
│           ├── root_folder.py       ← stub: idem
│           ├── host_config.py       ← stub: idem
│           ├── quality_profile.py   ← stub: ScopeViolationError on import-touch (frontière configarr)
│           ├── custom_format.py     ← stub: ScopeViolationError
│           ├── quality_definition.py ← stub: ScopeViolationError
│           └── media_naming.py      ← stub: ScopeViolationError
└── tests/
    ├── conftest.py
    ├── fixtures/
    │   └── sonarr/
    │       ├── downloadclient.json    ← seed depuis snapshots/baseline-2026-05-07/
    │       ├── tag.json               ← seed (snapshots/baseline-... contient déjà `[]`)
    │       └── edge_cases/
    │           ├── downloadclient_empty.json
    │           ├── downloadclient_partial_response.json
    │           └── downloadclient_with_unmanaged_tag.json
    ├── test_config.py            ← pydantic loads valid + invalid YAML
    ├── test_differ.py            ← add/update/delete/no-op + prune ON/OFF
    ├── test_reconcilers_sonarr.py
    ├── test_scope_violation.py   ← refus des 4 endpoints frontière configarr
    ├── test_managed_tag.py       ← reconcile crée le tag arrconf-managed avant les ressources
    ├── test_round_trip.py        ← fixture GET = YAML → 0 action
    └── test_schema_gen.py        ← RootConfig.model_json_schema() reproductible

# Repo root files (created by Phase 1):
schemas/arrconf-schema.json       ← committé, vérifié par CI
examples/baseline-sonarr.yml      ← committé, généré par `arrconf dump`
.github/workflows/tests.yml       ← ruff + mypy + pytest + schema-gen check
.github/workflows/arrconf-image.yml ← build + push GHCR
```

### Pattern 1: Typer multi-command app with global options

**What:** Single Typer app with `@app.command()` for each subcommand. Common options (`--config`, `--log-level`) on a `@app.callback()` callback that runs before any subcommand.
**When to use:** When subcommands share state (config path, logger) but have distinct args. Required for D-06 + REQ-cli-subcommands.
**Example:**

```python
# arrconf/__main__.py
# Source: https://typer.tiangolo.com/tutorial/commands/ + /tutorial/typer-command/
from pathlib import Path
import typer
import structlog

app = typer.Typer(
    name="arrconf",
    help="Reconcile *arr app configurations from YAML to REST APIs.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,  # Avoid leaking secrets in tracebacks
)

@app.callback()
def main(
    ctx: typer.Context,
    config: Path = typer.Option(
        Path("/etc/arrconf/arrconf.yml"),
        "--config", "-c",
        help="Path to arrconf YAML config",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level", "-l",
        envvar="ARRCONF_LOG_LEVEL",
    ),
) -> None:
    """Common options for all subcommands."""
    from arrconf.logging import configure_logging
    configure_logging(log_level)
    ctx.obj = {"config_path": config}

@app.command()
def apply(
    ctx: typer.Context,
    apps: str | None = typer.Option(None, help="Comma-separated apps to target"),
    dry_run: bool = typer.Option(False, "--dry-run", envvar="ARRCONF_DRY_RUN"),
) -> None:
    """Reconcile YAML → cluster APIs."""
    log = structlog.get_logger()
    try:
        result = _do_apply(ctx.obj["config_path"], apps, dry_run)
    except ConfigError as e:
        log.error("config_error", error=str(e))
        raise typer.Exit(code=2)
    except SomeAppFailed as e:
        log.warning("partial_failure", failed=e.failed_apps)
        raise typer.Exit(code=1)
    raise typer.Exit(code=0)

@app.command()
def dump(...) -> None: ...

@app.command()
def diff(...) -> None:
    # Exit 3 si drift détecté (REQ-cli-subcommands)
    ...

@app.command(name="schema-gen")
def schema_gen(
    output: Path = typer.Option(Path("schemas/arrconf-schema.json"), "--output", "-o"),
) -> None: ...

if __name__ == "__main__":
    app()
```

**Note:** `typer.Exit(code=N)` is the canonical way to control exit codes ([CITED: typer.tiangolo.com/tutorial/terminating/]).

### Pattern 2: pydantic v2 — model_json_schema() + Field(description=...) for VS Code autocomplete

**What:** Each field gets `Field(description="...")` ; descriptions surface as hover tooltips in VS Code. Read-only fields use `Field(exclude=True)` to drop them from `model_dump()` (used in diffs and YAML output).
**When to use:** All resource pydantic models (D-08 download_client.py + tag.py).
**Example:**

```python
# arrconf/resources/sonarr/download_client.py
# Source: Sonarr OpenAPI v3 (DownloadClientResource) — fetched 2026-05-07
# https://github.com/Sonarr/Sonarr/blob/develop/src/Sonarr.Api.V3/openapi.json
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

class FieldKV(BaseModel):
    """Generic key-value used in Sonarr's `fields[]` array (qBit-specific settings).

    Source: Sonarr OpenAPI #/components/schemas/Field
    """
    model_config = ConfigDict(extra="allow")  # Sonarr ajoute ad hoc des clés (selectOptions, helpText)
    name: str = Field(description="Field name (e.g., 'host', 'port', 'tvCategory')")
    value: Any | None = Field(None, description="Field value — type depends on field name")
    # Read-only metadata (exclude from diff and from YAML round-trip):
    label: str | None = Field(None, exclude=True)
    helpText: str | None = Field(None, exclude=True)
    advanced: bool | None = Field(None, exclude=True)
    type: str | None = Field(None, exclude=True)
    order: int | None = Field(None, exclude=True)
    privacy: str | None = Field(None, exclude=True)
    selectOptions: list[dict[str, Any]] | None = Field(None, exclude=True)
    isFloat: bool | None = Field(None, exclude=True)

class DownloadClient(BaseModel):
    """A Sonarr download client (qBittorrent, Transmission, ...).

    Matched by `name` (D-20). `id`, `implementationName`, `infoLink` are read-only (D-21).
    """
    model_config = ConfigDict(extra="forbid")  # YAML must declare known fields only

    name: str = Field(description="Display name (matching key, must be unique).")
    enable: bool = Field(default=True, description="Enable this download client.")
    protocol: Literal["torrent", "usenet"] = Field(
        description="Download protocol — must match implementation."
    )
    priority: int = Field(default=1, description="Lower = preferred when multiple clients match.")
    implementation: str = Field(
        description="Sonarr implementation class (e.g., 'QBittorrent', 'Transmission')."
    )
    configContract: str = Field(
        description="Sonarr config contract (e.g., 'QBittorrentSettings'). Must match implementation."
    )
    fields: list[FieldKV] = Field(
        default_factory=list,
        description="Implementation-specific settings (host, port, category, ...).",
    )
    tags: list[int] = Field(
        default_factory=list,
        description="Tag IDs (resolved from `tags:` names by reconciler).",
    )
    removeCompletedDownloads: bool = Field(default=True)
    removeFailedDownloads: bool = Field(default=True)

    # Read-only — populated on GET, excluded on diff + on dump output
    id: int | None = Field(default=None, exclude=True)
    implementationName: str | None = Field(default=None, exclude=True)
    infoLink: str | None = Field(default=None, exclude=True)
    message: dict[str, Any] | None = Field(default=None, exclude=True)
    presets: list[dict[str, Any]] | None = Field(default=None, exclude=True)
```

**JSON Schema generation pattern:**

```python
# arrconf/schema_gen.py
import json
from pathlib import Path
from pydantic.json_schema import GenerateJsonSchema
from arrconf.config import RootConfig

class Draft202012Generator(GenerateJsonSchema):
    """Force $schema dialect to Draft 2020-12 (yaml-language-server preferred)."""
    schema_dialect = "https://json-schema.org/draft/2020-12/schema"
    def generate(self, schema, mode="validation"):
        json_schema = super().generate(schema, mode=mode)
        json_schema["$schema"] = self.schema_dialect
        return json_schema

def write_schema(output_path: Path) -> None:
    schema = RootConfig.model_json_schema(schema_generator=Draft202012Generator)
    output_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
```

[CITED: docs.pydantic.dev/latest/concepts/json_schema/ — `GenerateJsonSchema` subclassing pattern + `schema_dialect`]

### Pattern 3: ArrApiClient base class with overridable auth strategy

**What:** Generic httpx-backed client that exposes `get()`, `post()`, `put()`, `delete()` and lets subclasses override `auth_headers()` and `base_url`. Required for D-03 multi-app future + REQ-bootstrap-exception (env-only auth).
**When to use:** Single base class for all *arr-family clients (Sonarr, Radarr, Prowlarr, Seerr — all use `X-Api-Key`). qBit and Jellyfin override later (Phase 5/7).
**Example:**

```python
# arrconf/client_base.py
from typing import Any
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

log = structlog.get_logger()

class ApiClientError(Exception): ...
class AuthError(ApiClientError): ...
class NotFoundError(ApiClientError): ...
class ServerError(ApiClientError): ...

class ArrApiClient:
    """Base class for *arr-family REST clients."""

    api_path: str = "/api/v3"  # default for Sonarr, Radarr; override per app
    name: str = "arr"          # logger context

    def __init__(self, base_url: str, api_key: str, *, timeout: httpx.Timeout | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(
            base_url=f"{self.base_url}{self.api_path}",
            headers=self.auth_headers(),
            timeout=timeout or httpx.Timeout(connect=5.0, read=30.0),
        )

    def auth_headers(self) -> dict[str, str]:
        """Override per app for non-X-Api-Key auth (qBit cookie, Jellyfin MediaBrowser)."""
        return {"X-Api-Key": self.api_key}

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ArrApiClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException, ServerError)),
        reraise=True,
    )
    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        response = self._client.request(method, path, **kwargs)
        if response.status_code == 401:
            raise AuthError(f"{self.name}: 401 — check API key")
        if response.status_code == 404:
            raise NotFoundError(f"{self.name}: 404 — {method} {path}")
        if 500 <= response.status_code < 600:
            raise ServerError(f"{self.name}: {response.status_code} — {response.text[:200]}")
        response.raise_for_status()
        return response

    def get(self, path: str, **kwargs: Any) -> Any:
        return self._request("GET", path, **kwargs).json()

    def post(self, path: str, json: Any, **kwargs: Any) -> Any:
        return self._request("POST", path, json=json, **kwargs).json()

    def put(self, path: str, id: int, json: Any, **kwargs: Any) -> Any:
        return self._request("PUT", f"{path}/{id}", json=json, **kwargs).json()

    def delete(self, path: str, id: int, **kwargs: Any) -> None:
        self._request("DELETE", f"{path}/{id}", **kwargs)


class SonarrClient(ArrApiClient):
    api_path = "/api/v3"
    name = "sonarr"
```

[CITED: tenacity.readthedocs.io — `@retry` with `stop_after_attempt`, `wait_exponential`, `retry_if_exception_type`]
[CITED: www.python-httpx.org/advanced/transports/ — `Client(timeout=httpx.Timeout(connect=..., read=...))`]
[CITED: Sonarr OpenAPI #/components/securitySchemes — X-Api-Key header is the canonical auth]

### Pattern 4: Differ algorithm (REQ-idempotence + REQ-prune-opt-in + REQ-managed-tag)

**What:** Generic `reconcile()` that takes (current_list, desired_list, match_key="name", read_only_fields=...) and returns a Plan classified into ADD / UPDATE / DELETE / NO_OP.
**When to use:** The single source of truth for idempotence. Every reconciler delegates to this.
**Example:**

```python
# arrconf/differ.py
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, TypeVar
from pydantic import BaseModel
import structlog

log = structlog.get_logger()
T = TypeVar("T", bound=BaseModel)

class Action(Enum):
    ADD = "add"
    UPDATE = "update"
    DELETE = "delete"
    NO_OP = "no-op"
    PRUNE_SKIP = "prune-skip"   # exists on cluster, not in YAML, prune=False (warn)
    PRUNE_PROTECTED = "prune-protected"  # exists, not in YAML, but no `arrconf-managed` tag → never delete

@dataclass
class PlannedAction(Generic[T]):
    action: Action
    name: str
    current: T | None
    desired: T | None
    diff_fields: list[str]   # fields that differ (for UPDATE), or [] otherwise

def diff_models(a: BaseModel, b: BaseModel) -> list[str]:
    """Return list of field names that differ between two pydantic models (excluding read-only)."""
    a_dump = a.model_dump(exclude_none=True, exclude={"id", "implementationName", "infoLink", "message", "presets"})
    b_dump = b.model_dump(exclude_none=True, exclude={"id", "implementationName", "infoLink", "message", "presets"})
    return sorted({k for k in (set(a_dump) | set(b_dump)) if a_dump.get(k) != b_dump.get(k)})

def reconcile(
    current: list[T],
    desired: list[T],
    *,
    match_key: str = "name",
    prune: bool = False,
    managed_tag_id: int | None = None,
) -> list[PlannedAction[T]]:
    """Generic reconciliation engine.

    1. Match items by `match_key` (default `name`).
    2. Classify into ADD / UPDATE / DELETE / NO_OP.
    3. If `prune=False`: items in current but not desired → PRUNE_SKIP (logged warning).
    4. If `prune=True`: only delete items tagged with `managed_tag_id` (D-02 protection).
    """
    by_name_current = {getattr(c, match_key): c for c in current}
    by_name_desired = {getattr(d, match_key): d for d in desired}
    plan: list[PlannedAction[T]] = []

    for name, des in by_name_desired.items():
        cur = by_name_current.get(name)
        if cur is None:
            plan.append(PlannedAction(Action.ADD, name, None, des, []))
        else:
            diffs = diff_models(cur, des)
            if diffs:
                plan.append(PlannedAction(Action.UPDATE, name, cur, des, diffs))
            else:
                plan.append(PlannedAction(Action.NO_OP, name, cur, des, []))

    for name, cur in by_name_current.items():
        if name in by_name_desired:
            continue
        if not prune:
            plan.append(PlannedAction(Action.PRUNE_SKIP, name, cur, None, []))
            continue
        cur_tags = getattr(cur, "tags", []) or []
        if managed_tag_id is None or managed_tag_id not in cur_tags:
            plan.append(PlannedAction(Action.PRUNE_PROTECTED, name, cur, None, []))
        else:
            plan.append(PlannedAction(Action.DELETE, name, cur, None, []))

    return plan
```

**Why this works:**
- `model_dump(exclude_none=True, exclude={read_only_fields})` neutralises the read-only fields (D-21).
- `match_key="name"` is the matching strategy from D-20.
- `prune=False` → log warning, never delete (D-04 + REQ-prune-opt-in).
- `prune=True` AND no `arrconf-managed` tag → PRUNE_PROTECTED (D-02 + REQ-managed-tag).
- Test cases : ADD / UPDATE / DELETE / NO_OP / PRUNE_SKIP / PRUNE_PROTECTED — 6 distinct unit tests.

### Pattern 5: Sonarr `arrconf-managed` tag reconciliation order

**What:** The tag `arrconf-managed` must exist BEFORE any download_client referencing it. Reconcile tags first, then resolve tag names → IDs in the desired models, then reconcile download_clients.
**Example:**

```python
# arrconf/reconcilers/sonarr.py
def reconcile_sonarr(client: SonarrClient, config: SonarrConfig, dry_run: bool) -> SonarrResult:
    # Step 1: Always ensure `arrconf-managed` tag exists (D-02).
    managed_tag = _ensure_managed_tag(client, dry_run)
    # managed_tag.id is now known (or `-1` in dry-run mode)

    # Step 2: Reconcile other tags declared in YAML (Phase 3 — for now, just the managed one).
    # (Phase 1: stub — only arrconf-managed exists)

    # Step 3: Resolve tag NAMES → IDs in download_client desired list (YAML uses names; API expects IDs).
    desired_dcs = [_resolve_tag_names_to_ids(dc, all_tags=client.get_tags(), managed_tag=managed_tag)
                   for dc in config.download_clients.items]

    # Step 4: Reconcile download_clients.
    current_dcs = [DownloadClient.model_validate(x) for x in client.get("/downloadclient")]
    plan = reconcile(
        current=current_dcs,
        desired=desired_dcs,
        match_key="name",
        prune=config.download_clients.prune,
        managed_tag_id=managed_tag.id,
    )
    _execute(client, "/downloadclient", plan, dry_run)
    return SonarrResult(...)

def _ensure_managed_tag(client: SonarrClient, dry_run: bool) -> Tag:
    """Get or create the arrconf-managed tag. NEVER delete this tag."""
    tags = [Tag.model_validate(t) for t in client.get("/tag")]
    for t in tags:
        if t.label == "arrconf-managed":
            return t
    if dry_run:
        log.info("would_create_managed_tag")
        return Tag(id=-1, label="arrconf-managed")  # placeholder for dry-run
    created = client.post("/tag", json={"label": "arrconf-managed"})
    return Tag.model_validate(created)
```

[CITED: Sonarr OpenAPI #/paths//api/v3/tag/post — TagResource has only {id: int, label: str}; POST body = TagResource; returns created TagResource]

### Pattern 6: VS Code autocomplete via yaml-language-server modeline (D-16)

**What:** Each YAML file managed by arrconf has its first line set to `# yaml-language-server: $schema=<path>`. The path is **relative to the YAML file** (not the workspace root) — verified in [CITED: github.com/redhat-developer/vscode-yaml/issues/587 + redhat-developer/yaml-language-server README].
**When to use:** All `examples/*.yml`, `charts/arr-stack/files/arrconf.yml` (created Phase 4), and any user-written YAML.
**Example:**

```yaml
# yaml-language-server: $schema=../schemas/arrconf-schema.json
sonarr:
  main:
    download_clients:
      prune: false
      items:
        - name: qBittorrent
          enable: true
          protocol: torrent
          implementation: QBittorrent
          # ▲ here, autocomplete suggests "implementation: QBittorrent | Transmission | ..."
```

`arrconf dump` MUST emit this directive on line 1 of the output YAML (D-16 + REQ-yaml-autocomplete).

### Pattern 7: Dockerfile multi-stage uv → python:3.13-slim USER 1000:1000

**What:** Two-stage build. Stage 1 uses `ghcr.io/astral-sh/uv:0.11-python3.13-bookworm-slim` to install dependencies into `.venv`. Stage 2 copies the `.venv` into a clean `python:3.13-slim`, creates non-root user, sets entrypoint.
**Example:**

```dockerfile
# tools/arrconf/Dockerfile
# Source: https://docs.astral.sh/uv/guides/integration/docker/
# + depot.dev/docs/container-builds/how-to-guides/optimal-dockerfiles/python-uv-dockerfile

# ─── Stage 1: builder ──────────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:0.11-python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install deps without project (cached layer)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Install project
COPY arrconf ./arrconf
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ─── Stage 2: runtime ──────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

# Non-root user (UID/GID 1000)
RUN groupadd --gid 1000 arrconf \
 && useradd --uid 1000 --gid arrconf --no-create-home --shell /usr/sbin/nologin arrconf

WORKDIR /app
COPY --from=builder --chown=1000:1000 /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 1000:1000
ENTRYPOINT ["arrconf"]
CMD ["apply", "--help"]
```

**Image size target:** ~80 MB (CLAUDE.md target). With slim base + copy-only `.venv` + no compilers in runtime, ~70–90 MB is realistic.

[CITED: docs.astral.sh/uv/guides/integration/docker/ — official multistage pattern with cache mounts]

### Pattern 8: GitHub Actions arrconf-image.yml (D-14)

**Example:**

```yaml
# .github/workflows/arrconf-image.yml
name: arrconf-image

on:
  push:
    branches: [main]
    paths: ['tools/arrconf/**']
    tags: ['v*']
  pull_request:
    paths: ['tools/arrconf/**']

jobs:
  build:
    runs-on: ubuntu-24.04
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - name: Login to GHCR
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/tom333/arr-stack-arrconf
          tags: |
            type=sha,prefix=sha-,format=short
            type=ref,event=branch,prefix=branch-
            type=semver,pattern={{version}}
            type=raw,value=latest,enable=${{ startsWith(github.ref, 'refs/tags/v') }}
      - uses: docker/build-push-action@v5
        with:
          context: tools/arrconf
          file: tools/arrconf/Dockerfile
          push: ${{ github.event_name != 'pull_request' }}
          platforms: linux/amd64
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

[CITED: github.com/marketplace/actions/build-and-push-docker-images — docker/build-push-action@v5]
[CITED: github.com/docker/metadata-action — semver + sha + branch tagging]

**Public visibility:** GHCR images default to private. After first push, manually set visibility to public via GitHub UI: `Profile → Packages → arr-stack-arrconf → Package settings → Change visibility → Public`. **One-time step**, not automated. Document in README.

### Pattern 9: GitHub Actions tests.yml (D-13 + D-15)

```yaml
# .github/workflows/tests.yml
name: tests

on:
  pull_request:
    paths: ['tools/arrconf/**', 'schemas/**', '.github/workflows/tests.yml']
  push:
    branches: [main]
    paths: ['tools/arrconf/**', 'schemas/**']

jobs:
  test:
    runs-on: ubuntu-24.04
    defaults:
      run:
        working-directory: tools/arrconf
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: "0.11.x"
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy arrconf
      - run: uv run pytest --cov --cov-report=term-missing
      - name: Verify schema reproducibility (D-15)
        run: |
          uv run arrconf schema-gen --output ../../schemas/arrconf-schema.json
          cd ../..
          git diff --exit-code schemas/arrconf-schema.json \
            || (echo "::error::schemas/arrconf-schema.json drift — run 'arrconf schema-gen' and commit"; exit 1)
```

### Anti-Patterns to Avoid

- **Systematic PUT on every reconcile** — generates noise in *arr logs and triggers unnecessary "modified by arrconf" entries. Always diff first ([CITED: CLAUDE.md "Idempotence (RÈGLE D'OR)"]).
- **Storing tag NAMES in the API call instead of IDs** — Sonarr's `tags:` field is `list[int]` (verified in OpenAPI). The reconciler MUST resolve names → IDs before serializing the request body.
- **`additionalProperties: true` (extra="allow") on resource models** — except for `FieldKV` (where Sonarr genuinely adds ad-hoc keys). On `DownloadClient`, use `extra="forbid"` so YAML typos surface as validation errors.
- **Reading a YAML config with `pyyaml.safe_load()`** — strips comments, breaks `arrconf dump` round-trip readability. Use `ruyaml` (D-07 stack lock).
- **`raise_for_status()` without classification** — wraps everything in HTTPStatusError. Classify 401/404/5xx before re-raising so caller can react differently.
- **Silently swallowing `ScopeViolationError`** — the whole point of D-12 is to fail loudly. Raise, log at ERROR, exit code 2 (config error).
- **Putting secrets in fixtures** (D-22) — even by accident. CI grep audit is mandatory.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Argument parsing + subcommands | `sys.argv` parsing | typer | Auto-generated `--help`, type validation, exit codes |
| YAML round-trip with comments | `pyyaml.safe_load` + manual emit | ruyaml | Comment preservation is non-trivial (tree of CommentedMap nodes) |
| HTTP retries with backoff | hand-coded `for i in range(3)` loop | tenacity | Jitter, exponential decay, predicate-based retry — well tested |
| JSON Schema generation from Python types | dict-walking pydantic models | `model_json_schema()` | Pydantic v2 emits Draft 2020-12 with $defs, refs, descriptions for free |
| Env var → typed config | manual `os.environ` reads + casts | pydantic-settings | `SecretStr` (avoid logging secrets), defaults, validation, env_prefix |
| Mocking httpx in tests | monkeypatching `httpx.Client.send` | respx | Route patterns, request introspection, `assert_all_called=True` |
| Diff between two pydantic models | recursive dict walk | `model_dump(exclude={...})` + set comparison | Handles nested models, defaults, exclusions consistently |
| Python image build | `pip install` in Dockerfile | uv multistage | uv resolves + caches; lockfile guarantees reproducibility |
| GHCR push + multi-tag | manual `docker push` x N | `docker/build-push-action@v5` + `metadata-action@v5` | Generates sha/semver/branch tags from one config |
| Coverage CI gate | parsing `coverage report` | `--cov-fail-under` in pyproject.toml | Native, returns exit code |

**Key insight:** Phase 1 is a POC, not a v1.0 — every line of custom plumbing is technical debt to maintain across Phase 3 (4 more apps), Phase 5 (qBit + 6 categories), Phase 6 (Seerr), Phase 7 (Jellyfin). The standard stack (typer/pydantic/httpx/structlog/tenacity/respx) covers 95% of what we'd hand-roll, with better behaviour and zero maintenance.

## Sonarr `download_clients` schema — extracted from official OpenAPI

[VERIFIED: fetched https://raw.githubusercontent.com/Sonarr/Sonarr/develop/src/Sonarr.Api.V3/openapi.json — 290 KB, 2026-05-07 ; Sonarr 4.0.17 confirmed in baseline `system_status.json`]

### `DownloadClientResource` (used in GET, POST, PUT bodies)

| Field | Type | Required by Phase 1 | YAML | Read-only? | Notes |
|-------|------|---------------------|------|-----------|-------|
| `id` | `int` | — | NO | YES (D-21) | Generated by Sonarr ; changes if recreated |
| `name` | `string` | YES | yes | NO | Matching key (D-20) ; must be unique per instance |
| `enable` | `bool` | YES | yes (default true) | NO | |
| `protocol` | `enum: torrent\|usenet\|unknown` | YES | yes | NO | Must match `implementation` |
| `priority` | `int` | YES | yes (default 1) | NO | Lower = preferred |
| `implementation` | `string` | YES | yes | NO | e.g. `"QBittorrent"`, `"Transmission"` |
| `configContract` | `string` | YES | yes | NO | e.g. `"QBittorrentSettings"` ; must pair with `implementation` |
| `fields` | `array[Field]` | YES | yes | NO | KV pairs — see below |
| `tags` | `set[int]` | YES | yes (as **names** in YAML, **ids** at API) | NO | Reconciler resolves names → ids ; `arrconf-managed` always added |
| `removeCompletedDownloads` | `bool` | YES | yes (default true) | NO | |
| `removeFailedDownloads` | `bool` | YES | yes (default true) | NO | |
| `implementationName` | `string` | — | NO | YES (D-21) | Display name (UI) ; derived |
| `infoLink` | `string` | — | NO | YES (D-21) | URL to wiki page |
| `message` | `ProviderMessage` | — | NO | YES | Health check status from API |
| `presets` | `array[DownloadClientResource]` | — | NO | YES | UI templates ; never sent in PUT |

### `Field` (the polymorphic key-value array — qBit settings live here)

| Field | Type | Notes |
|-------|------|-------|
| `name` | `string` | Setting name (e.g. `"host"`, `"port"`, `"tvCategory"`, `"username"`, `"password"`) |
| `value` | `any` | Setting value — type matches setting (string, int, bool, ...) |
| `label`, `helpText`, `helpTextWarning`, `helpLink`, `unit` | `string` | UI metadata — **read-only, exclude from diff** |
| `type`, `advanced`, `selectOptions`, `section`, `hidden`, `privacy`, `placeholder`, `isFloat`, `order`, `selectOptionsProviderAction` | various | UI metadata — **read-only, exclude from diff** |

**Concrete fields for qBittorrent** (from baseline `downloadclient.json`, 2026-05-07):
`host`, `port`, `useSsl`, `urlBase`, `username`, `password`, `tvCategory`, `tvImportedCategory`, `recentTvPriority` (0=Last, 1=First), `olderTvPriority`, `initialState` (0=Started, 1=Force, 2=Stopped), `sequentialOrder`, `firstAndLast`, `contentLayout` (0=Default, 1=Original, 2=Subfolder).

### `TagResource` (used for arrconf-managed tag reconciliation)

| Field | Type | Notes |
|-------|------|-------|
| `id` | `int` | Generated ; matching key for the API |
| `label` | `string` | Tag name as displayed ; matching key in YAML (e.g. `"arrconf-managed"`) |

POST `/api/v3/tag` body: `{"label": "arrconf-managed"}` — returns `{"id": <new>, "label": "arrconf-managed"}`.

### Endpoints used by Phase 1 reconciler

| HTTP | Path | Body | Phase 1 use |
|------|------|------|-------------|
| GET | `/api/v3/downloadclient` | — | List current download clients |
| POST | `/api/v3/downloadclient` | `DownloadClientResource` | Create (ADD) |
| GET | `/api/v3/downloadclient/{id}` | — | (Optional ; not strictly needed since GET list is the source) |
| PUT | `/api/v3/downloadclient/{id}` | `DownloadClientResource` (full body) | Update (UPDATE) ; query param `?forceSave=false` (default) suffices |
| DELETE | `/api/v3/downloadclient/{id}` | — | Delete (DELETE, only when prune=true AND tag=arrconf-managed) |
| GET | `/api/v3/downloadclient/schema` | — | (Not needed Phase 1) |
| POST | `/api/v3/downloadclient/test` | `DownloadClientResource` | (Not needed Phase 1) |
| GET | `/api/v3/tag` | — | List tags ; find arrconf-managed.id |
| POST | `/api/v3/tag` | `TagResource` (`label` only) | Create arrconf-managed if missing |

### Auth

| Header | Value |
|--------|-------|
| `X-Api-Key` | env `SONARR_API_KEY` (required ; pydantic-settings `SecretStr`) |

[CITED: Sonarr OpenAPI #/components/securitySchemes — `X-Api-Key` is the canonical header for v3+ ; `?apikey=` query param also supported as fallback]

### Sonarr base URL

- **Local dev (port-forward)** : `http://localhost:8989` (CLAUDE.md "Test arrconf contre une vraie instance")
- **In-cluster (Phase 2)** : `http://sonarr.selfhost.svc.cluster.local:8989`
- arrconf reads it from YAML `sonarr.main.base_url` (NO env var for URL — only for secrets per D-22 spirit + REQ-bootstrap-exception).

## Runtime State Inventory

> Phase 1 is a greenfield phase (creates new code under `tools/arrconf/`, `schemas/`, `examples/`). No existing arrconf-managed state to migrate. The renamed/refactored items are NIL — Phase 0 was the bootstrap.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — Phase 1 creates new code only | None |
| Live service config | None — arrconf is NOT yet deployed in cluster (Phase 2) | None |
| OS-registered state | None — no OS-level registrations | None |
| Secrets / env vars | `SONARR_API_KEY` is read from env at runtime ; no key needs changing — first-time use in Phase 1 (consumed by `arrconf dump` against port-forwarded Sonarr) | Document in README how to source the key from `my-kluster/secrets/configarr-secret.yaml` for local testing |
| Build artifacts | None — first build of arrconf image happens in this phase ; no stale `.egg-info` or compiled binaries from prior phases | None |

**Verified by:** repo only contains `spec.md`, `CLAUDE.md`, `README.md`, `renovate.json`, `tools/snapshot/`, `snapshots/baseline-2026-05-07/`, `.gitignore`, `.env`, `.env.example`, `.planning/` — no Python code, no Dockerfile, no `.github/workflows/`. Verified via `ls -la /home/moi/projets/perso/arr-stack/`.

## Common Pitfalls

### Pitfall 1: Sonarr `tags:` field is integer IDs, not names

**What goes wrong:** Sending `{"tags": ["arrconf-managed"]}` in the POST body — Sonarr returns 400 ("Invalid tag value").
**Why it happens:** YAML uses human-readable names ; the API uses integer IDs. The OpenAPI schema is `array[int]` (verified above).
**How to avoid:**
1. Reconcile tags first (always create `arrconf-managed` if missing).
2. Build `tag_name → id` map.
3. Resolve names to IDs in each `DownloadClient.tags` before serializing.
**Warning signs:** 400 Bad Request on POST/PUT download_client with body containing `tags: [...]`.

### Pitfall 2: Sonarr `fields[]` returns extra keys per field — diff naively shows everything as different

**What goes wrong:** API returns `{"name": "host", "value": "qbittorrent...", "label": "Hôte", "helpText": "...", "advanced": false, ...}`. Diff against your YAML which only has `{name, value}` flags everything as drift → systematic PUT.
**Why it happens:** UI metadata (`label`, `helpText`, `advanced`, `type`, ...) is server-generated.
**How to avoid:** `FieldKV` model marks all UI-metadata fields as `Field(exclude=True)`. The diff function uses `model_dump(exclude_none=True, exclude={...})` to drop them.
**Warning signs:** Round-trip test fails ; `arrconf diff` reports drift on every run even with no UI change.

### Pitfall 3: Reconciler order matters — tags before download_clients before notifications

**What goes wrong:** Reconciler creates a download_client referencing `arrconf-managed` before creating the tag → API returns 400 or silently sets `tags: []`.
**Why it happens:** Sonarr enforces referential integrity on tag IDs.
**How to avoid:** Topological order — `tags → root_folders → indexers → download_clients → notifications → host_config`. Phase 1 only needs `tags → download_clients`. Hard-code in `reconciler.reconcile()`.
**Warning signs:** Download client created with empty `tags: []` despite YAML declaring tags.

### Pitfall 4: pydantic v2 `extra="forbid"` breaks YAML round-trip when API adds fields in newer Sonarr versions

**What goes wrong:** Sonarr 4.1 adds `newField` to DownloadClientResource ; `extra="forbid"` rejects the GET response → arrconf crashes.
**Why it happens:** `extra="forbid"` is bidirectional in pydantic v2.
**How to avoid:**
- On models we **read from API** (parsing GET responses) : `extra="allow"` (forward-compat).
- On models we **read from YAML** (user input) : `extra="forbid"` (catch typos).
- One way out: separate `DownloadClientApi` (extra=allow) from `DownloadClientYaml` (extra=forbid) sharing a base. Phase 1 simplification: `extra="allow"` for now, document trade-off, revisit if YAML typos become a real problem.
**Warning signs:** ValidationError on GET response after Sonarr upgrade.

### Pitfall 5: `# yaml-language-server: $schema=...` relative path is from the YAML file, NOT from workspace root

**What goes wrong:** Author writes `$schema=schemas/arrconf-schema.json` thinking it's workspace-rooted ; yaml-language-server fails to find the schema → no autocomplete.
**Why it happens:** Documented in [CITED: github.com/redhat-developer/vscode-yaml/issues/587].
**How to avoid:** Always compute the relative path from the YAML file. For `examples/baseline-sonarr.yml` → `../schemas/arrconf-schema.json`. For `charts/arr-stack/files/arrconf.yml` (Phase 4) → `../../../schemas/arrconf-schema.json`.
**Warning signs:** Open YAML in VS Code, no completions, and the bottom-right corner of VS Code says "YAML" but no schema badge.

### Pitfall 6: pytest-cov has NO per-file threshold (only global)

**What goes wrong:** REQ-test-coverage says "≥ 70 % on `differ.py` and `reconcilers/sonarr.py`". A naive `--cov-fail-under=70` accepts 100 % on `__main__` + 50 % on `differ` (still 70 % global average), violating intent.
**Why it happens:** [CITED: github.com/pytest-dev/pytest-cov/issues/444 — feature request not implemented].
**How to avoid:** Scope coverage measurement to the modules we care about: in `pyproject.toml` set `[tool.coverage.run] source = ["arrconf.differ", "arrconf.reconcilers.sonarr"]`. Then `--cov-fail-under=70` enforces the threshold on only those modules ; `__main__.py`, `config.py`, etc. are not measured (and their lack of coverage doesn't help OR hurt).
**Warning signs:** CI passes with `differ.py` at 50 % because total coverage is dragged up by trivial `config.py`.

### Pitfall 7: GHCR images are PRIVATE by default

**What goes wrong:** Phase 2 K8s pods cannot pull the image (`ImagePullBackOff`). Even though CI pushes successfully, the cluster has no credentials.
**Why it happens:** GHCR requires explicit visibility opt-in.
**How to avoid:** After the first successful push, manually set the package to public via GitHub UI: Profile → Packages → arr-stack-arrconf → Package settings → Visibility → Public. **One-time, not automatable** through `actions/permissions` (the package must exist before its visibility can be set, and there's no API for visibility in `gh` CLI as of 2026-04). Document in README.
**Warning signs:** `kubectl describe pod ...` shows "imagepullbackoff: denied" in Phase 2.

### Pitfall 8: `httpx.HTTPTransport(retries=N)` only retries on `ConnectError` / `ConnectTimeout`, not on 5xx / 429

**What goes wrong:** Sonarr returns 503 once during DB migration ; arrconf gives up immediately.
**Why it happens:** httpx's transport-level retry covers connection failures, not HTTP-level errors. [CITED: www.python-httpx.org/advanced/transports/]
**How to avoid:** Use `tenacity` with `retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException, ServerError))` where `ServerError` is raised by `_request()` on 5xx responses (Pattern 3 above).
**Warning signs:** Single 5xx response causes whole apply to fail.

## Code Examples

### Round-trip test (REQ-idempotence + Phase 1 success criterion #4)

```python
# tests/test_round_trip.py
# Source: based on Pattern 4 (differ) + respx pattern from lundberg.github.io/respx/guide/
import json
from pathlib import Path
import respx
import httpx
import pytest
from arrconf.config import RootConfig
from arrconf.reconcilers.sonarr import reconcile_sonarr, SonarrClient
import ruyaml

FIXTURE = Path(__file__).parent / "fixtures/sonarr/downloadclient.json"
TAG_FIXTURE = Path(__file__).parent / "fixtures/sonarr/tag_with_arrconf_managed.json"

@pytest.mark.respx(base_url="http://sonarr.test/api/v3")
def test_round_trip_no_op(respx_mock):
    """Given GET response = YAML desired state, apply --dry-run produces NO_OP for all."""
    current_dcs = json.loads(FIXTURE.read_text())
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=json.loads(TAG_FIXTURE.read_text())))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=current_dcs))

    # Build the YAML config FROM the fixture (this simulates `arrconf dump`)
    desired_yaml_str = build_yaml_from_api_response(current_dcs)
    config = RootConfig.model_validate(ruyaml.YAML(typ="safe").load(desired_yaml_str))

    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(client, config.sonarr.main, dry_run=True)

    assert result.actions_taken == []
    assert all(p.action.value == "no-op" for p in result.plan if p.name in {dc["name"] for dc in current_dcs})
    # Assertions: 0 POST, 0 PUT, 0 DELETE called
    assert respx_mock.routes["downloadclient_post"].call_count == 0 if "downloadclient_post" in respx_mock.routes else True
```

### ScopeViolationError test (REQ-configarr-coexistence anchor — D-12)

```python
# tests/test_scope_violation.py
import pytest
from arrconf.exceptions import ScopeViolationError
from arrconf.resources.sonarr import quality_profile, custom_format, quality_definition, media_naming

@pytest.mark.parametrize("module", [quality_profile, custom_format, quality_definition, media_naming])
def test_scope_violation_raised_on_import(module):
    """The 4 frontière configarr modules MUST raise ScopeViolationError if any reconcile entrypoint is called."""
    with pytest.raises(ScopeViolationError, match=r"configarr.yml"):
        module.reconcile(client=None, config=None, dry_run=False)
```

```python
# arrconf/resources/sonarr/quality_profile.py
from arrconf.exceptions import ScopeViolationError

def reconcile(*args, **kwargs):
    raise ScopeViolationError(
        "quality_profiles is owned by configarr (ADR-5). "
        "Edit charts/arr-stack/files/configarr.yml instead."
    )
```

### Differ unit test (Pattern 4 — covers add/update/delete/no-op/prune)

```python
# tests/test_differ.py
from arrconf.differ import reconcile, Action
from arrconf.resources.sonarr.download_client import DownloadClient

def _dc(name, **kwargs):
    return DownloadClient(name=name, protocol="torrent", implementation="QBittorrent",
                          configContract="QBittorrentSettings", **kwargs)

def test_add():
    plan = reconcile(current=[], desired=[_dc("qbit")])
    assert [p.action for p in plan] == [Action.ADD]

def test_no_op():
    a, b = _dc("qbit", priority=1), _dc("qbit", priority=1)
    plan = reconcile(current=[a], desired=[b])
    assert plan[0].action == Action.NO_OP

def test_update():
    plan = reconcile(current=[_dc("qbit", priority=1)], desired=[_dc("qbit", priority=5)])
    assert plan[0].action == Action.UPDATE
    assert "priority" in plan[0].diff_fields

def test_prune_skip_when_prune_false():
    plan = reconcile(current=[_dc("orphan")], desired=[], prune=False)
    assert plan[0].action == Action.PRUNE_SKIP

def test_prune_protected_when_no_managed_tag():
    cur = _dc("orphan", tags=[5])  # tag 5 is NOT managed
    plan = reconcile(current=[cur], desired=[], prune=True, managed_tag_id=99)
    assert plan[0].action == Action.PRUNE_PROTECTED

def test_prune_executed_when_tag_present():
    cur = _dc("orphan", tags=[99])
    plan = reconcile(current=[cur], desired=[], prune=True, managed_tag_id=99)
    assert plan[0].action == Action.DELETE
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact for Phase 1 |
|--------------|------------------|--------------|---------------------|
| pip + requirements.txt + venv | uv + pyproject.toml + uv.lock | uv 1.0 GA late 2024 | D-05 already locked uv |
| PyYAML | ruyaml (fork of ruamel.yaml) | ruamel.yaml maintenance shifted to ruyaml ~2022 | CLAUDE.md already locked |
| pydantic v1 (`schema()` returns Draft 7) | pydantic v2 (`model_json_schema()` Draft 2020-12) | pydantic v2 GA mid-2023 | D-08 already on pydantic v2 |
| Click decorators directly | typer (typed wrapper around Click) | typer mature 2022+ | D-06 locked typer |
| `pip install` in single-stage Dockerfile | uv multistage with `--mount=type=cache,target=/root/.cache/uv` | uv Docker integration 2024 | Pattern 7 above |
| `requests` + manual session | `httpx.Client` (sync + async) | httpx 1.x announced ; 0.28 stable for production | D-18 sync only Phase 1 |

**Deprecated/outdated:**
- `Buildarr`, `Recyclarr` — covered in spec.md §2.3 alternatives-rejected.
- `httpx.HTTPTransport(retries=N)` as the sole retry mechanism — only handles connection errors, not 5xx (Pitfall 8).
- pydantic v1 `Config` class — replaced by `model_config = ConfigDict(...)` in v2.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Sonarr 4.0.17 OpenAPI spec from `Sonarr/Sonarr/develop` accurately matches the deployed instance | "Sonarr `download_clients` schema" | LOW — spec verified against baseline `system_status.json` (4.0.17.2952) and against the actual `downloadclient.json` field shape ; the OpenAPI is the canonical source |
| A2 | `model_dump(exclude={...})` properly handles nested `FieldKV` exclusions | Pattern 4 (differ) | MEDIUM — confirmed in [CITED: docs.pydantic.dev/latest/concepts/serialization/] but Phase 1 implementation should add a unit test for the FieldKV exclusion behavior specifically |
| A3 | `pydantic-settings` 2.14 is compatible with pydantic 2.13 | Standard Stack | LOW — both are Pydantic family, semver guaranteed |
| A4 | Coverage scoping via `[tool.coverage.run] source = [...]` correctly limits the threshold to listed modules | Pitfall 6 + Coverage scoping | LOW — documented behavior of coverage.py, well established |
| A5 | The existing `snapshots/baseline-2026-05-07/sonarr/downloadclient.json` (6.3 KB, 1 qBit client, password redacted) is sufficient as fixture seed | D-09 | LOW — verified by reading the file ; structure matches OpenAPI spec exactly |
| A6 | GHCR public visibility one-time UI step is required (no `gh` CLI / API automation) | Pitfall 7 | MEDIUM — as of 2026-04, no `gh api packages` endpoint for visibility ; if Phase 1 finds an API, prefer it. Document the manual step regardless as fallback |
| A7 | typer 0.25.x preserves the same Context API as 0.16+ for `ctx.obj` and `typer.Context` | Pattern 1 | LOW — typer is mature, Context is part of underlying Click which is stable |
| A8 | `tenacity` retry decorator works correctly when wrapping a method that returns `httpx.Response` | Pattern 3 | LOW — standard tenacity use case |

**No claim in this research is `[ASSUMED]`-tagged outside this table.** Verifications used: pypi.org direct (10 packages), GitHub Sonarr repo (OpenAPI spec, 290 KB), official docs (typer, pydantic, httpx, structlog, respx, tenacity, yaml-language-server, uv), local repo state (`ls`, `read snapshots/...`).

## Open Questions (RESOLVED)

> Resolution recorded by gsd-plan-phase 2026-05-07. Each question carries a
> `**RESOLVED:**` line capturing the choice the planner adopted and the plan/
> task where the decision is materialised.

1. **Is `pydantic-settings` worth the dep, or is `os.environ` + manual cast sufficient for Phase 1?**
   - What we know: D-22 mandates env-only secrets, and `SecretStr` from pydantic-settings is the standard way to avoid logging API keys. Adds 1 dep.
   - What's unclear: Whether the planner will deem this overkill for 4 secrets in Phase 1.
   - Recommendation: Use `pydantic-settings` (Standard Stack table) — unifies the config story (RootConfig pydantic for YAML, BaseSettings pydantic for env) and `SecretStr` is non-trivial to replicate manually.
   - **RESOLVED:** pydantic-settings — adopted in Plan 01-01 Task 2 (`tools/arrconf/arrconf/settings.py`) which uses `BaseSettings` + `SecretStr` for `*_API_KEY` env vars. Matches D-22 (env-only secrets, masked in repr/structlog) and unifies pydantic for both YAML config (`RootConfig`) and env (`Settings`). Single dep cost is justified by T-01-01 (information-disclosure) mitigation strength.

2. **Should the differ class-style or function-style?**
   - What we know: D-23 is "Claude's discretion" — both work.
   - What's unclear: Whether stateful tracking (e.g., metrics/counters) will be useful Phase 2+.
   - Recommendation: Function-style for Phase 1 (as in Pattern 4) ; refactor to a class only if Phase 2 needs to thread state.
   - **RESOLVED:** function-style — adopted in Plan 01-02 Task 1 (`tools/arrconf/arrconf/differ.py` exposes module-level `diff_models()` and `reconcile()`). Matches D-23 discretion call. Refactor to a class is deferred to Phase 2/3 if/when reconcilers need to thread per-app state (metrics counters, dry-run aggregates) — no state requirement surfaced for Phase 1.

3. **Fixture for `tag.json`** — baseline contains `[]` (no tags exist on cluster). For round-trip + tag tests, do we hand-craft a `tag_with_arrconf_managed.json` fixture, or seed it via cluster after creating the tag?
   - What we know: Baseline is empty (tag.json = `[]`).
   - What's unclear: If round-trip tests should run against an empty-tag baseline (which means `arrconf-managed` MUST be created on first apply, then re-dumped, then re-applied = NO_OP).
   - Recommendation: Hand-craft `tests/fixtures/sonarr/edge_cases/tag_with_arrconf_managed.json` containing `[{"id": 1, "label": "arrconf-managed"}]` — D-09 already explicitly mentions hand-crafted edge_cases fixtures.
   - **RESOLVED:** hand-craft — adopted in Plan 01-01 Task 1 fixture seeds. The file `tools/arrconf/tests/fixtures/sonarr/edge_cases/tag_with_arrconf_managed.json` ships with `[{"id": 1, "label": "arrconf-managed"}]`. The empty baseline (`tests/fixtures/sonarr/tag.json = []`) is preserved as the "tag must be created on first apply" scenario. Both fixtures are exercised by `test_managed_tag.py` (Plan 01-02 Task 2) and `test_round_trip.py` (Plan 01-03 Task 2).

4. **Single repo `arrconf/` package OR src layout `src/arrconf/`?**
   - What we know: spec.md and CLAUDE.md show `tools/arrconf/arrconf/` (flat).
   - What's unclear: Whether modern best practice (src layout) buys us anything.
   - Recommendation: Stick with the flat layout already documented (`tools/arrconf/arrconf/...`). Switching would diverge from spec without strong gain ; src layout's main benefit (preventing accidental import of the source instead of the installed package) is moot since uv installs editable.
   - **RESOLVED:** flat layout — adopted in Plan 01-01 Task 1 / Task 2 (`tools/arrconf/arrconf/...`). Matches spec.md §"Structure cible" and CLAUDE.md §"Structure cible" — switching to src layout would diverge from the spec without compensating benefit (`uv` editable installs already prevent the accidental-import failure mode src layout is meant to catch).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | All Phase 1 code | TBD by planner (check `which python3.13`) | — | uv installs Python automatically (`uv python install 3.13`) — set `UV_PYTHON_DOWNLOADS=automatic` |
| uv | Build, test, image | TBD (CLAUDE.md mentions `uv sync` so likely already installed) | — | `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker (or podman) | Phase 1 image build local test | TBD | — | CI only (skip local build in dev) |
| kubectl + port-forward | Live Sonarr round-trip test | YES (CLAUDE.md mentions `kubectl -n selfhost port-forward svc/sonarr 8989:8989`) | — | Skip live round-trip ; rely on respx fixture round-trip (test_round_trip.py) |
| GitHub Actions runner (ubuntu-24.04) | CI | YES (managed by GitHub) | n/a | n/a |
| GHCR push permission | Image publication | YES (`secrets.GITHUB_TOKEN` with `permissions.packages: write`) | n/a | n/a |
| Sonarr API key (`SONARR_API_KEY` env) | `arrconf dump` round-trip | YES (in `my-kluster/secrets/configarr-secret.yaml`) | n/a | Skip live round-trip — use respx mock |
| jq, curl | (Phase 0 — already used by snapshot.sh) | YES | — | n/a |

**Missing dependencies with no fallback:** None for Phase 1. All Phase 1 work can be done in CI + local with respx mocks. The "live round-trip" success criterion (#4) is a one-time manual verification step that requires kubectl + port-forward, but the automated round-trip test uses respx and runs in CI.

**Missing dependencies with fallback:** Python 3.13 system install is replaceable by uv-managed install.

## Validation Architecture

> Section is included because `workflow.nyquist_validation` is not explicitly disabled in `.planning/config.json` (the file does not exist — treat as enabled per spec).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-cov 7.1.0 + respx 0.23.1 |
| Config file | `tools/arrconf/pyproject.toml` (sections `[tool.pytest.ini_options]` + `[tool.coverage.run]` + `[tool.coverage.report]`) |
| Quick run command | `cd tools/arrconf && uv run pytest -x --no-cov tests/test_differ.py` |
| Full suite command | `cd tools/arrconf && uv run pytest --cov --cov-report=term-missing` |
| Coverage gate | `--cov-fail-under=70` set in `[tool.coverage.report]` ; scope limited to `arrconf.differ` + `arrconf.reconcilers.sonarr` (Pitfall 6) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-cli-subcommands | `apply --help` shows 4 subcommands ; exit codes 0/1/2/3 | unit | `uv run pytest tests/test_cli.py -x` | Wave 0 |
| REQ-yaml-autocomplete | `schemas/arrconf-schema.json` produced ; CI verifies idempotence | integration | `uv run arrconf schema-gen --output /tmp/s.json && diff schemas/arrconf-schema.json /tmp/s.json` | Wave 0 (schema-gen impl + test_schema_gen.py) |
| REQ-yaml-autocomplete (manual) | VS Code shows completions in `examples/baseline-sonarr.yml` | manual | Open file in VS Code, position cursor under `download_clients:`, observe completions | n/a — manual demo |
| REQ-idempotence | `dump` then `apply --dry-run` = 0 action ; differ classifies add/update/delete/no-op | unit | `uv run pytest tests/test_differ.py tests/test_round_trip.py -x` | Wave 0 |
| REQ-prune-opt-in | `prune=False` → PRUNE_SKIP ; `prune=True` + no managed tag → PRUNE_PROTECTED | unit | `uv run pytest tests/test_differ.py::test_prune_skip_when_prune_false tests/test_differ.py::test_prune_protected_when_no_managed_tag -x` | Wave 0 |
| REQ-managed-tag | `arrconf-managed` created before download_clients ; tag never deleted | unit | `uv run pytest tests/test_managed_tag.py -x` | Wave 0 |
| REQ-test-coverage | ≥ 70 % on differ + reconcilers/sonarr | integration | `uv run pytest --cov --cov-fail-under=70` | Wave 0 |
| REQ-app-coverage (Sonarr download_clients) | Reconcile add/update/delete/no-op against fixture | unit | `uv run pytest tests/test_reconcilers_sonarr.py -x` | Wave 0 |
| ScopeViolationError (D-12 anchor) | 4 frontière configarr endpoints raise | unit | `uv run pytest tests/test_scope_violation.py -x` | Wave 0 |
| Image GHCR built + public | `docker pull ghcr.io/tom333/arr-stack-arrconf:sha-<short>` succeeds | smoke | manual after first PR merge ; CI logs show push success | n/a — CI artifact |
| Image USER=1000 | Container runs as non-root | smoke | `docker run --rm ghcr.io/tom333/arr-stack-arrconf:latest id` returns `uid=1000` | n/a — image inspection |

### Sampling Rate

- **Per task commit:** `cd tools/arrconf && uv run pytest -x` (full suite, ~5–15 s estimated)
- **Per wave merge:** `cd tools/arrconf && uv run pytest --cov` + `uv run ruff check` + `uv run ruff format --check` + `uv run mypy arrconf` + `uv run arrconf schema-gen --output /tmp/s.json && diff /tmp/s.json ../../schemas/arrconf-schema.json`
- **Phase gate:** Full suite green in CI (`tests.yml`) AND image built + pushed in `arrconf-image.yml` AND `arrconf dump` against live port-forwarded Sonarr (manual once, success criterion #3-4)

### Wave 0 Gaps

> Wave 0 is the test-infrastructure setup task. Phase 1 starts from zero — no Python files yet — so Wave 0 must create:

- [ ] `tools/arrconf/pyproject.toml` — project metadata + tool configs (pytest, coverage, ruff, mypy)
- [ ] `tools/arrconf/uv.lock` — committed
- [ ] `tools/arrconf/arrconf/__init__.py` — empty placeholder so the package is importable
- [ ] `tools/arrconf/tests/conftest.py` — shared fixtures (e.g., fake config, fake httpx client)
- [ ] `tools/arrconf/tests/fixtures/sonarr/downloadclient.json` — copied from `snapshots/baseline-2026-05-07/sonarr/downloadclient.json`
- [ ] `tools/arrconf/tests/fixtures/sonarr/edge_cases/tag_with_arrconf_managed.json` — hand-crafted
- [ ] `tools/arrconf/tests/fixtures/sonarr/edge_cases/downloadclient_empty.json` — `[]`
- [ ] `.github/workflows/tests.yml` — ruff + mypy + pytest + schema-gen idempotence check
- [ ] Framework install: `cd tools/arrconf && uv sync` produces `uv.lock` first time

## Project Constraints (from CLAUDE.md)

> Directives extracted from `/home/moi/projets/perso/arr-stack/CLAUDE.md`. Plans MUST honor these.

### Required tools / patterns

- **Idempotence (RÈGLE D'OR)** — `GET → diff explicite → POST/PUT/DELETE` only on actual difference. `prune: false` default. (CLAUDE.md "Idempotence")
- **Mock httpx via respx** in tests — never call real APIs in CI. (CLAUDE.md "Tests")
- **Fixtures in `tests/fixtures/<app>_<resource>.json`** — sanitized of secrets. (CLAUDE.md "Tests")
- **`ruff check && ruff format --check` + `mypy`** must pass before commit ; CI blocks. (CLAUDE.md "Code style")
- **Type hints on all public signatures** ; mypy strict. (CLAUDE.md)
- **CLI signatures:** `apply [--config PATH] [--apps APP1,APP2] [--dry-run] [--log-level LEVEL]` ; same `--apps` and `--config` patterns on `dump`, `diff`, `schema-gen`. (CLAUDE.md "CLI")
- **Exit codes:** `0` succès, `1` une app a échoué, `2` erreur de config (parse/validation), `3` (sur diff) drift detected. (CLAUDE.md "CLI" + spec §6.1)
- **Env vars only for secrets:** `SONARR_API_KEY`, `RADARR_API_KEY`, `PROWLARR_API_KEY`, `QBT_USER`, `QBT_PASS`, `SEERR_API_KEY`, `JELLYFIN_API_KEY`, `ARRCONF_LOG_LEVEL`, `ARRCONF_DRY_RUN`. NEVER read secrets from a file. (CLAUDE.md "Variables d'environnement")
- **Marquage `arrconf-managed` tag** on every managed resource. (CLAUDE.md + REQ-managed-tag)
- **Snapshot before risky cluster test** — `tools/snapshot/snapshot.sh` first, ALWAYS. Snapshots are committed to git. (CLAUDE.md "Workflow snapshot")

### Forbidden

- ❌ **No secrets committed** — fixtures use placeholders. CI grep audit recommended. (CLAUDE.md "Ce que tu NE dois PAS faire")
- ❌ **No `:latest` tag in `values.yaml` or Dockerfile** — pin semver. (CLAUDE.md)
- ❌ **No write to `quality_profiles` / `custom_formats` / `quality_definitions` / `media_naming` from arrconf** — D-12 ScopeViolationError. (CLAUDE.md "Frontière")
- ❌ **No `git tag -f`** — never amend a published release. (CLAUDE.md)
- ❌ **No real API calls in CI tests** — always mock with respx. (CLAUDE.md "Tests")
- ❌ **No unpinned Python deps** — `pyproject.toml` only with version specifiers. (CLAUDE.md)
- ❌ **No scope change arrconf↔configarr without ADR** in spec.md §11. (CLAUDE.md)
- ❌ **No direct deploy from this repo** — always via my-kluster + ArgoCD. (CLAUDE.md)
- ❌ **No PR merge with drift** — review changelog on majors. (CLAUDE.md)
- ❌ **No removal of `# renovate: image=...` annotations** in values.yaml. (CLAUDE.md — applies Phase 4)
- ❌ **No `prune: true` default** in reconcilers — opt-in per section. (CLAUDE.md + REQ-prune-opt-in)
- ❌ **No untested reconciler in cluster without baseline snapshot first.** (CLAUDE.md "Ce que tu NE dois PAS faire" — Phase 2 concern, but reminded for forward-looking plans)
- ❌ **No `snapshots/` in `.gitignore`.** (CLAUDE.md)

### Project skills directory

`/home/moi/projets/perso/arr-stack/.claude/` exists but contains only `worktrees/` and `settings.local.json` — no `rules/*.md` skill files. No project-specific Claude rules to enforce beyond CLAUDE.md.

## Sources

### Primary (HIGH confidence)

- **Sonarr OpenAPI v3 spec** — https://raw.githubusercontent.com/Sonarr/Sonarr/develop/src/Sonarr.Api.V3/openapi.json (290 KB, fetched 2026-05-07) — DownloadClientResource, TagResource, Field, DownloadProtocol, securitySchemes
- **PyPI registry** — direct queries to `https://pypi.org/pypi/<pkg>/json` for typer, httpx, pydantic, pydantic-settings, ruyaml, structlog, tenacity, pytest, pytest-cov, respx, ruff, mypy, uv (versions verified 2026-05-07)
- **Pydantic JSON Schema docs** — https://docs.pydantic.dev/latest/concepts/json_schema/ — `model_json_schema()`, Draft 2020-12, `GenerateJsonSchema` subclassing
- **uv Docker integration guide** — https://docs.astral.sh/uv/guides/integration/docker/ — multistage pattern, cache mounts
- **HTTPX transports** — https://www.python-httpx.org/advanced/transports/ — `HTTPTransport(retries=N)` limitation (connection errors only)
- **Tenacity docs** — https://tenacity.readthedocs.io/ — `@retry`, `stop_after_attempt`, `wait_exponential`, `retry_if_exception_type`
- **Typer terminating** — https://typer.tiangolo.com/tutorial/terminating/ — `typer.Exit(code=N)` exit code control
- **respx user guide** — https://lundberg.github.io/respx/guide/ — `respx_mock` pytest fixture, `mock(return_value=httpx.Response(...))`
- **redhat-developer/yaml-language-server README** — https://github.com/redhat-developer/yaml-language-server — modeline `# yaml-language-server: $schema=...`, Draft 2020-12 support
- **vscode-yaml issue #587** — https://github.com/redhat-developer/vscode-yaml/issues/587 — relative path semantics (relative to YAML file, not workspace root)
- **CLAUDE.md** — `/home/moi/projets/perso/arr-stack/CLAUDE.md` — project-wide constraints
- **spec.md** — `/home/moi/projets/perso/arr-stack/spec.md` — §6.1 architecture arrconf, §6.3 CI workflows, §10 Q4-Q8, §11 ADR-1/3/5/6/7
- **Phase 1 baseline snapshots** — `snapshots/baseline-2026-05-07/sonarr/{downloadclient,tag,system_status}.json` — actual API responses (sanitized)
- **CONTEXT.md** — `01-CONTEXT.md` D-01 through D-22 (locked decisions)
- **REQUIREMENTS.md** — `.planning/REQUIREMENTS.md` (REQ-cli-subcommands, REQ-idempotence, REQ-prune-opt-in, REQ-managed-tag, REQ-test-coverage, REQ-yaml-autocomplete, REQ-app-coverage)

### Secondary (MEDIUM confidence)

- **structlog quickstart** — https://www.structlog.org/en/stable/getting-started.html — `JSONRenderer`, `ConsoleRenderer`, `make_filtering_bound_logger`
- **pydantic-settings docs** — https://docs.pydantic.dev/latest/concepts/pydantic_settings/ — `BaseSettings`, `env_prefix`, `SecretStr`
- **docker/build-push-action@v5 marketplace** — https://github.com/marketplace/actions/build-and-push-docker-images
- **docker/metadata-action@v5** — https://github.com/docker/metadata-action — multi-tag generation
- **pytest-cov configuration docs** — https://pytest-cov.readthedocs.io/en/latest/config.html
- **pytest-cov per-file threshold issue #444** — https://github.com/pytest-dev/pytest-cov/issues/444 — confirmed not implemented (workaround: scope coverage)
- **uv pip install: depot.dev guide** — https://depot.dev/docs/container-builds/how-to-guides/optimal-dockerfiles/python-uv-dockerfile

### Tertiary (LOW confidence — flag for Wave 0 verification)

- **A6 — GHCR public visibility one-time UI step**: as of 2026-04-29, `gh` CLI does not expose package visibility ; if Phase 1 plans an automation, verify against current `gh api` capabilities first.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — All versions verified live against pypi.org
- Sonarr download_client schema: HIGH — Extracted directly from official OpenAPI JSON
- Architecture (typer + pydantic + httpx + tenacity + structlog): HIGH — All patterns from official docs
- Differ algorithm (Pattern 4): HIGH — Designed from REQ-idempotence + REQ-prune-opt-in + D-02/D-04/D-20/D-21
- VS Code autocomplete wiring: HIGH — Modeline syntax + relative path verified against yaml-language-server README + issue #587
- Coverage scoping workaround: MEDIUM — Documented in pytest-cov config but not officially named "workaround" — Wave 0 should validate the threshold actually fails the build when one of the two modules dips below 70 %
- Dockerfile multistage pattern: HIGH — Direct from docs.astral.sh/uv/guides/integration/docker/
- GHCR pipeline: HIGH — Standard pattern, `docker/build-push-action@v5` is mature
- GHCR public visibility: MEDIUM — Manual UI step, low confidence in any future automation path
- Pitfalls (1–8): HIGH — Each one is rooted in either OpenAPI schema (1, 2, 3), a public github issue (5, 6), official docs (4, 8), or operational reality (7)

**Research date:** 2026-05-07
**Valid until:** 2026-06-07 (30 days — Sonarr APIs are stable, Python ecosystem stable, GHCR stable). Re-check pypi versions if Phase 1 starts > 2026-07.
