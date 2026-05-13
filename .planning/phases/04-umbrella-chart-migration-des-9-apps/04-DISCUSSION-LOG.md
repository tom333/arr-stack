# Phase 4: Umbrella chart + migration des 9 apps - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `04-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-05-12
**Phase:** 4-Umbrella chart + migration des 9 apps
**Areas discussed:** Cutover strategy, values.yaml shape + file layout, CronJob templates (arrconf + configarr), Pinning `:latest` (qbit/flare/cleanuparr)

---

## Cutover strategy

### How do you want to flip from 9 unit ArgoCD Apps + 2 custom charts to the umbrella?

| Option | Description | Selected |
|--------|-------------|----------|
| Atomic big-bang in one PR | Single my-kluster PR adds `arr-stack-app.yaml`, deletes 10 unit Apps + `charts/configarr/` + `charts/arrconf/`. Short risk window. | ✓ |
| Two-PR atomic (deploy, then cleanup) | PR-A: deploy umbrella alongside the 9 unit Apps with a shadow name. PR-B: delete units. Two windows but each reversible. | |
| Progressive per-app waves | Multiple PRs, 1-3 apps per wave. Risk: overlap on selfhost namespace with `prune: true`. | |
| Let Claude decide | — | |

**User's choice:** Atomic big-bang in one PR.
**Notes:** Aligns with byte-equivalent + ServerSideApply adoption plan.

### How do you protect the cutover?

| Option | Description | Selected |
|--------|-------------|----------|
| Suspend, dry-run diff, then sync | Remove `automated.*` initially. Run `argocd app diff` + `argocd app sync --server-side` manually. Re-enable automated after green. | ✓ |
| Trust ServerSideApply adoption | Merge with full `automated.{selfHeal,prune,ServerSideApply}` enabled. Lowest effort. | |
| Pre-delete unit Apps without cascade | `kubectl delete application --cascade=orphan` per app. Decouples Application from K8s lifecycle. | |
| Let Claude decide | — | |

**User's choice:** Suspend, dry-run diff, then sync.

### Byte-equivalent at cutover or consolidate?

| Option | Description | Selected |
|--------|-------------|----------|
| Byte-equivalent first, then iterate | Zero behavioral diff. Refactors land later. | ✓ |
| Consolidate at cutover | Use the moment to drop dead config, normalize defaults. Larger diff to audit. | |
| Let Claude decide | — | |

**User's choice:** Byte-equivalent first, then iterate.

### Rollback plan?

| Option | Description | Selected |
|--------|-------------|----------|
| Re-deploy the 9 unit Apps from git history | Revert my-kluster PR; ArgoCD restores units. PVCs survive. | ✓ |
| Keep `.disable` copies of unit Apps in my-kluster for 1 milestone | Roll-forward bias: keep umbrella, fix the issue. | |
| Let Claude decide | — | |

**User's choice:** Re-deploy from git history (revert PR).

---

## values.yaml shape + file layout

### Top-level shape of `charts/arr-stack/values.yaml`?

| Option | Description | Selected |
|--------|-------------|----------|
| Flat: one key per app-template alias | Simplest to debug. 1:1 with `dependencies[].alias`. | |
| Nested by domain | `media: {…}` / `tools: {…}`. Cleaner mental model, needs helper indirection. | |
| Flat + shared `defaults` block | Top-level `defaults:` merged into each alias. Eliminates TZ/PUID/PGID/cert-manager triplication. Renders byte-equivalent. | ✓ |

**User's choice:** Flat + shared `defaults` block.
**Notes:** Merge mechanism deferred to planner/researcher (app-template native vs `_helpers.tpl`).

### Where do `arrconf.yml` and `configarr.yml` live?

| Option | Description | Selected |
|--------|-------------|----------|
| Top-level `charts/arr-stack/files/` | Matches CLAUDE.md target structure. Mirrors my-kluster layout. | ✓ |
| Per-section nested under values | Inline as `arrconf.config: \|` multi-line string. Breaks `# yaml-language-server: $schema=…` directive. | |
| Per-app subdirs | `files/arrconf/arrconf.yml` etc. Extra nesting, no immediate benefit. | |

**User's choice:** Top-level `charts/arr-stack/files/`.

### Production values strategy?

| Option | Description | Selected |
|--------|-------------|----------|
| `values.yaml` IS prod | Matches spec §9.2 (no `helm.values:` in arr-stack-app.yaml). | ✓ |
| `values.yaml` minimal + `examples/values-prod.yaml` authoritative | Cleaner separation, transferable to forks, but adds indirection that breaks spec §9.2 example. | |
| Let Claude decide | — | |

**User's choice:** `values.yaml` IS prod.

### Scope of `values.schema.json`?

| Option | Description | Selected |
|--------|-------------|----------|
| Top-level only | Schema enforces presence/types at top-level. Cheap to write, sufficient for CI gate. | |
| Full strict schema | Every documented value typed and constrained. Generated via `helm schema-gen`, hand-tightened. Heavy upfront. | ✓ |
| Defer to a follow-up | Skip in Phase 4. Violates REQ-helm-validation strict reading. | |

**User's choice:** Full strict schema.

### Documentation scope (operator-added during discussion)?

| Option | Description | Selected |
|--------|-------------|----------|
| Targeted edits per-section | Edit only sections that changed. | |
| Full doc refresh | Audit README + CLAUDE.md end-to-end against current state. Clears doc debt. | ✓ |
| Targeted edits + new sections | Bounded scope + new "Umbrella chart" / "Umbrella conventions" sections. | |

