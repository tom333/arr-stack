---
phase: 04-umbrella-chart-migration-des-9-apps
plan: 05
type: execute
wave: 4
depends_on: ["04-04"]
files_modified:
  - charts/arr-stack/values.yaml
  - charts/arr-stack/values.schema.json
autonomous: true
requirements:
  - REQ-config-as-code
  - REQ-umbrella-deployment
  - REQ-helm-validation
tags: [helm, umbrella-chart, cronjob, values-schema, app-template]
user_setup:
  - service: helm-plugin-losisin
    why: "Generate values.schema.json once; subsequent regenerations and CI validation use the same plugin"
    setup_steps:
      - "Install once locally: helm plugin install https://github.com/losisin/helm-values-schema-json"
      - "CI installs in chart-lint.yml (Plan 06) — no operator action needed there"
must_haves:
  truths:
    - "values.yaml has the `arrconf:` alias rendering a CronJob with `schedule: \"0 */4 * * *\"`, `concurrencyPolicy: Forbid`, `defaultPodOptions.securityContext.runAsNonRoot: true`, and the secret reference `arrconf-env`"
    - "values.yaml has the `configarr:` alias rendering a CronJob with `schedule: \"0 */4 * * *\"`, `concurrencyPolicy: Forbid`, `containers.main.tty: true`, AND a persistent volume claim for `cache` (storageClass `microk8s-hostpath`, 1Gi)"
    - "arrconf args are `[\"--config\", \"/app/config/arrconf.yml\", \"apply\", \"--apps\", \"sonarr,radarr,prowlarr\"]` per D-04-CRON-03"
    - "Neither CronJob alias carries a `checksum/config` Pod annotation (D-04-CRON-02 — DROPPED on purpose)"
    - "`values.schema.json` exists and `helm lint` / `helm template` succeed under the schema (Helm 3 auto-validates when the file is present) — per D-04-VALUES-04 (full strict schema, generated + hand-tightened)"
    - "tools/scripts/check-renovate-annotations.sh exits 0 over all 10 aliases (8 media + 2 CronJobs)"
  artifacts:
    - path: "charts/arr-stack/values.yaml"
      provides: "All 10 aliases populated (8 media + arrconf + configarr CronJobs)"
      contains: "arrconf:"
      contains: "configarr:"
    - path: "charts/arr-stack/values.schema.json"
      provides: "JSON Schema gate for values.yaml; hand-tightened with enums on sync policies + tag patterns"
      contains: '"$schema"'
  key_links:
    - from: "values.yaml (arrconf alias persistence.config)"
      to: "templates/arrconf-configmap.yaml"
      via: "persistence.config.name: arrconf-config — alias references the ConfigMap rendered by the custom template"
      pattern: 'name: arrconf-config'
    - from: "values.yaml (configarr alias persistence.config)"
      to: "templates/configarr-configmap.yaml"
      via: "persistence.config.name: configarr-config"
      pattern: 'name: configarr-config'
    - from: "values.yaml (both CronJob envFrom)"
      to: "my-kluster/secrets/{arrconf,configarr}-secret.yaml"
      via: "envFrom.secretRef.name — pre-existing external Secrets stay separate per D-04-CRON-04"
      pattern: "secretRef:"
---

<objective>
Add the final two aliases (arrconf + configarr) to `values.yaml` as `bjw-s/app-template` CronJob controllers, and generate `values.schema.json` from the now-complete values file.

Purpose: Closes the chart-content side of Phase 4. After this plan the umbrella has all 10 aliases and a strict schema gate. Plan 06 wires this into CI; Plan 07 cuts over.

Output: A complete `values.yaml` with both CronJobs, a generated and hand-tightened `values.schema.json`, and a passing `helm template … | kubeconform` locally if the tool is installed.
</objective>

