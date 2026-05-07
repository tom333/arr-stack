# Phase 2: Validation cluster - Pattern Map

**Mapped:** 2026-05-08
**Files analyzed:** 13 (10 with strong analogs, 1 with partial, 2 fresh artifacts)
**Analogs found:** 11 / 13

> **Cross-repo phase.** Every file is tagged `[arr-stack]` or `[my-kluster]`. The `my-kluster/charts/configarr/` tree is the canonical analog for nearly every Helm/ArgoCD artifact this phase creates — substitute `configarr` → `arrconf`, drop the PVC stanza, add `ARRCONF_DRY_RUN` env + explicit `args:` + `securityContext`.

---

## File Classification

| # | New / Modified File | Repo | Role | Data Flow | Closest Analog | Match Quality |
|---|---------------------|------|------|-----------|----------------|---------------|
| 1 | `charts/arrconf/Chart.yaml` | my-kluster | Helm chart manifest | static config | `my-kluster/charts/configarr/Chart.yaml` | **exact** (mirror, rename only) |
| 2 | `charts/arrconf/values.yaml` | my-kluster | Helm values (chart config) | static config | `my-kluster/charts/configarr/values.yaml` | **exact** (drop PVC, add `arrconfDryRun`, add Renovate annotation) |
| 3 | `charts/arrconf/files/arrconf.yml` | my-kluster | reconciler config (mounted) | static → ConfigMap | `arr-stack/examples/baseline-sonarr.yml` + `my-kluster/charts/configarr/files/config.yml` | **role-match** (different content, identical mount mechanism) |
| 4 | `charts/arrconf/templates/_helpers.tpl` | my-kluster | Helm helper template | template-render | `my-kluster/charts/configarr/templates/_helpers.tpl` | **exact** (s/configarr/arrconf/g) |
| 5 | `charts/arrconf/templates/cronjob.yaml` | my-kluster | K8s CronJob template | scheduled batch | `my-kluster/charts/configarr/templates/cronjob.yaml` | **exact** (mirror with 6 substitutions — see §Pattern Assignments #5) |
| 6 | `charts/arrconf/templates/configmap.yaml` | my-kluster | K8s ConfigMap template | template-render | `my-kluster/charts/configarr/templates/configmap.yaml` | **exact** (s/config.yml/arrconf.yml/) |
| 7 | `argocd/argocd-apps/arrconf-app.yaml` | my-kluster | ArgoCD Application manifest | GitOps pull | `my-kluster/argocd/argocd-apps/configarr-app.yaml` | **exact** (3 string substitutions) |
| 8 | `secrets/arrconf-secret.yaml` | my-kluster | Bootstrap K8s Secret | static config | `my-kluster/secrets/configarr-secret.yaml` | **exact** (rename + drop RADARR_API_KEY) |
| 9 | `snapshots/before-phase-2-2026-05-08/` (already exists, may need re-snapshot) | arr-stack | snapshot artifact | read-only API capture | `snapshots/baseline-2026-05-07/` | **exact** (same `tools/snapshot/snapshot.sh` script) |
| 10 | `snapshots/post-phase2-pr1-<date>/` | arr-stack | snapshot artifact | read-only API capture | `snapshots/baseline-2026-05-07/` | **exact** |
| 11 | `snapshots/post-phase2-pr2-<date>/` | arr-stack | snapshot artifact | read-only API capture | `snapshots/baseline-2026-05-07/` | **exact** |
| 12 | `snapshots/drift-test-<date>/` (optional) | arr-stack | snapshot artifact | read-only API capture | `snapshots/baseline-2026-05-07/` | **exact** |
| 13 | `.planning/phases/02-arrconf-cluster-validation/evidence/drift-demo-<date>.log` | arr-stack | runbook evidence (kubectl logs capture) | log artifact | — | **no analog** (new artifact type) |
| — | `tools/snapshot/diff.sh` (optional, deferred) | arr-stack | shell helper | filter | — | **deferred** (not in scope per CONTEXT.md §Deferred) |
| — | Git tag `v0.1.0` + GitHub Release notes | arr-stack | release artifact | git ref | (none — first tag) | **no analog** (one-time bootstrap) |

---

## Pattern Assignments

### 1. `charts/arrconf/Chart.yaml` [my-kluster] — Helm chart manifest

**Analog:** `/home/moi/projets/perso/my-kluster/charts/configarr/Chart.yaml`

**Full analog content** (lines 1–7, the entire file):
```yaml
apiVersion: v2
name: configarr
description: Configarr — synchronisation TRaSH-Guides / Recyclarr templates pour Sonarr et Radarr
type: application
version: 0.1.0
appVersion: "1.16.0"
```

**Substitutions:**

| Field | Source | Target |
|-------|--------|--------|
| `name` | `configarr` | `arrconf` |
| `description` | TRaSH-Guides text | `arrconf — config-as-code reconciler for Sonarr/Radarr/Prowlarr/qBit/Seerr (Phase 2 scope: Sonarr download_clients only)` |
| `version` | `0.1.0` | `0.1.0` (chart version, independent of app — keep) |
| `appVersion` | `"1.16.0"` | `"0.1.0"` (matches Phase 1 image tag) |
| `apiVersion` / `type` | `v2` / `application` | unchanged |

**Pitfalls:** Quote `appVersion` (Helm requires string for `appVersion`, even if it looks numeric). Don't drop the leading `v` — wait, configarr's appVersion has no `v` prefix → keep `"0.1.0"` (numeric only).

---

### 2. `charts/arrconf/values.yaml` [my-kluster] — Helm values

**Analog:** `/home/moi/projets/perso/my-kluster/charts/configarr/values.yaml`

**Full analog content** (lines 1–27):
```yaml
image:
  repository: ghcr.io/raydak-labs/configarr
  tag: "1.16.0"
  pullPolicy: IfNotPresent

schedule: "0 */4 * * *"
timezone: "Europe/Paris"

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 50m
    memory: 128Mi

cache:
  storageClass: microk8s-hostpath
  size: 1Gi

# Secret manuel appliqué via secrets/configarr-secret.yaml (kubectl apply).
# Sera migré vers ESO/Akeyless en même temps que les autres secrets.
apiKeysSecret: configarr-env

successfulJobsHistoryLimit: 1
failedJobsHistoryLimit: 2
```

**Substitutions / additions:**

| Action | What | Why |
|--------|------|-----|
| **REPLACE** | `image.repository: ghcr.io/raydak-labs/configarr` → `ghcr.io/tom333/arr-stack-arrconf` | Different upstream image |
| **REPLACE** | `image.tag: "1.16.0"` → `"0.1.0"` | Phase 1 release tag (verify metadata-action — Pitfall 2 strips `v`; if `gh api …/versions` shows `v0.1.0`, pin that instead) |
| **ADD** above `image:` block | `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` | CLAUDE.md "Annotations Renovate (CRITIQUE)" — without it, no version bumps |
| **REPLACE** | `apiKeysSecret: configarr-env` → `arrconf-env` | Phase 2 secret name (D-29) |
| **DELETE** | entire `cache:` block (lines 17–19) | arrconf has no TRaSH-Guides Git cache need; idempotent reconciler |
| **ADD** | `arrconfDryRun: true` (with comment block — D-28 PR1 default) | Two-PR protocol toggle |
| **ADD** | `startingDeadlineSeconds: 600` | D-23 (10-min tolerance) |
| **KEEP unchanged** | `schedule`, `timezone`, `resources`, `successfulJobsHistoryLimit`, `failedJobsHistoryLimit` | Phase 2 mirrors configarr — same cadence, same resource budget |

**Final shape** (per RESEARCH.md Code Example 2):
```yaml
image:
  # renovate: image=ghcr.io/tom333/arr-stack-arrconf
  repository: ghcr.io/tom333/arr-stack-arrconf
  tag: "0.1.0"
  pullPolicy: IfNotPresent

schedule: "0 */4 * * *"
timezone: "Europe/Paris"
startingDeadlineSeconds: 600

# Two-PR dry-run protocol (D-28):
#   PR1: arrconfDryRun: true
#   PR2: arrconfDryRun: false
arrconfDryRun: true

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 50m
    memory: 128Mi

# Manual bootstrap secret (D-29):
#   kubectl apply -f my-kluster/secrets/arrconf-secret.yaml BEFORE merging PR1
apiKeysSecret: arrconf-env

successfulJobsHistoryLimit: 1
failedJobsHistoryLimit: 2
```

**Pitfalls:**
- Do NOT use `:latest` (CLAUDE.md hard rule).
- The `# renovate: image=...` annotation MUST be on the line immediately above `repository:` — Renovate's customManager regex matches strict adjacency.
- PR2 changes ONLY `arrconfDryRun: true` → `false`; nothing else. Atomic revert via `git revert`.

---

### 3. `charts/arrconf/files/arrconf.yml` [my-kluster] — reconciler config

**Primary analog:** `/home/moi/projets/perso/arr-stack/examples/baseline-sonarr.yml` (Phase 1 output — already in arrconf YAML format)
**Mount-pattern analog:** `/home/moi/projets/perso/my-kluster/charts/configarr/files/config.yml` (same `.Files.Get` injection pattern)

**Source content** (`examples/baseline-sonarr.yml`, lines 1–47 — qBittorrent download_client block):
```yaml
# yaml-language-server: $schema=../schemas/arrconf-schema.json
apps:
  sonarr:
    main:
      base_url: http://sonarr.selfhost.svc.cluster.local:8989
      download_clients:
        prune: false
        items:
          - name: qBittorrent
            enable: true
            protocol: torrent
            priority: 1
            implementation: QBittorrent
            configContract: QBittorrentSettings
            fields:
              - name: host
                value: qbittorrent.selfhost.svc.cluster.local
              - name: port
                value: 8080
              # ... (full qBit fields block)
            tags: []
            removeCompletedDownloads: true
            removeFailedDownloads: true
```

**Substitutions:**

| Action | What | Why |
|--------|------|-----|
| **MODELINE** | `# yaml-language-server: $schema=../schemas/arrconf-schema.json` → drop OR replace with URL `https://raw.githubusercontent.com/tom333/arr-stack/v0.1.0/schemas/arrconf-schema.json` | Relative path doesn't resolve from my-kluster (no schema there). RESEARCH.md Pattern 2 recommends Option A (drop). |
| **`base_url`** | `http://sonarr.selfhost.svc.cluster.local:8989` | VERIFIED via `my-kluster/argocd/argocd-apps/sonarr-app.yaml` lines 30–35: service `sonarr`, port `8989`. Keep as-is. |
| **`prune`** | `false` | D-04 carry-forward + Phase 2 scope (no deletion) |
| **`tags`** | `[]` | NOT `["arrconf-managed"]` — the tag is auto-managed by the reconciler (D-02), not user-declared in YAML. Keep empty. |
| **Sensitive fields** | `value: '***REDACTED***'` for `username` / `password` | Real credentials NEVER in YAML. arrconf reads them from env (CLAUDE.md "Aucune lecture de fichier de secrets"). |

**Pitfalls:**
- The `qbittorrent.selfhost.svc.cluster.local` host MUST resolve — verify against `my-kluster/argocd/argocd-apps/qbittorrent-app.yaml` service name before PR1.
- D-25 says minimal Sonarr-only — do NOT add `radarr:` or `prowlarr:` stubs.
- D-12 (`ScopeViolationError`) is enforced by the binary; the YAML schema also rejects `quality_profiles`, `custom_formats`, etc.

**Mount mechanism** (from configarr `templates/configmap.yaml` lines 1–9 — see #6 below):
```yaml
data:
  arrconf.yml: |-
{{ .Files.Get "files/arrconf.yml" | indent 4 }}
```

---

### 4. `charts/arrconf/templates/_helpers.tpl` [my-kluster] — Helm helpers

**Analog:** `/home/moi/projets/perso/my-kluster/charts/configarr/templates/_helpers.tpl`

**Full analog content** (lines 1–50 — pure mechanical rename):
```gotemplate
{{/*
Expand the name of the chart.
*/}}
{{- define "configarr.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "configarr.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Chart name + version label.
*/}}
{{- define "configarr.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "configarr.labels" -}}
helm.sh/chart: {{ include "configarr.chart" . }}
{{ include "configarr.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels.
*/}}
{{- define "configarr.selectorLabels" -}}
app.kubernetes.io/name: {{ include "configarr.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
```

**Substitutions:** Single global rename `configarr.` → `arrconf.` — affects 5 `define` blocks AND 3 `include` calls inside the file:

```bash
sed -i 's/configarr\./arrconf./g' charts/arrconf/templates/_helpers.tpl
```

The 5 helpers consumed by `cronjob.yaml` and `configmap.yaml`:
- `arrconf.name`
- `arrconf.fullname`
- `arrconf.chart`
- `arrconf.labels`
- `arrconf.selectorLabels`

**Pitfalls:** None. This is the safest substitution in the phase. After rename, `helm template charts/arrconf/` should render identically except for `app.kubernetes.io/name: arrconf` instead of `configarr`.

---

### 5. `charts/arrconf/templates/cronjob.yaml` [my-kluster] — CronJob template

**Analog:** `/home/moi/projets/perso/my-kluster/charts/configarr/templates/cronjob.yaml`

**Full analog content** (lines 1–47):
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: {{ include "configarr.fullname" . }}
  labels:
    {{- include "configarr.labels" . | nindent 4 }}
spec:
  schedule: {{ .Values.schedule | quote }}
  successfulJobsHistoryLimit: {{ .Values.successfulJobsHistoryLimit }}
  failedJobsHistoryLimit: {{ .Values.failedJobsHistoryLimit }}
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        metadata:
          labels:
            {{- include "configarr.selectorLabels" . | nindent 12 }}
          annotations:
            checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
        spec:
          restartPolicy: Never
          containers:
            - name: configarr
              image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
              imagePullPolicy: {{ .Values.image.pullPolicy }}
              tty: true
              env:
                - name: TZ
                  value: {{ .Values.timezone | quote }}
              envFrom:
                - secretRef:
                    name: {{ .Values.apiKeysSecret }}
              volumeMounts:
                - name: config
                  mountPath: /app/config/config.yml
                  subPath: config.yml
                - name: cache
                  mountPath: /app/repos
              resources:
                {{- toYaml .Values.resources | nindent 16 }}
          volumes:
            - name: config
              configMap:
                name: {{ include "configarr.fullname" . }}
            - name: cache
              persistentVolumeClaim:
                claimName: {{ include "configarr.fullname" . }}-cache
```

**Substitutions (6 distinct changes):**

| # | Action | What | Why |
|---|--------|------|-----|
| 1 | **RENAME** | `configarr.` → `arrconf.` (3 occurrences: `fullname`, `labels`, `selectorLabels`, `fullname` again in volume) | Helper rename consistency |
| 2 | **RENAME** | container `name: configarr` → `arrconf` | Pod-level identifier |
| 3 | **REMOVE** | `tty: true` (line 26) | configarr uses `tty: true` for pretty output; arrconf in CronJob context wants JSON (non-TTY) — RESEARCH.md Pitfall 10 |
| 4 | **ADD** below `imagePullPolicy:` | `args: ["apply", "--config", "/app/config/arrconf.yml", "--apps", "sonarr"]` | Phase 1 Dockerfile CMD is `["apply", "--help"]`; explicit args needed (RESEARCH.md Code Example 1) |
| 5 | **ADD** to `env:` block | `- name: ARRCONF_DRY_RUN`<br>&nbsp;&nbsp;`value: {{ .Values.arrconfDryRun \| quote }}` | D-28 two-PR protocol toggle |
| 6 | **REPLACE** mount path | `mountPath: /app/config/config.yml` + `subPath: config.yml` → `mountPath: /app/config/arrconf.yml` + `subPath: arrconf.yml` | D-27 |
| 7 | **DELETE** | the `cache` volumeMount (lines 37–38) AND the `cache` volume (lines 45–47) | arrconf has no PVC cache need; mirror PVC file is also deleted |
| 8 | **ADD** under `spec:` (above `restartPolicy:`) | `securityContext:`<br>&nbsp;&nbsp;`runAsNonRoot: true`<br>&nbsp;&nbsp;`runAsUser: 1000`<br>&nbsp;&nbsp;`runAsGroup: 1000` | CONTEXT.md "Pod securityContext" + defense-in-depth (image already runs as 1000) |
| 9 | **ADD** under `spec:` | `startingDeadlineSeconds: {{ .Values.startingDeadlineSeconds \| default 600 }}` | D-23 |

**Final target** (per RESEARCH.md Code Example 1, lines 609–659):
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: {{ include "arrconf.fullname" . }}
  labels:
    {{- include "arrconf.labels" . | nindent 4 }}
spec:
  schedule: {{ .Values.schedule | quote }}
  successfulJobsHistoryLimit: {{ .Values.successfulJobsHistoryLimit }}
  failedJobsHistoryLimit: {{ .Values.failedJobsHistoryLimit }}
  startingDeadlineSeconds: {{ .Values.startingDeadlineSeconds | default 600 }}
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        metadata:
          labels:
            {{- include "arrconf.selectorLabels" . | nindent 12 }}
          annotations:
            checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
        spec:
          restartPolicy: Never
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            runAsGroup: 1000
          containers:
            - name: arrconf
              image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
              imagePullPolicy: {{ .Values.image.pullPolicy }}
              args: ["apply", "--config", "/app/config/arrconf.yml", "--apps", "sonarr"]
              env:
                - name: TZ
                  value: {{ .Values.timezone | quote }}
                - name: ARRCONF_DRY_RUN
                  value: {{ .Values.arrconfDryRun | quote }}
              envFrom:
                - secretRef:
                    name: {{ .Values.apiKeysSecret }}
              volumeMounts:
                - name: config
                  mountPath: /app/config/arrconf.yml
                  subPath: arrconf.yml
              resources:
                {{- toYaml .Values.resources | nindent 16 }}
          volumes:
            - name: config
              configMap:
                name: {{ include "arrconf.fullname" . }}
```

**Pitfalls:**
- `concurrencyPolicy: Forbid` only applies to scheduler-created Jobs, NOT to `kubectl create job --from=cronjob/arrconf …` (RESEARCH.md Pitfall 4). Drift demo uses manual creation — document this in runbook.
- `checksum/config` annotation on `jobTemplate.spec.template` is largely ornamental for CronJobs (RESEARCH.md Pitfall 5). Keep it (harmless, mirrors configarr) but don't expect it to "force" anything.
- `args:` MUST be a JSON array (not block scalar) to override the image's CMD reliably.

---

### 6. `charts/arrconf/templates/configmap.yaml` [my-kluster] — ConfigMap template

**Analog:** `/home/moi/projets/perso/my-kluster/charts/configarr/templates/configmap.yaml`

**Full analog content** (lines 1–9):
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "configarr.fullname" . }}
  labels:
    {{- include "configarr.labels" . | nindent 4 }}
