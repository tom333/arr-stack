---
phase: 12-categories-deprecation
plan: D
type: SUMMARY
status: complete
tasks_complete:
  - D.1
  - D.2
date: 2026-05-22
---

# Plan 12-D Summary — docs + pre-merge snapshot

## Task D.1 — CLAUDE.md deprecation section ✅

Added `## v0.3.0 → v0.4.0 deprecation` at H2 between `### Accumulated-bumps escape hatch` and `## Conventions Helm — umbrella chart`.

Content covers the 4 D-11 facts:

1. **Pourquoi ce changement** — `merge_with_manual` + flat `*.items` retired; generators in `arrconf/generators/categories.py` are the sole source.
2. **Sections supprimées** — verbatim list of the 11 YAML paths deleted from `arrconf.yml` (matches Plan B's edit).
3. **Erreur attendue** — the literal ValidationError block from `12-B-pydantic-yaml-schema-SUMMARY.md#Captured-D-13-ValidationError`. References the dispositive test `tools/arrconf/tests/test_config_validation.py::test_load_config_rejects_legacy_items_field`.
4. **Fix one-shot** — 5-step operator runbook (verify branch → diff local YAML → delete `items:` blocks → re-test dry-run → commit/push).

The `**État actuel**` line at the top of CLAUDE.md was also updated to reflect Phase 12 completion.

Commit: see git log for `docs(12-D): add v0.3.0 → v0.4.0 deprecation section to CLAUDE.md (D-11)`.

## Task D.2 — Pre-merge cluster snapshot ✅

Captured against the live cluster running image `:0.6.7` from a `git worktree`
pinned to `b371ace` (last pre-Plan-A commit). Committed as
`snapshots/before-phase-12-2026-05-22/` (85 files, 988 KB).

Steps actually performed:

1. `git worktree add /tmp/arr-stack-pre-12 b371ace`
2. `kubectl -n selfhost port-forward svc/{sonarr,radarr,qbittorrent,seerr,jellyfin}` on standard ports; `prowlarr` forwarded to `:19696` (local port 9696 was occupied by a host-side Prowlarr process) and `PROWLARR_URL` env overridden accordingly.
3. Secrets extracted from `kubectl -n selfhost get secret arrconf-env -o json` (sealed-secret-decrypted Opaque secret holding all 7 API key/credential values).
4. `tools/snapshot/snapshot.sh --output snapshots/before-phase-12-2026-05-22/` from the pre-Plan-A worktree — captured 84 redacted JSON files across 6 apps; auto-redaction applied for apiKey/password/token/webhookUrl/sessionKey.
5. `arrconf apply --dry-run` from the pre-Plan-A worktree against a localhost-rewritten copy of `arrconf.yml` (cluster-internal DNS replaced with localhost ports). Captured 111-line `dry-run-plan-actions-v030.log` with the v0.3.0 `merge_decision` events that Plan E's v040 log will NOT have — making the SC#5 diff a true cross-version measurement.
6. Redaction audit: `grep -rniE "(api[-_]?key|password|passkey|token|webhookurl|sessionkey).*:.*[a-zA-Z0-9]{16,}" | grep -v "<redacted>"` returned empty.
7. `cp -r` snapshot back to `/data/projets/perso/arr-stack/snapshots/`; committed as `snapshot(12): capture pre-merge v0.3.0 cluster state (D-14, ADR-6)`.
8. Port-forwards killed; pre-Plan-A worktree removed.

Note: the localhost-rewritten YAML lived under `.arrconf-snapshot/` in the
temporary worktree only — the committed `arrconf.yml` on main retains
cluster-internal DNS as before.

### Runbook used (kept for reproducibility)

The cleanest path was a worktree pinned to the last pre-Plan-A commit:

```bash
cd /data/projets/perso/arr-stack
git worktree add /tmp/arr-stack-pre-12 b371ace

# 5 standard port-forwards + prowlarr on 19696 (local port 9696 held by host Prowlarr)
kubectl -n selfhost port-forward svc/sonarr 8989:8989 &
kubectl -n selfhost port-forward svc/radarr 7878:7878 &
kubectl -n selfhost port-forward svc/prowlarr 19696:9696 &
kubectl -n selfhost port-forward svc/qbittorrent 8080:8080 &
kubectl -n selfhost port-forward svc/seerr 5055:5055 &
kubectl -n selfhost port-forward svc/jellyfin 8096:8096 &

# Decrypt secrets directly from the live K8s secret (sealed-secret-decrypted)
SECRET_JSON=$(kubectl -n selfhost get secret arrconf-env -o json)
for K in SONARR_API_KEY RADARR_API_KEY PROWLARR_API_KEY SEERR_API_KEY JELLYFIN_API_KEY QBT_USER QBT_PASS; do
  export $K=$(echo "$SECRET_JSON" | python3 -c "import json,sys,base64;d=json.load(sys.stdin)['data'];print(base64.b64decode(d['$K']).decode())")
done
export PROWLARR_URL=http://localhost:19696

DATE=$(date +%F)
cd /tmp/arr-stack-pre-12
tools/snapshot/snapshot.sh --output snapshots/before-phase-12-${DATE}/

# Rewrite cluster DNS to localhost for the dry-run only (committed YAML untouched)
mkdir -p .arrconf-snapshot
sed -E \
  -e 's|http://sonarr\.selfhost\.svc\.cluster\.local:8989|http://localhost:8989|g' \
  -e 's|http://radarr\.selfhost\.svc\.cluster\.local:7878|http://localhost:7878|g' \
  -e 's|http://prowlarr\.selfhost\.svc\.cluster\.local:9696|http://localhost:19696|g' \
  -e 's|http://qbittorrent\.selfhost\.svc\.cluster\.local:8080|http://localhost:8080|g' \
  -e 's|http://seerr\.selfhost\.svc\.cluster\.local:5055|http://localhost:5055|g' \
  -e 's|http://jellyfin\.selfhost\.svc\.cluster\.local:8096|http://localhost:8096|g' \
  charts/arr-stack/files/arrconf.yml > .arrconf-snapshot/arrconf-localhost.yml

cd tools/arrconf
uv run arrconf --config ../../.arrconf-snapshot/arrconf-localhost.yml apply --dry-run \
  > ../../snapshots/before-phase-12-${DATE}/dry-run-plan-actions-v030.log 2>&1

# Redaction audit
LEAKS=$(grep -rniE "(api[-_]?key|password|passkey|token|webhookurl|sessionkey).*:.*[a-zA-Z0-9]{16,}" \
  ../../snapshots/before-phase-12-${DATE}/ | grep -v "<redacted>" || true)
[ -z "$LEAKS" ] && echo "AUDIT CLEAN" || (echo "LEAK: $LEAKS"; false)

# Commit on main, then cleanup
cp -r ../../snapshots/before-phase-12-${DATE}/ /data/projets/perso/arr-stack/snapshots/
cd /data/projets/perso/arr-stack
git add snapshots/before-phase-12-${DATE}/
git commit -m "snapshot(12): capture pre-merge v0.3.0 cluster state (D-14, ADR-6)"

pkill -f "kubectl.*port-forward.*selfhost"
git worktree remove --force /tmp/arr-stack-pre-12
```

The recorded `dry-run-plan-actions-v030.log` is consumed by Plan E's SC#5 diff
against the post-merge `dry-run-plan-actions-v040.log`.

## SC#5 dispositive — what this snapshot anchors

Phase 12 requires both:
- **SC#3** — Plan C's `test_sweep` (in-CI dispositive) ✅ — verified by `cd tools/arrconf && uv run pytest tests/test_phase10_idempotence_sweep.py::test_sweep`.
- **SC#5** — live-cluster diff between pre-merge (this snapshot) and post-merge (Plan E's after-snapshot). The two logs must come from different code versions running against the cluster at different image states — that's what makes the diff a true v0.3.0-vs-v0.4.0 measurement, not a tautological same-code self-diff.

## Status

| Acceptance criterion | Status |
|---|---|
| `## v0.3.0 → v0.4.0 deprecation` section added | ✅ |
| 11 verbatim YAML paths cited | ✅ |
| D-13 ValidationError block (verbatim from Plan B SUMMARY) | ✅ |
| Cross-reference to `test_load_config_rejects_legacy_items_field` | ✅ |
| `merge_with_manual` mentioned in deprecation context | ✅ |
| `arrconf/generators/categories.py` mentioned | ✅ |
| `<PASTE-VERBATIM…>` placeholder replaced (no template leakage) | ✅ |
| `snapshots/before-phase-12-2026-05-22/` captured | ✅ (85 files, 988 KB) |
| Snapshot redaction sanity check | ✅ clean |
| Snapshot committed to git | ✅ `e99334d` |
| `dry-run-plan-actions-v030.log` captured | ✅ (111 lines, contains `merge_decision` events) |

## Handoff to Plan E

Plan E (Wave 4) requires operator action OUTSIDE this orchestrator: open the
phase PR, merge it, ensure the `v0.7.0` tag publishes via the auto-tag chain
(or push it manually per CLAUDE.md "Accumulated-bumps escape hatch" — multiple
0.6.x→0.7.0 co-bumps accumulated without intermediate pushes in this phase),
let ArgoCD pick up image `:0.7.0`, then re-run the snapshot script + dry-run
from the post-merge `main` tree to produce `snapshots/after-phase-12-YYYY-MM-DD/`
and `dry-run-plan-actions-v040.log`. Diff against this baseline; write
12-HUMAN-UAT.md and 12-VERIFICATION.md per Plan E's templates. The orchestrator
halts here because the PR-merge gate is fundamentally human.
