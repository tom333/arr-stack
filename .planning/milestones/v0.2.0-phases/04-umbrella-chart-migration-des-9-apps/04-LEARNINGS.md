---
phase: 4
phase_name: "umbrella-chart-migration-des-9-apps"
project: "arr-stack"
generated: "2026-05-14T17:10:00Z"
counts:
  decisions: 8
  lessons: 10
  patterns: 8
  surprises: 7
missing_artifacts:
  - "VERIFICATION.md (Nyquist verifier never ran — Phase 4 chose UAT as the verification gate)"
---

# Phase 4 Learnings: umbrella-chart-migration-des-9-apps

## Decisions

### D-04-CUTOVER-01 — Atomic big-bang cutover in a single my-kluster PR
**What**: One PR adds `arr-stack-app.yaml` + deletes the 10 unit `Application` YAML files + `charts/configarr/` + `charts/arrconf/` directories.
**Why**: Byte-equivalent rendering means ArgoCD's first sync adopts existing K8s resources via ServerSideApply field-manager negotiation. A phased migration would require co-existing Applications managing overlapping K8s objects, and `prune: true` makes that hazardous.
**Source**: 04-CONTEXT.md §D-04-CUTOVER-01.

### D-04-CUTOVER-02 — Suspend automated.* on the new App for the first sync
**What**: `arr-stack-app.yaml` ships WITHOUT the `automated:` block at PR merge time. Operator runs `argocd app diff arr-stack` (or kubectl fallback), reviews against the ADR-6 baseline, manually syncs, then re-enables `automated.{selfHeal,prune}` in a follow-up one-line PR.
**Why**: Mitigates the prune-race risk during cutover; operator retains the abort button.
**Source**: 04-CONTEXT.md §D-04-CUTOVER-02; implemented in Plan 04-08 Task 8.3; closed in Plan 04-09 Task 9.1 via my-kluster PR #1393.

### D-04-CUTOVER-05 — Replace=true syncOption (emerged during cutover, not in original CONTEXT)
**What**: Add `Replace=true` (alongside `ServerSideApply=true`) to `arr-stack-app.yaml` syncOptions.
**Why**: The release name changes from `<app>` (per unit App) to `arr-stack` (umbrella), which changes `app.kubernetes.io/instance` labels. Deployment.spec.selector is IMMUTABLE — so a normal apply fails with "field is immutable". `Replace=true + Force=true` triggers delete+recreate on each Deployment, accepting a 5-10s pod restart per app as the cost.
**Source**: 04-RESEARCH.md §"Standard Stack" (added after the v0.2.6 chart refactor surfaced the issue); 04-08-CUTOVER-LOG.md Bug-fix history.

### Orphan-first cross-repo cutover (emerged, not in original plan)
**What**: Before merging the my-kluster cutover PR, suspend the `applications` parent ArgoCD App and remove the `resources-finalizer.argocd.argoproj.io` finalizer from each of the 10 unit Apps. After merge, parent App deletes the 10 unit Application CRs WITHOUT cascading to K8s resources. Then manually sync arr-stack with `Replace=true + Force=true` to adopt the orphaned resources.
**Why**: Without this, the parent App's `prune: true + selfHeal: true` triggers a cascade-delete cycle as soon as the PR merges — taking down all 8 apps before arr-stack has a chance to sync. The plan original 5-10s downtime estimate became "indefinite until manual sync" without the orphan step. ArgoCD selfHeal also races against `kubectl patch finalizers` — must suspend parent first.
**Source**: 04-08-CUTOVER-LOG.md §"Operator-side state changes" (this surfaced live during cutover; should be promoted to a global pattern for any App-of-Apps cutover).