data:
  config.yml: |-
{{ .Files.Get "files/config.yml" | indent 4 }}
```

**Substitutions:**

| Action | What |
|--------|------|
| **RENAME** | `configarr.fullname` → `arrconf.fullname`, `configarr.labels` → `arrconf.labels` |
| **REPLACE** | data key `config.yml` → `arrconf.yml` |
| **REPLACE** | `.Files.Get "files/config.yml"` → `.Files.Get "files/arrconf.yml"` |

**Pitfalls:**
- The `indent 4` after `.Files.Get` MUST match the ConfigMap data block indentation. Don't change it.
- The `|-` (chomp strip) avoids trailing newline issues; keep as-is.

---

### 7. `argocd/argocd-apps/arrconf-app.yaml` [my-kluster] — ArgoCD Application

**Analog:** `/home/moi/projets/perso/my-kluster/argocd/argocd-apps/configarr-app.yaml`

**Full analog content** (lines 1–23, the entire file):
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: configarr
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  destination:
    namespace: selfhost
    server: https://kubernetes.default.svc
  project: selfhost-project
  source:
    repoURL: https://github.com/tom333/my-kluster.git
    targetRevision: HEAD
    path: charts/configarr
  syncPolicy:
    syncOptions:
      - CreateNamespace=false
      - ServerSideApply=true
    automated:
      selfHeal: true
      prune: true
```

