# Phase 2: Validation cluster - Research

**Researched:** 2026-05-08
**Domain:** Kubernetes deployment of arrconf as a CronJob in `selfhost` namespace via a mini Helm chart in the sister repo `my-kluster`, drift detection demonstration, two-PR dry-run→apply progression
**Confidence:** HIGH on patterns (mirror configarr — known good, in-cluster), MEDIUM on operational specifics (manual job interaction, exact diff filter logic), LOW on nothing critical

## Summary

Phase 2 lands the first cluster deployment of arrconf. There is no new Python code — Phase 1 already shipped a complete CLI binary, Docker image, and round-trip-proven Sonarr download_clients reconciler. Phase 2's whole job is **packaging that binary as a CronJob in K8s** and **proving the drift loop works end-to-end on a real Sonarr instance** without breaking anything.

The strategy is conservative and entirely cribbed from the existing `my-kluster/charts/configarr/` chart — same Helm patterns, same CronJob shape, same secret injection via `envFrom: secretRef`, same ArgoCD App template. The only meaningfully new mechanism is the **two-PR dry-run protocol** (D-28): PR1 deploys with `arrconfDryRun: true` and proves zero writes via snapshot diff; PR2 flips the flag to `false` and lets arrconf actually apply. This is GitOps-friendly (every state change tracked in Git, atomic revert via `git revert`), and decouples "did the chart deploy correctly" from "did arrconf write what we expected" — two distinct failure modes that should not be debugged together.

**Primary recommendation:** Treat Phase 2 as a *cross-repo packaging exercise* rather than a code phase. Plans should fan out into clearly-tagged tasks per repo (`[arr-stack]`, `[my-kluster]`), front-load the GHCR public-toggle (Pitfall 7 — without it, no pod can pull the image) and the snapshot before PR1 (ADR-6 discipline — D-30), and treat the drift demo as a documented runbook rather than an ad-hoc exploration. Validation here is operational (snapshot-diff = 0 in dry-run, log JSON shows expected actions, Sonarr UI shows the managed download_client after PR2), not unit-test based.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Open questions résolues:**
- **D-23 (Q3 schedule arrconf):** `0 */4 * * *` (toutes les 4 h, sync avec configarr). `concurrencyPolicy: Forbid`, `startingDeadlineSeconds: 600` (tolérance 10 min de retard), `successfulJobsHistoryLimit: 1`, `failedJobsHistoryLimit: 2`.

**Emplacement & shape:**
- **D-24 (Mini-chart location):** Le chart Phase 2 vit dans **`my-kluster/charts/arrconf/`**, pas dans ce repo. Mirror exact de `my-kluster/charts/configarr/`. PRs Phase 2-3 atterrissent côté my-kluster. Phase 4 supprimera ce chart + l'ArgoCD App dédiée quand l'umbrella prendra le relais — exactement la même migration que pour configarr.
- **D-25 (`arrconf.yml` shape Phase 2):** Minimal Sonarr-only. Un seul bloc `sonarr.main` avec 1 download_client (qBittorrent existant), pas de stubs vides ni de sections commentées pour Phase 3+. Le JSON Schema généré en Phase 1 valide déjà cette shape.
- **D-26 (ArgoCD App):** `my-kluster/argocd/argocd-apps/arrconf-app.yaml` créée — `kind: Application`, `metadata.name: arrconf`, `spec.destination.namespace: selfhost`, `spec.project: selfhost-project`, `spec.source.repoURL: https://github.com/tom333/my-kluster.git`, `spec.source.path: charts/arrconf`, `targetRevision: HEAD`, `syncOptions: [CreateNamespace=false, ServerSideApply=true]`, `automated: { selfHeal: true, prune: true }`. Mirror exact de `configarr-app.yaml`.
- **D-27 (ConfigMap mount):** `arrconf.yml` est dans `charts/arrconf/files/arrconf.yml` côté my-kluster, injecté en ConfigMap via `.Files.Get` dans `templates/configmap.yaml`, monté en lecture seule à `/app/config/arrconf.yml` dans le container. Annotation `checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}` sur le pod template pour rolling reload.

**Bascule dry-run → apply:**
- **D-28 (Protocole 2-PR):** Helm value `arrconfDryRun: bool` dans `values.yaml`, mappée au CronJob template via `env: [{ name: ARRCONF_DRY_RUN, value: {{ .Values.arrconfDryRun | quote }} }]`.
  - **PR1**: ajoute le chart, ArgoCD App, ConfigMap, `arrconfDryRun: true`. Après merge → ArgoCD sync → attendre 1 cycle (4 h) → vérifier les logs JSON ("would ADD/UPDATE/DELETE …, dry_run=true") → re-snapshot post-run dans `snapshots/post-phase2-pr1-<date>/` → `diff -r` avec baseline = identique.
  - **PR2**: flippe `arrconfDryRun: false`. Le commit message documente l'observation des logs PR1 et la date du re-snapshot. Revert facile (`git revert`) en cas de pépin.

**Bootstrap secret:**
- **D-29 (Scope `arrconf-env`):** Secret manuel `my-kluster/secrets/arrconf-secret.yaml` ne contient **que** `SONARR_API_KEY` en Phase 2 (principe de moindre privilège, REQ-bootstrap-exception). Bump du secret par PR à chaque phase suivante.

**Re-snapshot discipline (ADR-6):**
- **D-30 (Snapshots Phase 2):** Trois snapshots minimum committés:
  1. `before-phase-2-<date>/` — re-snapshot avant tout déploiement
  2. `post-phase2-pr1-<date>/` — capture post-1er-run en dry-run, pour `diff = 0` vs `before-phase-2`
  3. `post-phase2-pr2-<date>/` — capture après bascule en apply
  4. `drift-test-<date>/` (optionnel mais recommandé)

### Claude's Discretion

- **Cluster service URL**: `http://sonarr.selfhost.svc.cluster.local:8989` — vérifier dans `my-kluster/argocd/argocd-apps/sonarr-app.yaml` (validé `[VERIFIED: my-kluster/argocd/argocd-apps/sonarr-app.yaml]` — port `8989` confirmé, service nom `sonarr` standard).
- **Pod securityContext**: `runAsNonRoot: true`, `runAsUser: 1000`, `runAsGroup: 1000`; `readOnlyRootFilesystem: false`.
- **Resources requests/limits**: copie configarr (50m/128Mi req, 500m/512Mi limit).
- **TZ env var**: `Europe/Paris`.
- **`imagePullPolicy: IfNotPresent`** + `image.tag` pinned (Phase 1 release tag).
- **Helm values.schema.json**: optionnel Phase 2.
- **Validation programmatique post-run**: petit script Bash `tools/snapshot/diff.sh` (recommandation: léger wrapper sur `diff -r` filtré jq, voir Recommendations §). Si planner juge trop, le faire à la main.
- **Drift detection demo**: modifier un download_client via `kubectl exec` curl ou via UI Sonarr (web port-forward). Documenter dans le README arrconf.
- **Documentation**: `my-kluster/charts/arrconf/README.md` court documentant la procédure 2-PR et le runbook de drift detection.

### Deferred Ideas (OUT OF SCOPE)

- `tools/snapshot/diff.sh` script structuré — peut rester du `diff -r` brut. Pour Phase 3 ou tools utilities.
- NetworkPolicy `selfhost` restrictive pour arrconf — Phase 8 (durcissement secrets/réseau).
- Notification Sonarr quand arrconf rétablit un drift — Phase 3+ ou nice-to-have.
- Helm `values.schema.json` pour le mini-chart Phase 2 — déféré à Phase 4 où l'umbrella en aura besoin.
- `arrconf` SDK metrics endpoint (Prometheus) — hors-scope MVP.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-drift-detection | Modification UI hors-Git détectée et corrigée; logs JSON visibles | Pattern 4 (drift demo runbook) + Pitfall 5 (`concurrencyPolicy: Forbid` + manual job) + Pattern 5 (log JSON parsing) |
| REQ-bootstrap-exception | 1ère API key via UI; env-only; `envFrom: secretRef` | Pattern 2 (envFrom secretRef mirror configarr) + Code Example 3 (CronJob env injection) |
| REQ-secret-management | Secrets restent dans `my-kluster/secrets/`; aucun secret committé dans arr-stack | Pattern 2 (manual `kubectl apply` pre-sync) + Pitfall 6 (pod CrashLoop si secret absent au sync) |

## Project Constraints (from CLAUDE.md)

The arr-stack `CLAUDE.md` (project-specific) imposes the following hard constraints relevant to Phase 2 — the planner MUST verify these are honored in every plan:

