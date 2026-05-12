---
phase: 04-umbrella-chart-migration-des-9-apps
plan: 02
type: execute
wave: 1
depends_on: ["04-01"]
files_modified:
  - charts/arr-stack/Chart.yaml
  - charts/arr-stack/Chart.lock
  - charts/arr-stack/charts/app-template-4.6.2.tgz
  - charts/arr-stack/templates/_helpers.tpl
  - charts/arr-stack/templates/arrconf-configmap.yaml
  - charts/arr-stack/templates/configarr-configmap.yaml
  - charts/arr-stack/files/arrconf.yml
  - charts/arr-stack/files/configarr.yml
  - charts/arr-stack/values.yaml
  - .gitignore
autonomous: true
requirements:
  - REQ-config-as-code
  - REQ-umbrella-deployment
  - REQ-helm-validation
tags: [helm, umbrella-chart, scaffold, app-template]
must_haves:
  truths:
    - "Chart.yaml declares the umbrella chart `arr-stack` v0.1.0 with 10 app-template v4.6.2 aliases"
    - "Chart.lock + charts/app-template-4.6.2.tgz committed so ArgoCD can render the path source without running `helm dependency update`"
    - "templates/_helpers.tpl defines `arr-stack.labels` (used by both ConfigMap templates) plus the two annotation fragments for downstream wave authoring ergonomics"
    - "templates/arrconf-configmap.yaml mounts files/arrconf.yml verbatim from my-kluster (frozen at Phase 3 state)"
    - "templates/configarr-configmap.yaml mounts files/configarr.yml (renamed from `config.yml`) verbatim from my-kluster — per D-04-VALUES-02 (files/ at top level)"
    - "`helm dependency update charts/arr-stack/` succeeds and `helm lint charts/arr-stack/` exits 0 against the placeholder values.yaml stub"
  artifacts:
    - path: "charts/arr-stack/Chart.yaml"
      provides: "Umbrella chart manifest with 10 dependency aliases"
      contains: "name: arr-stack"
    - path: "charts/arr-stack/Chart.lock"
      provides: "Pinned dependency resolution (committed for ArgoCD reproducibility)"
    - path: "charts/arr-stack/charts/app-template-4.6.2.tgz"
      provides: "Pre-downloaded sub-chart tarball (ArgoCD path-source requirement)"
    - path: "charts/arr-stack/templates/_helpers.tpl"
      provides: "Named templates `arr-stack.labels`, `arr-stack.oauth2ProxyAnnotations`, `arr-stack.certManagerAnnotation`"
      exports: ["arr-stack.labels", "arr-stack.oauth2ProxyAnnotations", "arr-stack.certManagerAnnotation"]
    - path: "charts/arr-stack/templates/arrconf-configmap.yaml"
      provides: "ConfigMap `arrconf-config` mounting files/arrconf.yml via .Files.Get"
    - path: "charts/arr-stack/templates/configarr-configmap.yaml"
      provides: "ConfigMap `configarr-config` mounting files/configarr.yml via .Files.Get"
    - path: "charts/arr-stack/files/arrconf.yml"
      provides: "arrconf reconciler config (Phase 3 frozen state, verbatim port)"
    - path: "charts/arr-stack/files/configarr.yml"
      provides: "configarr TRaSH-Guides config (verbatim port from my-kluster/charts/configarr/files/config.yml)"
    - path: "charts/arr-stack/values.yaml"
      provides: "Empty stub (filled by Plans 03/04/05). Needs to exist so helm lint can run."
  key_links:
    - from: "charts/arr-stack/templates/arrconf-configmap.yaml"
      to: "charts/arr-stack/files/arrconf.yml"
      via: ".Files.Get \"files/arrconf.yml\""
      pattern: "Files.Get .files/arrconf"
    - from: "charts/arr-stack/templates/configarr-configmap.yaml"
      to: "charts/arr-stack/files/configarr.yml"
      via: ".Files.Get \"files/configarr.yml\""
      pattern: "Files.Get .files/configarr"
    - from: "charts/arr-stack/Chart.yaml"
      to: "charts/arr-stack/Chart.lock"
      via: "helm dependency update writes Chart.lock from the dependencies block"
      pattern: "version: 4.6.2"