**Substitutions (3 changes):**

| Field | Source | Target |
|-------|--------|--------|
| `metadata.name` | `configarr` | `arrconf` |
| `spec.source.path` | `charts/configarr` | `charts/arrconf` |
| `spec.source.repoURL` | `https://github.com/tom333/my-kluster.git` | unchanged (D-26) |

**Everything else unchanged** — `selfhost-project` (verified A9 in RESEARCH.md), `selfhost` namespace, both `automated.selfHeal: true` AND `automated.prune: true`, both syncOptions.

**Pitfalls:**
- `prune: true` will be relevant during Phase 4 umbrella migration (Pitfall 6 in RESEARCH.md) — flag for Phase 4, not actionable here.
- `selfHeal: true` reverts manual `kubectl edit` within ~3min (Pitfall 8). All changes via PR only.
- Operator MUST `kubectl apply -f my-kluster/secrets/arrconf-secret.yaml` BEFORE merging PR1 (Pitfall 3) — ArgoCD doesn't manage that secret.

---

### 8. `secrets/arrconf-secret.yaml` [my-kluster] — Bootstrap Secret

**Analog:** `/home/moi/projets/perso/my-kluster/secrets/configarr-secret.yaml`

**Full analog content** (lines 1–9, the entire file):
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: configarr-env
  namespace: selfhost
