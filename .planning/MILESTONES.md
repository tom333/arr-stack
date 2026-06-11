# Milestones

## v0.11.0 Couche d'intention (tranche 2) (Shipped: 2026-06-11)

**Phases completed:** 3 phases (32-34), 7 plans
**Release:** chart tag `v0.24.0`, arrconf image `:0.22.0` → `:0.24.0`.

**Delivered:** Closed the intention layer — `intent.yml` is now the **single hand-edited source** for the entire stack. Hard-cut migration of `categories[]` into intent (arrconf.yml fully generated + read-only), per-category configarr generation (quality_profiles + custom_formats from TRaSH), and an `arrconf-ui` rebuilt to edit intent.yml only with read-only inspectors + materialization diff. 11/11 requirements validated (CATMIG-01..03, CFGARR-01..04, UI-01..04).

**Key accomplishments:**

- **Categories migration hard cut (Phase 32, arrconf `:0.23.0`)** — `IntentConfig` gains `categories` + `apps`; `RootConfig` drops `categories` (guard rejects hand-edited `categories:` in arrconf.yml); generators retargeted to `list[MediaCategory]`; `generate_arrconf_yml` emits 100% of arrconf.yml deterministically (categories-derived resources materialized at apply-time, not inlined); qbit_manage coupling inverted; CI `generate-idempotence` guard extended to arrconf.yml; `# GENERATED — do not edit` header. CATMIG-01..03 validated.
- **configarr.yml generation (Phase 33, arrconf `:0.24.0`)** — `generate_configarr_yml` emits `quality_profiles` per unique category `profile` + `custom_formats` from the v0.9.0-baked TRaSH catalogue; non-generated sections (`templates`, `includes`, Recyclarr refs) pass through verbatim from a dedicated intent block; ADR-5 preserved by construction (writes a file only, `ScopeViolationError` intact, configarr stays sole TRaSH applier); CI guard extended to configarr.yml. CFGARR-01..04 validated.
- **UI over intent (Phase 34, arrconf-ui only — no image co-bump)** — backend pivoted to `intent.yml` as sole editable source (4 `/api/intent/*` endpoints, legacy PUT removed, atomic writes for all 3 generated files); Svelte 5 three-tab UI (intent editable | arrconf.yml + configarr.yml read-only inspectors); `MaterializationDiffPanel` calling the **real** generators (diff == generate verified live by operator); per-profile TRaSH CF/QP picker re-mounted from v0.9.0. UI-01..04 validated, HUMAN-UAT 3/3 passed.

**Post-milestone review fixes (superpowers plan, 9 commits):** WR-01 atomic generated-file writes, WR-02 form remount-on-reload (stale textarea), WR-03 false aria-modal removed, WR-04 diff-time intent snapshot, WR-05 configarr PUT-removal regression test, IN-01/02 dead API + stale types purged, IN-03 NaN score guard, IN-04 no silent empty-diff fallback; 3 stale `test_io_roundtrip.py` tests retargeted to a dedicated fixture (arrconf.yml is now generated). Backend 77 passed, frontend svelte-check 0/0.

**Patterns established:**

- **Single-source intent (closure of ADR-10):** `intent.yml` is the only hand-edited file for the whole stack; arrconf.yml + configarr.yml join qbit_manage/cross-seed as 100% generated read-only artifacts.
- **Generated-file inspector UI:** the editing surface edits intent only; generated files are surfaced read-only with a pre-commit materialization diff produced by the real generator (no mock), so the operator reviews exactly what will be written.

**Known deferred items at close:** Phase 34 HUMAN-UAT persisted (3/3 passed). Code-review residue resolved by the post-milestone fix plan. No blockers.

---

## v0.10.0 Couche d'intention (tranche 1) (Shipped: 2026-05-31)

**Phases completed:** 4 phases (28-31), 15 plans
**Milestone audit:** `tech_debt` (no blockers) — [`milestones/v0.10.0-MILESTONE-AUDIT.md`](milestones/v0.10.0-MILESTONE-AUDIT.md)
**Stats:** 115 commits, 145 files, +15703/-126, ~6.5h same-day. arrconf `:0.18.0` → `:0.20.0`.