---

<objective>
Lay down the chart scaffolding (Chart.yaml + dependencies tarball + helpers + ConfigMap templates + files/ payload) that subsequent plans (03 media aliases, 04 CronJob aliases, 05 CI/Renovate, 06 docs) extend.

Purpose: The umbrella chart must exist as a renderable Helm chart before any alias values can be added (helm lint requires both Chart.yaml and a values.yaml file, even an empty one). The `files/` payload is byte-equivalence-critical (D-04-CUTOVER-03) — porting verbatim from my-kluster guarantees the reconciler / configarr behaviour does not regress at cutover. Committing the sub-chart tarball is required because ArgoCD's git-path source does NOT call `helm dependency update` (RESEARCH §Unknown #7).

Output: A scaffolded `charts/arr-stack/` directory that passes `helm lint` with an empty values.yaml stub.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/04-umbrella-chart-migration-des-9-apps/04-CONTEXT.md
@.planning/phases/04-umbrella-chart-migration-des-9-apps/04-RESEARCH.md
@.planning/phases/04-umbrella-chart-migration-des-9-apps/04-PATTERNS.md
@CLAUDE.md
@spec.md

<!-- Analog files to port verbatim -->
@/home/moi/projets/perso/my-kluster/charts/arrconf/files/arrconf.yml
@/home/moi/projets/perso/my-kluster/charts/configarr/files/config.yml
@/home/moi/projets/perso/my-kluster/charts/arrconf/templates/configmap.yaml
@/home/moi/projets/perso/my-kluster/charts/configarr/templates/configmap.yaml

<interfaces>
<!-- Exact Chart.yaml dependencies block — verbatim from RESEARCH §"Chart.yaml Dependencies Block (Exact)" -->

