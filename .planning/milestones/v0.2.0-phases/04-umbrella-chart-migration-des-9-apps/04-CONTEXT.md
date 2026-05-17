# Phase 4: Umbrella chart + migration des 9 apps — Context

**Gathered:** 2026-05-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the umbrella Helm chart `charts/arr-stack/` and migrate the homelab media stack from **10 separate ArgoCD Applications + 2 custom charts in `my-kluster`** to **1 unified ArgoCD Application pointing at this repo**.

**In scope:**
- `charts/arr-stack/Chart.yaml` with `dependencies:` pointing to `bjw-s/app-template` v4.6.2 (per ADR-2 Option A), **one alias per service for all 11 components**: `sonarr`, `radarr`, `prowlarr`, `cleanuparr`, `qbittorrent`, `seerr`, `flaresolverr`, `jellyfin` (8 media apps with UI) + `arrconf` + `configarr` (2 CronJob-style components, ADR-2 Option A applied uniformly per D-04-CRON-01).
- `charts/arr-stack/values.yaml` with:
  - Shared `defaults:` block (TZ=Europe/Paris, PUID=1000, PGID=1000, cert-manager issuer, oauth2-proxy annotations) merged into each alias via app-template's native inheritance or a `_helpers.tpl` indirection (planner/researcher decides mechanism).
  - One top-level key per alias, holding the per-app overrides.
  - All images annotated with `# renovate: image=<repo>` per CLAUDE.md convention.
  - All `:latest` tags pinned to the **currently-running cluster digest** (qbittorrent, flaresolverr, cleanuparr).
- `charts/arr-stack/values.schema.json` — **full strict schema** (generated via `helm schema-gen` plugin then hand-tightened). CI blocks on schema drift / values mismatch.
- `charts/arr-stack/files/arrconf.yml` + `charts/arr-stack/files/configarr.yml` — config files mounted as ConfigMaps into the respective CronJob Pods via app-template's `persistence.<name>.type: configMap`. Top-level `files/` directory (CLAUDE.md target layout).
- arrconf CronJob args: `apply --apps sonarr,radarr,prowlarr` (Phase 3 reconcilers live; opt-in `host_config.enable: false` per D-03-04 is the safety net).
- arrconf + configarr CronJob behaviors: `concurrencyPolicy: Forbid` **MANDATORY**; `checksum/config` Pod-rotation annotation **dropped** (next scheduled tick re-reads ConfigMap, ≤4h delay).
- arrconf-env + configarr-env Secrets remain **separate** (least privilege, zero cutover churn). Operator-applied via `kubectl apply -f my-kluster/secrets/{arrconf,configarr}-secret.yaml` (gitignored, manual bootstrap until Phase 8 ESO).
- ADR-6 pre-deploy snapshot of all 9 production apps + `charts/arrconf/` + `charts/configarr/` rendered manifests captured BEFORE the cutover PR.
- **Pre-plan operator checkpoint task** capturing currently-running cluster image digests into `.planning/phases/04-*/evidence/current-image-tags.txt` (3 `:latest` apps; planner reads to populate `values.yaml` pins).
- `examples/values-prod.yaml` — shipped as a documentation copy/symlink of `values.yaml` (per spec §9.2: `arr-stack-app.yaml` has empty `helm.values:`, so `values.yaml` IS prod).
- `.github/workflows/chart-lint.yml` — runs `helm lint`, `helm dependency update`, `helm template charts/arr-stack/ -f examples/values-prod.yaml | kubeconform -`, and validates `values.yaml` parses against `values.schema.json` (REQ-helm-validation; CI blocks).
- `renovate.json` updated with `customManagers` regex matching `# renovate: image=<repo>` annotations in `values.yaml` (REQ-renovate-image-tracking).
- Cross-repo PR in `my-kluster`:
  - Add `argocd/argocd-apps/arr-stack-app.yaml` pointing to this repo (`path: charts/arr-stack`, `targetRevision: vX.Y.Z`).
  - Delete the **10 unit ArgoCD Applications**: sonarr, radarr, prowlarr, cleanuparr, configarr, qbittorrent, seerr, flaresolverr, jellyfin, **arrconf** (the temporary Phase 2 chart deployment).
  - Delete `my-kluster/charts/configarr/` + `my-kluster/charts/arrconf/`.
