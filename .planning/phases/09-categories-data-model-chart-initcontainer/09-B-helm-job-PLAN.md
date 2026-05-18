---
phase: 09-categories-data-model-chart-initcontainer
plan: 09-B-helm-job
type: execute
wave: 1
depends_on: []
files_modified:
  - charts/arr-stack/templates/categories-init-job.yaml
autonomous: true
requirements:
  - REQ-filesystem-initcontainer
requirements_addressed:
  - REQ-filesystem-initcontainer
tags:
  - helm
  - chart
  - kubernetes
  - job

must_haves:
  truths:
    - "A new Helm-hooked Job template exists at charts/arr-stack/templates/categories-init-job.yaml and renders one mkdir step per categories[] entry in charts/arr-stack/files/arrconf.yml."
    - "The Job uses .Files.Get 'files/arrconf.yml' | fromYaml at template-render time (single-source pattern — D-08 pivot blessed by 09-RESEARCH.md Q1). No new values.yaml key, no CI sync gate."
    - "The Job container runs as runAsUser: 1000, runAsGroup: 1000, fsGroup: 1000 (D-12); image is pinned to busybox:1.36.1 (D-10); the # renovate: image=docker.io/busybox annotation sits directly above the image line (D-11)."
    - "Hook annotations helm.sh/hook: pre-install,pre-upgrade and helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded are present (D-07)."
    - "helm lint passes; kubeconform -strict -ignore-missing-schemas passes; the rendered Job manifest carries the locked hook annotations + image pin + security context + PVC mount under Wave 1 state (no categories in arrconf.yml yet → 0 printf lines rendered; the 20-line render is verified by Plan C Task C3 once Plan C lands the categories block)."
  artifacts:
    - path: "charts/arr-stack/templates/categories-init-job.yaml"
      provides: "Helm-hooked Job that creates /media/<name> for every category at install/upgrade"
      min_lines: 50
      contains: "media_dir_ensured"
  key_links:
    - from: "charts/arr-stack/templates/categories-init-job.yaml"
      to: "charts/arr-stack/files/arrconf.yml"
      via: ".Files.Get 'files/arrconf.yml' | fromYaml — resolves at template-render time before any pod runs (proven viable by 09-RESEARCH.md Q1)"
      pattern: "\\.Files\\.Get \"files/arrconf\\.yml\""
    - from: "charts/arr-stack/templates/categories-init-job.yaml"
      to: "media-nas-pvc"
      via: "spec.template.spec.volumes[].persistentVolumeClaim.claimName"
      pattern: "claimName: media-nas-pvc"
---

<objective>
Create the standalone Helm-hooked Job template that materializes the 10 `/media/<name>` directories on the NFS PVC before any media-app pod starts.

Purpose: This is the **filesystem layer** counterpart to Plan A's data contract. After this plan, every `helm install` / `helm upgrade` of `arr-stack` ensures the directories needed by Phase 10's propagators (Sonarr root_folders, Radarr root_folders, qBit savePaths, Jellyfin PathInfos) already exist. Idempotent by design (`mkdir -p` + `if [ -d ]` guard).

Output:
- `charts/arr-stack/templates/categories-init-job.yaml` (NEW — single file, ~60 lines)