**Delivered:** Generalised the `categories[]` pattern into an explicit intention layer — `intent.yml` (sole hand-edited source) → `arrconf generate` (pure function) → committed verbose configs → `apply`/configarr (unchanged). Tranche 1 ships the `generate` mechanism + 3 absorbed blocks: sagas, cross-seed, qbit_manage. 14/14 v1 requirements validated.

**Key accomplishments:**

- **Generate foundation (Phase 28, arrconf `:0.18.0`)** — `IntentConfig`/`ToolsConfig`/`CrossSeedConfig`/`SagaEntry` pydantic models (`extra="forbid"`) + `load_intent` + `intent-schema-gen`; `arrconf generate` CLI subcommand with `--check` drift mode reusing the `generators/` pure-function pattern (0 I/O, `sort_keys=True` determinism). CI `generate-idempotence` guard in `tests.yml` (`generate --check` + `charts/arr-stack/files/**` path filter, isolated from chart-lint per D-09). **ADR-10** formalises the intention layer + the *absorb-vs-deploy* boundary as an extension of ADR-5 (configarr stays the sole TRaSH applier). INTENT-01..04 validated.
- **Sagas (Phase 29, arrconf `:0.19.0`)** — `SagaEntry` locked (kind movies|series); `apply --intent` optional-load wiring; new **Radarr Collections reconciler** (GET / match-by-`tmdbId` / PUT-on-drift, log-skip absent, idempotent); **tmdbboxsets** Jellyfin plugin via two-run ADR-9 model (GUID bc4aad2e); series sagas → curated **Jellyfin BoxSet** (GET-before-POST idempotent) + Sonarr `arrconf-managed` tag (PUT /series/editor applyTags=add) — presentation-only, no Radarr-style reconciler. SAGAS-01..04 validated.
- **cross-seed (Phase 30, arrconf `:0.19.1`)** — `tools.cross_seed` (token-distinct `${PROWLARR_API_KEY}` + `${QBT_USER}:${QBT_PASS}`, no shared PLACEHOLDER) → generated `config.js` (`module.exports = {...}`); 12th Helm `app-template` alias with Node.js initContainer secret-injection → emptyDir `/config/config.js` via subPath (advancedMounts to avoid PVC shadowing); tcpSocket probes 2468; CI alias-unpack loop + renovate threshold 10→12; operator runbook (PVC + host dir + out-of-stack teardown + rollback). XSEED-01..03 validated (UAT 4/4 PASS).
- **qbit_manage (Phase 31, arrconf `:0.20.0`)** — `QbitManageConfig` (`extra="forbid"`, per-tracker named share_limits groups, recyclebin 30j + tag_nohardlinks default, rem_orphaned/rem_unregistered opt-in default-false) → `generate_qbit_manage()` emits `qbit_manage/config.yml` with **`cat_update: false` + `cat: {}` forced unconditionally** (QBM-02 — arrconf stays sole owner of qBit categories, no second writer) + `!ENV QBT_USER/QBT_PASS` creds (zero secret in git); 13th Helm `app-template` CronJob alias (`0 */4 * * *`, `QBT_RUN=true`+`QBT_SCHEDULE=0` run-once, envFrom arrconf-env); chart-lint annotation-guard 12→14. QBM-01..03 validated.

**Integration:** NO BLOCKERS. 14/14 requirements WIRED end-to-end (intent.yml → generate → commit → Helm deploy → apply); 5/5 E2E flows complete. 3 non-blocking diagnostic warnings recorded as tech debt (see below).

**Known deferred items at close:** 7 (acknowledged, see STATE.md "Deferred Items"). Phases 30/31 VERIFICATION=`human_needed` (runtime cluster observation pending; code 3/3 SC verified — artifact-only debt matching v0.8.0/v0.9.0 pattern); 31-HUMAN-UAT 2 pending scenarios; 3 integration warnings (1-line fixes: `generate_qbit_manage` not in `__all__`, `__main__.py:617` failure label, `cross-seed-config` ConfigMap/PVC name overlap); 2 carry-forward operator tasks (260527-jfk done-frontmatter, media FS migration).

