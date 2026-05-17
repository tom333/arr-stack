---
phase: 4
slug: umbrella-chart-migration-des-9-apps
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-12
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: derived from `04-RESEARCH.md` §"Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Helm (`helm lint`, `helm template`) + `kubeconform` + `renovate-config-validator` + Python `yaml.safe_load` smoke + existing `pytest` (Phase 3 reconcilers) |
| **Config file** | `charts/arr-stack/values.schema.json` (created Wave 1–3) |
| **Quick run command** | `helm lint charts/arr-stack/ -f examples/values-prod.yaml` |
| **Full suite command** | `helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml \| kubeconform -strict -ignore-missing-schemas -kubernetes-version 1.33.0` |
| **Estimated runtime** | ~30 seconds (lint + template + kubeconform locally) |

---

## Sampling Rate

- **After every task commit:** Run `helm lint charts/arr-stack/ -f examples/values-prod.yaml`
- **After every plan wave:** Run full suite (`helm template … | kubeconform -strict …`)
- **Before `/gsd-verify-work`:** Full suite green + Renovate validator green + byte-equivalence diff archived in `evidence/`
- **Max feedback latency:** ~30 seconds (lint+template+kubeconform). CI wall-clock target < 5 min for `chart-lint.yml`.

---

## Per-Task Verification Map

