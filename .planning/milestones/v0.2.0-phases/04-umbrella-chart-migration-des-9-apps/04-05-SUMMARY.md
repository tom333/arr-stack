---
phase: 04-umbrella-chart-migration-des-9-apps
plan: "05"
subsystem: infra
tags: [helm, app-template, cronjob, arrconf, configarr, values-schema, renovate]

# Dependency graph
requires:
  - phase: 04-02
    provides: arrconf-configmap.yaml + configarr-configmap.yaml (ConfigMaps mounted by these CronJob aliases)
  - phase: 04-04
    provides: 8 Deployment alias bodies (sonarr, radarr, prowlarr, qbittorrent, cleanuparr, seerr, flaresolverr, jellyfin)
provides:
  - arrconf CronJob alias body (v5 cronjob: key, concurrencyPolicy Forbid, D-04-CRON-03 args)
  - configarr CronJob alias body (tty:true, existingClaim: configarr-cache, D-04-CRON-04)
  - charts/arr-stack/values.schema.json (Draft 2020-12, additionalProperties: false at top level)
  - examples/values-prod.yaml (content-copy of values.yaml per D-04-VALUES-03)
  - 10/10 alias bodies populated — umbrella chart value-level work complete
affects: [04-06-chart-lint, 04-07-docs, 04-08-cutover]

# Tech tracking
tech-stack:
  added: [losisin/helm-values-schema-json v2.4.0 (helm plugin)]
  patterns:
    - "CronJob alias uses controllers.main.type: cronjob + controllers.main.cronjob.{schedule, concurrencyPolicy, successfulJobsHistory, failedJobsHistory} (v5 key names — app-template adds Limit suffix at render time)"
    - "restartPolicy goes in pod spec (inferred by app-template as Never for CronJob type) — NOT inside cronjob: block (schema rejects it as additionalProperties: false)"
    - "Separate Secrets per CronJob: arrconf-env, configarr-env via envFrom.secretRef"
    - "existingClaim for pre-existing PVC (configarr-cache) — umbrella does not re-create PVCs that pre-exist in cluster"
    - "values.schema.json: additionalProperties: false at top level (blocks unknown alias keys), true at each alias level (app-template sub-keys not enumerable)"

key-files:
  created:
    - charts/arr-stack/values.schema.json
    - examples/values-prod.yaml
  modified:
    - charts/arr-stack/values.yaml (arrconf + configarr alias bodies replacing {} placeholders)

key-decisions:
  - "restartPolicy removed from cronjob: block — app-template 5.0.0 schema has additionalProperties: false on the cronjob: object; restartPolicy is set by the template automatically (Never for CronJob type)"
  - "losisin/helm-values-schema-json v2.4.0 used — exact version flagged in RESEARCH; no fallback needed"
  - "additionalProperties: false at top level, true at alias level — Phase 4 posture; deep sub-key enumeration deferred (too brittle with app-template's nested structure)"
  - "configarr cache PVC referenced via existingClaim: configarr-cache — the PVC was created by my-kluster/charts/configarr/templates/pvc.yaml; umbrella does not re-create it"

patterns-established:
  - "Pattern: helm schema -f values.yaml -o values.schema.json generates initial schema; hand-tighten additionalProperties then verify with helm lint"
  - "Pattern: examples/values-prod.yaml = content-copy of values.yaml with 4-line header comment; diff test strips comment lines"

requirements-completed:
  - REQ-umbrella-deployment
  - REQ-helm-validation
  - REQ-config-as-code
  - REQ-pr-to-cluster-latency

# Metrics
duration: 25min
completed: 2026-05-13
---

# Phase 04 Plan 05: arrconf + configarr CronJob alias bodies + values.schema.json Summary

**arrconf + configarr CronJobs populated with app-template 5.0.0 cronjob: key, concurrencyPolicy Forbid, tty:true, and existingClaim PVC; Draft 2020-12 schema generated; umbrella values-level work 10/10 complete**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-13T05:00:00Z
- **Completed:** 2026-05-13T05:22:57Z
- **Tasks:** 3
- **Files modified:** 3 modified + 2 created

## Accomplishments

- arrconf CronJob alias body: v5 `cronjob:` key, `concurrencyPolicy: Forbid`, `successfulJobsHistory: 1`, `failedJobsHistory: 2`, args `[--config, /app/config/arrconf.yml, apply, --apps, sonarr,radarr,prowlarr]` (D-04-CRON-03), pod securityContext runAsNonRoot/1000:1000, envFrom: arrconf-env, ConfigMap subPath mount
- configarr CronJob alias body: `tty: true` mandatory (D-04-CRON-04), `existingClaim: configarr-cache` (no PVC re-creation), envFrom: configarr-env, ConfigMap subPath mount, no pod securityContext (matches production)
- `values.schema.json` generated via losisin v2.4.0, Draft 2020-12, `additionalProperties: false` at top level; `helm lint` validates green
- `examples/values-prod.yaml` shipped as content-copy of `values.yaml` per D-04-VALUES-03
- Final render: 8 Deployments + 8 Services + 7 Ingresses + 2 CronJobs + 2 ConfigMaps + 10 ServiceAccounts

## Task Commits

Each task was committed atomically:

1. **Task 5.1: arrconf CronJob alias body** - `e4e8562` (feat)
2. **Task 5.2: configarr CronJob alias body** - `5f94735` (feat)
3. **Task 5.3: values.schema.json + examples/values-prod.yaml** - `10c48de` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `charts/arr-stack/values.yaml` — replaced `arrconf: {}` and `configarr: {}` placeholders with full CronJob alias bodies; all 10 aliases now populated
- `charts/arr-stack/values.schema.json` — Draft 2020-12 JSON Schema generated by losisin helm-values-schema-json v2.4.0; top-level `additionalProperties: false`; each alias has `additionalProperties: true`
- `examples/values-prod.yaml` — 4-line header comment + verbatim copy of `values.yaml` per D-04-VALUES-03; my-kluster arr-stack-app.yaml valueFile target