### v0.3.0 chart shape — per-alias `global.nameOverride` + explicit `serviceAccount.<alias>: {}`
**What**: Each alias block in `values.yaml` declares both `global.nameOverride` and `global.fullnameOverride` (no `nameOverride` at top level — see Pattern 5 below), plus an explicit `serviceAccount.<alias>: {}` entry.
**Why**: app-template 5.0.0's `templates/common.yaml` has a hardcoded defaulter that fills `global.nameOverride = .Release.Name` when absent — collapsing every alias's `app.kubernetes.io/name` label to "arr-stack". Without per-alias nameOverride, Service selectors match all umbrella pods (Bug 1). The chart's `_init.tpl` also auto-injects a `serviceAccount.<release-name>: {}` if no SA is provided; the SA-name helper picks the IDENTIFIER (key), not the SA resource's resolved metadata.name — causing pod `serviceAccountName: arr-stack` while the SA resource is named per-alias (Bug 2).
**Source**: 04-08-CUTOVER-LOG.md §"Resolution"; arr-stack PR #5 (commit `9745d5a`, tag v0.2.6).

### D-04-PIN-04 → 72h hard decision gate for SC#2
**What**: Plan 04-09 Task 9.2 watches for the first Renovate-driven image bump. M1 (T+0–48h watch), M2 (T+48h: if no natural bump, force a cleanuparr patch downgrade per D-04-PIN-04 Path B), M3 (T+72h: verdict captured regardless).
**Why**: Without a bounded timeline, SC#2 verification stays open indefinitely. Hard gate creates a deterministic close.
**Source**: 04-RESEARCH.md (B4 fix from plan-checker iteration); 04-09-PLAN.md.

### `examples/values-prod.yaml` as a symlink (post-Phase-4 hardening)
**What**: Replace the file-copy at `examples/values-prod.yaml` with a symlink to `../charts/arr-stack/values.yaml`.
**Why**: Bug 5 of the cutover surfaced when arr-stack PR #3 updated only `charts/arr-stack/values.yaml` (cleanuparr 2.3.3 → 2.9.6), but ArgoCD's `arr-stack-app.yaml` loads via `valueFiles: [../../examples/values-prod.yaml]` — and that file was a STALE copy. Required v0.2.5 to manually re-sync. Symlink eliminates the drift class entirely.
**Source**: 04-08-CUTOVER-LOG.md Bug 5; symlink shipped post-UAT.

### Auto-tag CI job (B3 Path A) over manual release tagging
**What**: `.github/workflows/chart-lint.yml` includes a `tag:` job that fires on push-to-main when `lint:` is green. Uses `mathieudutour/github-tag-action@v6.2` with `default_bump: patch` + `tag_prefix: v`.
**Why**: Closes the manual-tag latency gap for SC#2 (REQ-pr-to-cluster-latency). Without it, Renovate auto-merge on arr-stack would land but a human would have to cut the tag before my-kluster's Renovate scan picks it up — easily violating the < 1h target overnight or on weekends.
**Source**: 04-RESEARCH.md §"chart-lint.yml" + B3 fix from plan-checker iteration; verified working across v0.2.2..v0.2.7 (6 auto-tags in ~24h).

---

## Lessons

### Helm 4 has a multi-alias-of-same-chart regression (#12748)
**What**: `helm dependency build` writes ONE tarball per unique chart+version, even when Chart.yaml declares N aliased dependencies of the same chart. Helm 4's render then fails with `"found in Chart.yaml, but missing in charts/ directory: app-template, app-template, ..."` — it expects N separate copies. Helm 3.x handled this differently.
**Context**: Discovered during Plan 04-08 cutover when ArgoCD's `helm template` failed on v0.2.2. CI workflow had a `tar -xzf` workaround but ArgoCD has no equivalent hook.
**Source**: 04-08-CUTOVER-LOG.md Bug 3; arr-stack PR #2 (commit `5bc0b0d`, tag v0.2.3) vendors the unpacked `app-template/` directory.

### `global.fullnameOverride` is NOT enough — also need `global.nameOverride`
**What**: bjw-s/app-template 5.0.0 uses TWO helpers: `chart.names.fullname` (controls resource names like `metadata.name`) AND `chart.names.name` (controls the `app.kubernetes.io/name` label). The fullname helper checks `.Values.global.fullnameOverride`; the name helper checks `.Values.global.nameOverride`. Setting only fullnameOverride leaves the name label at app-template's auto-default = `.Release.Name`.
**Context**: Originally Phase 4 plans set only `global.fullnameOverride: <alias>`, on the assumption that fullnameOverride would propagate to the name label too. Bug 1's investigation surfaced the two-helper split.
**Source**: 04-08-CUTOVER-LOG.md §"Resolution" + read of `charts/arr-stack/charts/app-template/charts/common/templates/lib/chart/_names.tpl`.