D-NN coverage (locked decisions implemented):
- **D-06** — Standalone Job, NOT per-controller initContainer (single audit trail, one Job per release).
- **D-07** — Helm hook annotations: `pre-install,pre-upgrade` + `before-hook-creation,hook-succeeded`. Failed Jobs persist for debugging.
- **D-08 (pivoted by RESEARCH.md Q1)** — Single-source: Job reads `categories[]` directly from `charts/arr-stack/files/arrconf.yml` via `.Files.Get | fromYaml` at template-render time. NO new `values.yaml` key, NO CI sync gate.
- **D-09** — JSON-line log: `{"event":"media_dir_ensured","path":"...","created":<bool>,"existed":<bool>}\n` per directory; snapshot anti-leak grep stays compatible.
- **D-10** — Image pinned `busybox:1.36.1`. No `:latest`.
- **D-11** — `# renovate: image=docker.io/busybox` annotation directly above the image line.
- **D-12** — Pod-level `securityContext: runAsUser/runAsGroup/fsGroup: 1000`. NFS uid-1000 mkdir proven viable by 09-RESEARCH.md Q2 (existing snapshots show accessible=true for every /media/* path with the same uid).
- **D-13** — This plan ships ZERO Python code; reconcilers are not touched.

Boundary: Plan B does NOT modify `charts/arr-stack/files/arrconf.yml` (Plan C's scope) — it reads it. At Wave 1 execution time, `files/arrconf.yml` does NOT yet contain a `categories:` block, so `.Files.Get | fromYaml | .categories` will resolve to nil. The Job MUST handle this case gracefully (zero iterations, zero mkdir, zero log lines) — `{{- range $cat := $cfg.categories }}` over a nil map is a no-op in Helm/Sprig.

After Plan C adds the 10-entry block, the same Job template renders 10 mkdir steps with no additional code change. This is the design payoff of the single-source pivot. **The 20-printf-line render check belongs to Plan C Task C3** (cross-plan integration verification), not Plan B (Plan B cannot evaluate it at Wave 1 exit time because Plan C has not yet shipped the categories block).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/09-categories-data-model-chart-initcontainer/09-CONTEXT.md
@.planning/phases/09-categories-data-model-chart-initcontainer/09-RESEARCH.md
@.planning/phases/09-categories-data-model-chart-initcontainer/09-PATTERNS.md
@.planning/phases/09-categories-data-model-chart-initcontainer/09-VALIDATION.md
@charts/arr-stack/templates/arrconf-configmap.yaml
@charts/arr-stack/templates/_helpers.tpl
@charts/arr-stack/values.yaml
@charts/arr-stack/files/arrconf.yml
@examples/values-prod.yaml

<interfaces>
<!-- Reference shape — the new Job mirrors the existing ConfigMap template's metadata pattern + the single-source .Files.Get pattern proven viable by RESEARCH.md Q1. -->

From `charts/arr-stack/templates/arrconf-configmap.yaml` (the ENTIRE existing file — 11 lines, proves `.Files.Get "files/arrconf.yml"` works against the chart layout):

```yaml
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

From `charts/arr-stack/templates/_helpers.tpl` (lines 1-10 — the labels helper this Job will reuse):

```yaml
{{- define "arr-stack.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: arr-stack
{{- end }}
```

From `charts/arr-stack/values.yaml` (lines 17-20 — Renovate annotation + image-pin pattern; 11 existing instances follow this shape):

```yaml
image:
  # renovate: image=lscr.io/linuxserver/sonarr
  repository: lscr.io/linuxserver/sonarr
  tag: "4.0.17"
```

NOTE: in a Job spec the `image:` value is a single `<repo>:<tag>` string (not a `repository:`/`tag:` split). The `# renovate: image=...` annotation form is identical and `customManagers` in Renovate's config matches both shapes.

From `charts/arr-stack/values.yaml` (lines 65-70 — media volume mount pattern in app-template DSL):

```yaml
media:
  type: persistentVolumeClaim
  existingClaim: media-nas-pvc
  globalMounts:
    - path: /media
```

The new Job is raw K8s spec (not app-template DSL), so the equivalent raw-spec block (verified verbatim from 09-RESEARCH.md §Pattern 3) is:

```yaml
volumeMounts:
  - name: media
    mountPath: /media
volumes:
  - name: media
    persistentVolumeClaim:
      claimName: media-nas-pvc
```

**Verified single-source pattern (09-RESEARCH.md Q1 — VIABLE):** `.Files.Get` returns a string; piping through `| fromYaml` returns a `map[string]interface{}` that survives the `# yaml-language-server: ...` modeline comment at line 1 of `files/arrconf.yml`. Live `helm template` run during research dispositively confirmed this works in Helm 3.18 against the actual chart layout. The Helm sprig `fromYaml` function has shipped since Helm 3.0.

**Resource limits + restartPolicy (Claude's discretion per 09-CONTEXT.md):**
- `resources.requests: {cpu: 10m, memory: 16Mi}` + `resources.limits: {cpu: 100m, memory: 64Mi}` — mkdir on NFS is essentially free.
- `restartPolicy: OnFailure` + `backoffLimit: 2` — gives 2 retries before the Job is marked Failed. Failed Jobs persist (per D-07's `hook-delete-policy: ...,hook-succeeded` — Failure is NOT in the list, so failed Jobs are kept for forensics).
- `activeDeadlineSeconds: 120` — 10 mkdirs on NFS should complete in well under 30s.
- `imagePullPolicy: IfNotPresent` — aligns with the rest of the chart; gives single-node MicroK8s pull caching.
- `arr-stack.fullname` helper does NOT exist in `_helpers.tpl`. Use `{{ .Release.Name }}-categories-init` directly (recommended by 09-RESEARCH.md line 615 to minimize chart surface).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task B1: Create charts/arr-stack/templates/categories-init-job.yaml — Helm-hooked Job with single-source .Files.Get pattern</name>
  <files>charts/arr-stack/templates/categories-init-job.yaml</files>
  <read_first>
    - charts/arr-stack/templates/arrconf-configmap.yaml (entire 11-line file — primary analog for .Files.Get + metadata.namespace + labels helper; per 09-PATTERNS.md line 207)
    - charts/arr-stack/templates/_helpers.tpl (full file — confirms arr-stack.labels exists but arr-stack.fullname does NOT)
    - charts/arr-stack/values.yaml lines 17-20 (Renovate annotation + image pin pattern — verify the # renovate: image=... comment placement)
    - charts/arr-stack/files/arrconf.yml (full file — confirm modeline at line 1; Helm fromYaml must skip this comment)
    - .planning/phases/09-categories-data-model-chart-initcontainer/09-CONTEXT.md (decisions D-06..D-12 — locked Job shape, plus the "illustrative skeleton" at §Specifics lines 407-449)
    - .planning/phases/09-categories-data-model-chart-initcontainer/09-RESEARCH.md §"Open Q1: .Files.Get | fromYaml viability" (the live-tool dispositive evidence) AND §"Pattern 3: Helm-hooked Job template (single-source — recommended)" (the verified-rendering skeleton at lines 555-612)
    - .planning/phases/09-categories-data-model-chart-initcontainer/09-PATTERNS.md §"charts/arr-stack/templates/categories-init-job.yaml (NEW — Helm Job + hooks)" (the pattern map for this file)
  </read_first>
  <action>
    Create the new file `charts/arr-stack/templates/categories-init-job.yaml` with EXACTLY this content (verbatim from 09-RESEARCH.md §"Pattern 3", with the Helm 3.18-verified `.Files.Get | fromYaml` single-source pattern from Open Question 1):

    ```yaml
    {{- /*
    categories-init-job.yaml — Phase 9 D-06..D-12.

    A Helm pre-install/pre-upgrade Job that creates one /media/<name> directory
    per Category declared in charts/arr-stack/files/arrconf.yml. Idempotent
    (mkdir -p + [ -d ] guard), runs as uid:gid 1000:1000 to match the linuxserver
    PUID/PGID convention every media-app uses.

    Single-source pattern (D-08 pivot, 09-RESEARCH.md Q1): the Job reads the
    canonical categories[] list directly from files/arrconf.yml at template-
    render time via .Files.Get | fromYaml. No values.yaml duplication, no CI
    sync gate. When files/arrconf.yml has no categories[] block (Phase 9 Wave 1
    state, before Plan C), the range is over a nil map and emits zero mkdir
    steps. After Plan C lands the 10-entry block, the same template renders
    10 mkdir steps with no further code change.

    NOTE: busybox does NOT honor PUID/PGID env vars (those are a linuxserver-
    image convention). uid/gid is set by the pod-level securityContext below.
    */ -}}
    {{- $cfg := .Files.Get "files/arrconf.yml" | fromYaml -}}
    apiVersion: batch/v1
    kind: Job
    metadata:
      name: {{ .Release.Name }}-categories-init
      namespace: {{ .Release.Namespace }}
      labels:
        {{- include "arr-stack.labels" . | nindent 4 }}
      annotations:
        "helm.sh/hook": pre-install,pre-upgrade
        "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
        "helm.sh/hook-weight": "0"
    spec:
      activeDeadlineSeconds: 120
      backoffLimit: 2
      template:
        metadata:
          labels:
            {{- include "arr-stack.labels" . | nindent 8 }}
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
              resources:
                requests:
                  cpu: 10m
                  memory: 16Mi
                limits:
                  cpu: 100m
                  memory: 64Mi
              command: ["/bin/sh", "-c"]
              args:
                - |
                  set -e
                  {{- range $cat := $cfg.categories }}
                  if [ -d {{ $cat.base_path | quote }} ]; then
                    printf '{"event":"media_dir_ensured","path":"%s","created":false,"existed":true}\n' {{ $cat.base_path | quote }}
                  else
                    mkdir -p {{ $cat.base_path | quote }}
                    printf '{"event":"media_dir_ensured","path":"%s","created":true,"existed":false}\n' {{ $cat.base_path | quote }}
                  fi
                  {{- end }}
              volumeMounts:
                - name: media
                  mountPath: /media
          volumes:
            - name: media
              persistentVolumeClaim:
                claimName: media-nas-pvc
    ```

    Locked elements (do NOT vary):
    - `name: {{ .Release.Name }}-categories-init` — fullname helper does not exist; use `.Release.Name` directly (09-RESEARCH.md line 615).
    - `# renovate: image=docker.io/busybox` — exact comment, directly above the `image:` line, no blank line between (CLAUDE.md "Annotations Renovate (CRITIQUE)").
    - `image: busybox:1.36.1` — D-10 locked tag, no `:latest`.
    - `securityContext` at pod level with all three fields (`runAsUser`, `runAsGroup`, `fsGroup`: 1000) — D-12 locked.
    - The two printf strings emit exactly `media_dir_ensured` as the `event` field — the snapshot anti-leak grep is already tuned for this shape (D-09).
    - Both branches (`[ -d ]` true + false) emit a printf line so `grep -c 'media_dir_ensured'` against the rendered template returns 2*N where N is the number of categories. Plan B Wave 1 has N=0 (no categories yet in arrconf.yml) → 0 lines; after Plan C lands N=10 → 20 lines (verified by Plan C Task C3, NOT by Plan B).

    Validation gates the new file MUST pass before commit:
    1. **helm lint**:
       ```bash
       helm dependency update charts/arr-stack/ 2>/dev/null || true
       # Run the multi-alias unpack workaround per CLAUDE.md "Conventions Helm — umbrella chart":
       tar -xzf charts/arr-stack/charts/app-template-5.0.0.tgz -C charts/arr-stack/charts/ 2>/dev/null || true
       for alias in sonarr radarr prowlarr qbittorrent cleanuparr seerr flaresolverr jellyfin arrconf configarr; do
         [ ! -d "charts/arr-stack/charts/$alias" ] && cp -r charts/arr-stack/charts/app-template "charts/arr-stack/charts/$alias" 2>/dev/null
       done
       helm lint charts/arr-stack/ -f examples/values-prod.yaml
       ```
    2. **helm template + kubeconform** (validates K8s API compatibility):
       ```bash
       helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | kubeconform -strict -ignore-missing-schemas
       ```
    3. **render-shape sanity** (Wave 1 state — no categories yet; verify the Job manifest is present with locked hook annotations):
       ```bash
       helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | grep -A5 'name:.*categories-init' | grep -E 'helm.sh/hook.*pre-(install|upgrade)'
       # Expected: matches the helm.sh/hook annotation line (Plan-B-feasible check — W-02 fix).
       ```
    4. **rendered manifest sanity** (the Job resource exists with correct hook annotations + image pin):
       ```bash
       helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | grep -A30 'name: arr-stack-categories-init' | head -50
       # Expected: helm.sh/hook lines, image: busybox:1.36.1, runAsUser: 1000, claimName: media-nas-pvc all visible
       ```

    All four MUST exit 0 / produce the expected output before considering the task complete. If `helm lint` fails, the most common cause is a `tpl` syntax error or mis-indented YAML — read the error line, fix, retry.

    Do NOT add a `values.yaml` key for `categoriesInit.basePaths` or anything similar. The single-source `.Files.Get | fromYaml` pattern is the design (09-RESEARCH.md Q1 dispositive). Adding a duplicate values key would re-introduce the CI sync gate the pivot eliminates.

    **W-02 deferral note:** The 20-printf-line render verification (10 created-branch + 10 existed-branch) CANNOT be evaluated at Plan B exit — Plan C has not yet shipped the categories block. That cross-plan integration check is owned by **Plan C Task C3** (which runs in Wave 2 after Plan C C1 lands the 10-entry block in arrconf.yml). Plan B's exit gate is the locked-shape check above (hook annotations + image pin + security context + PVC mount visible in the rendered manifest).
  </action>
  <verify>
    <automated>helm dependency update charts/arr-stack/ 2>/dev/null; tar -xzf charts/arr-stack/charts/app-template-5.0.0.tgz -C charts/arr-stack/charts/ 2>/dev/null; for alias in sonarr radarr prowlarr qbittorrent cleanuparr seerr flaresolverr jellyfin arrconf configarr; do [ ! -d "charts/arr-stack/charts/$alias" ] && cp -r charts/arr-stack/charts/app-template "charts/arr-stack/charts/$alias" 2>/dev/null; done; helm lint charts/arr-stack/ -f examples/values-prod.yaml && helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | kubeconform -strict -ignore-missing-schemas && helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | grep -F 'name: arr-stack-categories-init' && helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | grep -F 'image: busybox:1.36.1' && helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | grep -F 'claimName: media-nas-pvc'</automated>
  </verify>
  <acceptance_criteria>
    - `test -f charts/arr-stack/templates/categories-init-job.yaml` exits 0
    - `grep -F '.Files.Get "files/arrconf.yml" | fromYaml' charts/arr-stack/templates/categories-init-job.yaml` exits 0
    - `grep -F 'helm.sh/hook": pre-install,pre-upgrade' charts/arr-stack/templates/categories-init-job.yaml` exits 0
    - `grep -F 'helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded' charts/arr-stack/templates/categories-init-job.yaml` exits 0
    - `grep -B1 'image: busybox:1.36.1' charts/arr-stack/templates/categories-init-job.yaml | grep -F '# renovate: image=docker.io/busybox'` exits 0 (annotation directly above image)
    - `grep -F 'runAsUser: 1000' charts/arr-stack/templates/categories-init-job.yaml` exits 0
    - `grep -F 'runAsGroup: 1000' charts/arr-stack/templates/categories-init-job.yaml` exits 0
    - `grep -F 'fsGroup: 1000' charts/arr-stack/templates/categories-init-job.yaml` exits 0
    - `grep -F 'claimName: media-nas-pvc' charts/arr-stack/templates/categories-init-job.yaml` exits 0
    - `grep -F 'media_dir_ensured' charts/arr-stack/templates/categories-init-job.yaml` exits 0
    - `grep -F 'mkdir -p' charts/arr-stack/templates/categories-init-job.yaml` exits 0
    - `grep -F 'backoffLimit: 2' charts/arr-stack/templates/categories-init-job.yaml` exits 0
    - `grep -F 'activeDeadlineSeconds: 120' charts/arr-stack/templates/categories-init-job.yaml` exits 0
    - `helm lint charts/arr-stack/ -f examples/values-prod.yaml` exits 0
    - `helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | kubeconform -strict -ignore-missing-schemas` exits 0
    - `helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | grep -F 'name: arr-stack-categories-init'` exits 0
    - `helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | grep -A5 'name:.*categories-init' | grep -E 'helm.sh/hook.*pre-(install|upgrade)'` exits 0 (Plan-B-feasible Wave 1 check — W-02 replacement)
    - **NOT a Plan B exit criterion:** the 20-printf-line render count. That cross-plan check is owned by Plan C Task C3 (W-02 fix — the full 20-line render check stays in Plan C C3, not Plan B).
  </acceptance_criteria>
  <done>
    `charts/arr-stack/templates/categories-init-job.yaml` exists, helm-lints clean, kubeconforms clean, and the rendered manifest under Wave 1 state (no categories yet in `arrconf.yml`) contains all locked D-NN signals (hook annotations matching pre-(install|upgrade) per the Plan-B-feasible W-02 check, busybox:1.36.1 with renovate annotation, runAsUser 1000, claimName media-nas-pvc, both printf branches with `media_dir_ensured`). The 20-line render verification is deferred to Plan C Task C3.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `files/arrconf.yml` (committed config) → Helm template engine (`.Files.Get | fromYaml`) | Operator-edited YAML; resolves at chart-render time. |
