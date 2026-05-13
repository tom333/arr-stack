---
phase: 04-umbrella-chart-migration-des-9-apps
plan: "04"
subsystem: helm-chart
tags: [helm, umbrella-chart, values, renovate, cleanuparr, seerr, flaresolverr, jellyfin, latest-pin]
dependency_graph:
  requires: [04-03]
  provides: [cleanuparr-values, seerr-values, flaresolverr-values, jellyfin-values]
  affects: [04-08-byte-equivalence-diff]
tech_stack:
  added: []
  patterns: [app-template-5.0.0-alias-body, global-fullnameOverride, renovate-image-annotation, no-ingress-internal-app, no-oauth2-proxy-self-auth]
key_files:
  modified:
    - charts/arr-stack/values.yaml
decisions:
  - "cleanuparr tag pinned to 2.3.3 per D-04-PIN-01 (digest sha256:9b8f7a5f... resolved from evidence/current-image-tags.txt)"
  - "flaresolverr tag pinned to v3.4.6 per D-04-PIN-01 (digest sha256:7962759d... resolved from evidence/current-image-tags.txt)"
  - "flaresolverr has NO ingress — cluster-internal use only (Prowlarr FlareSolverr bypass), verbatim from my-kluster source"
  - "jellyfin ingress has NO oauth2-proxy annotations — Jellyfin handles its own authentication"
  - "jellyfin ingress keeps nginx.ingress.kubernetes.io/proxy-body-size: \"0\" — required for streaming"
  - "seerr tag v3.2.0 verbatim from my-kluster main (already pinned, not a :latest app)"
metrics:
  duration: "~20 minutes"
  completed: "2026-05-13T05:07:30Z"
  tasks_completed: 2
  files_modified: 1
---

# Phase 04 Plan 04: Media App Alias Bodies (cleanuparr/seerr/flaresolverr/jellyfin) Summary

Populated `charts/arr-stack/values.yaml` with verbatim per-alias bodies for the four remaining media apps, with pre-approved deltas: `global.fullnameOverride`, Renovate annotations, and semver pins for the two `:latest` apps (cleanuparr 2.3.3, flaresolverr v3.4.6). After this plan, the `:latest` migration invariant C9 is fully satisfied — no `tag: latest` anywhere in `values.yaml`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 4.1 | cleanuparr + seerr alias bodies | da83254 | charts/arr-stack/values.yaml |
| 4.2 | flaresolverr (no ingress) + jellyfin (no oauth2-proxy) bodies | 5a891ec | charts/arr-stack/values.yaml |

## What Was Done

### Task 4.1: cleanuparr + seerr

Replaced `cleanuparr: {}` and `seerr: {}` with full app-template 5.0.0 value bodies ported verbatim from `my-kluster main:argocd/argocd-apps/{cleanuparr,seerr}-app.yaml`.

**cleanuparr**: tag `latest` → `"2.3.3"` per D-04-PIN-01 (digest sha256:9b8f7a5f...). Port 11011, oauth2-proxy ingress annotations, 1Gi config PVC. Repository: `ghcr.io/cleanuparr/cleanuparr`.

**seerr**: tag `v3.2.0` (already pinned in my-kluster). Port 5055, oauth2-proxy ingress annotations, 2Gi config PVC at `/app/config`. Repository: `ghcr.io/seerr-team/seerr`.

Three deltas vs source:
1. `global.fullnameOverride: cleanuparr` / `seerr` — DNS preservation
2. `# renovate: image=ghcr.io/...` above each `repository:` line
3. cleanuparr tag pinned `"2.3.3"` (was `:latest`)

### Task 4.2: flaresolverr + jellyfin

Replaced `flaresolverr: {}` and `jellyfin: {}` skeletons.

**flaresolverr**: tag `latest` → `"v3.4.6"` per D-04-PIN-01 (digest sha256:7962759d...). Port 8191, `LOG_LEVEL: info` env. **No ingress block** — flaresolverr is consumed only by Prowlarr in-cluster; comment preserved verbatim from my-kluster source. Repository: `ghcr.io/flaresolverr/flaresolverr`.

**jellyfin**: tag `10.11.8` (already pinned). Port 8096, PUID/PGID env. Ingress present with:
- NO `auth-url` / `auth-signin` / `oauth2-proxy` annotations (Jellyfin handles its own auth)
- `nginx.ingress.kubernetes.io/proxy-body-size: "0"` preserved (required for streaming)
- Comment `# Pas d'oauth2-proxy : Jellyfin gère sa propre authentification` preserved verbatim
Two PVCs: 10Gi config + `existingClaim: media-nas-pvc` at `/media`. Repository: `lscr.io/linuxserver/jellyfin`.

## :latest Pin Migration Summary

| App | Plan | Was | Now | Digest |
|-----|------|-----|-----|--------|
| qbittorrent | 04-03 | `:latest` | `5.2.0` | `sha256:2e0148...` |
| cleanuparr | 04-04 | `:latest` | `2.3.3` | `sha256:9b8f7a5f...` |
| flaresolverr | 04-04 | `:latest` | `v3.4.6` | `sha256:7962759d...` |

After Plan 04-04, `! grep -q 'tag: latest' charts/arr-stack/values.yaml` holds — C9 invariant satisfied.

## Verification Results

```
helm lint charts/arr-stack/   → 1 chart(s) linted, 0 chart(s) failed
helm template arr-stack charts/arr-stack/
  → kind: Deployment × 8    (sonarr/radarr/prowlarr/qbittorrent/cleanuparr/seerr/flaresolverr/jellyfin)
  → kind: Service × 8
  → kind: Ingress × 7       (all except flaresolverr)
  → kind: PersistentVolumeClaim × 7
  → kind: ServiceAccount × 10
  → kind: ConfigMap × 2

flaresolverr in template: NO Ingress (PASS)
jellyfin in template: NO auth-url/auth-signin (PASS)
jellyfin in template: HAS proxy-body-size (PASS)
cleanuparr:latest in template: False (PASS)
flaresolverr:latest in template: False (PASS)
tag: latest in values.yaml: False (PASS — C9 satisfied)
fullnameOverride entries: 8 (PASS)
renovate annotations: 8 (PASS)
check-renovate-annotations.sh: OK — all repository: lines have annotations
arrconf/configarr still {}: PASS (for Plan 04-05)
No arr-stack-* prefix regression: PASS
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all 4 alias bodies are fully wired with real image references, persistence, service, and ingress configuration. The remaining 2 aliases (`arrconf`, `configarr`) are intentionally `{}` placeholders awaiting Plan 04-05.

## Threat Flags

None — no new network endpoints or auth paths introduced beyond what existed in the separate ArgoCD Applications being consolidated. Jellyfin's self-auth posture is explicitly preserved (no oauth2-proxy bypass).

## Self-Check

Files exist:
- charts/arr-stack/values.yaml: FOUND (351 lines)

Commits:
- da83254: FOUND (feat(04-04): cleanuparr + seerr alias bodies)
- 5a891ec: FOUND (feat(04-04): flaresolverr + jellyfin alias bodies)

## Self-Check: PASSED