- **Full doc refresh**: `README.md` (root) audited against Phase 0-4 state — new "Umbrella chart" + "Deploy" + "Operator runbook" sections; `CLAUDE.md` "Structure cible" becomes "Structure actuelle", "Intégration avec my-kluster" rewritten for single ArgoCD App, "Bootstrap" section archived to "Historical bootstrap (Phase 0-3)". README must clear REQ-readme-onboarding (< 30 min onboarding).
- Cutover orchestration: suspend `automated.{selfHeal,prune}` on `arr-stack-app.yaml` at first sync, run `argocd app diff arr-stack` + `argocd app sync --server-side` manually, verify against ADR-6 baseline, then re-enable `automated.*`.
- Post-cutover verification: rendered K8s manifests are byte-equivalent to current state (D-04-CUTOVER-03); ingresses still resolve (sonarr.tgu.ovh, …, jellyfin.tgu.ovh); shared mounts intact (`/opt/media-stack/torrents` hostPath, `media-nas-pvc` NFS); Jellyfin no-oauth2-proxy ingress preserved.

**Out of scope (deferred):**
- Consolidating duplicate env vars / ingress annotation refactors beyond the `defaults:` block (deferred to v0.3.0 — D-04-CUTOVER-03 byte-equivalent rule).
- Secret consolidation into a single `arr-stack-env` Secret (deferred to Phase 8 ESO rewrite).
- ESO / Akeyless ExternalSecret wiring (Phase 8).
- qBittorrent reconciler / categories / split tv-anime-family (Phase 5).
- Seerr / Jellyfin reconcilers (Phase 6 / 7).
- Bumping cluster image versions beyond pinning currently-running digests (Renovate handles bumps post-cutover).
- Adding `release.yml` / release-please automation (Q4 deferred; manual semver tags remain per D-01 from Phase 1).

</domain>

<decisions>
## Implementation Decisions

### Cutover strategy

- **D-04-CUTOVER-01: Atomic big-bang single PR in `my-kluster`.** One PR adds `arr-stack-app.yaml` and deletes the 10 unit `Application` YAML files + `charts/configarr/` + `charts/arrconf/`. Rationale: byte-equivalent rendering means ArgoCD's first sync adopts existing K8s resources via ServerSideApply field manager; a phased migration would require coexisting Applications managing overlapping K8s objects, which `prune: true` makes hazardous.
- **D-04-CUTOVER-02: Suspend `automated.{selfHeal,prune}` for the first sync.** The `arr-stack-app.yaml` ships with `automated:` removed/commented at PR merge time. Operator runs `argocd app diff arr-stack` → reviews diff against ADR-6 baseline → `argocd app sync --server-side` manually → re-enables `automated.{selfHeal,prune}` in a follow-up one-line PR once green. Mitigates the prune-race risk.
- **D-04-CUTOVER-03: Byte-equivalent at cutover.** `helm template charts/arr-stack/ -f examples/values-prod.yaml` rendered output must match `argocd app manifests <unit-app>` for each of the 10 unit Apps (modulo labels/annotations ArgoCD-added). Zero behavioral diff is the verification gate; any consolidation (env-var dedup, ingress factoring, image bumps beyond pinning) is deferred to follow-up PRs.
- **D-04-CUTOVER-04: Rollback = `git revert` the my-kluster PR.** Reverting re-introduces the 10 unit Apps; ArgoCD restores them; PVCs survive because `prune: true` does not delete claims still referenced. ADR-6 pre-snapshot is the forensic anchor for diff diagnosis.

### values.yaml shape + file layout