> Plans are not written yet — this table will be filled in (or refined) by `gsd-planner` per task.
> The rows below are seed entries derived from the requirement-to-test map in RESEARCH.md §"Validation Architecture".

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| REQ-umbrella-deployment | Umbrella chart renders valid K8s manifests for all 11 aliases | lint | `helm lint charts/arr-stack/ -f examples/values-prod.yaml` | ❌ W0 (chart not yet created) | ⬜ pending |
| REQ-helm-validation | Rendered manifests conform to K8s 1.33 API schema | conformance | `helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml \| kubeconform -strict -ignore-missing-schemas -kubernetes-version 1.33.0` | ❌ W0 | ⬜ pending |
| REQ-helm-validation | `values.yaml` parses against `values.schema.json` | schema | `helm lint` (auto-validates when `values.schema.json` exists) | ❌ W0 (schema not yet generated) | ⬜ pending |
| REQ-renovate-image-tracking | `renovate.json` is syntactically valid Renovate config | lint | `npx --yes renovate-config-validator renovate.json` | ❌ W0 | ⬜ pending |
| REQ-renovate-image-tracking | Every image in `values.yaml` carries a `# renovate: image=` annotation matching its `repository:` | regex contract | `tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml` (test script to add) | ❌ W0 | ⬜ pending |
| REQ-config-as-code | `files/arrconf.yml` parses as valid YAML | smoke | `python3 -c "import yaml; yaml.safe_load(open('charts/arr-stack/files/arrconf.yml'))"` | ❌ W0 (file created when port from my-kluster completes) | ⬜ pending |
| REQ-config-as-code | `files/configarr.yml` parses as valid YAML | smoke | `python3 -c "import yaml; yaml.safe_load(open('charts/arr-stack/files/configarr.yml'))"` | ❌ W0 | ⬜ pending |
| REQ-pr-to-cluster-latency | CronJob aliases (arrconf + configarr) render with `concurrencyPolicy: Forbid` and schedule `0 */4 * * *` | render assertion | `helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml \| yq 'select(.kind=="CronJob") \| {.metadata.name: {schedule: .spec.schedule, policy: .spec.concurrencyPolicy}}'` | ❌ W0 | ⬜ pending |
| REQ-pr-to-cluster-latency | End-to-end Renovate → arr-stack PR → my-kluster `targetRevision` PR → ArgoCD sync < 1 h | manual (operator) | n/a — D-04-PIN-04 SC#2 E2E target | manual only | ⬜ pending |
| REQ-readme-onboarding | README.md ships sections: Umbrella chart / Deploy / Operator runbook + < 30 min onboarding flow | manual (human review) | grep checks for required headings + UAT walkthrough | manual only | ⬜ pending |
| REQ-readme-onboarding | CLAUDE.md "Structure cible" rewritten to "Structure actuelle"; "Bootstrap (état actuel)" archived to historical | manual (human review) | grep for renamed headings | manual only | ⬜ pending |
| Goal — byte-equivalence | `helm template charts/arr-stack/ -f examples/values-prod.yaml` matches `argocd app manifests <unit-app>` for each of 10 unit Apps (modulo ArgoCD-injected labels/annotations) | diff contract | `tools/scripts/byte-equivalence-diff.sh evidence/argocd-manifests/ evidence/umbrella-rendered/` exits 0 | ❌ W0 (pre-snapshot script in Wave 0) | ⬜ pending |
| Goal — cutover safety | `arr-stack-app.yaml` ships **without** `automated:` block (operator drives first sync per D-04-CUTOVER-02) | grep contract | `! grep -q '^  automated:' my-kluster/argocd/argocd-apps/arr-stack-app.yaml` | ❌ W0 (file created in Wave 6) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Capture currently-running cluster image identifiers into `evidence/current-image-tags.txt` (qbittorrent / flaresolverr / cleanuparr) — D-04-PIN-02 operator checkpoint task.
- [ ] Run pre-cutover ADR-6 snapshot of all 10 unit ArgoCD Applications: `argocd app manifests <app> > evidence/argocd-manifests/<app>.yaml` for each of {sonarr, radarr, prowlarr, cleanuparr, configarr, qbittorrent, seerr, flaresolverr, jellyfin, arrconf}. Fallback: `kubectl get application <app> -n argocd -o jsonpath='{.status.sync.compareWith.target}'` if `argocd` CLI unavailable.
- [ ] Install `kubeconform` in CI runner — add step to `.github/workflows/chart-lint.yml` (no local install needed; CI is the verification surface).
- [ ] Install `losisin/helm-values-schema-json` plugin in CI runner — `helm plugin install https://github.com/losisin/helm-values-schema-json`.
- [ ] Add `helm repo add bjw-s-labs https://bjw-s-labs.github.io/helm-charts` step in `chart-lint.yml` before `helm dependency update`.
- [ ] Add `tools/scripts/check-renovate-annotations.sh` — fails if any `repository:` line in `values.yaml` lacks a preceding `# renovate: image=<same-repo>` annotation.
- [ ] Add `tools/scripts/byte-equivalence-diff.sh` — diff helper between `evidence/argocd-manifests/` baseline and `evidence/umbrella-rendered/` output (excludes ArgoCD-injected labels `argocd.argoproj.io/*`, annotations `kubectl.kubernetes.io/last-applied-configuration`, and resource versions).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cutover sync to live cluster | REQ-umbrella-deployment | Cannot be automated — requires operator to merge cross-repo PR, run `argocd app diff` + `argocd app sync --server-side`, verify health, then re-enable `automated.{selfHeal,prune}` in follow-up PR. | Follow D-04-CUTOVER-02 sequence in cutover plan (`05-cutover-PLAN.md` or equivalent). |
| Ingress smoke: 8 hostnames respond | Goal — no regression | Live HTTP probe against public Internet ingress. | `for h in sonarr radarr prowlarr cleanuparr configarr qbittorrent seerr flaresolverr jellyfin; do curl -I -s -o /dev/null -w "%{http_code} %{url_effective}\n" https://${h}.tgu.ovh; done` — all return 200/302/401 (oauth2-proxy challenge counts as healthy). |
| `/opt/media-stack/torrents` hostPath + `media-nas-pvc` NFS intact | Goal — no regression | Cluster state introspection on live nodes. | `kubectl -n selfhost exec deploy/qbittorrent -- ls /downloads`; `kubectl -n selfhost exec deploy/sonarr -- ls /media/series`. |
| Jellyfin internal auth preserved (no oauth2-proxy in front) | Goal — no regression | Compares ingress annotation set between unit App and umbrella render. | `kubectl -n selfhost get ingress jellyfin -o yaml \| grep -E 'oauth2-proxy\|auth-url'` returns **empty** before and after cutover. |
| arrconf CronJob smoke run post-cutover | REQ-pr-to-cluster-latency / REQ-config-as-code | Real API mutation against Sonarr/Radarr/Prowlarr; can't run in CI. | `kubectl -n selfhost create job --from=cronjob/arrconf arrconf-cutover-smoke; kubectl -n selfhost logs job/arrconf-cutover-smoke -f` — assert exit 0 + no resource churn (idempotence rule). |
| Renovate E2E (SC#2) | REQ-renovate-image-tracking + REQ-pr-to-cluster-latency | Real Renovate run via GitHub App; requires merged annotations + customManagers. | Wait up to 1 week post-cutover for first image bump PR; verify auto-merge passes; verify my-kluster `targetRevision` PR opens within the same Renovate cycle; verify ArgoCD sync < 1 h post-merge. Fallback per D-04-PIN-04: manually downgrade `cleanuparr` tag by one patch to force a bump. |
| README onboarding < 30 min walkthrough | REQ-readme-onboarding | Subjective human UX validation. | Operator (or trusted reviewer) runs `git clone` → bootstrap secrets → first `argocd app sync` following README only; measures wall-clock time. |

---

## Validation Sign-Off

- [ ] All tasks (once `gsd-planner` writes plans) have `<automated>` verify OR Wave 0 dependency declared
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (kubeconform install, schema plugin install, helm repo add, byte-equivalence diff script, renovate annotation check script)
- [ ] No watch-mode flags (CI must be one-shot)
- [ ] Feedback latency < 60 s (helm lint + template < 30 s; kubeconform < 10 s; renovate-config-validator < 20 s)
- [ ] Byte-equivalence diff archived in `evidence/byte-equivalence-diff.txt` before cutover (D-04-CUTOVER-03)
- [ ] `nyquist_compliant: true` set in frontmatter once plans + Wave 0 commit are in place

**Approval:** pending — set to `approved YYYY-MM-DD` after planner verification.
