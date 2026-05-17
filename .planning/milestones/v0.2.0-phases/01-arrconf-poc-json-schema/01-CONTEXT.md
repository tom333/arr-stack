# Phase 1: arrconf POC + JSON Schema - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning
**Source:** /gsd-discuss-phase 1 (interactif, mode default)

<domain>
## Phase Boundary

Livrer un squelette Python `arrconf` (sous `tools/arrconf/`) avec :
- 4 sous-commandes : `apply`, `dump`, `diff`, `schema-gen`
- 1 reconciler bout-en-bout : Sonarr `download_clients` (round-trip prouvé)
- JSON Schema généré (autocomplétion VS Code via yaml-language-server)
- Image Docker GHCR `ghcr.io/tom333/arr-stack-arrconf:sha-<short>` buildée par GitHub Actions
- Tests pytest+respx ≥ 70 % coverage (CI bloque sinon)
- 2 GitHub Actions workflows : `arrconf-image.yml` (build+push GHCR) + `tests.yml` (ruff+ruff format+mypy+pytest)

**OUT of scope Phase 1** :
- Autres reconcilers Sonarr (indexer, notification, root_folder, tag, host_config) → Phase 3
- Radarr, Prowlarr, qBittorrent, Seerr, Jellyfin reconcilers → Phases 3, 5, 6, 7
- Helm umbrella chart → Phase 4
- CronJob in-cluster + drift detection → Phase 2
- Migration des apps existantes my-kluster → Phase 4

</domain>

<decisions>
## Implementation Decisions

### Open questions résolues

- **D-01 (Q4 release strategy)** : Tags semver `vX.Y.Z` créés manuellement après merge sur main. CI build l'image avec tags `:vX.Y.Z` + `:latest` sur tag git ; `:sha-<short>` + `:branch-<name>` sur push branche. **Pas** de release-please en v1 — migration possible plus tard si la friction le justifie. *Source : recommandation researcher Phase 0 + spec §10 Q4.*

- **D-02 (Q6 managed-tag)** : Toute ressource créée ou modifiée par arrconf reçoit le tag `arrconf-managed` (champ `tags:` standard *arr). Le tag lui-même est réconcilié au runtime (créé s'il manque, jamais supprimé même en mode prune). **Seules** les ressources avec ce tag peuvent être prune par arrconf — les ressources non-taggées (créées manuellement par l'utilisateur) sont protégées. *Source : recommandation spec §10 Q6.*

- **D-03 (Q7 multi-version *arr)** : Support **uniquement** la version courante de chaque API au moment de Phase 1 :
  - Sonarr `/api/v3/`
  - Radarr `/api/v3/`
  - Prowlarr `/api/v1/`
  - qBittorrent `/api/v2/`
  - Seerr `/api/v1/`
  - Jellyfin v10.11+ (header `Authorization: MediaBrowser Token=...`)
  Pas de couche d'abstraction multi-version. Si breaking change upstream : Renovate alerte → adaptation ad hoc. *Source : recommandation spec §10 Q7 ; cohérent avec scope homelab single-user.*

- **D-04 (Q8 prune default)** : `prune: false` par défaut au niveau de chaque section de ressource dans le YAML. Opt-in explicite par section. Quand `prune: false` : log un warning pour les ressources cluster non présentes dans le YAML, ne supprime pas. Quand `prune: true` : supprime SEULEMENT les ressources taggées `arrconf-managed` (cf D-02). *Source : recommandation spec §10 Q8 + REQ-prune-opt-in.*

### Python tooling

- **D-05 (Package manager)** : **`uv`** (Astral). Lockfile auto (`uv.lock` committé). Build Docker via `uv sync --frozen`. CLAUDE.md mentionne déjà `uv sync` dans le workflow local. *Source : choix utilisateur ; cohérent avec ruff (même éditeur Astral) déjà dans la stack.*

- **D-06 (CLI framework)** : **`typer`**. Type-hint based, basé sur click, créé par l'auteur de FastAPI. Excellent fit avec pydantic v2 déjà dans la stack. Auto-help généré, types Python deviennent les flags. Ajoute 2 deps (typer + click). *Source : choix utilisateur.*

- **D-07 (Logging)** : `structlog` avec JSON formatter pour la sortie cluster (déjà locked dans CLAUDE.md "Stack technique"). Niveau via env `ARRCONF_LOG_LEVEL` (default `INFO`). Format pretty + couleurs en mode TTY local pour DX, JSON pour CronJob. *Source : CLAUDE.md ; locked.*