**Patterns established:**

- **Intention layer (ADR-10 / G1 model):** hand-edited `intent.yml` → `arrconf generate` (pure, local, committed) → CI idempotence-gated configs. G2 (in-cluster, loses Git diff/ADR-6) and G3 (auto-commit, auto-tagger noise) rejected.
- **Absorb-vs-deploy boundary:** a tool is *absorbed* (its config generated from intent: cross-seed, qbit_manage) vs *deploy-only* (DB/UI-only state: autobrr deferred). The intention layer never touches configarr's TRaSH endpoints (ADR-5 held).
- **`cat_update:false` forced literal** — when two tools could write the same resource (qBit categories), the generator emits the disabling knob as an unconditional string literal with unit-test assertions, so no code path can produce a conflicting second writer.

---

## v0.9.0 configarr-in-UI + Jellyfin skip-intro (Shipped: 2026-05-31)

**Phases completed:** 4 phases (24-27), 13 plans

**Key accomplishments:**

- **Jellyfin Intro Skipper (Phase 24, arrconf `:0.17.0`)** — arrconf reconciler extended to register the Intro Skipper plugin repo, install it via the two-run model (Run N queues install + logs the single `kubectl rollout restart`, Run N+1 enables + configures with `MaxParallelism=1`), and set `EnableChapterImageExtraction` on all 10 libraries. ADR-9 reverses D-07-PLUGINS-01 to install-capable. Operator live verification (2026-05-31): gating SC#1-4 PASS, Kodi `service.jellyskip` spike = ACCEPT.
- **configarr-in-UI backend (Phase 25)** — `ConfigarrRootConfig` pydantic model (`extra="forbid"`, `readOnly` markers), 4 `/api/configarr/*` endpoints (config GET/PUT, schema, diff), task-zero anti-leak round-trip test preserving `!env`/`!secret` tags verbatim, and a CI pydantic-validation gate (D-08 → Option C, no configarr invocation in CI). ADR-5 boundary held: no *arr API URL in arrconf-ui.
- **configarr-in-UI frontend (Phase 26)** — config selector tab bar + two-config App.svelte orchestration; `configarr.yml` rendered via the existing `FieldInput.svelte` dispatcher with read-only `quality_definition`/`media_naming`, diff preview, unsaved-switch confirm.
- **TRaSH CF/QP pickers + Recyclarr reference (Phase 27)** — build-time-baked TRaSH catalog (CFs + quality profiles, pinned SHAs, zero runtime GitHub HTTP), 3 read-only `/api/trash/*` endpoints, TRaSH CF picker (name→trash_id, multi-id-safe, custom/unknown classification, verbatim-preserve), append-only QP picker (collision-blocked, never touches the 3 hand-rolled profiles), and a read-only Recyclarr template reference (no `include:` insertion — CFGUI-06 boundary).

**Requirements:** 13/13 validated (8 CFGUI + 5 JFSKIP).

**Known deferred items at close: 5** (all previously accepted — see STATE.md Deferred Items). Notable: Phase 27 `27-HUMAN-UAT.md` (2 pending QP scenarios) + `27-VERIFICATION.md` human_needed (code-complete, operator-pending).

**Note:** No git tag created for this GSD milestone — `v0.9.0` already exists as a chart auto-release tag (tags v0.2.0..v0.17.0 are chart releases, not GSD milestones). Milestone is planning-archive only.

---

## v0.8.0 Categories cleanup — v0.2.0 legacy migration close-out (Shipped: 2026-05-27)

**Phases completed:** 4 phases (20-23), 5 plans · 60 commits · 2026-05-25 → 2026-05-27 (~3 days)
**Delivered:** Closed the half-applied v0.2.0 → v0.3.0 Categories migration at the config level — legacy roots/tags/catch-all-DC removed from the live cluster and locked out by code, proven durable via live operator UAT.

**Key accomplishments:**