type: Opaque
stringData:
  RADARR_API_KEY: "9a39fe509a6f489183be7538cdfff498"
  SONARR_API_KEY: "7996acf930d34ab88a992f2981097081"
```

**Substitutions:**

| Field | Source | Target |
|-------|--------|--------|
| `metadata.name` | `configarr-env` | `arrconf-env` |
| `stringData` | 2 keys (RADARR + SONARR) | **only** `SONARR_API_KEY` — D-29 (least privilege, Phase 2 scope) |
| `SONARR_API_KEY` value | `"7996acf930d34ab88a992f2981097081"` (configarr's) | **same value** (RESEARCH.md Open Q3 — both reconcilers target the same Sonarr instance, sharing is operationally fine for Phase 2; per-service segregation deferred to Phase 8 ESO) |

**Final shape** (per CONTEXT.md D-29):
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: arrconf-env
  namespace: selfhost
type: Opaque
stringData:
  SONARR_API_KEY: "<api key Sonarr récupérée via UI bootstrap>"
```

**Pitfalls:**
- Plaintext API key is committed to my-kluster (existing pattern — `configarr-secret.yaml` line 9 visible in `git log`). RESEARCH.md Open Q7: NOT a Phase 2 problem, predates this work. SOPS migration belongs to Phase 8.
- This file is committed in **my-kluster only**, NEVER in arr-stack (CLAUDE.md "Ne pas committer de secrets").
- Manual lifecycle: `kubectl apply -f` BEFORE ArgoCD sync (Pitfall 3 in RESEARCH.md). PR description must include this command in pre-merge checklist.
- Subsequent phases bump the secret (Phase 3: + RADARR_API_KEY + PROWLARR_API_KEY; Phase 5: + QBT_USER + QBT_PASS; Phase 6: + SEERR_API_KEY; Phase 7: + JELLYFIN_API_KEY) — D-29.