<executor_note>
**values.yaml is append-only across waves 2/3/4.** Plans 03, 04, and 05 (this plan) each append top-level alias blocks to `charts/arr-stack/values.yaml` in strict wave order. NO external tools (formatters, IDE auto-fixers, helm-values mutators) may rewrite this file between waves. After this plan, the file-modification pattern shifts from append (8 media aliases + 2 CronJob aliases) to schema-generate (Task 5.2 creates values.schema.json) — keep them distinct in your commit history. If you find this plan starts with a values.yaml whose existing wave-2/3 blocks have moved or changed indentation, STOP and re-establish the prior wave state from git before continuing — the append-only invariant is what guarantees byte-equivalence at cutover (D-04-CUTOVER-03).
</executor_note>

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

<!-- Verbatim CronJob sources from my-kluster -->
@/home/moi/projets/perso/my-kluster/charts/arrconf/templates/cronjob.yaml
@/home/moi/projets/perso/my-kluster/charts/arrconf/values.yaml
@/home/moi/projets/perso/my-kluster/charts/configarr/templates/cronjob.yaml
@/home/moi/projets/perso/my-kluster/charts/configarr/values.yaml
@/home/moi/projets/perso/my-kluster/charts/configarr/templates/pvc.yaml

<interfaces>
<!-- arrconf alias translation table (from PATTERNS.md §"values.yaml — arrconf alias" + RESEARCH §Pattern 1) -->

Source field                                       Target field in app-template alias
spec.schedule                                  →   controllers.main.cronjob.schedule
spec.concurrencyPolicy                         →   controllers.main.cronjob.concurrencyPolicy   (Forbid — MANDATORY)
spec.successfulJobsHistoryLimit                →   controllers.main.cronjob.successfulJobsHistory
spec.failedJobsHistoryLimit                    →   controllers.main.cronjob.failedJobsHistory
spec.startingDeadlineSeconds                   →   controllers.main.cronjob.startingDeadlineSeconds
spec.template.spec.securityContext             →   defaultPodOptions.securityContext   (arrconf only)
container.image                                →   containers.main.image (with renovate annotation)
container.args                                 →   containers.main.args
container.envFrom                              →   containers.main.envFrom (secretRef.name, NOT identifier)
volumeMounts: /app/config/arrconf.yml          →   persistence.config.globalMounts (type: configMap, name: arrconf-config)
metadata.annotations.checksum/config           →   DROPPED (D-04-CRON-02)
container.tty                                  →   containers.main.tty   (configarr only — Pitfall 3)

Image tag for arrconf at cutover:
  - Current my-kluster/charts/arrconf/values.yaml ships `0.1.4`.
  - Phase 3 closed at `0.2.0` (per STATE.md `[Phase 03 P06]`).
  - D-CLAUDE-Discretion: NO new arrconf tag if `tools/arrconf/` source is unchanged — use `0.2.0` (current GHCR public image from Phase 3 close).
  - Verify with: curl -fs https://ghcr.io/v2/tom333/arr-stack-arrconf/manifests/0.2.0 -H "Accept: application/vnd.oci.image.index.v1+json" -o /dev/null && echo "0.2.0 exists"

Args for arrconf at cutover (D-04-CRON-03 verbatim):
  ["--config", "/app/config/arrconf.yml", "apply", "--apps", "sonarr,radarr,prowlarr"]

