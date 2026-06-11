---
status: complete
phase: 30-cross-seed
source:
  - 30-01-SUMMARY.md
  - 30-02-SUMMARY.md
  - 30-03-SUMMARY.md
started: 2026-05-31T06:15:09Z
updated: 2026-05-31T06:17:00Z
---

## Current Test

[testing complete]

## Tests

### 1. cross-seed token emission
expected: grep PLACEHOLDER returns nothing; config.js has distinct ${PROWLARR_API_KEY} + ${QBT_USER}:${QBT_PASS} tokens; `arrconf generate --check` exit 0; values.yaml arrconf tag = 0.19.1
result: pass

### 2. Helm renders cross-seed Deployment + initContainer
expected: `helm template charts/arr-stack/` renders cross-seed Deployment with initContainer `config-init`; config-resolved emptyDir surfaces at /config/config.js via subPath; main container args=[daemon], port 2468, envFrom arrconf-env. `helm lint` passes (0 failures).
result: pass

### 3. CI + Renovate + README updated for 12th alias
expected: chart-lint.yml alias loop includes `cross-seed`; renovate synthetic-test threshold = 12 (count 13 passes); README local-verify loop includes cross-seed (12 aliases). `check-renovate-annotations.sh` exits 0.
result: pass

### 4. Operator runbook complete
expected: 30-OPERATOR-RUNBOOK.md documents pre-sync pre-reqs (cross-seed-config PVC, mkdir /media/data/torrents/cross-seed, arrconf-env keys), post-sync verification, teardown, rollback. References secret key NAMES only, never values.
result: pass

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
