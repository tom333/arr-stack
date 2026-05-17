# Roadmap: arr-stack

## Milestones

- ✅ **v0.2.0 forceSave fix** — Phases 0-7 (shipped 2026-05-17)
- 📋 **v0.3.0** — TBD (planned — run `/gsd-new-milestone` to scope)

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

### 📋 v0.3.0 (planned)

No phases scoped yet. Run `/gsd-new-milestone` to start the next cycle.

**Carry-forward backlog from v0.2.0** (16 deferred items — see `STATE.md` Deferred Items section for full context):

- [ ] Re-enable ArgoCD `automated.selfHeal` + `automated.prune` (Phase 4 plan 04-09 follow-up)
- [ ] Migration ESO/Akeyless (was Phase 8 in v0.2.0 — optional, depends on my-kluster ESO chantier)
- [ ] arrconf download_client POST: inject QBT_USER/QBT_PASS when YAML values empty (Phase 5 #1)
- [ ] Chart pre-create `/media/{anime,family,films-anime,films-family}` + torrent dirs via initContainer or Helm hook (Phase 5 #2)
- [ ] Port qBit 5.x auth fix (arrconf PR #11) to `tools/snapshot/snapshot.sh` (Phase 5 #3)
- [ ] Re-verify snapshot.sh password-redaction for `config_host.json` (Phase 5 #4 — reproduced Phase 6)
- [ ] Refine arrconf diff comparators to eliminate idempotence false-positives (Phase 5 #5 — expanded Phase 6)
- [ ] Install Mend Renovate App on `tom333/arr-stack` (Phase 5.1 #6 — blocks Renovate auto-bump path)
- [ ] Extend `chart-lint.yml` `paths:` to include `tools/arrconf/**` (Phase 5.1 #7)
- [ ] Fix `arrconf-image.yml` metadata-action `value=` for legacy `push:tags` semver (Phase 5.1 #8)
- [ ] D-06-Q10-01: native `animeTags` routing untested for TVDB-anime series (Phase 6 #10)
- [ ] `sudo rm -rf /opt/media-stack/torrents` cleanup (Phase 6 #11 — operator-deferred)
- [ ] D-07-CHART-PIN-LOOP: pre-bump `arrconf.image.tag` in same commit as reconciler code (Phase 7 CF-07-1)
- [ ] D-07-RUFF-FORMAT-CI: add `ruff format --check` to gsd-executor prompt + CLAUDE.md (Phase 7 CF-07-2)
- [ ] D-07-CRONJOB-CRUFT: `kubectl -n selfhost delete cm arrconf configarr` (Phase 7 CF-07-3 — Phase 4 leftover)
- [ ] D-07-PLAYLIST-MGMT-NULL: re-verify EnablePlaylistManagement on Jellyfin 11.x (Phase 7 CF-07-4)

## Progress

| Milestone | Phases | Plans | Status | Completed |
|-----------|--------|-------|--------|-----------|
| v0.2.0 forceSave fix | 11 | 65/66 | ✅ Shipped | 2026-05-17 |
| v0.3.0 | TBD | — | 📋 Planned | — |
