---
phase: 02-arrconf-cluster-validation
plan: 03
type: summary
wave: 2
status: complete
captured: 2026-05-08
arr_stack_commits:
  - f674f86  # docs(02): capture verified cluster service hostnames + image tag (W-03, B-NEW-01)
  - cf1a808  # docs(02): redact API key literals leaked into PATTERNS/RESEARCH (CLAUDE.md anti-secret)
my_kluster_state: working_tree_uncommitted  # 8 git-visible + 1 gitignored on disk; PR1 in Plan 02-04 will commit the 8
---

# Plan 02-03 Summary — my-kluster Chart Authoring

## Outcome

Mini-chart `my-kluster/charts/arrconf/` + ArgoCD App `arrconf-app.yaml` + bootstrap Secret `secrets/arrconf-secret.yaml` authored in the my-kluster working tree. helm lint passes, helm template renders 2 kinds (CronJob + ConfigMap) with all expected fields. arr-stack repo secret-leak audit clean.

Cross-repo working tree state matches the corrected expectation (8 git-visible + 1 gitignored — see Deviations §1) — Plan 02-04 Task 4.1 can proceed to commit + PR1.

## Files authored

### my-kluster (uncommitted)

| Path | git status | Provides |
|---|---|---|
| `charts/arrconf/Chart.yaml` | `??` | name=arrconf, version=0.1.2, appVersion="0.1.2" |
| `charts/arrconf/values.yaml` | `??` | image:0.1.2, arrconfDryRun:true (D-28 PR1), apiKeysSecret:arrconf-env, # renovate annotation immediately above repository |
| `charts/arrconf/files/arrconf.yml` | `??` | Sonarr-only YAML, base_url + qBit host literals from .cluster-services, prune:false, tags:[], no quality_profiles/custom_formats/quality_definitions/media_naming (ADR-5) |
| `charts/arrconf/templates/_helpers.tpl` | `??` | 5 helpers (arrconf.name/fullname/chart/labels/selectorLabels), no leftover `configarr.` |
| `charts/arrconf/templates/cronjob.yaml` | `??` | envFrom secretRef, ARRCONF_DRY_RUN env, runAsNonRoot 1000:1000, no tty:true (Pitfall 10), no cache volume, args: ["apply", "--config", "/app/config/arrconf.yml", "--apps", "sonarr"], startingDeadlineSeconds 600 (D-23) |
| `charts/arrconf/templates/configmap.yaml` | `??` | .Files.Get "files/arrconf.yml" |
| `charts/arrconf/README.md` | `??` | Two-PR protocol (D-28), pre-merge checklist, drift demo runbook, operational caveats (Pitfalls 4/5/8/10) |
| `argocd/argocd-apps/arrconf-app.yaml` | `??` | mirror of configarr-app.yaml: project=selfhost-project, path=charts/arrconf, selfHeal+prune, ServerSideApply |
| `secrets/arrconf-secret.yaml` | **gitignored** | Opaque Secret arrconf-env with SONARR_API_KEY only (D-29 least-privilege) |

### arr-stack (committed)

| Path | Commit | Provides |
|---|---|---|
| `.planning/phases/02-arrconf-cluster-validation/.cluster-services` | f674f86 | Verified hostnames + IMAGE_TAG_VERIFIED=0.1.2 capture file |
| `.planning/phases/02-arrconf-cluster-validation/02-PATTERNS.md` | cf1a808 | API key literals redacted (3 occurrences) |
| `.planning/phases/02-arrconf-cluster-validation/02-RESEARCH.md` | cf1a808 | API key literals redacted (2 occurrences) |

## Validation results

- **helm lint** — pass (1 INFO: "icon is recommended", non-blocking)
- **helm template** — renders 2 kinds (CronJob + ConfigMap)
- **kubeconform** — not installed on workstation (acceptable per VALIDATION.md fallback to helm lint only)
- **Render checks**: envFrom present, ARRCONF_DRY_RUN env present, image=ghcr.io/tom333/arr-stack-arrconf:0.1.2, no :latest
- **arr-stack secret-leak audit** — 0 matches after redaction
- **Cross-repo working tree (B-01 + W-NEW-01)** — 8 git-visible in scope, 0 out-of-scope (untracked or modified)

## Deviations from plan

