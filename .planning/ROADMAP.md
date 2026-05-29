# Roadmap: arr-stack

## Milestones

- ✅ **v0.2.0 forceSave fix** — Phases 0-7 (shipped 2026-05-17)
- ✅ **v0.3.0 Categories first-class** — Phases 9-11 (shipped 2026-05-22)
- ✅ **v0.4.0 Categories cleanup + content discovery + local config UI** — Phases 12-15 (shipped 2026-05-23)
- ✅ **v0.5.0 Jellyfin Categories-as-libs + CI/UX hardening** — Phases 16-18 (shipped 2026-05-24)
- ✅ **v0.6.0 arrconf observability — 4xx body logging** — Phase 19 (shipped 2026-05-25 via /gsd-quick 260525-bj5)
- ✅ **v0.8.0 Categories cleanup — v0.2.0 legacy migration close-out** — Phases 20-23 (shipped 2026-05-27)
- 🚧 **v0.9.0 configarr-in-UI + Jellyfin skip-intro** — Phases 24-27 (in progress)

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

### v0.9.0 — configarr-in-UI + Jellyfin skip-intro (Phases 24-27)

- [ ] **Phase 24: Jellyfin Intro Skipper** — arrconf reconciler extension: plugin repo + install + chapter extraction + Kodi spike
- [ ] **Phase 25: configarr-in-UI backend** — `!env` guard (task-zero) + `ConfigarrRootConfig` pydantic model + 4 endpoints + CI dry-run gate
- [ ] **Phase 26: configarr-in-UI frontend** — config selector tab + configarr form via existing `FieldInput.svelte` dispatcher
- [ ] **Phase 27: TRaSH CF picker + Recyclarr reference** — build-time-baked TRaSH catalog + `TrashPicker.svelte` + Recyclarr read-only informational dropdown

## Phase Details

### Phase 24: Jellyfin Intro Skipper
**Goal**: The Jellyfin server can detect and skip intros, credits, and outros for web/app/Swiftfin users, with chapter markers benefiting all clients including Kodi; the entire setup is declared in `arrconf.yml` and reconciled idempotently by arrconf
**Depends on**: Nothing (pure arrconf extension, independent of Phases 25-27)
**Requirements**: JFSKIP-01, JFSKIP-02, JFSKIP-03, JFSKIP-04, JFSKIP-05
**Success Criteria** (what must be TRUE):
  1. `arrconf apply` (dry-run) logs that the Intro Skipper plugin repository (`https://intro-skipper.org/manifest.json`) is registered and the plugin entry (GUID `c83d86bb-a1e0-4c35-a113-e2101cf4ee6b`) queued-for-install — both idempotent on second run (zero actions)
  2. After operator runs `kubectl rollout restart deployment/jellyfin -n selfhost` and a second `arrconf apply`, the plugin appears active in `GET /Plugins` and no duplicate repository entries exist
  3. Jellyfin web UI shows a skip-intro/skip-credits button during playback on at least one series episode (web client SC is dispositive; Swiftfin treated as equivalent)
  4. `EnableChapterImageExtraction: true` is confirmed set on all 10 libraries via `GET /Library/VirtualFolders` (seek-bar thumbnails visible in at least one client)
  5. Kodi/JellyCon spike result documented with binary accept (service.jellyskip works on LibreELEC 10.11.8) or reject (unsupported, runbook notes it as operator-manual only) — spike is non-gating but result is required before phase is declared complete
**Plans**: 3 plans
  - [x] 24-01-PLAN.md — Schema/model + chapter-extraction reconciler + Intro Skipper repo registration (JFSKIP-01, JFSKIP-04)
  - [x] 24-02-PLAN.md — Two-run install + enable + plugin-config logic + co-bump 0.16.0 + ADR reversal (JFSKIP-02, JFSKIP-03)
  - [ ] 24-03-PLAN.md — Operator runbook + live two-run verification + Kodi spike (JFSKIP-05)
**UI hint**: no

### Phase 25: configarr-in-UI backend
**Goal**: The arrconf-ui backend can read, validate, diff, and write `configarr.yml` with the same safety guarantees as `arrconf.yml`, including zero risk of secret leakage via `!env`/`!secret` tag drop
**Depends on**: Nothing (independent of Phase 24; can run in parallel)
**Requirements**: CFGUI-01, CFGUI-02, CFGUI-03, CFGUI-07
**Success Criteria** (what must be TRUE):
  1. A round-trip test loads the real `charts/arr-stack/files/configarr.yml`, writes it to a temp file, and asserts that every `!env` and `!secret` tag is present verbatim in the output bytes — this test ships as task-zero before any other configarr write-path code
  2. `GET /api/configarr/config` returns the parsed configarr.yml; `PUT /api/configarr/config` writes back without corrupting `!env`/`!secret` tags (verified by the round-trip test)
  3. `GET /api/configarr/schema` returns a JSON Schema with `api_key` fields marked `readOnly: true`; no `*arr` API URL appears anywhere in the arrconf-ui source (ADR-5 boundary assertion)
  4. `POST /api/configarr/diff` returns the diff between current and proposed YAML without resolving env vars — the literal string `!env SONARR_API_KEY` (or equivalent) appears in the diff output, never a resolved secret value
  5. A CI gate validates the YAML written by `PUT /api/configarr/config` via `ConfigarrRootConfig.model_validate` (pydantic-only, D-08 RESOLVED → Option C: configarr v1.28.0 has no offline validate mode, so the `extra="forbid"` pydantic model is the authoritative structural gate; no *arr containers, no configarr invocation in CI)
