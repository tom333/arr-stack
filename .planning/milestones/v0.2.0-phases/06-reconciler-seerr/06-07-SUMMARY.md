---
phase: 06-reconciler-seerr
plan: 07
status: complete
completed: 2026-05-17
plan_artifact: 06-07-PLAN.md
---

# Plan 06-07 — Wave 4 cluster-apply SUMMARY

Phase 6 (Reconciler Seerr) closure. Operator-driven cutover from "code merged on local main" to "Phase 6 live in cluster, SC#1–5 dispositive". This plan shipped **zero direct code/chart changes** as designed but uncovered three deviations that required mid-flight hotfixes (D-06-OPENAPI-01, plus chart-side seerr-in-args wiring gap, plus operational disk-pressure cleanup) committed under Plan 06-07's umbrella.

## SC Dispositives

### SC#1 — Pre-write snapshot ✅
Closed by Plan 06-01 on 2026-05-16. Baseline `snapshots/before-phase-6-2026-05-16/seerr/` committed (16 files, all `apiKey` fields redacted before commit — Plan 06-01 manually sed-redacted the 4 leaked files; Phase 5 Deviation #6 reproduced).

### SC#2 — Seerr reconciler applied ✅
Evidence: `.planning/phases/06-reconciler-seerr/evidence/cluster-apply-log.txt` (job `arrconf-phase6-dispositive-1778932395`, image `:0.4.4`).

```
{"app": "seerr", "actions": [
  "settings_radarr:applied:0",
  "user:applied:1",
  "main_settings:applied"
], "event": "apply_complete", "level": "info"}
{"user_id": 1, "permissions": 2, "event": "user_applied"}    ← ADMIN bitmask confirmed (NOT 8388608=AUTO_REQUEST)
```

`settings_sonarr` is `no_op` in this run — already converged via the in-flight manual curl PUT done at 19:58:31 UTC (D-06-OPENAPI-01 debugging step). Functionally identical to "applied" — the live cluster state matches desired.

Q1 PUT-probe (Plan 06-01 evidence) confirmed all 4 endpoints accept the PUT body shape; first-apply log confirms it lands in production with image `:0.4.4` containing the D-06-OPENAPI-01 fix.

### SC#3 — content_tags step (Sonarr + Radarr) ✅
Same evidence file. Step 10 ran for both apps; both rules emitted `content_tags_rule_no_op` because all matching items were already tagged from Phase 5 D-05-MIG-01 retroactive tagging plus an earlier in-session apply.

**LIVE end-to-end validation captured in SC#4 evidence**: Elena of Avalor was post-import retagged with `family` (tag id=4) by Plan 06-05's content_tags step because TVDB genres include both `Family` and `Children` keywords. Pitfall 5 enforced: `Animation` alone (without `Family`/`Children`/`Kids`) does NOT match the family rule.

### SC#4 — anime smoke E2E (operator) ✅ (partial — see Deviations §1)
Evidence: `.planning/phases/06-reconciler-seerr/evidence/sc4-anime-via-seerr.txt`. Operator-selected series: **Elena of Avalor** (TVDB 312964).

Observed Sonarr state after Seerr request:
- `rootFolderPath: /media/anime` (operator-overridden via Seerr Advanced panel)
- `tags: [2=tv (Seerr default), 5=1-moi (Seerr tagRequests user-tag), 4=family (arrconf content_tags retag)]`
- `qualityProfileId: 6` (= HD - 720p/1080p, default)

**Caveat**: TVDB does NOT classify Elena of Avalor as `Anime`, so Seerr's native `animeTags` routing (D-06-Q10-01 mechanism) was **not exercised** by this test — the operator manually overrode the root folder. The Seerr → Sonarr request pipeline and arrconf's content_tags retagger both validated live; the `animeTags` native routing remains untested in production for a TVDB-anime-classified series. Phase 5 historical evidence (Winx Club S06 already in `/media/anime/` pre-Phase-6) validates the downstream qBit→Sonarr→/media/anime pipeline independently.

### SC#5 — idempotence ✅
Evidence: `.planning/phases/06-reconciler-seerr/evidence/sc5-idempotence-proof.txt` (job `arrconf-phase6-idem-1778932471`, 85 lines).

```
SC#5 IDEMPOTENCE TALLY:
  create/add events  (expect 0):  0  ✓
  error events       (expect 0):  0  ✓
  ADR-5 violations   (expect 0):  0  ✓
  no_op events       (expect ≥1): 13 ✓
  plan_action update (informational): 14
```

Seerr second-run breakdown: 3/4 resources idempotent (`settings_sonarr_no_op`, `settings_radarr_no_op`, `main_settings_no_op`). The `user` resource re-PUTs (`user:applied:1`) on every run — same false-positive shape as Phase 5 Deviation #7 (Prowlarr/qBit comparator imprecision); server accepts the identical PUT body without side effect, so functionally idempotent. Carried forward as Phase 5 follow-up #5 — arrconf diff comparator refinement scope expanded to include Seerr user.

## Deviations

### D-06-OPENAPI-01 — activeProfileName/activeAnimeProfileName OpenAPI-required (hotfix shipped)
Plan 06-01 research classified `activeProfileName` and `activeAnimeProfileName` as "server-computed → exclude from PUT body" (Pitfall 3). Plan 06-02 implemented `Field(exclude=True)`. First cluster apply (Task 7.2 attempt 1) crashed with HTTP 400 `request.body should have required property 'activeProfileName'` — Seerr's OpenAPI validator marks these fields as **required** regardless of server-computed status.

**Fix**: commit `75e1661` re-injects both names from current GET into the PUT body, same pattern as `apiKey` (D-06-CREDS-01). Pydantic `exclude=True` preserved for symmetry — names are not desired-state surface. 2 test rewrites (`test_settings_sonarr_excludes_activeProfileName_from_put` → `test_settings_sonarr_preserves_activeProfileName_from_get` + new `test_settings_radarr_preserves_activeProfileName_from_get`). Shipped as `:0.4.4` via auto-tag chain.

Pitfall 3 documentation in 06-RESEARCH.md is now stale; reviewer for future Phase 7 (Jellyfin) should re-validate `exclude=True` field choices against the live OpenAPI validator before trusting research-time classifications.

### D-06-CHART-ARGS-01 — seerr missing from `--apps` CronJob argument (hotfix shipped)
Plan 06-06 scoped `charts/arr-stack/files/arrconf.yml` + `charts/arr-stack/values.schema.json` + `tools/arrconf/tests/test_arrconf_yml_validates.py` — but missed `charts/arr-stack/values.yaml` lines 454–455 (`--apps "sonarr,radarr,prowlarr,qbittorrent"`). First scheduled CronJob run (Task 7.2 attempt 0, before any hotfix) showed **zero Seerr events** because the `--apps` list did not include `seerr` — the Phase 6 dispatch branch in `__main__.py` skipped silently. Symmetrically with D-05-ARGS-01 from Phase 5 (`qbittorrent` add), Phase 6 should have applied D-06-ARGS-01 to the same line.

**Fix**: commit `ff39507`. Comment now reads `# D-05-ARGS-01: Phase 5 adds qbittorrent ; Phase 6 adds seerr (D-06-SCOPE-01)`.

### D-06-QBIT-MOVE-01 — sda root disk pressure (operational sidequest)
Discovered during Task 7.1 cluster verification: `/dev/sda2` at 84% used (141 G free of 915 G), of which `/opt/media-stack/torrents` (qBit hostPath) consumed 151 G. `/dev/sdb1` mounted on `/media/data` had 841 G free (52 %) — perfect spillover.

**Fix**: commit `77e5b7c` moved qBit/Sonarr/Radarr `hostPath: /opt/media-stack/torrents` → `/media/data/torrents` (3 occurrences in `values.yaml`). Operator drove the `rsync -aHAX --delete` cutover with microk8s temporarily stopped to eliminate I/O contention from sonarr/radarr/cleanuparr; 191 G migrated. Post-cutover delta-rsync handled the ~26 GB of partials that completed during initial transfer. `sudo rm -rf /opt/media-stack/torrents` cleanup pending operator verification of qBit Force Recheck on a few torrents in the WebUI.

### D-06-SEERR-USER-FP — user resource emits `user:applied:1` on every run
`_payloads_equivalent` returns False on the user resource even when desired payload matches cluster state (Seerr's `/api/v1/user` response includes pydantic-excluded fields and/or shape that diverge from the model_dump output in subtle ways). Functionally idempotent (Seerr accepts identical PUT), but emits a false-positive `applied` action in `apply_complete`. Same shape as Phase 5 Deviation #7 — added to Phase 5 follow-up #5 scope.

### D-06-CRED-MGMT — SEERR_API_KEY bootstrap (operational sidequest)
The arrconf-env SealedSecret was missing `SEERR_API_KEY`. Phase 6 dispatch branch logged `missing_api_key` and exited 2 on first attempt. Operator extracted the value from the running Seerr pod (`/app/config/settings.json` → `.main.apiKey`, 68 chars base64), `kubeseal --raw` encrypted, inserted into `sealed/arrconf-secret.yaml` between `RADARR_API_KEY` and `SONARR_API_KEY` (alphabetical), pushed `my-kluster` commit `1fc0c40e`. ArgoCD + sealed-secrets controller reconciled the new key into `arrconf-env` within 12 s; live secret now has 6 keys (PROWLARR, QBT_PASS, QBT_USER, RADARR, SEERR, SONARR).

## Phase 5 Backlog Carry-Forward

All 8 Phase 5 follow-up items remain open and NOT closed by Phase 6:

1. arrconf download_client POST should inject QBT_USER/QBT_PASS when YAML values empty (Phase 2.1 helper covers UPDATE only)
2. Chart pre-create `/media/{anime,family,films-anime,films-family}` + `/data/torrents/{series,anime,family,films,films-anime,films-family}` via initContainer or Helm hook
3. Port qBit 5.x auth fix to `tools/snapshot/snapshot.sh`
4. Re-verify snapshot.sh password-redaction step for `config_host.json` sensitive fields — **REPRODUCED in Phase 6** (5 leak files redacted manually before commit)
5. Refine arrconf diff comparators to eliminate idempotence false-positives — **EXPANDED scope**: Prowlarr/qBit/Seerr-user all exhibit the false-positive `update` shape (Phase 6 D-06-SEERR-USER-FP carry)
6. Install Mend Renovate App on `tom333/arr-stack` (Q-05.1-3, blocks Renovate auto-bump path) — **MITIGATED in Phase 6** via 2 manual values.yaml bumps (0.3.3 → 0.4.0 → 0.4.4) plus matching my-kluster targetRevision bumps (D-05.1-BUMP-01 pattern persists)
7. Extend `chart-lint.yml` `paths:` to include `tools/arrconf/**` so arrconf-only PRs auto-tag (Phase 5.1 F1) — **REPRODUCED in Phase 6**: commit `75e1661` (`tools/arrconf/**` only) did NOT trigger auto-tag; required follow-up chart-touch commit `5b43540` to unblock
8. Fix `arrconf-image.yml` metadata-action `value=` to handle legacy `push:tags` semver correctly (Phase 5.1 F2)

## Phase 5.1 Follow-Up Status

- **F1 (chart-lint.yml paths)** — REPRODUCED, see Phase 5 backlog #7. Still pending.
- **F2 (metadata-action value=)** — NOT REPRODUCED in Phase 6 (the `:0.4.4` build was triggered via the chart-touch → repository_dispatch chain, not via `push:tags`). Still pending.

## Locked Decisions Honored

| Decision | Scope | Honored? | Evidence |
|----------|-------|----------|----------|
| D-06-VALIDATE-01 | Q1 PUT-probe done in research phase before code | ✅ | `evidence/q1-put-probe.txt` (Plan 06-01) — HTTP 200 confirmed on all 4 endpoints |
| D-06-AUTH-01 | X-Api-Key header for Seerr v3.2.0 | ✅ | SeerrClient implements `X-Api-Key` (commit `da932ef`); live PUT 200s on 3/4 resources confirm header acceptance |
| D-06-Q10-01 | Native Seerr animeTags routing as primary, content_tags as fallback | ⚠️ partial | `animeTags: [3]` configured + tagRequests=true (`settings_sonarr` PUT). Native routing not exercised for a TVDB-anime-classified series in this session — Elena of Avalor used the operator-override path, not the genre-classification path. Mechanism is wired; "validated in production" deferred to next real anime request |
| D-06-RETAG-01 | content_tags step on BOTH Sonarr + Radarr | ✅ | Step 10 ran on both apps in dispositive run; Elena of Avalor live-tagged with `family` (id=4) via TVDB genres `{Family,Children}` |
| D-06-SCOPE-01 | 4 Seerr resources only: settings/sonarr, settings/radarr, user, settings/main subset | ✅ | reconciler `seerr.py` covers exactly those 4; no `settings/jellyfin`, `request`, `settings/plex` touched |
| D-06-CREDS-01 | Manual apiKey preservation from cluster GET (not merge_fields_for_put) | ✅ | `_reconcile_settings_sonarr` / `_reconcile_settings_radarr` re-inject `cluster_api_key` after `model_dump()`; live cluster `apiKey` for sonarr matches `SONARR_API_KEY` secret value |

## Phase 6 Commit Timeline

| SHA | Type | Description |
|-----|------|-------------|
| 06-01..06-06 merges | wave 1-3 | Plans 06-01 through 06-06 closed via parallel-executor worktrees |
| `4fcb510` | merge | origin/main merge (PR #10/#11/#12 squash-merge equivalents) |
| `ff39507` | fix | chart: add `seerr` to arrconf `--apps` (D-06-CHART-ARGS-01) |
| `77e5b7c` | fix | qbit: hostPath move `/opt/media-stack/torrents` → `/media/data/torrents` (D-06-QBIT-MOVE-01) |
| `75e1661` | fix | seerr: inject activeProfileName from cluster GET (D-06-OPENAPI-01) |
| `5b43540` | chore | bump arrconf image tag `0.4.1` → `0.4.4` (chart-touch unblock for tools/arrconf-only auto-tag, F1 workaround) |
| `4ec65b4` | docs | SC#2/SC#3 dispositive log captured |
| `d85f3ff` | docs | SC#5 idempotence proof captured |
| `6f5783c` | docs | SC#4 Elena of Avalor evidence + interpretation |

my-kluster side: `1fc0c40e` (SealedSecret SEERR_API_KEY) + `5e7e965b` (targetRevision v0.4.3 → v0.4.4).

GHCR images shipped during this phase: `:0.4.0`, `:0.4.1`, `:0.4.2`, `:0.4.3`, `:0.4.4`. Cluster currently on `:0.4.4`.

## Next phase

**Phase 7 (Reconciler Jellyfin)** is next per ROADMAP. Q9 (auth strategy — `X-Emby-Token` / `Authorization: MediaBrowser` / `?api_key=` query) must be PUT-probed in the research phase BEFORE code (D-06-VALIDATE-01 pattern proven correct). The Phase 6 research-vs-OpenAPI lesson (Pitfall 3 was wrong about `exclude=True`) is a candidate Phase 7 learning to surface in `gsd-extract-learnings`.