---

### 9–12. Snapshot artifacts [arr-stack]

**Files:**
- `snapshots/before-phase-2-2026-05-08/` (already exists empty per `ls`; needs population)
- `snapshots/post-phase2-pr1-<date>/`
- `snapshots/post-phase2-pr2-<date>/`
- `snapshots/drift-test-<date>/` (optional)

**Analog:** `/home/moi/projets/perso/arr-stack/snapshots/baseline-2026-05-07/sonarr/` — 17 JSON files captured by `tools/snapshot/snapshot.sh` (Phase 0 deliverable).

**Capture mechanism** (already built):
```bash
# From CLAUDE.md "Workflow snapshot (CRITIQUE)"
tools/snapshot/snapshot.sh --output snapshots/before-phase-2-2026-05-08/
tools/snapshot/snapshot.sh --output snapshots/post-phase2-pr1-$(date +%F)/
tools/snapshot/snapshot.sh --output snapshots/post-phase2-pr2-$(date +%F)/
tools/snapshot/snapshot.sh --output snapshots/drift-test-$(date +%FT%H%M)/
```

**Snapshot directory shape** (from `baseline-2026-05-07/sonarr/`):
```
snapshots/<name>/sonarr/
├── config_downloadclient.json
├── config_host.json
├── config_indexer.json
├── config_mediamanagement.json
├── config_naming.json
├── config_ui.json
├── customformat.json
├── downloadclient.json     ← key file for Phase 2 success criterion #3 + #4
├── importlist.json
├── indexer.json
├── metadata.json
├── notification.json
├── qualityprofile.json
├── remotepathmapping.json
├── rootfolder.json
├── system_status.json
└── tag.json                 ← key file for Phase 2 success criterion #4 (arrconf-managed tag)
```