### app-template auto-fills missing `global.nameOverride` with `.Release.Name`
**What**: `charts/arr-stack/charts/app-template/templates/common.yaml` has a hardcoded `app-template.hardcodedValues` block that injects `global.nameOverride = "{{ .Release.Name }}"` when the user doesn't provide one. This means an UNSET `global.nameOverride` is NOT the same as a "fall-through to chart name" — it's actively overridden to the release name.
**Context**: Bug 1 root cause. Even if we hadn't set `global.fullnameOverride`, the chart-name label would still have collapsed to `arr-stack` for every alias due to this defaulter.
**Source**: `charts/arr-stack/charts/app-template/templates/common.yaml` lines 4-9.

### app-template's SA name helper picks the IDENTIFIER, not the resource name
**What**: When `enabledServiceAccounts` has one entry, `_serviceAccountName.tpl` returns `$enabledServiceAccounts | keys | first` — the YAML key (identifier), not the SA resource's resolved `metadata.name`. The SA resource itself is named via `chart.names.fullname` (so it can be `sonarr` via fullnameOverride), but the Deployment's `serviceAccountName` reference uses the identifier. Without an explicit `serviceAccount.<alias>: {}` declaration, the chart's `values/_init.tpl` auto-injects `serviceAccount.<.Release.Name>: {}` — making the pod look for SA `arr-stack`, which doesn't exist.
**Context**: Bug 2. Manual workaround during cutover was `kubectl create sa arr-stack -n selfhost`; proper fix shipped in v0.2.6 by declaring `serviceAccount.<alias>: {}` per alias.
**Source**: `charts/arr-stack/charts/app-template/charts/common/templates/lib/pod/fields/_serviceAccountName.tpl` + `values/_init.tpl`.

### ADR-6 baseline catches drift BEFORE planning bakes assumptions
**What**: The original Phase 4 plan assumed `app-template 4.6.2` based on the my-kluster local checkout. The ADR-6 pre-cutover snapshot (Plan 04-01 Task 1.1) revealed `app-template 5.0.0` was actually deployed in production since 2026-05-11 (my-kluster Renovate PR #1381). Without the baseline, the cutover would have silently downgraded all 8 media apps.
**Context**: Plan 04-01 Task 1.1 fired at the START of Wave 0 — before the chart skeleton (Plan 04-02) was even written. The drift discovery prompted a full replan (RESEARCH.md rewrite + Plan 04-02..04-09 regenerated against v5.0.0). Cheap to catch then; expensive if it had reached cutover.
**Source**: 04-01-DRIFT-NOTE.md; STATE.md last_activity entry for 2026-05-13.

### Renovate uses JS regex `(?<name>...)`, Python uses `(?P<name>...)`
**What**: Renovate's `customManagers.matchStrings` regex runs on RE2/JS — named groups are `(?<name>...)`. Python's `re` module requires `(?P<name>...)` for named groups. A single regex string can't satisfy both.
**Context**: Plan 04-06 included a Python synthetic test that compiled the regex from `renovate.json` and applied it locally. With Python syntax in renovate.json, Renovate's validator rejected it; with JS syntax, Python's `re.findall` raised `error: unknown extension ?<d`. Fix in v0.2.5: keep JS syntax in renovate.json, convert `(?<...>)` → `(?P<...>)` on the fly in the Python test.
**Source**: PR #2 (chart-lint.yml fix); 04-08-CUTOVER-LOG.md.

### `renovate-config-validator` is shipped INSIDE the `renovate` npm package
**What**: There's no `renovate-config-validator` package on npmjs.com. The binary is inside `renovate` package itself. Invocation: `npm install -g renovate@39 && renovate-config-validator <file>`, OR per official docs `npx --yes --package renovate -- renovate-config-validator <file>` (the latter failed on local node v24 in this project; the former worked on CI's node v22).
**Context**: First chart-lint CI run on PR #1 failed at the validator step with `npm error 404 Not Found - GET https://registry.npmjs.org/renovate-config-validator`.
**Source**: chart-lint workflow run 25831448253; fix in PR #1 commit `b3df975`.