**User's choice:** Full doc refresh.
**Notes:** Captured as D-04-DOCS-01. User flagged this explicitly via free-text turn ("il faut aussi mettre à jour la documentation dans le README.md et CLAUDE.md pour refléter tous les changements").

---

## CronJob templates (arrconf + configarr)

### How do arrconf + configarr CronJobs get deployed by the umbrella?

| Option | Description | Selected |
|--------|-------------|----------|
| Custom templates (keep current) | Port my-kluster's `templates/cronjob.yaml` + `configmap.yaml` into umbrella. Matches CLAUDE.md target. | |
| bjw-s app-template alias | `controllers.main.type: CronJob` + `persistence.config.type: configMap`. Zero custom templates. | ✓ |
| Hybrid — app-template for arrconf, custom for configarr | Pragmatic but heterogeneous. | |
| Let Claude decide | — | |

**User's choice:** bjw-s app-template alias.
**Notes:** Drives the contradiction with CLAUDE.md "Structure cible" — addressed by D-04-DOCS-01 full refresh.

### Two behaviors must survive the move to app-template. How strict?

| Option | Description | Selected |
|--------|-------------|----------|
| Both must be preserved | `checksum/config` Pod-rotation AND `concurrencyPolicy: Forbid`. Falls back to template overrides if app-template lacks direct support. | |
| Forbid yes, checksum can drop | `Forbid` critical. `checksum/config` is nice-to-have — next schedule tick re-reads ConfigMap. | ✓ |
| Let Claude decide | — | |

**User's choice:** Forbid yes, checksum can drop.

### arrconf args at Phase 4 cutover?

| Option | Description | Selected |
|--------|-------------|----------|
| Apply all 3 apps | `apply --apps sonarr,radarr,prowlarr`. Phase 3 reconcilers go live. host_config opt-in is the safety net. | ✓ |
| Sonarr only at cutover, expand later | Keep `--apps sonarr`; expand in follow-up. | |
| Let Claude decide | — | |

**User's choice:** Apply all 3 apps.

### Secret consolidation?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep two Secrets, two `envFrom` blocks | Zero cutover churn. Least privilege. | ✓ |
| Consolidate into one `arr-stack-env` Secret | Flatter post-ESO, but cutover requires Secret rename + careful rollout. | |
| Let Claude decide | — | |

**User's choice:** Keep two Secrets, two `envFrom` blocks.

---

## Pinning `:latest` (qbit/flare/cleanuparr)

### Pin source of truth?

| Option | Description | Selected |
|--------|-------------|----------|
| Pin to currently-running cluster digest | Byte-equivalent at cutover. Renovate immediately proposes upgrades. | ✓ |
| Pin to latest upstream semver | Risk: unaudited version bump at cutover. | |
| Currently-running, then immediate Renovate PR | Best of both — clean cutover + visible audit trail. | |

**User's choice:** Pin to currently-running cluster digest.
**Notes:** Renovate handles the "currently-running → upstream latest" delta post-cutover naturally.

### How to capture the running digest?

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-plan checkpoint task | Operator runs `kubectl … -o jsonpath` for each app, output into `evidence/current-image-tags.txt`. | ✓ |
| Inline lookup during planning | Researcher pre-fills with 'latest known good' + explicit operator-review TODO. | |
| Let Claude decide | — | |

**User's choice:** Pre-plan checkpoint task.

### Renovate annotation shape?

| Option | Description | Selected |
|--------|-------------|----------|
| One annotation per image | `# renovate: image=<repo>` above each `repository:` line. CLAUDE.md verbatim. | ✓ |
| Global `customManagers` regex without inline annotation | Breaks CLAUDE.md documented contract. | |
| Let Claude decide | — | |

**User's choice:** One annotation per image.

### Canonical Renovate-bump E2E test target?

| Option | Description | Selected |
|--------|-------------|----------|
| First Renovate-detected bump after cutover | No pre-coordination. Fallback: manually stale-pin one image. | ✓ |
| Pre-stage a known-stale tag to force a bump | Validates path within hours of merge. Extra cognitive load. | |
| arrconf image itself is the canary | First arrconf release post-Phase 4 triggers Renovate end-to-end. | |
| Let Claude decide | — | |

**User's choice:** First Renovate-detected bump after cutover.

---

## Claude's Discretion

(Captured verbatim in `04-CONTEXT.md` `<decisions>` section under "Claude's Discretion".)

- app-template version pin (currently `4.6.2` in my-kluster — verify newest stable at planning time).
- `defaults:` merge mechanism (app-template native vs `_helpers.tpl`).
- arrconf release tag at cutover (`v0.2.1` patch vs `v0.3.0` minor, depending on source-vs-packaging change).
- Umbrella `Chart.yaml: version` (start at `0.1.0`).
- CronJob schedule unification (keep both at `0 */4 * * *`).
- `values.schema.json` authoring tool (`helm schema-gen` plugin vs hand-write).
- Renovate `packageRules` (automerge minor/patch, manual majors — standard).
- PR sequencing within arr-stack repo (one big vs split waves — planner's call).
- Cutover sequencing details (suspend → snapshot → merge → diff → sync → verify → re-enable).

---

## Deferred Ideas

- Consolidating duplicate env vars / ingress annotation refactors beyond the `defaults:` block — defer to a v0.3.0 cleanup PR (D-04-CUTOVER-03).
- Single `arr-stack-env` Secret consolidation — defer to Phase 8 ESO.
- `release.yml` / release-please automation (Q4) — manual tags remain per Phase 1 D-01.
- Pre-stage stale pin to force Renovate to fire immediately — fallback only.
- Image version bumps beyond pinning currently-running — defer to Renovate's first auto-PRs.
- `helm test` hooks — not in Phase 4 scope.