Configarr image tag: unchanged from my-kluster/charts/configarr/values.yaml — `1.16.0` (ghcr.io/raydak-labs/configarr).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 5.1: Add arrconf CronJob alias (per D-04-CRON-01..03 + RESEARCH Pattern 1)</name>
  <files>charts/arr-stack/values.yaml</files>
  <read_first>
    /home/moi/projets/perso/my-kluster/charts/arrconf/templates/cronjob.yaml (verbatim source: schedule/concurrencyPolicy/securityContext/args/envFrom/volumeMounts/checksum)
    /home/moi/projets/perso/my-kluster/charts/arrconf/values.yaml (image tag reference — currently 0.1.4 in my-kluster but Phase 3 shipped 0.2.0 to GHCR)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-PATTERNS.md §"values.yaml — arrconf alias" (analog mapping + target verbatim)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-RESEARCH.md §Pattern 1 (app-template CronJob alias — exact key is `cronjob:` NOT `cronJobConfig:`) + §Pitfall 1 + §Pitfall 4 (arrconf MUST have runAsNonRoot) + §Pitfall 7 (envFrom.secretRef.name not identifier)
    .planning/STATE.md `[Phase 03 P06]` (v0.2.0 GHCR tag — confirm pullable before using)
  </read_first>
  <action>
    Append the arrconf alias to `charts/arr-stack/values.yaml` after the jellyfin alias (last block from Plan 04 Task 4.2):

    ```yaml

    # ============================================================================
    # arrconf — config-as-code reconciler (CronJob via app-template alias)
    # D-04-CRON-01..03 + D-04-CRON-04 + RESEARCH Pattern 1
    # Source: my-kluster/charts/arrconf/templates/cronjob.yaml + values.yaml
    # ============================================================================
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
              env:
                TZ: "Europe/Paris"
                ARRCONF_DRY_RUN: "false"
              envFrom:
                - secretRef:
                    name: arrconf-env
              resources:
                limits:
                  cpu: 500m
                  memory: 512Mi
                requests:
                  cpu: 50m
                  memory: 128Mi
      defaultPodOptions:
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          runAsGroup: 1000
      persistence:
        config:
          type: configMap
          name: arrconf-config
          globalMounts:
            - path: /app/config/arrconf.yml
              subPath: arrconf.yml
              readOnly: true
    ```

    Verbatim cross-checks (mandatory before commit):
    - `controllers.main.cronjob` — singular `cronjob:`, NOT `cronJobConfig:` (RESEARCH Pitfall 1).
    - `concurrencyPolicy: Forbid` — D-04-CRON-02 MANDATORY.
    - NO `checksum/config` annotation block (D-04-CRON-02 DROPPED).
    - Args list matches D-04-CRON-03 EXACTLY (5 entries; `--apps` value is comma-separated `sonarr,radarr,prowlarr`; do not split into 3 entries).
    - `envFrom[0].secretRef.name: arrconf-env` — `name:` NOT `identifier:` (RESEARCH Pitfall 7 — external Secret).
    - `defaultPodOptions.securityContext` carries `runAsNonRoot: true, runAsUser: 1000, runAsGroup: 1000` (RESEARCH Pitfall 4 — arrconf MUST run non-root).
    - `persistence.config.name: arrconf-config` — must match the ConfigMap name created in Plan 02 Task 2.2.
    - `pullPolicy: IfNotPresent` — copied from my-kluster/charts/arrconf/values.yaml.

    Verify the arrconf tag is publicly pullable before commit:
    ```bash
    curl -fsSL -H "Accept: application/vnd.oci.image.index.v1+json" \
      https://ghcr.io/v2/tom333/arr-stack-arrconf/manifests/0.2.0 -o /dev/null \
      && echo "0.2.0 pullable" \
      || echo "WARN: 0.2.0 not pullable — review Phase 3 P06 release status before continuing"
    ```
    (If 0.2.0 is not yet public, surface this in the SUMMARY — Phase 4 cutover depends on it; alternative is to release a v0.2.1 alias-tag, but that contradicts CLAUDE's Discretion in the Phase 4 CONTEXT.)

    Smoke render:
    ```bash
    helm lint charts/arr-stack/
    helm template arr-stack charts/arr-stack/ -f charts/arr-stack/values.yaml --namespace selfhost \
      | awk '/^---$/{p=0} /^kind: CronJob$/{p=1} p' > /tmp/arrconf-cronjob.yaml

    # CronJob exists:
    grep -q 'kind: CronJob' /tmp/arrconf-cronjob.yaml
    # schedule:
    grep -q 'schedule: 0 \*/4 \* \* \*' /tmp/arrconf-cronjob.yaml
    # concurrencyPolicy: Forbid:
    grep -q 'concurrencyPolicy: Forbid' /tmp/arrconf-cronjob.yaml
    # securityContext runAsNonRoot:
    grep -q 'runAsNonRoot: true' /tmp/arrconf-cronjob.yaml
    # args present in render (string match on the joined args):
    grep -q -- '--apps' /tmp/arrconf-cronjob.yaml
    grep -q 'sonarr,radarr,prowlarr' /tmp/arrconf-cronjob.yaml
    # secretRef name (not identifier):
    grep -q 'name: arrconf-env' /tmp/arrconf-cronjob.yaml
    # NO checksum/config annotation:
    ! grep -q 'checksum/config' /tmp/arrconf-cronjob.yaml
    ```
  </action>
  <verify>
    <automated>
      helm lint charts/arr-stack/ && \
      tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml && \
      grep -q '^arrconf:' charts/arr-stack/values.yaml && \
      helm template arr-stack charts/arr-stack/ -f charts/arr-stack/values.yaml --namespace selfhost > /tmp/arrconf-render.yaml && \
      grep -q '^kind: CronJob$' /tmp/arrconf-render.yaml && \
      awk '/name: arrconf/,/^---/' /tmp/arrconf-render.yaml | grep -q 'concurrencyPolicy: Forbid' && \
      awk '/name: arrconf/,/^---/' /tmp/arrconf-render.yaml | grep -q 'runAsNonRoot: true' && \
      awk '/name: arrconf/,/^---/' /tmp/arrconf-render.yaml | grep -q 'sonarr,radarr,prowlarr' && \
      awk '/name: arrconf/,/^---/' /tmp/arrconf-render.yaml | grep -q 'name: arrconf-env' && \
      ! awk '/name: arrconf/,/^---/' /tmp/arrconf-render.yaml | grep -q 'checksum/config'
    </automated>
  </verify>
  <acceptance_criteria>
    - `^arrconf:$` present in values.yaml.
    - app-template CronJob render keys exist: rendered CronJob has `kind: CronJob`, `schedule: 0 */4 * * *`, `concurrencyPolicy: Forbid`, `runAsNonRoot: true`, `runAsUser: 1000`, `runAsGroup: 1000`.
    - Args reconcile all 3 apps: rendered CronJob contains the literal `sonarr,radarr,prowlarr` string AND the `--apps` flag.
    - External Secret reference: rendered CronJob contains `name: arrconf-env` under `envFrom.secretRef`.
    - NO `checksum/config` annotation in arrconf CronJob: `awk '/name: arrconf/,/^---/' /tmp/arrconf-render.yaml | grep -c 'checksum/config'` returns 0.
    - Renovate annotation present for arrconf image: `grep -q '# renovate: image=ghcr.io/tom333/arr-stack-arrconf' charts/arr-stack/values.yaml` returns 0 exit.
    - `tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml` exits 0.
    - `helm lint charts/arr-stack/` exits 0.
    - **W3 — wrong-key absence**: `! grep -q 'cronJobConfig:' charts/arr-stack/values.yaml` (the correct app-template key is `cronjob:` singular — RESEARCH Pitfall 1. If `cronJobConfig:` ever appears, the CronJob silently renders with default schedule + concurrencyPolicy and the acceptance criteria above will pass coincidentally — this guard prevents that silent-failure mode).
  </acceptance_criteria>
  <done>
    arrconf alias renders a CronJob byte-equivalent to the production my-kluster CronJob (modulo the intentional `checksum/config` removal and the args-list expansion to `sonarr,radarr,prowlarr`).
  </done>
</task>

<task type="auto">
  <name>Task 5.2: Add configarr CronJob alias (tty:true + cache PVC) and generate values.schema.json</name>
  <files>charts/arr-stack/values.yaml, charts/arr-stack/values.schema.json</files>
  <read_first>
    /home/moi/projets/perso/my-kluster/charts/configarr/templates/cronjob.yaml (verbatim source — note tty: true, NO runAsNonRoot, cache volume)
    /home/moi/projets/perso/my-kluster/charts/configarr/templates/pvc.yaml (the cache PVC: storageClass microk8s-hostpath, 1Gi)
    /home/moi/projets/perso/my-kluster/charts/configarr/values.yaml (image tag 1.16.0)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-PATTERNS.md §"values.yaml — configarr alias" (target block)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-RESEARCH.md §Pattern 2 + §Pitfall 3 (tty preserved) + §Pitfall 4 (NO runAsNonRoot on configarr) + §Unknown #3 (losisin/helm-values-schema-json plugin)
  </read_first>
  <action>
    **Step A — append configarr alias.**

    Append to `charts/arr-stack/values.yaml`:

    ```yaml

    # ============================================================================
    # configarr — TRaSH-Guides / quality_profile sync (CronJob via app-template alias)
    # D-04-CRON-01..02 + D-04-CRON-04 + RESEARCH Pattern 2 + Pitfall 3 (tty) + Pitfall 4 (no securityContext)
    # Source: my-kluster/charts/configarr/templates/cronjob.yaml + values.yaml + pvc.yaml
    # ============================================================================
    configarr:
      controllers:
        main:
          type: CronJob
          cronjob:
            schedule: "0 */4 * * *"
            concurrencyPolicy: Forbid
            successfulJobsHistory: 1
            failedJobsHistory: 2
          containers:
            main:
              image:
                # renovate: image=ghcr.io/raydak-labs/configarr
                repository: ghcr.io/raydak-labs/configarr
                tag: "1.16.0"
                pullPolicy: IfNotPresent
              tty: true
              env:
                TZ: "Europe/Paris"
              envFrom:
                - secretRef:
                    name: configarr-env
              resources:
                limits:
                  cpu: 500m
                  memory: 512Mi
                requests:
                  cpu: 50m
                  memory: 128Mi
      defaultPodOptions:
        securityContext: {}
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

    Verbatim cross-checks:
    - `tty: true` is at `containers.main.tty` (RESEARCH Pitfall 3 — production configarr requires it).
    - `defaultPodOptions.securityContext: {}` — empty map, NOT runAsNonRoot (RESEARCH Pitfall 4: configarr's production Pod has no securityContext).
    - `persistence.config.globalMounts.path: /app/config/config.yml` and `subPath: config.yml` — configarr reads from `/app/config/config.yml`. The ConfigMap created in Plan 02 Task 2.2 has data key `config.yml` precisely so this subPath resolves.
    - `persistence.cache.type: persistentVolumeClaim` with `storageClass: microk8s-hostpath` + `size: 1Gi` replaces the separate `pvc.yaml` template from my-kluster.
    - NO `checksum/config` annotation (D-04-CRON-02 DROPPED).
    - `envFrom.secretRef.name: configarr-env` — separate Secret from arrconf-env (D-04-CRON-04).

    Smoke render the configarr CronJob:
    ```bash
    helm lint charts/arr-stack/
    helm template arr-stack charts/arr-stack/ -f charts/arr-stack/values.yaml --namespace selfhost > /tmp/full-render.yaml

    awk '/name: configarr/,/^---/' /tmp/full-render.yaml | grep -q 'tty: true'
    awk '/name: configarr/,/^---/' /tmp/full-render.yaml | grep -q 'concurrencyPolicy: Forbid'
    awk '/name: configarr/,/^---/' /tmp/full-render.yaml | grep -q 'name: configarr-env'
    ! awk '/name: configarr/,/^---/' /tmp/full-render.yaml | grep -q 'runAsNonRoot'   # configarr MUST NOT have this
    awk '/name: configarr/,/^---/' /tmp/full-render.yaml | grep -q 'storageClass.*microk8s-hostpath'
    awk '/name: configarr/,/^---/' /tmp/full-render.yaml | grep -q '/app/repos'
    grep -c '^kind: CronJob$' /tmp/full-render.yaml     # ≥ 2 (arrconf + configarr)
    grep -c '^kind: PersistentVolumeClaim$' /tmp/full-render.yaml  # ≥ 7 (sonarr/radarr/jellyfin config + cleanuparr/prowlarr/qbit config + configarr cache + configarr config + arrconf config — but configMap-typed mounts are NOT PVCs)
    # Actually expected PVCs: sonarr config (1) + sonarr media (existingClaim — no PVC rendered) + radarr config (1) + prowlarr (1) + cleanuparr (1) + qbittorrent config (1) + seerr (1) + jellyfin config (1) + configarr cache (1) = 8
    ```

    **Step B — generate `values.schema.json` using losisin/helm-values-schema-json plugin.**

    Install the plugin if not already installed locally:
    ```bash
    helm plugin list | grep -q 'schema' || helm plugin install https://github.com/losisin/helm-values-schema-json
    ```

    Generate the initial schema:
    ```bash
    cd charts/arr-stack
    # Plugin invocation per its README (losisin/helm-values-schema-json):
    helm schema -input values.yaml -output values.schema.json
    cd -
    ```

    Hand-tighten the generated schema with the following constraints (open `charts/arr-stack/values.schema.json` and add/refine these keys; the generator produces a base structure — augment it without breaking the JSON Schema draft):

    1. Add a top-level `"$schema": "https://json-schema.org/draft-07/schema#"` if the generator did not.
    2. For each alias's `controllers.main.containers.main.image.tag` field, narrow the type to `"string"` and add `"pattern": "^([a-zA-Z0-9._-]+|.+@sha256:[a-f0-9]{64})$"` so `latest` is rejected (any digest-pin syntax is allowed; pure-latest matches the pattern but Plan 06 CI calls `check-renovate-annotations.sh` which is the real `:latest`-blocker).
    3. For each `cronjob.schedule` field, add `"pattern": "^([0-9*/, -]+\\s+){4}[0-9*/, -]+$"` (a basic cron-syntax regex).
    4. For each `concurrencyPolicy`, add `"enum": ["Allow", "Forbid", "Replace"]`.
    5. Keep additional properties OPEN at the alias root level (do not set `additionalProperties: false` on the alias roots — sub-chart values are unbounded and we do not own the app-template schema).

    Hand-tightening is a one-time investment; subsequent regenerations via the plugin will REPLACE the file, so the hand-tightening MUST be re-applied OR the plugin's `-schemaRoot.additionalProperties false` flag used selectively. For Phase 4, accept that regenerations require re-applying constraints — document this in the SUMMARY.

    **Step C — smoke check Helm's auto-validation.**

    Helm 3 auto-validates `values.yaml` against `values.schema.json` during `helm template` and `helm lint`. Any value that violates the schema causes `helm lint` to exit non-zero.

    ```bash
    helm lint charts/arr-stack/
    helm template arr-stack charts/arr-stack/ -f charts/arr-stack/values.yaml --namespace selfhost > /dev/null

    # Negative-path test (transient): inject a bad value and prove lint catches it.
    cp charts/arr-stack/values.yaml /tmp/values.yaml.backup
    sed -i 's|tag: "0.2.0"|tag: latest|' charts/arr-stack/values.yaml
    if helm lint charts/arr-stack/; then
      echo "BUG: schema did not reject tag: latest"
      mv /tmp/values.yaml.backup charts/arr-stack/values.yaml
      exit 1
    fi
    echo "OK: schema rejects tag: latest"
    mv /tmp/values.yaml.backup charts/arr-stack/values.yaml
    helm lint charts/arr-stack/   # must succeed again
    ```

    Note: if the regex above is too permissive (matches `latest`), tighten the pattern or rely on `tools/scripts/check-renovate-annotations.sh` (which Plan 06 CI runs) as the dispositive `:latest` blocker. Document in SUMMARY which gate ultimately catches `:latest`.

    Final gate — full render + tool check:
    ```bash
    helm lint charts/arr-stack/
    tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml
    [ "$(grep -cE '^(sonarr|radarr|prowlarr|cleanuparr|qbittorrent|seerr|flaresolverr|jellyfin|arrconf|configarr):$' charts/arr-stack/values.yaml)" -eq 10 ]
    if command -v kubeconform >/dev/null 2>&1; then
      helm template arr-stack charts/arr-stack/ -f charts/arr-stack/values.yaml --namespace selfhost \
        | kubeconform -strict -ignore-missing-schemas -kubernetes-version 1.33.0
    fi
    ```
  </action>
  <verify>
    <automated>
      helm lint charts/arr-stack/ && \
      tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml && \
      grep -q '^configarr:' charts/arr-stack/values.yaml && \
      test -f charts/arr-stack/values.schema.json && \
      [ "$(grep -cE '^(sonarr|radarr|prowlarr|cleanuparr|qbittorrent|seerr|flaresolverr|jellyfin|arrconf|configarr):$' charts/arr-stack/values.yaml)" = "10" ] && \
      helm template arr-stack charts/arr-stack/ -f charts/arr-stack/values.yaml --namespace selfhost > /tmp/full-render.yaml && \
      [ "$(grep -c '^kind: CronJob$' /tmp/full-render.yaml)" -ge 2 ] && \
      awk '/name: configarr/,/^---/' /tmp/full-render.yaml | grep -q 'tty: true' && \
      ! awk '/name: configarr/,/^---/' /tmp/full-render.yaml | grep -q 'runAsNonRoot' && \
      awk '/name: configarr/,/^---/' /tmp/full-render.yaml | grep -q 'storageClass.*microk8s-hostpath'
    </automated>
  </verify>
  <acceptance_criteria>
    - All 10 top-level aliases present: count == 10.
    - configarr CronJob renders with `tty: true`.
    - configarr Pod has NO `runAsNonRoot` (block-grep returns 0).
    - configarr cache PVC: rendered output has `storageClass: microk8s-hostpath` AND `mountPath: /app/repos`.
    - `values.schema.json` exists and is valid JSON: `python3 -c "import json; json.load(open('charts/arr-stack/values.schema.json'))"` exits 0.
    - `helm lint charts/arr-stack/` exits 0 against the populated values.yaml.
    - `tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml` exits 0.
    - At least 2 rendered CronJobs (arrconf + configarr).
    - **W3 — wrong-key absence**: `! grep -q 'cronJobConfig:' charts/arr-stack/values.yaml` (also asserted in Task 5.1 — re-asserted here because the configarr alias is the second CronJob authored in this plan and the same silent-failure risk applies).
    - Optional: if `kubeconform` is installed locally, `helm template … | kubeconform -strict …` exits 0.
  </acceptance_criteria>
  <done>
    All 10 aliases populated. `values.schema.json` exists and Helm auto-validates `values.yaml` against it. Plan 06 wires this into CI; Plan 07 (cross-repo PR) does the cutover.
  </done>
</task>

</tasks>

<verification>
- 10 top-level aliases in values.yaml.
- `helm lint charts/arr-stack/` exits 0.
- `tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml` exits 0.
- 2 CronJob kinds rendered with `concurrencyPolicy: Forbid`.
- arrconf CronJob: `runAsNonRoot: true` present, NO `checksum/config`, args=`sonarr,radarr,prowlarr`, `name: arrconf-env`.
- configarr CronJob: `tty: true` present, NO `runAsNonRoot`, cache PVC with `microk8s-hostpath`.
- `values.schema.json` exists and parses as valid JSON.
</verification>

<success_criteria>
The umbrella chart is content-complete. Plan 06 (CI + Renovate config) and Plan 07 (cross-repo cutover) operate on the chart as it exists at the end of this plan.
</success_criteria>

<output>
After completion, create `.planning/phases/04-umbrella-chart-migration-des-9-apps/04-05-cronjob-aliases-schema-SUMMARY.md` documenting:
- Whether the `0.2.0` arrconf GHCR tag was confirmed pullable.
- The hand-tightening applied to `values.schema.json` (so future regenerations can re-apply).
- Which gate ultimately blocks `:latest` (schema pattern vs check-renovate-annotations.sh).
- Local kubeconform run output if available.
</output>