| Directive | Source | Phase 2 Application |
|-----------|--------|---------------------|
| Workflow snapshot CRITIQUE | CLAUDE.md "Workflow snapshot" | Re-snapshot AVANT chaque phase scope nouveau (D-30 #1 obligatoire avant PR1) |
| Aucune lecture de fichier de secrets — uniquement env | CLAUDE.md "Variables d'environnement" | `arrconf-env` injection via `envFrom: secretRef` only; D-29 enforces this |
| Bootstrap secrets restent dans my-kluster/secrets/ | CLAUDE.md "Intégration avec my-kluster" | `arrconf-secret.yaml` lives in `my-kluster/secrets/`, NEVER in arr-stack |
| Toujours via my-kluster + ArgoCD; jamais `helm install` direct | CLAUDE.md "Ce que tu NE dois PAS faire" | Plans MUST NOT include `helm install` or `kubectl apply -f` of the chart; only `kubectl apply -f arrconf-secret.yaml` is allowed (manual bootstrap) |
| Pas d'image `:latest` en production | CLAUDE.md / spec C9 | `values.yaml` MUST pin `image.tag: v0.1.0` (or whatever Phase 1 ships) |
| Pas de secrets committés | CLAUDE.md "Ce que tu NE dois PAS faire" | `arrconf-secret.yaml` NOT to be committed to arr-stack ; CI fixture audit already covers Python code, but Phase 2 chart values MUST never reference an inline secret |
| Snapshot avant test risqué + committed in Git | CLAUDE.md "Discipline" | All 3-4 snapshot directories committed (NOT in `.gitignore`) |
| Annotation `# renovate: image=...` au-dessus de chaque image | CLAUDE.md "Conventions Helm" | Phase 2 mini-chart `values.yaml` MUST include annotation above `arrconf.image` (forward-compat — Renovate runs on this repo too) |
| Ne pas changer le scope arrconf↔configarr | CLAUDE.md frontière | `arrconf.yml` Phase 2 must NOT contain `quality_profiles`, `custom_formats`, `quality_definitions`, `media_naming` sections (already enforced by `ScopeViolationError` D-12 and pydantic schema) |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Helm chart (mini-chart `arrconf`) | my-kluster repo (Helm + ArgoCD) | — | Mirrors existing `charts/configarr/` pattern; ArgoCD pulls from the my-kluster GitOps repo; arr-stack repo only owns the image binary |
| ArgoCD Application manifest | my-kluster repo (GitOps) | — | All ArgoCD Applications live in `my-kluster/argocd/argocd-apps/`; arr-stack never declares its own Application |
| Bootstrap secret (`arrconf-env`) | my-kluster repo `secrets/` (manual `kubectl apply`) | — | Secret lifecycle is manual until ESO migration (Phase 8); ArgoCD Application's syncPolicy explicitly does NOT manage this secret |
| Container image build & publish | arr-stack repo (CI) | — | GitHub Actions `arrconf-image.yml` already shipped Phase 1; pushes to `ghcr.io/tom333/arr-stack-arrconf` on tag `v*` |
| Reconciliation logic (apply, dump, diff) | Container runtime (CronJob pod) | — | Already shipped Phase 1; runs in-cluster, reads ConfigMap + env, writes to Sonarr API via Service DNS |
| Configuration declaration (`arrconf.yml`) | my-kluster `charts/arrconf/files/arrconf.yml` | — | Phase 2 ConfigMap source (will move to arr-stack `charts/arr-stack/files/arrconf.yml` in Phase 4 umbrella migration) |
| Drift detection orchestration | CronJob schedule + Sonarr API | Manual `kubectl create job --from=cronjob/arrconf` | Schedule-driven (4h) + on-demand for the demo |
| Snapshot artifacts | arr-stack repo (`snapshots/`) | — | Lossless JSON dumps committed to Git; ADR-6 discipline; this repo owns the assurance trail |
| Validation (snapshot diff = 0 in dry-run) | arr-stack repo (`tools/snapshot/`) — manual or scripted | — | The diff is a property of two Git-committed snapshots in arr-stack; validation runs locally, not in cluster |

**Key insight:** Phase 2 spans BOTH repos. The dependency graph is one-way: arr-stack publishes the image (a binary contract — `ghcr.io/tom333/arr-stack-arrconf:v0.1.0`); my-kluster consumes it via Helm. There is no circular dependency. The image tag is the only cross-repo coupling — Phase 2 PR1 my-kluster pins `v0.1.0`, which must exist on GHCR before the PR merges, which means the **arr-stack tag MUST be created before the my-kluster PR is opened**. Plans must order this correctly.

## Standard Stack

### Core (Phase 2 — operational, no new code dependencies)

| Library / Tool | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| Helm | 3 | Templating mini-chart | Already used by `charts/configarr/` and every other my-kluster chart |
| ArgoCD | (cluster-installed v2.x) | Pull + sync | App-of-Apps pattern already in place; `automated: { selfHeal: true, prune: true }` is the cluster-wide convention |
| Kubernetes CronJob (`batch/v1`) | apiVersion `batch/v1` | Scheduled run of arrconf | Matches configarr; the only batch primitive that supports schedule + concurrencyPolicy + jobHistoryLimit |
| GHCR (public package) | — | Image distribution | Phase 1 already publishes; cluster pulls anonymously (C2, ADR-3) |
| `arrconf` v0.1.0 (binary) | from Phase 1 | Reconciler | Phase 1 deliverable — no Phase 2 code changes [VERIFIED: tools/arrconf/ exists, all 6 ROADMAP success criteria PASS in 01-VERIFICATION.md] |

**No new Python dependencies, no new chart dependencies (no `bjw-s/app-template` here — that arrives Phase 4).** The mini-chart is hand-rolled, exactly like `charts/configarr/` is hand-rolled.

### Supporting

| Library / Tool | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| `kubectl` 1.28+ | already installed | Manual secret apply, port-forward, `create job --from=cronjob`, log inspection | Phase 2 runbook actions only |
| `jq` 1.7+ | already installed (used by snapshot.sh) | JSON log parsing, snapshot diff filter | Drift demo + post-run validation |
| `curl` 8.x | already installed (used by snapshot.sh) | Manual drift induction (`curl -X PUT` to Sonarr API) for the demo | Drift demo only |
| `diff` (POSIX `diffutils`) | already installed | Snapshot directory comparison | Success criterion #3 verification (snapshot-diff = 0) |

### Image version verification

[VERIFIED: arr-stack/.github/workflows/arrconf-image.yml] The workflow triggers on `tags: ['v*']` and produces these tags via `docker/metadata-action@v5`:
- `type=sha,prefix=sha-,format=short` → `:sha-<short>`
- `type=ref,event=branch,prefix=branch-` → `:branch-<name>` on push
- `type=semver,pattern={{version}}` → `:v0.1.0` (or `:0.1.0`?) on tag push
- `type=raw,value=latest,enable=${{ startsWith(github.ref, 'refs/tags/v') }}` → `:latest` on tag

⚠️ **Verification needed in plan:** The `type=semver,pattern={{version}}` template normalizes the leading `v` — i.e., a Git tag of `v0.1.0` produces an image tag of `0.1.0`, not `v0.1.0`. Plans should pin `image.tag: 0.1.0` in `values.yaml`, OR change the pattern to `{{raw}}` to preserve the leading `v`. **This is the kind of off-by-one that breaks `ImagePullBackOff` silently.** [CITED: docker/metadata-action README — `{{version}}` strips the `v` prefix; `{{raw}}` preserves it]

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Mini-chart in `my-kluster/charts/arrconf/` | Full umbrella now (`charts/arr-stack/` in arr-stack) | D-24 explicitly defers umbrella to Phase 4; mini-chart matches the configarr pattern and is throwaway — net cost is one chart deletion in Phase 4, which is trivial |
| `automated: { prune: true }` from day 1 | `prune: false`, manual prune in Phase 2 only | D-26 mirrors configarr (which uses `prune: true`); risk surfaced as Pitfall 8 below — Phase 4 cleanup must be ordered carefully |
| Manual `kubectl apply -f cronjob.yaml` | Helm chart | Violates GitOps (CLAUDE.md), no template + no values, no Renovate trail. Ruled out. |
| Single PR with `arrconfDryRun: false` from start | D-28 two-PR protocol | Single PR conflates "did the chart deploy" with "did arrconf write what was planned"; debugging two failure modes simultaneously is error-prone. Two-PR is cheap and clean. |
| Helm `pre-install` hook for the secret | Manual `kubectl apply` of `arrconf-secret.yaml` | Helm hooks couple secret to chart lifecycle; ArgoCD doesn't run hooks reliably. CLAUDE.md mandates manual bootstrap. |

## Architecture Patterns

### System Architecture Diagram

```
                           ┌──────────────────────────────────┐
                           │  arr-stack (this repo)            │
                           │                                   │
                           │  Tag v0.1.0 (manual)              │
                           │      │                            │
                           │      ▼                            │
                           │  GH Actions: arrconf-image.yml    │
                           │  → push image                     │
                           └────────────┬──────────────────────┘
                                        │
                                        ▼
                              ghcr.io/tom333/arr-stack-arrconf:0.1.0
                              (PUBLIC — Pitfall 7)
                                        │
                                        │ (pulled at pod startup)
                                        ▼
┌──────────────────────────────────────────────────────────────────┐
│  my-kluster (sister repo)                                        │
│                                                                   │
│  PR1: charts/arrconf/ + arrconf-app.yaml + arrconfDryRun: true   │
│      │                                                            │
│      ├─→ argocd/argocd-apps/arrconf-app.yaml                     │
│      │      (Application metadata.name: arrconf)                 │
│      │                                                            │
│      ▼                                                            │
│  ArgoCD (in-cluster)                                             │
│      │                                                            │
│      │  pull manifests from charts/arrconf/                      │
│      │  helm template → apply                                    │
│      ▼                                                            │
│  Cluster resources in namespace `selfhost`:                      │
│      • ConfigMap arrconf (data.arrconf.yml from .Files.Get)      │
│      • CronJob arrconf (schedule "0 */4 * * *")                  │
│      ──────────── (manual: kubectl apply -f arrconf-secret.yaml) │
│      • Secret arrconf-env (only SONARR_API_KEY in Phase 2)       │
│                                                                   │
│  PR2: arrconfDryRun: false                                       │
│      ArgoCD self-heals, ConfigMap unchanged but env changes      │
└────────────────────────────────────────────┬─────────────────────┘
                                              │
                                              │ (every 4h, or on-demand)
                                              ▼
                             ┌────────────────────────────┐
                             │ Job (controlled by CronJob) │
                             │  Pod arrconf-<hash>         │
                             │   • envFrom: secretRef      │
                             │     name: arrconf-env       │
                             │   • mounts ConfigMap @       │
                             │     /app/config/arrconf.yml │
                             │   • runs `arrconf apply`    │
                             │     (dry-run or apply       │
                             │     based on env)           │
                             └────────┬───────────────────┘
                                      │
                                      │ HTTP (X-Api-Key: $SONARR_API_KEY)
                                      ▼
                             sonarr.selfhost.svc.cluster.local:8989
                                      │
                                      │ structured JSON logs
                                      ▼
                             stdout → kubectl logs
                             → drift events visible
```

### Pattern 1: Mirror configarr chart, substitute names + paths

**What:** Copy `my-kluster/charts/configarr/` into `my-kluster/charts/arrconf/`, then make exactly these substitutions. No invention.

**When to use:** Phase 2 mini-chart construction.

**Substitution map** [VERIFIED: read all 4 files in `my-kluster/charts/configarr/templates/` + `Chart.yaml` + `values.yaml`]:

| File | Substitution |
|------|-------------|
| `Chart.yaml` | `name: configarr` → `arrconf`; `description` rewritten; `appVersion: "1.16.0"` → `"0.1.0"` (matches Phase 1 image tag); `version: 0.1.0` (chart version, independent of app); leave `apiVersion: v2`, `type: application` unchanged |
| `templates/_helpers.tpl` | All 4 helpers prefix `configarr.` → `arrconf.` (5 helpers: `configarr.name`, `configarr.fullname`, `configarr.chart`, `configarr.labels`, `configarr.selectorLabels`) |
| `templates/cronjob.yaml` | Container `name: configarr` → `arrconf`; image repo + tag from values; mountPath `/app/config/config.yml` → `/app/config/arrconf.yml`; subPath `config.yml` → `arrconf.yml`; **REMOVE** the `cache` volume + volumeMount (configarr-specific PVC for TRaSH-Guides Git cache; arrconf has no equivalent need); ADD `env: [{name: ARRCONF_DRY_RUN, value: "{{ .Values.arrconfDryRun }}"}]` (D-28); keep `envFrom: secretRef: name: {{ .Values.apiKeysSecret }}`; keep `concurrencyPolicy: Forbid` + history limits |
| `templates/configmap.yaml` | Data key `config.yml` → `arrconf.yml`; `.Files.Get "files/config.yml"` → `.Files.Get "files/arrconf.yml"` |
| `templates/pvc.yaml` | **DELETE** entirely — arrconf has no cache PVC need |
| `values.yaml` | `image.repository: ghcr.io/raydak-labs/configarr` → `ghcr.io/tom333/arr-stack-arrconf`; `tag: "1.16.0"` → `"0.1.0"` (verify Phase 1 emits `0.1.0` not `v0.1.0` per metadata-action `{{version}}`); `apiKeysSecret: configarr-env` → `arrconf-env`; **REMOVE** the `cache` block (no PVC); ADD `arrconfDryRun: true` (Phase 2 PR1 default); ADD `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` annotation above the image block (CLAUDE.md convention) |

**ArgoCD App** [VERIFIED: `my-kluster/argocd/argocd-apps/configarr-app.yaml` is 24 lines; mirror exactly]:
- `metadata.name: arrconf`
- `spec.source.path: charts/arrconf`
- All other fields identical to configarr-app.yaml

**Secret** [VERIFIED: `my-kluster/secrets/configarr-secret.yaml` is 9 lines]:
- `metadata.name: arrconf-env`, `metadata.namespace: selfhost`, `type: Opaque`
- `stringData.SONARR_API_KEY: "<from Sonarr UI>"` — Phase 2 only key (D-29)

### Pattern 2: ConfigMap-injected `arrconf.yml` via `.Files.Get`

**What:** Helm pattern where chart-time files are baked into a ConfigMap at template-render time.

**Source** [VERIFIED: `my-kluster/charts/configarr/templates/configmap.yaml`]:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "arrconf.fullname" . }}
  labels:
    {{- include "arrconf.labels" . | nindent 4 }}