### Image-digest-to-semver resolution can downgrade
**What**: D-04-PIN-01 resolves each running `:latest` digest to its corresponding semver tag via the registry. But if `:latest` has been advancing through versions over time (Renovate-driven on the upstream repo), the digest's "best match" semver may be ancient — and the on-disk state (SQLite DB, config schema) has been migrated by NEWER versions in between. Pinning to the resolved semver effectively downgrades the binary against a forward-migrated state.
**Context**: cleanuparr digest `9b8f7a5f…` matched semver `2.3.3`. The binary started but immediately crashed with `SQLite Error: no such column: g.search_delay` — the DB had been written by 2.9.x. Fix in v0.2.4: bump pin to `2.9.6`. Resolution heuristic for next time: cross-check digest's semver against upstream's latest release; if the gap is more than 1 minor, pin to upstream latest instead.
**Source**: 04-08-CUTOVER-LOG.md Bug 4.

### Suspended CronJobs mask config-schema regressions
**What**: The arrconf CronJob was SUSPENDED in production since 2026-05-09T06:48:11Z (Phase 02.2 forensic period — D-02.2-AUTH-REGRESSION). During that suspension, my-kluster's `arrconf.yml` ConfigMap retained the obsolete Phase 1 `apps:` schema while arrconf v0.2.1 binary (shipped in Phase 3) tightened the schema to flat root keys (D-03-05) via `model_config = ConfigDict(extra='forbid')`. The schema mismatch existed in production for 5+ days but the suspended CronJob never tried to load it. Cutover re-enabled the schedule via the new umbrella CronJob → bug surfaced immediately.
**Context**: UAT Test 7. Fix in v0.2.7. Promote to deferred-items: any time we suspend a CronJob during forensic / debugging periods, ALSO add a config-schema validation step to the un-suspend procedure.
**Source**: 04-UAT.md Test 7 + 04-08-CUTOVER-LOG.md Bug-fix list.

### `examples/values-prod.yaml` file-copy invariant is unenforceable
**What**: D-04-VALUES-03 declared `examples/values-prod.yaml` as a content-copy of `charts/arr-stack/values.yaml`. Plan 04-05 ensured initial sync. But the copy invariant has no enforcer — any subsequent edit to one file silently desynchronizes them.
**Context**: Bug 5 of the cutover. arr-stack PR #3 fixed cleanuparr in the canonical values.yaml but missed the example copy; ArgoCD continued to render the OLD value. Cost a full release iteration (v0.2.5) to catch and re-sync. Post-Phase-4 hardening: replace the copy with a symlink (PR #7) — `ln -s` doesn't drift.
**Source**: 04-08-CUTOVER-LOG.md Bug 5; PR #7.

---

## Patterns

### Orphan-first cross-repo App-of-Apps cutover
**Pattern**: For ArgoCD App-of-Apps setups where a parent prunes child Apps based on a directory listing: (1) suspend the parent's `automated:`, (2) remove `resources-finalizer.argocd.argoproj.io` from each child you're replacing, (3) merge the cross-repo PR that adds the new structure + deletes the old, (4) manually sync the parent (`kubectl patch application <parent> --type merge -p '{"operation":{"sync":{}}}'`) to delete the old child Application CRs WITHOUT cascading to K8s resources, (5) manually sync the new App with `Replace=true + Force=true` to adopt the orphaned resources, (6) restore parent's `automated:`.
**When to use**: Any time you collapse N unit Apps into 1 umbrella in an App-of-Apps system, or rename `app.kubernetes.io/instance` labels on existing Deployments/StatefulSets.
**Source**: 04-08-CUTOVER-LOG.md (this surfaced live; cost ~30 min to discover + workaround). Worth promoting to the `gsd-cutover` knowledge base if one exists.

