---
status: partial
phase: 31-qbit-manage
source: [31-VERIFICATION.md]
started: 2026-05-31
updated: 2026-05-31
---

## Current Test

[awaiting human testing — cluster deployment required]

## Tests

### 1. CronJob run-once lifecycle
expected: After `arrconf apply` + ArgoCD sync, manually triggering the qbit-manage CronJob (`kubectl -n selfhost create job --from=cronjob/arr-stack-qbit-manage qbm-uat`) produces a pod that runs once and reaches `Completed` (NOT a daemon hang). `QBT_RUN=true` + `QBT_SCHEDULE=0` enforce single-run. Pod logs show share_limits/tracker_tags/recyclebin sections executing and NO category writes (cat_update disabled).
result: [pending]

### 2. !ENV credential resolution in live pod
expected: The `user: !ENV QBT_USER` / `pass: !ENV QBT_PASS` literals in the mounted ConfigMap (`/config/config.yml`) resolve at runtime from `envFrom: arrconf-env` (SealedSecret carries QBT_USER/QBT_PASS). qbit_manage authenticates to the in-cluster qBittorrent successfully — no auth error in logs.

result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