## Decisions Made

- **restartPolicy removed from cronjob: block** — app-template 5.0.0 schema enforces `additionalProperties: false` inside `cronjob:`. The `restartPolicy` is controlled by app-template itself (defaults to Never for CronJob type). The plan's suggested YAML included `restartPolicy: Never` inside `cronjob:` but the schema rejects it; removing it is the correct fix (auto-applied per Rule 1).
- **losisin v2.4.0 used** — exact version the RESEARCH flagged; install via `helm plugin install --verify=false` since Helm 4 signature verification isn't set up.
- **Schema additionalProperties strategy** — `false` at top level (only the 10 declared alias keys accepted), `true` at each alias level (app-template has deeply nested sub-keys that the generator captures but would break if we set false deeper).
- **existingClaim for configarr-cache** — PVC pre-exists from my-kluster/charts/configarr; not re-created in the umbrella. Cache mount path is `/app/repos` (TRaSH-Guides git clone target).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed restartPolicy from cronjob: block**

- **Found during:** Task 5.1 (arrconf CronJob alias body)
- **Issue:** Plan's suggested YAML included `restartPolicy: Never` inside `controllers.main.cronjob:`. app-template 5.0.0 schema declares `additionalProperties: false` on that object — `helm lint` failed with "additional properties 'restartPolicy' not allowed".
- **Fix:** Removed `restartPolicy: Never` from the `cronjob:` block. app-template auto-sets `restartPolicy: Never` for CronJob type controllers. Applied the same fix preemptively to configarr in Task 5.2.
- **Files modified:** charts/arr-stack/values.yaml
- **Verification:** `helm lint` exits 0; rendered CronJob shows `restartPolicy: Never` correctly
- **Committed in:** e4e8562 (Task 5.1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - schema constraint not covered in plan's suggested YAML)
**Impact on plan:** Minimal — `restartPolicy: Never` is still present in the render (set by app-template). Functional behavior unchanged.

## v5-Specific Invariants (Final Verification)

| Invariant | Status |
|-----------|--------|
| No `cronJobConfig:` anywhere in values.yaml (W3 carry-forward) | PASS |
| No `tag: latest` anywhere in values.yaml | PASS |
| All 10 aliases have `fullnameOverride:` | PASS (count = 10) |
| All 10 `repository:` lines have `# renovate: image=` annotations | PASS |
| `successfulJobsHistory:` / `failedJobsHistory:` (no `Limit` suffix) | PASS |

## Known Stubs

None. Both CronJob aliases reference real cluster resources (Secrets `arrconf-env`/`configarr-env`, ConfigMaps `arrconf-config`/`configarr-config`, PVC `configarr-cache`) that exist in the `selfhost` namespace.

## Threat Flags

None. No new network endpoints, auth paths, or schema changes at trust boundaries introduced. The values.yaml additions are configuration-as-code for existing cluster resources.

## Deferred Items

- **CI drift check** between `values.yaml` and `examples/values-prod.yaml` — deferred to Plan 04-06 (chart-lint.yml). Currently documented only as a comment in values-prod.yaml.
- **Schema deep tightening** (enum validation for individual alias sub-fields) — deferred beyond Phase 4. Current posture (`additionalProperties: true` at alias level) is sufficient for Phase 4; tightening is a follow-up concern once the umbrella's structure stabilizes.
- **losisin plugin in CI** — the plugin is used locally to generate the schema; CI runs `helm lint` which validates values.yaml against the committed schema. CI doesn't re-run schema generation. Plan 04-06 can optionally add schema drift detection.

## Issues Encountered

- **Helm 4 multi-alias workaround**: `helm dependency build` downloads a single `app-template-5.0.0.tgz` tarball, but Helm 4 needs separate directories per alias. Applied the documented workaround: `tar -xzf ... charts/app-template-5.0.0.tgz -C charts/arr-stack/charts/` then `cp -r app-template/ <alias>/` for all 9 remaining aliases. This is an ephemeral local artifact (gitignored) — Plan 04-06 will codify it in `chart-lint.yml`.
- **RTK output filtering**: The `helm template > /tmp/w4a.yaml` redirect was being filtered by RTK (only 41 lines instead of 1600+). Worked around by using `rtk proxy helm template ... > /tmp/w4a.yaml` to bypass filtering.

## Next Phase Readiness

- Plan 04-06 (chart-lint.yml): The chart is feature-complete at the values level. CI can now run `helm lint`, `helm template`, and `kubeconform` in a proper workflow. The multi-alias workaround (unpack tarball) needs to be codified there.
- Plan 04-07 (docs): README.md and CLAUDE.md refresh can now reflect the final 10-alias umbrella structure.
- Plan 04-08 (cutover): Both CronJob aliases have the correct args, secrets, and ConfigMap bindings. No remaining blockers for cutover planning.

---
*Phase: 04-umbrella-chart-migration-des-9-apps*
*Completed: 2026-05-13*

## Self-Check: PASSED

| Item | Status |
|------|--------|
| charts/arr-stack/values.yaml | FOUND |
| charts/arr-stack/values.schema.json | FOUND |
| examples/values-prod.yaml | FOUND |
| 04-05-SUMMARY.md | FOUND |
| commit e4e8562 (Task 5.1) | FOUND |
| commit 5f94735 (Task 5.2) | FOUND |
| commit 10c48de (Task 5.3) | FOUND |