### `kubectl patch application` for argocd-CLI-free sync
**Pattern**: When `argocd` CLI isn't installed on the operator workstation, drive ArgoCD App syncs via kubectl: `kubectl annotate application <app> -n argocd argocd.argoproj.io/refresh=hard --overwrite` followed by `kubectl patch application <app> -n argocd --type merge -p '{"operation":{"sync":{"syncStrategy":{"apply":{"force":true}}}}}'`. The `operation:` field on the Application CR is the API surface ArgoCD's CLI uses.
**When to use**: Phase 02.2 P05 documented argocd CLI absence on operator workstation. Carried through Phase 4 cutover. Should be the default pattern.
**Source**: STATE.md Phase 02.2 P05 lesson; 04-08-CUTOVER-LOG.md.

### Symlink for single-source-of-truth-with-two-consumers
**Pattern**: When two paths conceptually hold the same file (e.g., chart values vs ArgoCD valueFiles example) and risk drift, replace the secondary with a symlink to the canonical. Both Helm and ArgoCD follow symlinks at the chart-source level. Renovate's `customManagers` regex still matches against the symlink target.
**When to use**: Any time a file-copy invariant becomes unenforceable. Look for `cp -f X Y` patterns in plans or CI scripts — likely candidates.
**Source**: PR #7 (Bug 5 follow-up).

### Helm 4 multi-alias `tar -xzf` workaround
**Pattern**: After `helm dependency build`, unpack the dependency tarball into a directory of its name: `tar -xzf charts/<chart>/charts/<dep>-<ver>.tgz -C charts/<chart>/charts/`. Helm 4 then resolves all N aliased dependencies against the single unpacked directory. Required for both local renders and ArgoCD source rendering. Best approach: COMMIT the unpacked vendor directory and gitignore only the `.tgz` (so ArgoCD never has to do dep resolution at all).
**When to use**: Any umbrella chart with multiple aliased dependencies of the same chart in Helm 4+. Helm 3.x handles this via separate tarballs per alias.
**Source**: arr-stack PR #2 (commit `5bc0b0d`, tag v0.2.3) — and the .gitignore exception that makes it stick.

### Auto-tag GitHub Action with push-to-main + lint-green gate
**Pattern**: A `tag:` job in chart-lint.yml: `needs: lint`, `if: github.event_name == 'push' && github.ref == 'refs/heads/main'`, `permissions: contents: write`, uses `mathieudutour/github-tag-action@v6.2` with `default_bump: patch` + `tag_prefix: v`. Every clean merge to main creates a new patch tag automatically. Renovate downstream consumers pick up the new tag on their next scan.
**When to use**: Any time a release-tag manual step would block a < 1h end-to-end SLO. Closes the manual-tag bottleneck for Renovate-driven multi-repo flows.
**Source**: arr-stack chart-lint.yml; verified across 6 auto-tags in ~24h (v0.2.2..v0.2.7).

### gsd-pr-branch flow for full-history-local + clean-PR-upstream
**Pattern**: Local main keeps the full `.planning/` history (PLAN.md, SUMMARY.md, etc.). PRs are made from feature branches that get squash-merged on GitHub. Renovate/auto-tag references the squash commits and tags. Local main and origin/main diverge by design (172 commits ahead at one point in Phase 4) — that's expected. To create a clean upstream PR from a feature branch, `/gsd-pr-branch` filters out planning-only commits via cherry-pick + path filtering.
**When to use**: Projects that use GSD planning artifacts and want a clean code-review surface upstream without losing local context.
**Source**: `.claude/skills/gsd-pr-branch/SKILL.md`; used implicitly in PR #1 (we pushed phase-4-umbrella-cutover with .planning/ included — could have been cleaner via gsd-pr-branch).

