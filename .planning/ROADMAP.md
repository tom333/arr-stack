# Roadmap: arr-stack

## Milestones

- ✅ **v0.2.0 forceSave fix** — Phases 0-7 (shipped 2026-05-17)
- ✅ **v0.3.0 Categories first-class** — Phases 9-11 (shipped 2026-05-22)
- ✅ **v0.4.0 Categories cleanup + content discovery + local config UI** — Phases 12-15 (shipped 2026-05-23)
- 🚧 **v0.5.0 Jellyfin Categories-as-libs + CI/UX hardening** — Phases 16-18 (in progress)

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

### ✅ v0.4.0 Categories cleanup + content discovery + local config UI (Phases 12-15) — shipped 2026-05-23

**Goal**: Achever le pivot Categories first-class (deprecation des flat sections v0.2.0), ajouter content discovery automatisé (SuggestArr), fournir un éditeur local pour `arrconf.yml`.

### Phase checklist

- [x] **Phase 12: Categories deprecation** — `merge_with_manual` removed; flat sections deleted from `arrconf.yml`; generators are sole source; sweep manual-path tests pruned; migration doc in CLAUDE.md (completed 2026-05-22)
- [x] **Phase 13: SuggestArr research spike** — `13-RESEARCH.md` locks Option A (Helm sidecar) via SuggestArr's native `SEER_ANIME_PROFILE_CONFIG` per-request routing; SEED-001 closed; Phase 14 preflight handed off (completed 2026-05-22)
- [x] **Phase 14: SuggestArr implementation** — Helm sidecar OR declarative reconciler OR CronJob (per Phase 13 decision); SealedSecret + ConfigMap; Categories routing wiring; integration test (completed 2026-05-22)
- [x] **Phase 15: Local config UI** — `tools/arrconf-ui/` FastAPI backend + frontend (React/Svelte TBD) + full file editor + pydantic-driven validation + ruyaml round-trip + potentially split into 15-A backend + 15-B frontend during plan-phase (completed 2026-05-23)

### 🚧 v0.5.0 Jellyfin Categories-as-libs + CI/UX hardening (Phases 16-18)

**Goal**: Refactor Jellyfin pour rendre les 10 Categories visibles nativement (clients Kodi/JellyCon sur LibreELEC salon + Swiftfin + web), restaurer la couverture CI sur `tools/arrconf-ui`, et fixer le fallback credentials côté qBit POST.

### Phase checklist

- [ ] **Phase 16: Jellyfin Categories-as-libs** — `generate_jellyfin()` refactored to emit 10 `VirtualFolder` libs (1 per Category) replacing the 2 super-libs; D-07-LIB-01 reversed or adapted; arrconf image co-bump `0.7.0 → 0.8.0` (minor — feature)
- [ ] **Phase 17: arrconf-ui CI coverage** — `chart-lint.yml` + `tests.yml` path-filters extended to `tools/arrconf-ui/**`; backend triad (ruff + mypy) + frontend (`npm ci` + `npm run check` + `npm run build`); auto-tag guarded against UI-only changes (no chart-pin co-bump — CI-only change)
- [ ] **Phase 18: qBit POST credentials fallback** — qBit `download_clients` reconciler injects `QBT_USER` / `QBT_PASS` from env when YAML empty; idempotent; 3-case respx test coverage; arrconf image co-bump `0.8.0 → 0.8.1` (patch — bugfix)

## Phase Details

**v0.4.0 milestone archived (Phase 12–15)**: see [`milestones/v0.4.0-ROADMAP.md`](milestones/v0.4.0-ROADMAP.md) for full phase details, requirements, and lessons learned.

<details>
<summary>Show archived Phase 12–15 details (collapsed)</summary>