### Schéma pydantic Sonarr

- **D-08 (Scope schéma Sonarr Phase 1)** : Approche **hybride** :
  - `resources/sonarr/download_client.py` → schéma **complet** Sonarr v3 (~25 fields : `id`, `name`, `enable`, `protocol`, `priority`, `categories`, `removeCompletedDownloads`, `removeFailedDownloads`, `host`, `port`, `apiKey`, `urlBase`, `useSsl`, `username`, `password`, `tvDirectory`, `recentTvPriority`, `olderTvPriority`, `initialState`, `tags`, `fields[]`, `implementationName`, `implementation`, `configContract`, `infoLink`)
  - `resources/sonarr/{indexer,notification,root_folder,tag,host_config,quality_profile,custom_format,quality_definition,media_naming}.py` → fichiers **stubs** présents (forward-compat Phase 3) avec :
    - 4 endpoints frontière configarr (`quality_profile`, `custom_format`, `quality_definition`, `media_naming`) : raise `ScopeViolationError` si `apply` les touche (ADR-5 codé en dur dès Phase 1)
    - 5 endpoints futurs (`indexer`, `notification`, `root_folder`, `tag`, `host_config`) : NotImplementedError + TODO Phase 3 explicite
  - `resources/sonarr/__init__.py` exporte les noms publics
  - Phase 3 ajoutera l'implémentation, le scaffold est déjà là
  *Source : choix utilisateur ; minimise re-architecture en Phase 3 + ancre la frontière configarr immédiatement.*

### Tests + fixtures

- **D-09 (Fixtures source)** : Stratégie **hybride** :
  - **Seed** : `tests/fixtures/sonarr/downloadclient.json` copié depuis `snapshots/baseline-2026-05-07/sonarr/downloadclient.json` (déjà sanitisé par redaction Phase 0). Single source of truth pour le happy path.
  - **Cas limites hand-written** dans `tests/fixtures/sonarr/edge_cases/` : `downloadclient_empty.json` (no clients), `downloadclient_invalid_json.json` (parsing error), `downloadclient_partial_response.json` (truncated), `downloadclient_with_unmanaged_tag.json` (test prune protection), etc.
  - **Mocks d'erreur HTTP** via respx : 401 (auth wrong), 404 (resource gone), 500 (server error), timeout
  *Source : choix utilisateur ; évite duplication, tire parti du baseline déjà committé.*

- **D-10 (Test coverage cible)** : ≥ 70 % sur `differ.py` et `reconcilers/sonarr.py` (CI bloque sinon, déjà locked CLAUDE.md). Couverture mesurée via `pytest-cov`. Pas d'objectif sur fixtures ni `__main__`. *Source : REQ-test-coverage ; locked.*

### Idempotence + frontière configarr

- **D-11 (Idempotence — règle d'or)** : Pattern obligatoire dans `differ.py` : `GET` → matcher par `name` (clé de matching stable côté API *arr) → diff explicite par champ → `POST/PUT/DELETE` SEULEMENT si différence. Round-trip `dump → apply --dry-run` produit 0 action. Test unitaire dédié `test_no_op_idempotent`. *Source : CLAUDE.md "Idempotence (RÈGLE D'OR)" + REQ-idempotence ; locked.*

- **D-12 (ScopeViolationError)** : Exception définie dans `arrconf/exceptions.py`. Levée si une opération (`apply`, `dump`, `diff`) tente d'écrire ou lire un endpoint frontière configarr (`quality_profiles`, `custom_formats`, `quality_definitions`, `media_naming`). Message clair pointant vers `charts/arr-stack/files/configarr.yml` comme alternative. Test unitaire dédié. *Source : ADR-5 + REQ-configarr-coexistence ; codé en dur dès Phase 1.*

### CI + image

- **D-13 (`tests.yml` workflow steps)** : `ruff check → ruff format --check → mypy → pytest --cov` dans cet ordre. CI bloque si l'un échoue. Trigger : PR modifiant `tools/arrconf/**`. *Source : CLAUDE.md + spec §6.3 + récente promotion mypy.*