### ADR-6 baseline via kubectl-only fallback
**Pattern**: When argocd CLI is absent, capture the ADR-6 baseline with: `kubectl -n argocd get application <name> -o yaml` (Application CR + status) + `kubectl -n <ns> get all,ingress,configmap,pvc,secret -l app.kubernetes.io/instance=<name> -o yaml` (live K8s state). Combine both into one file per app. Diff against `helm template <umbrella>` output (with exclusion list for ArgoCD-injected `argocd.argoproj.io/*` annotations, `resourceVersion`, `creationTimestamp`, etc.) for cutover byte-equivalence verification.
**When to use**: Plan 04-01 + Plan 04-08 patterns. The kubectl fallback IS the primary path when argocd CLI is unavailable.
**Source**: 04-01-DRIFT-NOTE.md operator runbook; `tools/scripts/byte-equivalence-diff.sh`.

### Iterative bug-fix release loop with rapid auto-tag
**Pattern**: When a cutover surfaces nested bugs (Helm regression → schema drift → label semantics → SA defaulter), ship each fix as a tiny PR + new patch tag + my-kluster targetRevision bump rather than batching. Each iteration costs ~5 min wall-clock thanks to auto-tag. The iteration loop became the natural debugging shape, not a failure mode.
**When to use**: Any cutover or refactor where surface-level bugs likely mask deeper ones. Don't try to fix everything in one PR — let the loop expose layers.
**Source**: Phase 4 release sequence v0.2.2..v0.2.7 (6 releases in ~24h).

---

## Surprises

### Phase 4 took 6 release iterations, not 1 — and that turned out to be fine
**What**: The plan implied a single release for the cutover (v0.2.2). Reality: v0.2.2 (cutover) → v0.2.3 (Helm 4) → v0.2.4 (cleanuparr) → v0.2.5 (values-prod sync) → v0.2.6 (per-alias overrides + SA) → v0.2.7 (arrconf schema). Each surfaced a layer of bugs that wasn't visible until the previous layer was fixed.
**Impact**: Time-cost was acceptable because the auto-tag job made each iteration cheap. The iteration loop became a debugging asset, not a failure pattern. Recorded as "iterative bug-fix release loop" pattern.
**Source**: 04-08-CUTOVER-LOG.md Cutover release sequence.

### Internal cross-app traffic had been silently broken in production for weeks
**What**: The pre-cutover unit Apps had `app.kubernetes.io/name: <app>` (per-app), so Service selectors matched only their own pod. After cutover, the umbrella's Bug 1 caused every Service to select on `app.kubernetes.io/name: arr-stack` (release name) — matching ALL umbrella pods. But what's surprising is that this looked OK from browser smoke checks (oauth2-proxy `auth-url` annotation returns 302 BEFORE the Service is hit), and the only public app without oauth2-proxy is prowlarr — which is exactly where the bug surfaced as 50/50 200/502.
**Impact**: A normal "cluster post-cutover walkthrough" with browser-only tests would have missed the bug entirely. Promoted as a UAT pattern: **internal cross-app traffic checks** (e.g., `kubectl exec deploy/sonarr -- curl http://prowlarr:9696/api/v1/system/status`) belong alongside ingress smoke.
**Source**: UAT Test 6 (10× prowlarr retries) — caught it; 04-08-CUTOVER-LOG.md Bug 1.

### The pre-cutover production was also broken (just masked by SUSPEND)
**What**: arrconf v0.2.1 was deployed in Phase 3 with the strict pydantic schema. The my-kluster `arrconf.yml` ConfigMap kept the old Phase 1 schema. The mismatch existed in production from 2026-05-09 onward — but the arrconf CronJob was SUSPENDED for the entire window (forensic period from D-02.2-AUTH-REGRESSION). The bug stayed latent.
**Impact**: Phase 4 cutover unsuspended the CronJob via the new umbrella schedule, and the bug surfaced immediately. Phase 4 didn't *introduce* the bug — it *exposed* it. Worth ~$0 to fix here; would have been $$$ to fix in a stand-alone "why is arrconf broken in production?" incident later.
**Source**: 04-UAT.md Test 7 + STATE.md "CronJob arrconf SUSPENDED at 2026-05-09T06:48:11Z" entry.

