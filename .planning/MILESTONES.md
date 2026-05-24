# Milestones

## v0.5.0 Jellyfin Categories-as-libs + CI/UX hardening (Shipped: 2026-05-24)

**Phases:** 3 (16-18) | **Plans:** 3/3 | **Commits:** 31 since v0.4.0 close | **Cluster:** arr-stack tag `v0.13.0` (with rescue tag `v0.12.1`), arrconf image `:0.12.1`

### Delivered

Jellyfin now exposes the 10 v0.3.0 Categories as native top-level libraries (1 `VirtualFolder` per Category instead of 2 super-libs), making Categories visible structurally in every Jellyfin client — web, Swiftfin, and most importantly **JellyCon on the LibreELEC salon mini-PC** (Kodi-side visibility was the original driver). `tools/arrconf-ui/**` is now covered by CI (`arrconf-ui-backend` triad + `arrconf-ui-frontend` quad, both green on closure commit) while remaining architecturally isolated from `chart-lint.yml` (UI-only PRs do NOT trigger auto-tag, by design). qBit POST credentials now resolve from `QBT_USER` / `QBT_PASS` env vars at reconcile time with a pre-flight gate in `__main__.py` and fail-fast `ConfigError` when both YAML and env are empty — verified dispositively on the live cluster with 9/9 Sonarr + 9/9 Radarr qBit DCs returning HTTP 200 on `/api/v3/downloadclient/test` (auth confirmed against live qBittorrent).

### Key accomplishments

1. **Jellyfin Categories-as-libs** (Phase 16) — `generate_jellyfin()` refactored to emit 10 `VirtualFolder` libs (1 per Category) replacing the 2 super-libs (D-07-LIB-01 reversed by D-16-PRUNE-01). `_reconcile_libraries()` extended with CREATE + prune-gated DELETE so the cutover doesn't destroy operator-added ad-hoc libs. SC#1-2-3 validated live on cluster: 10 libs visible in Jellyfin web UI ✓, 12 paths pruned from legacy super-libs ✓, prune re-locked false post-cutover ✓. SC#4 (JellyCon LibreELEC top-level browse) carry-forward per D-16-JELLYCON-UAT-01. Image bump landed as `0.10.x` after a tag-collision detour caught and documented in CLAUDE.md.