- **D-04-VALUES-01: Flat top-level shape + shared `defaults` block.** `values.yaml` has top-level keys matching `dependencies[].alias` in `Chart.yaml` (one per service), plus a top-level `defaults:` block carrying `env.TZ`, `env.PUID`, `env.PGID`, ingress class, cert-manager annotations, and oauth2-proxy annotations (where applicable — Jellyfin opts out). Merge mechanism is planner/researcher's call (app-template's `defaultPodOptions`/`defaultContainerOptions` if it covers our needs, otherwise a `_helpers.tpl` indirection). The shared defaults render byte-equivalent because all 10 current Apps carry identical TZ/PUID/PGID and identical cert-manager issuer.
- **D-04-VALUES-02: `files/` at top level.** `charts/arr-stack/files/arrconf.yml` and `charts/arr-stack/files/configarr.yml` mount into respective CronJob Pods as ConfigMap via app-template's `persistence.<name>.type: configMap`. Mirrors `my-kluster/charts/{arrconf,configarr}/files/` layout.
- **D-04-VALUES-03: `values.yaml` IS production.** The future `arr-stack-app.yaml` in `my-kluster` has no `helm.values:` block (per spec §9.2). `values.yaml` ships production-ready defaults; `examples/values-prod.yaml` ships as a copy/symlink for documentation / fork ergonomics. Single-tenant homelab justifies bleeding prod config into defaults.
- **D-04-VALUES-04: Full strict `values.schema.json`.** Generated via `helm schema-gen` plugin, hand-tightened (enums for sync policies, regex for image tags, required fields). CI blocks if `values.yaml` doesn't parse. Heavy upfront cost is justified by REQ-helm-validation and by Phase 5+ reconciler additions where the schema will need to evolve.
- **D-04-DOCS-01: Full doc refresh for README.md and CLAUDE.md.** Phase 4 is the natural audit point — both files get rewritten end-to-end against post-Phase-4 reality, not just patched. Anticipatory sections in CLAUDE.md ("Structure cible", "Bootstrap (état actuel)") become ground truth or archive sections.

### CronJob templates (arrconf + configarr)

- **D-04-CRON-01: bjw-s `app-template` alias for both CronJobs (zero custom templates).** Both `arrconf` and `configarr` ship as app-template dependency aliases in `Chart.yaml` with `controllers.main.type: CronJob` + `cronJobConfig.{schedule, concurrencyPolicy: Forbid}` + `persistence.config.type: configMap` referencing the `files/` content. Uniform Renovate tracking (app-template version bumps already followed). `charts/arr-stack/templates/` ends up nearly empty (maybe an `_helpers.tpl` for `defaults` merge).
- **D-04-CRON-02: `concurrencyPolicy: Forbid` MANDATORY; `checksum/config` Pod-rotation OPTIONAL.** `Forbid` prevents overlapping arrconf runs racing on API. `checksum/config` annotation is dropped — the next scheduled tick reads the new ConfigMap mount; max delay = `schedule` (currently `0 */4 * * *` for arrconf), which still satisfies REQ-pr-to-cluster-latency (< 1h is the merge-to-cluster latency, not config-edit-to-applied latency).
- **D-04-CRON-03: arrconf args at cutover: `apply --apps sonarr,radarr,prowlarr`.** All three Phase 3 reconcilers go live in the same PR as the umbrella. D-03-04 `host_config.enable: false` opt-in default is the safety net against accidental auth lockout. Researcher must verify Phase 3 fixtures haven't drifted from current cluster state via the ADR-6 pre-snapshot.
- **D-04-CRON-04: Two Secrets stay separate (`arrconf-env`, `configarr-env`).** Each CronJob aliases the respective Secret via `envFrom: secretRef`. No `my-kluster/secrets/` churn at cutover. Consolidation into a single `arr-stack-env` deferred to Phase 8 ESO when the source-of-secrets layer is being rewritten anyway.

### Pinning `:latest` (qbittorrent, flaresolverr, cleanuparr)

- **D-04-PIN-01: Pin to currently-running cluster digest.** Operator (you) captures running image identifiers per the pre-plan checkpoint task; planner pins those exact tags. Renders byte-equivalent at cutover (satisfies D-04-CUTOVER-03). Renovate immediately tracks via the `# renovate: image=` annotation and proposes upgrades in subsequent PRs.
- **D-04-PIN-02: Pre-plan operator checkpoint task.** Plan-phase emits a Wave 1 task instructing operator to run:
  ```
  for app in qbittorrent flaresolverr cleanuparr; do
    kubectl -n selfhost get pod -l app.kubernetes.io/name=$app \
      -o jsonpath='{.spec.containers[0].image}{"\n"}{.status.containerStatuses[0].imageID}{"\n---\n"}'
  done > .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/current-image-tags.txt
  ```
  The output (image + digest pair) gets committed in the phase dir; researcher resolves each digest to the corresponding semver tag via the registry (linuxserver.io / GHCR) and writes the pinned values into `values.yaml`.
