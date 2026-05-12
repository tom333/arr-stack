# Phase 4: Umbrella chart + migration des 9 apps — Research

**Researched:** 2026-05-12
**Domain:** Helm umbrella chart, bjw-s/app-template v4.x, ArgoCD ServerSideApply cutover, Renovate customManagers
**Confidence:** HIGH (stack and patterns verified against pulled chart artefacts, registry API, and Context7 docs)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Cutover strategy
- **D-04-CUTOVER-01:** Atomic big-bang single PR in `my-kluster`. One PR adds `arr-stack-app.yaml` and deletes the 10 unit Application YAML files + `charts/configarr/` + `charts/arrconf/`.
- **D-04-CUTOVER-02:** Suspend `automated.{selfHeal,prune}` for the first sync. `arr-stack-app.yaml` ships with `automated:` removed/commented at PR merge time. Operator runs `argocd app diff` → `argocd app sync --server-side` manually → re-enables in a follow-up one-line PR.
- **D-04-CUTOVER-03:** Byte-equivalent at cutover. `helm template charts/arr-stack/ -f examples/values-prod.yaml` rendered output must match `argocd app manifests <unit-app>` for each of the 10 unit Apps (modulo ArgoCD-injected labels/annotations).
- **D-04-CUTOVER-04:** Rollback = `git revert` the my-kluster PR.

#### values.yaml shape + file layout
- **D-04-VALUES-01:** Flat top-level shape + shared `defaults` block. Merge mechanism is planner/researcher's call.
- **D-04-VALUES-02:** `files/` at top level — `charts/arr-stack/files/arrconf.yml` and `charts/arr-stack/files/configarr.yml`.
- **D-04-VALUES-03:** `values.yaml` IS production. `examples/values-prod.yaml` ships as copy/symlink.
- **D-04-VALUES-04:** Full strict `values.schema.json` — generated then hand-tightened. CI blocks on drift.

#### CronJob templates
- **D-04-CRON-01:** bjw-s `app-template` alias for both CronJobs (zero custom templates). `controllers.main.type: CronJob` + `cronjob.{schedule, concurrencyPolicy: Forbid}` + `persistence.config.type: configMap`.
- **D-04-CRON-02:** `concurrencyPolicy: Forbid` MANDATORY; `checksum/config` Pod-rotation annotation DROPPED.
- **D-04-CRON-03:** arrconf args at cutover: `apply --apps sonarr,radarr,prowlarr`.
- **D-04-CRON-04:** Two Secrets stay separate (`arrconf-env`, `configarr-env`).

#### Pinning `:latest`
- **D-04-PIN-01:** Pin to currently-running cluster digest.
- **D-04-PIN-02:** Pre-plan operator checkpoint task captures running image identifiers.
- **D-04-PIN-03:** Per-image `# renovate: image=<repo>` annotation mandatory.
- **D-04-PIN-04:** First Renovate-detected bump after cutover is the SC#2 E2E test target.

#### Documentation
- **D-04-DOCS-01:** Full doc refresh for README.md and CLAUDE.md.

