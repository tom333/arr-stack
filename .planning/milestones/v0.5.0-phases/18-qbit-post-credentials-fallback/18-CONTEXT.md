# Phase 18 — qBit POST credentials fallback — CONTEXT

**Phase:** 18
**Name:** qBit POST credentials fallback
**Milestone:** v0.5.0
**Status:** Context gathered, ready for `/gsd-plan-phase 18`
**Date:** 2026-05-24

## Domain

Le générateur Categories produit aujourd'hui des `download_clients[].fields[]` qBit avec `username: ""` et `password: ""` hardcodés. Sur **CREATE/POST** vers Sonarr/Radarr `/api/v3/downloadclient`, ces empty strings sont envoyés tels-quels — le DC se crée mais ne peut pas authentifier contre qBit (Sonarr's "Test" button retourne 401). L'opérateur doit alors entrer les creds manuellement via la UI Sonarr/Radarr, ce qui casse le modèle "fully-as-code".

Phase 18 ajoute un helper `_resolve_qbit_credentials_from_env()` dans `reconcilers/_shared.py` qui transforme la liste `derived.download_clients` AVANT l'appel `reconcile()` côté Sonarr ET Radarr. Si une entrée DC a `username`/`password` empty dans `fields[]`, le helper les substitue par `os.environ["QBT_USER"]` / `os.environ["QBT_PASS"]`. Si l'env est aussi vide → `ConfigError` fail-fast (exit code 2).

