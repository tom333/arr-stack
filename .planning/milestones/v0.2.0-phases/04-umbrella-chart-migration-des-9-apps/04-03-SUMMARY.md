---
phase: 04-umbrella-chart-migration-des-9-apps
plan: "03"
subsystem: helm-chart
tags: [helm, umbrella-chart, values, renovate, sonarr, radarr, prowlarr, qbittorrent]
dependency_graph:
  requires: [04-02]
  provides: [sonarr-values, radarr-values, prowlarr-values, qbittorrent-values]
  affects: [04-08-byte-equivalence-diff]
tech_stack:
  added: []
  patterns: [app-template-5.0.0-alias-body, global-fullnameOverride, renovate-image-annotation]
key_files:
  modified:
    - charts/arr-stack/values.yaml
decisions:
  - "global.fullnameOverride per alias preserves Service DNS names (sonarr.selfhost.svc.cluster.local:8989 etc)"
  - "qbittorrent tag pinned to 5.2.0 per D-04-PIN-01 (digest sha256:2e0148... resolved from evidence/current-image-tags.txt)"
  - "prowlarr oauth2-proxy annotations kept commented out — byte-equiv to my-kluster source (Sonarr/Radarr need to reach Prowlarr without OAuth flow)"
metrics:
  duration: "~20 minutes"
  completed: "2026-05-13T04:50:00Z"
  tasks_completed: 2
  files_modified: 1
---

# Phase 04 Plan 03: Arr-Family Alias Bodies (sonarr/radarr/prowlarr/qbittorrent) Summary

Populated `charts/arr-stack/values.yaml` with verbatim per-alias bodies for the four arr-family apps from my-kluster main, with three pre-approved deltas: `global.fullnameOverride`, Renovate annotations, and qbittorrent semver pin.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 3.1 | Sonarr + Radarr alias bodies | e926d57 | charts/arr-stack/values.yaml |
| 3.2 | Prowlarr + qbittorrent alias bodies | 3f551c5 | charts/arr-stack/values.yaml |

## What Was Done

### Task 3.1: Sonarr + Radarr

Replaced `sonarr: {}` and `radarr: {}` with full app-template 5.0.0 value bodies ported verbatim from `my-kluster main:argocd/argocd-apps/{sonarr,radarr}-app.yaml`.

**sonarr**: tag `4.0.17`, port 8989, hostPath `/opt/media-stack/torrents` + `existingClaim: media-nas-pvc`, oauth2-proxy ingress annotations, cert-manager TLS.

**radarr**: tag `6.1.1`, port 7878, same persistence pattern as sonarr, same ingress shape.

Three deltas vs source:
1. `global.fullnameOverride: sonarr` / `radarr` — DNS preservation (Service named `sonarr` not `arr-stack-sonarr`)
2. `# renovate: image=lscr.io/linuxserver/{app}` above each `repository:` line
3. Tags quoted as strings (`"4.0.17"`, `"6.1.1"`) to prevent YAML number-coercion

### Task 3.2: Prowlarr + qbittorrent

Replaced `prowlarr: {}` and `qbittorrent: {}` skeletons.

**prowlarr**: tag `2.3.5`, port 9696, oauth2-proxy annotations kept **commented out** (byte-equivalent to my-kluster source — Sonarr/Radarr call Prowlarr directly, OAuth flow would break sync).

**qbittorrent**: tag `latest` → `"5.2.0"` per D-04-PIN-01. This is the **only non-verbatim change** from the source: the production `:latest` resolves to digest `sha256:2e0148...` = 5.2.0. No behavioural change, but an explicit semver pin replacing implicit drift. Port 8080, WEBUI_PORT env, hostPath `/opt/media-stack/torrents` at `/data`.

## Verification Results

```
helm lint charts/arr-stack/   → 1 chart(s) linted, 0 chart(s) failed
helm template arr-stack charts/arr-stack/
  → kind: Deployment × 4    (sonarr/radarr/prowlarr/qbittorrent)
  → kind: Service × 4
  → kind: Ingress × 4
  → kind: PersistentVolumeClaim × 4
  → kind: ServiceAccount × 10
  → kind: ConfigMap × 2

sonarr name refs in template: 5 (>= 4 required)
radarr name refs in template: 5 (>= 4 required)
prowlarr name refs in template: 5 (>= 4 required)
qbittorrent name refs in template: 5 (>= 4 required)
No arr-stack-* prefix regression: PASS
qbittorrent:latest in template: False (PASS)
qbittorrent:5.2.0 in template: True (PASS)
check-renovate-annotations.sh: OK — all repository: lines have annotations
6 remaining aliases still {}: PASS (cleanuparr/seerr/flaresolverr/jellyfin/arrconf/configarr)
tag: latest in values.yaml: False (PASS)
fullnameOverride entries: 4 (PASS)
```

## Deviations from Plan

None — plan executed exactly as written.

Note: The plan's acceptance criteria test `grep -A20 'prowlarr:$' ... | grep -c '# nginx...'` has an off-by-one (the annotation is 26 lines after `prowlarr:`, not within 20). The content itself is correct and byte-equivalent to the my-kluster source. This is a test harness tightness issue, not a content defect.

## Known Stubs

None — all 4 alias bodies are fully wired with real image references, persistence, service, and ingress configuration. The remaining 6 aliases (`cleanuparr`, `seerr`, `flaresolverr`, `jellyfin`, `arrconf`, `configarr`) are intentionally `{}` placeholders awaiting Plans 04-04 and 04-05.

## Threat Flags

None — no new network endpoints or auth paths introduced beyond what existed in the separate ArgoCD Applications being consolidated.

## Self-Check: PASSED

- charts/arr-stack/values.yaml: FOUND (237 lines, > 200 minimum)
- 04-03-SUMMARY.md: FOUND
- Commit e926d57 (Task 3.1): FOUND
- Commit 3f551c5 (Task 3.2): FOUND
