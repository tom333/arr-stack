---
phase: 02
slug: arrconf-cluster-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-08
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
>
> **Phase 2 has NO unit tests** (it's a deployment phase, not a code phase). Validation is operational — proven by snapshots, log captures, ArgoCD sync state, and Sonarr UI/API inspection.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | none (operational validation only — Phase 1 already covers code paths with 99% pytest coverage) |
| **Config file** | none |
| **Quick run command** | `helm lint my-kluster/charts/arrconf/` (local sanity, < 2 s) |
| **Full suite command** | full Phase 2 runbook (snapshot → tag → PR1 → snapshot diff → PR2 → snapshot → drift demo) |
| **Estimated runtime** | ~30 min elapsed (includes 1 cron cycle wait) |

---

## Sampling Rate

- **Per task commit (arr-stack repo):** none (no Python tests touched in Phase 2)
- **Per PR (my-kluster repo):** `helm lint charts/arrconf/` + `helm template charts/arrconf/ | kubeconform -` (if installed); manual review of YAML diff
- **Per merge to main (my-kluster):** ArgoCD self-sync; observe in ArgoCD UI
- **Phase gate:** all 5 ROADMAP success criteria checked against the runbook output (snapshots committed, log captures attached to commits or stored under `.planning/phases/02-arrconf-cluster-validation/evidence/`)
- **Max feedback latency:** 4 h (one cron cycle) for live drift detection; instant for `helm lint` / `kubeconform`

---

## Per-Task Verification Map

> Task IDs are placeholders — planner will fill them in. Rows are organized by ROADMAP success criterion / REQ.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-XX | snapshot-baseline | 1 | success-criterion-1 (D-30 #1) | — | full re-snapshot before deploy | automated (file presence) | `test -d snapshots/before-phase-2-2026-05-08/sonarr && find snapshots/before-phase-2-2026-05-08/sonarr -type f \| head -1` | ❌ W0 (sonarr/ subdir empty as of 2026-05-08) | ⬜ pending |
| 02-01-XX | release-tag-v0.1.0 | 1 | (Phase 1 image release) | T-image-supply-chain | image pinned to immutable tag | automated (GHCR query) | `gh api /users/tom333/packages/container/arr-stack-arrconf/versions \| jq '.[] \| .metadata.container.tags'` (verify `0.1.0` or `v0.1.0` exists) | post-tag | ⬜ pending |
| 02-01-XX | ghcr-public-toggle | 1 | (Phase 1 HUMAN-UAT #1) | T-image-supply-chain | image publicly pullable | manual (UI) + automated (anonymous pull test) | `docker pull ghcr.io/tom333/arr-stack-arrconf:0.1.0` from a host with no GHCR credentials | manual UI step | ⬜ pending |
| 02-02-XX | mini-chart-arrconf | 1 | success-criterion-2 | T-secret-leak / T-priv-escalation | chart + ConfigMap + ArgoCD App + secret pattern | automated (helm lint + kubeconform) | `helm lint my-kluster/charts/arrconf/ && helm template my-kluster/charts/arrconf/ \| kubeconform -strict -` | post-create | ⬜ pending |
| 02-02-XX | secret-grep-audit | 1 | REQ-secret-management | T-secret-leak | no plaintext secrets in arr-stack repo | automated (grep) | `! grep -rE '(SONARR_API_KEY\|RADARR_API_KEY\|PROWLARR_API_KEY)\s*[:=]\s*"[^"]+"' . --include="*.yaml" --include="*.yml" --include="*.py" --exclude-dir=.git --exclude-dir=snapshots` (must produce no match) | (always runnable) | ⬜ pending |
| 02-03-XX | pr1-deploy-dryrun | 2 | success-criterion-2 + REQ-bootstrap-exception | T-secret-leak / T-priv-escalation | CronJob exists, secret bound via envFrom | automated (kubectl) | `kubectl get cronjob arrconf -n selfhost && kubectl get secret arrconf-env -n selfhost && kubectl get cronjob arrconf -n selfhost -o yaml \| yq '.spec.jobTemplate.spec.template.spec.containers[0].envFrom \| length' \| grep -q '^1$'` | post-PR1 sync | ⬜ pending |
| 02-03-XX | snapshot-post-pr1 | 2 | success-criterion-3 | — | snapshot captured after dry-run cycle | automated (file presence + diff) | `test -d snapshots/post-phase2-pr1-$(date +%F)/sonarr && diff -rq snapshots/before-phase-2-2026-05-08/sonarr/ snapshots/post-phase2-pr1-$(date +%F)/sonarr/` (expect zero output = identical) | runbook step T+6 | ⬜ pending |
| 02-04-XX | pr2-flip-apply | 3 | success-criterion-4 | T-drift-pr1-pr2 | dry-run flag flipped to false; arrconf applies download_client | automated (curl Sonarr API) | `curl -s "http://localhost:8989/api/v3/downloadclient/<id>" -H "X-Api-Key: $SONARR_API_KEY" \| jq '.tags \| length > 0'` (expect `true` after run; tag id = arrconf-managed) | runbook step T+9 | ⬜ pending |
| 02-04-XX | snapshot-post-pr2 | 3 | success-criterion-4 (D-30 #3) | — | snapshot captured post-apply showing managed resource | automated (file presence) | `test -d snapshots/post-phase2-pr2-$(date +%F)/sonarr` | runbook step T+9 | ⬜ pending |
| 02-05-XX | drift-demo-runbook | 3 | REQ-drift-detection + success-criterion-5 (D-30 #4) | — | UI mod corrected at next run; JSON logs captured | manual + automated (kubectl logs) | `kubectl create job --from=cronjob/arrconf arrconf-drift-demo -n selfhost && kubectl logs job/arrconf-drift-demo -n selfhost \| jq -c 'select(.event \| contains("update_planned") or contains("applied"))'` (expect at least one event line) | runbook step T+10 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] **`tools/snapshot/snapshot.sh` operational** — already shipped Phase 0; verify `--apps` flag and output structure with a dry sanity run
- [ ] **`helm` 3.x available** on operator workstation
- [ ] **`kubeconform`** available on operator workstation (optional but recommended for chart-lint CI)
- [ ] **`kubectl` context = my-kluster** with `selfhost` namespace access
- [ ] **`snapshots/before-phase-2-2026-05-08/`** — re-populate (currently has only Prowlarr/Jellyfin partials; sonarr/, radarr/, seerr/ subdirs are EMPTY). The plan's first task MUST be: re-run `tools/snapshot/snapshot.sh --output snapshots/before-phase-2-$(date +%F)/` and commit.
- [ ] **`gh` CLI authenticated** with read access to `tom333/arr-stack` GHCR packages (for image tag verification + public-visibility toggle)

*If none of the above are missing on operator workstation: the plan can skip Wave 0 prep and start at "snapshot baseline".*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GHCR package public-visibility toggle | (Phase 1 HUMAN-UAT #1) — image must be anonymously pullable | GHCR has no `gh` CLI command for this; UI-only | After `git tag v0.1.0 && git push --tags` triggers `arrconf-image.yml` and the package appears: visit `https://github.com/users/tom333/packages/container/arr-stack-arrconf/settings`, scroll to "Danger Zone", click "Change visibility" → Public. Verify with `docker pull ghcr.io/tom333/arr-stack-arrconf:0.1.0` from an unauthenticated host. |
| Apply `arrconf-secret.yaml` BEFORE PR1 ArgoCD sync | success-criterion-2 + REQ-bootstrap-exception | ArgoCD does not manage `my-kluster/secrets/` (excluded from sync); operator must `kubectl apply` manually | `kubectl apply -f my-kluster/secrets/arrconf-secret.yaml` → `kubectl get secret arrconf-env -n selfhost`. If skipped: pod CrashLoops on missing `SONARR_API_KEY`. |
| Sonarr UI inspection — managed download_client appears with `arrconf-managed` tag | success-criterion-4 | Visual sanity — confirms Phase 1's `tags=[arrconf-managed]` annotation reaches Sonarr | After PR2 + 1 cron cycle (≤ 4 h): port-forward `kubectl -n selfhost port-forward svc/sonarr 8989:8989`, visit `http://localhost:8989/settings/downloadclients`, confirm `qbittorrent-tv` (or whatever D-25 names it) is listed and the row's tags include `arrconf-managed`. |
| Drift demo log capture committed as evidence | REQ-drift-detection + success-criterion-5 | Visual proof for stakeholders / future debugging — JSON log lines must be persisted | Save `kubectl logs job/arrconf-drift-demo -n selfhost` output to `.planning/phases/02-arrconf-cluster-validation/evidence/drift-demo-<date>.log`, link from the final Phase 2 commit message. |
| ArgoCD sync state green for `arrconf` Application after PR1 and PR2 | success-criterion-2 | ArgoCD UI is the source of truth for sync status | `argocd app get arrconf` (CLI) or visit ArgoCD UI; expect Sync Status = Synced + Healthy. |

---

## Validation Sign-Off

- [ ] All tasks have an automated verification command OR are listed in Manual-Only Verifications with explicit instructions
- [ ] Sampling continuity: snapshot diff is the per-stage feedback signal (no 3 consecutive tasks without an observable outcome)
- [ ] Wave 0 covers all MISSING references (especially the empty `before-phase-2-2026-05-08/sonarr/` directory)
- [ ] No watch-mode flags (deploy phase — no test runners)
- [ ] Feedback latency < 4 h (one cron cycle) for live verifications; < 2 s for chart-lint
- [ ] `nyquist_compliant: true` set in frontmatter once all rows above pass

**Approval:** pending