data:
  arrconf.yml: |-
{{ .Files.Get "files/arrconf.yml" | indent 4 }}
```

**Initial `files/arrconf.yml` content** [Source: copy `examples/baseline-sonarr.yml` from arr-stack, with the `$schema` modeline path reset]:

The Phase 1 `examples/baseline-sonarr.yml` modeline points to `../schemas/arrconf-schema.json` (relative to arr-stack `examples/`). For my-kluster's `charts/arrconf/files/arrconf.yml`, the relative path doesn't resolve (no schema in my-kluster). Two options:

**Option A (recommended):** Drop the modeline in my-kluster (no IDE editing of cluster configs anyway).
**Option B:** Use a URL-based modeline pointing to GitHub raw: `# yaml-language-server: $schema=https://raw.githubusercontent.com/tom333/arr-stack/v0.1.0/schemas/arrconf-schema.json` — but this implies the tag exists at edit time, which is the case only after Phase 1 release.

**When to use:** Phase 2 ConfigMap.

### Pattern 3: Two-PR dry-run protocol (D-28)

**What:** Toggle `arrconfDryRun: true` then `arrconfDryRun: false` in two separate PRs in my-kluster, with ArgoCD self-healing the env change between Job runs.

**Sequence** (the planner will materialize as tasks):

```
T+0    [arr-stack]   Re-snapshot baseline → snapshots/before-phase-2-<date>/  (D-30 #1)
                     Commit; verify diff vs baseline-2026-05-07/ ≈ 0 changes  (or note divergence)

T+1    [arr-stack]   git tag v0.1.0 && git push --tags
                     → triggers arrconf-image.yml → publishes ghcr.io/tom333/arr-stack-arrconf:0.1.0
                     → MANUAL: visit GHCR settings, toggle package visibility to Public  (Pitfall 7)
                     → verify: docker pull ghcr.io/tom333/arr-stack-arrconf:0.1.0 succeeds anonymously

T+2    [my-kluster]  PR1 opens:
                     • secrets/arrconf-secret.yaml (with real SONARR_API_KEY) — NOT committed; applied manually
                     • charts/arrconf/{Chart.yaml,values.yaml,templates/*,files/arrconf.yml}
                     • argocd/argocd-apps/arrconf-app.yaml
                     • values.yaml: arrconfDryRun: true
                     • image.tag: 0.1.0  (or v0.1.0 — verify metadata-action behavior)
                     PR description includes:
                     • Pre-merge checklist: kubectl apply -f secrets/arrconf-secret.yaml
                     • GHCR public toggle confirmed
                     • Reference to before-phase-2 snapshot

T+3    [operator]    BEFORE merge: kubectl apply -f my-kluster/secrets/arrconf-secret.yaml
                     (Pitfall 6: pod CrashLoop if secret not present at sync time)

T+4    [my-kluster]  Merge PR1
                     ArgoCD: detects new App → creates ConfigMap + CronJob in selfhost
                     CronJob waits for next schedule slot OR operator forces:
                     kubectl create job --from=cronjob/arrconf arrconf-pr1-smoke -n selfhost

T+5    [operator]    Verify Job pod logs JSON:
                     • event: "no_drift" OR "would ADD/UPDATE/…, dry_run=true"
                     • exit code 0
                     • NO POST/PUT/DELETE to Sonarr (verify by Sonarr logs OR by re-snapshot)

T+6    [arr-stack]   Re-snapshot → snapshots/post-phase2-pr1-<date>/  (D-30 #2)
                     diff -r snapshots/before-phase-2-<date>/ snapshots/post-phase2-pr1-<date>/
                     EXPECTED: 0 differences (filtered for read-only fields)
                     Commit snapshot; SUCCESS CRITERION #3 SATISFIED.

T+7    [my-kluster]  PR2 opens: values.yaml arrconfDryRun: true → false
                     PR description references the PR1 log capture + post-phase2-pr1 snapshot
                     Merge after review.

T+8    [my-kluster]  Merge PR2 → ArgoCD self-heals env change
                     Next CronJob run (or forced via kubectl create job) writes to Sonarr

T+9    [arr-stack]   Re-snapshot → snapshots/post-phase2-pr2-<date>/  (D-30 #3)
                     EXPECTED: download_client now has tags=[<arrconf-managed-id>]
                     Commit snapshot; SUCCESS CRITERION #4 SATISFIED.

T+10   [operator]    Drift demo:
                     1. Modify a download_client.category via Sonarr UI (or kubectl exec curl)
                     2. kubectl create job --from=cronjob/arrconf arrconf-drift-demo -n selfhost
                     3. Capture logs JSON: expect "event=update_planned action=UPDATE diff={category: ...}"
                     4. Re-fetch via Sonarr UI: original value restored
                     5. (Optional) Re-snapshot → snapshots/drift-test-<date>/  (D-30 #4)
                     SUCCESS CRITERION #5 SATISFIED.
```

**When to use:** Always — this is the Phase 2 spine.

### Pattern 4: Drift detection demo (REQ-drift-detection runbook)

**What:** Inject a UI-side drift, force the next CronJob run, verify arrconf rolls it back, capture logs.

**Inject drift** (two viable approaches; recommend curl for reproducibility):

```bash
# Port-forward Sonarr from outside the cluster for the demo
kubectl -n selfhost port-forward svc/sonarr 8989:8989 &

# Capture current download_client (id=1, qBittorrent)
curl -s http://localhost:8989/api/v3/downloadclient/1 -H "X-Api-Key: $SONARR_API_KEY" | jq '.' > /tmp/dc-before.json

# Mutate one safe field — `priority: 1` → `priority: 5` (no functional impact)
jq '.priority = 5' /tmp/dc-before.json > /tmp/dc-drifted.json

curl -X PUT http://localhost:8989/api/v3/downloadclient/1 \
  -H "X-Api-Key: $SONARR_API_KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/dc-drifted.json

# Confirm drift landed
curl -s http://localhost:8989/api/v3/downloadclient/1 -H "X-Api-Key: $SONARR_API_KEY" | jq '.priority'
# → 5
```

**Force CronJob run** [VERIFIED: kubectl docs]:

```bash
kubectl create job --from=cronjob/arrconf arrconf-drift-demo -n selfhost
kubectl wait --for=condition=complete job/arrconf-drift-demo -n selfhost --timeout=120s
kubectl logs job/arrconf-drift-demo -n selfhost
```

**Expected log output** (structlog JSON, one line per event — based on Phase 1 reconciler behavior):

```json
{"event": "managed_tag_present", "tag_id": 1, "level": "info", "logger": "arrconf.reconcilers.sonarr"}
{"event": "fetched_current", "resource": "download_clients", "count": 1}
{"event": "diff_computed", "action": "UPDATE", "name": "qBittorrent", "diff": {"priority": {"current": 5, "desired": 1}}}
{"event": "applying", "action": "UPDATE", "name": "qBittorrent", "dry_run": false}
{"event": "applied", "action": "UPDATE", "name": "qBittorrent", "id": 1}
{"event": "reconcile_complete", "app": "sonarr", "actions_taken": [{"action": "UPDATE", "name": "qBittorrent"}]}
```

**Verify rollback:**

```bash
curl -s http://localhost:8989/api/v3/downloadclient/1 -H "X-Api-Key: $SONARR_API_KEY" | jq '.priority'
# → 1   (restored to YAML-declared value)
```

