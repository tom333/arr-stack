# Roadmap: arr-stack

## Milestones

- ✅ **v0.2.0 forceSave fix** — Phases 0-7 (shipped 2026-05-17)
- ✅ **v0.3.0 Categories first-class** — Phases 9-11 (shipped 2026-05-22)
- ✅ **v0.4.0 Categories cleanup + content discovery + local config UI** — Phases 12-15 (shipped 2026-05-23)
- ✅ **v0.5.0 Jellyfin Categories-as-libs + CI/UX hardening** — Phases 16-18 (shipped 2026-05-24)
- ✅ **v0.6.0 arrconf observability — 4xx body logging** — Phase 19 (shipped 2026-05-25 via /gsd-quick 260525-bj5)
- ✅ **v0.8.0 Categories cleanup — v0.2.0 legacy migration close-out** — Phases 20-23 (shipped 2026-05-27)
- ✅ **v0.9.0 configarr-in-UI + Jellyfin skip-intro** — Phases 24-27 (shipped 2026-05-31)
- 🔄 **v0.10.0 Couche d'intention (tranche 1)** — Phases 28-31 (in progress)

## Phases

<details>
<summary>✅ v0.2.0 forceSave fix (Phases 0-7) — SHIPPED 2026-05-17</summary>

- [x] Phase 0: Bootstrap repo + snapshot raw (3/3 plans) — 2026-05-07
- [x] Phase 1: arrconf POC + JSON Schema (3/3 plans) — 2026-05-08
- [x] Phase 2: Validation cluster (5/5 plans) — 2026-05-08
- [x] Phase 2.1: Field-merge fix for sensitive YAML values (4/4 plans) — 2026-05-09
- [x] Phase 2.2: v0.1.4 forceSave fix (INSERTED — 13/13 plans) — 2026-05-10
- [x] Phase 3: Étendre arrconf (6/6 plans) — 2026-05-11
- [x] Phase 4: Umbrella chart + migration des 9 apps (8/9 plans — 04-09 deferred to v0.3.0) — 2026-05 (production-deployed)
- [x] Phase 5: Reconciler qBittorrent + split tv/anime/family (8/8 plans) — 2026-05-16
- [x] Phase 5.1: CI auto-tag → image-build chain repair (INSERTED — 2/2 plans) — 2026-05-15
- [x] Phase 6: Reconciler Seerr (7/7 plans) — 2026-05-17
- [x] Phase 7: Reconciler Jellyfin (6/6 plans) — 2026-05-17

Total: **11 phases, 65/66 plans complete**.

Full archived details: [`milestones/v0.2.0-ROADMAP.md`](milestones/v0.2.0-ROADMAP.md)
Phase artifacts: [`milestones/v0.2.0-phases/`](milestones/v0.2.0-phases/)

</details>

<details>
<summary>✅ v0.3.0 Categories first-class (Phases 9-11) — SHIPPED 2026-05-22</summary>

- [x] Phase 9: Categories data model + chart initContainer (4/4 plans) — 2026-05-18
- [x] Phase 10: Categories → 6-app propagation (10/10 plans) — 2026-05-19
- [x] Phase 11: Operational polish bundle (2/2 plans) — 2026-05-21

Total: **3 phases, 16/16 plans complete, 87 commits, 5 days**.

Highlights: 1 declarative `categories[i]` entry propagates to 6 apps + auto-creates `/media/<name>` ; pure-function generators + `merge_with_manual` toggle ; SC#2 idempotence dispositive on live cluster (3 B2-allowlist FP fixes + `ProwlarrInstance.prowlarr_url` separation) ; chart-pin co-bump pattern (0.5.3 → 0.7.0) ; Renovate App + cross-repo loop validated end-to-end (my-kluster PR #1413 MERGED) ; ArgoCD selfHeal+prune dispositive ; pre-commit hook + snapshot auto-redaction.

Full archived details: [`milestones/v0.3.0-ROADMAP.md`](milestones/v0.3.0-ROADMAP.md)
Phase artifacts: [`milestones/v0.3.0-phases/`](milestones/v0.3.0-phases/)
Audit: [`v0.3.0-MILESTONE-AUDIT.md`](v0.3.0-MILESTONE-AUDIT.md) — `passed_with_caveats`

</details>

<details>
<summary>✅ v0.4.0 Categories cleanup + content discovery + local config UI (Phases 12-15) — SHIPPED 2026-05-23</summary>

- [x] Phase 12: Categories deprecation (5/5 plans) — 2026-05-22
- [x] Phase 13: SuggestArr research spike (1/1 plan) — 2026-05-22
- [x] Phase 14: SuggestArr implementation (3/3 plans) — 2026-05-22
- [x] Phase 15: Local config UI (2/2 plans) — 2026-05-23