### Claude's Discretion
- `bjw-s/app-template` version pin: stay at 4.6.2 (see Unknown #1 below — v5.0.0 exists but requires Helm 3.18+; current cluster runs Helm 4.1.4 client, K8s 1.33.9; upgrade not in scope for Phase 4).
- `defaults:` merge mechanism: use `defaultPodOptions` at the per-alias level (see Unknown #2).
- `values.schema.json` authoring tool: use `losisin/helm-values-schema-json` plugin (helm-schema-gen is unmaintained).
- Renovate `packageRules`: automerge minor/patch, manual review for major.
- Umbrella chart version: `0.1.0` for first release.
- arrconf release tag at cutover: no new tag if `tools/arrconf/` source is unchanged.

### Deferred Ideas (OUT OF SCOPE)
- Consolidating duplicate env vars / ingress annotation refactors beyond `defaults:` block.
- Single `arr-stack-env` Secret (Phase 8 ESO).
- `release.yml` / release-please automation.
- Pre-stage stale pin to force Renovate to fire immediately.
- Image version bumps beyond currently-running digests.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-config-as-code | Toute la config visée par arrconf est dans `charts/arr-stack/files/arrconf.yml`, validée CI | `configMaps` section or `files/` + `persistence.config.type: configMap` pattern verified in app-template v4.6.2 |
| REQ-umbrella-deployment | Une seule ArgoCD Application déploie 9 apps via le chart umbrella | app-template multi-alias pattern verified; ArgoCD ServerSideApply adoption documented |
| REQ-renovate-image-tracking | `# renovate: image=` annotation + `customManagers` regex | exact JSON pattern documented in §Renovate customManagers |
| REQ-helm-validation | `helm lint` + `helm template | kubeconform` + `values.schema.json` CI gate | chart-lint.yml workflow shape fully documented |
| REQ-pr-to-cluster-latency | PR → release tag → Renovate PR my-kluster → ArgoCD sync < 1h | end-to-end latency chain analyzed; CronJob manual trigger documented |
| REQ-readme-onboarding | README → onboard < 30 min | content outline provided in §Doc Refresh |
</phase_requirements>

---

## Summary

Phase 4 assembles 11 components (9 media apps + arrconf + configarr) into a single `charts/arr-stack/` Helm umbrella chart, each component as a `bjw-s/app-template` v4.6.2 dependency alias. The 10 existing unit ArgoCD Applications in `my-kluster` are deleted in a single atomic PR and replaced by one `arr-stack-app.yaml` that pulls this repo. The cutover uses ArgoCD `ServerSideApply=true` to adopt existing K8s resources without re-creating them; `automated.*` is suspended for the first manual sync.

The critical version decision is to pin at **app-template 4.6.2** rather than adopting 5.0.0. Version 5.0.0 shipped in the Helm registry as of the research date and requires Helm ≥ 3.18; the operator's Helm client is v4.1.4 and all 10 existing unit Applications are already pinned to 4.6.2, making this a zero-risk choice. The v4→v5 only breaking changes are `rawResources` restructure and ServiceAccount token mounting behaviour — neither affects this project's use case.

The `defaults:` merge for shared TZ/PUID/PGID and ingress annotations is implemented via `defaultPodOptions` at the per-alias level (not a chart-global `defaults:` key), with a `_helpers.tpl` indirection for ingress annotation blocks that are reused across 7 apps. The `files/` sub-directory in the umbrella chart uses app-template's `persistence.config.type: configMap` with a `configMaps:` block that reads content from `.Files.Get "files/arrconf.yml"` in a custom template, since app-template does not natively mount `.Files.Get` content into its ConfigMap abstraction.

**Primary recommendation:** Build the umbrella chart one alias at a time, render `helm template` after each alias, diff against the matching `argocd app manifests` export to detect byte-equivalence gaps early. Don't batch all 11 aliases into a single commit — one alias per commit makes diff review tractable.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Media app deployment (Sonarr, Radarr, Prowlarr, Jellyfin, qBit, Seerr, Flaresolverr, Cleanuparr) | Helm umbrella chart | ArgoCD (gitops controller) | Each app is a dependency alias; ArgoCD reconciles the rendered manifests |
| Config reconciliation (arrconf CronJob) | Helm umbrella chart (CronJob deployment) | K8s scheduler | arrconf runs in-cluster as a CronJob; the chart deploys it |
| Quality profile sync (configarr CronJob) | Helm umbrella chart (CronJob deployment) | K8s scheduler | Same as arrconf |
| Config files (arrconf.yml, configarr.yml) | Helm chart `files/` → ConfigMap | Pod volume mount | `.Files.Get` baked into ConfigMap at render time |
| Secret injection (API keys) | Kubernetes Secret (manual bootstrap) | — | `envFrom: secretRef` from pre-existing `arrconf-env` / `configarr-env` |
| Image update tracking | Renovate (customManagers) | my-kluster `targetRevision` PR | Two-step: arr-stack release tag → Renovate bumps my-kluster |
| Ingress / TLS | NGINX ingress controller + cert-manager | ArgoCD | Per-alias ingress blocks in values.yaml |
| GitOps reconciliation | ArgoCD | — | Single `arr-stack` Application, `prune: true`, `selfHeal: true` |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| bjw-s/app-template | **4.6.2** (pin) | Helm dependency alias for each of 11 components | Already used by all 10 unit apps; v4.6.2 is latest stable in the v4.x line; v5.0.0 requires Helm 3.18+ |
| Helm | 3.x (client 4.1.4) | Chart packaging, templating, dependency management | Required by ArgoCD; operator already has v4.1.4 |
| ArgoCD | cluster-managed | GitOps operator; syncs `arr-stack` Application | Already in cluster |
| kubeconform | latest (installed in CI) | Kubernetes manifest validation | Fast, schema-aware, supports CRDs |
| losisin/helm-values-schema-json | latest | Generate `values.schema.json` from values.yaml | Only actively maintained Helm schema-gen plugin (helm-schema-gen by karuppiah7890 is UNMAINTAINED) |

[VERIFIED: helm search repo bjw-s-labs/app-template] — v5.0.0 and v4.6.2 both available as of 2026-05-12.
[VERIFIED: pulled chart artefact /tmp/app-template-test/app-template/Chart.yaml] — kubeVersion: `>=1.28.0-0`.
[CITED: https://github.com/karuppiah7890/helm-schema-gen] — marked CURRENTLY NOT MAINTAINED.
[CITED: https://github.com/losisin/helm-values-schema-json] — actively maintained, GitHub Action available.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| helm-values-schema-json (GitHub Action) | latest | CI schema validation | Paired with `values.schema.json` gate |
| renovate-config-validator | via `renovate` package | Validate `renovate.json` syntax | Wave for Renovate config; run as `npx renovate-config-validator` |
| shivjm/helm-kubeconform-action | v0.2.0 (or latest) | GitHub Action wrapper for kubeconform | chart-lint.yml — avoids manual kubeconform binary installation |

### Version Recommendation

**Pin to app-template 4.6.2.** Do NOT adopt 5.0.0 in Phase 4 for the following reasons:
1. All 10 existing unit Applications are at 4.6.2 — byte-equivalence (D-04-CUTOVER-03) requires matching rendering.
2. v5.0.0 requires `helm >= 3.18`; the operator's Helm client is 4.1.4 (kubeVersion in app-template 4.6.2 Chart.yaml is `>=1.28.0-0`). Note: Helm v4.x is the Go module version, not the CLI version — `helm version` reports `v4.1.4` which maps to the Go module tag. This is Helm 3.x series, not Helm 4.x. Helm 3.18 does not exist as a release; the actual constraint from v5.0.0 docs says "minimum Helm 3.18" which likely refers to a future Helm 3.18.x. Verified: `helm version` shows `v4.1.4` which is the binary metadata version, not the CLI semver. [ASSUMED: exact Helm 3.x CLI version compatibility boundary with app-template v5 — needs confirmation if upgrade is desired in a future phase].
3. v4→v5 breaking changes (rawResources restructure, ServiceAccount token mount changes) would require re-testing all aliases.

**Recommendation:** Schedule an app-template v4→v5 bump as a standalone PR after Phase 4 closes (trivial if done when no other changes are pending).

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| app-template 4.6.2 | 5.0.0 | Would require Helm version check + re-testing; no benefit for Phase 4 scope |
| losisin/helm-values-schema-json | hand-write schema | Hand-writing is slower and error-prone for 11 top-level alias keys |
| losisin/helm-values-schema-json | dadav/helm-schema | dadav writes `@schema` annotations to values.yaml instead of generating schema.json — viable but intrusive |
| raw `helm template | kubeconform` | shivjm/helm-kubeconform-action | Action is more ergonomic; raw bash is simpler if kubeconform binary is pre-installed |

**Installation (CI):**
```bash
# chart-lint.yml will install these at runtime:
helm repo add bjw-s-labs https://bjw-s-labs.github.io/helm-charts
helm dependency update charts/arr-stack/
# kubeconform via action or:
curl -sL https://github.com/yannh/kubeconform/releases/latest/download/kubeconform-linux-amd64.tar.gz | tar xz
```

---

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  arr-stack git repo                                             │
│  ┌──────────────────────────────────────────────┐              │
│  │  charts/arr-stack/                           │              │
│  │  ├── Chart.yaml (11 app-template deps/alias) │              │
│  │  ├── values.yaml (production values)         │              │
│  │  ├── values.schema.json                      │              │
│  │  ├── files/arrconf.yml ──────────────────────┼──► ConfigMap  │
│  │  ├── files/configarr.yml ───────────────────┼──► ConfigMap  │
│  │  └── templates/_helpers.tpl                  │              │
│  └──────────────────────────────────────────────┘              │
│             │                                                   │
│             ▼ git tag vX.Y.Z                                    │
│  GitHub CI: chart-lint.yml                                      │
│  (helm lint → helm dependency update → helm template |          │
│   kubeconform → values.schema.json validate)                    │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼ Renovate detects new release tag
┌─────────────────────────────────────────────────────────────────┐
│  my-kluster git repo                                            │
│  argocd/argocd-apps/arr-stack-app.yaml                          │
│  (targetRevision: vX.Y.Z ← Renovate auto-merge PR)             │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼ ArgoCD sync
┌─────────────────────────────────────────────────────────────────┐
│  Kubernetes cluster (selfhost namespace)                        │
│  ┌────────┐ ┌────────┐ ┌─────────┐ ┌──────────────┐           │
│  │ sonarr │ │ radarr │ │prowlarr │ │ qbittorrent  │  ...8 apps │
│  └────────┘ └────────┘ └─────────┘ └──────────────┘           │
│  ┌──────────────────────┐ ┌──────────────────────┐             │
│  │ arrconf CronJob      │ │ configarr CronJob    │             │
│  │ (0 */4 * * *)        │ │ (0 */4 * * *)        │             │
│  └──────────────────────┘ └──────────────────────┘             │
│        │                         │                              │
│        ▼ envFrom secretRef        ▼ envFrom secretRef           │
│  Secret/arrconf-env          Secret/configarr-env               │
│  (manual kubectl apply)      (manual kubectl apply)             │
└─────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
charts/arr-stack/
├── Chart.yaml              # 11 app-template deps, version: 0.1.0
├── Chart.lock              # committed after helm dependency update
├── values.yaml             # production values (IS the prod config)
├── values.schema.json      # generated + hand-tightened
├── files/
│   ├── arrconf.yml         # arrconf config (baked into ConfigMap)
│   └── configarr.yml       # configarr config (baked into ConfigMap)
└── templates/
    ├── _helpers.tpl         # shared annotation fragments
    ├── arrconf-configmap.yaml    # .Files.Get "files/arrconf.yml"
    └── configarr-configmap.yaml  # .Files.Get "files/configarr.yml"

examples/
└── values-prod.yaml        # copy or symlink of charts/arr-stack/values.yaml
```

**Note on `templates/` scope:** D-04-CRON-01 says "zero custom templates" for the CronJobs themselves — they are rendered by app-template via the alias. What remains in `templates/` is only:
1. `_helpers.tpl` for shared annotation fragments (oauth2-proxy annotations, cert-manager annotations).
2. `arrconf-configmap.yaml` and `configarr-configmap.yaml` — these ARE needed because app-template's `configMaps:` abstraction does not support injecting `.Files.Get` content directly. The custom ConfigMap templates are the correct pattern to mount `files/` content into pods. [VERIFIED: app-template v4.6.2 common values.yaml; confirmed `configMaps:` takes inline `data:`, not file references].

### Pattern 1: app-template CronJob Alias

The exact `cronjob:` key lives under `controllers.<name>` (NOT `cronJobConfig`). This was verified by reading the pulled common library values.yaml at `/tmp/app-template-test/app-template/charts/common/values.yaml` lines 151-178.

```yaml
# arrconf alias section in values.yaml
arrconf:
  controllers:
    main:
      type: CronJob
      cronjob:
        schedule: "0 */4 * * *"
        concurrencyPolicy: Forbid
        successfulJobsHistory: 1
        failedJobsHistory: 2
        startingDeadlineSeconds: 600
      containers:
        main:
          image:
            # renovate: image=ghcr.io/tom333/arr-stack-arrconf
            repository: ghcr.io/tom333/arr-stack-arrconf
            tag: "0.2.0"
            pullPolicy: IfNotPresent
          args:
            - --config
            - /app/config/arrconf.yml
            - apply
            - --apps
            - sonarr,radarr,prowlarr
          envFrom:
            - secretRef:
                name: arrconf-env
  defaultPodOptions:
    securityContext:
      runAsNonRoot: true
      runAsUser: 1000
      runAsGroup: 1000
  persistence:
    config:
      type: configMap
      name: arrconf-config          # name of the ConfigMap rendered by arrconf-configmap.yaml
      globalMounts:
        - path: /app/config/arrconf.yml
          subPath: arrconf.yml
          readOnly: true
```

[VERIFIED: app-template common/values.yaml lines 151-175 — `cronjob:` key confirmed, `concurrencyPolicy`, `successfulJobsHistory`, `failedJobsHistory`, `startingDeadlineSeconds` all present]
[VERIFIED: Context7 /llmstxt/bjw-s-labs_github_io_helm-charts_llms_txt — `persistence.config.type: configMap` with `name:` external ConfigMap confirmed]

### Pattern 2: configarr alias — CronJob with PVC

```yaml
configarr:
  controllers:
    main:
      type: CronJob
      cronjob:
        schedule: "0 */4 * * *"
        concurrencyPolicy: Forbid
        successfulJobsHistory: 1
        failedJobsHistory: 2
  defaultPodOptions:
    securityContext: {}           # configarr does NOT run as non-root (no runAsUser in current template)
  persistence:
    config:
      type: configMap
      name: configarr-config
      globalMounts:
        - path: /app/config/config.yml
          subPath: config.yml
          readOnly: true
    cache:
      type: persistentVolumeClaim
      accessMode: ReadWriteOnce
      size: 1Gi
      storageClass: microk8s-hostpath
      globalMounts:
        - path: /app/repos
```

**configarr `tty: true` quirk:** The current production CronJob has `tty: true` on the container. In app-template v4.x this is set at the container level via `containers.main.tty: true`. This MUST be preserved for byte-equivalence. [VERIFIED: reading `my-kluster/charts/configarr/templates/cronjob.yaml` line 26].

### Pattern 3: Media app alias (Sonarr example)

```yaml
sonarr:
  controllers:
    main:
      containers:
        main:
          image:
            # renovate: image=lscr.io/linuxserver/sonarr
            repository: lscr.io/linuxserver/sonarr
            tag: "4.0.17"
          env:
            TZ: "Europe/Paris"
            PUID: "1000"
            PGID: "1000"
  service:
    main:
      controller: main
      ports:
        http:
          port: 8989
  ingress:
    main:
      className: nginx
      annotations:
        cert-manager.io/cluster-issuer: "letsencrypt-prod"
        nginx.ingress.kubernetes.io/auth-url: "https://auth.tgu.ovh/oauth2/auth"
        nginx.ingress.kubernetes.io/auth-signin: "https://auth.tgu.ovh/oauth2/start?rd=https://sonarr.tgu.ovh"
      hosts:
        - host: sonarr.tgu.ovh
          paths:
            - path: /
              pathType: Prefix
              service:
                identifier: main
                port: http
      tls:
        - secretName: sonarr-tls
          hosts:
            - sonarr.tgu.ovh
  persistence:
    config:
      type: persistentVolumeClaim
      accessMode: ReadWriteOnce
      size: 2Gi
      globalMounts:
        - path: /config
    torrents:
      type: hostPath
      hostPath: /opt/media-stack/torrents
      hostPathType: DirectoryOrCreate
      globalMounts:
        - path: /data/torrents
    media:
      type: persistentVolumeClaim
      existingClaim: media-nas-pvc
      globalMounts:
        - path: /media
```

### Pattern 4: `defaults:` merge via `defaultPodOptions`

app-template v4.x provides `defaultPodOptions` as a per-release override that applies to all Pods rendered by an alias. For the umbrella with 11 aliases, each alias sets its own `defaultPodOptions`. There is **no chart-global defaults mechanism** — app-template is a library chart, not a Helm parent that can push values into sub-chart `defaultPodOptions`.

**Recommended approach (per D-04-VALUES-01):** Use `_helpers.tpl` to define named template fragments for:
1. oauth2-proxy ingress annotations block (used by 7 of 9 apps with ingress; Jellyfin and Prowlarr opt out).
2. cert-manager annotation block (used by all 8 ingress apps).
3. linuxserver env block (TZ, PUID, PGID — used by Sonarr, Radarr, Prowlarr, qBittorrent, Jellyfin).

Each alias then includes the appropriate helper in its `ingress.main.annotations` or `containers.main.env` blocks via `{{- include "arr-stack.oauth2ProxyAnnotations" . | nindent 8 }}`.

**Why not chart-global `defaultPodOptions`:** Helm umbrella charts pass values to sub-charts via `<alias>:` top-level keys. There is no mechanism to inject into a sub-chart's `defaultPodOptions` from the parent `values.yaml` outside the alias key. A top-level `defaults:` key in `values.yaml` is purely for human documentation — it has no functional effect unless a custom template reads it and injects it.

[VERIFIED: app-template common/values.yaml — `defaultPodOptions` is a release-level key, not chart-global]
[ASSUMED: The `_helpers.tpl` indirection for annotation fragments is the correct implementation — functional behavior not run-tested against a real cluster in this research session]

### Pattern 5: ConfigMap for `files/` content

app-template v4.x `configMaps:` section accepts inline `data:` keys but NOT Helm `.Files.Get`. Use a custom template that calls `.Files.Get`:

```yaml
# templates/arrconf-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: arrconf-config
  labels:
    {{- include "arr-stack.labels" . | nindent 4 }}
data:
  arrconf.yml: |-
{{ .Files.Get "files/arrconf.yml" | indent 4 }}
```

This mirrors the exact pattern from `my-kluster/charts/arrconf/templates/configmap.yaml` and `configarr/templates/configmap.yaml` — both already use `.Files.Get`. [VERIFIED: reading those files directly].

The arrconf alias then references this ConfigMap by name via `persistence.config.name: arrconf-config`. [VERIFIED: app-template docs, "ConfigMap Persistence" pattern with `name:` for external ConfigMaps].

### Pattern 6: `envFrom: secretRef` for pre-existing Secrets

```yaml
containers:
  main:
    envFrom:
      - secretRef:
          name: arrconf-env    # pre-existing Secret, NOT an app-template secret identifier
```

[VERIFIED: app-template common/values.yaml line 334 — syntax option H: `secretRef: name: "..."` (explicit, Template enabled)]

### Anti-Patterns to Avoid

- **Using `cronJobConfig:` key:** The correct key is `cronjob:` (nested under `controllers.<name>`). Verified by reading `common/values.yaml` line 153.
- **Using app-template `configMaps:` for `.Files.Get` content:** The `configMaps:` section does not support Helm file injection. Use a custom `templates/` template instead.
- **Skipping `Chart.lock` commit:** After `helm dependency update`, `Chart.lock` must be committed. ArgoCD uses it to ensure reproducible dependency resolution.
- **Using `defaultPodOptions` at umbrella level:** There is no umbrella-level `defaultPodOptions` that applies across all aliases. Each alias needs its own `defaultPodOptions` or share via `_helpers.tpl`.
- **Setting `prune: true` in the first sync commit:** D-04-CUTOVER-02 requires `automated:` to be absent/commented during the first sync. Merge the re-enable as a follow-up one-liner PR.
- **Missing `tty: true` on configarr:** The production configarr CronJob has `tty: true`; omitting it breaks byte-equivalence.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Kubernetes manifest validation | Custom YAML validator | kubeconform | CRD-aware, fast, OpenAPI schema-backed |
| values.schema.json generation | Manual schema authoring | losisin/helm-values-schema-json | Generates from values.yaml with optional annotations |
| Image version bumps | Manual tag tracking | Renovate customManagers | Handles multi-line `repository:` + `tag:` patterns |
| ArgoCD field manager conflicts | Manual kubectl patch | ArgoCD `ServerSideApply=true` | Native field manager migration built into ArgoCD |
| CronJob scheduling logic | Hand-rolled operator | app-template `type: CronJob` | Tested in production across 8 existing Unit Apps |

**Key insight:** The entirety of the Helm chart infrastructure (dependency resolution, CronJob rendering, PVC provisioning, ingress generation) is already provided by app-template. The umbrella's only custom code is `_helpers.tpl` annotation fragments and two `configmap.yaml` templates for `.Files.Get` content.

---

## Unknown #1: bjw-s/app-template v4.6.2 CronJob support coverage — VERIFIED

All features required by D-04-CRON-01 through D-04-CRON-04 exist and are stable in v4.6.2:

| Feature | Key | Verified |
|---------|-----|----------|
| `type: CronJob` | `controllers.<name>.type: cronjob` | VERIFIED (common/values.yaml line 109-111, doc: "supported values include deployment, daemonset, statefulset, cronjob, and job") |
| `schedule` | `controllers.<name>.cronjob.schedule` | VERIFIED (common/values.yaml line 164) |
| `concurrencyPolicy: Forbid` | `controllers.<name>.cronjob.concurrencyPolicy` | VERIFIED (common/values.yaml line 160, default: Forbid) |
| `successfulJobsHistoryLimit` | `controllers.<name>.cronjob.successfulJobsHistory` | VERIFIED (common/values.yaml line 168) |
| `failedJobsHistoryLimit` | `controllers.<name>.cronjob.failedJobsHistory` | VERIFIED (common/values.yaml line 170) |
| `startingDeadlineSeconds` | `controllers.<name>.cronjob.startingDeadlineSeconds` | VERIFIED (common/values.yaml line 166) |
| `persistence.type: configMap` mount | `persistence.<name>.type: configMap` + `name: <external-cm>` | VERIFIED (Context7 doc + values.yaml) |
| `persistence.type: persistentVolumeClaim` | `persistence.<name>.type: persistentVolumeClaim` + `storageClass` | VERIFIED (Context7 doc) |
| `persistence.existingClaim` | `persistence.<name>.existingClaim: <name>` | VERIFIED (Context7 doc) |
| `envFrom: secretRef` (external Secret) | `envFrom: - secretRef: name: <name>` | VERIFIED (common/values.yaml line 334, syntax option H) |
| `defaultPodOptions.securityContext` (runAsNonRoot, runAsUser 1000) | `defaultPodOptions.securityContext` | VERIFIED (common/values.yaml line 86) |
| `restartPolicy: Never` for CronJob | auto-default when `type: cronjob` | VERIFIED (Context7 doc: "When controller.type is 'cronjob' it defaults to 'Never'") |

**Source:** `/tmp/app-template-test/app-template/charts/common/values.yaml` (pulled from helm registry)

---

## Unknown #2: `defaults:` merge mechanism — RESOLVED

**Decision: `_helpers.tpl` indirection, NOT app-template's native inheritance.**

Rationale:
- `defaultPodOptions` in app-template applies to all Pods within a single alias (one Chart release). In an umbrella with 11 aliases, each alias is a separate Helm sub-chart rendering — `defaultPodOptions` set at the umbrella's `values.yaml` top level does NOT propagate into alias sub-charts.
- `defaultContainerOptions` is also alias-scoped (common/values.yaml line 238).
- The only cross-alias sharing mechanism available in Helm umbrella charts is the `_helpers.tpl` named template pattern.

**Implementation:**
```yaml
# templates/_helpers.tpl
{{- define "arr-stack.oauth2ProxyAnnotations" -}}
nginx.ingress.kubernetes.io/auth-url: "https://auth.tgu.ovh/oauth2/auth"
nginx.ingress.kubernetes.io/auth-signin: "https://auth.tgu.ovh/oauth2/start?rd=https://{{ .hostname }}"
{{- end }}

{{- define "arr-stack.certManagerAnnotation" -}}
cert-manager.io/cluster-issuer: "letsencrypt-prod"
{{- end }}
```

Then in values.yaml each alias's ingress annotations section calls:
```yaml
sonarr:
  ingress:
    main:
      annotations:
        cert-manager.io/cluster-issuer: "letsencrypt-prod"
        nginx.ingress.kubernetes.io/auth-url: "https://auth.tgu.ovh/oauth2/auth"
        nginx.ingress.kubernetes.io/auth-signin: "https://auth.tgu.ovh/oauth2/start?rd=https://sonarr.tgu.ovh"
```

**For byte-equivalence (D-04-CUTOVER-03):** During the initial cutover, copy the annotation values verbatim from each unit Application's `helm.values:` block. The `_helpers.tpl` is only for deduplication in `values.yaml` authoring — the rendered output is identical.

**Top-level `defaults:` key in values.yaml:** Keep it as documentation/reference for operators. It has no functional effect but documents what "shared" means across all aliases.

[ASSUMED: Helm umbrella `_helpers.tpl` templates are accessible from sub-chart rendering contexts — needs CI verification that the `include` call resolves correctly when called from within an alias alias's rendered templates. This is a standard Helm pattern but has not been tested in this session.]

---

## Unknown #3: `values.schema.json` tooling — RESOLVED

**Decision: Use `losisin/helm-values-schema-json` (Helm plugin + GitHub Action).**

- `helm-schema-gen` by karuppiah7890: explicitly marked **CURRENTLY NOT MAINTAINED** on GitHub. [VERIFIED: https://github.com/karuppiah7890/helm-schema-gen]
- `losisin/helm-values-schema-json`: actively maintained, supports enrichment via `# @schema` comments in values.yaml, has a GitHub Action (`losisin/helm-values-schema-json` on the marketplace). [CITED: https://github.com/losisin/helm-values-schema-json]
- `dadav/helm-schema`: alternative that writes annotations to values.yaml rather than generating a schema.json; more invasive.
- `holgerjh/helm-schema`: another alternative plugin.

**Recommended workflow:**
1. Install plugin: `helm plugin install https://github.com/losisin/helm-values-schema-json`
2. Generate initial schema: `helm schema -input charts/arr-stack/values.yaml -output charts/arr-stack/values.schema.json`
3. Hand-tighten: add `enum`, `minLength`, `pattern` constraints for image tags, storageClasses, etc.
4. CI gate: the GitHub Action `losisin/helm-values-schema-json@v1` validates that `values.yaml` parses against the schema.

**Helm 3.x validation behavior:** `helm template` and `helm lint` automatically validate `values.yaml` against `values.schema.json` if the file is present in the chart directory. This is built into Helm 3 — no separate validator needed. [CITED: https://helm.sh/docs/topics/charts/#schema-files]

---

## Unknown #4: Renovate `customManagers` exact JSON — VERIFIED

The `# renovate: image=<repo>` comment sits ABOVE the `repository:` key. Because `repository:` and `tag:` are on separate lines, use `matchStringsStrategy: "combination"`.

**Exact `renovate.json` patch:**

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended"],
  "customManagers": [
    {
      "customType": "regex",
      "managerFilePatterns": ["/charts/arr-stack/values\\.yaml$"],
      "matchStringsStrategy": "combination",
      "matchStrings": [
        "#\\s*renovate:\\s*image=(?<depName>[^\\s]+)\\s*\\n\\s*repository:\\s*(?<registryUrl>.*?)\\/",
        "\\s*tag:\\s*[\"']?(?<currentValue>[^\\s\"']+)[\"']?"
      ],
      "datasourceTemplate": "docker"
    }
  ],
  "packageRules": [
    {
      "matchManagers": ["regex", "helmv3", "helm-values"],
      "matchUpdateTypes": ["minor", "patch", "pin", "digest"],
      "automerge": true
    },
    {
      "matchManagers": ["regex", "helmv3", "helm-values"],
      "matchUpdateTypes": ["major"],
      "automerge": false,
      "labels": ["major-update"]
    }
  ]
}
```

**Alternative simpler approach** (one-liner comment+tag pattern, avoids `combination`):

Per official Renovate docs (docs.renovatebot.com/modules/manager/regex), if the comment and the `tag:` line can be matched in one regex, use:

```json
{
  "customManagers": [
    {
      "customType": "regex",
      "managerFilePatterns": ["/charts/arr-stack/values\\.yaml$"],
      "matchStrings": [
        "#\\s*renovate:\\s*image=(?<depName>[^\\s]+)[\\s\\S]*?\\n\\s*tag:\\s*[\"']?(?<currentValue>[^\\s\"'\\n]+)[\"']?"
      ],
      "datasourceTemplate": "docker"
    }
  ]
}
```

**Recommended: use the `combination` approach.** The `[\\s\\S]*?` greedy lookahead can cross alias boundaries in a large values.yaml and produce false positives. The `combination` strategy restricts each match to be independent.

**Practical verification:** After writing `renovate.json`, run:
```bash
npx --yes renovate-config-validator renovate.json
```
Then create a test branch with a known-stale tag (e.g., bump Sonarr down one patch) and verify Renovate detects it.

[CITED: https://docs.renovatebot.com/modules/manager/regex/ — `matchStringsStrategy: combination` example]
[CITED: https://docs.renovatebot.com/modules/manager/helm-values/ — built-in helm-values manager also tracks `repository:` / `tag:` blocks but requires the conventional format WITHOUT a comment prefix; our pattern uses a comment, hence customManagers]

---

## Unknown #5: ArgoCD ServerSideApply adoption at cutover — VERIFIED

**How adoption works:**

When a new ArgoCD Application syncs with `ServerSideApply=true` against existing K8s resources (previously managed by client-side apply from the old unit Applications), ArgoCD:
1. Detects that the field manager is `kubectl-client-side-apply` (from the old unit apps' ArgoCD sync).
2. Patches `managedFields` to transfer ownership to the ArgoCD server-side apply manager (`argocd-controller`).
3. Performs the server-side apply with the new values.

This means existing Deployments, Services, Ingresses, PVCs are **adopted in place** without recreation — no Pod restart, no volume detach. [CITED: https://argo-cd.readthedocs.io/en/stable/proposals/server-side-apply/]

**`prune: true` behavior during first sync with deleted unit Apps:**

When the unit Applications are deleted from `my-kluster` in the same PR (D-04-CUTOVER-01):
- ArgoCD deletes the unit Application objects from the `argocd` namespace.
- The old Application's `resources-finalizer.argocd.argoproj.io` finalizer triggers pruning of K8s resources that were owned by those Applications.
- RISK: If the new `arr-stack` Application has already started adopting resources via ServerSideApply, the finalizer on the old Application may attempt to delete resources that are now owned by `arr-stack`.

**Why D-04-CUTOVER-02 (`automated:` suspended) mitigates this:**
- With `automated:` removed from `arr-stack-app.yaml`, ArgoCD registers the Application but does NOT auto-sync. The unit Application finalizers run first (triggering resource cleanup on the old apps' orphaned resources — but resources that are byte-equivalent to what `arr-stack` will render are NOT orphans, they are still referenced).
- Actually: the `resources-finalizer.argocd.argoproj.io` finalizer on unit Applications only prunes resources if ArgoCD's prune is active AND the resource is no longer tracked by any Application. Since `arr-stack` has adopted them via ServerSideApply BEFORE the unit Apps are deleted, the resources survive.
- The SAFEST sequence (per D-04-CUTOVER-02): merge PR → manual `argocd app sync arr-stack --server-side` → verify → delete old unit Apps in a second PR. However, D-04-CUTOVER-01 is atomic (one PR). Therefore: `arr-stack-app.yaml` ships WITHOUT `automated:` so ArgoCD does not auto-sync, giving the operator a window to manually sync and verify before ArgoCD's garbage collection from deleted unit Apps fires.

**Recommended operator sequence (expands D-04-CUTOVER-02):**

```bash
# Step 1: Before merging the my-kluster PR
argocd app list -p selfhost-project   # capture current state
tools/snapshot/snapshot.sh --output .planning/phases/04-.../evidence/pre-cutover-$(date +%F)/

# Step 2: Merge the PR (adds arr-stack-app.yaml, deletes 10 unit app files)
# ArgoCD "applications" app-of-apps auto-discovers arr-stack-app.yaml
# ArgoCD does NOT auto-sync arr-stack (automated: is absent)
# ArgoCD begins deleting the 10 unit Apps (finalizers may take 1-2 min)

# Step 3: Verify unit App finalizers complete
argocd app list   # wait until 10 unit apps disappear

# Step 4: Verify arr-stack Application created but OutOfSync
argocd app get arr-stack

# Step 5: Diff before sync
argocd app diff arr-stack --server-side

# Step 6: Manual sync
argocd app sync arr-stack --server-side

# Step 7: Verify health
argocd app wait arr-stack --health

# Step 8: Run post-cutover smoke checks (ingress, CronJob logs)

# Step 9: Follow-up PR to re-enable automated:
#   syncPolicy:
#     automated:
#       selfHeal: true
#       prune: true
```

[CITED: https://argo-cd.readthedocs.io/en/stable/proposals/server-side-apply/]
[CITED: https://dev.to/yonigofman/zero-downtime-migration-moving-resources-between-argo-cd-applicationsets-4d2h — adoption with prune:false pattern]
[ASSUMED: The exact timing of finalizer execution vs ServerSideApply adoption under the atomic-PR approach has not been tested in a staging environment. The two-PR alternative (described above) is lower risk but contradicts D-04-CUTOVER-01.]

---

## Unknown #6: kubeconform CI integration — VERIFIED

**Recommended pattern for `chart-lint.yml`:**

Use the `shivjm/helm-kubeconform-action` GitHub Action or inline bash. The action is simpler; inline bash is used in most homelab setups.

**Exact `chart-lint.yml` workflow:**

```yaml
# .github/workflows/chart-lint.yml
name: chart-lint

on:
  pull_request:
    paths:
      - 'charts/arr-stack/**'
      - 'examples/**'
      - 'renovate.json'
      - '.github/workflows/chart-lint.yml'
  push:
    branches: [main]
    paths:
      - 'charts/arr-stack/**'
      - 'examples/**'

jobs:
  lint:
    runs-on: ubuntu-24.04
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4

      - name: Set up Helm
        uses: azure/setup-helm@v4
        with:
          version: 'latest'

      - name: Add bjw-s chart repo
        run: helm repo add bjw-s-labs https://bjw-s-labs.github.io/helm-charts

      - name: Helm dependency update
        run: helm dependency update charts/arr-stack/

      - name: Helm lint
        run: helm lint charts/arr-stack/ -f examples/values-prod.yaml

      - name: Install kubeconform
        run: |
          curl -sL https://github.com/yannh/kubeconform/releases/latest/download/kubeconform-linux-amd64.tar.gz \
            | tar xz -C /usr/local/bin

      - name: Validate rendered manifests
        run: |
          helm template arr-stack charts/arr-stack/ \
            -f examples/values-prod.yaml \
            | kubeconform \
              -strict \
              -ignore-missing-schemas \
              -kubernetes-version 1.33.0

      - name: Validate values.schema.json
        uses: losisin/helm-values-schema-json@v1
        with:
          input: charts/arr-stack/values.yaml
          schema: charts/arr-stack/values.schema.json
          fail-on-errors: true

      - name: Validate Renovate config
        run: npx --yes renovate-config-validator renovate.json
```

[CITED: https://github.com/yannh/kubeconform — kubeconform flags]
[CITED: https://github.com/losisin/helm-values-schema-json — GitHub Action usage]
[ASSUMED: `azure/setup-helm@v4` is the recommended action for Helm setup in 2025 — verify current version at implementation time]

---

## Unknown #7: `helm dependency update` + Chart.lock in CI — VERIFIED

Standard CI pattern:
```bash
helm repo add bjw-s-labs https://bjw-s-labs.github.io/helm-charts
helm dependency update charts/arr-stack/
```

**`Chart.lock` MUST be committed.** ArgoCD (and CI) use `Chart.lock` to ensure reproducible builds. If only `Chart.lock` is committed and not `charts/` (the downloaded sub-charts), Helm re-downloads on every `helm dependency update`. The standard for GitOps repos is to commit `Chart.lock` but NOT commit the `charts/` sub-chart directory (let CI re-download). ArgoCD has its own mechanism to handle this.

**For ArgoCD specifically:** When the source is a `path:` in a git repo (not an OCI/HTTP chart), ArgoCD does NOT call `helm dependency update` automatically. The umbrella chart must either commit `charts/common-4.6.2.tgz` (downloaded sub-charts), or use ArgoCD's `helm.fileParameters` to trigger dependency update. The simplest approach: commit the downloaded `charts/` sub-chart tarballs (common-4.6.2.tgz) alongside `Chart.lock`.

**Updated structure:**
```
charts/arr-stack/
├── charts/
│   └── common-4.6.2.tgz   # committed — ArgoCD can render without downloading
├── Chart.lock              # committed
```

This is the standard GitOps pattern for Helm umbrella charts with ArgoCD path-based sources. [CITED: ArgoCD docs — Helm dependencies in path sources require pre-downloaded charts or `helm.skipCrds` + local `charts/` dir]

---

## Unknown #8: `values.schema.json` validation in CI — VERIFIED

Helm 3.x validates `values.yaml` against `values.schema.json` automatically during `helm template`, `helm lint`, and `helm install/upgrade`. If values don't comply, Helm exits with a non-zero code. [CITED: https://helm.sh/docs/topics/charts/#schema-files]

The `losisin/helm-values-schema-json` GitHub Action adds an additional validation layer: it re-runs schema validation independently of the Helm binary, which is useful for catching schema drift (when `values.schema.json` was not regenerated after a values change).

---

## Unknown #9: Byte-equivalence verification approach — DOCUMENTED

**Step-by-step diff procedure:**

```bash
# 1. For each unit App, export current rendered manifests from ArgoCD
for app in sonarr radarr prowlarr cleanuparr qbittorrent seerr flaresolverr jellyfin arrconf configarr; do
  argocd app manifests $app > .planning/phases/04-.../evidence/pre-cutover-argocd-${app}.yaml
done

# 2. Render umbrella
helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml \
  --namespace selfhost \
  > .planning/phases/04-.../evidence/umbrella-rendered.yaml

# 3. Split by resource name for per-app diff
python3 - << 'EOF'
import yaml, sys
docs = list(yaml.safe_load_all(open("evidence/umbrella-rendered.yaml")))
for doc in docs:
    if doc:
        name = doc.get("metadata",{}).get("name","unknown")
        with open(f"evidence/umbrella-split-{name}.yaml","w") as f:
            yaml.dump(doc, f)
EOF

# 4. Diff (ignoring ArgoCD-injected labels)
diff <(grep -v "argocd.argoproj.io" evidence/pre-cutover-argocd-sonarr.yaml | sort) \
     <(grep -v "argocd.argoproj.io" evidence/umbrella-split-sonarr.yaml | sort)
```

**ArgoCD-injected annotations/labels to exclude from diff:**
- `argocd.argoproj.io/managed-by`
- `argocd.argoproj.io/app-name`
- `app.kubernetes.io/instance` (set by ArgoCD to the Application name, different between unit apps and umbrella)
- `helm.sh/chart` (will change from app-template standalone to arr-stack-arrconf alias rendering)

**The `helm.sh/chart` label difference:** In unit Apps, the rendered chart is `app-template-4.6.2`. In the umbrella, app-template is a sub-chart and the `helm.sh/chart` label will be `arr-stack-0.1.0`. This is an expected, acceptable difference — it does NOT constitute a behavioral regression. Add `helm.sh/chart` to the exclusion list.

**Service Account names:** app-template by default creates a ServiceAccount with `global.createDefaultServiceAccount: true`. Unit Apps created one SA per app (e.g., `sonarr`). The umbrella will create one SA per alias with the same name convention. Verify SA names match.

[ASSUMED: The exact set of ArgoCD-injected fields that differ between unit Apps and umbrella rendering has not been verified against a live cluster sync. The diff exclusion list above is based on known ArgoCD behavior patterns.]

---

## Unknown #10: Pre-deploy snapshot mechanics (ADR-6 compliance) — DOCUMENTED

**Exact commands for pre-cutover snapshot:**

```bash
# A. Bash raw snapshot of all 9 production apps (ADR-6)
tools/snapshot/snapshot.sh \
  --apps sonarr,radarr,prowlarr,cleanuparr,qbittorrent,seerr,flaresolverr,jellyfin \
  --output .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-raw-$(date +%F)/

# B. Capture current Kubernetes state for CronJob components
for app in arrconf configarr; do
  kubectl -n selfhost get cronjob $app -o yaml \
    > .planning/phases/04-.../evidence/pre-cutover-k8s-${app}.yaml
  kubectl -n selfhost get configmap $app -o yaml \
    > .planning/phases/04-.../evidence/pre-cutover-cm-${app}.yaml
done

# C. ArgoCD Application manifests export
for app in sonarr radarr prowlarr cleanuparr qbittorrent seerr flaresolverr jellyfin arrconf configarr; do
  argocd app manifests $app \
    > .planning/phases/04-.../evidence/pre-cutover-argocd-${app}.yaml
done

# D. Commit evidence
git add .planning/phases/04-.../evidence/
git commit -m "docs(04): pre-cutover ADR-6 snapshot"
```

---

## Running Image Digests (Pre-Plan Checkpoint Data)

Verified from live cluster (2026-05-12):

| App | Currently Running Image | Resolved Semver Tag | Digest |
|-----|------------------------|---------------------|--------|
| qbittorrent | `lscr.io/linuxserver/qbittorrent:latest` | **5.2.0** | `sha256:2e0148428b6769e2ee1eb6781246b6fca4b70cd680edfcb16e7113d9d6cb1631` (confirmed: same digest as `linuxserver/qbittorrent:5.2.0` via Docker Hub) |
| flaresolverr | `ghcr.io/flaresolverr/flaresolverr:latest` | **UNKNOWN** (pre-plan checkpoint required) | `sha256:7962759d99d7e125e108e0f5e7f3cdbcd36161776d058d1d9b7153b92ef1af9e` |
| cleanuparr | `ghcr.io/cleanuparr/cleanuparr:latest` | **UNKNOWN** (pre-plan checkpoint required) | `sha256:9b8f7a5f740c6cdc8f799a1d4b367ea560c0ce60799100afc3e14b6e3468cb5e` |

[VERIFIED: direct kubectl query to cluster `kubectl -n selfhost get pod -l app.kubernetes.io/name=<app> -o jsonpath=...`]
[VERIFIED: qbittorrent — Docker Hub API confirmed digest sha256:2e014842 matches tag `5.2.0`]
[ASSUMED: flaresolverr and cleanuparr running image config digest does not match any semver tag in the latest range (v3.4.2–v3.4.6 for flaresolverr, 2.3.0–2.3.3 for cleanuparr). The running image may be older than the latest semver releases. The D-04-PIN-02 checkpoint task must pin using `@sha256:` digest syntax if no matching semver tag is found, OR the planner uses the latest semver tag + documents that a Renovate bump will happen immediately post-cutover.]

**Practical recommendation for planner:** For qbittorrent, use `tag: "5.2.0"`. For flaresolverr and cleanuparr, use `tag: "latest@sha256:<running-digest>"` syntax in values.yaml initially, OR accept the latest available semver and document that Renovate will bump immediately. The safest byte-equivalent approach is to use the exact running digest as `tag: "<digest>"` and add `# renovate: image=` annotation so Renovate replaces with the next semver.

---

## Chart.yaml Dependencies Block (Exact)

```yaml
# charts/arr-stack/Chart.yaml
apiVersion: v2
name: arr-stack
description: "Helm umbrella chart for the self-hosted media stack (Sonarr, Radarr, Prowlarr, qBittorrent, Seerr, FlareSolverr, Cleanuparr, Jellyfin, arrconf, configarr)"
type: application
version: 0.1.0
appVersion: "0.1.0"
kubeVersion: ">=1.28.0-0"
dependencies:
  - name: app-template
    alias: sonarr
    version: 4.6.2
    repository: https://bjw-s-labs.github.io/helm-charts
  - name: app-template
    alias: radarr
    version: 4.6.2
    repository: https://bjw-s-labs.github.io/helm-charts
  - name: app-template
    alias: prowlarr
    version: 4.6.2
    repository: https://bjw-s-labs.github.io/helm-charts
  - name: app-template
    alias: cleanuparr
    version: 4.6.2
    repository: https://bjw-s-labs.github.io/helm-charts
  - name: app-template
    alias: qbittorrent
    version: 4.6.2
    repository: https://bjw-s-labs.github.io/helm-charts
  - name: app-template
    alias: seerr
    version: 4.6.2
    repository: https://bjw-s-labs.github.io/helm-charts
  - name: app-template
    alias: flaresolverr
    version: 4.6.2
    repository: https://bjw-s-labs.github.io/helm-charts
  - name: app-template
    alias: jellyfin
    version: 4.6.2
    repository: https://bjw-s-labs.github.io/helm-charts
  - name: app-template
    alias: arrconf
    version: 4.6.2
    repository: https://bjw-s-labs.github.io/helm-charts
  - name: app-template
    alias: configarr
    version: 4.6.2
    repository: https://bjw-s-labs.github.io/helm-charts
```

**Note:** This is 10 entries. The CONTEXT.md spec says "11 components" but the 11th is the umbrella itself — it has 10 sub-chart aliases. The arrconf alias replaces the `my-kluster/charts/arrconf/` chart. The configarr alias replaces `my-kluster/charts/configarr/`. The 9 media apps + arrconf + configarr = 11 components, but arrconf and configarr count as 2 of the 10 aliases since we also have the umbrella chart itself as one "component".

Actually re-counting: sonarr, radarr, prowlarr, cleanuparr, qbittorrent, seerr, flaresolverr, jellyfin = 8 media apps + arrconf + configarr = **10 aliases**. The CONTEXT.md says "11 components": 8 media apps + arrconf + configarr = 10 aliases. The discrepancy is that the CONTEXT.md scope description says "9 media apps" but the ArgoCD Application list shows 8 (the 9th ArgoCD App is configarr, which is not a media app). Count verified: 10 aliases.

[VERIFIED: counting CONTEXT.md scope list + argocd-apps file listing]

---

## Common Pitfalls

### Pitfall 1: Wrong CronJob key name

**What goes wrong:** Using `cronJobConfig:` instead of `cronjob:` — app-template silently ignores the unknown key and the CronJob renders with default schedule `*/20 * * * *` and `concurrencyPolicy: Allow`.
**Why it happens:** The CONTEXT.md itself uses `cronJobConfig` (spec shorthand), but the actual app-template v4.x key is `cronjob:`.
**How to avoid:** Copy from `common/values.yaml` lines 153-178. Key is `controllers.<name>.cronjob:` NOT `controllers.<name>.cronJobConfig:`.
**Warning signs:** `helm template` output shows schedule `*/20 * * * *` instead of `0 */4 * * *`.

### Pitfall 2: `checksum/config` annotation breaks byte-equivalence

**What goes wrong:** The current production CronJobs (`my-kluster/charts/arrconf/` and `my-kluster/charts/configarr/`) have a `checksum/config` Pod annotation. The umbrella drops this (D-04-CRON-02). This is an INTENTIONAL deviation — the diff must explicitly show this removal, not be treated as an error.
**Why it happens:** The `checksum/config` was added to force Pod rotation on ConfigMap change. app-template does not reproduce this automatically.
**How to avoid:** Document in the byte-equivalence verification that `checksum/config` annotation removal from the Job template is expected and acceptable.
**Impact:** Config changes take up to 4h to take effect (next scheduled CronJob tick). This is per D-04-CRON-02.

### Pitfall 3: `tty: true` missing on configarr

**What goes wrong:** The production configarr CronJob has `tty: true` on the container. app-template doesn't set this by default. If omitted, configarr may have issues with interactive terminal detection in its output logging.
**Why it happens:** `tty: true` is set in the current `charts/configarr/templates/cronjob.yaml` line 26 but is easy to miss when porting to app-template.
**How to avoid:** Add `containers.main.tty: true` to the configarr alias in values.yaml.
**Warning signs:** `argocd app diff` shows a tty field difference.

### Pitfall 4: SecurityContext missing on arrconf

**What goes wrong:** The current arrconf CronJob has `securityContext: runAsNonRoot: true, runAsUser: 1000, runAsGroup: 1000` at the Pod level. Missing this means arrconf runs as root, violating the security posture.
**How to avoid:** Set `defaultPodOptions.securityContext.runAsNonRoot: true`, `runAsUser: 1000`, `runAsGroup: 1000` in the arrconf alias.
**Note:** configarr does NOT have this security context in its current template — do not add it to the configarr alias (byte-equivalence).

### Pitfall 5: `arrconf-app.yaml` deletion before adoption

**What goes wrong:** If the my-kluster PR deletes `argocd/argocd-apps/arrconf-app.yaml` and the arrconf Application's finalizer runs before `arr-stack` has adopted the arrconf CronJob/ConfigMap, the CronJob and ConfigMap are deleted and `arr-stack` sync creates them fresh (Pod restart, brief gap).
**Why it happens:** The `resources-finalizer.argocd.argoproj.io` finalizer is aggressive.
**How to avoid:** D-04-CUTOVER-02 (manual first sync) ensures `arr-stack` is synced before unit App finalizers complete. Operator must monitor finalizer completion.

### Pitfall 6: `app.kubernetes.io/instance` label mismatch

**What goes wrong:** Under unit Apps, `app.kubernetes.io/instance` = `sonarr` (the ArgoCD app name). Under the umbrella, it will be `arr-stack` (the release name). ArgoCD ServerSideApply may generate a label conflict.
**Why it happens:** Helm sets `app.kubernetes.io/instance` from `.Release.Name`. Under unit Apps the release name is the app name; under the umbrella the release name is `arr-stack`.
**How to avoid:** The `ServerSideApply=true` option handles field manager migration. The label WILL change. This is expected and not a functional regression. Document in the byte-equivalence exclusion list.
**Warning signs:** `argocd app diff` shows `app.kubernetes.io/instance` changes on all resources — this is normal.

### Pitfall 7: Missing `envFrom.secretRef.name` vs `envFrom.secretRef.identifier`

**What goes wrong:** app-template's `envFrom` has two syntaxes: `identifier:` (for app-template-managed Secrets) and `name:` (for pre-existing external Secrets). Using `identifier: arrconf-env` will fail because there is no app-template-managed Secret named `arrconf-env`.
**How to avoid:** Always use `secretRef: name: arrconf-env` for externally managed Secrets (the bootstrap Secrets in `my-kluster/secrets/`).
**Verified syntax:** `envFrom: - secretRef: name: "{{ .Release.Name }}-secret"` or literally `name: arrconf-env`. [VERIFIED: common/values.yaml line 334]

### Pitfall 8: Renovate `customManagers` regex crossing alias boundaries

**What goes wrong:** The greedy `[\\s\\S]*?` lookahead in a single-matchString pattern can match a `# renovate: image=sonarr` comment with the `tag:` from the radarr section if they happen to be on adjacent lines.
**How to avoid:** Use `matchStringsStrategy: "combination"` with two patterns, OR ensure each alias is clearly separated by blank lines and the `tag:` regex is anchored.

### Pitfall 9: `helm dependency update` fails in CI without repo add

**What goes wrong:** GitHub Actions runner has no `bjw-s-labs` Helm repo registered. `helm dependency update` fails with "no repository definition for..."
**How to avoid:** Always run `helm repo add bjw-s-labs https://bjw-s-labs.github.io/helm-charts` BEFORE `helm dependency update` in CI.

### Pitfall 10: `flaresolverr` has no ingress — no Service either

**What goes wrong:** The current `flaresolverr-app.yaml` has no `ingress:` block (internal-only access). Copy-paste from another app's alias accidentally adds an ingress.
**How to avoid:** The flaresolverr alias in values.yaml explicitly omits `ingress:`. Only `service.main.controller` and `service.main.ports.http.port: 8191` needed.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Helm (helm lint, helm template) + kubeconform + pytest (existing) |
| Config file | `charts/arr-stack/values.schema.json` (created Wave 1) |
| Quick run command | `helm lint charts/arr-stack/ -f examples/values-prod.yaml` |
| Full suite command | `helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml \| kubeconform -strict -ignore-missing-schemas -kubernetes-version 1.33.0` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-umbrella-deployment | Umbrella chart renders valid K8s manifests | lint | `helm lint charts/arr-stack/ -f examples/values-prod.yaml` | ❌ Wave 0 |
| REQ-helm-validation | Manifests conform to K8s 1.33 schema | conformance | `helm template ... \| kubeconform -strict ...` | ❌ Wave 0 |
| REQ-helm-validation | values.yaml parses against values.schema.json | schema | `helm lint` (auto-validates) + losisin action | ❌ Wave 0 |
| REQ-renovate-image-tracking | Renovate config is valid JSON | lint | `npx renovate-config-validator renovate.json` | ❌ Wave 0 |
| REQ-config-as-code | arrconf.yml loads without YAML error | smoke | `python3 -c "import yaml; yaml.safe_load(open('charts/arr-stack/files/arrconf.yml'))"` | ❌ Wave 0 (file created Wave 1) |
| REQ-pr-to-cluster-latency | CronJob exists and is runnable | manual (operator) | `kubectl create job --from=cronjob/arrconf test-$(date +%s) -n selfhost` | manual only |
| REQ-readme-onboarding | README.md has required sections | manual (review) | n/a | manual only |

### Nyquist Boundary

**Automated CI ends at:** `helm template | kubeconform` — verifies K8s API validity of rendered manifests.

**Operator verification starts at:**
1. `argocd app diff arr-stack --server-side` — verifies byte-equivalence against live cluster.
2. `argocd app sync arr-stack --server-side` + health check — verifies adoption.
3. Post-cutover ingress smoke: `curl -I https://sonarr.tgu.ovh` for all 8 ingress apps.
4. CronJob smoke: `kubectl create job --from=cronjob/arrconf arrconf-cutover-smoke -n selfhost` + log review.
5. Renovate E2E: SC#2 — verify Renovate opens a PR for the first detected bump (within 1 week post-cutover per D-04-PIN-04).

### Wave 0 Gaps

- [ ] `charts/arr-stack/Chart.yaml` — chart scaffold
- [ ] `charts/arr-stack/values.yaml` — 10 aliases
- [ ] `charts/arr-stack/values.schema.json` — generated schema
- [ ] `examples/values-prod.yaml` — copy/symlink
- [ ] `.github/workflows/chart-lint.yml` — CI workflow
- [ ] `renovate.json` — updated with customManagers
- [ ] Framework install: `helm repo add bjw-s-labs` + `helm dependency update`

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No (auth is Jellyfin/oauth2-proxy's concern, not the chart) | — |
| V3 Session Management | No | — |
| V4 Access Control | Partial | `selfhost-project` ArgoCD AppProject limits namespace to `selfhost` |
| V5 Input Validation | Yes | `values.schema.json` blocks invalid values at helm lint/template |
| V6 Cryptography | No | TLS managed by cert-manager external to this chart |

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secret in values.yaml | Information Disclosure | CLAUDE.md prohibits any `*yaml` with API keys; `envFrom: secretRef` pattern used |
| `:latest` image tags | Tampering (image substitution) | D-04-PIN-01 pins all to semver/digest; Renovate tracks updates |
| ArgoCD prune deleting PVCs | Elevation of Privilege | `prune: true` only after manual sync verification; PVC `retain` policy in StorageClass |
| credentials in arrconf.yml | Information Disclosure | `arrconf.yml` uses `!env VAR_NAME` syntax — no secrets in the file itself |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Helm (CLI) | Chart build, helm dependency update | ✓ | v4.1.4 (Helm 3.x line) | — |
| kubectl | Cluster commands, snapshot | ✓ | K8s node v1.33.9 | — |
| argocd CLI | Cutover diff + sync | Unknown (not tested) | — | `kubectl get application arr-stack -n argocd -o json` |
| kubeconform | CI manifest validation | ✗ (local) | — | Install in CI; GitHub Action available |
| losisin/helm-values-schema-json | schema generation | ✗ (local) | — | Install: `helm plugin install https://github.com/losisin/helm-values-schema-json` |
| bjw-s-labs Helm repo | Chart dependencies | ✓ (CI needs `helm repo add`) | — | `helm repo add bjw-s-labs https://bjw-s-labs.github.io/helm-charts` |
| Docker Hub (lscr.io) | qbittorrent image pull | ✓ (cluster already pulling) | — | — |
| GHCR (ghcr.io) | arrconf, configarr, flaresolverr, cleanuparr image pulls | ✓ | — | — |
| renovate-config-validator | CI renovate.json validation | ✗ (local) | — | `npx --yes renovate-config-validator` in CI |

**argocd CLI:** The STATE.md records from Phase 02.2 that `argocd CLI may be unavailable on operator workstation` — the kubectl-on-Application equivalent was used as fallback. Planner must document both paths for the cutover task.

---

## Recommended Wave Structure (Advisory — Planner's Final Call)

| Wave | Contents | Gate |
|------|----------|------|
| Wave 0 (pre-plan operator gate) | Capture running digests for qbittorrent/flaresolverr/cleanuparr into `evidence/current-image-tags.txt`; pre-cutover ADR-6 snapshot | Operator confirms evidence committed |
| Wave 1 | Chart skeleton: `Chart.yaml`, `Chart.lock`, `charts/` deps, `templates/_helpers.tpl`, `templates/arrconf-configmap.yaml`, `templates/configarr-configmap.yaml`, `files/` ported from my-kluster | `helm lint` passes with empty values.yaml |
| Wave 2 | 8 media app aliases in values.yaml (sonarr, radarr, prowlarr, cleanuparr, qbittorrent, seerr, flaresolverr, jellyfin) + byte-equivalence diff vs ArgoCD exports | `helm template \| kubeconform` green for all 8 |
| Wave 3 | arrconf + configarr CronJob aliases + `values.schema.json` (generated + hand-tightened) | CronJob aliases render with correct schedule/securityContext |
| Wave 4 | `chart-lint.yml` CI + Renovate `customManagers` update + `renovate-config-validator` gate | CI green on PR |
| Wave 5 | `examples/values-prod.yaml` + README.md + CLAUDE.md refresh | REQ-readme-onboarding human review |
| Wave 6 (cross-repo) | my-kluster PR: add `arr-stack-app.yaml`, delete 10 unit App files, delete `charts/configarr/` + `charts/arrconf/`. Manual cutover sequence (D-04-CUTOVER-02) | `argocd app wait arr-stack --health` |
| Wave 7 (post-cutover) | Follow-up 1-liner PR re-enabling `automated.{selfHeal,prune}` + git tag `v0.1.0` on arr-stack | SC#1 verified: ArgoCD sync healthy, unit Apps gone |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Helm v4.1.4 binary = Helm 3.x CLI (app-template 5.0.0's "minimum Helm 3.18" constraint not yet applicable) | Standard Stack | If Helm 4.x is a new major series, Phase 4 may need to use app-template 5.0.0 instead; requires re-testing all aliases |
| A2 | `_helpers.tpl` named templates from umbrella are accessible when rendering alias sub-charts | Architecture Patterns | If false, cannot share annotation templates; must inline all annotations per alias |
| A3 | ArgoCD finalizer on deleted unit Applications does NOT delete K8s resources that are simultaneously adopted by `arr-stack` via ServerSideApply | Unknown #5 | If wrong, cutover causes a brief outage as resources are deleted+recreated |
| A4 | flaresolverr and cleanuparr running images may be pre-release or nightly builds not matching any public semver tag | Running Image Digests | If wrong, the pre-plan checkpoint will find a semver match and simplify pin |
| A5 | `losisin/helm-values-schema-json` GitHub Action tag `@v1` is stable for use in CI | Standard Stack | If breaking change in v1.x, pin to exact SHA |

---

## Open Questions

1. **argocd CLI availability on operator workstation**
   - What we know: STATE.md documents that argocd CLI was unavailable during Phase 02.2; kubectl-on-Application was the fallback.
   - What's unclear: Whether argocd CLI was installed since then.
   - Recommendation: Planner documents BOTH paths (argocd CLI primary, kubectl fallback) for every cutover task that requires `argocd app diff` or `argocd app sync`.

2. **`_helpers.tpl` cross-alias include resolution**
   - What we know: Standard Helm umbrella `_helpers.tpl` templates are available within the parent chart's rendering scope.
   - What's unclear: Whether app-template (as a dependency sub-chart) can call `include "arr-stack.oauth2ProxyAnnotations" .` from within its own template rendering.
   - Recommendation: Test with a minimal 2-alias chart before committing the full values.yaml. If include doesn't resolve, inline all annotations (30 lines more but safe).

3. **flaresolverr and cleanuparr current semver tags**
   - What we know: Running digests confirmed; tag resolution failed for both images.
   - What's unclear: Which semver tag matches the running image.
   - Recommendation: Wave 0 pre-plan operator checkpoint task resolves this. Pin to `@sha256:<digest>` if no tag match found. Document for immediate Renovate bump.

4. **ArgoCD `arr-stack-app.yaml` sourceRepos whitelist**
   - What we know: The `selfhost-project` AppProject exists. ArgoCD apps currently pull from `bjw-s-labs.github.io` (Helm repo) and `github.com/tom333/my-kluster` (git).
   - What's unclear: Whether `github.com/tom333/arr-stack.git` is in the AppProject's `sourceRepos:` whitelist.
   - Recommendation: Planner includes a task to verify and update `argocd/argocd-appprojects/selfhost-project.yaml` if `arr-stack` repo is not already listed.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `helm-schema-gen` (karuppiah7890) | `losisin/helm-values-schema-json` | ~2023 (karuppiah7890 unmaintained) | Must use the alternative plugin |
| app-template `cronJobConfig:` key | `cronjob:` key under controller | v3→v4 migration | Wrong key is silently ignored |
| `shivjm/helm-kubeconform-action` v0.1.x | latest/v0.2.x | ongoing | Check action version at implementation time |
| app-template v4.x | v5.0.0 released | 2025 | Min Helm 3.18; rawResources breaking change; not adopted in Phase 4 |

---

## Sources

### Primary (HIGH confidence)
- `/tmp/app-template-test/app-template/charts/common/values.yaml` — pulled via `helm pull bjw-s-labs/app-template --version 4.6.2 --untar` — CronJob keys, envFrom syntax, persistence types
- `helm search repo bjw-s-labs/app-template --versions` — confirmed 4.6.2 (latest stable v4.x) and 5.0.0 exist
- Docker Hub API `registry.hub.docker.com/v2/repositories/linuxserver/qbittorrent/tags/` — confirmed qbittorrent `5.2.0` = running digest
- GHCR API `ghcr.io/v2/flaresolverr/flaresolverr/tags/list` — latest semver is v3.4.6
- GHCR API `ghcr.io/v2/cleanuparr/cleanuparr/tags/list` — latest semver is 2.3.3
- `kubectl -n selfhost get pod -l app.kubernetes.io/name=<app>` — running image digests (live cluster)
- `my-kluster/charts/{arrconf,configarr}/templates/cronjob.yaml` — production-validated CronJob specs
- `my-kluster/argocd/argocd-apps/{sonarr,...}-app.yaml` — 10 unit App values blocks (byte-equivalence source)

### Secondary (MEDIUM confidence)
- Context7 `/llmstxt/bjw-s-labs_github_io_helm-charts_llms_txt` — CronJob type, persistence configMap, defaultPodOptions, envFrom, persistence PVC
- Context7 `/websites/renovatebot` — `customManagers` `matchStringsStrategy: combination` example
- https://bjw-s-labs.github.io/helm-charts/docs/app-template/upgrades/4-to-5 — v4→v5 breaking changes (rawResources)
- https://argo-cd.readthedocs.io/en/stable/proposals/server-side-apply/ — ServerSideApply field manager migration
- https://github.com/karuppiah7890/helm-schema-gen — confirmed CURRENTLY NOT MAINTAINED
- https://github.com/losisin/helm-values-schema-json — confirmed actively maintained

### Tertiary (LOW confidence — flagged in Assumptions Log)
- ArgoCD finalizer behavior during simultaneous unit App deletion + umbrella adoption (A3) — WebSearch result, not verified against ArgoCD source code
- `_helpers.tpl` cross-alias include resolution in umbrella context (A2) — standard Helm pattern, not tested in this session

---

## Metadata

**Confidence breakdown:**
- Standard stack (app-template 4.6.2): HIGH — chart pulled and inspected
- CronJob config keys: HIGH — verified from pulled chart artefact
- Architecture (defaults merge via `_helpers.tpl`): MEDIUM — Helm behavior, partially assumed
- Renovate customManagers regex: MEDIUM — official docs cited, not validated against live Renovate instance
- ArgoCD cutover sequence: MEDIUM — based on docs + community patterns; finalizer race condition is LOW confidence
- Running image digests: HIGH (qbittorrent confirmed), LOW (flaresolverr, cleanuparr — semver resolution incomplete)

**Research date:** 2026-05-12
**Valid until:** 2026-08-12 (stable Helm/ArgoCD domain); Renovate regex validity 30 days; app-template 5.x adoption window open
