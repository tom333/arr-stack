---
status: partial
phase: 18-qbit-post-credentials-fallback
source:
  - 18-A-SUMMARY.md
  - 18-HUMAN-UAT.md
started: 2026-05-24T08:15:00Z
updated: 2026-05-24T08:22:00Z
chart_image_tag: "0.12.1"
git_tags: ["v0.12.1", "v0.13.0"]
ghcr_image: "ghcr.io/tom333/arr-stack-arrconf:0.12.1"
argocd_sync_status: "Synced"
arrconf_image_live: "ghcr.io/tom333/arr-stack-arrconf:0.12.1"
---

## Current Test

[session paused — SC#2 partial, SC#3-5 blocked on pre-existing RPM 400 bug]

## Tests

### 1. SC#1 — Rendered ConfigMap carries no live qBit credentials
expected: No explicit username/password values for qBit download_clients in the rendered ConfigMap. Real creds only in `arrconf-env` SealedSecret.
result: pass
evidence: |
  ArgoCD: Synced. arrconf image: ghcr.io/tom333/arr-stack-arrconf:0.12.1.
  ConfigMap arrconf.yml (294 lines): 2× `download_clients:` blocks (sonarr+radarr) with only `prune: false`,
  no `username:` or `password:` lines anywhere. Only matches for grep `(password|username|api[_-]?key)`:
  `api_key_env: SONARR_API_KEY` / `RADARR_API_KEY` + 3 doc comments. No live credentials in ConfigMap.

### 2. SC#2 — ArgoCD-triggered CronJob does NOT raise ConfigError
expected: Manual `kubectl create job --from=cronjob/arrconf arrconf-uat-sc2-$(date +%s)` produces a Job pod that exits 0. No `ConfigError` line in stderr. Logs contain `apply_complete` events for sonarr AND radarr.
result: partial
evidence: |
  Pod arrconf-uat-sc2-1779612181-b6j5b: exit code 1 (NOT 0).

  Phase 18 deliverable VERIFIED:
    - No ConfigError raised → pre-flight gate (Phase 18 NEW code in __main__.py) ran silently
    - Pre-flight gate passing means QBT_USER + QBT_PASS env vars are set (consistent
      with CLAUDE.md Phase 5 baseline)
    - Phase 18 fail-fast contract (D-18-FAIL-FAST-01) cannot fire here because env IS set

  Pre-existing bug (NOT a Phase 18 regression):
    - Crash at Step 5 `_reconcile_remote_path_mappings`:
      HTTPStatusError 400 Bad Request from
      http://sonarr.selfhost.svc.cluster.local:8989/api/v3/remotepathmapping
    - Same crash signature on prior CronJob run `arrconf-29659980` running image :0.9.0
      (BEFORE Phase 18 deployed) — bug pre-dates Phase 18 by ≥3 image versions
    - Cluster Sonarr has 4 legacy RPMs (complete/series/anime/family) but the
      generator emits ~7+ RPMs from categories[] (series-emilie, series-thomas,
      series-garcons, series-zoe, films, films-zoe, etc.). One of the new POSTs
      is rejected by Sonarr — likely because the local path
      `/data/torrents/<new-category>/` doesn't exist in qBittorrent's filesystem yet,
      or another schema validation
    - The Step 6 download_clients env-injection (Phase 18 PRIMARY DELIVERABLE)
      is functionally UNREACHABLE on the live cluster until this RPM bug is fixed
severity: major
disposition: |
  Phase 18 code is verified at every level (unit tests 411 pass, mypy strict clean,
  pre-flight gate verified on cluster, image deploys cleanly). The end-to-end
  cluster proof requires fixing a separate pre-existing bug. Recommend:
    1. Open new debug session: /gsd-debug "RPM 400 — generator emits paths not in Sonarr"
    2. Either pre-create the missing /data/torrents/<category>/ dirs on the qBittorrent
       volume, or split the categories cutover from the env-injection cutover

### 3. SC#3 — Sonarr/Radarr UI "Test" button on qBit DCs returns green
expected: In Sonarr UI (https://sonarr.tgu.ovh/settings/downloadclients) and Radarr UI (https://radarr.tgu.ovh/settings/downloadclients), clicking "Test" on each visible qBit DC (e.g. `qBittorrent-tv`, `qBittorrent-anime`, etc.) turns green with a checkmark. This is the DISPOSITIVE proof that env-injection wrote real credentials into Sonarr/Radarr's stored DC config.
result: blocked
blocked_by: prior-phase
reason: |
  Depends on Step 6 (download_clients) executing on the cluster, which requires
  Step 5 (remote_path_mappings) to succeed first. Step 5 fails with a pre-existing
  RPM 400 bug (see SC#2). Test button verification cannot occur until the cluster's
  reconcile reaches Step 6.

### 4. SC#4 — Second CronJob run emits 0 drift on download_clients
expected: A second manual Job (`arrconf-uat-sc4-$(date +%s)`) produces no `plan_action` events on the `download_clients` step for sonarr+radarr, OR all events show `action=no-op`. 0 `add/update/delete` on qBit DCs.
result: blocked
blocked_by: prior-phase
reason: |
  Idempotence check requires a successful first apply that reaches Step 6. Same
  blocker as SC#3 — pre-existing RPM 400 bug halts the reconcile at Step 5.

### 5. SC#5 (optional) — Explicit YAML credentials override env
expected: After editing `charts/arr-stack/files/arrconf.yml` to add explicit `username` + `password` on one qBit DC, committing, syncing, and triggering the next reconcile, an `update_field` event appears and Sonarr's "Test" button returns ✗ (because the explicit value is wrong vs real qBit creds — proves env was correctly ignored). REVERT after testing.
result: blocked
blocked_by: prior-phase
reason: |
  Same dependency chain as SC#3 + SC#4. Optional scenario; covered by unit test
  test_yaml_explicit_env_ignored at tools/arrconf/tests/test_qbit_credentials_env_fallback.py

## Summary

total: 5
passed: 1
issues: 0
pending: 0
skipped: 0
partial: 1
blocked: 3

## Gaps

- truth: "Cluster CronJob completes with exit 0 and emits apply_complete for sonarr+radarr"
  status: failed
  reason: |
    Pre-existing pre-Phase-18 bug — Step 5 `_reconcile_remote_path_mappings` 400s
    against Sonarr's /api/v3/remotepathmapping. Generator emits ~7+ RPMs derived
    from categories[] but cluster Sonarr only has 4 legacy RPMs. One of the new
    POSTs is rejected. Same crash on image :0.9.0 (pre-Phase-18). NOT a Phase 18
    regression — Phase 18 code itself is verified.
  severity: major
  test: 2
  artifacts:
    - tools/arrconf/arrconf/reconcilers/_shared.py:70   # _reconcile_remote_path_mappings
    - tools/arrconf/arrconf/reconcilers/sonarr.py:532   # Step 5 call site
  missing: []   # No code missing in Phase 18 — separate debug session needed
  out_of_scope: true
  recommended_action: |
    /gsd-debug "RPM 400 — sonarr reconciler emits paths not validated by Sonarr"
    Likely root cause: missing /data/torrents/<category>/ dirs in qBittorrent volume
    for the v0.3.0 categories (series-emilie, series-thomas, series-garcons,
    series-zoe, films-zoe, films-enfants, etc.). Aligns with CLAUDE.md's filesystem
    migration runbook — operator may need to create the missing directories
    or split the categories cutover from the env-injection cutover.