1. **Plan expected 9 git-visible files; reality is 8 + 1 gitignored** — `my-kluster/.gitignore` line 2: `secrets/`. So `secrets/arrconf-secret.yaml` exists on disk (158 bytes, written by this plan) but is intentionally NOT tracked by git. This matches the operational pattern documented in 02-VALIDATION.md "Manual-Only Verifications" row 2 ("ArgoCD does not manage `my-kluster/secrets/` (excluded from sync); operator must `kubectl apply` manually"). Plan 02-03 Task 3.4's count assertion (`== 9`) was a spec-vs-implementation drift. The corrected expectation is **8 git-visible + 1 on-disk-only** = 9 files authored total. Plan 02-04 Task 4.1 must NOT try to `git add secrets/arrconf-secret.yaml` — it would silently no-op due to gitignore (and the file is already filed for `kubectl apply` outside ArgoCD's purview). For Plan 02-04 reference: stage these 8 paths only:
   ```
   argocd/argocd-apps/arrconf-app.yaml
   charts/arrconf/Chart.yaml
   charts/arrconf/README.md
   charts/arrconf/files/arrconf.yml
   charts/arrconf/templates/_helpers.tpl
   charts/arrconf/templates/configmap.yaml
   charts/arrconf/templates/cronjob.yaml
   charts/arrconf/values.yaml
   ```

2. **Chart.yaml description colon quoted** — initial version of Chart.yaml had `description: arrconf — ... (Phase 2 scope: Sonarr download_clients only)`. The unquoted `:` after "scope" was parsed by helm/yaml as a nested mapping start, failing helm lint with "mapping values are not allowed in this context, line 3". Fixed by quoting the entire description string. Plan 02-03 <interfaces> block (line 146) shows the description un-quoted — that block has the same bug. If/when Plan 02-03 is re-executed, the executor must quote it.

3. **Planning-doc credential leak caught + redacted** — Task 3.3's secret-leak audit on arr-stack found 5 occurrences of literal `RADARR_API_KEY` / `SONARR_API_KEY` 32-hex values in `02-PATTERNS.md` (3) and `02-RESEARCH.md` (2). These were authored during Phase 2 planning to document Open Q3 / D-29 secret-strategy decisions. The values match `my-kluster/secrets/configarr-secret.yaml` (acknowledged plaintext until Phase 8 ESO). Per CLAUDE.md "Ne pas committer de secrets" (spirit applies to docs too), redacted to `<SONARR_API_KEY redacted — see my-kluster/secrets/configarr-secret.yaml>` with similar form for RADARR. Re-audit: 0 leaks. Commit cf1a808.

4. **my-kluster pre-existing changes stashed** — when this plan began, my-kluster had 8 unrelated out-of-scope changes (README.md, beszel/, CLAUDE.md, TODO.md, config/, openmetadata/, scripts/). Stashed in 2 entries (`stash@{0}: pre-arrconf-Phase2-tracked-2026-05-08`, `stash@{1}: pre-arrconf-Phase2-2026-05-08`) so the W-NEW-01 out-of-scope checks could be honest. Both stashes will be `git stash pop`'d after Phase 2 closes.

5. **`.kube/` permission warning** — `git status` in my-kluster prints `warning: impossible d'ouvrir le répertoire '.kube/': Permission non accordée`. Cosmetic; the directory contains a kubeconfig with restricted perms (intentional). Doesn't affect any check.

## What this unblocks

- Plan 02-04 Task 4.1 can stage the 8 in-scope my-kluster files + commit + PR1.
- The bootstrap Secret file is on disk in `my-kluster/secrets/` ready for Plan 02-04 Task 4.1 step "manual `kubectl apply -f my-kluster/secrets/arrconf-secret.yaml`" BEFORE ArgoCD syncs the chart.
- The `image_tag_verified: 0.1.2` literal round-tripped cleanly: 02-02-SUMMARY → .cluster-services (f674f86) → values.yaml.image.tag="0.1.2" (rendered).

## Reminder for Phase 2 close

After Wave 4 (Plan 02-05) completes, run in `/home/moi/projets/perso/my-kluster/`:

```bash
git stash pop stash@{0}   # pre-arrconf-Phase2-tracked-2026-05-08 (README.md, beszel/beszel.yml)
git stash pop stash@{0}   # pre-arrconf-Phase2-2026-05-08 (CLAUDE.md, TODO.md, config/, openmetadata/, scripts/) — note same index since first pop shifted
```

(After first pop, the second stash becomes `stash@{0}`.)