- **Phase 20** — `arrconf audit` + `audit-verify` read-only legacy-state inventory CLI (`audit.py`, 26 respx tests, `AUTO_PATH_MAPPING` verbatim from CLAUDE.md filesystem table, verify-gate rejects unresolved `?`/`TBD` cells). Closes CAT-CLEANUP-01.
- **Phase 21** — one-shot `tools/scripts/migrate-categories.py` (filesystem `mv` + qBit `setLocation` + Radarr/Sonarr API PUT + Jellyfin refresh); 21 *arr PUTs + 37 torrents relocated live, no halt; ADR-6 pre/post snapshots committed. `both_missing` disk-drift soft-skip deviation. Closes CAT-CLEANUP-02 (file-on-disk sub-clause partial — disk drift).
- **Phase 22** — arrconf `differ.force_prune` path + pydantic legacy-path guard wired on Sonarr/Radarr root_folders/tags/download_clients; shipped `arrconf:0.15.0` (chart co-bump 0.14.1→0.15.0, 455 tests). Live cleanup: 4 legacy roots + catch-all DC id=1 + 3 orphan torrents removed (surgical id-DELETE). Closes CAT-CLEANUP-03.
- **Phase 23** — live operator UAT on `:0.15.0`: SC#1-4 PASS (legacy roots absent Radarr+Sonarr, Seerr→`qBittorrent - Films - Enfants` per-Category DC routing not the deleted catch-all, non-dry-run apply idempotent ×2); SC#5 PARTIAL-deferred (10 libs structured, 3 empty pending media FS migration). Closes CAT-CLEANUP-04.

**Milestone audit:** `tech_debt` (no critical blockers; cleanup goal achieved + proven durable). Integration chain intact 4/4 flows. See [`milestones/v0.8.0-MILESTONE-AUDIT.md`](milestones/v0.8.0-MILESTONE-AUDIT.md).

**Known deferred items at close:** 8 (see STATE.md "Deferred Items" → "Acknowledged at v0.8.0 close"). Notable: no 22-VERIFICATION.md (cross-verified by P23); `force_prune` live-path unexercised (surgical deletes used) — re-verify before `prune:true`; 10 records missing-on-disk; SC#5 media FS migration pending.

**⚠ Tag note:** No git tag created for this milestone. The repo's git tags (`v0.1.0`…`v0.15.0`) are auto-generated **chart release** tags (mathieudutour on push) — a separate scheme from the planning milestone numbering. `v0.8.0` already exists as an old chart tag. Milestone versioning is planning-only here (prior milestones v0.2.0-v0.7.0 likewise un-tagged as milestones).

---

## v0.7.0 Media stack scope closure (Shipped: 2026-05-25)

**Phases:** 0 (doc-only, no phases) | **Plans:** 0 | **Commits:** 1 | **Cluster:** unchanged (arrconf image `:0.14.0`, no code or chart change)

### Delivered

Declared the media stack **complete and closed** — Sonarr, Radarr, Prowlarr, qBittorrent, Seerr, Jellyfin, FlareSolverr, Cleanuparr, SuggestArr (9 apps) + arrconf + configarr. Removed Bazarr from the project's intent surface (CLAUDE.md, spec.md, PROJECT.md, ROADMAP.md) and explicitly declared Bazarr / Lidarr / Whisparr / Readarr **out of scope** with rationale documented to prevent re-introduction at the next backlog review.

This was a deliberate documentation-only scope-narrowing milestone, executed inline (no formal `/gsd-execute-phase` cycle) because the change footprint was 5 file edits with no code, tests, or chart bump. Pattern validated: structural scope decisions can be milestone-recorded without scaffolding overhead.

### Key accomplishments

1. **Bazarr removed from arrconf scope description** — CLAUDE.md and spec.md (lines 13 / 14) listed `(Sonarr, Radarr, Prowlarr, qBittorrent, Seerr, Bazarr)` as the apps arrconf manages. Updated to `(Sonarr, Radarr, Prowlarr, qBittorrent, Seerr, Jellyfin)` — matches the actual implemented scope.