**Validation pattern** (RESEARCH.md Pattern 5):
```bash
# Success criterion #3: zero writes during dry-run
diff -r snapshots/before-phase-2-2026-05-08/sonarr/ snapshots/post-phase2-pr1-<date>/sonarr/
# Expected: empty output

# Success criterion #4: managed tag present after PR2
jq '.[].name' snapshots/post-phase2-pr2-<date>/sonarr/tag.json
# Expected: includes "arrconf-managed"

jq '.[].tags' snapshots/post-phase2-pr2-<date>/sonarr/downloadclient.json
# Expected: includes the id of the arrconf-managed tag
```

**Pitfalls:**
- D-30 #1 says re-snapshot CAN be identical to `baseline-2026-05-07` if no UI change happened between — in that case, add a `README.md` in `before-phase-2-2026-05-08/` noting "identique à baseline". The current `before-phase-2-2026-05-08/` directory exists with empty subdirs — needs actual capture.
- All 4 snapshot dirs MUST be committed in Git (CLAUDE.md "Ne pas ignorer `snapshots/` dans `.gitignore`").
- The `tag.json` baseline currently shows `[]` (empty) — Phase 1 round-trip created and reverted the tag during dump→apply test. Post-PR2 it should show `[{"id": 1, "label": "arrconf-managed"}]`.

---

### 13. `evidence/drift-demo-<date>.log` [arr-stack] — runbook evidence

**Role:** runbook evidence (kubectl logs JSON capture)
**Analog:** **none** — first artifact of this kind in the repo.
**Match Quality:** no analog (state new)

**Capture mechanism** (RESEARCH.md Pattern 4 + Code Example 4):
```bash
# After inducing drift (priority: 1 → 5 via curl PUT to Sonarr API)
kubectl create job --from=cronjob/arrconf arrconf-drift-demo-$(date +%s) -n selfhost
kubectl wait --for=condition=complete job/arrconf-drift-demo-<...> -n selfhost --timeout=120s
kubectl logs job/arrconf-drift-demo-<...> -n selfhost > \
  .planning/phases/02-arrconf-cluster-validation/evidence/drift-demo-$(date +%F).log
```

**Expected log content** (structlog JSON, RESEARCH.md Pattern 4):
```json
{"event": "managed_tag_present", "tag_id": 1, "level": "info"}
{"event": "fetched_current", "resource": "download_clients", "count": 1}
{"event": "diff_computed", "action": "UPDATE", "name": "qBittorrent", "diff": {"priority": {"current": 5, "desired": 1}}}
{"event": "applying", "action": "UPDATE", "name": "qBittorrent", "dry_run": false}
{"event": "applied", "action": "UPDATE", "name": "qBittorrent", "id": 1}
{"event": "reconcile_complete", "app": "sonarr", "actions_taken": [{"action": "UPDATE", "name": "qBittorrent"}]}
```

