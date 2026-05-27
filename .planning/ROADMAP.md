# Roadmap: arr-stack

## Milestones

- ✅ **v0.2.0 forceSave fix** — Phases 0-7 (shipped 2026-05-17)
- ✅ **v0.3.0 Categories first-class** — Phases 9-11 (shipped 2026-05-22)
- ✅ **v0.4.0 Categories cleanup + content discovery + local config UI** — Phases 12-15 (shipped 2026-05-23)
- ✅ **v0.5.0 Jellyfin Categories-as-libs + CI/UX hardening** — Phases 16-18 (shipped 2026-05-24)
- ✅ **v0.6.0 arrconf observability — 4xx body logging** — Phase 19 (shipped 2026-05-25 via /gsd-quick 260525-bj5)
- 🚧 **v0.8.0 Categories cleanup — v0.2.0 legacy migration close-out** — Phases 20-23 (in progress, started 2026-05-25)

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

Highlights: Jellyfin emits 10 `VirtualFolder` libs (1 per Category) — reverses D-07-LIB-01, makes Categories visible in JellyCon/Kodi on LibreELEC salon ; `tools/arrconf-ui/**` covered by CI (`arrconf-ui-backend` triad + `arrconf-ui-frontend` quad) without triggering chart-lint auto-tag (architectural isolation SC#3 dispositive) ; qBit POST credentials env-injected for Sonarr+Radarr with pre-flight gate in `__main__.py` and fail-fast ConfigError ; UAT dispositive 9/9 + 9/9 qBit DCs HTTP 200 + 0 plan_actions on 2nd run ; side-quest unblock of pre-existing Sonarr RPM 400 (PathExistsValidator, pre-dated Phase 18 by ≥3 image versions) via `/gsd-debug` session.

Full archived details: [`milestones/v0.5.0-ROADMAP.md`](milestones/v0.5.0-ROADMAP.md)

</details>

<details>
<summary>✅ v0.6.0 arrconf observability — 4xx body logging (Phase 19) — SHIPPED 2026-05-25</summary>

- [x] Phase 19: arrconf observability — 4xx body logging (shipped via /gsd-quick 260525-bj5, single atomic commit 9726d81) — 2026-05-25

Total: **1 phase, 1 deliverable, 5 commits including release-chain rescue**.

Highlights: `client_4xx` structlog warning emitted in `ArrApiClient._request` between the 4xx fast-path (404/401) and the 5xx ServerError block; payload includes client/method/path/status_code/body_excerpt=response.text[:500]; 5 new respx tests (416 pass total, up from 411) cover 400 verbatim, 422 truncation, 401/404 short-circuit, 500 ServerError no-cross-fire. Chart pin co-bump 0.12.1 → 0.14.0 (initial 0.13.0 then rescue alignment with v0.14.0 auto-tag minor bump from `feat:`). Phase 19 was small enough to ship via /gsd-quick rather than full discuss/plan/execute cycle — pattern documented as a valid path for micro-milestones.

Quick task artifact: [`.planning/quick/260525-bj5-client-base-py-add-4xx-response-text-500/`](quick/260525-bj5-client-base-py-add-4xx-response-text-500/)

</details>

### 🚧 v0.8.0 Categories cleanup — v0.2.0 legacy migration close-out (in progress)

- [x] Phase 20: Categories cleanup audit — legacy items/tags/paths inventory (0/1 plans) (completed 2026-05-26)
- [x] Phase 21: Filesystem + metadata migration — `mv` + Radarr/Sonarr API mutation + Jellyfin re-scan (1/1 plans) (completed 2026-05-27)
- [x] Phase 22: arrconf prune reconciler — prune legacy root_folders/tags + DC catch-all decision (0/2 plans planned) (completed 2026-05-27)
- [ ] Phase 23: UAT dispositive — end-to-end Seerr-to-disk verification + chart bump 0.14.x → 0.15.0 (0/1 plans)

## Phase Details

### Phase 20: Categories cleanup audit
**Goal**: Produce an exhaustive inventory of v0.2.0 legacy state across Radarr / Sonarr / qBittorrent so Phase 21 has a deterministic migration plan with no ambiguous per-item decisions left to runtime.
**Depends on**: Nothing (read-only baseline)
**Requirements**: CAT-CLEANUP-01
**Success Criteria** (what must be TRUE):
  1. `.planning/phases/20-categories-cleanup-audit/20-AUDIT.md` exists and lists every Radarr movie + Sonarr series whose `rootFolderPath` is a legacy v0.2.0 path, with target Category path resolved per item (auto-mapped or operator-decided).
  2. Audit captures every qBit torrent whose `save_path` starts with a legacy `/data/torrents/<legacy>/` segment, with target Category save_path resolved.
  3. Audit enumerates every Radarr/Sonarr tag that is legacy (`movies`, `family`, `films`, `anime`) vs Category (`films-enfants`, `series-zoe`, etc.) with the proposed prune/rename action per tag.
  4. `legacy_path → Category` and `legacy_tag → Category_tag` mapping tables are committed and validated against the CLAUDE.md "Filesystem migration v0.2.0 → v0.3.0" reference table.
**Plans**: 1 plan (~half-day)

Plans:
- [x] 20-01-PLAN.md — Audit module + Typer commands + tests + chart bump + operator-edit + verify gate (holistic single plan per CONTEXT.md)

### Phase 21: Filesystem + metadata migration
**Goal**: Move every item identified in Phase 20 audit to its Category target — filesystem `mv` on the Jellyfin NFS volume + qBit `setLocation` for in-flight torrents + Radarr/Sonarr API mutations + post-migration re-scans — leaving the cluster functional throughout.
**Depends on**: Phase 20 (consumes `20-AUDIT.md`)
**Requirements**: CAT-CLEANUP-02
**Success Criteria** (what must be TRUE):
  1. ADR-6 snapshots exist for both pre-migration AND post-migration states under `snapshots/before-categories-cleanup-*` and `snapshots/after-categories-cleanup-*`, both committed; `diff` confirms only the expected `rootFolderPath` / `path` / `tags` / `save_path` mutations.
  2. Radarr `/api/v3/movie` returns every previously-legacy movie with its new Category `rootFolderPath` + `path` + Category tag, file present on disk at the new path, no `monitored: false` regression vs pre-migration.
  3. Sonarr `/api/v3/series` idem: every legacy series now anchored on its Category root folder, series tag updated, episode files re-detected after `RefreshSeries`.
  4. qBit `/api/v2/torrents/info` shows every previously-legacy in-flight torrent with the Category `save_path` + Category as its `category` field, and the torrent remains in its prior state (downloading/seeding) without re-hashing failure.
  5. Jellyfin `/Library/Refresh` completes, all 10 Category libs still report `ItemCount > 0`, no lib went empty post-migration.
**Plans**: 1 plan (~1 day operator-time, step-by-step kubectl exec)

Plans:
- [x] 21-01-PLAN.md — One-shot script tools/scripts/migrate-categories.py + 21-RUNBOOK.md + ADR-6 pre+post snapshots + operator live run (holistic single plan per D-21-PLAN-01)

### Phase 22: arrconf prune reconciler — lock the cleanup in
**Goal**: Extend arrconf so the legacy v0.2.0 paths/tags cannot drift back: pydantic validation refuses non-Category `rootFolderPath`, reconcilers prune legacy root_folders + tags filtered to Categories, and the qBit DC catch-all decision (full prune OR low-priority `unsorted` fallback) is implemented + tested. Ship via chart-pin co-bump 0.14.x → 0.15.0.
**Depends on**: Phase 21 (cluster already in Category-only state; pruning is safe)
**Requirements**: CAT-CLEANUP-03
**Success Criteria** (what must be TRUE):
  1. Triade Python green on `tools/arrconf/`: `uv run ruff format --check . && uv run ruff check . && uv run mypy . && uv run pytest -q` exits 0; new respx tests cover every new prune step + the pydantic legacy-path refusal.
  2. `arrconf apply --dry-run` on the post-Phase-21 cluster shows 0 plan_action on root_folders/tags/download_clients for Sonarr+Radarr — i.e. cluster is already aligned with the new generators (no regression from the prune step).
  3. `arrconf apply --dry-run` on a synthetic config containing a legacy `rootFolderPath` (e.g. `/media/films-family`) exits code 2 with a `ConfigError` / pydantic `ValidationError` naming the offending path — fail-fast gate works.
  4. DC catch-all `qBittorrent` (id=1) decision is implemented end-to-end: either pruned from generators output (with respx test asserting absence) OR re-tagged as `unsorted` with priority demoted (with respx test asserting tag+priority), per `/gsd-discuss-phase 22` choice; decision documented in phase ADR.
  5. Same commit that lands the Python code bumps `charts/arr-stack/values.yaml#arrconf.image.tag` from `0.14.x` to `0.15.0` per CLAUDE.md "Release pin co-bump pattern"; Renovate annotation preserved verbatim.
**Plans**: 2 plans (code + chart co-bump; live operator cleanup — ~1 day total)

Plans:
**Wave 1**
- [x] 22-01-PLAN.md — Prune reconciler (differ.force_prune + Sonarr/Radarr wiring) + pydantic legacy-path guard + respx/unit tests + chart co-bump 0.14.1 -> 0.15.0 (autonomous)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 22-02-PLAN.md — Live operator cleanup runbook (3 orphan torrents + 10 missing records) + SC#2 dry-run gate + plan-split/DC ADR (wave 2, human-action)

### Phase 23: UAT dispositive — end-to-end verification
**Goal**: Prove the cleanup holds end-to-end in the live cluster: legacy paths absent from API responses, a fresh Seerr request routes through the Category DC (not the catch-all), and a second `arrconf apply` is fully idempotent.
**Depends on**: Phase 22 (cluster running arrconf `:0.15.0` with prune steps active)
**Requirements**: CAT-CLEANUP-04
**Success Criteria** (what must be TRUE):
  1. SC#1 — `curl http://radarr.selfhost.svc.cluster.local:7878/api/v3/rootfolder` returns Category paths only (including the valid default `/media/films`); the 2 legacy paths `/media/films-anime`, `/media/films-family` are absent from the response body. (`/media/films` is a valid default Category, NOT legacy.)
  2. SC#2 — Sonarr `/api/v3/rootfolder` idem: Category paths only (including the valid default `/media/series`); the 2 legacy paths `/media/anime`, `/media/family` are absent. (`/media/series` is a valid default Category, NOT legacy.)
  3. SC#3 — A new Seerr request for a kids' film lands on disk at `/media/films-enfants/<title>/`, qBit shows `category=films-enfants` + `save_path=/data/torrents/films-enfants/`, and the qBit "Added by" / download-client trace identifies `qBittorrent - Films - Enfants` as the accepting DC (NOT the catch-all `qBittorrent` id=1).
  4. SC#4 — `arrconf apply` (not dry-run) on the post-cleanup cluster emits 0 plan_action across root_folders / tags / download_clients for sonarr + radarr; second back-to-back run idem (idempotence preserved).
  5. SC#5 — Jellyfin web UI shows all 10 Category libs each with `ItemCount > 0`; no empty lib introduced by the migration.
**Plans**: 1 plan (~half-day, runbook execution + result tracking in `23-HUMAN-UAT.md`)

## Progress

| Milestone | Phases | Plans | Status | Completed |
|-----------|--------|-------|--------|-----------|
| v0.2.0 forceSave fix | 11 | 65/66 | ✅ Shipped | 2026-05-17 |
| v0.3.0 Categories first-class | 3 | 16/16 | ✅ Shipped | 2026-05-22 |
| v0.4.0 Categories cleanup + content discovery + local config UI | 4 | 11/11 | ✅ Shipped | 2026-05-23 |
| v0.5.0 Jellyfin Categories-as-libs + CI/UX hardening | 3 | 3/3 | ✅ Shipped | 2026-05-24 |
| v0.6.0 arrconf observability — 4xx body logging | 1 | 1/1 | ✅ Shipped | 2026-05-25 |
| v0.8.0 Categories cleanup — v0.2.0 legacy migration close-out | 4 | 0/5 | 🚧 In progress | — |

**Cluster HUMAN-UAT pending from v0.3.0** (operator-exercise opt-in, not blocking):
- Phase 9 initContainer NFS uid=1000 write test (09-HUMAN-UAT.md, 2 open scenarios)
- Phase 10 SC#1 cluster apply Categories-derived path (empty arrconf.yml flat sections to exercise) — REQ-categories-deprecation will exercise this naturally
- Phase 10 SC#3 TVDB-anime live routing test in Seerr UI

**v0.9.0+ carry-forward backlog** (REQ-bazarr-addition removed in v0.7.0 — declared out of scope, see PROJECT.md):
- REQ-arrconf-ui-distribution — package `arrconf-ui` for non-dev install
- REQ-config-ui-git-integration — auto-commit/push from UI (after v0.5.0 ships and operator decides)
- REQ-config-ui-multi-config — configarr.yml editing in same UI (ADR-5 frontière check)
- REQ-suggestarr-ingress — SuggestArr ingress + auto-submit (currently port-forward + manual approval)
- REQ-arrconf-dry-run-pr-gate — GHA job running `arrconf apply --dry-run` on PRs
- REQ-jellyfin-native-subtitles — activate Open Subtitles plugin Jellyfin
- REQ-jellyfin-skip-intro — chapter markers + skip intro
- REQ-radarr-sonarr-lists — TMDb/Trakt list auto-import
- REQ-radarr-sonarr-release-profiles — preferred/required/ignored keywords per tag
- D-07-PLAYLIST-MGMT-NULL: re-verify `EnablePlaylistManagement` on Jellyfin 11.x upgrade
- Phase 9 / Phase 10 HUMAN-UAT carry-forward from v0.3.0