2. **Bazarr removed from spec.md alternative-comparison row** — The Flemmarr line in the alternatives-rejected table said "...étendre à qBit/Seerr/Bazarr"; updated to "...étendre à qBit/Seerr/Jellyfin" to match the actual extension path that shipped (v0.2.0 → v0.5.0).

3. **"Apps potentielles ultérieures" section rewritten** — spec.md §5.3 (image inventory) previously listed Bazarr + Lidarr/Whisparr/Readarr as "hors scope MVP, ajoutables plus tard sans repenser l'architecture". Rewritten as **"Apps explicitement hors scope (décidé v0.7.0)"** with the reason documented inline (no need / homelab UX preference / out of media-video domain).

4. **PROJECT.md "Out of Scope" reasoning expanded** — Replaced the bullet `Bazarr / Lidarr / Whisparr / Readarr — v2 potentiel` (which was an ambivalent "maybe later") with 3 explicit entries: Bazarr (no real need — burned-in subs OR Jellyfin/Kodi native search suffices), Lidarr/Whisparr/Readarr (stack scope = video only, not audio/written/adult), and a stack-closure entry (the 9 apps are complete).

5. **REQ-bazarr-addition removed** from PROJECT.md "Next Milestone candidates", PROJECT.md "Active carry-forward", and ROADMAP.md "v0.7.0+ carry-forward backlog". The requirement no longer exists.

### Decisions

- **D-19-CLOSURE-01** — The media stack is declared complete at 9 apps. Future *arr additions require an explicit revisit of the v0.7.0 Out of Scope decision, not a quiet bump.
- **D-19-RATIONALE-01** — Bazarr's specific rationale (no real need) is documented to prevent it being re-suggested at every milestone close. Burned-in subs cover the typical case; Jellyfin/Kodi native search covers the rest at watch-time, with operator quality control.
- **D-19-VIDEO-ONLY-01** — Lidarr/Whisparr/Readarr are explicitly out because the project scope is **video media** (séries + films). Audio/written/adult content domains have different UX needs (library structure, metadata sources, naming conventions, user preferences) that would warrant their own stack, not a bolt-on.

### Why v0.7.0 had no phases

The change was 5 file edits totaling ~30 lines, doc-only, with no test or build impact. Going through `/gsd-discuss-phase 20` → `/gsd-plan-phase 20` → `/gsd-execute-phase 20` → `/gsd-verify-work 20` would have generated 4-5x more orchestration artifacts than actual content. Inline execution with a milestone entry preserves the historical record (a future grep for "why is Bazarr not in this stack" finds this v0.7.0 decision) without the scaffolding.

Pattern documented: **structural scope decisions** (declaring something explicitly out, retiring a planned-but-never-built feature, archiving a research direction) are valid milestone material even with zero phases — the milestone IS the decision, the artifact IS the doc edit.

---

## v0.6.0 arrconf observability — 4xx body logging (Shipped: 2026-05-25)

**Phases:** 1 (Phase 19) | **Plans:** 1/1 (shipped via /gsd-quick 260525-bj5 instead of /gsd-execute-phase — pattern-appropriate for a 2-line code change) | **Commits:** 5 | **Cluster:** arr-stack tag `v0.14.0`, arrconf image `:0.14.0`

### Delivered

`arrconf/client_base.py` now emits a structured `client_4xx` log event with `response.text[:500]` body excerpt before raising `httpx.HTTPStatusError` on any 4xx response. The v0.5.0 Sonarr `PathExistsValidator` 400 incident — which went unsurfaced for 3 image versions because client_base only logged 5xx response bodies — is no longer possible: the server's actual JSON error message now appears in `arrconf` logs on first occurrence.

Sized as a deliberate micro-milestone (single phase, single deliverable, ~1-2 hours from plan to ship). Executed via `/gsd-quick` rather than full `/gsd-execute-phase` because the change footprint (2 lines of code + 1 test file + 1 chart-pin co-bump) didn't warrant the discuss/plan/execute orchestration overhead. Pattern validated for future micro-milestones.

### Key accomplishments