| Helm template engine → Kubernetes API (Job manifest) | Renders to `kubectl apply`-able YAML; ArgoCD pushes to cluster. |
| Kubernetes API → Job pod (busybox container) → NFS PVC (`/Public/media-stack` on `192.168.88.103`) | Pod runs as `uid:gid 1000:1000`; mounts `media-nas-pvc`; only privileged action is `mkdir -p` under `/media/`. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-09B-01 | Tampering | Operator commits malicious `categories[].base_path` (e.g. `/etc/cron.d/whatever`) or `name` with path-traversal payload | mitigate | Pydantic validation in the CI gate is the primary defense (kebab-case `name` regex `^[a-z0-9]+(-[a-z0-9]+)*$` + `model_validator` enforcing `base_path == f'/media/{name}'`). Defense-in-depth: the Job pod is ephemeral, runs as uid 1000 with no privileged capabilities; any `mkdir` outside `/media` writes to the container's overlay filesystem (dies with the pod, never reaches host). The NFS share is only writable at `/media`; no other host path is mounted into the Job container. |
| T-09B-02 | Tampering | Operator commits a `name` with shell-injection chars (e.g. `"; rm -rf /; echo "`) | mitigate | Plan A's kebab-case regex `^[a-z0-9]+(-[a-z0-9]+)*$` rejects every non-alphanumeric character. The Job's printf/mkdir invocations also use `{{ $cat.base_path | quote }}` (Helm sprig `quote`) which wraps the value in double-quotes — `set -e` + `quote` together prevent shell-metachar injection even if pydantic ever lapsed. Two independent layers. |
| T-09B-03 | Tampering | Renovate auto-bumps `busybox` to a backdoored version | mitigate | Renovate annotation `# renovate: image=docker.io/busybox` + pinned tag `1.36.1` (no `:latest`); patch/minor bumps automerge per existing rule but introduce no SHA-level pin. Mitigation parity with the other 10 images in `values.yaml`. Higher-assurance options (digest pin) are out of scope for v0.3.0 and explicitly deferred. |
| T-09B-04 | Information Disclosure | Job log leaks PVC contents | accept | The printf payload is `path` only (operator-public `base_path` like `/media/series-emilie`), no secret material. The pod runs `[ -d ]` + `mkdir -p` only — no `ls`, no `cat`. JSON-line shape is already snapshot-anti-leak-grep-safe (D-09). |
| T-09B-05 | Denial of Service | Job blocks `helm upgrade` indefinitely | mitigate | `activeDeadlineSeconds: 120` caps total Job duration. `backoffLimit: 2` caps retries. After timeout, ArgoCD shows the Job as Failed; operator inspects logs. Even worst-case-stuck Job blocks only the helm release transition, not running media pods (D-08 single-source ensures the Job is reachability-orthogonal to media-app pods). |
| T-09B-06 | Elevation of Privilege | Container escapes to root on the NFS server | mitigate | Pod-level `securityContext: runAsUser/runAsGroup/fsGroup: 1000`. busybox image runs as the requested uid (no PUID/PGID env-var nonsense — D-12 documented inline). NFS server-side `root_squash` (researched in Q2) is moot because the pod never runs as root. No privileged containers, no capabilities added. |
| T-09B-07 | Repudiation | Job runs but operator cannot prove which dirs were created | mitigate | Per-dir JSON-line log with `created: bool` + `existed: bool` (D-09). `kubectl logs job/<release>-categories-init -n selfhost` produces a forensic-grade audit trail. Failed Jobs persist (D-07's `hook-delete-policy` omits `Failed`) so the operator can read the failure logs without ArgoCD ripping the resource. |
| T-09B-08 | Spoofing | Attacker swaps the busybox image | accept | Image-pin + Renovate annotation control the supply chain. Cluster pulls from `docker.io/busybox` (anonymous) which is the official Docker Hub image. No mutating webhook in the cluster rewrites images. Pull-time integrity is anchored by Docker Hub's TUF chain (out of scope to harden further this phase). |

**Zero HIGH-severity unmitigated threats.** The dominant Tampering vector (T-09B-01/T-09B-02) is defended at TWO layers — pydantic at source-edit time + Helm sprig `quote` at render time. The container runs as a non-root, non-privileged uid on a mount scoped to `/media`.
</threat_model>

<verification>
After Task B1 completes:

```bash
# 1. Lint pass
helm lint charts/arr-stack/ -f examples/values-prod.yaml

# 2. Render + kubeconform
helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | kubeconform -strict -ignore-missing-schemas

# 3. Sanity: the Job appears in the render output with correct hook annotations
helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml \
  | awk '/^---/{block=""} {block=block"\n"$0} /name: arr-stack-categories-init/{print block; exit}' \
  | head -80

# 4. Wave-1-feasible check (W-02 replacement): the Job's hook annotations render correctly even with no categories yet:
helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | grep -A5 'name:.*categories-init' | grep -E 'helm.sh/hook.*pre-(install|upgrade)'
# Expected: matches.

# NOTE: the 20-printf-line count check moves to Plan C Task C3 (cross-plan integration verification).
```

The 20-printf-line render verification is OUT of Plan B's scope (W-02 fix). It lives in Plan C Task C3.
</verification>

<success_criteria>
- `charts/arr-stack/templates/categories-init-job.yaml` exists with the exact structure from 09-RESEARCH.md §"Pattern 3".
- `helm lint` + `kubeconform -strict` both green on `examples/values-prod.yaml`.
- The rendered manifest contains: `helm.sh/hook: pre-install,pre-upgrade`, `helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded`, `image: busybox:1.36.1` with `# renovate: image=docker.io/busybox` directly above, `runAsUser: 1000`, `runAsGroup: 1000`, `fsGroup: 1000`, `claimName: media-nas-pvc`.
- The Job iteration is over `$cfg.categories` from `.Files.Get "files/arrconf.yml" | fromYaml` (single-source pattern — no values.yaml key, no CI sync gate).
- **The 20-printf-line render verification is OWNED by Plan C Task C3, not Plan B** (W-02 fix). Plan B's exit gate is the Wave-1-feasible hook-annotation check.
- Manual cluster-time gates per 09-VALIDATION.md "Manual-Only Verifications" rows 1-4 are documented and the runbook is reachable from the operator's snapshot/deploy checklist (these gates do NOT block CI but MUST be exercised before the my-kluster `targetRevision` bump in Plan D — see ADR-6 + 09-VALIDATION.md row "Snapshot baseline taken BEFORE first Phase 9 cluster deploy").
</success_criteria>

<output>
After completion, create `.planning/phases/09-categories-data-model-chart-initcontainer/09-B-helm-job-SUMMARY.md` covering:
- Task B1 executed (file diff, byte count)
- D-NN coverage table (D-06, D-07, D-08-pivoted, D-09, D-10, D-11, D-12, D-13-boundary-preserved)
- `helm lint` + `kubeconform` exit codes
- Rendered manifest excerpt showing the hook annotations + image pin + security context + PVC mount
- Wave-1-feasible check result: hook annotations matched (Plan-B-feasible W-02 check). Note that the 20-printf-line render check is deferred to Plan C Task C3.
- Pointer to Plan C (which feeds this Job with the 10-entry categories block + Task C3 owns the 20-line verification) and Plan D (which release-tags the chart)
</output>
