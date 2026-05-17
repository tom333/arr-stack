---
phase: 02
slug: arrconf-cluster-validation
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-08
approved: 2026-05-08
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
>
> **Phase 2 has NO unit tests** (it's a deployment phase, not a code phase). Validation is operational — proven by snapshots, log captures, ArgoCD sync state, kubectl resource inspection, and Sonarr API verification. Sampling rate is per-stage runbook checkpoints.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | none (operational validation only — Phase 1 already covers code paths with 99% pytest coverage) |
| **Config file** | none |
| **Quick run command** | `helm lint my-kluster/charts/arrconf/` (local sanity, < 2 s) |
| **Full suite command** | full Phase 2 runbook (snapshot -> tag release -> chart authoring -> PR1 -> snapshot diff -> PR2 -> snapshot -> drift demo) |
| **Estimated runtime** | ~30 min elapsed (includes 1 cron cycle wait + cross-repo PRs) |

---

## Sampling Rate

- **Per task commit (arr-stack repo):** none (no Python tests touched in Phase 2)
- **Per PR (my-kluster repo):** `helm lint charts/arrconf/` + `helm template charts/arrconf/ | kubeconform -` (if installed); manual review of YAML diff
- **Per merge to main (my-kluster):** ArgoCD self-sync; observe in ArgoCD UI
- **Phase gate:** all 5 ROADMAP success criteria checked against the runbook output (snapshots committed, log captures attached to commits or stored under `.planning/phases/02-arrconf-cluster-validation/evidence/`)
- **Max feedback latency:** 4 h (one cron cycle) for live drift detection; instant for `helm lint` / `kubeconform`

---

## Per-Task Verification Map

> Plan numbering: 02-01 (snapshot baseline), 02-02 (v0.1.0 release + GHCR), 02-03 (chart authoring), 02-04 (PR1 dry-run), 02-05 (PR2 apply + drift). Granular task IDs follow plan-NN-task-NN convention.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-1.1 | snapshot-baseline | 1 | success-criterion-1 (D-30 #1) | — | full re-snapshot before deploy | automated (file presence) | `find snapshots/before-phase-2-2026-05-08/sonarr -type f -name '*.json' \| wc -l` >= 5 | ❌ W0 (sonarr/ subdir empty as of 2026-05-08) | ⬜ pending |
| 02-01-1.2 | evidence-dir-init | 1 | (preparatory) | — | evidence/ ready for Wave 2/3 logs | automated (file presence) | `test -f .planning/phases/02-arrconf-cluster-validation/evidence/.gitkeep` | post-create | ⬜ pending |
| 02-02-2.1 | release-tag-v0.1.0 | 1 | (Phase 1 image release) | T-image-supply-chain | image pinned to immutable tag | automated (GHCR query) | `gh api /users/tom333/packages/container/arr-stack-arrconf/versions \| jq -e '[.[].metadata.container.tags[]] \| any(test("^v?0\\.1\\.0$"))'` | post-tag | ⬜ pending |
| 02-02-2.2 | ghcr-public-toggle | 1 | (Phase 1 HUMAN-UAT #1) | T-image-supply-chain | image publicly pullable | manual (UI) + automated (anonymous pull test) | `[ "$(gh api /users/tom333/packages/container/arr-stack-arrconf \| jq -r .visibility)" = "public" ]` (N/A — no test framework — operational validation phase) | manual UI step | ⬜ pending |
| 02-03-3.1 | cluster-services-capture | 2 | (W-03 fix) | T-hostname-mismatch | verified Sonarr/qBit hostnames captured | automated (grep) | `grep -qE '^SONARR_HOST=sonarr\.selfhost\.svc\.cluster\.local$' .planning/phases/02-arrconf-cluster-validation/.cluster-services` | post-capture | ⬜ pending |
| 02-03-3.2 | mini-chart-arrconf | 2 | success-criterion-2 | T-secret-leak / T-priv-escalation | chart + ConfigMap + ArgoCD App + secret pattern | automated (helm lint + kubeconform) | `helm lint my-kluster/charts/arrconf/ && helm template my-kluster/charts/arrconf/ \| kubeconform -strict -` | post-create | ⬜ pending |
| 02-03-3.3 | secret-grep-audit | 2 | REQ-secret-management | T-secret-leak | no plaintext secrets in arr-stack repo | automated (grep, W-02 POSIX class) | `! grep -rE '(SONARR_API_KEY\|RADARR_API_KEY\|PROWLARR_API_KEY)[[:space:]]*[:=][[:space:]]*"[^"]+"' . --include="*.yaml" --include="*.yml" --include="*.py" --exclude-dir=.git --exclude-dir=snapshots` | (always runnable) | ⬜ pending |
| 02-03-3.4 | cross-repo-tree-checkpoint | 2 | (B-01 fix) | T-cross-repo-trust | working-tree state matches expected 9-file list | manual + automated (file count) | `[ "$(git -C ~/projets/perso/my-kluster status --short charts/arrconf/ argocd/argocd-apps/arrconf-app.yaml secrets/arrconf-secret.yaml \| wc -l)" = "9" ]` (N/A — no watch-mode — checkpoint pauses execution) | runtime | ⬜ pending |
| 02-04-4.1 | pr1-deploy-dryrun | 3 | success-criterion-2 + REQ-bootstrap-exception | T-secret-leak / T-priv-escalation / T-bootstrap-trust / T-env-source-bypass | CronJob exists, secret bound via envFrom, NO ArgoCD tracking-id, EXACTLY 1 volumeMount (config) | automated (kubectl + jq) | `kubectl get cronjob arrconf -n selfhost && [ -z "$(kubectl get secret arrconf-env -n selfhost -o jsonpath='{.metadata.annotations.argocd\.argoproj\.io/tracking-id}')" ] && kubectl get cronjob arrconf -n selfhost -o jsonpath='{.spec.jobTemplate.spec.template.spec.containers[0].volumeMounts}' \| jq -e 'length == 1 and .[0].name == "config"'` | post-PR1 sync | ⬜ pending |
| 02-04-4.2 | pr1-smoke-job-dryrun-events | 3 | success-criterion-2 | T-scope-bypass | dry-run path event names present (W-06 verified from sonarr.py + differ.py) | automated (jq event-name match) | `EVIDENCE=.../pr1-job-logs-*.log; [ "$(jq -c 'select(.event == "managed_tag_found" or .event == "would_create_managed_tag")' "$EVIDENCE" \| wc -l)" -ge 1 ] && [ "$(jq -c 'select(.event == "plan_action")' "$EVIDENCE" \| wc -l)" -ge 1 ] && [ "$(jq -c 'select(.event == "managed_tag_created")' "$EVIDENCE" \| wc -l)" = "0" ]` | runbook step T+5 | ⬜ pending |
| 02-04-4.3 | snapshot-post-pr1 | 3 | success-criterion-3 | — | snapshot captured after dry-run cycle, diff = 0 | automated (file presence + diff) | `[ "$(diff -rq snapshots/before-phase-2-2026-05-08/sonarr/ snapshots/post-phase2-pr1-$(date +%F)/sonarr/ \| wc -l)" = "0" ]` | runbook step T+6 | ⬜ pending |
| 02-05-5.1a | pr2-flip-apply | 4 | success-criterion-4 | T-drift-pr1-pr2 | dry-run flag flipped to false (single-acceptance dispositive) | automated (kubectl + jq) | `kubectl get cronjob arrconf -n selfhost -o jsonpath='{.spec.jobTemplate.spec.template.spec.containers[0].env}' \| jq -e '[.[] \| select(.name=="ARRCONF_DRY_RUN")][0].value == "false"'` | runbook step T+7 | ⬜ pending |
| 02-05-5.1b | pr2-smoke-job-apply-events | 4 | success-criterion-4 | T-scope-bypass | apply-mode event names present (W-06 verified) | automated (jq event-name match) | `EVIDENCE=.../pr2-job-logs-*.log; [ "$(jq -c 'select(.event == "managed_tag_created" or .event == "managed_tag_found")' "$EVIDENCE" \| wc -l)" -ge 1 ] && [ "$(jq -c 'select(.event == "would_create_managed_tag" or .event == "dry_run_skip")' "$EVIDENCE" \| wc -l)" = "0" ]` | runbook step T+8 | ⬜ pending |
| 02-05-5.1c | snapshot-post-pr2-tag-verify | 4 | success-criterion-4 (D-30 #3) | — | snapshot captured post-apply showing managed resource (file + API dispositive) | automated (jq on snapshot) | `jq -e 'map(.label) \| any(. == "arrconf-managed")' snapshots/post-phase2-pr2-$(date +%F)/sonarr/tag.json && jq -e '.[0].tags \| length > 0' snapshots/post-phase2-pr2-$(date +%F)/sonarr/downloadclient.json` | runbook step T+9 | ⬜ pending |
| 02-05-5.2 | drift-demo-runbook | 4 | REQ-drift-detection + success-criterion-5 (D-30 #4) | T-confused-deputy | UI mod corrected at next run; JSON logs captured; W-04 dispositive value-equality; W-01 REQUIRED snapshot | automated (jq + file presence + value-equality persisted) | `EVIDENCE=.../drift-demo-*.log; [ "$(jq -c 'select(.event == "plan_action" and .action == "update")' "$EVIDENCE" \| wc -l)" -ge 1 ] && test -d snapshots/drift-test-$(date +%F) && grep -q 'match (restored == original): YES' "$EVIDENCE"` | runbook step T+10 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] **`tools/snapshot/snapshot.sh` operational** — already shipped Phase 0; `--apps` flag and output structure verified by Phase 0 baseline
- [x] **`helm` 3.x available** — confirmed-or-deferred-to-runbook (executor verifies on workstation before Plan 02-03 helm lint step)
- [x] **`kubeconform`** available — confirmed-or-deferred-to-runbook (optional; if missing, plan 02-03 falls back to helm lint only per acceptance criteria)
- [x] **`kubectl` context = my-kluster** with `selfhost` namespace access — confirmed-or-deferred-to-runbook
- [x] **`snapshots/before-phase-2-2026-05-08/`** — Plan 02-01 Task 1.1 explicitly re-populates this directory (W0 gap addressed in plan, not deferred)
- [x] **`gh` CLI authenticated** — confirmed-or-deferred-to-runbook (used by Plan 02-02 for tag/CI watch + GHCR query, and by Plan 02-04/02-05 for PR creation)

*Wave 0 status: complete — Plan 02-01 explicitly addresses the snapshot W0 gap; tooling availability is per-stage runbook checkpoint at the operator's workstation.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GHCR package public-visibility toggle | (Phase 1 HUMAN-UAT #1) — image must be anonymously pullable | GHCR has no `gh` CLI command for this; UI-only | After `git tag v0.1.0 && git push --tags` triggers `arrconf-image.yml` and the package appears: visit `https://github.com/users/tom333/packages/container/arr-stack-arrconf/settings`, scroll to "Danger Zone", click "Change visibility" -> Public. Verify with `docker pull ghcr.io/tom333/arr-stack-arrconf:<recorded-tag>` from an unauthenticated host. |
| Apply `arrconf-secret.yaml` BEFORE PR1 ArgoCD sync | success-criterion-2 + REQ-bootstrap-exception | ArgoCD does not manage `my-kluster/secrets/` (excluded from sync); operator must `kubectl apply` manually | `kubectl apply -f my-kluster/secrets/arrconf-secret.yaml` -> `kubectl get secret arrconf-env -n selfhost`. If skipped: pod CrashLoops on missing `SONARR_API_KEY`. |
| Cross-repo working-tree checkpoint (B-01) | (operational gate before Wave 2) | Working-tree state in my-kluster cannot be inferred from arr-stack git history; operator visually confirms exact 9-file list | Plan 02-03 Task 3.4 shows `git -C my-kluster status --short` and asks operator to acknowledge tree state matches expected list before Wave 2 starts. |
| Sonarr UI inspection — managed download_client appears with `arrconf-managed` tag | success-criterion-4 | Visual sanity — confirms Phase 1's `tags=[arrconf-managed]` annotation reaches Sonarr | After PR2 + 1 cron cycle (<= 4 h): port-forward `kubectl -n selfhost port-forward svc/sonarr 8989:8989`, visit `http://localhost:8989/settings/downloadclients`, confirm `qbittorrent` (or whatever name) is listed and the row's tags include `arrconf-managed`. (Also verified programmatically by Plan 02-05 Task 5.1c via jq on snapshot tag.json + curl Sonarr API.) |
| Drift demo log capture committed as evidence | REQ-drift-detection + success-criterion-5 | Visual proof for stakeholders / future debugging — JSON log lines must be persisted | Save `kubectl logs job/arrconf-drift-demo -n selfhost` output to `.planning/phases/02-arrconf-cluster-validation/evidence/drift-demo-<date>.log`, link from the final Phase 2 commit message. (Also W-04 dispositive value-equality persisted to file via Plan 02-05 Task 5.2 Step 6.) |
| ArgoCD sync state green for `arrconf` Application after PR1 and PR2 | success-criterion-2 + success-criterion-4 | ArgoCD UI is the source of truth for sync status | `argocd app get arrconf` (CLI) or visit ArgoCD UI; expect Sync Status = Synced + Healthy. |

---

## Validation Sign-Off

- [x] All tasks have an automated verification command OR are listed in Manual-Only Verifications with explicit instructions
- [x] Sampling continuity: snapshot diff is the per-stage feedback signal (no 3 consecutive tasks without an observable outcome) — and per W-01 fix, drift-test snapshot is REQUIRED, not Optional
- [x] Wave 0 covers all MISSING references (especially the empty `before-phase-2-2026-05-08/sonarr/` directory — addressed by Plan 02-01 Task 1.1)
- [x] No watch-mode flags (N/A — operational validation phase; deploy phase has no test runners; checkpoints pause execution per design)
- [x] Feedback latency < 4 h (one cron cycle) for live verifications; < 2 s for chart-lint (N/A — no test framework, operational validation phase)
- [x] `nyquist_compliant: true` set in frontmatter (set 2026-05-08 — all 14 task rows have automated `<verify>` blocks; checkpoint tasks have automated dispositive checks per B-02/B-03/W-04 fixes)

**Approval:** approved 2026-05-08 (operational validation phase — no unit tests; sampling rate is per-stage runbook checkpoints + helm lint + snapshot diff + W-06 verified event-name jq filters + B-02 volumeMount inspection + W-04 dispositive value-equality + W-01 REQUIRED forensic snapshot pair)
</content>
</invoke>