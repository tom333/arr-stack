# Phase 18 — qBit POST credentials fallback — HUMAN-UAT

**Phase:** 18
**Status:** Pending operator validation
**Date:** 2026-05-24
**Triggered after:** ArgoCD sync of the chart with arrconf image `:0.10.1` (post-merge of the Phase 18 PR)

## Context

Phase 18 closes REQ-qbit-post-credentials (v0.5.0 milestone). The fix is small —
`_resolve_qbit_credentials_from_env()` injects `QBT_USER` / `QBT_PASS` env vars
into qBit `download_clients[]` fields[] for Sonarr AND Radarr, on both the
CREATE/POST and UPDATE/PUT paths. Before Phase 18, the generator emitted
`username: ""` / `password: ""` literals, leaving Sonarr/Radarr unable to
authenticate against qBittorrent unless the operator entered creds manually
in the UI (breaking "fully-as-code"). After Phase 18, those empty fields are
substituted from env at reconcile time; if env is ALSO empty, `ConfigError`
fail-fasts the run with the offending DC name in the message (D-18-FAIL-FAST-01,
CLI exit code 2).

Idempotence is acquired by construction — `differ._strip_redacted_fields` already
strips credential-name fields on both sides of `diff_models` via privacy
metadata (D-02.2-AUTH-REGRESSION carry-forward). The 2nd-apply `download_clients`
step produces 0 actions; SC#4 below is the cluster-side dispositive proof of
this property.

## Pre-requisites

- `arr-stack` PR for Phase 18 merged to `main`.
- `mathieudutour/github-tag-action` auto-tag CI ran on the merge commit and
  created `vX.Y.Z` (patch or minor depending on conventional-commit prefixes
  on the merged commits — operator inspects the GitHub Releases page).
- `arrconf-image.yml` GHCR build ran and pushed `:0.10.1`. Operator verifies
  via https://github.com/users/tom333/packages/container/arr-stack-arrconf/versions
  that the `0.10.1` tag exists in the registry.
- Renovate on `my-kluster` opened a PR bumping `targetRevision: vX.Y.Z` on
  `argocd/argocd-apps/arr-stack-app.yaml`. Operator merges it.
- ArgoCD sync completed:
  ```bash
  kubectl -n argocd get application arr-stack -o jsonpath='{.status.sync.status}'
  ```
  Returns `Synced`.
- `arrconf-env` SealedSecret still carries `QBT_USER` + `QBT_PASS` (baseline
  since Phase 5 — cluster-secrets-sealed memory note confirms this).

## Scenarios

### SC#1 (mandatory) — Generator preserves empty credential fields in arrconf.yml

**Pre-condition:** Phase 18 chart deployed (no operator-side YAML edit needed
for this scenario).

**Action:** None — visual confirmation that the chart-shipped ConfigMap still
carries the empty credential placeholders (the helper substitutes them at
reconcile time, not in the source YAML).

**Verification:**
```bash
kubectl -n selfhost get configmap arrconf-config -o jsonpath='{.data.arrconf\.yml}' \
  | grep -A 2 "username" | head -20
```
Or — for an in-cluster snapshot mounted in a debug pod:
```bash
kubectl -n selfhost get configmap arrconf-config -o yaml | grep -A 2 -B 2 "username"
```

**Expected:** No explicit `username: <value>` or `password: <value>` for qBit
`download_clients` entries — the generator's empty placeholders dominate (or
the fields[] entries are absent entirely, depending on what shipped in the
chart `arrconf.yml`).

**Pass criterion:** No live credentials appear in the rendered ConfigMap.
Real creds live ONLY in the `arrconf-env` SealedSecret.

### SC#2 (mandatory) — ArgoCD-triggered CronJob does NOT raise ConfigError

**Pre-condition:** SC#1 passed. `arrconf-env` SealedSecret has `QBT_USER` +
`QBT_PASS` populated (Phase 5 baseline).

**Action:** Wait for the next scheduled `arrconf` CronJob firing, OR trigger
it manually:
```bash
kubectl -n selfhost create job --from=cronjob/arrconf arrconf-uat-sc2-$(date +%s)
```

**Verification:**
```bash
POD=$(kubectl -n selfhost get pods -l job-name=arrconf-uat-sc2-* \
  -o jsonpath='{.items[0].metadata.name}' \
  --sort-by='.metadata.creationTimestamp' | tail -1)
kubectl -n selfhost logs "$POD" | grep -iE "(ConfigError|missing_env|exit code 2)"
```
**Expected:** Empty output (no error lines).

Then confirm sonarr + radarr completed:
```bash
kubectl -n selfhost logs "$POD" | grep -E "apply_complete"
```
Expected: `apply_complete` events for both `sonarr` and `radarr`.

**Pass criterion:** The Job pod exits 0. No `ConfigError` line in stderr. Logs
contain `apply_complete` events for sonarr + radarr.

### SC#3 (mandatory — dispositive) — Sonarr UI "Test" button on qBit DCs returns HTTP 200

**Pre-condition:** SC#2 passed.

**Action:** Open Sonarr UI at https://sonarr.tgu.ovh/settings/downloadclients.
For each of the qBit DCs visible (e.g. `qBittorrent-tv`, `qBittorrent-anime`,
`qBittorrent-family` — exact names depend on the generator output for the
configured Categories), click the "Test" button.

**Verification:** Each "Test" button turns green with a checkmark indicator.
This is qBittorrent confirming that the credentials Sonarr stored on POST
authenticate successfully against qBit's Web UI.

**Pass criterion:** All visible qBit DCs in Sonarr test green. This is the
dispositive proof that env-injection at POST time wrote real credentials into
Sonarr's stored DC config, which Sonarr then uses to authenticate against
qBittorrent.

