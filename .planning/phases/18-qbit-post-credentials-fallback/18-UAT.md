---
status: complete
phase: 18-qbit-post-credentials-fallback
source:
  - 18-A-SUMMARY.md
  - 18-HUMAN-UAT.md
started: 2026-05-24T08:15:00Z
updated: 2026-05-24T09:10:00Z
chart_image_tag: "0.12.1"
git_tags: ["v0.12.1", "v0.13.0"]
ghcr_image: "ghcr.io/tom333/arr-stack-arrconf:0.12.1"
argocd_sync_status: "Synced"
arrconf_image_live: "ghcr.io/tom333/arr-stack-arrconf:0.12.1"
unblocked_by: ".planning/debug/sonarr-rpm-400-categories.md (resolved 2026-05-24)"
---

## Current Test

[testing complete — all SC pass]

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
result: pass
evidence: |
  Pod arrconf-fix-rpm-1779613542-g4zjz: Phase=Succeeded, exit code 0.
  No ConfigError, no HTTPStatusError, no Traceback in logs.
  apply_complete events fired for all 5 apps:
    - sonarr: 5 new qBit DCs added (Séries, Séries-Émilie, Séries-Thomas, Séries-Garçons, Séries-Zoé)
      + 3 new RPMs (series-thomas, series-garcons, series-zoe; series-emilie already pre-existed from debug repro)
    - radarr: 5 new qBit DCs added (Films, Nouveaux Films, Films-Enfants, Films-Animation-Enfants, Films-Zoé)
      + 4 new RPMs (nouveaux-films, films-enfants, films-animation-enfants, films-zoe)
      + 4 new root_folders
    - qbittorrent: 10 categories updated (series, series-emilie, ..., films-zoe)
    - seerr: user policy applied
    - jellyfin: user policy applied
  Phase 18 pre-flight gate ran without error (env vars set correctly).
  Phase 18 Step 6 env-injection helper executed for the first time on the live cluster.

### 3. SC#3 — Sonarr/Radarr UI "Test" button on qBit DCs returns green
expected: In Sonarr UI (https://sonarr.tgu.ovh/settings/downloadclients) and Radarr UI (https://radarr.tgu.ovh/settings/downloadclients), clicking "Test" on each visible qBit DC turns green with a checkmark. DISPOSITIVE proof env-injection wrote real credentials.
result: pass
evidence: |
  API equivalent of UI Test button: POST /api/v3/downloadclient/test on each qBit DC,
  authenticating against qBittorrent's Web UI with the stored credentials.

  Sonarr — 9/9 qBit DCs HTTP 200 (PASS):
    id=1  qBittorrent              | id=3  qBittorrent - Anime          | id=4  qBittorrent - Family
    id=5  qBittorrent - Séries     | id=6  qBittorrent - Séries-Émilie  | id=7  qBittorrent - Séries-Thomas
    id=8  qBittorrent - Séries-Garçons | id=9  qBittorrent - Séries-Zoé | id=2  qBittorrent - TV

  Radarr — 9/9 qBit DCs HTTP 200 (PASS):
    id=1  qBittorrent              | id=3  qBittorrent - Anime          | id=4  qBittorrent - Family
    id=5  qBittorrent - Films      | id=6  qBittorrent - Nouveaux Films | id=7  qBittorrent - Films-Enfants
    id=8  qBittorrent - Films-Animation-Enfants | id=9  qBittorrent - Films-Zoé | id=2  qBittorrent - Movies

  HTTP 200 from /downloadclient/test confirms the stored username+password authenticated
  successfully against qBittorrent's Web UI — Phase 18's env-injection wrote real creds.

### 4. SC#4 — Second CronJob run emits 0 drift on download_clients
expected: A second manual Job produces no `plan_action` events on the `download_clients` step for sonarr+radarr. 0 add/update/delete on qBit DCs.
result: pass
evidence: |
  Pod arrconf-uat-sc4-1779613679-b5rd5: Phase=Succeeded, exit code 0.
  Total plan_action events during download_clients step: 0 (both sonarr and radarr).
  Apply_complete only emitted for seerr (user policy) and jellyfin (user policy) — unrelated
  to Phase 18. Sonarr+Radarr+qBittorrent emitted no apply_complete because there were no
  actions to commit.

  Dispositive idempotence proof:
    - 0 ADD/UPDATE/DELETE on Sonarr download_clients (5 qBit DCs already match desired state)
    - 0 ADD/UPDATE/DELETE on Radarr download_clients (5 qBit DCs already match desired state)
    - 0 ADD/UPDATE/DELETE on Sonarr remote_path_mappings (4 new RPMs from 1st apply now match)
    - 0 ADD/UPDATE/DELETE on Radarr remote_path_mappings (same)
    - 0 ADD/UPDATE/DELETE on qBittorrent categories

  Phase 18's `differ.merge_fields_for_put` + `_strip_redacted_fields` machinery
  (D-02.2-AUTH-REGRESSION + D-18-IDEMPOTENCE-FREE) verified working end-to-end:
  env-injected credentials do NOT cause spurious PUT diffs on 2nd apply.

### 5. SC#5 (optional) — Explicit YAML credentials override env
expected: Explicit YAML username/password values in arrconf.yml win over env. Sonarr's "Test" button returns ✗ (because the explicit value differs from real qBit creds) on the next reconcile.
result: skipped
reason: |
  Optional scenario, non-blocking. Already covered by unit test
  `test_yaml_explicit_env_ignored` in `tools/arrconf/tests/test_qbit_credentials_env_fallback.py`.
  Skipping the cluster-side test to avoid mutating production YAML for a property
  already proven by deterministic unit test.

## Summary

total: 5
passed: 4
issues: 0
pending: 0
skipped: 1
partial: 0
blocked: 0

## Gaps

[none — all SC pass after RPM-400 debug session resolved the cluster-side blocker]

## Resolution

Phase 18 is **dispositively verified end-to-end** on the live cluster:
- Unit tests: 411 pass, 95.38% coverage on differ + reconcilers (CI)
- Code review: 2 BLOCKERs + 5 WARNINGs auto-fixed (commits 5cc40ee → 6c9579e)
- Triade Python green: ruff format + ruff check + mypy strict on `arrconf`
- Cluster deploy: image `:0.12.1` synced via ArgoCD
- Pre-flight gate (Phase 18 NEW code in `__main__.py`): verified silent on cluster (no ConfigError → env vars present)
- Step 6 env-injection (Phase 18 PRIMARY DELIVERABLE): 5 Sonarr + 5 Radarr qBit DCs added with real creds
- Dispositive auth test: 18/18 qBit DC `/test` endpoints HTTP 200 against live qBittorrent
- Idempotence (D-02.2-AUTH-REGRESSION + D-18-IDEMPOTENCE-FREE): 2nd run emits 0 plan_actions

The cluster-side blocker (`sonarr-rpm-400-categories` — pre-existing PathExistsValidator
bug on `/api/v3/remotepathmapping` that pre-dated Phase 18 by ≥3 image versions) was
resolved in the same UAT session via 8 `mkdir -p /data/<category>/` operator commands
on the qBittorrent volume. See `.planning/debug/sonarr-rpm-400-categories.md` for the
full debug session record.

REQ-qbit-post-credentials is fully satisfied. Phase 18 can be marked complete in ROADMAP.md.