Total: **4 phases, 11/11 plans complete**.

Highlights: v0.2.0 transition layer fully ripped out (`merge_with_manual` deleted, flat `items:` sections removed) ; SuggestArr ships as 11th umbrella alias with Categories-aware Seerr routing via `SEER_ANIME_PROFILE_CONFIG` ; `tools/arrconf-ui/` ships as FastAPI + Svelte 5 SPA editing `arrconf.yml` from the LAN with pydantic validation, ruyaml round-trip, French i18n + dark theme.

Full archived details: [`milestones/v0.4.0-ROADMAP.md`](milestones/v0.4.0-ROADMAP.md)
Phase artifacts: [`milestones/v0.4.0-phases/`](milestones/v0.4.0-phases/)

</details>

<details>
<summary>✅ v0.5.0 Jellyfin Categories-as-libs + CI/UX hardening (Phases 16-18) — SHIPPED 2026-05-24</summary>

- [x] Phase 16: Jellyfin Categories-as-libs (1/1 plan) — 2026-05-24
- [x] Phase 17: arrconf-ui CI coverage (1/1 plan) — 2026-05-24
- [x] Phase 18: qBit POST credentials fallback (1/1 plan) — 2026-05-24

Total: **3 phases, 3/3 plans complete, 31 commits, 1-day intensive close-out**.

