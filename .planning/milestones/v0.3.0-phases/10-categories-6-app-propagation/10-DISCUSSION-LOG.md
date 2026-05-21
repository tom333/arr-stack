# Phase 10: Categories → 6-app propagation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-19
**Phase:** 10-categories-6-app-propagation
**Areas discussed:** Generation architecture, Override merge granularity, qBit/Sonarr/Radarr naming, Idempotence FP fix scope

---

## Generation architecture

| Option | Description | Selected |
|--------|-------------|----------|
| A — Pre-validation rewrite in config.py | RootConfig post-init merges Categories-derived into flat sections in place; reconcilers stay Categories-blind. Simplest reconciler diffs. Downsides: arrconf dump loses Categories→derived round-trip; debugging "why did this item appear" tangled with validation. | |
| B — Separate generators/categories.py module | Pure function emits per-app resource lists; reconcilers explicitly merge generated + manual. Maximum testability. Plan structure: 1 generator + 1 merger + 6 reconciler-wiring plans. Override semantics live in one place. | ✓ |
| C — In-reconciler generation | Each reconciler reads RootConfig.categories directly. Maximum parallelism but logic duplicated; override merge re-implemented per reconciler; FP risk if reconcilers diverge. | |

**User's choice:** B
**Notes:** Matches arrconf's existing pattern (pydantic at boundary, helpers in middle, reconcilers thin).

---

## Override merge granularity

| Option | Description | Selected |
|--------|-------------|----------|
| i — Per-resource toggle | If manual.<resource>.items non-empty → Categories generation skipped for that resource entirely. Simplest contract; one-line predicate. Operator escape hatch is "declare the full list manually for this one resource". | ✓ |
| ii — Per-item match-by-name | Categories items merge in; manual items with same name win. Granular but subtle silent override on name collision. Logging needs per-item merge_action events. | |
| iii — Per-field deep merge | Same name = field-by-field merge. Maximum flexibility but pydantic doesn't deep-merge natively. Hardest to debug. | |

**User's choice:** i
**Notes:** This is a transition layer planned for deprecation in REQ-categories-deprecation (v0.4.0+), so granular per-item merge would be over-engineering. Per-resource toggle + a clear log line gives operator full visibility.

---

## qBit / Sonarr / Radarr naming convention

### Question 1: qBit category naming

| Option | Description | Selected |
|--------|-------------|----------|
| Bare <name> | Drop <kind>- prefix from REQ-categories-qbit-propagation. Categories named exactly categories[i].name: series, series-emilie, films, etc. savePath stays /data/torrents/<name>. Update REQUIREMENTS.md wording. | ✓ |
| Literal <kind>-<name> | Honor REQ wording: series-series-emilie, movies-nouveaux-films. Disambiguates kind but redundant since 10 production names don't collide. | |
| Hybrid (bare name + kind tag) | Bare name + separate kind tracking. Not currently supported by qBit category schema. | |

**User's choice:** Bare <name>
**Notes:** REQUIREMENTS.md wording for REQ-categories-qbit-propagation needs a one-line edit to drop "<kind>-" prefix.

### Question 2: Sonarr/Radarr download_clients restructure

| Option | Description | Selected |
|--------|-------------|----------|
| 5 per category (REQ-aligned) | One download_client per Category. Sonarr-side: 5; Radarr-side: 5. tag_labels=[<name>], tvCategory=<name>. | ✓ |
| Keep 3 per profile | Categories generates only tags/root_folders/RPMs; the 3 manual download_clients fan out via tag_labels. Cluster migration smaller. Less aligned with REQ. | |

**User's choice:** 5 per category
**Notes:** Cluster-side content re-tagging (Sonarr UI bulk-edit + Radarr + qBit torrent categories) is operator manual step; arrconf only manages config-side.

---

## Idempotence FP fix scope

| Option | Description | Selected |
|--------|-------------|----------|
| Fix 3 enumerated FPs only | qBit categories (Phase 5 SC#5), Prowlarr app-sync (Phase 5), Seerr user (Phase 6 D-06-SEERR-USER-FP). One plan with 3 atomic commits + 3 regression tests. | ✓ |
| Fix 3 + audit pass across all 6 reconcilers | Add audit task: run apply twice against Phase 9 baseline, log surviving plan_action events. May surface 0-2 additional cases. | |
| Defer to a dedicated phase | Phase 10 ships only propagation; FP fix moves to Phase 10.1. SC#2 wording would need updating. | |

**User's choice:** Fix 3 enumerated FPs only
**Notes:** Same root cause (cluster returns more fields than arrconf models). Fix pattern = filter cluster GET to model.model_fields.keys() OR per-resource ALLOWLIST (mirror Jellyfin SERVER_CONFIG_ALLOWLIST). Planner picks one approach consistent across the 3 fixes.

---

## Claude's Discretion

- Plan/wave decomposition (proposed 3 waves with 9-10 plans; planner finalizes).
- Test layout (mirrors existing arrconf test conventions).
- Snapshot discipline (ADR-6 baseline before Wave 2 cluster-touch tests).
- Configarr quality-profile derivation path (locked: arrconf does NOT write configarr.yml;
  operator hand-edits it. arrconf only validates that union(categories[].profile) is a
  subset of {general, anime, family}, which Phase 9's Literal enum already enforces).
- Whether to fold Prowlarr FP-fix into the qBit reconciler plan or keep it separate
  (small enough to fold).

## Deferred Ideas

### To Phase 11 (already scoped)
- REQ-04-09-argocd-selfheal, REQ-cm-cruft-cleanup, REQ-ruff-format-ci-gate,
  REQ-paths-filter-arrconf, REQ-renovate-app-install, REQ-snapshot-redaction-harden,
  REQ-readme-onboarding-v030

### To v0.4.0+
- REQ-categories-deprecation (remove override-merge path; Categories become sole source of truth)
- REQ-bazarr-addition (7th *arr-stack app)
- Phase 8 ESO/Akeyless secret migration (deferred)
- Multi-instance Sonarr/Radarr (ADR-7 reconsideration if BDD saturates)

### Cluster-side content migration (operator manual step)
- Re-tag existing Sonarr series + Radarr movies + qBit torrents from v0.2.0 profile tags
  to one of the 5 new Category-named tags. Documented in CLAUDE.md migration runbook
  extension (Phase 9-D output + D-03f addition).