**Repeat for Radarr:** https://radarr.tgu.ovh/settings/downloadclients — same
"Test" button check on each Radarr-side qBit DC (e.g. `qBittorrent-movies`,
`qBittorrent-anime`, `qBittorrent-family` — same caveat on naming).

### SC#4 (mandatory) — Second CronJob run emits 0 drift on download_clients

**Pre-condition:** SC#3 passed.

**Action:** Trigger a second manual run (or wait for the next scheduled firing):
```bash
kubectl -n selfhost create job --from=cronjob/arrconf arrconf-uat-sc4-$(date +%s)
```

**Verification:**
```bash
POD=$(kubectl -n selfhost get pods -l job-name=arrconf-uat-sc4-* \
  -o jsonpath='{.items[0].metadata.name}' \
  --sort-by='.metadata.creationTimestamp' | tail -1)
kubectl -n selfhost logs "$POD" \
  | grep -E '"step":\s*"download_clients"|plan_action' \
  | head -20
```
**Expected:** Either no `plan_action` events on the `download_clients` step
for sonarr + radarr, OR every `plan_action` shows `action=no-op` for the qBit
DCs. The 0.10.1 image strips credential-name fields symmetrically on both
sides of `diff_models` via privacy metadata; cluster's `"********"` mask vs
desired's env-injected value collapses to NO_OP.

**Pass criterion:** 0 `add` / `update` / `delete` actions on `download_clients`
for both Sonarr and Radarr on the 2nd run.

### SC#5 (optional follow-up) — Explicit YAML credentials override env

**Pre-condition:** SC#1-4 passed. Operator wants to validate the explicit-YAML
branch (env-ignore path).

**Action:** Edit `charts/arr-stack/files/arrconf.yml` to add `username` and
`password` overrides on one qBit DC entry (e.g. an explicit `fields[]` block
in the relevant `sonarr.main.download_clients[]` entry — overrides the
generator's empty default). Commit, PR, merge, ArgoCD sync.

**Verification:**
```bash
POD=$(kubectl -n selfhost get pods -l job-name=arrconf-* \
  -o jsonpath='{.items[0].metadata.name}' \
  --sort-by='.metadata.creationTimestamp' | tail -1)
kubectl -n selfhost logs "$POD" | grep -E "update_field|action=update" | head -5
```
**Expected:** The next reconcile cycle emits an `update`/`update_field` event
on the affected DC. Sonarr's "Test" button now returns ✗ (because the explicit
YAML value is wrong vs the real qBit password), proving the YAML value was
sent verbatim per the helper's "YAML wins" branch — env was correctly ignored.

**Pass criterion:** Explicit YAML values appear in the next reconcile cycle.
**Revert this change** after testing — restore generator-emitted empties for
normal operation.

## Result tracking

| Scenario | Status            | Date       | Notes |
|----------|-------------------|------------|-------|
| SC#1     | ✓ pass            | 2026-05-24 | ConfigMap carries no live qBit credentials. Cluster Synced on `:0.12.1`. |
| SC#2     | ✓ pass            | 2026-05-24 | After resolving the RPM 400 blocker (see Disposition below), pod exits 0, all 5 apps emit `apply_complete`. Step 6 download_clients runs: Sonarr+Radarr each add 5 qBit DCs with env-injected credentials. |
| SC#3     | ✓ pass            | 2026-05-24 | Dispositive — POST /api/v3/downloadclient/test returns HTTP 200 for ALL 9 Sonarr qBit DCs AND ALL 9 Radarr qBit DCs (incl. 5 new Phase-18-derived each side). Auth confirmed against live qBittorrent. |
| SC#4     | ✓ pass            | 2026-05-24 | 2nd reconcile produces 0 plan_actions on download_clients step (both sonarr+radarr). Sonarr+Radarr+qBittorrent emit no apply_complete because there were no actions to commit. Dispositive idempotence proof. |
| SC#5     | skipped (optional)| 2026-05-24 | Already covered by unit test `test_yaml_explicit_env_ignored`. Skipped to avoid mutating production YAML for a property proven by deterministic unit test. |

### Disposition

Phase 18 is **dispositively verified end-to-end** on the live cluster.

**Cluster-side blocker resolved mid-UAT.** SC#2 initially partial-passed (Phase 18 pre-flight gate verified, but Step 5 `_reconcile_remote_path_mappings` 400'd against Sonarr). The 400 was a pre-existing bug that pre-dated Phase 18 by ≥3 image versions — investigated and resolved via a separate debug session `.planning/debug/sonarr-rpm-400-categories.md`. Root cause: Sonarr v4 enforces `PathExistsValidator` on `LocalPath`; the v0.3.0 Categories cutover never created the matching `/data/<category>/` dirs on the qBittorrent volume. Operator-side fix (8× `mkdir -p` in the qBittorrent pod) unblocked the reconcile.

After the unblock, all SC#1-SC#4 passed in a single re-run of `arrconf apply`. SC#5 skipped (unit-test-covered).

**REQ-qbit-post-credentials is fully satisfied.** Phase 18 ready to mark complete in ROADMAP.md.

## Phase 18 close criteria

Phase 18 closes when SC#1, SC#2, SC#3, SC#4 all pass. SC#5 is optional and
non-blocking — it validates the "explicit YAML wins" branch, which is already
covered by the unit test `test_yaml_explicit_env_ignored` in
`tools/arrconf/tests/test_qbit_credentials_env_fallback.py`.

On close, update `.planning/STATE.md` and tick the Phase 18 checklist in
`.planning/ROADMAP.md`.