Highlights: Jellyfin emits 10 `VirtualFolder` libs (1 per Category) — reverses D-07-LIB-01, makes Categories visible in JellyCon/Kodi on LibreELEC salon ; `tools/arrconf-ui/**` covered by CI (`arrconf-ui-backend` triad + `arrconf-ui-frontend` quad) without triggering chart-lint auto-tag (architectural isolation SC#3 dispositive per D-17-WORKFLOW-01) ; qBit POST credentials env-injected for Sonarr+Radarr with pre-flight gate in `__main__.py` and fail-fast ConfigError ; UAT dispositive 9/9 + 9/9 qBit DCs HTTP 200 + 0 plan_actions on 2nd run ; side-quest unblock of pre-existing Sonarr RPM 400 (PathExistsValidator, pre-dated Phase 18 by ≥3 image versions) via `/gsd-debug` session.

Full archived details: [`milestones/v0.5.0-ROADMAP.md`](milestones/v0.5.0-ROADMAP.md)

</details>

<details>
<summary>✅ v0.6.0 arrconf observability — 4xx body logging (Phase 19) — SHIPPED 2026-05-25</summary>

- [x] Phase 19: arrconf observability — 4xx body logging (shipped via /gsd-quick 260525-bj5, single atomic commit 9726d81) — 2026-05-25

Total: **1 phase, 1 deliverable, 5 commits including release-chain rescue**.

Highlights: `client_4xx` structlog warning emitted in `ArrApiClient._request` between the 4xx fast-path (404/401) and the 5xx ServerError block; payload includes client/method/path/status_code/body_excerpt=response.text[:500]; 5 new respx tests (416 pass total, up from 411) cover 400 verbatim, 422 truncation, 401/404 short-circuit, 500 ServerError no-cross-fire. Chart pin co-bump 0.12.1 → 0.14.0 (initial 0.13.0 then rescue alignment with v0.14.0 auto-tag minor bump from `feat:`). Phase 19 was small enough to ship via /gsd-quick rather than full discuss/plan/execute cycle — pattern documented as a valid path for micro-milestones.

Quick task artifact: [`.planning/quick/260525-bj5-client-base-py-add-4xx-response-text-500/`](quick/260525-bj5-client-base-py-add-4xx-response-text-500/)

</details>

<details>
<summary>✅ v0.8.0 Categories cleanup — v0.2.0 legacy migration close-out (Phases 20-23) — SHIPPED 2026-05-27</summary>

- [x] Phase 20: Categories cleanup audit — legacy items/tags/paths inventory (1/1 plans) — 2026-05-26
- [x] Phase 21: Filesystem + metadata migration — `mv` + Radarr/Sonarr API mutation + Jellyfin re-scan (1/1 plans) — 2026-05-27
- [x] Phase 22: arrconf prune reconciler — force_prune + legacy-path guard + `:0.15.0` (2/2 plans) — 2026-05-27
- [x] Phase 23: UAT dispositive — end-to-end live verification (1/1 plans) — 2026-05-27

Total: **4 phases, 5/5 plans complete, 60 commits, 3 days**.

Highlights: closed the half-applied v0.2.0→v0.3.0 Categories migration at the config level. `arrconf audit`/`audit-verify` read-only inventory (P20) → one-shot `migrate-categories.py` live migration, 21 *arr PUTs + 37 torrents relocated (P21) → `differ.force_prune` + pydantic legacy-path guard shipped `:0.15.0`, live cleanup of 4 legacy roots + catch-all DC id=1 + 3 orphan torrents (P22) → live operator UAT SC#1-4 PASS, SC#5 partial-deferred (P23). Audit: `tech_debt` (no blockers).

Full archived details: [`milestones/v0.8.0-ROADMAP.md`](milestones/v0.8.0-ROADMAP.md)
Audit: [`milestones/v0.8.0-MILESTONE-AUDIT.md`](milestones/v0.8.0-MILESTONE-AUDIT.md) — `tech_debt`

</details>

<details>
<summary>✅ v0.9.0 configarr-in-UI + Jellyfin skip-intro (Phases 24-27) — SHIPPED 2026-05-31</summary>

- [x] Phase 24: Jellyfin Intro Skipper (3/3 plans) — 2026-05-31
- [x] Phase 25: configarr-in-UI backend (4/4 plans) — 2026-05-29
- [x] Phase 26: configarr-in-UI frontend (2/2 plans) — 2026-05-30
- [x] Phase 27: TRaSH CF picker + Recyclarr reference + QP picker (4/4 plans) — 2026-05-30

Total: **4 phases, 13/13 plans complete**.

Full archived details: [`milestones/v0.9.0-ROADMAP.md`](milestones/v0.9.0-ROADMAP.md)

</details>

### v0.10.0 — Couche d'intention (tranche 1)

- [ ] **Phase 28: Generate foundation** — `intent.yml` schema + `arrconf generate` CLI + CI idempotence guard + intent-boundary ADR
- [ ] **Phase 29: Sagas** — Radarr Collections reconciler (tmdbId-matched) + Jellyfin tmdbboxsets plugin depuis `sagas` dans `intent.yml`
- [ ] **Phase 30: cross-seed** — `cross-seed/config.js` généré + alias Helm app-template (consolidation hors-stack)
- [ ] **Phase 31: qbit_manage** — `qbit_manage/config.yml` généré (`cat_update: False`) + alias Helm CronJob

## Phase Details

### Phase 28: Generate foundation
**Goal**: L'opérateur édite un seul `intent.yml` et `arrconf generate` transforme l'intention en configs verbeuses committées, avec un garde-fou CI qui bloque tout drift
**Depends on**: Nothing (first phase of this milestone)
**Requirements**: INTENT-01, INTENT-02, INTENT-03, INTENT-04
**Success Criteria** (what must be TRUE):
  1. L'opérateur crée ou modifie `intent.yml` — c'est le seul fichier hand-edited ; `arrconf.yml`, `configarr.yml`, `qbit_manage/config.yml`, `cross-seed/config.js` sont tous marqués read-only (commentaire en tête) et jamais modifiés à la main
  2. `arrconf generate` exécuté localement produit les 4 configs cibles identiques au run précédent (idempotence de la fonction pure) ; les générateurs réutilisent le pattern `arrconf/generators/` existant sans réinvention
  3. La CI échoue sur une PR où les configs committées divergent de l'intention (`arrconf generate && git diff --exit-code` non-zéro) — drift détecté avant merge
  4. Un nouvel ADR documenté dans `.planning/` formalise la couche d'intention, la frontière "absorber vs déployer", et l'extension d'ADR-5 (configarr reste seul appliqueur TRaSH)
**Plans**: 6 plans
- [x] 28-01-PLAN.md — IntentConfig model + load_intent + intent-schema-gen + CI schema-reproducibility (INTENT-01)
- [x] 28-02-PLAN.md — generate_cross_seed pure-function generator (JS module.exports literal) (INTENT-02)
- [ ] 28-03-PLAN.md — `arrconf generate` CLI subcommand + `--check` drift mode (INTENT-02, INTENT-03)
- [ ] 28-04-PLAN.md — seed intent.yml + generated cross-seed/config.js (INTENT-01, INTENT-03)
- [ ] 28-05-PLAN.md — generate-idempotence CI guard job + tests.yml path trigger (INTENT-03)
- [x] 28-06-PLAN.md — ADR-10 intention layer + absorber/deployer boundary (INTENT-04)

### Phase 29: Sagas
**Goal**: L'opérateur déclare des sagas dans `intent.yml` et les voit réconciliées automatiquement dans Radarr (Collections par tmdbId) et présentées dans Jellyfin (BoxSets via tmdbboxsets)
**Depends on**: Phase 28
**Requirements**: SAGAS-01, SAGAS-02, SAGAS-03, SAGAS-04
**Success Criteria** (what must be TRUE):
  1. L'opérateur ajoute une entrée `sagas: [{name, tmdb_collection, profile, root}]` dans `intent.yml` — `arrconf generate` émet la configuration Radarr Collections correspondante dans `arrconf.yml`
  2. `arrconf apply` réconcilie les Radarr Collections : GET de l'état courant, match par `tmdbId`, PUT uniquement si drift — idempotent (2e run = 0 plan_actions)
  3. Le plugin Jellyfin `tmdbboxsets` est installé et activé via le two-run model ADR-9 (Run N = install queued + hint `kubectl rollout restart`, Run N+1 = plugin actif + BoxSets visibles dans Jellyfin)
  4. Les sagas de séries (Sonarr sans Collections) sont présentées dans Jellyfin via tag `arrconf-managed` + BoxSet curé — la présentation Jellyfin est la seule automation, sans reconciler Sonarr-style
**Plans**: TBD
**UI hint**: yes

### Phase 30: cross-seed
**Goal**: cross-seed est consolidé dans l'umbrella chart avec sa config entièrement générée depuis `intent.yml`, remplaçant l'instance hors-stack existante
**Depends on**: Phase 28
**Requirements**: XSEED-01, XSEED-02, XSEED-03
**Success Criteria** (what must be TRUE):
  1. L'opérateur déclare `tools.cross_seed` (torznab URLs, link policy) dans `intent.yml` — `arrconf generate` émet un `cross-seed/config.js` valide avec la syntaxe `module.exports = {...}`
  2. `cross-seed/config.js` généré est monté dans le pod cross-seed via ConfigMap ; cross-seed démarre et s'authentifie aux torznab configurés sans erreur
  3. L'instance cross-seed précédemment hors-stack est remplacée par l'alias Helm `app-template` dans `charts/arr-stack/` — un seul ArgoCD sync suffit à déployer la version consolidée
**Plans**: TBD

### Phase 31: qbit_manage
**Goal**: qbit_manage est déployé en CronJob avec sa config entièrement générée depuis `intent.yml`, sans jamais entrer en conflit avec arrconf sur la propriété des catégories qBit
**Depends on**: Phase 28
**Requirements**: QBM-01, QBM-02, QBM-03
**Success Criteria** (what must be TRUE):
  1. L'opérateur déclare `tools.qbit_manage` (share_limits/ratio, recyclebin, tracker_tags, orphaned) dans `intent.yml` — `arrconf generate` émet un `qbit_manage/config.yml` avec `cat_update: False` et `cat: {}` imposés inconditionnellement
  2. qbit_manage s'exécute en CronJob et applique les share_limits/recyclebin/tracker_tags configurés sans toucher aux catégories qBit (propriété exclusive d'arrconf) — pas de conflit d'écriture observable
  3. L'alias Helm `app-template` CronJob est opérationnel dans `charts/arr-stack/` avec la config.yml montée ; un `arrconf apply` + ArgoCD sync suffit pour déployer qbit_manage
