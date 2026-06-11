---
phase: 30-cross-seed
audit_date: 2026-05-31
asvs_level: 1
block_on: high
threats_total: 11
threats_closed: 11
threats_open: 0
register_authored_at_plan_time: true
status: secured
---

# SECURITY.md — Phase 30 (cross-seed)

**Audit date:** 2026-05-31
**ASVS Level:** 1
**Auditor role:** gsd-security-auditor (adversarial stance)
**Phase:** 30 — cross-seed (plans 01-03)
**block_on:** high (open threats with mitigate disposition = BLOCKER)

---

## Threat Verification Summary

**Threats Closed:** 11/11
**Threats Open:** 0/11
**Unregistered Flags:** 0

---

## Threat Verification Detail

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-30-01 | Information Disclosure | mitigate | CLOSED | `config.js:9,13` — only `${QBT_USER}:${QBT_PASS}` and `apikey=${PROWLARR_API_KEY}` tokens present; grep for PLACEHOLDER returns 0 matches in both `intent.yml` and `config.js` |
| T-30-02 | Tampering | mitigate | CLOSED | `intent_config.py:30` — `CrossSeedConfig` has `model_config = ConfigDict(extra="forbid")`; `__main__.py:1016` — `--check` flag present on `generate` command |
| T-30-03 | Repudiation | accept | CLOSED | `generators/intent.py:48` — `json.dumps(..., sort_keys=True)`; `test_generate_cross_seed.py:24` — `test_generate_cross_seed_deterministic` enforces byte-identical output |
| T-30-04 | Information Disclosure | mitigate | CLOSED | `cross-seed-configmap.yaml:10` — renders via `.Files.Get "files/cross-seed/config.js"` (tokens only); `values.yaml:647-648,661-662` — initContainer and main container reference `arrconf-env` by name via `secretRef`; no inline secret literal anywhere in committed files |
| T-30-05 | Information Disclosure | mitigate | CLOSED | `values.yaml:709-710` — `config-resolved` volume is `type: emptyDir`; `values.yaml:640-645` — initContainer writes resolved file to `/config-resolved/config.js` (ephemeral emptyDir); PVC (`cross-seed-config`) mounts only at `/config` in the main container, never holds the resolved config.js |
| T-30-06 | Tampering | mitigate | CLOSED | `values.yaml:705` — `readOnly: true` on the `config-cm` ConfigMap volume mount into `config-init`; `config-resolved` emptyDir is a separate write target; initContainer never writes back to the ConfigMap volume |
| T-30-07 | Denial of Service | accept | CLOSED | `values.yaml:642-644` — `process.env.X \|\| ''` pattern used for all three tokens; documented accepted risk (T-30-07); operator pre-req in `30-OPERATOR-RUNBOOK.md` |
| T-30-08 | Elevation of Privilege | accept | CLOSED | `values.yaml:727-728` — `hostPath: /media/data/torrents`, `hostPathType: DirectoryOrCreate`; identical pattern as qBittorrent alias (established trust boundary); documented accepted risk |
| T-30-09 | Information Disclosure | mitigate | CLOSED | `30-OPERATOR-RUNBOOK.md:23-25,115` — references only key NAMES (`PROWLARR_API_KEY`, `QBT_USER`, `QBT_PASS`); step 6 explicitly warns operator not to paste resolved output; no secret values appear in any committed file |
| T-30-10 | Tampering | accept | CLOSED | `chart-lint.yml:48-49` — `[ ! -d ... ] && cp -r charts/arr-stack/charts/app-template "charts/arr-stack/charts/$alias"` idempotent guard; sources only the pinned `app-template-5.0.0.tgz` tarball; documented accepted risk |
| T-30-11 | Denial of Service | mitigate | CLOSED | `30-OPERATOR-RUNBOOK.md` sections 2 and 3 — PVC (`cross-seed-config`) and host dir (`mkdir -p /media/data/torrents/cross-seed`) listed as explicit BEFORE-sync gates; failure surfaces as Pending pod, not silent secret leakage |

---

## Accepted Risk Log

| Threat ID | Accepted Risk Description | Justification |
|-----------|--------------------------|---------------|
| T-30-03 | Generator non-determinism | `json.dumps(sort_keys=True)` provides byte-identical output; `test_generate_cross_seed_deterministic` enforces this property at test time. Accepted because determinism is enforced by code + test, not just policy. |
| T-30-07 | initContainer fails on empty secret keys | `process.env.X \|\| ''` yields empty string; cross-seed fails auth visibly in logs. Operator pre-req runbook (Plan 03) documents required keys. Accepted: visible failure mode, not silent data exfiltration. |
| T-30-08 | hostPath /media/data/torrents privilege surface | Identical hostPath as the existing qBittorrent alias (established trust boundary in production). Required for hardlink integrity (D-05). `DirectoryOrCreate` adds no new kernel-level privilege. |
| T-30-10 | CI alias unpack copy sources only app-template | `cp -r` sources the verified `app-template-5.0.0.tgz` (chart version pinned in Chart.yaml); idempotent `[ ! -d ]` guard prevents clobbering. Accepted: read-only CI validation, no secret handling. |

---

## Unregistered Flags

None. The SUMMARY.md `## Threat Flags` sections for plans 01-03 each explicitly state no new unmodeled trust boundaries were introduced beyond what is captured in the respective plan threat models.

---

## Files Verified

| File | Role in Audit |
|------|---------------|
| `charts/arr-stack/files/intent.yml` | T-30-01: token content verified (no PLACEHOLDER, no resolved secrets) |
| `charts/arr-stack/files/cross-seed/config.js` | T-30-01: generated artifact carries only `${...}` tokens |
| `charts/arr-stack/templates/cross-seed-configmap.yaml` | T-30-04: renders via `.Files.Get` (tokens only, no inline secrets) |
| `charts/arr-stack/values.yaml` (lines 619-733) | T-30-04, T-30-05, T-30-06, T-30-07, T-30-08: initContainer wiring, emptyDir, readOnly, envFrom |
| `charts/arr-stack/Chart.yaml` (line 54-57) | T-30-10: 12th alias `cross-seed` pinned at `app-template@5.0.0` |
| `.github/workflows/chart-lint.yml` (lines 40-50, 118-135) | T-30-10, T-30-11: alias unpack loop (12 aliases), threshold `< 12` |
| `tools/arrconf/arrconf/intent_config.py` (line 30) | T-30-02: `CrossSeedConfig` `extra="forbid"` |
| `tools/arrconf/arrconf/generators/intent.py` (line 48) | T-30-03: `sort_keys=True` |
| `tools/arrconf/arrconf/__main__.py` (line 1016) | T-30-02: `--check` drift gate |
| `tools/arrconf/tests/test_generate_cross_seed.py` (line 24) | T-30-03: `test_generate_cross_seed_deterministic` |
| `.planning/phases/30-cross-seed/30-OPERATOR-RUNBOOK.md` | T-30-09, T-30-11: key names only, BEFORE-sync gates documented |