2. **arrconf-ui CI coverage** (Phase 17) — `tests.yml` path-filter extended to include `tools/arrconf-ui/**` + 2 new jobs (`arrconf-ui-backend` triad `ruff format --check` + `ruff check` + `mypy .` + `pytest -q` 32 tests / 13 files mypy-clean; `arrconf-ui-frontend` quad `npm ci` + `npm run check` + `npm run typecheck` + `npm run build` 92 files / 0 errors). `chart-lint.yml` intentionally UNCHANGED (architectural SC#3 dispositive — UI-only PR never triggers auto-tag). Lockfiles `tools/arrconf-ui/uv.lock` + `web/package-lock.json` committed (Phase 15 oversight fix). 3/3 jobs green on closure commit `c53c9a3`.

3. **qBit POST credentials fallback** (Phase 18) — `_resolve_qbit_credentials_from_env()` helper in `_shared.py` injects `QBT_USER` / `QBT_PASS` for Sonarr+Radarr qBit DCs when YAML fields are empty; YAML explicit wins verbatim when present; both empty raises `ConfigError` (D-18-FAIL-FAST-01). Pre-flight gate in `__main__.py` (added during code-review auto-fix CR-02) validates ALL qBit DC credentials BEFORE any Step 1-5 POSTs fire, preventing partial-reconcile state on missing env. 12 respx tests cover the 5 mandated cases + asymmetric env tests + idempotence regression test. Idempotence acquired by construction via existing `differ.merge_fields_for_put` + `_strip_redacted_fields` (D-02.2-AUTH-REGRESSION + D-18-IDEMPOTENCE-FREE). Code review auto-fix loop: 2 BLOCKERs + 5 WARNINGs surfaced and resolved before live deploy. Cluster UAT: 9/9 Sonarr + 9/9 Radarr qBit DCs HTTP 200 on `/api/v3/downloadclient/test`; 0 plan_actions on download_clients on 2nd run (idempotence dispositive).

4. **Side-quest unblock: Sonarr RPM 400 debug** (during Phase 18 UAT) — surfaced a pre-existing bug that pre-dated Phase 18 by ≥3 image versions: Sonarr v4's `PathExistsValidator` on `POST /api/v3/remotepathmapping` was rejecting categories[]-derived RPMs because the matching `/data/<category>/` dirs didn't exist on the qBittorrent volume (CLAUDE.md filesystem-migration runbook never ran on `/data/torrents/`). Captured via `/gsd-debug` session, fixed via 8× `mkdir -p` operator command, debug session archived to `.planning/debug/resolved/sonarr-rpm-400-categories.md`.

### Decisions

- **D-16-PRUNE-01** — Reverses D-07-LIB-01. Single-tenant homelab UX (everybody sees everything) doesn't need the "clean 2-section UI" rationale; 10 libs is the right native Kodi/JellyCon shape.
- **D-16-JELLYCON-UAT-01** — JellyCon LibreELEC top-level browse UAT carry-forward, non-blocking for Phase 16 close.
- **D-17-WORKFLOW-01** — Path-filter on `tests.yml` triggers ALL 3 jobs on any matching path; `chart-lint.yml` intentionally unchanged so UI-only PRs never trigger auto-tag.
- **D-18-INJECT-LOC-01** — Helper lives in `_shared.py` and is called from Sonarr + Radarr Step 6 between `_resolve_download_client_tag_labels` and `_ensure_managed_tag_in_desired`.
- **D-18-FAIL-FAST-01** — Pinned `ConfigError` message format `f"download_client '{dc.name}': username is empty in YAML AND QBT_USER env is unset/empty"`.
- **D-18-SCOPE-01** — Helper wired into Sonarr + Radarr ONLY; Prowlarr/Seerr/Jellyfin/qBittorrent-native untouched.
- **D-18-IDEMPOTENCE-FREE** — SC#3 idempotence reuses the existing `differ._strip_redacted_fields` privacy-by-metadata stripping; no new code path.
- **D-18-CHART-BUMP-01** — Initial patch bump 0.10.0 → 0.10.1, then 0.10.1 → 0.10.2 in the fix-batch with CR-01/CR-02 auto-fix commits, then 0.10.2 → 0.12.1 as a final co-bump to align with the v0.13.0 auto-tag train.

### Tech debt observed (carry-forward to v0.6.0+)

- **client_base.py 4xx body logging** — `_request` logs `response.text[:200]` only for 5xx; 4xx raises raw `HTTPStatusError` with no body excerpt. This is why the Sonarr `PathExistsValidator` 400 went unsurfaced for 3 image versions. 2-line change candidate for an observability micro-plan.
- **Tag train alignment** — Auto-tag minored to v0.13.0 because Phase 17's `feat(17): arrconf-ui CI coverage` commit was unreleased between v0.12.0 (Phase 16 SC#3) and the Phase 18 push. The "Accumulated-bumps escape hatch" pattern from CLAUDE.md handled it correctly (manual `v0.12.1` rescue tag at HEAD), but the underlying issue — auto-tag aggregates ALL unreleased conventional-commit bumps from prior phases — should be a process note for future milestones.
- **HUMAN-UAT format consistency** — Audit-open parser doesn't recognize the project's Markdown `**Status:**` header convention (only YAML frontmatter `status:`). Headers updated to `Status: closed` during this milestone close, but a future micro-plan could standardize on frontmatter-style metadata across all HUMAN-UAT files.

---

## v0.4.0 Categories cleanup + content discovery + local config UI (Shipped: 2026-05-23)

**Phases:** 4 (12-15) | **Plans:** 11/11 | **Commits:** 73 | **Cluster:** arr-stack chart `v0.8.2`, arrconf image `:0.7.0`

### Delivered

The v0.2.0 transition layer is fully ripped out (no `merge_with_manual`, no flat `items:` sections; the pure-function generators in `arrconf/generators/categories.py` are the only reconciler input source). SuggestArr ships as the 11th `bjw-s/app-template` alias in the umbrella chart with Categories-aware Seerr routing wired through `SEER_ANIME_PROFILE_CONFIG`. `tools/arrconf-ui/` ships as a single-binary FastAPI + Svelte 5 SPA editing `arrconf.yml` from the LAN with pydantic validation, ruyaml round-trip preserving comments, a semantic diff preview, French i18n on every label and tooltip, and a dark theme — operator UAT signed off on all 10 scenarios.

### Key accomplishments

1. **Categories deprecation — clean ripout** (Phase 12) — `merge_with_manual()` deleted; reconciler signatures accept `*Derived` dataclasses directly; 11 flat `items:` blocks removed from `arrconf.yml`; pydantic Section models slimmed with `extra="forbid"` to refuse stale YAML; 8 manual-path tests deleted and 8 sweep tests renamed; CLAUDE.md "v0.3.0 → v0.4.0 deprecation" runbook documents the operator one-shot edit; SC#5 dispositive `arrconf apply --dry-run` on live cluster post-deprecation emits the same plan_action shape as pre-deprecation.

2. **SuggestArr architecture decision locked via source-code evidence** (Phase 13) — `gsd-phase-researcher` spike confirmed Option A (Helm sidecar) using SuggestArr's native `SEER_ANIME_PROFILE_CONFIG` per-request routing (rootFolder + profileId + tags). SEED-001 closed with frontmatter `closed_in: v0.4.0 Phase 13`; phase 14 preflight handoff document emitted; zero production-code drift in this phase.

3. **SuggestArr in-cluster** (Phase 14) — 11th `bjw-s/app-template@5.0.0` alias in `Chart.yaml` + Helm 4 multi-alias unpack workaround codified in CI; `suggestarr-env` SealedSecret with Jellyfin + Seerr + TMDB keys (operator-merged into existing `arrconf-env`); ConfigMap dropped after plan-checker BLOCKER (SuggestArr ignores it at runtime — documented in RESEARCH); integration test asserts Categories routing maps `anime-zoe` → Sonarr profile 4 root `/media/series-zoe` and equivalents for the other 9 categories. Live cluster passed readiness on first ArgoCD sync after TMDB key seeded.

4. **Local config UI** (Phase 15) — `tools/arrconf-ui/` Python package exposes 4 FastAPI endpoints (`GET/PUT /api/config`, `GET /api/schema`, `POST /api/diff`); reuses `tools/arrconf/arrconf/config.py` pydantic models + atomic ruyaml round-trip preserving comments and key order; semantic diff endpoint reports added/removed/changed entries per top-level section. Frontend is Svelte 5 vanilla + Vite + TS — single `FieldInput.svelte` 6-branch dispatcher walks the JSON Schema (D-13 schema-driven form) with HelpTooltip surfacing pydantic descriptions verbatim. Frontend-design skill applied mid-execution: IBM Plex Sans + Mono, architectural-blueprint palette, full French i18n (FIELD_LABELS, FIELD_DESCRIPTIONS, SECTION_DOCS), dark theme via `[data-theme]` attribute, `[object Object]` array-of-objects rendering bug fixed via repeatable nested form. D-04 amended mid-cycle to bind `0.0.0.0` for LAN access per operator request.

5. **Release pipeline survives the milestone batch** — 4 image co-bumps (`0.6.7 → 0.7.0` in Phase 12; `0.6.7` unchanged for sidecar-only Phases 13/14; `0.7.0` unchanged for Phase 15 since arrconf code untouched) executed cleanly. Path-filter on `chart-lint.yml` + `tests.yml` correctly excluded `tools/arrconf-ui/**` from CI gates — locally-verified triad + Svelte build accepted as sufficient for homelab.

6. **Operator UAT all-green** — Phase 15 `15-HUMAN-UAT.md` 10/10 scenarios PASSED including LAN reachability (Scenario 10), schema validation 422 surfaced inline, comment preservation via ruyaml, dark theme persistence, French copy on every visible string, repeatable nested rules rendered correctly for sonarr/radarr.

### Validated v0.4.0 requirements (6/6)

All 6 REQs marked Complete in [`milestones/v0.4.0-REQUIREMENTS.md`](milestones/v0.4.0-REQUIREMENTS.md): REQ-categories-deprecation, REQ-suggestarr-research, REQ-suggestarr-integration, REQ-local-config-ui-backend, REQ-local-config-ui-frontend, REQ-local-config-ui-packaging.

### Known deferred items at close

- **REQ-arrconf-ui-ci** — path-filter on `chart-lint.yml` + `tests.yml` excludes `tools/arrconf-ui/**`; CI coverage punted to v0.5.x
- **REQ-arrconf-ui-distribution** — UI currently runs from source via `uv run` only; packaging deferred
- **SuggestArr ingress + auto-submit** — port-forward + manual approval baseline; ingress + auto-submit punted
- **Auto-tag chain for arrconf-ui-only changes** — same path-filter caveat; v0.8.2 is the latest chart tag, UI changes don't bump
- **Phase 9 / Phase 10 HUMAN-UAT carry-forward from v0.3.0** — still open, still not blocking

### Cluster end state

- arr-stack chart **v0.8.2** rendered by ArgoCD, arrconf image **`:0.7.0`**, SuggestArr running as 11th alias
- `arrconf-env` SealedSecret extended with Jellyfin + Seerr + TMDB keys (kubeseal `--merge-into`)
- `arrconf-ui` runs from source on the operator laptop, bound to `0.0.0.0:8765`, no auth (homelab single-tenant)
- Snapshots: `before-phase-12-2026-05-22/` + `after-phase-12-2026-05-22/`

### Archive references

- [`milestones/v0.4.0-ROADMAP.md`](milestones/v0.4.0-ROADMAP.md) — full per-phase scope, success criteria, lessons learned
- [`milestones/v0.4.0-REQUIREMENTS.md`](milestones/v0.4.0-REQUIREMENTS.md) — all 6 v0.4.0 requirements with final status
- [`milestones/v0.4.0-phases/`](milestones/v0.4.0-phases/) — 4 phase directories (Phase 12 5 plans, Phase 13 1 plan, Phase 14 3 plans, Phase 15 2 plans)
- Git tag: `v0.4.0` (commit TBD after milestone-close commit)

---

## v0.3.0 Categories first-class (Shipped: 2026-05-22)

**Phases:** 3 (9-11) | **Plans:** 16/16 | **Commits:** 87 | **Cluster:** arr-stack chart `v0.7.0`, arrconf image `:0.6.7`

### Delivered

A single declarative `categories[i]` entry in `arrconf.yml` now propagates across all 6 apps (qBit categories + Sonarr 4-resources + Radarr 4-resources + Seerr animeTags + Jellyfin 2-superlibs) and auto-creates the matching `/media/<name>` directory via a chart-mounted initContainer Job. 10 production categories (5 movies + 5 series) reproduce the operator's real-world content organization. Plus closure on the 8-item operational carry-forward bundle from v0.2.0 — `arr-stack v0.3.0 is operationally complete`.

### Key accomplishments

1. **Categories first-class data model** (Phase 9) — Pydantic-validated `categories[]` block at `RootConfig` level with required fields `name`/`kind`/`profile`/`display`/`base_path`. JSON Schema regenerates via `arrconf schema-gen`. 10 production categories declared in `charts/arr-stack/files/arrconf.yml`. Helm-hooked initContainer Job creates `/media/<name>` dirs idempotently (busybox:1.36.1, uid 1000:1000, NFS-safe).

2. **Pure-function generator architecture** (Phase 10-A + 10-B) — New `tools/arrconf/arrconf/generators/categories.py` module exposes 5 generators (qBit, Sonarr, Radarr, Jellyfin, anime-tag-labels). Pre-merge dispatch in `__main__.py` (apply + diff branches, Pitfall 5). `merge_with_manual` helper in `reconcilers/_shared.py` implements D-02 per-resource toggle: manual flat-section non-empty → manual wins; empty → Categories-derived. Reconciler signatures unchanged.

3. **Dispositive idempotence on live cluster** (Phase 10-C/F/H/J + follow-up `310aebf`) — 2nd-run `arrconf apply` emits 0 `plan_action` events across all 6 apps. Three B2-allowlist FP fixes (qBit categories, Prowlarr Application + fields[] sub-allowlist, Seerr user) + `ProwlarrInstance.prowlarr_url` field separation (API-access URL vs in-cluster `prowlarrUrl` injection). 384 unit tests + dual-path SC#2 sweep + live cluster proof (2026-05-22).

4. **Release pipeline hardening** (Phase 10-I + Phase 11 follow-ups) — Chart-pin co-bump pattern documented in CLAUDE.md "Release pin co-bump pattern" + injected into `gsd-executor` agent prompt. Practiced across 10 plans (0.5.3 → 0.6.7). Accumulated-bumps escape hatch documented for batch-push scenarios. CI workflow `github.ref_name` bug-fix (`12c05da`) ensures `:0.6.7` and similar tags publish correctly on git-tag pushes (previously only `:latest` + `:sha-<short>` were emitted).

5. **Operational polish closeout** (Phase 11) — ArgoCD `selfHeal: true` + `prune: true` dispositive drift-UAT on live cluster (kubectl scale → auto-revert within 3 min). Legacy ConfigMaps (`arrconf`, `configarr`) absent (auto-pruned by ArgoCD). Pre-commit hook with `astral-sh/ruff-pre-commit` belt-and-suspenders alongside CI `ruff format --check`. `tools/snapshot/snapshot.sh` auto-redacts apiKey/password/token/webhookUrl/sessionKey via inline jq filter (with `mv -f` to bypass interactive prompt). Mend Renovate App installed → cross-repo loop validated end-to-end (my-kluster PR #1413 v0.7.0 MERGED).

6. **Frontière integrity preserved** — ADR-5 (configarr quality_profiles frontière) intact: `ScopeViolationError` enforcement preserved on 4 resource types, 0 grep hits on `configarr.yml` in any reconciler. ADR-6 (snapshot baseline before risky tests) extended: snapshot.sh now auto-redacts secrets by default. ADR-7 (single-instance + tags) continues: 5 tags per side (Sonarr + Radarr), no multi-instance plumbing. ADR-8 (ArrApiClient + `_ArrV3Client` mixin) unchanged.

### Validated v0.3.0 requirements (18/18)

All 18 REQs marked Complete in [`milestones/v0.3.0-REQUIREMENTS.md`](milestones/v0.3.0-REQUIREMENTS.md): Categories Data Model (2), Propagation (6), Migration Strategy (3), Operational Polish (8 incl. REQ-chart-pin-prebump + REQ-idempotence-fp-fix), Documentation (1).

### Retired requirement

- **REQ-eso-akeyless-migration** (was Phase 8 in v0.2.0 roadmap) — retired 2026-05-22 by user decision. Bitnami sealed-secrets is the long-term baseline; no external-secret migration planned. REQ-secret-management closed in spirit.

### Known deferred items at close: 3

See [`STATE.md`](STATE.md) Deferred Items + [`v0.3.0-MILESTONE-AUDIT.md`](v0.3.0-MILESTONE-AUDIT.md). All 3 are HUMAN-UAT operator-exercise items (Phase 9 initContainer NFS write test, Phase 10 SC#1 + SC#3 cluster materialization + TVDB-anime routing), not code defects. Non-blocking for v0.3.0 ship.

### Cluster end state

- arr-stack chart **v0.7.0** rendered by ArgoCD (chart's `arrconf.image.tag = "0.6.7"`)
- 9 apps + 2 CronJobs (arrconf, configarr) running in `selfhost` namespace, all Synced + Healthy
- ArgoCD `automated.selfHeal: true` + `automated.prune: true` (dispositive UAT 2026-05-21)
- Mend Renovate App active on `tom333/arr-stack` — cross-repo loop validated
- Snapshots: v0.2.0 baselines + `before-phase-10-2026-05-19/` + `before-argocd-selfheal-uat-2026-05-21/` (anti-leak auto-redaction baked in)

### Archive references

- [`milestones/v0.3.0-ROADMAP.md`](milestones/v0.3.0-ROADMAP.md) — full per-phase scope and success criteria
- [`milestones/v0.3.0-REQUIREMENTS.md`](milestones/v0.3.0-REQUIREMENTS.md) — all 18 v0.3.0 requirements with final status
- [`milestones/v0.3.0-phases/`](milestones/v0.3.0-phases/) — 3 phase directories (Phase 9 4 plans, Phase 10 10 plans, Phase 11 2 plans)
- [`v0.3.0-MILESTONE-AUDIT.md`](v0.3.0-MILESTONE-AUDIT.md) — cross-phase integration verdict `passed_with_caveats`
- Git tag: `v0.3.0` (commit TBD after milestone-close commit)

---

## v0.2.0 forceSave fix (Shipped: 2026-05-17)

**Phases:** 11 | **Plans:** 65/66 | **Tasks:** ~109 | **Cluster:** arr-stack chart `v0.5.2`, arrconf image `:0.5.0`

### Delivered

The MVP of arr-stack: a Python reconciler (`arrconf`) that drives 6 *arr-stack apps from declarative YAML, packaged in a Helm umbrella chart, deployed to MicroK8s via a single ArgoCD Application, with CI auto-tag → image build → Renovate-style PR loop bumping the cluster. UI-free configuration achieved end-to-end.

### Key accomplishments

1. **6-app declarative reconciler coverage** — Sonarr (download_clients, tags, root_folders, indexers, host_config, notifications), Radarr (movies-side equivalents), Prowlarr (app sync), qBittorrent (categories + preferences), Seerr (services connectés + admin user + main settings + content_tags routing), Jellyfin (libraries + admin user policy + server config + plugins). Each reconciler is idempotent (`arrconf dump | arrconf diff` returns 0 drift), respects `prune: false` by default, and lives behind a hardcoded scope frontier against configarr's quality_profiles/custom_formats/quality_definitions/media_naming.

2. **9-app umbrella chart deployed to production** (Phase 4) — Single ArgoCD Application at `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` pulls `charts/arr-stack/` (10 `bjw-s/app-template@5.0.0` aliases + arrconf + configarr CronJobs). Replaced 10 unit ArgoCD Applications. Renovate `customManagers` regex tracks all image annotations in `values.yaml`.

3. **CI auto-tag → GHCR image build chain operational** (Phase 5.1) — `chart-lint.yml` runs `helm lint + kubeconform + 5 guards + auto-tag` on every push touching `charts/` or `tools/arrconf/`. A `repository_dispatch` bridges the auto-tag job to `arrconf-image.yml` which publishes `ghcr.io/tom333/arr-stack-arrconf:vX.Y.Z` anonymously pullable. Operator drives `targetRevision` bump in my-kluster (Renovate App not yet installed — manual fallback documented).

4. **forceSave + credential-aware merge** (Phase 2.1 + 2.2) — `?forceSave=true` query param added to `_ArrV3Client.put()` bypasses *arr UI-grade pre-save validation (ADR-8), enabling automated drift correction; `merge_fields_for_put` helper omits credential-like fields when the YAML value is empty AND detects API-mask `"********"` to prevent stomping cluster-stored passwords. v0.1.6 closed the D-02.1-06 / D-02.2-AUTH-REGRESSION architectural finding with a composite dispositive (Sonarr Test API HTTP 200 + credential survival + manual_nudge_used=NO).

5. **Phase 5 split tv/anime/family layout** — qBittorrent now has 6 categories (sonarr-tv, sonarr-anime, sonarr-family, radarr-movies, radarr-anime, radarr-family) routing torrents to `/media/{series,anime,family,films,films-anime,films-family}`. Sonarr/Radarr each manage 3 download clients tagged by route, 3 root folders, 3 tags. ADR-7 single-instance-with-tags pattern validated in production. configarr produces 3 corresponding quality profiles per instance (MULTi.VF, Anime, Family).

6. **Phase 6 + Phase 7 reconciler hardening** — Seerr's `D-06-OPENAPI-01` (hot-fix in `:0.4.4` for activeProfileName / activeAnimeProfileName not actually being server-computed) and Jellyfin's 9 Pitfalls (POST-not-PUT for /Configuration full-replace + /VirtualFolders/Paths non-idempotent + /Plugins/{id}/{version}/Enable + UserPolicy AuthenticationProviderId re-injection + others) catalog the empirical gotchas of writing to live *arr APIs. Both reconcilers shipped with ≥10 respx tests each, ≥84% coverage on the new code paths.

### Validated v1 requirements (17/19)

Closed: REQ-baseline-snapshot, REQ-config-as-code, REQ-idempotence, REQ-umbrella-deployment, REQ-renovate-image-tracking, REQ-configarr-coexistence, REQ-bootstrap-exception, REQ-pr-to-cluster-latency, REQ-helm-validation, REQ-test-coverage, REQ-cli-subcommands, REQ-yaml-autocomplete, REQ-prune-opt-in, REQ-managed-tag (Sonarr/Radarr/Prowlarr — Jellyfin N/A), REQ-phase-roadmap, REQ-app-coverage (6 apps), REQ-drift-detection.

Carried to v0.3.0: REQ-readme-onboarding (README exists but not yet operator-validated for the < 30-min onboarding metric), REQ-secret-management (sealed-secrets working — closed in spirit, no migration planned).

### Known deferred items at close: 16

See [`STATE.md`](STATE.md) Deferred Items section + [`ROADMAP.md`](ROADMAP.md) Carry-forward backlog. All 16 are non-blocking for v0.2.0 ship; bundle for v0.3.0 grooming.

### Cluster end state

- arr-stack chart **v0.5.2** rendered by ArgoCD (chart's `arrconf.image.tag = "0.5.0"`)
- 9 apps + 2 CronJobs (arrconf, configarr) running in `selfhost` namespace
- `arrconf-env` SealedSecret has 7 keys: SONARR_API_KEY, RADARR_API_KEY, PROWLARR_API_KEY, QBT_USER, QBT_PASS, SEERR_API_KEY, JELLYFIN_API_KEY
- Snapshots: 11 baseline + post-apply directories under `snapshots/` (Phase 0 baseline + per-phase before/after pairs, anti-leak clean)

### Archive references

- [`milestones/v0.2.0-ROADMAP.md`](milestones/v0.2.0-ROADMAP.md) — full per-phase scope and success criteria
- [`milestones/v0.2.0-REQUIREMENTS.md`](milestones/v0.2.0-REQUIREMENTS.md) — all v1 requirements with final status
- [`milestones/v0.2.0-phases/`](milestones/v0.2.0-phases/) — 11 phase directories (plans + summaries + evidence)
- Git tag: `v0.2.0` (commit TBD after milestone-close commit)