1. **client_4xx structured log event** (Phase 19 / OBS-01) — Inserted a 9-line block in `ArrApiClient._request` between the 404 `NotFoundError` fast-path (line 78) and the 5xx `ServerError` block (line 79). Payload includes `client` (self.name), `method`, `path`, `status_code`, and `body_excerpt` (`response.text[:500]`). Preserves caller contract: no new exception type, no change to `raise_for_status()` behavior. 401 `AuthError` and 404 `NotFoundError` continue to short-circuit BEFORE the new block, so typed exceptions do NOT trigger spurious `client_4xx` events.

2. **5 respx tests** (`test_client_base_4xx_logging.py`, 82 lines) — Uses `structlog.testing.capture_logs()` (established pattern from `test_reconcilers_sonarr.py:1126`) and `respx` for HTTP mocking. Covers: 400 with short JSON body verbatim, 422 with body > 500 chars truncated, 401 short-circuit (no client_4xx event), 404 short-circuit (no event), 500 ServerError unchanged (no cross-fire). Test count: 411 → 416.

3. **Chart-pin co-bump 0.12.1 → 0.14.0** — Initial atomic commit (`9726d81`) bumped to 0.13.0 per the SC#3 spec. Auto-tag minor-bumped to v0.14.0 (because `feat:` commit prefix with `default_bump: patch` config still produces minor on `feat:`), so a follow-up rescue commit (`a994a9e`) aligned values.yaml → 0.14.0 to match the actual GHCR-published image. The same accumulated-tag-train trap as v0.5.0's `v0.13.0` vs `v0.12.1` mismatch — the existing escape-hatch pattern in CLAUDE.md handled it cleanly.

### Decisions

- **No new exception type for 4xx.** The new block is observational only; `response.raise_for_status()` continues to raise `httpx.HTTPStatusError` as before. Preserves caller contract and minimizes surface area.
- **Distinct event name `client_4xx`.** Symmetric to a hypothetical future `client_5xx` if `ServerError` is ever refactored to structlog. Keeps log filters cleanly separable from the typed-exception fast-paths.
- **`text[:500]` cap (vs 5xx's `text[:200]` cap).** 4xx bodies typically contain validation error arrays with field paths and messages (e.g., Sonarr's `PathExistsValidator` response is ~150 chars per error × N errors). 500 chars accommodates 2-3 validation errors without truncation. The 5xx cap stays at 200 (5xx bodies are usually generic stack traces — first 200 chars are enough to identify the failure class).
- **Shipped via `/gsd-quick`** (not `/gsd-execute-phase`) — Phase 19 was correctly recognized as size-appropriate for the quick path during scope confirmation. Pattern: micro-milestones (≤ 3 tasks, ≤ 1 hour, no architectural decisions) may bypass discuss/plan/execute and go straight to quick orchestration; Phase 19 remains in ROADMAP.md as `[x]` with a "shipped via /gsd-quick" note for traceability.

### Tech debt observed (carry-forward to v0.7.0+)

- **Auto-tag train alignment STILL bites every milestone close.** v0.5.0 hit it (v0.13.0 auto-tag vs values.yaml 0.12.1), v0.6.0 hit it again (v0.14.0 auto-tag vs values.yaml 0.13.0). Both resolved cleanly via the CLAUDE.md "Accumulated-bumps escape hatch", but the recurrence suggests a process improvement: either (a) push every conventional-commit phase commit individually so auto-tag fires per-commit and chart-pin co-bumps stay in lock-step, OR (b) add a post-push verification step that compares the latest auto-tag against `values.yaml#arrconf.image.tag` and emits a rescue commit automatically. Candidate for a v0.7.0 process micro-plan.
- **`milestone.complete` SDK accomplishments extractor pulls stale phase data.** When v0.6.0 closed via a quick task, the SDK scanned `.planning/phases/` (which still has Phase 9/10/11 v0.3.0 carry-forward) and extracted random one-liners that have nothing to do with v0.6.0. The MILESTONES.md entry had to be manually rewritten. Worth either improving the extractor to scope by milestone phase range, OR making the manual rewrite an explicit step in the workflow.

---

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