**Plans**: TBD

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 28. Generate foundation | 3/6 | In Progress|  |
| 29. Sagas | 0/TBD | Not started | - |
| 30. cross-seed | 0/TBD | Not started | - |
| 31. qbit_manage | 0/TBD | Not started | - |

## Historical Progress

| Milestone | Phases | Plans | Status | Completed |
|-----------|--------|-------|--------|-----------|
| v0.2.0 forceSave fix | 11 | 65/66 | ✅ Shipped | 2026-05-17 |
| v0.3.0 Categories first-class | 3 | 16/16 | ✅ Shipped | 2026-05-22 |
| v0.4.0 Categories cleanup + content discovery + local config UI | 4 | 11/11 | ✅ Shipped | 2026-05-23 |
| v0.5.0 Jellyfin Categories-as-libs + CI/UX hardening | 3 | 3/3 | ✅ Shipped | 2026-05-24 |
| v0.6.0 arrconf observability — 4xx body logging | 1 | 1/1 | ✅ Shipped | 2026-05-25 |
| v0.8.0 Categories cleanup — v0.2.0 legacy migration close-out | 4 | 5/5 | ✅ Shipped | 2026-05-27 |
| v0.9.0 configarr-in-UI + Jellyfin skip-intro | 4 | 13/13 | ✅ Shipped | 2026-05-31 |
| v0.10.0 Couche d'intention (tranche 1) | 4 | 0/TBD | In progress | - |

**Cluster HUMAN-UAT pending from v0.3.0** (operator-exercise opt-in, not blocking):
- Phase 9 initContainer NFS uid=1000 write test (09-HUMAN-UAT.md, 2 open scenarios)
- Phase 10 SC#1 cluster apply Categories-derived path (empty arrconf.yml flat sections to exercise) — REQ-categories-deprecation will exercise this naturally
- Phase 10 SC#3 TVDB-anime live routing test in Seerr UI