### Phase 12: Categories deprecation
**Goal**: Remove the v0.2.0 transition layer entirely — `merge_with_manual` toggle, flat sections in `arrconf.yml`, and the manual-path sweep tests. Categories generators become the sole source of truth for reconciler inputs.
**Depends on**: v0.3.0 baseline (16/16 plans shipped, production cluster running chart v0.7.0 / image :0.6.7)
**Requirements**: REQ-categories-deprecation
**Success Criteria** (what must be TRUE):
  1. `tools/arrconf/arrconf/reconcilers/_shared.py merge_with_manual()` function removed (and all callsites in `__main__.py` simplified to direct generator call).
  2. `charts/arr-stack/files/arrconf.yml` flat sections (`sonarr.main.tags.items`, `radarr.main.root_folders.items`, `qbittorrent.main.categories.items`, `seerr.main.sonarr_service.animeTags`, `jellyfin.main.libraries.items`, and equivalents) are deleted — schema regen confirms the simplified shape; pydantic validates the new layout.
  3. `tools/arrconf/tests/test_phase10_idempotence_sweep.py::test_sweep_manual_override_path` and any other manual-path-specific tests are removed. The Categories-derived sweep `test_sweep_categories_derived_path` becomes the sole SC#2 dispositive test.
  4. `CLAUDE.md` gets a "v0.3.0 → v0.4.0 deprecation" section documenting the operator-side YAML cleanup procedure (one-time edit before upgrade).
  5. `arrconf apply --dry-run` on the live cluster after the deprecation lands emits the same plan_action shape as immediately before (the Categories-derived path was already exercised in v0.3.0 — this just removes dead code/YAML).
**Plans**: 5 plans

Plans:
**Wave 1**
- [x] 12-A-reconciler-refactor-PLAN.md — Remove merge_with_manual, refactor reconciler signatures to accept *Derived dataclasses, co-bump values.yaml 0.6.7→0.7.0 (D-01, D-03, D-04, D-06, D-15)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 12-B-pydantic-yaml-schema-PLAN.md — Slim pydantic Section models, delete 11 flat YAML sections, regen schema, refactor diff_cmd.py (D-01, D-02, D-05, D-13)
- [x] 12-C-test-cleanup-PLAN.md — Delete 8 manual-path tests, rename test_sweep, rename 8 *_wiring_empty_manual tests, conftest audit (D-06, D-07, D-08, D-09, D-10)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 12-D-docs-snapshot-PLAN.md — CLAUDE.md v0.3.0→v0.4.0 deprecation section, capture before-phase-12 snapshot (D-11, D-12, D-13, D-14)

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 12-E-live-cluster-dispositive-PLAN.md — Post-merge SC#5 dispositive: after-snapshot + diff + HUMAN-UAT + VERIFICATION (D-14, D-16, D-17)
**UI hint**: no

### Phase 13: SuggestArr research spike
**Goal**: Produce a `13-RESEARCH.md` that locks the SuggestArr deployment architecture decision (sidecar Helm-only vs declarative reconciler in arrconf vs CronJob mode). SEED-001 closed with reference to the decision.
**Depends on**: Phase 12 (clean Categories model is the routing target; no transition layer noise)
**Requirements**: REQ-suggestarr-research
**Success Criteria** (what must be TRUE):
  1. `gsd-phase-researcher` produces `13-RESEARCH.md` covering: SuggestArr's runtime model (daemon vs cron), its REST API surface (if any), Jellyfin watch-history scan auth, Seerr request submission mechanics, Categories-aware routing capability (does it match arrconf's tag-based routing on `series-zoe` / `films-zoe`?), and resource footprint estimates.
  2. `13-CONTEXT.md` locks the architecture decision: Helm sidecar OR `arrconf/reconcilers/suggestarr.py` OR CronJob. Rationale documented.
  3. `.planning/seeds/SEED-001-suggestarr.md` gets a closure note: `status: closed (Phase 13 architecture decided)` + frontmatter `closed_in: v0.4.0 Phase 13`.
  4. No production code/chart change yet — this phase is research-only.
**Plans**: 1 plan

Plans:
**Wave 1**
- [x] 13-A-research-consumption-PLAN.md — Close SEED-001, append Phase 13 lock to CLAUDE.md État actuel, emit 13-PHASE14-PREFLIGHT.md handoff, verify SC#4 zero-prod-drift, mark ROADMAP complete (REQ-suggestarr-research)
**UI hint**: no

### Phase 14: SuggestArr implementation
**Goal**: Ship SuggestArr in the umbrella chart per the Phase 13 architecture decision. Categories-aware routing wired; integration test confirms end-to-end flow.
**Depends on**: Phase 13 (arch decision locked)
**Requirements**: REQ-suggestarr-integration
**Success Criteria** (what must be TRUE):
  1. Deployment artifact present per Phase 13's decision: either an 11th `bjw-s/app-template@5.0.0` alias in `Chart.yaml` + new SealedSecret `suggestarr-env`, OR `arrconf/reconcilers/suggestarr.py` + `suggestarr:` block in `arrconf.yml`, OR a CronJob with the appropriate schedule.
  2. SuggestArr can connect to Jellyfin (read watch history) and Seerr (submit requests) on the live cluster — health-check endpoint or first scan-cycle log line confirms.
  3. Categories-aware routing: a SuggestArr-emitted anime suggestion creates a Seerr request that lands on the `series-zoe` Sonarr category (anime profile); a family suggestion lands on `series-garcons`. Integration test or live UAT confirms.
  4. ArgoCD sync of the chart with SuggestArr enabled succeeds without manual intervention.
  5. Per-Phase chart-pin co-bump if arrconf code touched (per D-05 — applies if reconciler path chosen; not if sidecar-only).