**Pitfalls:**
- The `evidence/` subdirectory does NOT exist yet — planner must create.
- File MUST contain literal JSON (not pretty-printed) to satisfy "logs JSON visibles" success criterion #5. RESEARCH.md Pitfall 10: `kubectl logs` is non-interactive → JSON activates correctly.
- Linked from final Phase 2 commit message (CONTEXT.md "Le commit Phase 2 final doit linker une capture des logs JSON montrant l'override").

---

## Shared Patterns

### Shared Pattern 1: GitOps strict — never `kubectl apply` chart resources

**Source:** CLAUDE.md "Ce que tu NE dois PAS faire" + my-kluster `CLAUDE.md`
**Apply to:** files #1–#7 (everything in `my-kluster/charts/arrconf/` and `my-kluster/argocd/argocd-apps/`)

**Rule:** All chart-managed resources (Chart.yaml, values.yaml, templates/, ArgoCD App) flow through PR + ArgoCD sync. NEVER `helm install`, NEVER `kubectl apply -f charts/arrconf/...`.

**Single exception:** file #8 (`secrets/arrconf-secret.yaml`) is the manual bootstrap — applied via `kubectl apply -f` BEFORE PR1 sync, never templated through Helm.

```bash
# ALLOWED (manual bootstrap):
kubectl apply -f my-kluster/secrets/arrconf-secret.yaml

# FORBIDDEN:
helm install arrconf my-kluster/charts/arrconf/
kubectl apply -f my-kluster/charts/arrconf/templates/cronjob.yaml
```

---

### Shared Pattern 2: Secret injection via `envFrom: secretRef`

**Source:** `my-kluster/charts/configarr/templates/cronjob.yaml` lines 30–32
**Apply to:** file #5 (`templates/cronjob.yaml`)

```yaml
envFrom:
  - secretRef:
      name: {{ .Values.apiKeysSecret }}
```

**Why:** CLAUDE.md "Variables d'environnement" — "Aucune lecture de fichier de secrets — uniquement env." All API keys reach the binary as env vars. arrconf is coded to read `os.environ["SONARR_API_KEY"]`, never a file path.

---

### Shared Pattern 3: Renovate annotation above every image reference

**Source:** CLAUDE.md "Conventions Helm — Annotations Renovate (CRITIQUE)"
**Apply to:** file #2 (`values.yaml`) — the only file in Phase 2 that references an image.

```yaml
image:
  # renovate: image=ghcr.io/tom333/arr-stack-arrconf
  repository: ghcr.io/tom333/arr-stack-arrconf
  tag: "0.1.0"
```

**Pitfall:** The annotation MUST be on the line immediately above `repository:` — strict adjacency required by Renovate's customManager regex. Don't insert a blank line between them.

---

### Shared Pattern 4: ArgoCD `automated.selfHeal + prune` everywhere

**Source:** `my-kluster/argocd/argocd-apps/configarr-app.yaml` lines 17–23
**Apply to:** file #7 (`argocd-apps/arrconf-app.yaml`)

```yaml
syncPolicy:
  syncOptions:
    - CreateNamespace=false
    - ServerSideApply=true
  automated:
    selfHeal: true
    prune: true
```

**Behavior implications:**
- `selfHeal: true` reverts any `kubectl edit` of cluster resources within ~3 min (Pitfall 8 — debugging discipline).
- `prune: true` will become relevant during Phase 4 umbrella migration (Pitfall 6 — flag for Phase 4 plan).
- `ServerSideApply=true` — better field-management semantics than client-side merge (cluster-wide convention).
- `CreateNamespace=false` — `selfhost` already exists; no auto-creation.

---

### Shared Pattern 5: Snapshot-based validation (ADR-6 discipline)

**Source:** CLAUDE.md "Workflow snapshot (CRITIQUE)" + `tools/snapshot/snapshot.sh`
**Apply to:** files #9–#12 + plan task ordering (re-snapshot before any cluster-modifying step).

**Discipline rules:**
1. Re-snapshot BEFORE any new-scope test (Phase 2 PR1 = new scope).
2. Re-snapshot AFTER any potentially-mutating run (post-PR1 dry-run, post-PR2 apply, post-drift-demo).
3. ALL snapshots committed in Git (NOT in `.gitignore`).
4. `diff -r` between snapshot dirs is the ground-truth for "did anything change?"

