# Roadmap: arr-stack

## Milestones

- ✅ **v0.2.0 forceSave fix** — Phases 0-7 (shipped 2026-05-17)
- ✅ **v0.3.0 Categories first-class** — Phases 9-11 (shipped 2026-05-22)
- ✅ **v0.4.0 Categories cleanup + content discovery + local config UI** — Phases 12-15 (shipped 2026-05-23)
- ✅ **v0.5.0 Jellyfin Categories-as-libs + CI/UX hardening** — Phases 16-18 (shipped 2026-05-24)
- 🚧 **v0.6.0 arrconf observability — 4xx body logging** — Phase 19 (in progress, started 2026-05-24)

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

### 🚧 v0.6.0 arrconf observability — 4xx body logging (in progress)

- [ ] **Phase 19: arrconf observability — 4xx body logging** — `client_base.py:79-81` logs `response.text[:500]` for 4xx responses symmetric with existing 5xx logging; respx test asserts body excerpt presence

## Phase Details

### Phase 19: arrconf observability — 4xx body logging
**Goal**: Close the v0.5.0 observability gap by surfacing 4xx response bodies in `arrconf` logs. Today `_request` in `tools/arrconf/arrconf/client_base.py` logs `response.text[:200]` for 5xx (line 80) but raises raw `HTTPStatusError` for 4xx — the server's actual error message is invisible, which is why Sonarr's `PathExistsValidator` 400 went unsurfaced for 3 image versions. Add symmetric 4xx body logging so future API regressions are debuggable on first occurrence.
**Depends on**: v0.5.0 (Phase 18) — landed `:0.12.1` baseline that this fix co-bumps from
**Requirements**: OBS-01
**Success Criteria** (what must be TRUE):
  1. On any 4xx HTTP response inside `_request`, a structured log event (e.g. `client_4xx`) is emitted containing the client name, HTTP method, request path, status code, and `response.text[:500]` excerpt — verified by a new respx test that asserts the body excerpt appears verbatim in the captured log output.
  2. Triade Python green locally and in CI: `cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy arrconf && uv run pytest -q` exits 0 on the commit that ships the fix (CI `tests.yml` gates pass on push).
  3. Chart-pin co-bump applied in the same commit per CLAUDE.md "Release pin co-bump pattern": `charts/arr-stack/values.yaml#arrconf.image.tag` advances from `0.12.1` to `0.13.0` (minor bump — this is a `feat` adding observability surface) with the Renovate annotation `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` preserved verbatim above `repository:`.
**Plans**: TBD (1 plan expected in Wave 1 — Phase 19-A)

## Progress

| Milestone | Phases | Plans | Status | Completed |
|-----------|--------|-------|--------|-----------|
| v0.2.0 forceSave fix | 11 | 65/66 | ✅ Shipped | 2026-05-17 |
| v0.3.0 Categories first-class | 3 | 16/16 | ✅ Shipped | 2026-05-22 |
| v0.4.0 Categories cleanup + content discovery + local config UI | 4 | 11/11 | ✅ Shipped | 2026-05-23 |
| v0.5.0 Jellyfin Categories-as-libs + CI/UX hardening | 3 | 3/3 | ✅ Shipped | 2026-05-24 |
| v0.6.0 arrconf observability — 4xx body logging | 1 | 0/1 | 🚧 In progress | — |

**Cluster HUMAN-UAT pending from v0.3.0** (operator-exercise opt-in, not blocking):
- Phase 9 initContainer NFS uid=1000 write test (09-HUMAN-UAT.md, 2 open scenarios)
- Phase 10 SC#1 cluster apply Categories-derived path (empty arrconf.yml flat sections to exercise) — REQ-categories-deprecation will exercise this naturally
- Phase 10 SC#3 TVDB-anime live routing test in Seerr UI

**v0.7.0+ carry-forward backlog**:
- REQ-bazarr-addition — Bazarr (subtitles) as an 8th *arr-stack app
- REQ-arrconf-ui-distribution — package `arrconf-ui` for non-dev install
- REQ-config-ui-git-integration — auto-commit/push from UI (after v0.5.0 ships and operator decides)
- REQ-config-ui-multi-config — configarr.yml editing in same UI (ADR-5 frontière check)
- REQ-suggestarr-ingress — SuggestArr ingress + auto-submit (currently port-forward + manual approval)
- REQ-jellyfin-collections — only re-surface if Phase 16 doesn't fully solve Kodi visibility
- D-07-PLAYLIST-MGMT-NULL: re-verify `EnablePlaylistManagement` on Jellyfin 11.x upgrade
- Phase 9 / Phase 10 HUMAN-UAT carry-forward from v0.3.0