**Plans**: 3 plans

Plans:
**Wave 1**
- [x] 14-01-PLAN.md — Helm chart vendoring: add suggestarr alias to Chart.yaml + helm dependency build + unpack workaround (D-12)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 14-02-PLAN.md — values.yaml suggestarr block + ConfigMap template + files/suggestarr-config.yml (live-cluster discovery checkpoint for Jellyfin ItemIds + Sonarr/Radarr profileIds) (D-01, D-04, D-05, D-06, D-07, D-08, D-09, D-14)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 14-03-PLAN.md — Integration test test_suggestarr_routing_config.py + 14-HUMAN-UAT.md operator runbook (D-02, D-10, D-11, D-13)
**UI hint**: no

### Phase 15: Local config UI
**Goal**: A local web UI (browser on `localhost:NNNN`) lets the operator edit `charts/arr-stack/files/arrconf.yml` entirely from a browser, with pydantic-driven validation, ruyaml round-trip preserving comments, and a Save action that writes the file (operator handles `git add/commit/push` manually).
**Depends on**: Phase 12 (UI works against the post-deprecation YAML shape; not the transition shape)
**Requirements**: REQ-local-config-ui-backend, REQ-local-config-ui-frontend, REQ-local-config-ui-packaging
**Success Criteria** (what must be TRUE):
  1. `uv run arrconf-ui` from `tools/arrconf-ui/` (or repo root, depending on packaging) starts a FastAPI server on `127.0.0.1:NNNN` and opens the browser at the UI page automatically (or prints the URL).
  2. The UI loads `charts/arr-stack/files/arrconf.yml`, parses it via the pydantic models from `tools/arrconf/arrconf/config.py`, and renders a typed form covering all sections: `categories`, `sonarr`, `radarr`, `prowlarr`, `qbittorrent`, `seerr`, `jellyfin`.
  3. Categories editor supports add/remove/reorder operations with kind/profile dropdowns and base_path validation; per-app sections render form inputs typed by pydantic field types (string/int/enum/list).
  4. Diff preview (current file vs pending edits) renders before Save; Save validates via pydantic + writes the file via ruyaml (round-trip preserves comments, blank lines, and key ordering).
  5. Schema validation indicators (green/red) on each input; submission with invalid data returns 422 with pydantic errors highlighted in-form.
  6. No git automation in the UI — Save shows a toast/notification: "Saved. Review `git diff` then push manually."
  7. README.md gains a "Local config UI" section with launch + workflow instructions.
**Plans**: 2 plans

Plans:
**Wave 1**
- [x] 15-A-backend-PLAN.md — `tools/arrconf-ui/` Python package + FastAPI 4 endpoints + pydantic validation + ruyaml atomic round-trip + semantic diff + Typer CLI (REQ-local-config-ui-backend, REQ-local-config-ui-packaging)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 15-B-frontend-PLAN.md — Svelte 5 + Vite + TS SPA, schema-driven FieldInput (D-13) + HelpTooltip (D-14) + SuggestArrBadge (D-09) + Categories editor + DiffPanel + SaveToast + README update (REQ-local-config-ui-frontend, REQ-local-config-ui-packaging)
**UI hint**: yes — frontend has visual surfaces (Categories table, per-app forms, diff preview)

</details>