- **D-04-PIN-03: Per-image `# renovate: image=<repo>` annotation.** Every `repository:` line in `values.yaml` carries the annotation on the line above. `renovate.json` `customManagers` regex matches `# renovate: image=$repo\n.*repository: $repo\n.*tag: $tag`. CLAUDE.md convention is the authoritative shape (it explicitly warns: "Sans ça, Renovate ne suit pas").
- **D-04-PIN-04: First Renovate-detected bump after cutover is the SC#2 E2E test target.** Don't pre-stage a stale pin. If no bump arrives within 1 week post-cutover, fall back to manually downgrading one image (e.g. cleanuparr) by one patch to force Renovate to fire. Validates the customManagers regex + auto-merge pipeline end-to-end without pre-coordination.

### Claude's Discretion

- **app-template version pin**: planner/researcher picks the exact `bjw-s/app-template` version (current my-kluster usage is `4.6.2`; check for a newer stable release at planning time, but no breaking-change adoption in Phase 4).
- **`defaults:` merge mechanism**: app-template's native `defaultPodOptions` / `defaultContainerOptions` if it covers env + ingress annotations, otherwise a `_helpers.tpl` indirection. Researcher reads app-template docs and picks; both are acceptable.
- **arrconf release tag at cutover**: `v0.2.1` (patch, no code change) vs `v0.3.0` (minor, new deployment shape). Planner's call; preference is to NOT cut a new tag if `tools/arrconf/` source is unchanged (cutover changes packaging, not the script).
- **Umbrella chart's own version**: `Chart.yaml: version: 0.1.0` for the first release of `charts/arr-stack/`. Pinned by my-kluster's `targetRevision: v0.1.0` git tag.
- **CronJob schedule unification**: both arrconf and configarr currently `0 */4 * * *`. Keep as-is in Phase 4 (no change). If a user wants more frequent arrconf later, change in Phase 5+ once the umbrella is proven.
- **`values.schema.json` authoring tool**: `helm schema-gen` plugin (one-shot) then commit + hand-tighten, vs hand-writing from scratch. Researcher recommends; both pass CI gate.
- **Renovate `packageRules`**: automerge minor/patch on all customManagers / helmv3 / helm-values per spec.md, majors gated for manual review. Standard pattern.
- **PR sequencing within arr-stack repo**: how many internal PRs (one big or split into "chart skeleton" → "9 app values" → "CronJobs" → "schema + CI" → "renovate + docs")? Planner decides per wave structure.
- **Cutover sequencing details**: order of operations (suspend → snapshot → merge → diff → sync → verify → re-enable automated). Planner expands into discrete tasks.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Spec and roadmap (authoritative)
- `spec.md` §7 Phase 4 (lines 547-564) — Livrables + Critères de fin verbatim.
- `spec.md` §9.1 (lines 660-675) — État pré-migration: liste des 9 ArgoCD Applications + chart configarr.
- `spec.md` §9.2 (lines 677-718) — État cible post-Phase 4: exemple `arr-stack-app.yaml` à reproduire.
- `spec.md` §9.3 (lines 724-727) — Compatibilité ascendante: fenêtre de coexistence + recyclarr déjà désactivé.
- `spec.md` §10 Q2 (line 734) — Question ouverte sur multi-alias syntax (tranche ADR-2 Option A; valider en Phase 4).
- `spec.md` §11 ADR-2 (lines 766-779) — Helm dependencies sur app-template (alias par service).
- `spec.md` §11 ADR-4 — Repo séparé arr-stack pull par une seule ArgoCD App.
- `spec.md` §11 ADR-6 — Snapshot baseline avant toute écriture (s'applique au cutover Phase 4).
- `.planning/ROADMAP.md` lignes 152-165 (Phase 4 entry) — Goal + 6 Success Criteria.
- `.planning/PROJECT.md` — Core value, Constraints, Out of scope, ADRs, Open Questions Q2.
- `.planning/REQUIREMENTS.md` — REQ-config-as-code, REQ-umbrella-deployment, REQ-renovate-image-tracking, REQ-helm-validation, REQ-pr-to-cluster-latency, REQ-readme-onboarding (all targeted at Phase 4).

### Conventions and guardrails (project-local)
- `CLAUDE.md` "Structure cible" — anticipatory layout for `charts/arr-stack/`; Phase 4 makes it ground truth.
- `CLAUDE.md` "Conventions Helm — umbrella chart" — Renovate annotation format, `dependencies:` alias pattern, `values.schema.json` posture.
- `CLAUDE.md` "Ce que tu NE dois PAS faire" — `:latest` interdit, annotation Renovate obligatoire, pas de déploiement direct depuis ce repo.
- `CLAUDE.md` "Intégration avec my-kluster" — single ArgoCD App pull pattern + secrets bootstrap path.

### Current production state (to absorb / replace)
- `/home/moi/projets/perso/my-kluster/charts/arrconf/` (Chart.yaml + values.yaml + templates/{cronjob,configmap}.yaml + files/arrconf.yml) — absorb into umbrella per D-04-CRON-01 (port logic to app-template alias).
- `/home/moi/projets/perso/my-kluster/charts/configarr/` (Chart.yaml + values.yaml + templates/{cronjob,configmap,pvc}.yaml + files/config.yml) — same absorption; note the `cache` PVC dependency for configarr's TRaSH-Guides repo.
- `/home/moi/projets/perso/my-kluster/argocd/argocd-apps/arrconf-app.yaml` — 10th Application to delete at cutover.
- `/home/moi/projets/perso/my-kluster/argocd/argocd-apps/{sonarr,radarr,prowlarr,cleanuparr,configarr,qbittorrent,seerr,flaresolverr,jellyfin}-app.yaml` — 9 unit Applications to delete at cutover (source of byte-equivalence target).
- `/home/moi/projets/perso/my-kluster/secrets/{arrconf,configarr}-secret.yaml` — gitignored manual bootstrap Secrets that remain post-cutover.

### Repo state (current)
- `renovate.json` — currently only `extends: ["config:recommended"]`; Phase 4 adds `customManagers` block.
- `.github/workflows/{arrconf-image.yml,tests.yml}` — existing CI; Phase 4 adds `chart-lint.yml`.
- `tools/arrconf/` — Phase 3-complete reconciler covering sonarr/radarr/prowlarr (Phase 4 doesn't touch source; only packages it via umbrella alias).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`my-kluster/charts/arrconf/templates/cronjob.yaml`** — production-validated CronJob spec (concurrencyPolicy Forbid, runAsNonRoot 1000:1000, args structure `--config /app/config/arrconf.yml apply --apps <list>`, envFrom secretRef). Source for translating into app-template `controllers.main` shape per D-04-CRON-01.
- **`my-kluster/charts/configarr/templates/cronjob.yaml`** — production-validated CronJob for configarr including the `cache` PVC for TRaSH repo + `tty: true` quirk. Same translation target.
- **`my-kluster/charts/configarr/templates/pvc.yaml`** — `<release>-cache` PVC (storageClass `microk8s-hostpath`, 1Gi). Must be expressed via app-template's `persistence.<name>.type: persistentVolumeClaim`.
- **`my-kluster/charts/{arrconf,configarr}/templates/_helpers.tpl`** — standard bjw-s naming helpers; Phase 4's umbrella may need its own `_helpers.tpl` for the `defaults` merge per D-04-VALUES-01.
- **9 unit `argocd-apps/*.yaml`** — each contains the per-app `helm.values:` block that becomes the per-alias `values.yaml` section in the umbrella. Verbatim port (with the shared `defaults:` factored out) gives byte-equivalence per D-04-CUTOVER-03.

### Established Patterns

- **bjw-s/app-template 4.6.2** is the universal sub-chart (8 of 9 unit Apps already use it). app-template v4.x supports `controllers.<name>.type: CronJob` + `cronJobConfig` natively — D-04-CRON-01 assumes this; researcher verifies coverage of `concurrencyPolicy`, `successfulJobsHistoryLimit`, `securityContext`, `envFrom`, `persistence.type: configMap`.
- **Renovate `# renovate: image=` annotation** (CLAUDE.md) — Phase 4 introduces the FIRST use of this convention in the repo; sets the pattern for Phase 5+ image additions.
- **GitOps via ArgoCD** — automated `selfHeal: true` + `prune: true` is the standard setup across `my-kluster`. The cutover temporarily disables it (D-04-CUTOVER-02) — pattern recorded for future migrations.
- **Two-PR rollout discipline (Phase 2 D-28)** — used for arrconf dry-run/apply flip. Phase 4 cutover is conceptually similar (suspend → diff → sync → re-enable) but compressed into one PR with operator-driven sync gating.

### Integration Points

- **`my-kluster/secrets/{arrconf,configarr}-secret.yaml`** — manual `kubectl apply` Secrets, gitignored. The umbrella references them by name via `envFrom`. Unchanged at cutover.
- **`/opt/media-stack/torrents` hostPath** — shared by qBittorrent + Sonarr + Radarr. Each alias re-declares it via `persistence.torrents.type: hostPath`. Byte-equivalent port from unit Apps.
- **`media-nas-pvc` (NFS)** — shared by Sonarr + Radarr + Jellyfin. Each alias references via `persistence.media.existingClaim: media-nas-pvc`. PVC itself lives outside the umbrella (cluster-level resource).
- **`selfhost-project` ArgoCD project + `selfhost` namespace** — the umbrella's single `Application` lives in `argocd` namespace targeting `selfhost`. Reused unchanged from current 10 unit Apps.
- **`*.tgu.ovh` ingress hostnames** — 8 entries (sonarr/radarr/prowlarr/cleanuparr/configarr/qbittorrent/seerr/flaresolverr/jellyfin). Each per-alias `ingress.main` block carries its hostname + TLS secret. Byte-equivalent.

</code_context>

<specifics>
## Specific Ideas

- **Doc refresh extends beyond CONTEXT scope.** User explicitly added: "il faut aussi mettre à jour la documentation dans le README.md et CLAUDE.md pour refléter tous les changements" → captured as D-04-DOCS-01 (full refresh, not targeted edits).
- **Byte-equivalence is verifiable.** The verification gate is `diff` between rendered umbrella manifests and `argocd app manifests` exports of the 10 unit Apps. Planner should include this diff as an explicit verification task.
- **arrconf is in the umbrella.** Despite arrconf being "our code", it gets the same app-template alias treatment as the 3rd-party apps (D-04-CRON-01). Uniformity > special-casing.
- **CLAUDE.md "Structure cible" is anticipatory and partially wrong.** It lists `templates/arrconf-cronjob.yaml` / `templates/arrconf-configmap.yaml` etc. — D-04-CRON-01 contradicts this. D-04-DOCS-01 rewrites the section to match the app-template-alias reality.

</specifics>

<deferred>
## Deferred Ideas

- **Consolidating duplicate env vars / ingress annotation refactors** beyond the `defaults:` block — defer to a v0.3.0 cleanup PR (D-04-CUTOVER-03 byte-equivalent rule).
- **Single `arr-stack-env` Secret** consolidating arrconf + configarr env — defer to Phase 8 ESO rewrite (Secret-source layer changes anyway).
- **`release.yml` / release-please automation** (Q4 open question) — manual tags remain per Phase 1 D-01.
- **Pre-stage stale pin to force Renovate to fire immediately** — fallback only if no natural bump arrives within 1 week post-cutover (D-04-PIN-04).
- **Image version bumps beyond pinning currently-running** — defer to Renovate's first auto-PRs post-cutover (validates SC #2).
- **`helm test` hooks** — not in Phase 4 scope; could come with `chart-lint.yml` evolution in a follow-up.

</deferred>

---

*Phase: 4-Umbrella chart + migration des 9 apps*
*Context gathered: 2026-05-12*
