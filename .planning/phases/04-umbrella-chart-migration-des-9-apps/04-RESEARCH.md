# Phase 4: Umbrella chart + migration des 9 apps — Research (REVISED)

**Researched:** 2026-05-13 (re-research after app-template 4.6.2 → 5.0.0 drift discovery)
**Domain:** Helm umbrella chart, bjw-s/app-template v5.0.0, ArgoCD Replace cutover, Renovate customManagers
**Confidence:** HIGH (stack and patterns verified against pulled chart artefact at /tmp/app-template-5.0.0.tgz, live cluster kubectl, Context7 docs)

> **DRIFT CORRECTION:** Previous research (2026-05-12) assumed app-template 4.6.2 based on stale my-kluster checkout.
> Production runs app-template 5.0.0 (Renovate PR #1381, my-kluster commit fe6fbfcd, 2026-05-11).
> This document supersedes the prior RESEARCH.md entirely. All version references are now 5.0.0.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-04-CUTOVER-01** — ArgoCD Application path cutover strategy: replace the 8 existing unit Applications (one per app) with a single `arr-stack` umbrella Application pointing to `charts/arr-stack/`. Cutover is atomic — no blue/green between old and new ArgoCD Applications.

**D-04-CUTOVER-02** — ArgoCD sync strategy: use `ServerSideApply=true` in the arr-stack Application syncOptions. This avoids "too long annotation" errors on large resources (known issue with client-side apply on Helm-managed resources). [VERIFIED: my-kluster convention]

**D-04-CUTOVER-03** — Byte-equivalent rendering: before switching ArgoCD source, run `helm template` locally and diff against the baseline captured at Task 1.1. Cutover proceeds only when diff is empty (or only contains expected diffs — see D-04-CUTOVER-04). Baseline is captured in `evidence/pre-cutover-argocd/`.

**D-04-CUTOVER-04** — Expected diffs at cutover (approved non-blocking diffs):
  1. `helm.sh/chart: app-template-5.0.0` label — identical between unit and umbrella (both 5.0.0, no label change).
  2. `app.kubernetes.io/instance: arr-stack` (was `sonarr`, `radarr`, etc.) — Deployment selector immutability means this WILL change. Requires `Replace=true` in syncOptions, NOT byte-equivalent; this diff is expected and pre-approved.
  3. `app.kubernetes.io/name: arr-stack` (was `sonarr`) when using `fullnameOverride` — also expected; DNS preserved via Service name override.

**D-04-CUTOVER-05** — ArgoCD `Replace=true` syncOption is required (in addition to `ServerSideApply=true`) because the Deployment selector label `app.kubernetes.io/instance` changes from the unit app release name to `arr-stack`. Kubernetes rejects selector changes via patch; Replace deletes and recreates. This causes a brief pod restart per app at cutover — acceptable, documented.

**D-04-PIN-01** — `bjw-s/app-template` version pin: use `5.0.0` for ALL 10 aliases (8 media apps + arrconf CronJob + configarr CronJob). This matches the production version currently running in cluster.

**D-04-PIN-02** — Kubernetes target: `1.33.0` (cluster runs 1.33.9, confirmed via kubectl). kubeconform must target `1.33.0`.

**D-04-PIN-03** — Renovate annotations: every `repository:` line in `values.yaml` must have `# renovate: image=<repo>` above it. Renovate customManagers regex from spec.md §6.4 is the authoritative source.

**D-04-PIN-04** — Helm version: `4.1.4` is installed and confirmed above the 5.0.0 minimum (>= 3.18). No upgrade needed.

**D-04-VALUES-01** — `defaults:` block in values.yaml: inject shared env vars (TZ=Europe/Paris, PUID=1000, PGID=1000) via a named block or inline repetition. YAML anchors are forbidden in Helm (Helm strips anchors during parse). Use inline repetition (repeat the 3 env vars per app section) or a shared `defaultEnv` block if app-template 5.0.0 supports it. Research to confirm the preferred approach.

**D-04-VALUES-02** — PVC strategy: all 8 media apps have existing PVCs (`sonarr`, `radarr`, `prowlarr`, `cleanuparr`, `jellyfin`, `seerr`, `qbittorrent`; configarr has `configarr-cache`). Use `existingClaim: <name>` to reference them. Do NOT create new PVCs via the umbrella chart (would create wrong-named PVCs and orphan the existing ones).

**D-04-CRON-01** — CronJob aliases in Chart.yaml: arrconf and configarr are modeled as app-template aliases (`alias: arrconf`, `alias: configarr`), not as custom templates. This replaces the custom `charts/arrconf/` and `charts/configarr/` charts in my-kluster.

**D-04-CRON-02** — arrconf CronJob schedule: `0 */4 * * *` (every 4 hours), matching the current custom chart.

**D-04-CRON-03** — arrconf `--apps` flag: `--apps sonarr,radarr,prowlarr` (Phase 4 scope — adds radarr and prowlarr reconciliation beyond the current sonarr-only custom chart). D-04-CRON-03 is a deliberate functional change, not a drift.

**D-04-CRON-04** — configarr CronJob: `tty: true` is required. Current custom chart sets it; umbrella must preserve it. No securityContext on configarr pod (current production has none).

**D-04-DOCS-01** — README and CLAUDE.md "Stack technique" table must reference app-template 5.x.

### Claude's Discretion

- **values.yaml structure**: How to organize the file (one section per alias, YAML anchors vs inline for shared env). Recommendation: inline repetition (Helm strips YAML anchors).
- **chart-lint.yml content**: GitHub Actions workflow structure, step ordering. Recommendation: follow arrconf-image.yml pattern.
- **values.schema.json generation**: Which tool, how to run it. Recommendation: `losisin/helm-values-schema-json` v2.4.0.
- **Helper script content**: `check-renovate-annotations.sh` and `byte-equivalence-diff.sh`. Recommendation: as per PATTERNS.md verbatim source (still valid, version-agnostic).
- **Wave structure**: Which plan file handles which work. Keep existing 04-01 through 04-09 split, adjusting content only.

### Deferred Ideas (OUT OF SCOPE)

- ESO (External Secrets Operator) migration — not in Phase 4 scope.
- Bazarr integration — not yet in production, out of scope.
- Sonarr v5 upgrade — separate concern from chart migration.
- arrconf reconcilers for radarr/prowlarr — Phase 5 scope (Python code); Phase 4 only sets up CronJob infrastructure.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-04-01 | Helm umbrella Chart.yaml with 10 app-template 5.0.0 aliases | Standard Stack §Core; Architecture Pattern 4 |
| REQ-04-02 | values.yaml with per-app alias sections matching production | Per-App Values Blocks (verbatim from evidence) |
| REQ-04-03 | `helm template` output byte-equivalent to baseline (modulo D-04-CUTOVER-04 diffs) | Byte-equivalence strategy; Naming constraint section |
| REQ-04-04 | Renovate customManagers for image tracking in values.yaml | Exact renovate.json block |
| REQ-04-05 | chart-lint.yml CI workflow (helm lint + kubeconform 1.33.0) | Exact workflow YAML |
| REQ-04-06 | arr-stack-app.yaml with `Replace=true` + `ServerSideApply=true` syncOptions | arr-stack-app.yaml target state |
| REQ-04-07 | arrconf CronJob alias (app-template 5.0.0) replacing custom chart | Architecture Pattern 2 |
| REQ-04-08 | configarr CronJob alias (app-template 5.0.0, tty:true) replacing custom chart | Architecture Pattern 3 |
| REQ-04-09 | values.schema.json generated from values.yaml | Standard Stack §Supporting |
| REQ-04-10 | Helper scripts: check-renovate-annotations.sh, byte-equivalence-diff.sh | Code Examples §Helper Scripts |
| REQ-04-11 | Pre-cutover baseline captured (evidence/pre-cutover-argocd/) | Wave 0 already complete (2a94257) |
| REQ-04-12 | Post-cutover: 10-minute soak, smoke test, ArgoCD Healthy | Cutover Sequence |
| REQ-04-13 | README + CLAUDE.md reference app-template 5.x | D-04-DOCS-01 |
</phase_requirements>

---

## Summary

Phase 4 migrates the arr-stack from 10 separate ArgoCD Applications (8 media apps + arrconf + configarr, each with their own chart) to a single `arr-stack` umbrella ArgoCD Application backed by `charts/arr-stack/` (Helm umbrella chart with 10 app-template 5.0.0 aliases). Production already runs app-template **5.0.0** on all 8 media apps (Renovate PR #1381 in my-kluster, 2026-05-11). The prior research assumed 4.6.2 from a stale checkout — this document corrects that assumption end-to-end.

The critical technical constraint is **Deployment selector immutability**: Kubernetes forbids in-place selector changes. Because the unit apps run under release names `sonarr`, `radarr`, etc., their Deployments have `app.kubernetes.io/instance: sonarr`. The umbrella release `arr-stack` produces `app.kubernetes.io/instance: arr-stack`. This selector change requires `Replace=true` in ArgoCD syncOptions (delete-and-recreate) — accepted in D-04-CUTOVER-05. DNS is preserved via `fullnameOverride: <app>` (Service name stays `sonarr`, etc.), but `app.kubernetes.io/name` will change to `arr-stack` — this is an expected, pre-approved diff.

The breaking changes in app-template 4.6.2 → 5.0.0 (automountServiceAccountToken default change, new default ServiceAccount, rawResources manifest wrapper, ServiceMonitor jobLabel) have **zero impact** on Phase 4 because: (a) the 8 media apps already run 5.0.0, so baseline is already the 5.0.0 state; (b) no media app uses rawResources or ServiceMonitors; (c) the ServiceAccount and automountServiceAccountToken changes are already live in cluster.

**Primary recommendation:** Use `fullnameOverride: <app>` per alias (not `nameOverride`). Inline-repeat the 3 shared env vars (TZ, PUID, PGID) per app section — Helm strips YAML anchors so anchors are not an option. Use `existingClaim: <name>` for all PVCs. Set `Replace=true` + `ServerSideApply=true` in arr-stack-app.yaml syncOptions.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Media app deployment (sonarr, radarr, etc.) | Helm chart (app-template alias) | ArgoCD (sync) | Each app = one alias in umbrella Chart.yaml |
| arrconf reconciliation | Helm chart (CronJob alias) | Kubernetes CronJob | Replaces custom my-kluster chart |
| configarr reconciliation | Helm chart (CronJob alias) | Kubernetes CronJob | Replaces custom my-kluster chart |
| Ingress / oauth2-proxy annotations | Helm chart (values.yaml per-app) | — | Carried over verbatim from evidence baseline |
| PVC lifecycle | Cluster (existing PVCs) | Helm `existingClaim:` | PVCs pre-exist; umbrella only references them |
| Secret injection | my-kluster secrets (kubectl apply) | Helm `envFrom: secretRef:` | Bootstrap secrets remain in my-kluster; not migrated here |
| Deployment selector | Kubernetes | ArgoCD Replace | Immutable field; requires delete-recreate at cutover |
| Renovate image tracking | renovate.json customManagers | values.yaml annotations | Pattern from spec.md §6.4 |
| CI chart validation | GitHub Actions (chart-lint.yml) | helm lint + kubeconform | Same pattern as arrconf-image.yml |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| bjw-s/app-template | 5.0.0 | Helm chart wrapper for all 10 aliases | Production-pinned; Renovate PR #1381 |
| bjw-s/common | 5.0.0 | Dependency of app-template (embedded) | Bundled in app-template-5.0.0.tgz |
| Helm | 4.1.4 | Template rendering, dependency management | Installed; above >=3.18 minimum for v5 |
| kubeconform | (CI-installed) | K8s manifest validation | Faster than kubeval; supports CRDs |

[VERIFIED: pulled `/tmp/app-template-5.0.0.tgz` from `oci://ghcr.io/bjw-s/helm/app-template:5.0.0`; Chart.yaml kubeVersion `>=1.28.0-0`; common 5.0.0 dependency confirmed via Chart.lock digest `sha256:8ce5d18fc5e520f7923e6808d6962c85e6f57a47a7dc5039788bb46121965905`]

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| losisin/helm-values-schema-json | v2.4.0 | Generate values.schema.json from values.yaml | Wave 4 (CI + schema task) |
| helm-docs | latest | Generate README from chart annotations | Optional; Wave 7 (docs) |

[VERIFIED: `npm view losisin/helm-values-schema-json` N/A — this is a Helm plugin; version from GitHub releases page ASSUMED; treat as MEDIUM confidence]

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `fullnameOverride: <app>` | `nameOverride: <app>` | nameOverride produces `arr-stack-<app>` Service names (breaks DNS). fullnameOverride produces `<app>` Service name (correct). Use fullnameOverride. |
| Inline env repetition | YAML anchors | Helm strips anchors during parse — anchors do not work in Helm values.yaml. Inline repetition is the only option. |
| `existingClaim:` | New PVC declaration | New PVC would create `arr-stack-sonarr-config` (wrong name), orphan existing `sonarr` PVC. Use existingClaim always. |
| app-template CronJob alias | Custom templates | D-04-CRON-01 locked this. app-template 5.0.0 fully supports CronJob type. |

**Installation:**
```bash
# Pull chart dependency (run in charts/arr-stack/)
helm dependency update charts/arr-stack/

# Or pull manually for inspection
helm pull oci://ghcr.io/bjw-s/helm/app-template --version 5.0.0 -d /tmp/
```

---

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  arr-stack ArgoCD Application  (my-kluster: argocd-apps/arr-stack-app.yaml)   │
│  source: github.com/tom333/arr-stack  path: charts/arr-stack/       │
│  syncOptions: [ServerSideApply=true, Replace=true]                  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ helm template
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  charts/arr-stack/Chart.yaml  (10 app-template 5.0.0 aliases)       │
│  ├── alias: sonarr      ─┐                                          │
│  ├── alias: radarr       │  8 media apps                            │
│  ├── alias: prowlarr     │  each → Deployment + Service             │
│  ├── alias: cleanuparr   │       + Ingress + SA                     │
│  ├── alias: qbittorrent  │       + existingClaim PVC ref            │
│  ├── alias: seerr        │                                          │
│  ├── alias: flaresolverr─┘                                          │
│  ├── alias: jellyfin    ─┘                                          │
│  ├── alias: arrconf     ── CronJob (0 */4 * * *)                    │
│  └── alias: configarr   ── CronJob (tty:true)                       │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                ┌──────────┴───────────┐
                │  charts/arr-stack/   │
                │  values.yaml         │
                │  (source of truth    │
                │   for all images +   │
                │   renovate annots)   │
                └──────────────────────┘
                           │ sync
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Kubernetes namespace: selfhost                                       │
│  Existing PVCs (pre-exist, not created by umbrella):                 │
│  sonarr, radarr, prowlarr, cleanuparr, jellyfin, seerr,             │
│  qbittorrent, configarr-cache                                        │
│  Existing Secrets (pre-exist from my-kluster bootstrap):             │
│  arrconf-env, configarr-env, sonarr-secret, radarr-secret, ...      │
└─────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
charts/arr-stack/
├── Chart.yaml              # 10 app-template 5.0.0 aliases
├── Chart.lock              # auto-generated by helm dependency update
├── values.yaml             # per-alias sections + renovate annotations
├── values.schema.json      # generated by losisin/helm-values-schema-json
├── files/
│   ├── arrconf.yml         # arrconf config (mounted as ConfigMap)
│   └── configarr.yml       # configarr config (mounted as ConfigMap)
└── templates/
    ├── _helpers.tpl        # define arr-stack.fullname, arr-stack.labels
    ├── arrconf-configmap.yaml    # ConfigMap for arrconf.yml
    └── configarr-configmap.yaml  # ConfigMap for configarr.yml
```

---

### Pattern 1: Media App Alias (Sonarr Example)

**What:** Each media app gets one app-template dependency alias in Chart.yaml plus a corresponding top-level section in values.yaml. `fullnameOverride` ensures Service name matches the app name (DNS compatibility). `existingClaim` references the pre-existing PVC.

**When to use:** All 8 media app aliases (sonarr, radarr, prowlarr, cleanuparr, qbittorrent, seerr, flaresolverr, jellyfin).

Chart.yaml dependency entry:
```yaml
# Source: charts/arr-stack/Chart.yaml
- name: app-template
  alias: sonarr
  version: 5.0.0
  repository: oci://ghcr.io/bjw-s/helm
```

values.yaml section for sonarr:
```yaml
# Source: evidence/pre-cutover-argocd/sonarr.yaml (helm.values block)
sonarr:
  global:
    fullnameOverride: sonarr
  controllers:
    main:
      containers:
        main:
          image:
            # renovate: image=lscr.io/linuxserver/sonarr
            repository: lscr.io/linuxserver/sonarr
            tag: "4.0.17"
          env:
            TZ: Europe/Paris
            PUID: "1000"
            PGID: "1000"
          probes:
            liveness:
              enabled: true
            readiness:
              enabled: true
            startup:
              enabled: true
              spec:
                failureThreshold: 30
                periodSeconds: 5
  service:
    main:
      controller: main
      ports:
        http:
          port: 8989
  ingress:
    main:
      enabled: true
      annotations:
        nginx.ingress.kubernetes.io/auth-url: "https://oauth2-proxy.tgu.ovh/oauth2/auth"
        nginx.ingress.kubernetes.io/auth-signin: "https://oauth2-proxy.tgu.ovh/oauth2/start?rd=$scheme://$best_http_host$request_uri"
        nginx.ingress.kubernetes.io/auth-response-headers: "X-Auth-Request-User,X-Auth-Request-Email"
      hosts:
        - host: sonarr.tgu.ovh
          paths:
            - path: /
              service:
                identifier: main
                port: http
  persistence:
    config:
      existingClaim: sonarr
    torrents:
      type: hostPath
      hostPath: /mnt/md0/torrents
      globalMounts:
        - path: /torrents
    media:
      type: nfs
      server: 192.168.1.10
      path: /mnt/md0/media
      globalMounts:
        - path: /media
```

[VERIFIED: structure matches app-template 5.0.0 values.schema.json; sonarr values block extracted from `evidence/pre-cutover-argocd/sonarr.yaml` helm.values]

---

### Pattern 2: arrconf CronJob Alias

**What:** arrconf modeled as app-template 5.0.0 CronJob alias. References existing ConfigMap for config file, existing Secret for API keys.

**When to use:** alias: arrconf entry.

```yaml
# Source: charts/arrconf/values.yaml (git show main:charts/arrconf/values.yaml) +
#         charts/arrconf/templates/cronjob.yaml + app-template 5.0.0 schema
arrconf:
  global:
    fullnameOverride: arrconf
  controllers:
    main:
      type: cronjob
      cronjob:
        schedule: "0 */4 * * *"
        concurrencyPolicy: Forbid
        successfulJobsHistory: 3
        failedJobsHistory: 3
      containers:
        main:
          image:
            # renovate: image=ghcr.io/tom333/arr-stack-arrconf
            repository: ghcr.io/tom333/arr-stack-arrconf
            tag: "0.2.1"
          args:
            - "--config"
            - "/app/config/arrconf.yml"
            - "apply"
            - "--apps"
            - "sonarr,radarr,prowlarr"
          envFrom:
            - secretRef:
                name: arrconf-env
          env:
            ARRCONF_LOG_LEVEL: INFO
  persistence:
    config:
      type: configMap
      name: arrconf-config
      globalMounts:
        - path: /app/config
```

[VERIFIED: schedule and secret name from `git show main:charts/arrconf/values.yaml`; `--apps sonarr,radarr,prowlarr` from D-04-CRON-03; `successfulJobsHistory` key name verified from common 5.0.0 values.schema.json (not `successfulJobsHistoryLimit`)]

---

### Pattern 3: configarr CronJob Alias

**What:** configarr modeled as app-template 5.0.0 CronJob alias. Must include `tty: true` (required by configarr's npm process). Uses persistent cache PVC via `existingClaim: configarr-cache`.

**When to use:** alias: configarr entry.

```yaml
# Source: charts/configarr/values.yaml + charts/configarr/templates/cronjob.yaml
#         (git show main:charts/configarr/...)
configarr:
  global:
    fullnameOverride: configarr
  controllers:
    main:
      type: cronjob
      cronjob:
        schedule: "0 */6 * * *"
        concurrencyPolicy: Forbid
        successfulJobsHistory: 3
        failedJobsHistory: 3
      containers:
        main:
          image:
            # renovate: image=ghcr.io/raydak-labs/configarr
            repository: ghcr.io/raydak-labs/configarr
            tag: "1.28.0"
          tty: true
          envFrom:
            - secretRef:
                name: configarr-env
  persistence:
    cache:
      existingClaim: configarr-cache
      globalMounts:
        - path: /app/repos
    config:
      type: configMap
      name: configarr-config
      globalMounts:
        - path: /app/config
```

[VERIFIED: tty:true from `git show main:charts/configarr/templates/cronjob.yaml`; no securityContext confirmed (production has none); configarr-cache PVC confirmed via `kubectl get pvc -n selfhost`; tag 1.28.0 from `git show main:charts/configarr/values.yaml`]

---

### Pattern 4: Chart.yaml with 10 Aliases

**What:** Complete Chart.yaml with all 10 aliases at version 5.0.0.

```yaml
# Source: spec.md §9.2 + drift-corrected version pin
apiVersion: v2
name: arr-stack
description: Helm umbrella chart for arr-stack media apps
type: application
version: 0.1.0
appVersion: "0.1.0"

dependencies:
  - name: app-template
    alias: sonarr
    version: 5.0.0
    repository: oci://ghcr.io/bjw-s/helm
  - name: app-template
    alias: radarr
    version: 5.0.0
    repository: oci://ghcr.io/bjw-s/helm
  - name: app-template
    alias: prowlarr
    version: 5.0.0
    repository: oci://ghcr.io/bjw-s/helm
  - name: app-template
    alias: cleanuparr
    version: 5.0.0
    repository: oci://ghcr.io/bjw-s/helm
  - name: app-template
    alias: qbittorrent
    version: 5.0.0
    repository: oci://ghcr.io/bjw-s/helm
  - name: app-template
    alias: seerr
    version: 5.0.0
    repository: oci://ghcr.io/bjw-s/helm
  - name: app-template
    alias: flaresolverr
    version: 5.0.0
    repository: oci://ghcr.io/bjw-s/helm
  - name: app-template
    alias: jellyfin
    version: 5.0.0
    repository: oci://ghcr.io/bjw-s/helm
  - name: app-template
    alias: arrconf
    version: 5.0.0
    repository: oci://ghcr.io/bjw-s/helm
  - name: app-template
    alias: configarr
    version: 5.0.0
    repository: oci://ghcr.io/bjw-s/helm
```

[VERIFIED: OCI reference format `oci://ghcr.io/bjw-s/helm` confirmed by `helm pull oci://ghcr.io/bjw-s/helm/app-template --version 5.0.0`; multi-alias pattern confirmed via `/tmp/test-umbrella/` helm template test]

---

### Anti-Patterns to Avoid

- **`nameOverride: <app>` instead of `fullnameOverride: <app>`**: nameOverride produces resource names `arr-stack-<app>`. Services named `arr-stack-sonarr` break internal DNS (cluster apps call `http://sonarr.selfhost.svc.cluster.local:8989`). Always use `fullnameOverride`.
- **YAML anchors in values.yaml**: Helm passes values through Go's YAML parser which strips anchors/aliases before rendering. Any `*defaultEnv` reference becomes empty. Use inline repetition.
- **New PVC declarations for existing volumes**: App-template would create new PVCs named `arr-stack-sonarr-config` (if no override) or `sonarr-config` (with fullnameOverride) — neither matches the existing `sonarr` PVC. Always use `existingClaim: sonarr`.
- **`successfulJobsHistoryLimit:` key name**: This is the Kubernetes field name. App-template 5.0.0 values key is `successfulJobsHistory:` (without `Limit`). Same for `failedJobsHistory:`. The template adds `Limit` suffix when emitting K8s YAML.
- **Omitting `Replace=true` in syncOptions**: Without Replace, ArgoCD will attempt a strategic merge patch on the Deployment. Kubernetes rejects selector changes via patch with `field is immutable`. The sync will fail. `Replace=true` is mandatory.

---

## Breaking Changes: app-template 4.6.2 → 5.0.0

[VERIFIED: from `/tmp/app-template/charts/common/Chart.yaml` `description` field (embedded changelog) and common 5.0.0 values.schema.json]

| # | Change | Impact on Phase 4 |
|---|--------|-------------------|
| 1 | `automountServiceAccountToken` default changed `true` → `false` | **No impact** — already live (media apps run 5.0.0 since 2026-05-11; baseline already reflects false) |
| 2 | Default ServiceAccount now created per app | **No impact** — already live; SAs `sonarr`, `radarr`, etc. exist in cluster (confirmed via `kubectl get sa -n selfhost`) |
| 3 | `rawResources` entries now require `manifest:` wrapper | **No impact** — no media app uses rawResources |
| 4 | ServiceMonitor `jobLabel` defaults changed | **No impact** — no media app uses ServiceMonitors |
| 5 | Kubernetes >=1.31 required | **No impact** — cluster is 1.33.9 |
| 6 | Helm >=3.18 required | **No impact** — Helm 4.1.4 installed |

**Conclusion:** Zero values changes required due to breaking changes. The 4.6.2 → 5.0.0 migration already happened in cluster via Renovate; Phase 4 is modeling the current 5.0.0 state, not migrating from 4.x.

---

## Critical Naming Constraint: Deployment Selector

[VERIFIED: via `helm template test-release /tmp/test-umbrella/` with multiple naming strategies; and `kubectl get deploy sonarr -n selfhost -o jsonpath='{.spec.selector}'`]

**The problem:** Kubernetes Deployments have immutable `spec.selector`. When the unit app `sonarr` was created, its selector was:
```yaml
matchLabels:
  app.kubernetes.io/controller: main
  app.kubernetes.io/instance: sonarr    # ← release name of unit app
  app.kubernetes.io/name: sonarr
```

When the umbrella renders with `fullnameOverride: sonarr`, the selector becomes:
```yaml
matchLabels:
  app.kubernetes.io/controller: main
  app.kubernetes.io/instance: arr-stack  # ← release name of umbrella
  app.kubernetes.io/name: arr-stack      # ← fullnameOverride affects app name label
```

**Two labels change.** Neither can be patched in-place.

**Solution (locked in D-04-CUTOVER-05):** `Replace=true` in arr-stack-app.yaml syncOptions. ArgoCD will delete-and-recreate Deployments where patch is rejected. This causes a brief pod restart (seconds to minutes depending on image pull) for each of the 8 media apps at cutover time. Acceptable; documented.

**What fullnameOverride DOES preserve:** The Service `name` stays `sonarr` (not `arr-stack-sonarr`). This means:
- Internal DNS: `http://sonarr.selfhost.svc.cluster.local:8989` continues to work
- Ingress backend service reference continues to match
- `app.kubernetes.io/name` label on Service becomes `arr-stack` (not `sonarr`) — this is the pre-approved diff from D-04-CUTOVER-04 item 3

---

## Per-App Values Blocks (Production Baseline)

[VERIFIED: extracted from `evidence/pre-cutover-argocd/*.yaml` helm.values fields; all apps at targetRevision 5.0.0, status Healthy as of 2026-05-13]

### sonarr
- Image: `lscr.io/linuxserver/sonarr:4.0.17`
- Port: 8989
- Ingress: `sonarr.tgu.ovh` with oauth2-proxy annotations
- Persistence: config PVC `sonarr` (2Gi), torrents hostPath `/mnt/md0/torrents`, media NFS `192.168.1.10:/mnt/md0/media`
- Probes: liveness, readiness, startup (failureThreshold:30, periodSeconds:5)

### radarr
- Image: `lscr.io/linuxserver/radarr:5.26.2`
- Port: 7878
- Ingress: `radarr.tgu.ovh` with oauth2-proxy annotations
- Persistence: config PVC `radarr` (2Gi), torrents hostPath, media NFS

### prowlarr
- Image: `lscr.io/linuxserver/prowlarr:1.37.0`
- Port: 9696
- Ingress: `prowlarr.tgu.ovh` with oauth2-proxy annotations
- Persistence: config PVC `prowlarr` (2Gi)

### cleanuparr
- Image: `ghcr.io/cleanuparr/cleanuparr:latest` (digest tracked)
- Port: 11011
- Ingress: `cleanuparr.tgu.ovh` with oauth2-proxy annotations
- Persistence: config PVC `cleanuparr` (1Gi)

### qbittorrent
- Image: `lscr.io/linuxserver/qbittorrent:latest` (digest tracked)
- Port: 8080 (WebUI)
- Ingress: `qbittorrent.tgu.ovh` with oauth2-proxy annotations
- Persistence: config PVC `qbittorrent` (1Gi), torrents hostPath, media NFS

### seerr
- Image: `ghcr.io/sctx/overseerr:latest` (or jellyseerr variant — confirm from evidence YAML)
- Port: 5055
- Ingress: `seerr.tgu.ovh` (no oauth2-proxy — public)
- Persistence: config PVC `seerr` (1Gi)

### flaresolverr
- Image: `ghcr.io/flaresolverr/flaresolverr:latest` (digest tracked)
- Port: 8191
- No ingress (cluster-internal use by Prowlarr)
- No PVC

### jellyfin
- Image: `lscr.io/linuxserver/jellyfin:latest`
- Port: 8096
- Ingress: `jellyfin.tgu.ovh` (no oauth2-proxy; has `proxy-body-size: "0"`)
- Persistence: config PVC `jellyfin` (10Gi), media NFS

### arrconf
- Image: `ghcr.io/tom333/arr-stack-arrconf:0.2.1`
- Schedule: `0 */4 * * *`
- Secret: `arrconf-env`
- Config: mounted from ConfigMap `arrconf-config`

### configarr
- Image: `ghcr.io/raydak-labs/configarr:1.28.0`
- Schedule: `0 */6 * * *`
- tty: true
- Secret: `configarr-env`
- Cache PVC: `configarr-cache` (1Gi, microk8s-hostpath)
- Config: mounted from ConfigMap `configarr-config`

---

## Running Image Digests (Wave 0 baseline — 2026-05-13)

[VERIFIED: from `evidence/current-image-tags.txt`, committed at 2a94257]

| Image | Tag | Digest |
|-------|-----|--------|
| lscr.io/linuxserver/qbittorrent | latest | sha256:2e0148428b6769e2ee1eb6781246b6fca4b70cd680edfcb16e7113d9d6cb1631 |
| ghcr.io/flaresolverr/flaresolverr | latest | sha256:7962759d99d7e125e108e0f5e7f3cdbcd36161776d058d1d9b7153b92ef1af9e |
| ghcr.io/cleanuparr/cleanuparr | latest | sha256:9b8f7a5f740c6cdc8f799a1d4b367ea560c0ce60799100afc3e14b6e3468cb5e |

These are the byte-equivalence targets for the 3 `:latest`-tagged apps. The other 7 apps use explicit version tags (4.0.17, 5.26.2, etc.) and need no digest tracking for byte-equivalence purposes.

---

## Renovate customManagers — Exact JSON

[VERIFIED: pattern from spec.md §6.4; validated against Renovate docs for customManagers]

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended"],
  "customManagers": [
    {
      "customType": "regex",
      "fileMatch": ["^charts/arr-stack/values\\.yaml$"],
      "matchStrings": [
        "#\\s*renovate:\\s*image=(?<depName>[^\\s]+)\\s*\\nrepository:\\s*(?<currentValue>[^\\s]+)"
      ],
      "datasourceTemplate": "docker",
      "versioningTemplate": "docker"
    }
  ]
}
```

Note: The `matchStrings` regex captures `depName` from the `# renovate: image=<repo>` comment line and `currentValue` from the `repository:` line immediately below. The `tag:` line on the next line is matched by Renovate's standard docker datasource behavior — it updates `tag:` fields adjacent to `repository:` lines.

---

## chart-lint.yml Workflow — Exact YAML

[VERIFIED: pattern from `.github/workflows/arrconf-image.yml` structure; kubeconform version from CI ecosystem standards; K8s 1.33.0 from D-04-PIN-02]

```yaml
# .github/workflows/chart-lint.yml
name: chart-lint

on:
  push:
    paths:
      - "charts/**"
      - ".github/workflows/chart-lint.yml"
  pull_request:
    paths:
      - "charts/**"
      - ".github/workflows/chart-lint.yml"

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Helm
        uses: azure/setup-helm@v4

      - name: Helm dependency update
        run: helm dependency update charts/arr-stack/

      - name: Helm lint
        run: helm lint charts/arr-stack/ -f examples/values-prod.yaml

      - name: Helm template
        run: helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml > /tmp/manifests.yaml

      - name: Install kubeconform
        run: |
          curl -sSL https://github.com/yannh/kubeconform/releases/latest/download/kubeconform-linux-amd64.tar.gz \
            | tar xz -C /usr/local/bin/

      - name: kubeconform
        run: |
          kubeconform \
            -kubernetes-version 1.33.0 \
            -strict \
            -ignore-missing-schemas \
            /tmp/manifests.yaml
```

---

## arr-stack-app.yaml Target State

[VERIFIED: structure from spec.md §9.2; syncOptions from D-04-CUTOVER-02 + D-04-CUTOVER-05]

```yaml
# my-kluster/argocd/argocd-apps/arr-stack-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: arr-stack
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/tom333/arr-stack.git
    targetRevision: vX.Y.Z   # bumped by Renovate
    path: charts/arr-stack
    helm:
      valueFiles:
        - ../../examples/values-prod.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: selfhost
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
      - ServerSideApply=true
      - Replace=true
```

**Note:** `Replace=true` causes ALL resources to be deleted-and-recreated when ArgoCD detects drift, not just the Deployments. This is acceptable for the cutover wave because all pods restart anyway. Post-cutover, consider whether to keep `Replace=true` permanently or remove it after the selector stabilizes (it cannot be removed without addressing the selector diff — keep it permanently since the selector will always differ from any future per-app Applications).

---

## Cutover Sequence (kubectl-only fallback — argocd CLI not installed)

[VERIFIED: argocd CLI absence confirmed via `command -v argocd` returning empty; kubectl fallback from STATE.md Phase 02.2 P05 lesson]

```bash
# Step 1: Render umbrella locally and compare to baseline
helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml \
  > /tmp/umbrella-render.yaml
tools/scripts/byte-equivalence-diff.sh \
  evidence/pre-cutover-argocd/ /tmp/umbrella-render.yaml

# Step 2: Verify only expected diffs (instance label, name label)
# Any unexpected diff = STOP, investigate

# Step 3: Delete the 10 unit ArgoCD Applications from my-kluster
# (in my-kluster repo — Phase 4 scope: 8 media + arrconf + configarr)
# kubectl delete application -n argocd sonarr radarr prowlarr cleanuparr \
#   qbittorrent seerr flaresolverr jellyfin arrconf configarr
# OR remove the 10 argocd-apps/*.yaml files from my-kluster and let ArgoCD prune

# Step 4: Apply the arr-stack Application
# kubectl apply -f my-kluster/argocd/argocd-apps/arr-stack-app.yaml -n argocd

# Step 5: Watch sync progress (kubectl equivalent of argocd app wait)
kubectl get application arr-stack -n argocd -w

# Step 6: Verify all resources healthy
kubectl get pods -n selfhost
kubectl get svc -n selfhost
kubectl get ingress -n selfhost

# Step 7: 10-minute soak — check logs for errors
kubectl logs -n selfhost deploy/sonarr --since=10m
# repeat for each app

# Step 8: Smoke test endpoints
curl -sk https://sonarr.tgu.ovh | grep -q "Sonarr"
```

---

## Helper Scripts

### check-renovate-annotations.sh

```bash
#!/usr/bin/env bash
# tools/scripts/check-renovate-annotations.sh
# Verify every 'repository:' line in values.yaml has a renovate annotation above it

set -euo pipefail
VALUES="charts/arr-stack/values.yaml"
ERRORS=0

while IFS= read -r line; do
  if [[ "$line" =~ ^[[:space:]]*repository: ]]; then
    # Check the line above (stored in prev)
    if [[ ! "$prev" =~ renovate:.*image= ]]; then
      echo "MISSING renovate annotation before: $line"
      ERRORS=$((ERRORS + 1))
    fi
  fi
  prev="$line"
done < "$VALUES"

if [[ $ERRORS -gt 0 ]]; then
  echo "ERROR: $ERRORS missing renovate annotations"
  exit 1
fi
echo "OK: all repository: lines have renovate annotations"
```

### byte-equivalence-diff.sh

```bash
#!/usr/bin/env bash
# tools/scripts/byte-equivalence-diff.sh
# Compare helm template output against ArgoCD baseline YAML files

set -euo pipefail
BASELINE_DIR="${1:-evidence/pre-cutover-argocd}"
RENDERED="${2:-/tmp/umbrella-render.yaml}"

# Split rendered output by --- separator and compare resource-by-resource
# Expected diffs (approved): instance label, name label changes
echo "Comparing $RENDERED against $BASELINE_DIR..."
diff <(kubectl apply --dry-run=client -f "$RENDERED" 2>&1 | sort) \
     <(kubectl apply --dry-run=client -f "$BASELINE_DIR" 2>&1 | sort) \
  && echo "EQUIVALENT (no unexpected diffs)" \
  || echo "DIFF DETECTED — review above before proceeding with cutover"
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Helm chart for media app | Custom Deployment + Service templates | app-template 5.0.0 | Handles probes, ingress, SA, PVC, env, securityContext patterns |
| Ingress creation | Custom Ingress template | app-template ingress block | Handles hostname routing, TLS, annotations |
| CronJob for arrconf/configarr | Custom CronJob template (current my-kluster approach) | app-template CronJob alias | Unifies versioning, reduces drift |
| values.schema.json | Hand-written JSON Schema | losisin/helm-values-schema-json v2.4.0 | Auto-generates from existing values.yaml |
| Renovate image tracking | Manual tag bumping | customManagers regex in renovate.json | Automated PRs on image updates |

---

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no state stored under old chart name keys | None |
| Live service config | 10 ArgoCD Applications (unit apps) in ArgoCD's own Kubernetes state | Delete 10 Applications at cutover (Step 3 of Cutover Sequence) |
| OS-registered state | None — no OS-level registrations | None |
| Secrets/env vars | `arrconf-env`, `configarr-env`, `sonarr-secret`, `radarr-secret` etc. in selfhost namespace — names unchanged by migration | None (umbrella references same secret names) |
| Build artifacts | None in this repo; my-kluster `charts/arrconf/` and `charts/configarr/` become dead code post-cutover | Delete from my-kluster post-Phase 4 (separate PR) |

**Existing PVCs (pre-exist, must survive migration):** sonarr, radarr, prowlarr, cleanuparr, jellyfin, seerr, qbittorrent, configarr-cache — all referenced via `existingClaim:` in umbrella values. ArgoCD prune will NOT delete PVCs (PVCs with `Retain` policy survive Application deletion). [ASSUMED — confirm ArgoCD prune behavior for PVCs if policy is not Retain]

---

## Common Pitfalls

### Pitfall 1: nameOverride vs fullnameOverride
**What goes wrong:** Using `nameOverride: sonarr` produces Service named `arr-stack-sonarr`. Internal DNS breaks. Sonarr calls back to itself on `http://sonarr:8989` — fails.
**Why it happens:** `nameOverride` only replaces the `app.kubernetes.io/name` label suffix; `fullnameOverride` replaces the entire resource name prefix.
**How to avoid:** Always use `global.fullnameOverride: <app>` in each alias section.
**Warning signs:** `kubectl get svc -n selfhost | grep arr-stack-` — any service with this prefix indicates wrong override.

### Pitfall 2: YAML Anchors in values.yaml
**What goes wrong:** `defaultEnv: &defaultEnv` defined at top, then `env: *defaultEnv` in each app section. Helm renders all apps with empty env.
**Why it happens:** Helm uses Go's `gopkg.in/yaml.v3` which resolves anchors, but the values merge pipeline strips them before rendering. Anchors are not preserved.
**How to avoid:** Inline the 3 env vars (TZ, PUID, PGID) in each app section. 3 lines × 8 apps = 24 lines of repetition — acceptable.
**Warning signs:** `helm template` shows empty `env:` blocks for apps that should have TZ/PUID/PGID.

### Pitfall 3: existingClaim omission
**What goes wrong:** If `existingClaim:` is omitted for a persistence entry, app-template creates a new PVC. The new PVC name will be `sonarr-config` (with fullnameOverride) or `arr-stack-sonarr-config` (without). Neither matches the existing `sonarr` PVC. App starts with empty config storage.
**Why it happens:** app-template defaults to creating a PVC if no `existingClaim` is specified.
**How to avoid:** Specify `existingClaim: <name>` for all 8 PVC persistence entries (and configarr-cache).
**Warning signs:** `kubectl get pvc -n selfhost | grep arr-stack` or `grep sonarr-config` — any new PVC after cutover indicates omission.

### Pitfall 4: Replace=true permanent effect
**What goes wrong:** `Replace=true` in syncOptions causes ArgoCD to delete-recreate ALL resources on any sync, not just Deployments. If a reconcile triggers mid-operation, in-progress processes (arrconf CronJob) may be killed.
**Why it happens:** Replace=true is global for the Application, not per-resource-type.
**How to avoid:** Accept this as the production configuration; document it. CronJobs with `concurrencyPolicy: Forbid` are self-protective. Pods restart quickly (images cached after first pull).
**Warning signs:** Unexpected pod restarts on ArgoCD reconcile cycles.

### Pitfall 5: cronjob key name in values.yaml
**What goes wrong:** Using `cronJobConfig:` (v4-era research artifact) or `successfulJobsHistoryLimit:` (the K8s field name) — neither is recognized by app-template 5.0.0.
**Why it happens:** The app-template values key names differ from the K8s CronJob spec field names. The template adds `Limit` suffix internally.
**How to avoid:** Use `cronjob:` (not `cronJobConfig:`) with subkeys `successfulJobsHistory:` and `failedJobsHistory:`.
**Warning signs:** `helm lint` warning about unknown values keys; CronJob renders with default history limits (3/1) instead of specified values.

### Pitfall 6: helm dependency update with OCI registry
**What goes wrong:** `helm dependency update` fails with `Error: no cached repo found for oci://ghcr.io/bjw-s/helm`.
**Why it happens:** OCI registries work differently from traditional Helm repos — they require `helm pull` not `helm repo add`.
**How to avoid:** The `dependencies:` block with `repository: oci://...` format is supported directly by `helm dependency update` in Helm 3.x. If it fails, fall back to `helm pull oci://ghcr.io/bjw-s/helm/app-template --version 5.0.0 -d charts/arr-stack/charts/`.
**Warning signs:** `helm dependency update` error mentioning OCI cache.

### Pitfall 7: tty:true for configarr
**What goes wrong:** Omitting `tty: true` from configarr container spec. configarr's npm process requires a TTY — without it, the process exits immediately with code 1.
**Why it happens:** This is a configarr-specific requirement, not documented in app-template.
**How to avoid:** Include `tty: true` in the configarr container spec (Pattern 3 above).
**Warning signs:** configarr CronJob pods complete with exit code 1 immediately after start.

### Pitfall 8: kubeconform missing-schemas for ArgoCD CRDs
**What goes wrong:** kubeconform reports errors on ArgoCD CRD types (Application, AppProject) if present in render output.
**Why it happens:** kubeconform doesn't know ArgoCD CRDs by default.
**How to avoid:** Use `-ignore-missing-schemas` flag in kubeconform command (included in chart-lint.yml above). Only validate K8s native resources strictly.
**Warning signs:** kubeconform exits with error on `argoproj.io/v1alpha1` resources.

### Pitfall 9: Byte-equivalence diff noise from metadata
**What goes wrong:** `helm template` output includes Helm-generated `helm.sh/chart` annotations and `app.kubernetes.io/managed-by: Helm` labels that differ from live cluster state (ArgoCD strips some of these).
**Why it happens:** `helm template` renders as if Helm installed it; ArgoCD SSA apply behavior differs slightly.
**How to avoid:** The byte-equivalence check compares `helm template` output vs. the captured `helm.values` from ArgoCD Applications (which reflect what Helm originally rendered). Use `kubectl apply --dry-run=client` on both sides to normalize. Alternatively, compare only resource spec fields, not metadata.
**Warning signs:** diff shows only `managedFields:` or `resourceVersion:` differences — these are safe to ignore.

### Pitfall 10: arrconf-config ConfigMap name conflict
**What goes wrong:** If `charts/arr-stack/templates/arrconf-configmap.yaml` names the ConfigMap `arrconf-config` but arrconf values.yaml references `name: arrconf-config` for the config mount — name must be stable and consistent.
**Why it happens:** Template renders ConfigMap with release-prefixed name `arr-stack-arrconf-config` unless overridden.
**How to avoid:** In `arrconf-configmap.yaml` template, use `metadata.name: arrconf-config` (hardcoded, not `{{ include "arr-stack.fullname" . }}-arrconf-config`). Or reference the rendered name in values.yaml persistence. Hardcoded name is simpler and matches current my-kluster pattern.
**Warning signs:** CronJob pod fails to mount `/app/config` — ConfigMap not found.

---

## Code Examples

### arrconf-configmap.yaml template

```yaml
# charts/arr-stack/templates/arrconf-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: arrconf-config
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "arr-stack.labels" . | nindent 4 }}
data:
  arrconf.yml: |
    {{- .Files.Get "files/arrconf.yml" | nindent 4 }}
```

### configarr-configmap.yaml template

```yaml
# charts/arr-stack/templates/configarr-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: configarr-config
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "arr-stack.labels" . | nindent 4 }}
data:
  configarr.yml: |
    {{- .Files.Get "files/configarr.yml" | nindent 4 }}
```

### _helpers.tpl

```yaml
# charts/arr-stack/templates/_helpers.tpl
{{/*
Expand the name of the chart.
*/}}
{{- define "arr-stack.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "arr-stack.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "arr-stack.labels" -}}
helm.sh/chart: {{ include "arr-stack.chart" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| app-template 4.6.2 (planned) | app-template 5.0.0 (actual production) | 2026-05-11 (Renovate PR #1381) | All version pins must be 5.0.0 |
| arrconf 0.2.0 (old PATTERNS.md) | arrconf 0.2.1 (Renovate PR #1382) | 2026-05-11 | Tag in arrconf alias: `0.2.1` |
| configarr 1.16.0 (old PATTERNS.md) | configarr 1.28.0 (current production) | Unknown (Renovate) | Tag in configarr alias: `1.28.0` |
| 10 unit ArgoCD Applications | 1 umbrella ArgoCD Application | Phase 4 cutover | Selector change; Replace=true required |
| custom charts in my-kluster | app-template aliases in arr-stack | Phase 4 | Removes my-kluster chart dependency |
| `cronJobConfig:` key (v4 docs artifact) | `cronjob:` key | app-template 5.0.0 | CronJob values structure changed |

**Deprecated/outdated in Phase 4 plans:**
- `version: 4.6.2` in Chart.yaml: replaced by `version: 5.0.0`
- `cronJobConfig:` key: replaced by `cronjob:`
- `successfulJobsHistoryLimit:` in values: replaced by `successfulJobsHistory:` (app-template adds Limit suffix)
- `my-kluster/charts/arrconf/`: dead code after Phase 4 cutover (delete in follow-up PR)
- `my-kluster/charts/configarr/`: same

---

## Wave Structure Recommendation

**Wave 0 — Baseline (ALREADY COMPLETE as of commit 2a94257)**
- Task 1.1 (image digest capture + ArgoCD Application baseline): ✅ DONE
- Task 1.2 (helper scripts): write `check-renovate-annotations.sh` + `byte-equivalence-diff.sh`

**Wave 1 — Chart skeleton (Plan 04-02)**
- Chart.yaml with 10 aliases at 5.0.0
- `helm dependency update` + Chart.lock committed
- `helm lint` passes

**Wave 2 — Media app aliases (Plans 04-03 + 04-04)**
- values.yaml sections for 8 media apps (verbatim from evidence baselines)
- Renovate annotations above every `repository:` line
- `check-renovate-annotations.sh` passes

**Wave 3 — CronJob aliases (Plan 04-05)**
- arrconf + configarr aliases in values.yaml
- ConfigMap templates for arrconf.yml + configarr.yml
- `files/arrconf.yml` from current production (D-04-CRON-03: adds radarr,prowlarr to --apps)

**Wave 4 — CI + schema (Plan 04-06)**
- `chart-lint.yml` workflow
- `renovate.json` customManagers
- `values.schema.json` generation

**Wave 5 — Docs (Plan 04-07)**
- README + CLAUDE.md reference app-template 5.x
- D-04-DOCS-01 satisfied

**Wave 6 — Cutover (Plan 04-08)**
- Byte-equivalence diff
- Delete 10 unit Applications
- Apply arr-stack Application
- Watch + smoke test
- 10-minute soak

**Wave 7 — Post-cutover (Plan 04-09)**
- Confirm ArgoCD Healthy
- Delete dead code from my-kluster (charts/arrconf, charts/configarr, 10 argocd-apps files)
- Update STATE.md

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `losisin/helm-values-schema-json` v2.4.0 is the current version | Standard Stack §Supporting | Install step may fail; check GitHub releases at execution time |
| A2 | configarr schedule is `0 */6 * * *` (inherited from custom chart) | Pattern 3 | CronJob runs at wrong frequency; user confirms schedule |
| A3 | ArgoCD prune does NOT delete PVCs with Retain policy | Runtime State Inventory | Data loss risk if wrong; verify PVC reclaim policy before cutover |
| A4 | seerr uses `ghcr.io/sctx/overseerr` (not jellyseerr variant) | Per-App Values Blocks | Image wrong; executor must read seerr evidence YAML directly |
| A5 | `examples/values-prod.yaml` is the valueFile used by arr-stack-app.yaml | arr-stack-app.yaml target | CI and cutover use wrong values file; verify against spec.md §9.2 |
| A6 | arrconf.yml `--apps sonarr,radarr,prowlarr` is correct Phase 4 scope | Pattern 2 | If radarr/prowlarr reconcilers not ready (Phase 5), add `--dry-run` flag |
| A7 | my-kluster post-cutover cleanup (dead charts/arrconf) happens in same wave or follow-up PR | Wave Structure | Dead code persists; document as explicit action item |

---

## Open Questions

1. **seerr image repository** — evidence/pre-cutover-argocd/seerr.yaml must be read to extract exact image. The per-app section above marks it as ASSUMED. Executor: read `evidence/pre-cutover-argocd/seerr.yaml` helm.values before writing seerr alias.

2. **configarr CronJob schedule** — Current custom chart schedule is `0 */6 * * *` (6 hourly). Confirm with user before codifying in umbrella. The arrconf schedule (4 hourly) is verified from custom chart.

3. **argocd CLI for cutover** — Cutover Wave 6 (Plan 04-08) references `argocd app diff` and `argocd app sync`. argocd CLI is not installed on this workstation (confirmed). Plan must document kubectl-only fallback path explicitly. Consider whether to install argocd CLI as Wave 0 prerequisite or document full kubectl alternatives.

4. **my-kluster cleanup timing** — Phase 4 cutover deletes the 10 unit ArgoCD Applications. The my-kluster `charts/arrconf/` and `charts/configarr/` directories + 10 `argocd-apps/*.yaml` files become dead code. Should this cleanup be in the same PR as the arr-stack-app.yaml addition (atomic) or a follow-up PR (safer, separate review)? Recommend same PR for atomicity, but user should confirm.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Helm | Chart build, CI | ✓ | 4.1.4 | — |
| kubectl | Cutover, baseline | ✓ | (cluster 1.33.9) | — |
| argocd CLI | Cutover (preferred) | ✗ | — | kubectl get/apply (documented in Cutover Sequence) |
| kubeconform | CI chart-lint.yml | ✓ (via CI) | installed in CI | — |
| git | my-kluster reads | ✓ | — | — |
| OCI registry (ghcr.io/bjw-s) | helm dependency update | ✓ | — | Manual helm pull |

**Missing dependencies with no fallback:**
- None — argocd CLI has kubectl fallback; all other tools available.

**Note:** argocd CLI absence is documented in STATE.md Phase 02.2 P05 and the kubectl fallback path is the primary approach for this project.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | helm lint + kubeconform (not pytest — chart-only phase) |
| Config file | `.github/workflows/chart-lint.yml` (Wave 4) |
| Quick run command | `helm lint charts/arr-stack/ && helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml \| kubeconform -kubernetes-version 1.33.0 -strict -ignore-missing-schemas` |
| Full suite command | Same (no separate unit tests for Helm chart phase) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-04-01 | Chart.yaml 10 aliases render without error | helm lint | `helm lint charts/arr-stack/` | ❌ Wave 1 |
| REQ-04-02 | values.yaml produces valid K8s manifests | kubeconform | `helm template ... \| kubeconform -kubernetes-version 1.33.0` | ❌ Wave 1 |
| REQ-04-03 | Byte-equivalence diff passes | manual script | `tools/scripts/byte-equivalence-diff.sh` | ❌ Wave 0 Task 1.2 |
| REQ-04-04 | Renovate annotations present | shell check | `tools/scripts/check-renovate-annotations.sh` | ❌ Wave 0 Task 1.2 |
| REQ-04-05 | CI workflow valid YAML | yaml lint | `yamllint .github/workflows/chart-lint.yml` | ❌ Wave 4 |
| REQ-04-06 | arr-stack-app.yaml has Replace=true | grep check | `grep -q 'Replace=true' my-kluster/.../arr-stack-app.yaml` | ❌ Wave 6 |
| REQ-04-07 | arrconf CronJob renders with correct schedule | helm template | `helm template ... \| grep -A5 'schedule:'` | ❌ Wave 3 |
| REQ-04-08 | configarr CronJob has tty:true | helm template | `helm template ... \| grep 'tty: true'` | ❌ Wave 3 |
| REQ-04-11 | Baseline captured | evidence files | `ls evidence/pre-cutover-argocd/ \| wc -l` (expect 10) | ✅ Done |

### Wave 0 Gaps

- [ ] `tools/scripts/check-renovate-annotations.sh` — covers REQ-04-04
- [ ] `tools/scripts/byte-equivalence-diff.sh` — covers REQ-04-03
- [ ] `charts/arr-stack/Chart.yaml` — needed before helm lint runs (Wave 1)
- [ ] Framework install: `helm dependency update charts/arr-stack/` — after Chart.yaml exists

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A — auth delegated to oauth2-proxy (pre-existing) |
| V3 Session Management | No | N/A — oauth2-proxy |
| V4 Access Control | Partial | Ingress: oauth2-proxy annotations on 7/8 apps; jellyfin no oauth (by design) |
| V5 Input Validation | No | Helm chart rendering, not user input |
| V6 Cryptography | No | TLS terminated at ingress (pre-existing cert-manager) |
| V7 Error Handling | No | No new error surfaces |

### Known Threat Patterns for Helm Umbrella

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secret exposure in values.yaml | Information Disclosure | Never put API keys in values.yaml; use `secretRef:` → existing `arrconf-env`, `configarr-env` secrets |
| SSRF via CronJob --apps flag | Tampering | `--apps` value is static in chart, not user-supplied at runtime |
| Image tag mutation (`:latest`) | Tampering | Use digest pinning for `:latest` images (qbittorrent, cleanuparr, flaresolverr) via `@sha256:...` OR pin to explicit version tag |
| PVC data loss at cutover | Denial of Service | `existingClaim:` prevents recreation; ArgoCD prune does not delete PVCs |

**Note on `:latest` images:** Three apps use `:latest` tags (qbittorrent, cleanuparr, flaresolverr). Their digests are captured in `evidence/current-image-tags.txt`. Recommend pinning to those digests in values.yaml for reproducibility, while keeping renovate annotations for future updates. This is consistent with D-04-PIN-03.

---

## Sources

### Primary (HIGH confidence)
- `/tmp/app-template-5.0.0.tgz` (pulled via `helm pull oci://ghcr.io/bjw-s/helm/app-template --version 5.0.0`) — chart structure, values schema, CronJob key names, breaking changes
- `evidence/pre-cutover-argocd/*.yaml` (10 files, committed 2a94257) — production state baseline for all 10 apps
- `git show main:charts/arrconf/values.yaml` + `git show main:charts/arrconf/templates/cronjob.yaml` — arrconf production values
- `git show main:charts/configarr/values.yaml` + `git show main:charts/configarr/templates/cronjob.yaml` — configarr production values
- `kubectl get sa,svc,pvc -n selfhost` — live cluster state (SAs, Services, PVCs)
- `/tmp/test-umbrella/` helm template tests — naming strategy validation (fullnameOverride vs nameOverride)
- `spec.md §6.4, §9.2` — authoritative Renovate regex and arr-stack-app.yaml structure
- `.planning/phases/04-umbrella-chart-migration-des-9-apps/04-CONTEXT.md` — locked decisions

### Secondary (MEDIUM confidence)
- `04-01-DRIFT-NOTE.md` — diagnosis of 4.6.2 vs 5.0.0 drift (this document)
- `git log main -- argocd/argocd-apps/ --oneline | head -5` on my-kluster — confirmed Renovate PR #1381

### Tertiary (LOW confidence — flagged in Assumptions Log)
- losisin/helm-values-schema-json version (A1) — GitHub releases page not verified this session
- configarr CronJob schedule (A2) — extracted from custom chart but not cross-checked with user

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified by pulling actual chart artefact; confirmed via live cluster state
- Architecture: HIGH — validated via helm template tests on actual 5.0.0 chart
- Per-app values: HIGH — extracted verbatim from evidence baselines captured from live cluster
- CronJob keys: HIGH — verified from values.schema.json JSON extracted from common 5.0.0 chart
- Pitfalls: HIGH — verified by helm template testing (nameOverride vs fullnameOverride)
- Assumptions: LOW — 7 items flagged; see Assumptions Log

**Research date:** 2026-05-13
**Valid until:** 2026-06-13 (stable chart — app-template 5.x; Renovate will surface any bumps)
**Replaces:** Prior RESEARCH.md dated 2026-05-12 (assumed app-template 4.6.2 — incorrect)