**Critique architecturale :** Phase 18 ne touche QUE la branche CREATE/POST. La branche UPDATE/PUT est déjà couverte par `differ.py::merge_fields_for_put` (Phase 2.1 / D-02.2-AUTH-REGRESSION) qui omet les credential fields des PUT bodies → cluster preserves stored value. Idempotence (SC#3 de REQ) est donc acquise par construction, sans nouveau code.

## Decisions

### D-18-INJECT-LOC-01 — Helper dans `reconcilers/_shared.py`

**Décidé :** Nouvelle fonction `_resolve_qbit_credentials_from_env(dcs: list[DownloadClient]) -> list[DownloadClient]` dans `tools/arrconf/arrconf/reconcilers/_shared.py`. Mirrors le pattern existant `_resolve_download_client_tag_labels()` (line 103) — transform desired liste BEFORE `reconcile()` call. Appelé depuis `reconcilers/sonarr.py` (ligne ~545) ET `reconcilers/radarr.py` (location à confirmer mais même pattern).

**Conséquences :**
- Les générateurs (`generators/categories.py::_qbit_dc_fields_sonarr`/_radarr`) restent purs (testables sans env). Aucun changement à la signature ni au comportement.
- Le helper lit `os.environ.get("QBT_USER", "")` et `os.environ.get("QBT_PASS", "")` à chaque call (pas de cache module-level — env changes survivent entre tests + reconciles successifs).
- Tests unitaires : respx mock + `monkeypatch.setenv()` pour les 3 cas de SC#5.

### D-18-FAIL-FAST-01 — `ConfigError` quand YAML vide + env vide

**Décidé :** Si une entrée DC a `username` empty dans YAML (= `fields[name=username].value == ""`) ET `os.environ.get("QBT_USER", "")` est aussi vide → `raise ConfigError(f"download_client '{dc.name}': username is empty in YAML AND QBT_USER env is unset/empty")`. Idem pour password / QBT_PASS. Exit code 2 propagé via `__main__.py` (déjà mappé).

**Conséquences :**
- Match exactement REQ SC#2 ("raises a clear error message" + "fail-fast, not silent").
- Aligné avec le pattern existant du qBit reconciler natif (`__main__.py:281` `Exit(code=2)` quand QBT_USER/QBT_PASS manquent).
- L'opérateur sait immédiatement quelle DC entry est cassée (le nom est dans le message).
- Pas de fallback silencieux — Phase 2.2 a montré qu'un silent failure (mask `"********"` accepté comme value) est dangereux. Fail-fast est la bonne discipline.

### D-18-SCOPE-01 — Sonarr ET Radarr ensemble

**Décidé :** Le helper est appelé depuis `reconcilers/sonarr.py` ET `reconcilers/radarr.py` (les 2 reconcilers ont un step `download_clients` qui consume les fields[] depuis le générateur). Une seule fonction helper sert les 2 callers (DRY).

**Conséquences :**
- Symétrie complète : `_qbit_dc_fields_sonarr` ET `_qbit_dc_fields_radarr` (générateur) → même helper de résolution env (reconciler).
- Pas de scope creep — Prowlarr / Seerr / Jellyfin n'ont pas de qBit DC fields, donc pas concernés.
- Test coverage couvre les 2 reconcilers en mockant chacun. Surface tests doublée mais shape identique.

### D-18-IDEMPOTENCE-FREE — SC#3 acquise par construction

**Décidé :** REQ SC#3 (idempotence — 2nd `arrconf apply` émet `0 plan_action` sur `download_clients`) est satisfaite SANS nouveau code. Mécanisme :

1. **Phase 18 helper** : injecte env creds dans desired fields[] avant POST/PUT.
2. **Cluster GET-side** : Sonarr retourne `password: "********"` masqué (jamais le real value).
3. **`merge_fields_for_put` (Phase 2.1)** : sur UPDATE PUT, compare desired vs current ; omet les credential fields du PUT body car cluster's masked value `!=` desired's env value mais c'est un faux positif que le helper omit-handles.
4. **Résultat** : 2nd run = desired credentials = env values, current credentials = `"********"` masked, `merge_fields_for_put` omits les fields, PUT body n'inclut PAS username/password, donc cluster's stored values preserved, donc `?forceSave=true` PUT n'écrit pas la mask comme valeur. Pas de plan_action change.

**Conséquences :**
- Test SC#3 = un cas de respx où le 2nd apply (après le 1er CREATE) émet 0 actions sur download_clients. Probablement déjà couvert par les tests Phase 2.1 / Phase 5 existants ; ajouter 1 test spécifique pour la combo env-inject + 2nd-run idempotence si pas déjà fait.
- Pas de risque de D-02.2-AUTH-REGRESSION récurrence : `merge_fields_for_put` est toujours en place (vérifié `tools/arrconf/arrconf/differ.py:148`).

### D-18-CHART-BUMP-01 — Patch bump 0.10.x → 0.10.(x+1)

**Décidé :** Co-bump `charts/arr-stack/values.yaml#arrconf.image.tag` selon le pattern habituel (CLAUDE.md "Release pin co-bump pattern"). Surface du change = `tools/arrconf/**` → bump obligatoire. Type = patch (bugfix, pas feature) → `0.10.x → 0.10.(x+1)`.

**Conséquences :**
- Current values.yaml a `arrconf.image.tag: "0.10.0"` (depuis le merge de PR #30 en Phase 16 close-out chain).
- Phase 18 bump : `0.10.0 → 0.10.1` (patch). Sauf si Renovate a déjà bumpé entre temps — vérifier juste avant le commit.
- Tag chain CI normale : push main → auto-tag (patch bump car commit `fix:` ou `feat(18):` chore — peut être minor selon convention) → image build → Renovate my-kluster.

## Code Context

### Files to modify (probable scope)

- **`tools/arrconf/arrconf/reconcilers/_shared.py`** — nouvelle fonction `_resolve_qbit_credentials_from_env(dcs: list[DownloadClient]) -> list[DownloadClient]`. Itère sur chaque DC, walk `fields[]`, pour name=`username`/`password` : si `value == ""`, substituer par `os.environ[QBT_USER/QBT_PASS]`. Si env aussi vide → `raise ConfigError(...)`. Sinon retourne nouvelle liste avec fields[] modifié.
- **`tools/arrconf/arrconf/reconcilers/sonarr.py`** — ligne ~545 (après `_resolve_download_client_tag_labels`, AVANT `reconcile()`) : ajouter `label_resolved = _resolve_qbit_credentials_from_env(label_resolved)` (ou nouvelle variable).
- **`tools/arrconf/arrconf/reconcilers/radarr.py`** — même injection à l'endroit symétrique.
- **`tools/arrconf/tests/test_reconcilers_shared.py`** (ou similaire — créer si n'existe pas) — 3 tests respx + monkeypatch :
  1. Both YAML empty + env set → POST body contient les env values
  2. Both YAML explicit (non-empty) → POST body contient les YAML values (env ignored)
  3. Partial : YAML username explicit + YAML password empty + env QBT_PASS set → POST body username=YAML, password=env
  + 1 test ConfigError : YAML empty + env vide → `pytest.raises(ConfigError)` avec message contenant le DC name
- **`charts/arr-stack/values.yaml`** — co-bump `arrconf.image.tag: "0.10.0" → "0.10.1"`. Renovate annotation préservée verbatim.

### Files explicitly NOT to modify

- `tools/arrconf/arrconf/generators/categories.py` — générateurs purs intacts (la pureté est l'invariant qu'on protège).
- `tools/arrconf/arrconf/differ.py::merge_fields_for_put` — déjà fait son boulot pour UPDATE PUT.
- `tools/arrconf/arrconf/__main__.py` — pas de nouvelle env var, pas de nouvelle gate (qBit reconciler natif a déjà sa propre gate Phase 5).
- `charts/arr-stack/files/arrconf.yml` — les empty strings dans le générateur sont préservés (l'arrconf.yml lui-même ne contient pas username/password explicites — c'est le générateur qui les pose).
- `.github/workflows/*.yml` — pas de CI change, le job `test` existant couvre les nouveaux tests.

### Existing patterns to reuse

- **`_resolve_download_client_tag_labels` pattern** (`reconcilers/_shared.py:103`) — receives DCs, transforms in-place ou retourne nouvelle liste, est appelé entre generator output et `reconcile()` call. Phase 18 helper mirrors exactly ce shape.
- **`SecretStr | None` from settings.py** — `QBT_USER` / `QBT_PASS` déjà disponibles via `arrconf.settings.Settings`. MAIS le helper lit directement `os.environ` (settings.py est lu UNE fois au boot, le helper doit lire à chaque reconcile pour les tests à monkeypatch).
- **`merge_fields_for_put`** (`differ.py:148`) — omits credential fields from PUT bodies, déjà en place. Pas de changement requis.
- **`?forceSave=true` PUT** (ADR-8) — déjà en place. La masked password ne peut pas casser le PUT car omited from body.
- **Chart-pin co-bump pattern** (CLAUDE.md) — `tools/arrconf/**` change → `charts/arr-stack/values.yaml#arrconf.image.tag` patch bump dans le même commit.

## Canonical Refs

- [`.planning/ROADMAP.md`](../../ROADMAP.md) — Phase 18 entry (5 SC)
- [`.planning/REQUIREMENTS.md`](../../REQUIREMENTS.md) — REQ-qbit-post-credentials full spec
- [`.planning/PROJECT.md`](../../PROJECT.md) — Current Milestone v0.5.0
- [`CLAUDE.md`](../../../CLAUDE.md) — "Release pin co-bump pattern" + "Variables d'environnement (api-contract)" + ADR-8 (forceSave context)
- [`tools/arrconf/arrconf/reconcilers/_shared.py`](../../../tools/arrconf/arrconf/reconcilers/_shared.py) — pattern `_resolve_download_client_tag_labels` line 103 (mirror target)
- [`tools/arrconf/arrconf/reconcilers/sonarr.py`](../../../tools/arrconf/arrconf/reconcilers/sonarr.py) — line 540-556 (download_clients step, inject point)
- [`tools/arrconf/arrconf/reconcilers/radarr.py`](../../../tools/arrconf/arrconf/reconcilers/radarr.py) — symmetric inject point
- [`tools/arrconf/arrconf/generators/categories.py`](../../../tools/arrconf/arrconf/generators/categories.py) — line 74-87 + 98-111 (`_qbit_dc_fields_sonarr/radarr`, where empty `""` values originate)
- [`tools/arrconf/arrconf/differ.py`](../../../tools/arrconf/arrconf/differ.py) — `merge_fields_for_put` line 148 (idempotence mechanism)
- [`tools/arrconf/arrconf/exceptions.py`](../../../tools/arrconf/arrconf/exceptions.py) — `ConfigError` (CLI exit code 2)
- [`tools/arrconf/arrconf/settings.py`](../../../tools/arrconf/arrconf/settings.py) — `QBT_USER` / `QBT_PASS` defined as `SecretStr | None` (lines 24-25)
- [`tools/arrconf/arrconf/__main__.py`](../../../tools/arrconf/arrconf/__main__.py) — line 274-281 (existing fail-fast pattern for qBit reconciler natif, MIRROR the message style)
- Project memory : `project_cluster_secrets_sealed.md` — sealed-secrets baseline confirms `arrconf-env` SealedSecret has QBT_USER + QBT_PASS already in cluster (Phase 5 boot validation).

## Research Items (none — Phase 18 needs no external research)

Phase 18 surface = ~50 LOC entièrement dans le repo, sur pattern existant (Phase 2.1 / Phase 5 reference). Pas besoin de gsd-phase-researcher.

Spot-check inline pendant plan-phase :
- Vérifier la signature exacte de `DownloadClient` pydantic model (immutability ? mutate field value possible ?)
- Vérifier la structure `FieldKV` (depuis quelle resource module ?)
- Vérifier l'endroit symétrique dans `reconcilers/radarr.py` (line approximative pour le step download_clients)

## Plan Structure Proposed

Single plan **18-A**, 1 wave, ~5-6 tasks :
1. Implement `_resolve_qbit_credentials_from_env()` dans `_shared.py` (TDD : tests d'abord, code ensuite)
2. Wire callers dans `sonarr.py` + `radarr.py` (2 lignes chacun)
3. Add 4 respx unit tests (3 SC#5 cases + 1 ConfigError case) couvrant `test_reconcilers_shared.py` OU étendre les `test_reconcilers_sonarr.py` / `test_reconcilers_radarr.py` existants
4. Co-bump `charts/arr-stack/values.yaml#arrconf.image.tag: 0.10.0 → 0.10.1`
5. Triad green local (`cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy . && uv run pytest --cov-fail-under=70`)
6. Write `18-HUMAN-UAT.md` — 3-4 scénarios (strip qBit creds dans arrconf.yml, cron run, Sonarr Test button HTTP 200, idempotence 2nd run)

Operator checkpoint à la fin : revue du diff + triad + co-bump + git status avant PR.

## HUMAN-UAT Scenarios (provisional)

- **SC#1 (mandatory)** — Sur arr-stack repo, vérifier que `arrconf.yml` (généré) n'a JAMAIS de username/password explicites pour qBit (déjà le cas — generator emit `""`). Pas d'action opérateur requise, juste documentation visuelle.
- **SC#2 (mandatory)** — Après merge + ArgoCD sync + cron firing : observer le job arrconf logs cluster-side et confirmer qu'il NE fail PAS avec `ConfigError`. L'env injection a fonctionné.
- **SC#3 (mandatory)** — Sur Sonarr UI cluster (`https://sonarr.tgu.ovh`) → Settings → Download Clients → click "Test" button sur les qBit DCs (qBittorrent-tv, qBittorrent-anime, qBittorrent-family) → vert ✓ (HTTP 200). C'est la preuve dispositive que les credentials POST'ed via env match qBit's real creds.
- **SC#4 (mandatory)** — 2nd cron firing après SC#3 : confirmer `0 plan_action` event sur `download_clients` dans les logs (idempotence dispositive via `merge_fields_for_put`).
- **SC#5 (optional follow-up)** — Si l'opérateur a un download_client qBit explicit (avec creds dans YAML) à des fins de test : confirmer que `arrconf apply` ignore l'env et POST les YAML values verbatim.

## Locked Boundaries

- ❌ **Pas de touche au générateur Categories** — `_qbit_dc_fields_sonarr/radarr` restent purs.
- ❌ **Pas de modification de `merge_fields_for_put`** — Phase 2.1 helper fonctionne, SC#3 acquise par construction.
- ❌ **Pas de nouvelle env var** — `QBT_USER` + `QBT_PASS` déjà dans `arrconf-env` SealedSecret + settings.py.
- ❌ **Pas de fallback silencieux** — fail-fast `ConfigError` est la discipline (anti-D-02.2-AUTH-REGRESSION).
- ❌ **Pas de scope expansion vers Prowlarr/Seerr/Jellyfin** — ils n'ont pas de qBit DC fields.
- ❌ **Pas de CI change** — le job `test` existant couvre les nouveaux tests via path-filter `tools/arrconf/**`.
- ❌ **Pas de modification de arrconf.yml live** — l'operator UAT ne change rien au YAML, l'injection env est transparente.

## Open Questions

Aucune restante. Plan-phase peut démarrer directement avec `/gsd-plan-phase 18 --skip-research`.
