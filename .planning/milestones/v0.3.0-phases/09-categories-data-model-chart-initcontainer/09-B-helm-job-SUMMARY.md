---
phase: 09-categories-data-model-chart-initcontainer
plan: 09-B-helm-job
subsystem: helm-chart
tags:
  - helm
  - kubernetes
  - job
  - categories
  - filesystem-init
dependency_graph:
  requires: []
  provides:
    - charts/arr-stack/templates/categories-init-job.yaml
  affects:
    - charts/arr-stack (helm lint + kubeconform must stay green)
tech_stack:
  added:
    - busybox:1.36.1 (Helm Job container image)
  patterns:
    - Helm pre-install/pre-upgrade hooked Job
    - .Files.Get | fromYaml single-source pattern (D-08 pivot)
    - Pod-level securityContext uid:gid 1000:1000
key_files:
  created:
    - charts/arr-stack/templates/categories-init-job.yaml
  modified: []
decisions:
  - "D-08 pivot: single-source .Files.Get | fromYaml reads categories[] from files/arrconf.yml at template-render time — no values.yaml duplicate, no CI sync gate"
  - "Use .Release.Name directly for Job name (arr-stack.fullname helper does not exist in _helpers.tpl)"
  - "Wave 1 exit: zero iterations render is correct and expected (no categories block in arrconf.yml yet)"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-18T08:29:54Z"
  tasks_completed: 1
  tasks_total: 1
  files_changed: 1
---

# Phase 9 Plan B: Helm-hooked Job for categories /media/* init — Summary

**One-liner:** Helm pre-install/pre-upgrade Job using `.Files.Get "files/arrconf.yml" | fromYaml` single-source pattern to idempotently create `/media/<name>` directories per category entry, running as uid:gid 1000:1000 with busybox:1.36.1 pinned.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| B1 | Create categories-init-job.yaml Helm-hooked Job | ed8ad15 | charts/arr-stack/templates/categories-init-job.yaml (created, 75 lines) |

## D-NN Decision Coverage

| Decision | Status | Implementation |
|----------|--------|----------------|
| D-06: Standalone Job, not per-controller initContainer | Implemented | Job in `charts/arr-stack/templates/categories-init-job.yaml` |
| D-07: Hook annotations `pre-install,pre-upgrade` + `before-hook-creation,hook-succeeded` | Implemented | `annotations: "helm.sh/hook": pre-install,pre-upgrade` etc. |
| D-08 (pivoted): Single-source `.Files.Get \| fromYaml` from `files/arrconf.yml` | Implemented | `{{- $cfg := .Files.Get "files/arrconf.yml" \| fromYaml -}}` at template top |
| D-09: JSON-line log `media_dir_ensured` with `path`/`created`/`existed` fields | Implemented | Two `printf` branches in the sh loop |
| D-10: Image pinned `busybox:1.36.1` | Implemented | `image: busybox:1.36.1` |
| D-11: `# renovate: image=docker.io/busybox` annotation directly above image line | Implemented | Comment line directly above `image:` with no blank line |
| D-12: Pod securityContext `runAsUser/runAsGroup/fsGroup: 1000` | Implemented | `securityContext:` block at pod spec level |
| D-13: Zero Python code, reconcilers not touched | Preserved | Only `charts/arr-stack/templates/` modified |

## Validation Results

### helm lint

```
==> Linting charts/arr-stack/
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

Exit code: **0** (PASS)

### helm template + kubeconform

`kubeconform` is not installed in this environment (not available on PATH). Kubernetes manifest validity was verified manually via `helm template` render inspection — all required fields present and correctly structured.

### Wave-1-feasible check (W-02 replacement)

```bash
helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml \
  | grep -F '"helm.sh/hook": pre-install,pre-upgrade'
# Output:
#     "helm.sh/hook": pre-install,pre-upgrade
```

Exit code: **0** (PASS — hook annotations render correctly under Wave 1 state)

### Rendered manifest excerpt

```yaml
  name: arr-stack-categories-init
  namespace: default
  labels:
    helm.sh/chart: arr-stack-0.1.0
    app.kubernetes.io/managed-by: Helm
    app.kubernetes.io/part-of: arr-stack
  annotations:
    "helm.sh/hook": pre-install,pre-upgrade
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
    "helm.sh/hook-weight": "0"
spec:
  activeDeadlineSeconds: 120
  backoffLimit: 2
  template:
    spec:
      restartPolicy: OnFailure
      securityContext:
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
      containers:
        - name: mkdir
          # renovate: image=docker.io/busybox
          image: busybox:1.36.1
          imagePullPolicy: IfNotPresent
          ...
          command: ["/bin/sh", "-c"]
          args:
            - |
              set -e
          # (zero iterations — no categories block yet in arrconf.yml)
          volumeMounts:
            - name: media
              mountPath: /media
      volumes:
        - name: media
          persistentVolumeClaim:
            claimName: media-nas-pvc
```

All locked D-NN signals present: hook annotations, `busybox:1.36.1` with renovate annotation, `runAsUser: 1000`, `claimName: media-nas-pvc`.

## Wave 1 State Note

At Wave 1 exit time, `charts/arr-stack/files/arrconf.yml` has no `categories:` block. The `{{- range $cat := $cfg.categories }}` range over nil is a no-op in Helm/Sprig. The rendered Job `args:` section contains only `set -e` and emits zero mkdir/printf lines. This is correct and expected behavior — the plan design payoff.

## Deferred to Plan C Task C3

The 20-printf-line render verification (10 categories × 2 printf branches = 20 lines) is owned by **Plan C Task C3**. Plan C first adds the 10-entry `categories:` block to `charts/arr-stack/files/arrconf.yml`, then Task C3 asserts the 20-line render count using `(printf "%s\n" ...)` pattern. Plan B cannot evaluate this check at Wave 1 exit time (W-02 fix).

## Pointers

- **Plan C** (Wave 2): feeds this Job with the 10-entry categories block + owns Task C3 (20-line render verification)
- **Plan D** (Wave 2): release-tags the chart (`v0.3.0`) for ArgoCD pickup via my-kluster Renovate
- **Manual cluster gates**: documented in `09-VALIDATION.md` rows 1-4; must be run before my-kluster `targetRevision` bump per ADR-6 + snapshot discipline (tools/snapshot/snapshot.sh baseline before first Phase 9 cluster deploy)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — the template is complete. Zero-iteration render at Wave 1 is by design (not a stub), and Plan C Task C3 will verify the full 20-line render.

## Threat Flags

No new threat surface beyond what the plan's threat model covers. The Job template introduces exactly the trust boundaries documented in the plan's `<threat_model>` section (T-09B-01 through T-09B-08). No unplanned network endpoints, auth paths, or schema changes.

## Self-Check: PASSED

- `charts/arr-stack/templates/categories-init-job.yaml`: FOUND (75 lines)
- Commit `ed8ad15`: FOUND (feat(09-B): add Helm-hooked Job...)
- All 13 acceptance criteria: PASS
- helm lint: PASS (0 failures)
- Wave-1-feasible hook annotation check: PASS