- **D-14 (`arrconf-image.yml` workflow)** : Trigger sur push main (modifiant `tools/arrconf/**`) + tag `v*`. Steps : checkout → setup buildx → login GHCR via `${{ secrets.GITHUB_TOKEN }}` → build multi-arch (amd64 only en v1) → push. Tags : `:sha-<short>`, `:branch-<name>` sur push, `:vX.Y.Z` + `:latest` sur tag. cosign signing **deferred** (post-MVP, Q4 résolu donc). *Source : spec §6.3 + D-01.*

- **D-15 (CI vérifie schema-gen)** : Step CI dans `tests.yml` : `arrconf schema-gen --output schemas/arrconf-schema.json` puis `git diff --exit-code schemas/arrconf-schema.json`. Si différence → CI rouge, message clair ("Run `arrconf schema-gen` and commit the result"). *Source : ROADMAP success criterion #6 + REQ-yaml-autocomplete.*

### Autocomplétion VS Code

- **D-16 (Schema directive YAML)** : Chaque fichier YAML arrconf (`charts/arr-stack/files/arrconf.yml`, `examples/baseline-sonarr.yml`, etc.) commence par :
  ```yaml
  # yaml-language-server: $schema=../../schemas/arrconf-schema.json
  ```
  (Chemin relatif au YAML.) `examples/baseline-sonarr.yml` créé par `arrconf dump` doit inclure cette directive automatiquement. *Source : REQ-yaml-autocomplete + ROADMAP success criterion #5.*

- **D-17 (`.vscode/settings.json` — optionnel)** : Pas committé en Phase 1. Si l'utilisateur veut un mapping global (`yaml.schemas: { ".../arrconf-schema.json": "*arrconf*.yml" }`), il l'ajoute dans son `.vscode/settings.json` perso. *Source : choix conservateur — éviter de polluer le repo avec une config IDE.*

### HTTP client

- **D-18 (httpx mode)** : Sync uniquement en Phase 1 (`httpx.Client`). Le scope (1 reconciler, ~10-30 GET/PUT par run) ne justifie pas l'async. Migration possible Phase 5+ si latence devient un problème. *Source : choix conservateur ; cohérent CLAUDE.md "Sync + async" mais on commence sync.*

- **D-19 (Retry + timeout)** : `httpx.Client(timeout=httpx.Timeout(connect=5.0, read=30.0))`. Retries via `tenacity` ou via httpx transport custom — recommandation researcher attendue. 3 retries max sur 5xx + connection errors, exponential backoff. *Source : Claude's Discretion ; à confirmer en research.*

### Frontière endpoints `download_clients` Sonarr

