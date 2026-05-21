---
status: partial
phase: 09-categories-data-model-chart-initcontainer
source: [09-VERIFICATION.md]
started: 2026-05-18T12:00:00Z
updated: 2026-05-18T12:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Cluster upgrade — Job emits 10 events + 10 dirs exist

test: Deploy arr-stack chart upgrade to my-kluster; run `kubectl logs job/arr-stack-categories-init -n selfhost` and verify 10 `media_dir_ensured` JSON lines are emitted; then run `kubectl exec -n selfhost deployment/jellyfin -- ls /media/` and verify all 10 `/media/<name>` directories exist.
expected: All 10 directories (`series`, `series-emilie`, `series-thomas`, `series-garcons`, `series-zoe`, `films`, `nouveaux-films`, `films-enfants`, `films-animation-enfants`, `films-zoe`) are present; Job emits exactly 10 JSON-line events; re-running the upgrade (`helm upgrade` a second time) produces 0 new `created` dirs (idempotent).
why_human: ROADMAP SC#3 is a cluster-time gate — the Helm pre-install/pre-upgrade Job's actual execution against the NFS PVC (`media-nas-pvc`) and NFS `root_squash` behavior cannot be verified programmatically from the repo without a running cluster.
result: [pending]

### 2. CR-01 — NFS uid:1000 / fsGroup verified non-blocking

test: Observe that CR-01 (NFS `root_squash` / `fsGroup` interaction) does NOT block the first helm upgrade. If the Job fails, check the pod log for `EPERM` and validate the NAS export is accessible to uid 1000.
expected: Job pod runs as uid 1000, `mkdir -p` on `/media` succeeds, all 10 dirs created without `EPERM`. If it fails, the pre-install hook blocks the chart install and the operator sees `hook failed` from ArgoCD — recoverable by fixing the NAS export.
why_human: CR-01 from the code review is an operational/runtime concern about NFS semantics that cannot be resolved by static analysis. Whether the specific cluster's NAS export allows writes from uid 1000 is a cluster-time observable, not a codebase observable.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