apiVersion: v2 (Helm 3 chart format — required)
chart name: arr-stack
chart version: 0.1.0
kubeVersion: ">=1.28.0-0" (matches app-template 4.6.2's own constraint per RESEARCH)

Dependency aliases (10 total, every entry uses app-template 4.6.2 from bjw-s-labs):
  sonarr, radarr, prowlarr, cleanuparr, qbittorrent, seerr, flaresolverr, jellyfin, arrconf, configarr

bjw-s repository URL: https://bjw-s-labs.github.io/helm-charts

<!-- Named templates to expose in _helpers.tpl -->
arr-stack.labels        — Helm chart label fragment (used by arrconf-configmap, configarr-configmap)
arr-stack.oauth2ProxyAnnotations — oauth2-proxy ingress block, takes a `hostname` dict key
arr-stack.certManagerAnnotation  — single line for cluster-issuer
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 2.1: Create Chart.yaml + run helm dependency update + commit Chart.lock and sub-chart tarball</name>
  <files>charts/arr-stack/Chart.yaml, charts/arr-stack/Chart.lock, charts/arr-stack/charts/app-template-4.6.2.tgz, charts/arr-stack/values.yaml, .gitignore</files>
  <read_first>
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-RESEARCH.md §"Chart.yaml Dependencies Block (Exact)" (verbatim block to copy) + §Unknown #7 (Chart.lock + sub-chart tarball commit policy)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-PATTERNS.md §"charts/arr-stack/Chart.yaml"
    CLAUDE.md §"Dependencies" (alias-per-service convention)
  </read_first>
  <action>
    Create `charts/arr-stack/Chart.yaml` with EXACTLY this content (10 aliases — sonarr, radarr, prowlarr, cleanuparr, qbittorrent, seerr, flaresolverr, jellyfin, arrconf, configarr — order locked, do not re-sort alphabetically; this order mirrors RESEARCH.md §"Chart.yaml Dependencies Block (Exact)"):

    ```yaml
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

    Create `charts/arr-stack/values.yaml` as an EMPTY placeholder containing a single safety comment so `helm lint` accepts the chart:

    ```yaml
    # arr-stack umbrella chart — production values.
    # Aliases (one per dependency in Chart.yaml) populated by Plans 03 (media apps) and 04 (CronJobs).
    # See `.planning/phases/04-umbrella-chart-migration-des-9-apps/04-CONTEXT.md` for the design rationale.
    # Each alias section is per D-04-VALUES-01 (flat top-level shape).
    ```

    Then download the sub-chart and refresh the lock file:

    ```bash
    cd charts/arr-stack
    helm repo add bjw-s-labs https://bjw-s-labs.github.io/helm-charts 2>/dev/null || helm repo update bjw-s-labs
    helm dependency update .
    # ↑ writes Chart.lock and downloads charts/app-template-4.6.2.tgz
    cd -
    ```

    Confirm the artifacts exist:
    ```bash
    ls -la charts/arr-stack/Chart.lock charts/arr-stack/charts/app-template-4.6.2.tgz
    ```

    Both `Chart.lock` AND `charts/app-template-4.6.2.tgz` MUST be committed. RESEARCH §Unknown #7 is dispositive: ArgoCD's git-path source does NOT call `helm dependency update`, so the tarball MUST be checked in.

    Ensure `.gitignore` at the repo root does NOT match `charts/arr-stack/charts/*.tgz`. Read the current `.gitignore`; if a generic `*.tgz` or `charts/*/charts/` rule exists, add an explicit negation:

    ```
    # Helm sub-chart tarballs MUST be committed (ArgoCD path-source requirement, RESEARCH §Unknown #7).
    !charts/arr-stack/charts/*.tgz
    ```

    Verify with `git check-ignore -v charts/arr-stack/charts/app-template-4.6.2.tgz` — exit code must be 1 (NOT ignored).

    Run smoke checks:
    ```bash
    helm lint charts/arr-stack/
    helm template arr-stack charts/arr-stack/ --namespace selfhost > /tmp/wave1-render.yaml
    ```

    Both must exit 0. The template output will be near-empty (no aliases configured yet) — that is expected and acceptable for Wave 1.
  </action>
  <verify>
    <automated>
      helm lint charts/arr-stack/ && \
      test -f charts/arr-stack/Chart.lock && \
      test -f charts/arr-stack/charts/app-template-4.6.2.tgz && \
      grep -c '^  - name: app-template' charts/arr-stack/Chart.yaml | grep -qE '^10$' && \
      grep -qE '^[[:space:]]*version: 4\.6\.2' charts/arr-stack/Chart.lock && \
      ! git check-ignore charts/arr-stack/charts/app-template-4.6.2.tgz
    </automated>
  </verify>
  <acceptance_criteria>
    - `helm lint charts/arr-stack/` exits 0.
    - `Chart.yaml` declares exactly 10 dependency entries (one per alias): `grep -c '^  - name: app-template' charts/arr-stack/Chart.yaml` returns 10.
    - All 10 aliases listed by name: `grep -cE '^    alias: (sonarr|radarr|prowlarr|cleanuparr|qbittorrent|seerr|flaresolverr|jellyfin|arrconf|configarr)$' charts/arr-stack/Chart.yaml` returns 10.
    - Every dependency pins version 4.6.2: `grep -c '^    version: 4.6.2$' charts/arr-stack/Chart.yaml` returns 10.
    - `Chart.lock` exists and pins to 4.6.2: `grep -qE 'version: 4.6.2' charts/arr-stack/Chart.lock`.
    - Sub-chart tarball committed AND not gitignored: `test -f charts/arr-stack/charts/app-template-4.6.2.tgz && ! git check-ignore charts/arr-stack/charts/app-template-4.6.2.tgz`.
    - `helm template arr-stack charts/arr-stack/ --namespace selfhost` exits 0 (output may be empty — that's fine).
  </acceptance_criteria>
  <done>
    The umbrella chart scaffolding is on disk and lint-clean. Subsequent plans can add alias content into `values.yaml` and re-render without re-bootstrapping the chart.
  </done>
</task>

<task type="auto">
  <name>Task 2.2: Port files/ payload and create _helpers.tpl + two ConfigMap templates</name>
  <files>
    charts/arr-stack/files/arrconf.yml
    charts/arr-stack/files/configarr.yml
    charts/arr-stack/templates/_helpers.tpl
    charts/arr-stack/templates/arrconf-configmap.yaml
    charts/arr-stack/templates/configarr-configmap.yaml
  </files>
  <read_first>
    /home/moi/projets/perso/my-kluster/charts/arrconf/files/arrconf.yml (verbatim port source)
    /home/moi/projets/perso/my-kluster/charts/configarr/files/config.yml (verbatim port source — renamed to configarr.yml in target)
    /home/moi/projets/perso/my-kluster/charts/arrconf/templates/configmap.yaml (analog for arrconf-configmap.yaml)
    /home/moi/projets/perso/my-kluster/charts/configarr/templates/configmap.yaml (analog for configarr-configmap.yaml)
    /home/moi/projets/perso/my-kluster/charts/arrconf/templates/_helpers.tpl (analog for _helpers.tpl — bjw-s naming pattern)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-PATTERNS.md §"templates/_helpers.tpl" + §"templates/arrconf-configmap.yaml" + §"templates/configarr-configmap.yaml" + §"files/arrconf.yml" + §"files/configarr.yml"
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-RESEARCH.md §Pattern 5 (ConfigMap for files/ content) + §Unknown #2 (_helpers.tpl indirection)
  </read_first>
  <action>
    **Step A — port files/ payload verbatim.**

    Copy `/home/moi/projets/perso/my-kluster/charts/arrconf/files/arrconf.yml` to `charts/arr-stack/files/arrconf.yml` byte-for-byte. No edits. This file is frozen at Phase 3 state (D-04-CRON-03: the args `apply --apps sonarr,radarr,prowlarr` drive which sections are reconciled, not this file's structure).

    ```bash
    mkdir -p charts/arr-stack/files
    cp /home/moi/projets/perso/my-kluster/charts/arrconf/files/arrconf.yml charts/arr-stack/files/arrconf.yml
    ```

    Copy `/home/moi/projets/perso/my-kluster/charts/configarr/files/config.yml` to `charts/arr-stack/files/configarr.yml` byte-for-byte BUT RENAME the file (analog is named `config.yml`, target is `configarr.yml` — PATTERNS.md §"files/configarr.yml" — disambiguates the umbrella's shared `files/` directory):

    ```bash
    cp /home/moi/projets/perso/my-kluster/charts/configarr/files/config.yml charts/arr-stack/files/configarr.yml
    ```

    Verify byte-equivalence:
    ```bash
    diff /home/moi/projets/perso/my-kluster/charts/arrconf/files/arrconf.yml charts/arr-stack/files/arrconf.yml
    diff /home/moi/projets/perso/my-kluster/charts/configarr/files/config.yml charts/arr-stack/files/configarr.yml
    # Both diffs MUST produce zero output.
    ```

    Both files MUST parse as valid YAML:
    ```bash
    python3 -c "import yaml; yaml.safe_load(open('charts/arr-stack/files/arrconf.yml'))"
    python3 -c "import yaml; yaml.safe_load(open('charts/arr-stack/files/configarr.yml'))"
    ```

    **Step B — author `templates/_helpers.tpl`** with EXACTLY this content (verbatim from PATTERNS.md §"templates/_helpers.tpl" translation block; the analog `arrconf.name`/`arrconf.fullname` per-chart helpers are NOT needed because all 10 aliases handle naming inside app-template):

    ```yaml
    {{/*
    arr-stack umbrella chart helpers.
    Two purposes:
    1. `arr-stack.labels` — chart label fragment, consumed by the custom ConfigMap templates.
    2. Reusable annotation fragments for documentation / future deduplication.
       Note: per RESEARCH §Unknown #2, `_helpers.tpl` may not be reachable from sub-chart
       (app-template) rendering contexts. For byte-equivalence at cutover, annotations are
       inlined verbatim in each alias's values.yaml block. These fragments document the
       canonical content; they are not required to be called from values.yaml.
    */}}

    {{- define "arr-stack.labels" -}}
    helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
    app.kubernetes.io/managed-by: {{ .Release.Service }}
    {{- end }}

    {{/*
    oauth2-proxy ingress annotations — used by 7 of 9 ingress apps (sonarr, radarr, cleanuparr,
    qbittorrent, seerr, prowlarr-NO, jellyfin-NO, flaresolverr-NO-ingress).
    Call signature: {{- include "arr-stack.oauth2ProxyAnnotations" (dict "hostname" "sonarr.tgu.ovh") | nindent 8 }}
    */}}
    {{- define "arr-stack.oauth2ProxyAnnotations" -}}
    nginx.ingress.kubernetes.io/auth-url: "https://auth.tgu.ovh/oauth2/auth"
    nginx.ingress.kubernetes.io/auth-signin: "https://auth.tgu.ovh/oauth2/start?rd=https://{{ .hostname }}"
    {{- end }}

    {{/*
    cert-manager annotation — used by all 8 ingress apps (sonarr, radarr, prowlarr, cleanuparr,
    qbittorrent, seerr, jellyfin; NOT flaresolverr which has no ingress).
    */}}
    {{- define "arr-stack.certManagerAnnotation" -}}
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    {{- end }}
    ```

    **Step C — author `templates/arrconf-configmap.yaml`** with EXACTLY this content (verbatim from PATTERNS.md §"templates/arrconf-configmap.yaml" target block — name hardcoded to `arrconf-config` so the arrconf alias can reference it by exact name via `persistence.config.name: arrconf-config`):

    ```yaml
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

    **Step D — author `templates/configarr-configmap.yaml`** with EXACTLY this content (verbatim from PATTERNS.md §"templates/configarr-configmap.yaml" target block — note the file is `files/configarr.yml` (NOT `files/config.yml`), and the ConfigMap data key remains `config.yml` because configarr expects to find its config at `/app/config/config.yml`):

    ```yaml
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: configarr-config
      labels:
        {{- include "arr-stack.labels" . | nindent 4 }}
    data:
      config.yml: |-
    {{ .Files.Get "files/configarr.yml" | indent 4 }}
    ```

    **Step E — smoke render the templates** to confirm `_helpers.tpl` resolves and `.Files.Get` produces non-empty data:

    ```bash
    helm lint charts/arr-stack/
    helm template arr-stack charts/arr-stack/ --namespace selfhost --show-only templates/arrconf-configmap.yaml > /tmp/wave1-arrconf-cm.yaml
    helm template arr-stack charts/arr-stack/ --namespace selfhost --show-only templates/configarr-configmap.yaml > /tmp/wave1-configarr-cm.yaml

    # Sanity check: ConfigMap names match Wave 2/3 references.
    grep '^  name: arrconf-config$' /tmp/wave1-arrconf-cm.yaml
    grep '^  name: configarr-config$' /tmp/wave1-configarr-cm.yaml

    # Sanity check: Files content is present (not empty).
    grep -c 'apps:' /tmp/wave1-arrconf-cm.yaml         # ≥1 (arrconf.yml starts with apps:)
    grep -c 'trashGuideUrl:' /tmp/wave1-configarr-cm.yaml  # ≥1 (configarr.yml has trashGuideUrl)
    ```
  </action>
  <verify>
    <automated>
      diff /home/moi/projets/perso/my-kluster/charts/arrconf/files/arrconf.yml charts/arr-stack/files/arrconf.yml >/dev/null && \
      diff /home/moi/projets/perso/my-kluster/charts/configarr/files/config.yml charts/arr-stack/files/configarr.yml >/dev/null && \
      python3 -c "import yaml; yaml.safe_load(open('charts/arr-stack/files/arrconf.yml'))" && \
      python3 -c "import yaml; yaml.safe_load(open('charts/arr-stack/files/configarr.yml'))" && \
      helm lint charts/arr-stack/ && \
      helm template arr-stack charts/arr-stack/ --namespace selfhost --show-only templates/arrconf-configmap.yaml | grep -q '^  name: arrconf-config$' && \
      helm template arr-stack charts/arr-stack/ --namespace selfhost --show-only templates/configarr-configmap.yaml | grep -q '^  name: configarr-config$' && \
      helm template arr-stack charts/arr-stack/ --namespace selfhost --show-only templates/arrconf-configmap.yaml | grep -q 'apps:' && \
      helm template arr-stack charts/arr-stack/ --namespace selfhost --show-only templates/configarr-configmap.yaml | grep -q 'trashGuideUrl:'
    </automated>
  </verify>
  <acceptance_criteria>
    - `files/arrconf.yml` byte-equivalent to source: `diff /home/moi/projets/perso/my-kluster/charts/arrconf/files/arrconf.yml charts/arr-stack/files/arrconf.yml` produces no output.
    - `files/configarr.yml` byte-equivalent to source: `diff /home/moi/projets/perso/my-kluster/charts/configarr/files/config.yml charts/arr-stack/files/configarr.yml` produces no output.
    - Both `files/*.yml` are valid YAML (Python `yaml.safe_load` exits 0).
    - `_helpers.tpl` defines all 3 named templates: `grep -cE '^\{\{- define "arr-stack\.(labels|oauth2ProxyAnnotations|certManagerAnnotation)"' charts/arr-stack/templates/_helpers.tpl` returns 3.
    - Both ConfigMap templates use `.Files.Get`: `grep -c 'Files.Get' charts/arr-stack/templates/arrconf-configmap.yaml` returns at least 1; same for configarr-configmap.yaml.
    - `helm template` rendering produces a ConfigMap named `arrconf-config` AND another named `configarr-config`.
    - Rendered ConfigMaps contain expected content tokens (`apps:` in arrconf-config data; `trashGuideUrl:` in configarr-config data).
    - `helm lint charts/arr-stack/` exits 0.
  </acceptance_criteria>
  <done>
    The chart can render its two ConfigMaps end-to-end against the ported `files/` payload. Wave 2/3 alias additions in `values.yaml` will reference these ConfigMaps by name (`arrconf-config`, `configarr-config`).
  </done>
</task>

</tasks>

<verification>
- `helm lint charts/arr-stack/` exits 0.
- `helm dependency list charts/arr-stack/` shows 10 entries all at `4.6.2`.
- `Chart.lock` + `charts/app-template-4.6.2.tgz` committed.
- Both `files/*.yml` byte-equivalent to my-kluster source.
- All 3 `_helpers.tpl` named templates defined.
- Both ConfigMap templates render with non-empty data content.
</verification>

<success_criteria>
The chart skeleton is ready to accept alias content from Plan 03 (media apps) and Plan 04 (CronJobs) without further structural changes. ArgoCD can render the chart from `path: charts/arr-stack` because the sub-chart tarball is checked in.
</success_criteria>

<output>
After completion, create `.planning/phases/04-umbrella-chart-migration-des-9-apps/04-02-chart-skeleton-SUMMARY.md`.
</output>