- **D-20 (Matching key)** : `name` (string unique par instance Sonarr). C'est l'identifiant stable côté API *arr (l'ID numérique change si recréé). Pattern réutilisable pour les autres resources. *Source : CLAUDE.md "Idempotence" + REQ-idempotence.*

- **D-21 (Champs read-only / exclude du diff)** : `id` (numérique, généré par Sonarr), `implementationName` (nom UI affiché, dérivé), `infoLink` (URL doc upstream). Marqués `Field(exclude=True)` dans pydantic. *Source : Claude's Discretion ; à valider en code review.*

- **D-22 (Sécurité fixtures)** : Les API keys / passwords des download_clients dans les fixtures sont **toujours** des valeurs factices (`"test-api-key-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"`) ou `"***REDACTED***"`. Le seed depuis `snapshots/` est déjà redacted. Audit anti-leak `grep` en pre-commit hook ou en CI. *Source : Phase 0 audit pattern + CLAUDE.md "ne pas committer secrets".*

### Claude's Discretion

Les détails suivants sont laissés au planner / executor (cohérents avec spec.md + CLAUDE.md mais pas explicitement décidés ici) :
- Structure exacte de `differ.py` (fonction unique vs class) — recommandation researcher
- Format exact des logs structlog (champs ajoutés, processeurs)
- Convention de naming pour les tests (`test_<feature>_<case>` vs `test_<file>` flat)
- Choix entre `pydantic-settings` vs lecture manuelle des env vars dans `config.py`
- Pre-commit hooks dans le repo (deferred, à voir Phase 2+)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source spec + conventions
- `spec.md §6.1` — Architecture arrconf (CLI, structure, stack)
- `spec.md §6.3` — CI workflows (tests.yml, arrconf-image.yml steps)
- `spec.md §10 Q4-Q8` — Open questions résolues ici (D-01 à D-04)
- `spec.md §11 ADR-1, ADR-3, ADR-5, ADR-6` — Décisions structurantes (Python custom, GHCR, frontière configarr, baseline snapshot)
- `CLAUDE.md` "Conventions développement — arrconf" — Idempotence règle d'or, code style, tests, CLI
- `CLAUDE.md` "Frontière arrconf / configarr" — Boundary table arrconf vs configarr (18 rows)

### Phase 0 outputs (utilisables comme seeds Phase 1)
- `snapshots/baseline-2026-05-07/sonarr/downloadclient.json` — Seed pour fixtures (déjà redacted)
- `snapshots/baseline-2026-05-07/sonarr/system_status.json` — Confirme Sonarr v4.0.17.2952 + endpoint `/api/v3/`
- `tools/snapshot/snapshot.sh` — Patterns de référence (env vars, auth, jq sort-keys) — bien que Bash, l'organisation des endpoints inspire le code Python
- `tools/snapshot/README.md` — Documentation port-forward / env vars / troubleshooting (à étendre avec patterns arrconf)

### Phase 1 deliverables (à créer)
- `tools/arrconf/pyproject.toml` — uv workspace + ruff + mypy + pytest config
- `tools/arrconf/Dockerfile` — Multi-stage (uv builder → distroless ou python:3.13-slim) USER 1000:1000 ~80 MB
- `tools/arrconf/arrconf/` — Package layout (cf spec §6.1)
- `tools/arrconf/tests/` — Tests + fixtures
- `schemas/arrconf-schema.json` — JSON Schema généré (committé)
- `examples/baseline-sonarr.yml` — Round-trip artefact (généré par `arrconf dump`)
- `.github/workflows/tests.yml` — ruff + mypy + pytest
- `.github/workflows/arrconf-image.yml` — Build + push GHCR

### Tooling refs
- `https://docs.astral.sh/uv/` — uv docs (workspaces, lockfile)
- `https://typer.tiangolo.com/` — typer CLI framework
- `https://docs.pydantic.dev/2.x/` — pydantic v2 (model_json_schema, Field exclude)
- `https://www.python-httpx.org/` — httpx (sync client, transports, retries)
- `https://docs.python.org/3/library/json.html` + `https://github.com/lemicalDev/python-ruyaml` — JSON / ruyaml
- `https://lukasbestle.com/blog/structlog-quickstart` — structlog patterns
- `https://github.com/lundberg/respx` — respx (httpx mocks)
- `https://docs.pytest.org/` — pytest, pytest-cov

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets (depuis Phase 0)
- **`snapshots/baseline-2026-05-07/sonarr/downloadclient.json`** : Réponse réelle sanitisée de l'API Sonarr (déjà redacted par Phase 0 audit). Sera copié vers `tests/fixtures/sonarr/downloadclient.json` comme seed du happy path. Évite de réinventer la structure.
- **`snapshots/baseline-2026-05-07/sonarr/{system_status,config_host,*}.json`** : Inspirations pour les schémas pydantic des autres resources Sonarr (stubs en D-08).
- **`tools/snapshot/snapshot.sh` lignes 240-280 (snapshot_arr_app)** : Pattern d'invocation curl — sert de référence pour les URL d'endpoint construit côté Python (`{SONARR_URL}/api/v3/downloadclient` etc.).

### Established Patterns (depuis spec.md / CLAUDE.md)
- **Env vars only** : `SONARR_API_KEY`, etc. ; jamais lus depuis fichier (`pydantic-settings` recommandé pour le binding env→config).
- **`prune: false` par défaut** (D-04) : implémenté au niveau du `differ.py` ; chaque resource section du YAML a un flag `prune` opt-in.
- **`arrconf-managed` tag protection** (D-02) : implémenté au niveau de `tags.reconcile()` (le tag lui-même n'est jamais supprimé) + `differ.py` (filter prune candidates par tag).
- **Round-trip dump→apply** (D-11) : test unitaire `test_round_trip` qui appelle `dump()` puis parse + `apply --dry-run` et asserte 0 action.

### Integration Points
- **Phase 2 (cluster validation)** : arrconf doit pouvoir tourner en CronJob → image Docker minimaliste, env via `envFrom: secretRef`, exit codes corrects (0/1/2/3 cf D-13 spec). Phase 1 doit prouver le contrat exit codes.
- **Phase 3 (extension)** : Stubs Sonarr en D-08 + frontière `ScopeViolationError` en D-12 ancrent l'architecture. Phase 3 ajoute juste l'impl des stubs sans réorganisation.
- **Phase 4 (umbrella chart)** : `arrconf` est consommé via Helm dans `charts/arr-stack/templates/arrconf-cronjob.yaml`. Phase 1 livre l'image — Phase 4 livre le wrapping K8s.

</code_context>

<specifics>
## Specific Ideas

### Round-trip prouvé bout-en-bout
Le success criterion #3 du ROADMAP est très spécifique : `arrconf dump --apps sonarr` produit `examples/baseline-sonarr.yml`, puis `arrconf diff --config examples/baseline-sonarr.yml --apps sonarr` retourne 0 diff. Test d'intégration manuel (avec port-forward Sonarr local) à scripter en runbook ; test unitaire automatisé dans pytest avec fixture seed.

### Frontière configarr ancrée dès Phase 1
Bien que Phase 1 ne touche QUE `download_clients`, l'erreur `ScopeViolationError` (D-12) doit déjà refuser explicitement `quality_profiles`, `custom_formats`, `quality_definitions`, `media_naming` — même si les reconcilers correspondants n'existent pas encore (stubs D-08). Test unitaire dédié `test_scope_violation_*`. Cela garantit que personne ne peut "accidentellement" étendre arrconf au scope configarr.

### `arrconf-managed` réconciliation explicite
Le tag `arrconf-managed` doit lui-même être réconcilié dès Phase 1 (créé sur l'instance Sonarr s'il n'existe pas). Test unitaire pour vérifier que le tag est créé avant tout `download_client` qui le référence (ordre topologique).

### Autocomplete VS Code en démo
Success criterion #5 demande une démo manuelle : ouvrir `examples/baseline-sonarr.yml` dans VS Code, taper sous `download_clients:`, voir les propositions des champs valides avec descriptions docstrings pydantic. La directive `# yaml-language-server: $schema=...` (D-16) doit être en tête du fichier, et le yaml-language-server VS Code doit être installé localement (déjà standard chez la plupart des devs Python). Documenter dans `tools/arrconf/README.md`.

</specifics>

<deferred>
## Deferred Ideas

### Reportées à Phase 2+ (cluster validation)
- **CronJob YAML K8s** + secrets injection via `envFrom: secretRef` — c'est le scope de Phase 2.
- **Drift detection logging** : structuré pour parsing par observability stack — Phase 2 a `REQ-drift-detection`.
- **Backoff/retry policy** quand l'API *arr est temporairement down (5xx) — recommandation researcher.

### Reportées à Phase 3 (extension arrconf)
- **Reconcilers** : `indexer`, `notification`, `root_folder`, `tag`, `host_config` Sonarr (stubs créés en Phase 1, impl en Phase 3)
- **Radarr et Prowlarr complets** (Phase 3 cible "Sonarr + Radarr + Prowlarr étendus")
- **App sync Prowlarr** : push des indexers Prowlarr vers Sonarr/Radarr → Phase 3

### Reportées à Phase 4 (umbrella + migration)
- **Custom managers Renovate** sur `values.yaml` (regex)
- **Helm umbrella chart** + ArgoCD Application unique
- **Suppression des 9 ArgoCD Applications unitaires côté my-kluster** + `charts/configarr/`

### Reportées post-MVP
- **release-please** ou semantic-release (tags manuels suffisent v1, cf D-01)
- **cosign signing** de l'image (deferred Q4)
- **Multi-arch Docker** (amd64 only en v1, arm64 si besoin futur)
- **`pre-commit` hooks** dans le repo (audit fixtures, ruff, mypy avant push) — Phase 2+ si DX manque
- **httpx async** : migration sync→async si latence devient un problème
- **Layer d'abstraction multi-version** (Q7 résolu : v4+ only en v1)

### Hors scope définitif (ADR-5)
- Les 4 endpoints frontière configarr (`quality_profiles`, `custom_formats`, `quality_definitions`, `media_naming`) — refus codé en dur dès Phase 1 via `ScopeViolationError` (D-12). NE JAMAIS être réimplémenté côté arrconf.

</deferred>

---

*Phase: 1-arrconf-poc-json-schema*
*Context gathered: 2026-05-07 via /gsd-discuss-phase 1*