### ADR-6 baseline saved Phase 4 from a silent app-template downgrade
**What**: Pre-Wave-0, the Phase 4 plan assumed app-template 4.6.2 (based on my-kluster local checkout). The ADR-6 baseline run revealed production was at 5.0.0 since 2026-05-11 (Renovate PR #1381 on my-kluster, one day before Phase 4 context was gathered). Without ADR-6, the cutover would have committed Chart.yaml with `version: 4.6.2` × 8 deps and silently downgraded everything.
**Impact**: One day of replan work (RESEARCH.md rewrite + Plan 04-02..04-09 regenerate) vs. an unbounded production incident with PVC schema rollbacks. Cheapest moment Phase 4 had to catch this.
**Source**: 04-01-DRIFT-NOTE.md.

### `git commit -am` swept stash-popped WIP into a cross-repo PR
**What**: While I had user's my-kluster WIP files stash-popped (README.md modifications + beszel/beszel.yml deletion from a much earlier session), I ran `git commit -am "..."` to commit a one-line targetRevision bump. The `-a` flag staged ALL tracked modifications, including the unrelated WIP. PR #1389 ended up with 3 file changes instead of 1.
**Impact**: Cosmetic (both unintended changes were benign per investigation), but bad hygiene. Lesson: in a workflow where stash-pop leaves working files around, ALWAYS `git add <specific file>` rather than `-a`. Recorded in 04-08-CUTOVER-LOG.md as a postmortem item.
**Source**: my-kluster PR #1389 postmortem.

### Auto-tag job fires within 30s of a green chart-lint
**What**: The mathieudutour action turned out to be very fast — typically ~30s from "push to main" to "tag created on origin", assuming chart-lint takes ~3-5 min. The end-to-end "PR-merge → tag visible to Renovate" loop is dominated by chart-lint, not the tag job itself.
**Impact**: The release iteration loop felt low-friction. Each fix cycle (commit → push → CI green → auto-tag → my-kluster bump → ArgoCD sync) took ~10-15 min on average. The 72h SC#2 budget is comfortable; even the < 1h end-to-end target should be easy.
**Source**: Observed across v0.2.2 → v0.2.7 release sequence (~24h elapsed for 6 releases).

### arrconf's "no-op" log event was the dispositive signal we'd never seen
**What**: Plan 04-08 UAT Test 7 (arrconf smoke) showed `{"app": "sonarr", "count": 1, "event": "no-op"}` in the logs. This is the idempotence proof that Phase 3 D-13/D-22 designed for: arrconf observed the YAML config matched cluster state exactly, applied nothing. Before Phase 4 the production CronJob was suspended; before Phase 3 the dry-run mode never ran apply. This was the first production-equivalent observation of idempotent arrconf in 200+ days of project history.
**Impact**: Phase 3's "idempotence is the golden rule" decision (CLAUDE.md) finally has an in-cluster proof point. Worth a `LEARNINGS.md` entry on its own.
**Source**: 04-UAT.md Test 7 logs.

---

## Notes for next phase (Phase 5: qBittorrent reconciler + split tv/anime/family)

Phase 5 should benefit from:
- The orphan-first cutover pattern (if it needs to touch existing K8s resources)
- The auto-tag CI flow (no manual release steps)
- The Helm 4 multi-alias vendor pattern (Chart.yaml stays as-is)
- The kubectl-only ArgoCD sync pattern (still no argocd CLI on workstation)
- arrconf v0.2.1 binary IS WORKING in production now — no config schema regressions expected as long as new YAML follows D-03-05 flat root structure

Phase 5 will introduce NEW reconciler (qBittorrent uses cookie-based login auth, not X-Api-Key like *arr) — `client_base.py` will need an auth-strategy override. Plan ahead: write the auth abstraction in the same iteration that adds qBittorrent (don't defer).

Split tv/anime/family will need values.yaml restructure in arr-stack chart — each Sonarr/Radarr instance gets 3 root folders + 3 download clients + 3 tags as YAML lists. Worth a values.schema.json update too (Phase 4's schema is permissive on the relevant fields).
