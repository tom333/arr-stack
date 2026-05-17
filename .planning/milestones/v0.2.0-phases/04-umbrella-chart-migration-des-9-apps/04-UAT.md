---
status: partial
phase: 04-umbrella-chart-migration-des-9-apps
source:
  - 04-01-SUMMARY.md
  - 04-02-SUMMARY.md
  - 04-03-SUMMARY.md
  - 04-04-SUMMARY.md
  - 04-05-SUMMARY.md
  - 04-06-SUMMARY.md
  - 04-07-SUMMARY.md
  - 04-08-SUMMARY.md
started: 2026-05-14T16:00:00Z
updated: 2026-05-14T16:47:00Z
---

## Current Test

[testing paused — 2 items outstanding: operator-timed README walkthrough (Test 10) + 72h passive SC#2 watch (Test 11). Both are time/operator-bound, not blockers.]

## Tests

### 1. arr-stack ArgoCD App Synced + Healthy
expected: kubectl shows arr-stack App Synced+Healthy with automated:{prune,selfHeal}. Maps to ROADMAP SC#1 + Plan 04-09 T9.1.
result: pass
evidence: |
  $ kubectl -n argocd get application arr-stack -o jsonpath='...'
  sync: Synced  health: Healthy  automated: {"prune":true,"selfHeal":true}

### 2. 10 unit ArgoCD Applications + 2 custom charts deleted
expected: All 10 unit Apps return "not found"; both chart dirs do not exist on my-kluster main. Maps to ROADMAP SC#1.
result: pass
evidence: |
  sonarr/radarr/prowlarr/cleanuparr/qbittorrent/seerr/flaresolverr/jellyfin/arrconf/configarr — all 10 report "deleted" (kubectl returned not-found).
  /home/moi/projets/perso/my-kluster/charts/arrconf/ — No such file or directory
  /home/moi/projets/perso/my-kluster/charts/configarr/ — No such file or directory

### 3. No regression — ingress smoke (7 public hostnames respond)
expected: Each of 7 hostnames returns 200 or 302 (oauth2 redirect counts as healthy). Maps to ROADMAP SC#3.
result: pass
evidence: |
  sonarr.tgu.ovh -> 302
  radarr.tgu.ovh -> 302
  prowlarr.tgu.ovh -> 200
  cleanuparr.tgu.ovh -> 302
  qbittorrent.tgu.ovh -> 302
  seerr.tgu.ovh -> 302
  jellyfin.tgu.ovh -> 302

### 4. Per-alias Service selectors — Bug 1 fix verified
expected: Each Service EndpointSlice returns exactly 1 endpoint. Proves Bug 1 (Service selector too broad) is fixed in v0.2.6.
result: pass
evidence: |
  sonarr: 1 endpoint(s)
  radarr: 1 endpoint(s)
  prowlarr: 1 endpoint(s)
  cleanuparr: 1 endpoint(s)
  qbittorrent: 1 endpoint(s)
  seerr: 1 endpoint(s)
  flaresolverr: 1 endpoint(s)
  jellyfin: 1 endpoint(s)

### 5. Per-alias Deployment SA refs — Bug 2 fix verified
expected: Each Deployment serviceAccountName matches the alias name. Proves Bug 2 (SA mismatch) is fixed in v0.2.6.
result: pass
evidence: |
  sonarr/radarr/prowlarr/cleanuparr/qbittorrent/seerr/flaresolverr/jellyfin — all OK (SA name == alias name).

### 6. prowlarr inter-app stability — 10/10 retries return 200
expected: 10/10 retries return 200 (was ~50/50 200/502 pre-Bug-1 fix).
result: pass
evidence: |
  All 10 retries returned 200.

### 7. arrconf CronJob runs cleanly
expected: arrconf-uat-smoke job completes within 60s, logs show no validation errors and `event: no-op` (or apply_complete) for sonarr.
result: pass
evidence: |
  Initially FAILED on v0.2.6 with: "Config validation error in /app/config/arrconf.yml: 1 validation error for RootConfig — apps: Extra inputs are not permitted". Root cause: charts/arr-stack/files/arrconf.yml used the obsolete Phase 1 schema (apps: wrapper).
  Fix shipped as arr-stack PR #6, auto-tagged v0.2.7 at commit 14a5717. my-kluster PR #1394 bumped targetRevision v0.2.6 -> v0.2.7. Re-ran the smoke job post-sync:
    $ kubectl -n selfhost create job --from=cronjob/arrconf arrconf-uat-smoke-retry
    $ kubectl -n selfhost wait job/arrconf-uat-smoke-retry --for=condition=complete --timeout=120s
    > job.batch/arrconf-uat-smoke-retry condition met
  Logs show: prune_skip (expected for unmanaged indexers, prune:false default), host_config_reconcile_skipped (D-03-04 opt-in default), event: no-op for sonarr (idempotent — YAML matches Sonarr's current state). Exit code 0.

### 8. No :latest in values.yaml + Renovate annotations on all images
expected: No 'tag: latest' lines; check-renovate-annotations.sh exits 0. Maps to ROADMAP SC#4.
result: pass
evidence: |
  grep 'tag: latest' charts/arr-stack/values.yaml → (no matches)
  tools/scripts/check-renovate-annotations.sh → exit 0, "OK: all repository: lines have renovate annotations"

### 9. chart-lint CI green on latest push to main + auto-tag working
expected: Latest push-to-main run conclusion is success; 5 v0.2.x tags exist. Maps to ROADMAP SC#5.
result: pass
evidence: |
  conclusion: success  title: "fix(chart): per-alias nameOverride + serviceAccount identifier (#5)"  at: 2026-05-14T04:35:08Z
  v0.2.2 / v0.2.3 / v0.2.4 / v0.2.5 / v0.2.6 — all 5 tags created via auto-tag job.

### 10. README onboarding < 30 min (Plan 04-07 Task 7.3)
expected: Operator-timed walkthrough completes in < 30 min following README.md only. Maps to ROADMAP SC#6 / REQ-readme-onboarding.
result: pending

### 11. SC#2 — Renovate E2E PR-to-cluster-latency < 1h
expected: First Renovate-driven bump lands end-to-end (arr-stack PR → auto-tag → my-kluster targetRevision PR → ArgoCD sync) < 1h. T+72h hard gate per D-04-PIN-04. Maps to ROADMAP SC#2 / REQ-pr-to-cluster-latency.
result: pending

## Summary

total: 11
passed: 9
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps

- truth: "arrconf CronJob runs cleanly against the umbrella-mounted ConfigMap"
  status: resolved
  reason: "Initially FAILED on v0.2.6 with: 'Config validation error in /app/config/arrconf.yml: 1 validation error for RootConfig — apps: Extra inputs are not permitted'. Root cause: charts/arr-stack/files/arrconf.yml used obsolete Phase 1 schema (apps: wrapper) ported verbatim from my-kluster pre-cutover state. v0.2.1 binary's RootConfig pydantic model expects flat root keys (Phase 3 D-03-05). Pre-cutover the arrconf CronJob was SUSPENDED (Phase 02.2 forensic period, 2026-05-09T06:48:11Z), masking the bug; cutover unsuspended it via the new umbrella CronJob."
  severity: major
  test: 7
  root_cause: "charts/arr-stack/files/arrconf.yml wraps config under 'apps:' root key. arrconf v0.2.1's RootConfig schema (tools/arrconf/arrconf/config.py:195) sets model_config = ConfigDict(extra='forbid') with fields sonarr/radarr/prowlarr at root level. Plan 04-02 Task 2.2 ported the file verbatim without updating to the new schema."
  fix_commits:
    - "arr-stack: 14a5717 (PR #6, tag v0.2.7) — flatten apps: → root-level sonarr"
    - "my-kluster: PR #1394 — bump targetRevision v0.2.6 → v0.2.7"
  resolution_evidence: |
    Post-fix re-run of UAT Test 7 at 2026-05-14T05:43Z: arrconf-uat-smoke-retry job condition met within 60s, logs show no validation error, event: no-op for sonarr (idempotent reconcile), exit 0.