**Plans**: 4 plans
Plans:
- [ ] 25-01-PLAN.md — Task-zero anti-leak round-trip test + tag-literal read helper + configarr path resolvers (CFGUI-01)
- [ ] 25-02-PLAN.md — ConfigarrRootConfig pydantic model (fully typed, extra="forbid", readOnly markers) + local JSON Schema generator (CFGUI-02)
- [ ] 25-03-PLAN.md — 4 /api/configarr/* endpoints + configarr-shape structured diff + D-09 anti-leak runtime guard (CFGUI-01, CFGUI-03)
- [ ] 25-04-PLAN.md — CI gate: pydantic validation of the committed configarr.yml + schema-reproducibility check (CFGUI-07)
**UI hint**: no

### Phase 26: configarr-in-UI frontend
**Goal**: Operators can select, view, and edit `configarr.yml` from the arrconf-ui web interface alongside `arrconf.yml`, using the same schema-driven form pattern
**Depends on**: Phase 25
**Requirements**: CFGUI-04
**Success Criteria** (what must be TRUE):
  1. The arrconf-ui web UI displays a config selector (e.g., tab or dropdown) allowing the operator to switch between `arrconf.yml` and `configarr.yml` without a page reload
  2. After selecting `configarr.yml`, the form renders quality profiles, custom formats, and scores per profile via the existing `FieldInput.svelte` dispatcher; `quality_definition` and `media_naming` fields appear read-only
  3. The operator can make a change to a quality profile score and save it; the diff preview shows only the changed field; the saved file round-trips correctly through the Phase 25 backend (no tag corruption)
**Plans**: TBD
**UI hint**: yes

### Phase 27: TRaSH CF picker + Recyclarr reference
**Goal**: Operators can add or remove TRaSH custom formats by human-readable name (no manual hex `trash_id` copying), and can reference Recyclarr template names as an informational guide without risk of inadvertent `include:` insertion
**Depends on**: Phase 26
**Requirements**: CFGUI-05, CFGUI-06
**Success Criteria** (what must be TRUE):
  1. The configarr form includes a searchable picker where the operator can type a CF name (e.g., "French MULTi") and select it; the corresponding `trash_id` hex value is inserted into `custom_formats[].trash_ids` in the saved YAML — no manual hex entry required
  2. The TRaSH catalog is served from a build-time-baked snapshot (committed static asset at a pinned commit SHA); no runtime HTTP call to GitHub is made from the FastAPI backend or the frontend
  3. A Recyclarr template reference dropdown is present and shows template names; clicking a template name shows its description only — no `include:` block is inserted into `configarr.yml` (CFGUI-06 scope boundary enforced in UI)
  4. An unknown `trash_id` already present in the live `configarr.yml` (e.g., a hand-rolled French CF) is displayed with a warning indicator rather than silently dropped or rejected
**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 24. Jellyfin Intro Skipper | 2/3 | In Progress|  |
| 25. configarr-in-UI backend | 0/? | Not started | - |
| 26. configarr-in-UI frontend | 0/? | Not started | - |
| 27. TRaSH CF picker + Recyclarr reference | 0/? | Not started | - |

**Milestone progress:** 0/4 phases complete

---

## Historical Progress

| Milestone | Phases | Plans | Status | Completed |
|-----------|--------|-------|--------|-----------|
| v0.2.0 forceSave fix | 11 | 65/66 | ✅ Shipped | 2026-05-17 |
| v0.3.0 Categories first-class | 3 | 16/16 | ✅ Shipped | 2026-05-22 |
| v0.4.0 Categories cleanup + content discovery + local config UI | 4 | 11/11 | ✅ Shipped | 2026-05-23 |
| v0.5.0 Jellyfin Categories-as-libs + CI/UX hardening | 3 | 3/3 | ✅ Shipped | 2026-05-24 |
| v0.6.0 arrconf observability — 4xx body logging | 1 | 1/1 | ✅ Shipped | 2026-05-25 |
| v0.8.0 Categories cleanup — v0.2.0 legacy migration close-out | 4 | 5/5 | ✅ Shipped | 2026-05-27 |

**Cluster HUMAN-UAT pending from v0.3.0** (operator-exercise opt-in, not blocking):
- Phase 9 initContainer NFS uid=1000 write test (09-HUMAN-UAT.md, 2 open scenarios)
- Phase 10 SC#1 cluster apply Categories-derived path (empty arrconf.yml flat sections to exercise) — REQ-categories-deprecation will exercise this naturally
- Phase 10 SC#3 TVDB-anime live routing test in Seerr UI