**When to use:** Once after PR2 merge to satisfy success criterion #5 + REQ-drift-detection.

⚠️ **Pitfall 5 interaction:** `concurrencyPolicy: Forbid` does NOT block manually-created Jobs from `--from=cronjob/...`. The Forbid policy is enforced by the CronJob controller against its own scheduled creations, not against arbitrary Jobs that copy the template. So `kubectl create job --from=cronjob/arrconf foo` will run even if a scheduled Job is currently active — but in practice arrconf jobs complete in seconds, so this is theoretical. [CITED: kubernetes/kubernetes#107827 — concurrencyPolicy applies only to scheduler-created Jobs]

### Pattern 5: Snapshot diff for "zero writes in dry-run" verification

**What:** Compare two snapshot directories field-by-field, ignoring known volatile fields.

**Minimum viable approach** (recommended for Phase 2; D-30 success criterion #3):

```bash
# Crude but sufficient — both snapshot dirs have jq --sort-keys'd JSON,
# so diff -r is deterministic.
diff -r snapshots/before-phase-2-2026-05-08/sonarr/ snapshots/post-phase2-pr1-<date>/sonarr/
# Expected: no output (zero diff)

# If output is non-empty: inspect each differing file. Acceptable noise:
# • timestamps (none in *arr GET responses for these endpoints)
# • Sonarr's own internal counters (none affecting downloadclient.json / tag.json)
# Anything else = arrconf wrote during dry-run = CRITICAL BUG (regression of Phase 1's dry-run guarantee)
```

**Why crude is enough:** Phase 1 already proved `apply --dry-run` does zero writes via respx-mocked `test_round_trip_dump_apply_dry_run_is_noop` (52 tests pass, coverage 99% on `differ.py` + `reconcilers/sonarr.py`). The Phase 2 snapshot diff is a *cluster-level corroboration* of that guarantee, not the primary proof. If Phase 1 mocks are right, the snapshot diff will be empty without any filtering.

**Optional enhancement (deferred to Phase 3 per D-30 deferred):** `tools/snapshot/diff.sh` wrapper that filters known-volatile fields:

```bash
#!/usr/bin/env bash
# Compare two snapshot dirs, filter Sonarr's known volatile fields (id auto-renumbering, etc.)
# Phase 2 plan: SKIP — diff -r is sufficient.
# Phase 3 plan: implement if drift demo creates noise (e.g., id renumbering after delete).
```

**When to use:** Post-PR1 run (zero writes proof), post-drift-demo (rollback proof).

### Anti-Patterns to Avoid

- **Putting the chart in `arr-stack/charts/`** — D-24 explicitly puts it in `my-kluster/charts/`. Phase 4 will create the umbrella in arr-stack. Mixing now = double migration cost.
- **Using the `bjw-s/app-template` chart for Phase 2** — that's Phase 4 territory. The mini-chart is hand-rolled (mirror configarr) deliberately, to keep Phase 2 small and disposable.
- **Single PR for both deploy and dry-run flip** — D-28 mandates two PRs. Combining them defeats the validation purpose.
- **Committing `arrconf-secret.yaml`** to either repo — secrets only in `my-kluster/secrets/`, manually applied. CLAUDE.md hard rule.
- **Skipping the GHCR public-toggle step** — Pitfall 7. Without it, ArgoCD sync of PR1 results in `ImagePullBackOff` and the entire phase stalls.
- **Forgetting to apply the secret BEFORE PR1 merge** — Pitfall 6. The pod CrashLoops on `SONARR_API_KEY` missing, PR1 looks broken, debugging burns hours.
- **Hardcoding `image.tag: latest`** — CLAUDE.md hard rule + ADR-3. Pin the exact `0.1.0` Phase 1 produces.
- **Treating drift detection as "the schedule did something"** — REQ-drift-detection requires the **logs** to show drift events. The runbook MUST capture log output as evidence; a mute success is not success.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| K8s manifest templating | `envsubst`, sed-based generators, raw kubectl manifests | Helm 3 + the configarr template skeleton | Helm is already the cluster's templating tool; `_helpers.tpl` patterns mature, Renovate integrates |
| GitOps deployment trigger | CI that runs `helm install` | ArgoCD App watching the my-kluster repo | CLAUDE.md hard rule: deployment ALWAYS via ArgoCD |
| Image build/push | Manual `docker build && docker push` | The existing `arrconf-image.yml` GitHub Action | Already shipped Phase 1, signed by tag, reproducible |
| Image pull secrets | `imagePullSecrets` + dockerconfigjson | GHCR Public visibility (one-time UI toggle) | ADR-3 + spec C2; cluster pulls anonymously |
| Job scheduling | Wrapper Deployment + sleep loop | K8s native CronJob (`batch/v1`) | Native support for schedule + concurrency + history limits + jobTemplate |
| ConfigMap from external file | Custom init container that fetches | `.Files.Get` in Helm template | Bakes file contents into ConfigMap at template-render time, idempotent |
| Per-resource diff for "did dry-run write?" | Custom binary that GETs every API | The existing `tools/snapshot/snapshot.sh` + `diff -r` | Already runs in Phase 0+, sufficient for Phase 2 (Phase 1 already proves zero-write at unit level) |
| Cron format validation | Build-time linter | Trust K8s API server validation OR `crontab -e` mental check | `0 */4 * * *` is canonical and well-known |
| Secret rotation | Sidecar that polls Vault | Manual `kubectl apply` (Phase 2-7) → ESO/Akeyless (Phase 8) | Phased adoption per spec; Phase 2 is bootstrap-only scope |

**Key insight:** Phase 2 has *no* code to write — all logic is in the Phase 1 image. The phase is 100% YAML and operational discipline. Resist the urge to write helper scripts, custom validation tools, or new Python; reuse existing patterns and let the operational runbook be the deliverable.

## Runtime State Inventory

This is a deploy phase that introduces new in-cluster state and consumes existing in-cluster state. Inventory:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — Sonarr's SQLite DB is the only stateful store, and arrconf reads/writes it via API only via the patterns Phase 1 already exercises against mocks; no new collections, keys, or user_ids | none |
| Live service config | (a) Sonarr download_clients table — Phase 2 PR2 will modify entry id=1 to add the `arrconf-managed` tag; (b) Sonarr tags table — Phase 2 PR2 will add `arrconf-managed` tag if absent. Both are recoverable via `arrconf dump` post-write or via `before-phase-2` snapshot | rollback path = `git revert PR2 && git revert PR1` + `kubectl delete cronjob/arrconf cm/arrconf -n selfhost` (ArgoCD prune handles auto if `prune: true`) ; manually restore via `curl -X PUT` with `before-phase-2/sonarr/downloadclient.json` if needed |
| OS-registered state | None — no Windows Task Scheduler, no systemd unit, no launchd, no pm2 saved processes. The CronJob lives entirely in cluster | none |
| Secrets/env vars | (a) `arrconf-env` Secret in `selfhost` namespace — NEW, manually applied from `my-kluster/secrets/arrconf-secret.yaml`; (b) `SONARR_API_KEY` value reused from `configarr-secret.yaml` (same Sonarr instance, same key); (c) GHCR pulls anonymous so no `imagePullSecrets` to manage | document in PR1 description: pre-merge `kubectl apply -f my-kluster/secrets/arrconf-secret.yaml`; verify env injection via `kubectl exec ... -- printenv \| grep SONARR_API_KEY` (will show value masked unless decoded) |
| Build artifacts / installed packages | (a) `ghcr.io/tom333/arr-stack-arrconf:0.1.0` image — NEW, built from arr-stack tag `v0.1.0`; (b) ArgoCD will re-pull on first sync of PR1; (c) The Phase 1 `tools/arrconf/` Python package and uv venv are not affected | verify GHCR public toggle (Pitfall 7) before merging PR1 |

**Nothing else found.** Phase 2 introduces zero stale-state risk if rolled back: the only persisted side-effect is the addition of `arrconf-managed` tag and tag membership in Sonarr's DB, which is reversible via API.

## Common Pitfalls

### Pitfall 1: GHCR package defaults to private (already known — Pitfall 7 from Phase 1)

**What goes wrong:** First push to `main` or first `v*` tag publishes the image, but GHCR sets visibility to **private** by default. ArgoCD sync of PR1 succeeds (manifests apply), but the resulting Pod is stuck in `ImagePullBackOff` because the cluster has no `imagePullSecrets` configured (deliberate per ADR-3 — anonymous public pull is the design).

**Why it happens:** GitHub does not (as of 2026-04 per Phase 1 RESEARCH) expose package visibility via the `gh` CLI or REST API. It's a one-time UI step, often forgotten when the first push happens.

**How to avoid:**
1. Plan task order: tag `v0.1.0` → CI completes → operator visits https://github.com/users/tom333/packages/container/arr-stack-arrconf/settings → Danger Zone → Change visibility → Public → confirm.
2. Verification gate: `docker pull ghcr.io/tom333/arr-stack-arrconf:0.1.0` from a logged-out Docker daemon.
3. ONLY THEN open PR1 in my-kluster.

**Warning signs:** `kubectl describe pod -n selfhost <arrconf-pod>` shows `Failed to pull image ... unauthorized` or `denied`.

### Pitfall 2: `metadata-action` `{{version}}` strips the leading `v`

**What goes wrong:** Author tags `v0.1.0`, expects image `:v0.1.0`, but `docker/metadata-action@v5` with `pattern={{version}}` produces `:0.1.0` (no `v`). Plan pins `image.tag: v0.1.0` in `values.yaml` → `ImagePullBackOff` because `:v0.1.0` does not exist on GHCR.

**Why it happens:** `{{version}}` is the semver-normalized form per `docker/metadata-action` docs; `{{raw}}` preserves the literal Git ref.

**How to avoid:**
1. After Phase 1 release, verify on GHCR which tag was actually published (`docker manifest inspect ghcr.io/tom333/arr-stack-arrconf:0.1.0` vs `:v0.1.0`).
2. Pin `image.tag` in `values.yaml` to whatever exists.
3. (Optional, if `v` prefix preferred) modify `arrconf-image.yml` to `pattern={{raw}}` — but this changes the Phase 1 contract, so prefer adapting Phase 2 to whatever Phase 1 publishes.

**Warning signs:** Same as Pitfall 1 — `ImagePullBackOff`. Differentiate by checking GHCR's actual tag list.

### Pitfall 3: Pod CrashLoop because `arrconf-secret.yaml` not applied before ArgoCD sync

**What goes wrong:** Operator merges PR1 in my-kluster forgetting the manual `kubectl apply -f secrets/arrconf-secret.yaml` step. ArgoCD syncs the chart → CronJob created → next scheduled or forced Job → Pod tries to read `SONARR_API_KEY` from the missing Secret → either Pod refuses to start (`CreateContainerConfigError` if `envFrom: secretRef` is required) or Pod starts but fast-fails inside arrconf with `event: missing_api_key` (Phase 1 implements this — exit code 2) or 401 from Sonarr.

**Why it happens:** Manual apply is easy to forget; CLAUDE.md mandates the manual lifecycle until Phase 8 ESO.

**How to avoid:**
1. PR1 description includes a pre-merge checklist with the literal command.
2. Reviewer enforces the checkbox before merge.
3. (Belt and suspenders) ArgoCD App `syncOptions: [SkipDryRunOnMissingResource=true]` — actually no, that masks the problem. Better: rely on the runbook and the visible Pod failure.
4. After merge, before forcing a Job: `kubectl get secret arrconf-env -n selfhost` should return the secret.

**Warning signs:** `kubectl describe pod ... -n selfhost` shows `Error: secret "arrconf-env" not found` (CreateContainerConfigError).

### Pitfall 4: `concurrencyPolicy: Forbid` only applies to scheduled runs, not manual Jobs

**What goes wrong:** During the drift demo, operator does `kubectl create job --from=cronjob/arrconf foo` while a scheduled CronJob run is already executing. Both Jobs run concurrently, both call `arrconf apply`, both diff against the same Sonarr state, race conditions possible (e.g., both try to create the `arrconf-managed` tag).

**Why it happens:** [CITED: kubernetes/kubernetes#107827, GH issue thread] `concurrencyPolicy` is enforced by the CronJob controller against Jobs *it* creates from the schedule. A Job created via `kubectl create job --from=cronjob/...` is owned by the user, not the CronJob, so it bypasses the policy.

**How to avoid:**
1. Operator visually checks `kubectl get jobs -n selfhost` for active jobs before forcing a manual one.
2. Document this in the my-kluster `charts/arrconf/README.md` runbook.
3. In practice, arrconf runs complete in <30s, so the race window is small. Phase 1's `_ensure_managed_tag` is idempotent (get-or-create), so even a tag-race produces no harm.

**Warning signs:** Two Jobs visible in `kubectl get jobs` simultaneously; conflicting log lines if you tail both.

### Pitfall 5: `checksum/config` annotation on CronJob `jobTemplate` is largely ornamental

**What goes wrong:** Author copies the configarr `checksum/config` annotation expecting it to "force a restart on ConfigMap change." But CronJob's `jobTemplate.spec.template` is the template for *each new Job's pod*; CronJobs don't manage long-lived pods, so there's nothing to "restart." Each scheduled Job already creates a fresh Pod that reads the latest ConfigMap mount. The annotation is not harmful but doesn't do what the author thinks.

**Why it happens:** Confusion with Deployment behavior (where `checksum/config` triggers a rolling update on pod template hash change).

**How to avoid:**
1. Keep the annotation — it's harmless and matches the configarr pattern (preserves muscle memory).
2. Don't expect it to "speed up" propagation of ConfigMap changes — the next scheduled Job will pick them up regardless.
3. For immediate propagation after a values change: `kubectl create job --from=cronjob/arrconf arrconf-manual-<date>`.

**Warning signs:** None — this is a "documented harmlessness," not a bug.

[CITED: helm/helm#10346 + Helm docs "Chart Tips and Tricks" — checksum annotation is for Deployments; CronJob jobTemplate already creates fresh pods]

### Pitfall 6: ArgoCD `automated.prune: true` will delete the chart wholesale during Phase 4 migration

**What goes wrong:** Phase 4 will replace `arrconf-app.yaml` (mini-chart) with the umbrella `arr-stack-app.yaml` (deps app-template). If both Apps have `automated.prune: true` and the migration PR is poorly ordered, ArgoCD prunes the CronJob/ConfigMap created by the mini-chart before the umbrella has created its replacements → arrconf is briefly gone from the cluster → no drift detection during the gap.

**Why it happens:** ArgoCD prune is fast and aggressive when the App's source path changes or the App is deleted.

**How to avoid (Phase 4 — flagging now):**
1. Phase 4 plan should include explicit ordering: deploy umbrella first → verify umbrella's arrconf CronJob is healthy → THEN delete mini-chart App.
2. Document in `my-kluster/charts/arrconf/README.md`: "This chart will be replaced by the arr-stack umbrella in Phase 4. See arr-stack Phase 4 runbook for migration sequence."
3. Phase 2 doesn't need to act on this; just flag for Phase 4.

**Warning signs:** During Phase 4, `kubectl get cronjob -n selfhost` shows arrconf missing for >5 minutes during sync.

### Pitfall 7: `0 */4 * * *` is interpreted in the controller's TZ, not user-local

**What goes wrong:** Cron schedule `0 */4 * * *` runs at 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 in **the kube-controller-manager's timezone**, which is typically UTC on most distros. Operator expects "every 4 hours starting at midnight Paris time" → actual runs are 2 hours offset in winter, 1 hour offset in summer (DST).

**Why it happens:** K8s CronJob historically was UTC-only; v1.27+ introduced a `timeZone` field on CronJob spec for explicit TZ.

**How to avoid:**
1. For Phase 2 (4-hour cadence, no human consumer waiting at a specific clock time), don't bother with `timeZone` — operational tolerance is wide.
2. The TZ environment variable inside the container (`Europe/Paris` per discretion) only affects log timestamps and arrconf's own time-of-day output, NOT the schedule.
3. (Optional, future) add `spec.timeZone: "Europe/Paris"` to the CronJob spec if the schedule becomes user-visible. K8s 1.27+. [VERIFIED: kubernetes.io/docs CronJob §Time Zone]

**Warning signs:** `kubectl get cronjob arrconf -n selfhost` shows `LAST SCHEDULE` timestamp 2h off from wall-clock.

### Pitfall 8: ArgoCD self-heal will revert manual `kubectl edit cronjob/arrconf` changes within 3 minutes

**What goes wrong:** During debugging, operator does `kubectl edit cronjob/arrconf -n selfhost` to (e.g.) bump resources or add an env. ArgoCD's `selfHeal: true` polls every ~3 min and reverts. Operator concludes "K8s ate my change" and gets confused.

**Why it happens:** D-26 mandates `automated: { selfHeal: true, prune: true }` mirroring configarr's pattern.

**How to avoid:**
1. All changes go via PR in my-kluster, never `kubectl edit`. (Standard GitOps discipline; CLAUDE.md.)
2. For debugging only: `argocd app set arrconf --sync-policy none` temporarily; remember to restore.
3. Document in runbook.

**Warning signs:** Manual edit visible in `kubectl get cronjob -o yaml` for 1-2 minutes, then disappears; `kubectl get application arrconf -n argocd -o jsonpath='{.status.history}'` shows a self-heal sync.

### Pitfall 9: Phase 1 image doesn't auto-emit `:0.1.0` tag without a Git tag

**What goes wrong:** Phase 1 already shipped (commit `ba1c285` per git log) but the `v0.1.0` Git tag may not yet exist. `arrconf-image.yml` only triggers `:vX.Y.Z` when `tags: ['v*']` is pushed. Until the tag is pushed, only `:sha-<short>` and `:branch-main` exist on GHCR — no semver tag for the chart to pin.

**Why it happens:** Phase 1's HUMAN-UAT explicitly notes this as deferred; Phase 2 PR1 in my-kluster cannot pin `0.1.0` until tag exists.

**How to avoid:**
1. First task of Phase 2 plan (in arr-stack): `git tag v0.1.0 && git push origin v0.1.0` (or via GitHub Releases UI for prettier audit trail).
2. Verify CI ran `arrconf-image.yml` and pushed `:0.1.0` (and `:latest`).
3. ONLY THEN proceed to PR1 in my-kluster.

**Verification command:**
```bash
gh api -H "Accept: application/vnd.github+json" /users/tom333/packages/container/arr-stack-arrconf/versions \
  | jq -r '.[].metadata.container.tags[]' | sort -u
# Expected output includes: 0.1.0, latest, sha-<short>, branch-main
```

**Warning signs:** `docker pull ghcr.io/tom333/arr-stack-arrconf:0.1.0` returns `manifest unknown`.

### Pitfall 10: structlog JSON output requires non-TTY for activation

**What goes wrong:** Phase 1 D-07 sets up structlog with auto-detection: pretty-printed colored output on TTY, JSON on non-TTY. In a Job pod, stdout is connected to the kubelet container runtime, which in most CRI implementations is NOT a TTY. So JSON should activate. But some debugging modes (`kubectl run -it` interactive sessions) DO get a TTY — where the dev expects JSON and gets pretty output.

**Why it happens:** TTY detection via `sys.stdout.isatty()` differs between batch and interactive contexts.

**How to avoid:**
1. CronJob Pods run non-interactively → JSON output reliably. The drift demo uses `kubectl logs` (post-hoc, not interactive) → JSON also reliable.
2. For interactive debugging: `kubectl run -it --rm --image=ghcr.io/tom333/arr-stack-arrconf:0.1.0 ...` will produce pretty output. For machine-parsable output add `--env=ARRCONF_FORCE_JSON=true` if Phase 1 implements that override (NOT verified — would need to check `arrconf/logging.py`).
3. Phase 2 success criterion #5 ("logs JSON visibles") is satisfied by the standard `kubectl logs` from a Job (non-interactive).

**Warning signs:** Drift demo shows pretty-printed output instead of JSON when running interactively. Mitigation: trust the actual CronJob run, not the interactive test.

## Code Examples

### Example 1: `my-kluster/charts/arrconf/templates/cronjob.yaml` (full file)

This is the literal target after substitution from `configarr/templates/cronjob.yaml`:

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

**Diff vs configarr/cronjob.yaml** (for reviewer):
- Container `name: configarr` → `arrconf`
- ADD `args: ["apply", "--config", "/app/config/arrconf.yml", "--apps", "sonarr"]` (configarr uses ENTRYPOINT default; arrconf needs explicit subcommand and config path because Phase 1 Dockerfile CMD is `["apply", "--help"]`)
- ADD `env: ARRCONF_DRY_RUN` block
- mountPath `/app/config/config.yml` → `/app/config/arrconf.yml`; subPath `config.yml` → `arrconf.yml`
- REMOVE `cache` volume + volumeMount + PVC reference
- ADD explicit `securityContext` (defense-in-depth; configarr image already runs as 1000 but K8s-side reinforcement helps `restricted` PSP/PSS)
- ADD `tty: true` removal — configarr has `tty: true` for pretty colored output; arrconf in CronJob context wants JSON (non-TTY) → drop the line

[Source: derived from `my-kluster/charts/configarr/templates/cronjob.yaml` which I read in full]

### Example 2: `my-kluster/charts/arrconf/values.yaml` (full file)

```yaml
# arrconf — config-as-code reconciler for Sonarr (Phase 2: Sonarr download_clients only)
# Mini-chart Phase 2; supplanted by arr-stack umbrella in Phase 4.

image:
  # renovate: image=ghcr.io/tom333/arr-stack-arrconf
  repository: ghcr.io/tom333/arr-stack-arrconf
  tag: "0.1.0"   # ⚠️ verify Phase 1 publishes "0.1.0" (no v) — see Pitfall 2
  pullPolicy: IfNotPresent

# Schedule synced with configarr (4h) for ops cadence consistency.
schedule: "0 */4 * * *"
timezone: "Europe/Paris"
startingDeadlineSeconds: 600   # 10-min tolerance for kubelet/scheduler delays

# Two-PR dry-run protocol (D-28):
#   PR1: arrconfDryRun: true   → observe logs, prove zero writes, snapshot diff = 0
#   PR2: arrconfDryRun: false  → enables apply
arrconfDryRun: true

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 50m
    memory: 128Mi

# Manual bootstrap secret (D-29):
#   kubectl apply -f my-kluster/secrets/arrconf-secret.yaml  BEFORE merging PR1
# Phase 2 contains only SONARR_API_KEY; bumped per phase (3+).
apiKeysSecret: arrconf-env

successfulJobsHistoryLimit: 1
failedJobsHistoryLimit: 2
```

[Source: derived from `my-kluster/charts/configarr/values.yaml` which I read in full]

### Example 3: Image tag verification (post Phase 1 release)

```bash
# After git tag v0.1.0 && git push origin v0.1.0
# Wait ~5 min for arrconf-image.yml workflow.

# Verify tag exists on GHCR
gh api -H "Accept: application/vnd.github+json" \
  /users/tom333/packages/container/arr-stack-arrconf/versions \
  | jq -r '.[] | .metadata.container.tags[]' | sort -u
# Expected: 0.1.0, latest, sha-<short>, branch-main
# (NOT v0.1.0 unless metadata-action pattern was changed to {{raw}})

# Verify anonymous pull (Pitfall 1 — toggle public)
docker logout ghcr.io   # (or run from a fresh shell)
docker pull ghcr.io/tom333/arr-stack-arrconf:0.1.0
# Expected: success. If "denied", visit GHCR settings → Public.
```

[VERIFIED: arrconf-image.yml metadata-action template at line 33 of the workflow file]

### Example 4: Forcing a CronJob run on demand (drift demo + smoke test)

```bash
# Pattern: kubectl create job --from=cronjob/<name> <new-job-name> -n <namespace>
kubectl create job --from=cronjob/arrconf arrconf-smoke-$(date +%s) -n selfhost

# Wait for completion (defaults to ActiveDeadlineSeconds; arrconf is fast)
kubectl wait --for=condition=complete job/arrconf-smoke-<...> -n selfhost --timeout=120s

# Inspect logs
kubectl logs job/arrconf-smoke-<...> -n selfhost

# Cleanup (optional — failedJobsHistoryLimit=2 keeps recent fails)
kubectl delete job arrconf-smoke-<...> -n selfhost
```

[CITED: kubectl create job --help; kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `apiVersion: batch/v1beta1` for CronJob | `apiVersion: batch/v1` | K8s 1.21 (1.25 hard removal) | Use `batch/v1` exclusively; configarr already does |
| Cron schedule UTC-only | `spec.timeZone: "Region/City"` field | K8s 1.27 GA (`CronJobTimeZone` feature gate) | Optional for Phase 2; consider if scheduling becomes user-visible. [CITED: kubernetes.io/docs/concepts/workloads/controllers/cron-jobs#time-zones] |
| `imagePullPolicy: Always` for safety | `imagePullPolicy: IfNotPresent` with pinned semver tags | Industry shift toward immutable tags | Phase 2 pins `0.1.0`, IfNotPresent is correct |
| ArgoCD `syncPolicy.automated` without `selfHeal` | `selfHeal: true` + `prune: true` standard | ArgoCD 1.5+ | Phase 2 follows configarr precedent |
| Helm 2 (`helm install` with Tiller) | Helm 3 (Tiller-less) | Helm 3 GA 2019-11 | Already using Helm 3 cluster-wide |

**Deprecated/outdated:**
- `batch/v1beta1` CronJob — removed 1.25; do NOT use.
- Helm 2 + Tiller — never used here, irrelevant.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `docker/metadata-action@v5` `pattern={{version}}` strips leading `v` from Git tag `v0.1.0` to produce image tag `0.1.0` | Standard Stack > Image version verification; Pitfall 2 | MEDIUM — wrong tag pin = `ImagePullBackOff` = Phase 2 stalls. Verifiable in 30s by reading the action's docs OR by inspecting GHCR after first tag push. Plan should include a verification task. [CITED: docker/metadata-action README] |
| A2 | `concurrencyPolicy: Forbid` does NOT apply to manually-created Jobs (`kubectl create job --from=cronjob/...`) | Pitfall 4 | LOW — even if wrong, arrconf is idempotent so race is benign. [CITED: kubernetes/kubernetes#107827 thread; secondary verification recommended] |
| A3 | `checksum/config` annotation on CronJob `jobTemplate` is harmless but ineffective for triggering ConfigMap reload | Pitfall 5 | LOW — cosmetic; doesn't break anything. [CITED: helm/helm#10346] |
| A4 | Phase 1 image will accept the CronJob `args: ["apply", "--config", "/app/config/arrconf.yml", "--apps", "sonarr"]` literally | Code Example 1 | LOW — Phase 1 ENTRYPOINT is `["arrconf"]` (verified in Dockerfile) and the CLI accepts these flags (verified in 01-VERIFICATION.md). Plan should include a smoke-run task in PR1 to confirm. |
| A5 | `arrconf-managed` tag write during PR2 is recoverable via `arrconf dump` or via baseline snapshot | Runtime State Inventory | LOW — Phase 1 managed-tag tests prove idempotent get-or-create; reverting both PRs restores the cluster but the tag remains in Sonarr (latent harmless artifact). |
| A6 | Sonarr's `priority` field on download_client is safe to mutate for the drift demo (no functional impact on torrent routing) | Pattern 4 | LOW — `priority` is used for tie-breaking among multiple download_clients of the same protocol; with 1 client in Phase 2, it has no effect. Alternative safe field: `enable: true ↔ false` (but disable might block torrents during the demo window — DON'T use). |
| A7 | The Phase 1 binary's `apply --dry-run` does zero writes to Sonarr (already proven at unit level via 52 respx-mocked tests) | Pattern 5 | LOW — VERY high confidence; D-12 + 99% coverage on `differ.py` + `reconcilers/sonarr.py`. The cluster-level snapshot diff is corroboration, not the primary proof. |
| A8 | `kubectl create job --from=cronjob/arrconf` uses the latest CronJob template (i.e., picks up post-PR2 env values) | Pattern 3 (T+8 step) | LOW — `--from` reads the live CronJob spec at command time. [CITED: kubectl docs] |
| A9 | The `selfhost-project` AppProject permits the new `arrconf` Application | Architecture Diagram | LOW — verified `selfhost-project.yaml` allows `clusterResourceWhitelist: '*'` and `destinations: [{namespace: selfhost}]`; no per-App allowlist [VERIFIED: my-kluster/argocd/argocd-appprojects/selfhost-project.yaml] |
| A10 | The CronJob's container image (`arrconf` Phase 1 build) defaults to TTY-disabled stdout, producing JSON logs in cluster | Pitfall 10 | LOW — kubelet container stdout is not a TTY; arrconf's structlog auto-detect activates JSON. Confirmed indirectly by Phase 1 D-07. |

**Caveat:** Assumptions A1 (image tag format) and A4 (CLI args literal) MUST be confirmed during Phase 2 execution before PR1 merges. The plan should include explicit verification tasks for each.

## Open Questions

1. **Should the arrconf CLI `--apps` flag default to all apps in the YAML, or be required?**
   - What we know: Phase 1 D-13 says "default: toutes celles déclarées dans le YAML" but Code Example 1 hardcodes `--apps sonarr` in the CronJob args.
   - What's unclear: If `--apps` is omitted, does arrconf process all apps in `arrconf.yml`? Phase 2 has only Sonarr in the YAML so the answer doesn't matter operationally, but Phase 3 does.
   - Recommendation: Phase 2 plan keeps `--apps sonarr` explicit (defensive); Phase 3 plan revisits.

2. **Does `arrconf-image.yml` produce `:v0.1.0` or `:0.1.0`?**
   - What we know: metadata-action `{{version}}` strips the `v`; but we haven't actually pushed a tag yet so the empirical answer is unknown.
   - What's unclear: Empirical reality.
   - Recommendation: First task of Phase 2 plan (in arr-stack) is `git tag v0.1.0 && git push --tags`, then a verification task `gh api .../packages/container/arr-stack-arrconf/versions | jq` to read the actual tag list. Plan branches: if `0.1.0` exists, use it. If `v0.1.0`, use it. Don't pre-commit to one in the chart values.

3. **Is the SONARR_API_KEY value in `configarr-secret.yaml` reusable for arrconf?**
   - What we know: Both arrconf and configarr target the same Sonarr instance, so the same API key works. configarr-secret.yaml has `SONARR_API_KEY: "7996acf930d34ab88a992f2981097081"` [VERIFIED, but note: this is committed plaintext — see Concerns below].
   - What's unclear: Should arrconf get its own API key (per-service principle of least privilege) or share?
   - Recommendation: Phase 2 share the existing key (operational simplicity); Phase 8 ESO migration is the right time to per-service-segregate. The key has full Sonarr admin scope anyway.

4. **Can `arrconfDryRun` be set via `--dry-run` CLI flag instead of env?**
   - What we know: Phase 1 supports both `ARRCONF_DRY_RUN=true` env AND `--dry-run` CLI flag.
   - What's unclear: Which is more idiomatic for Helm-templated CronJob args?
   - Recommendation: Env is more flexible (can be overridden per-Job via `kubectl create job --env ARRCONF_DRY_RUN=false`), and matches the configarr pattern of env injection. D-28 mandates env. Stick with env.

5. **Should the chart include a Helm `values.schema.json`?**
   - What we know: D-30 deferred says "optionnel Phase 2; only 4-5 valeurs à valider, pas critique. Phase 4 (umbrella) en aura besoin."
   - What's unclear: Is `helm lint` enough for Phase 2?
   - Recommendation: Skip values.schema.json for Phase 2 (matches configarr which has none). Helm's built-in YAML parser will catch type errors anyway.

6. **What happens if PR1 sits in `arrconfDryRun: true` for >1 cron cycle (multiple Jobs run with no writes)?**
   - What we know: Each scheduled Job is independent; multiple dry-run cycles produce identical logs.
   - What's unclear: Any cluster-side state accumulation? Job history limit is 1 success + 2 failures → only the most recent Job is kept.
   - Recommendation: Operationally fine to leave PR1 deployed for hours/days before PR2. Plan task ordering: PR1 → ≥1 Job run observed → snapshot → PR2 (no fixed delay).

7. **Concerns: `configarr-secret.yaml` is committed plaintext in `my-kluster/`.**
   - What we know: [VERIFIED] `my-kluster/secrets/configarr-secret.yaml` contains `RADARR_API_KEY: "9a39fe509a6f489183be7538cdfff498"` and `SONARR_API_KEY: "7996acf930d34ab88a992f2981097081"` — committed in plaintext.
   - What's unclear: Is the my-kluster repo public or private?
   - Recommendation: NOT a Phase 2 problem (predates this work and is acknowledged in `my-kluster/CLAUDE.md` "Choses à faire / améliorations connues" — TODO SOPS encryption). Plan note: `arrconf-secret.yaml` should follow the SAME convention as `configarr-secret.yaml` (i.e., plaintext for now, SOPS later) for consistency. If the operator wants to start SOPS-encrypted secrets with arrconf, that's a Phase 8-aligned bonus, not Phase 2 scope.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `kubectl` | Manual secret apply, drift demo, port-forward, log inspection | ✓ | 1.28+ (already used by Phase 0 snapshot.sh) | — |
| `helm` 3.x | Local `helm lint`, `helm template` checks | ✓ | (assumed; cluster runs Helm 3) | — |
| `kubeconform` | Optional manifest validation step in plan | unknown | — | `helm lint` alone, OR install via Brew/Krew on demand |
| GHCR public access | ArgoCD sync of PR1 | needs MANUAL toggle (Pitfall 1) | — | None — must be done before PR1 merge |
| `docker` (operator-side) | Verify `docker pull ghcr.io/...` after Phase 1 release | ✓ | (assumed) | `crane manifest` from `go-containerregistry`; OR `gh api packages/...` |
| ArgoCD App-of-Apps controller | Auto-detect `arrconf-app.yaml` in `argocd/argocd-apps/` | ✓ (cluster-resident) | (cluster-installed) | — |
| Sonarr running in `selfhost` | API target for arrconf + drift demo | ✓ | 4.0.17 [VERIFIED: my-kluster/argocd/argocd-apps/sonarr-app.yaml] | — |
| GitHub Actions (arr-stack) | Image build on `v0.1.0` tag push | ✓ | (Phase 1 already passing) | Manual `docker build && docker push` (NOT recommended — breaks reproducibility) |
| `gh` CLI | Verify GHCR tags post-release; create the v0.1.0 GitHub Release | ✓ (operator workstation) | (assumed) | `git tag v0.1.0 && git push --tags` (no Release page); GHCR REST API via `curl` |
| `jq` 1.7+ | Snapshot diff filtering, drift demo log parsing | ✓ | (used by Phase 0 snapshot.sh) | — |

**Missing dependencies with no fallback:** None — all tooling is in place from Phase 0.

**Missing dependencies with fallback:** GHCR public toggle (manual UI step; documented runbook).

## Validation Architecture

> Phase 2 has NO unit tests (it's a deployment phase, not a code phase). Validation is operational — proven by snapshots, log captures, and Sonarr UI inspection.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | (no Python test framework added in Phase 2) — operational validation only |
| Config file | none |
| Quick run command | `helm lint my-kluster/charts/arrconf/` (local sanity check, runs in <2s) |
| Full suite command | full Phase 2 runbook (snapshot → tag → PR1 → snapshot diff → PR2 → snapshot → drift demo) — run once, takes ~30 minutes elapsed (including cron wait for live runs) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-drift-detection | UI modification corrected at next CronJob run; logs JSON visible | manual+observable (drift demo runbook, Pattern 4) | `kubectl logs job/arrconf-drift-demo -n selfhost \| jq 'select(.event \| contains("update_planned") or contains("applied"))'` | runbook in plan; logs persisted in commit message of "drift demo evidence" |
| REQ-bootstrap-exception | 1ère API key obtenue via UI; injection K8s envFrom: secretRef | manual+observable | `kubectl get secret arrconf-env -n selfhost -o jsonpath='{.data.SONARR_API_KEY}' \| base64 -d \| head -c 8` (echo first 8 chars only — NEVER full key) | secret applied manually pre-PR1 merge |
| REQ-secret-management | Aucun secret committé dans arr-stack | automated (grep audit) | `! grep -rE '(SONARR_API_KEY\|RADARR_API_KEY)\s*[:=]\s*"[^"]+"' arr-stack/ --include="*.yaml" --include="*.yml" 2>&1` (must produce no match) | grep audit can run as a Phase 2 plan task |
| Success Criterion #1 | `before-phase-2/` re-snapshot committed before deploy (D-30 #1) | automated (file presence) | `test -d snapshots/before-phase-2-2026-05-08/sonarr` | snapshots/before-phase-2-2026-05-08/ already created (currently empty per file listing — needs population) |
| Success Criterion #2 | CronJob exists in `selfhost`; secret manual; envFrom secretRef | automated (kubectl) | `kubectl get cronjob arrconf -n selfhost && kubectl get secret arrconf-env -n selfhost && kubectl get cronjob arrconf -n selfhost -o yaml \| yq '.spec.jobTemplate.spec.template.spec.containers[0].envFrom'` | post-PR1 |
| Success Criterion #3 | Dry-run produces zero writes (snapshot diff = 0) | automated (diff -r) | `diff -rq snapshots/before-phase-2-2026-05-08/sonarr/ snapshots/post-phase2-pr1-<date>/sonarr/` | runbook step T+6 |
| Success Criterion #4 | Sonarr UI shows arrconf-managed download_client (post-PR2) | manual (UI inspection) + automated (API check) | `curl -s http://localhost:8989/api/v3/downloadclient/1 -H "X-Api-Key: $SONARR_API_KEY" \| jq '.tags'` (expect non-empty array containing arrconf-managed tag id) | runbook step T+9 |
| Success Criterion #5 | Drift detection prouvée via UI mod + log capture | manual+observable (Pattern 4 runbook) | sequence of `curl PUT` (drift) → `kubectl create job` → `kubectl logs \| jq` | runbook step T+10 |

### Sampling Rate

- **Per task commit (arr-stack repo):** none (no Python tests touched in Phase 2)
- **Per PR (my-kluster repo):** `helm lint charts/arrconf/` + `helm template charts/arrconf/ \| kubeconform -` if installed; manual review of YAML diff
- **Per merge to main (my-kluster):** ArgoCD self-sync; observe in ArgoCD UI
- **Phase gate:** all 5 ROADMAP success criteria checked against the runbook output (snapshots committed, log captures attached to commits or stored under `.planning/phases/02-arrconf-cluster-validation/evidence/`)

### Wave 0 Gaps

- [ ] No new test framework needed.
- [ ] (Optional) `helm` 3.x and `kubeconform` available on operator workstation — verify before plan starts.
- [ ] `snapshots/before-phase-2-2026-05-08/` directory exists but is empty per current file listing — populate via fresh snapshot run as the FIRST plan task. Currently has only empty `sonarr/`, `radarr/`, etc. directories per `find` output (only Prowlarr + Jellyfin partials in subdirs — incomplete). The plan must include "re-run `tools/snapshot/snapshot.sh --output snapshots/before-phase-2-$(date +%F)/` and commit" as task 0.

*(The `before-phase-2-2026-05-08/` directory was created during context-gathering today but only Prowlarr/Jellyfin endpoints landed; sonarr/, radarr/, seerr/ subdirs are EMPTY. Phase 2 plan task #1 must complete this snapshot.)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | yes | API keys via env (`SONARR_API_KEY` from `arrconf-env` Secret); no in-cluster auth bypass; Sonarr's API key model |
| V3 Session Management | no | arrconf is a one-shot CronJob — no sessions |
| V4 Access Control | yes | K8s RBAC: arrconf Pod uses `default` ServiceAccount in `selfhost`; talks to Sonarr Service via cluster DNS (no auth on inter-pod traffic — flat network); Sonarr API key is the only auth boundary |
| V5 Input Validation | yes | `arrconf.yml` validated by pydantic (Phase 1 D-08); JSON Schema gate (D-15); ConfigMap immutable post-render |
| V6 Cryptography | yes (operationally) | TLS to GHCR for image pull; in-cluster HTTP to Sonarr (no TLS — `selfhost` flat namespace, Service IPs); secrets encoded base64 in etcd (NOT encrypted at rest unless cluster has EncryptionConfiguration — out of arr-stack scope) |
| V7 Error Handling & Logging | yes | structlog JSON; SecretStr masking on `repr()`; Phase 1 D-22 fixture audit (irrelevant for Phase 2 chart files but enforces non-leak culture) |
| V10 Communications | partial | TLS to GHCR (image); plaintext to Sonarr in-cluster (acceptable for selfhost flat-network model); no public exposure of arrconf |
| V14 Configuration | yes | `imagePullPolicy: IfNotPresent` + pinned tag; non-root pod (`runAsUser: 1000`); secret only via env, never on disk; `concurrencyPolicy: Forbid`; PVC absent (no persistent state risk) |

### Known Threat Patterns for Phase 2

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secret leak via Pod env dump (`kubectl describe pod` shows env from secretRef in some contexts) | Information Disclosure | `envFrom: secretRef` (NOT inline `env:` with `valueFrom: secretKeyRef`) — `kubectl describe pod` shows only the secret reference, not values; verified by reading kubectl docs and configarr's pattern. SecretStr masking in arrconf ensures `repr()` doesn't leak. [VERIFIED: 01-VERIFICATION.md T-01-01 mitigated] |
| Image supply chain (GHCR public toggle = anonymous pull, no integrity check beyond manifest SHA) | Tampering | Public GHCR (ADR-3 acceptance); cosign signing deferred to v2 (`OPSV2-03`); cluster pinned to exact `0.1.0` tag (no `:latest`); SHA from `metadata-action` provides post-hoc integrity proof |
| Privilege escalation in CronJob pod | Elevation of Privilege | `runAsNonRoot: true`, `runAsUser: 1000`, `runAsGroup: 1000`; no `privileged: true`; no `hostNetwork`; no `hostPath` mounts; default ServiceAccount has no extra RoleBindings; mitigation matches Phase 1 T-01-02 |
| Cross-repo trust (chart in my-kluster pins arr-stack image tag — repo compromise risk) | Tampering | Both repos under same GitHub identity (`tom333`); GitHub branch protection on `main` (assumed; verify if not); arr-stack Phase 1 release process is human-gated (manual `git tag`); a malicious push to arr-stack `main` does not auto-update my-kluster — Renovate or manual PR is required |
| Drift between PR1 and PR2 (window where dry-run is deployed but apply is pending — could be hours) | Repudiation (audit trail) | Two-PR Git history makes the transition explicit; commit messages document the inspection (D-28); ArgoCD's sync history retains the env change |
| ScopeViolationError bypass (somebody adds `quality_profiles` section to `charts/arrconf/files/arrconf.yml` thinking arrconf will write it — but Phase 1 raises ScopeViolationError) | Confused Deputy | Phase 1 D-12 + ADR-5 + 12 parametrized tests prove ScopeViolationError raises BEFORE any HTTP call; pydantic schema in `schemas/arrconf-schema.json` does NOT have a `quality_profiles` section, so YAML editing tools (yaml-language-server) flag it as invalid |
| `kubectl exec` into the CronJob pod during the 4h window | Tampering | CronJob's pod is `Job-controlled` and short-lived (<1min in the apply path); `kubectl exec` is technically possible but the window is small; mitigation = audit `kubectl exec` events via cluster audit log (out of scope for arr-stack to enforce) |
| Sonarr API key reuse across configarr+arrconf (same key, full admin, broader blast radius if leaked) | Information Disclosure | Operationally accepted (D-29 reuses configarr key); rotated together if compromised; per-service segregation deferred to Phase 8 ESO migration |

**Phase 2 net new threat surface (vs Phase 1):** ONE — the secret moving from "lives in arr-stack tests as redacted fixtures" to "lives in my-kluster `secrets/` as plaintext (matching configarr-secret.yaml) and is bound to a real cluster Pod's env." Mitigation: `envFrom: secretRef` is the standard pattern, `arrconf-secret.yaml` is in `.gitignore` per arr-stack but committed to my-kluster (acknowledged TODO; SOPS migration). REQ-secret-management is satisfied as written: the secret is NEVER committed in arr-stack.

## Sources

### Primary (HIGH confidence)

- **arr-stack repo files** (read in full):
  - `/home/moi/projets/perso/arr-stack/.planning/phases/02-arrconf-cluster-validation/02-CONTEXT.md` — Phase 2 locked decisions D-23 to D-30
  - `/home/moi/projets/perso/arr-stack/.planning/REQUIREMENTS.md` — REQ-drift-detection, REQ-bootstrap-exception, REQ-secret-management
  - `/home/moi/projets/perso/arr-stack/.planning/STATE.md`, `/home/moi/projets/perso/arr-stack/.planning/ROADMAP.md` — phase status
  - `/home/moi/projets/perso/arr-stack/spec.md` — §6.4, §7 Phase 2, §10 Q3, §11 ADR-3/5/6
  - `/home/moi/projets/perso/arr-stack/CLAUDE.md` — Workflow snapshot, env vars, my-kluster integration
  - `/home/moi/projets/perso/arr-stack/tools/arrconf/README.md` — Phase 1 CLI reference + Pitfall 7 GHCR public toggle
  - `/home/moi/projets/perso/arr-stack/tools/snapshot/snapshot.sh` (407 lines) and `tools/snapshot/README.md`
  - `/home/moi/projets/perso/arr-stack/examples/baseline-sonarr.yml` — Phase 1 round-trip artefact
  - `/home/moi/projets/perso/arr-stack/.planning/phases/01-arrconf-poc-json-schema/{01-CONTEXT,01-VERIFICATION,01-HUMAN-UAT}.md` — Phase 1 D-01 to D-22 + outcomes
  - `/home/moi/projets/perso/arr-stack/.github/workflows/{arrconf-image,tests}.yml` — Phase 1 CI workflows
  - `/home/moi/projets/perso/arr-stack/tools/arrconf/Dockerfile` — image build, USER 1000:1000, ENTRYPOINT
  - `/home/moi/projets/perso/arr-stack/snapshots/baseline-2026-05-07/sonarr/downloadclient.json` — Phase 0 baseline (qBit client)

- **my-kluster repo files** (read in full):
  - `/home/moi/projets/perso/my-kluster/CLAUDE.md` — sister-repo conventions, AppProjects, secrets discipline, Renovate
  - `/home/moi/projets/perso/my-kluster/charts/configarr/{Chart.yaml,values.yaml,templates/_helpers.tpl,templates/cronjob.yaml,templates/configmap.yaml,templates/pvc.yaml}` — full template reference for substitution
  - `/home/moi/projets/perso/my-kluster/argocd/argocd-apps/{configarr-app.yaml,sonarr-app.yaml,jellyfin-app.yaml}` — ArgoCD App templates + Sonarr Service config (port 8989)
  - `/home/moi/projets/perso/my-kluster/argocd/argocd-appprojects/selfhost-project.yaml` — AppProject scope
  - `/home/moi/projets/perso/my-kluster/secrets/configarr-secret.yaml` — secret pattern reference

### Secondary (MEDIUM confidence)

- WebSearch verified with official sources:
  - [Kubernetes CronJob `concurrencyPolicy` semantics](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/) — confirms Forbid policy semantics
  - [GitHub issue kubernetes/kubernetes#107827](https://github.com/kubernetes/kubernetes/issues/107827) — confirms manual `kubectl create job --from=cronjob` bypasses concurrencyPolicy
  - [ArgoCD Automated Sync Policy docs](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/) — `automated.prune`/`selfHeal` semantics
  - [Helm Chart Tips & Tricks — checksum/config](https://helm.sh/docs/howto/charts_tips_and_tricks/) — checksum annotation pattern
  - [helm/helm#10346](https://github.com/helm/helm/issues/10346) — checksum annotation behavior on CronJob jobTemplate (largely cosmetic per discussion)
- [docker/metadata-action@v5 docs (assumed; verify Phase 2 task)](https://github.com/docker/metadata-action) — `{{version}}` strips leading `v`

### Tertiary (LOW confidence — flagged for Phase 2 verification)

- A1 (image tag format): only verifiable empirically once `v0.1.0` tag is pushed to arr-stack and arrconf-image.yml runs.
- A4 (CronJob `args:` literal acceptance by Phase 1 image): only verifiable by an actual `kubectl create job --from=cronjob/arrconf` post-deploy.

## Metadata

**Confidence breakdown:**

- **Standard stack & substitution map**: HIGH — all source files for substitution were read in full and the deltas are tabulated; configarr's pattern is battle-tested in cluster
- **Architecture (two-PR protocol, ConfigMap injection, ArgoCD App)**: HIGH — locked by D-26/D-27/D-28; mirror existing configarr; no novel mechanisms
- **Pitfalls 1-3 (GHCR public, image tag, secret-before-sync)**: HIGH — directly experienced in Phase 1 HUMAN-UAT (#1 + #3) or canonical configarr operational story (#3)
- **Pitfalls 4-8 (concurrency, checksum, prune, TZ, self-heal)**: MEDIUM — verified by official docs + GitHub issues; minor risk of K8s version-specific drift but Phase 2 is on a stable cluster
- **Pitfalls 9-10 (Phase 1 tag absent, structlog TTY)**: HIGH on conceptual, MEDIUM on operational
- **Drift demo runbook**: MEDIUM — log format inferred from Phase 1 reconciler structure (`reconcilers/sonarr.py`) and structlog conventions; exact event names may differ slightly
- **Validation strategy (snapshot-diff = 0)**: HIGH — Phase 1 already proved zero-write at unit level (52 tests, 99% coverage on critical paths); Phase 2 corroboration is the easy half
- **Threat model**: HIGH — Phase 1 already locked T-01-01 through T-01-07; Phase 2 adds nothing novel beyond the secret-in-cluster step (well-trodden by configarr)
- **Image tag verification (A1)**: MEDIUM — need empirical confirmation; documented as a plan task

**Research date:** 2026-05-08
**Valid until:** 2026-06-08 (30 days; stable mature cluster, no upstream churn expected on K8s/ArgoCD/Helm patterns)
