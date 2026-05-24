# Requirements — Milestone v0.5.0

**Milestone:** v0.5.0 Jellyfin Categories-as-libs + CI/UX hardening
**Status:** Active (defining)
**Started:** 2026-05-24

## Goal

Refactor Jellyfin pour rendre les 10 Categories visibles nativement (clients Kodi/JellyCon sur LibreELEC salon + Swiftfin + web), restaurer la couverture CI sur `tools/arrconf-ui`, et fixer le fallback credentials côté qBit POST.

## v1 Requirements

### Jellyfin layout

- [ ] **REQ-jellyfin-categories-as-libs** — `tools/arrconf/arrconf/generators/categories.py::generate_jellyfin()` is refactored to emit **10 `VirtualFolder` entries**, one per `categories[].name`, each with a single `PathInfo` pointing at `/media/<name>`. The library `kind` (TV vs Movies) is derived from `categories[].kind`. The two super-libraries `Séries` and `Films` are no longer emitted. Migration is purely declarative: `helm upgrade` propagates the new layout, Jellyfin re-scans, and the 10 Categories appear as top-level libs in every Jellyfin client (web UI, Swiftfin, JellyCon, Jellyfin for Kodi). Pydantic models updated accordingly; JSON Schema regenerated; unit tests cover the new layout per Category combination. D-07-LIB-01 (`prune: false` hardcoded on jellyfin.libraries) is re-evaluated — either reversed entirely (let opt-in prune work like everywhere else), or adapted to "preserve user-added libs only" with a documented matching rule. Live cluster UAT: opening Jellyfin web UI shows 10 libs instead of 2 ; opening JellyCon on the salon LibreELEC mini-PC shows the same 10 libs as top-level browse buckets.

### CI hardening

- [ ] **REQ-arrconf-ui-ci** — `chart-lint.yml` + `tests.yml` path-filters extended to trigger on `tools/arrconf-ui/**`. The `tests.yml` workflow gains an `arrconf-ui` job: `cd tools/arrconf-ui && uv sync && uv run ruff format --check . && uv run ruff check . && uv run mypy .` for the Python backend, then `cd tools/arrconf-ui/web && npm ci && npm run check && npm run build` for the Svelte frontend. The job runs on PR + push to main. Auto-tag step in `chart-lint.yml` remains gated by chart/code paths (must NOT bump on arrconf-ui-only changes — UI changes don't ship with a chart bump). README updated with the new CI matrix.

### arrconf bugfix

- [ ] **REQ-qbit-post-credentials** — `tools/arrconf/arrconf/reconcilers/qbittorrent.py` (or the relevant `download_clients` POST/PUT codepath in Sonarr/Radarr/etc.) injects `QBT_USER` and `QBT_PASS` from environment variables when the `username` and `password` fields are empty (or omitted) in `arrconf.yml`. If both env vars are missing and YAML values are also empty, the reconciler raises a clear error message. Idempotent: explicit YAML values always win over env. Test coverage: 3 cases via respx — both empty + env set, both explicit, one empty + one explicit (partial).

## Future Requirements (deferred)

Carry-forward from v0.4.0 close-out, **not** scoped for v0.5.0 — re-evaluate at v0.6.0 milestone scoping:

- REQ-bazarr-addition — Bazarr (subtitles) as the 8th *arr-stack app
- REQ-arrconf-ui-distribution — package `arrconf-ui` for non-dev install
- REQ-config-ui-git-integration — auto-commit/push from `arrconf-ui`
- REQ-config-ui-multi-config — `configarr.yml` editing in the same UI
- REQ-suggestarr-ingress — SuggestArr ingress + auto-submit (currently port-forward + manual approval)
- D-07-PLAYLIST-MGMT-NULL — re-verify `EnablePlaylistManagement` on Jellyfin 11.x upgrade
- Phase 9 / Phase 10 HUMAN-UAT — deferred operator-exercise items from v0.3.0
- REQ-jellyfin-collections — only re-surface if `REQ-jellyfin-categories-as-libs` doesn't fully solve the Kodi visibility need

## Out of Scope (v0.5.0)

Explicit exclusions with reasoning to prevent re-adding mid-milestone:

- **Migration filesystem** — `/media/<name>` directories already exist since v0.3.0 Phase 9 ; refactor is purely declarative.
- **Multi-user Jellyfin** — single-tenant homelab, accounts are login-only, no permissions / no ACL. Reaffirmed.
- **Kodi-side code** — Kodi/JellyCon installation on the LibreELEC mini-PC is operator-driven (no arr-stack code). Documentation in README is OK, scripted install is NOT.
- **Bazarr** — explicitly deferred (no time to add an 8th app in this milestone).
- **arrconf-ui packaging** — runs from source via `uv run` is fine for a homelab. Packaging deferred.
- **REQ-jellyfin-collections** — only adds complexity if `REQ-jellyfin-categories-as-libs` ships clean. Skipped by design.

## Traceability

| Requirement | Phase(s) | Status |
|-------------|----------|--------|
| REQ-jellyfin-categories-as-libs | Phase 16 | Active |
| REQ-arrconf-ui-ci | Phase 17 | Active |
| REQ-qbit-post-credentials | Phase 18 | Active |