### Phase 16: Jellyfin Categories-as-libs
**Goal**: Refactor `generate_jellyfin()` to emit 10 `VirtualFolder` libs (one per Category) instead of 2 super-libs with PathInfos, so that every Jellyfin client (web, Swiftfin, JellyCon on the LibreELEC salon mini-PC) sees the 10 Categories as native top-level browse buckets.
**Depends on**: v0.4.0 baseline (production cluster running chart `v0.8.2` / arrconf image `:0.7.0`, generators are sole reconciler input source post-Phase-12).
**Requirements**: REQ-jellyfin-categories-as-libs
**Success Criteria** (what must be TRUE):
  1. After `helm upgrade` of the new chart on the live cluster, the Jellyfin web UI home page shows **10 top-level libraries** (one per `categories[].name`: `series`, `series-emilie`, `series-thomas`, `series-garcons`, `series-zoe`, `films`, `nouveaux-films`, `films-enfants`, `films-animation-enfants`, `films-zoe`) instead of the two super-libs `Séries` and `Films`. Each library's `kind` (TV vs Movies) matches the Category's `kind` field, and its single `PathInfo` points at `/media/<name>`.
  2. `arrconf apply` on the live cluster is idempotent after the refactor lands: a second run emits `0` `plan_action` events on `jellyfin.libraries` (no drift). D-07-LIB-01 (`prune: false` hardcoded on jellyfin.libraries) is **explicitly addressed** in the phase decisions — either reversed to honor YAML opt-in, or adapted to "preserve user-added libs only" with the matching rule documented in `_shared.py` (or equivalent).
  3. Unit tests cover the new layout: `tools/arrconf/tests/` gains coverage for `generate_jellyfin()` producing 10 `VirtualFolder` entries from a 10-Category fixture, and the `categories[].kind` → Jellyfin `CollectionType` mapping is asserted per kind value (`tvshows` for `kind: tv`, `movies` for `kind: movies`). The pre-Phase-12 sweep test (Phase 12 SC#5 dispositive) continues to pass.
  4. Chart-pin co-bump executed in the implementation commit(s): `charts/arr-stack/values.yaml#arrconf.image.tag` bumped from `0.7.0` to `0.8.0` (minor — new feature), `# renovate: image=...` annotation preserved verbatim above `repository:`. The chart's own `version:` in `Chart.yaml` bumps accordingly per existing convention.
  5. Operator UAT confirms 10-libs visibility from at least the Jellyfin web UI (mandatory) ; JellyCon on the salon LibreELEC mini-PC verification is documented as a scenario in `16-HUMAN-UAT.md` but **may be deferred** as a carry-forward HUMAN-UAT item if the operator hasn't yet installed JellyCon — non-blocking for Phase 16 close.
**Plans**: TBD (refined by `/gsd-plan-phase`)
**UI hint**: no

### Phase 17: arrconf-ui CI coverage
**Goal**: Extend `chart-lint.yml` and `tests.yml` path-filters to cover `tools/arrconf-ui/**`, so that backend (Python) and frontend (Svelte) regressions in the arrconf-ui sub-project are caught at PR time — paying the v0.4.0 CI dette without changing the chart release behavior.
**Depends on**: None (independent of Phase 16 — different files, different workflows).
**Requirements**: REQ-arrconf-ui-ci
**Success Criteria** (what must be TRUE):
  1. A PR that touches a Python file under `tools/arrconf-ui/` (e.g. `tools/arrconf-ui/arrconf_ui/api.py`) triggers a `tests.yml` job that runs `cd tools/arrconf-ui && uv sync && uv run ruff format --check . && uv run ruff check . && uv run mypy .` and reports its status on the PR. The job fails the PR if any of the triad commands fails.
  2. A PR that touches a frontend file under `tools/arrconf-ui/web/` (e.g. `tools/arrconf-ui/web/src/App.svelte`) triggers a `tests.yml` job that runs `cd tools/arrconf-ui/web && npm ci && npm run check && npm run build` and reports its status on the PR. The job fails the PR if `svelte-check` errors or the Vite build fails.
  3. A PR that touches **only** `tools/arrconf-ui/**` (no `tools/arrconf/**` or `charts/**` change) does **not** trigger the auto-tag step in `chart-lint.yml` (operator-visible: no new `vX.Y.Z` tag created on merge). README updated to document the new CI matrix and which paths trigger which workflow.
  4. The PR that ships REQ-arrconf-ui-ci itself (which touches `.github/workflows/*.yml`) shows the new arrconf-ui CI jobs green on GitHub before merge — operator-checkable on the PR's "Checks" tab.
  5. **No** chart-pin co-bump of `charts/arr-stack/values.yaml#arrconf.image.tag` (CI-only change does not touch `tools/arrconf/**`, so the arrconf image does not rebuild).
**Plans**: TBD (refined by `/gsd-plan-phase`)
**UI hint**: no

### Phase 18: qBit POST credentials fallback
**Goal**: When the `username` / `password` fields of a qBit `download_clients` entry are empty (or omitted) in `arrconf.yml`, the reconciler injects `QBT_USER` / `QBT_PASS` from environment variables at POST/PUT time — idempotent, explicit values always win — so the operator can keep credentials out of the committed YAML without breaking the reconcile.
**Depends on**: Phase 16 (sequential per chart-pin co-bump order: 0.7.0 → 0.8.0 lands first, then 0.8.0 → 0.8.1 patch). Phase 17 is independent and may have landed before Phase 18; either way Phase 18's CI benefits from the extended arrconf-ui gates if any tangential UI test exercises this code path.
**Requirements**: REQ-qbit-post-credentials
**Success Criteria** (what must be TRUE):
  1. The qBit-side `download_clients` reconciler codepath (in `tools/arrconf/arrconf/reconcilers/sonarr.py` / `radarr.py` or shared helper — whichever owns the POST body composition) injects `os.environ["QBT_USER"]` and `os.environ["QBT_PASS"]` when the corresponding YAML field is empty/missing, and uses the explicit YAML value otherwise. If both YAML and env are missing for a credential field, the reconciler raises a `ConfigError` (or equivalent) with a message naming the offending download-client entry — fail-fast, not silent.
  2. Respx unit tests cover the 3 cases: (a) YAML empty/empty + `QBT_USER` and `QBT_PASS` both set in env → POST body contains the env values; (b) YAML explicit/explicit → POST body contains the YAML values (env ignored); (c) partial (YAML username explicit, password empty + env `QBT_PASS` set) → POST body contains YAML username + env password. All 3 tests pass in CI.
  3. Idempotence preserved: a second `arrconf apply` against the live cluster (or unit-test equivalent) emits `0` `plan_action` events on `download_clients` when env-injected credentials match what's already stored cluster-side. No spurious PUT bumps from the new codepath.
  4. Chart-pin co-bump executed in the implementation commit(s): `charts/arr-stack/values.yaml#arrconf.image.tag` bumped from `0.8.0` to `0.8.1` (patch — bugfix), `# renovate: image=...` annotation preserved verbatim. Chart `version:` bumps per existing convention.
  5. Operator UAT: after the chart redeploys with `:0.8.1`, the operator strips `username` / `password` from at least one qBit `download_clients` entry in `arrconf.yml`, commits, waits for ArgoCD sync, and confirms via `kubectl logs -n selfhost <arrconf-cronjob-pod>` that the next `arrconf apply` cycle reports `0` drift on `download_clients` — env injection works end-to-end on the live cluster.
**Plans**: TBD (refined by `/gsd-plan-phase`)
**UI hint**: no

## Progress

| Milestone | Phases | Plans | Status | Completed |
|-----------|--------|-------|--------|-----------|
| v0.2.0 forceSave fix | 11 | 65/66 | ✅ Shipped | 2026-05-17 |
| v0.3.0 Categories first-class | 3 | 16/16 | ✅ Shipped | 2026-05-22 |
| v0.4.0 Categories cleanup + content discovery + local config UI | 4 | 11/11 | ✅ Shipped | 2026-05-23 |
| v0.5.0 Jellyfin Categories-as-libs + CI/UX hardening | 3 | 0/TBD | 🚧 In progress | — |

**Cluster HUMAN-UAT pending from v0.3.0** (operator-exercise opt-in, not blocking):
- Phase 9 initContainer NFS uid=1000 write test (09-HUMAN-UAT.md, 2 open scenarios)
- Phase 10 SC#1 cluster apply Categories-derived path (empty arrconf.yml flat sections to exercise) — REQ-categories-deprecation will exercise this naturally
- Phase 10 SC#3 TVDB-anime live routing test in Seerr UI

**v0.6.0+ carry-forward backlog**:
- REQ-bazarr-addition — Bazarr (subtitles) as an 8th *arr-stack app
- REQ-arrconf-ui-distribution — package `arrconf-ui` for non-dev install
- REQ-config-ui-git-integration — auto-commit/push from UI (after v0.5.0 ships and operator decides)
- REQ-config-ui-multi-config — configarr.yml editing in same UI (ADR-5 frontière check)
- REQ-suggestarr-ingress — SuggestArr ingress + auto-submit (currently port-forward + manual approval)
- REQ-jellyfin-collections — only re-surface if Phase 16 doesn't fully solve Kodi visibility
- D-07-PLAYLIST-MGMT-NULL: re-verify `EnablePlaylistManagement` on Jellyfin 11.x upgrade
- Phase 9 / Phase 10 HUMAN-UAT carry-forward from v0.3.0