**Bash invocation pattern** (shared across all 4 snapshot files):
```bash
tools/snapshot/snapshot.sh --output snapshots/<phase-name>-<date>/
git add snapshots/<phase-name>-<date>/
git commit -m "snapshot(02): <phase-name> capture"
```

---

### Shared Pattern 6: Helm helper `include` chain

**Source:** `my-kluster/charts/configarr/templates/_helpers.tpl` (5 helpers) consumed by `cronjob.yaml` + `configmap.yaml`
**Apply to:** files #4 (definer), #5 + #6 (consumers).

**Consumer pattern:**
```gotemplate
metadata:
  name: {{ include "arrconf.fullname" . }}
  labels:
    {{- include "arrconf.labels" . | nindent 4 }}
```

**Selector pattern (in pod template):**
```gotemplate
metadata:
  labels:
    {{- include "arrconf.selectorLabels" . | nindent 12 }}
```

**Coherence rule:** If you rename a helper (`configarr.X` → `arrconf.X`) in `_helpers.tpl`, you MUST update EVERY `include` call in EVERY template. The `sed -i 's/configarr\./arrconf./g'` global rename catches all consumers in one pass.

---

## No Analog Found

Files with no close match in the codebase:

| File | Repo | Role | Reason | Mitigation |
|------|------|------|--------|------------|
| `evidence/drift-demo-<date>.log` | arr-stack | runbook evidence | First "evidence" artifact in `.planning/phases/*/evidence/` | Use RESEARCH.md Pattern 4 + Code Example 4 directly; the file is just `kubectl logs` output redirected to disk. No template needed. |
| Git tag `v0.1.0` + (optional) GitHub Release notes | arr-stack | release artifact | First release of the project | Standard `git tag vX.Y.Z && git push origin vX.Y.Z` per CLAUDE.md "Release". `arrconf-image.yml` workflow auto-triggers on `v*` tags. RESEARCH.md Pitfall 9 details verification. |
| `tools/snapshot/diff.sh` (optional, deferred) | arr-stack | shell helper | New utility | **DEFERRED** per CONTEXT.md "Deferred Ideas" — `diff -r` is sufficient for Phase 2. If planner wants it, the closest analog would be `tools/snapshot/snapshot.sh` for shell style (set -euo pipefail, refus root, args parsing). |

---

## Cross-Repo Coupling

Phase 2 spans both repos with one unidirectional contract: **the image tag**.

```
arr-stack: git tag v0.1.0 → CI publishes ghcr.io/tom333/arr-stack-arrconf:0.1.0
                                     │
                                     │ (manual GHCR public toggle — Pitfall 1)
                                     ▼
my-kluster: PR1 pins values.yaml `image.tag: "0.1.0"` → ArgoCD pulls
```

**Plan ordering enforcement:**
1. arr-stack `git tag v0.1.0 && git push --tags` (file: tag, not a checked-in artifact)
2. CI `arrconf-image.yml` runs (verify with `gh run list`)
3. GHCR public toggle (manual UI step — Pitfall 1)
4. Verify pull anonymously: `docker logout ghcr.io && docker pull ghcr.io/tom333/arr-stack-arrconf:0.1.0`
5. Verify exact tag string (Pitfall 2): `gh api /users/tom333/packages/container/arr-stack-arrconf/versions | jq` — confirm `0.1.0` (no `v`) before pinning in `values.yaml`
6. ONLY THEN open my-kluster PR1

**No reverse coupling:** my-kluster never pushes back to arr-stack. arr-stack is binary-contract publisher only.

---

## Metadata

**Analog search scope:**
- `/home/moi/projets/perso/my-kluster/charts/configarr/` (full tree — 6 files)
- `/home/moi/projets/perso/my-kluster/argocd/argocd-apps/` (focused: `configarr-app.yaml`, `sonarr-app.yaml`)
- `/home/moi/projets/perso/my-kluster/secrets/` (focused: `configarr-secret.yaml`)
- `/home/moi/projets/perso/arr-stack/examples/baseline-sonarr.yml`
- `/home/moi/projets/perso/arr-stack/snapshots/baseline-2026-05-07/sonarr/` (structure)
- `/home/moi/projets/perso/arr-stack/tools/snapshot/snapshot.sh`

**Files scanned:** 11 analog files read in full + structure of 1 baseline directory + structure of 1 partial directory (`before-phase-2-2026-05-08/` — empty subdirs awaiting capture)

**Pattern extraction date:** 2026-05-08

**Decisions referenced:** D-23 through D-30 (CONTEXT.md), D-01/D-02/D-04/D-07/D-12 carry-forward (Phase 1), ADR-3/ADR-5/ADR-6 (spec.md), REQ-drift-detection / REQ-bootstrap-exception / REQ-secret-management (REQUIREMENTS.md).
