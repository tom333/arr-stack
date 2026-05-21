# Phase 9: Categories data model + chart initContainer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `09-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-05-18
**Phase:** 09-categories-data-model-chart-initcontainer
**Areas discussed:** Categories declaration table, initContainer architecture, initContainer image + pinning, Phase 9 / Phase 10 boundary on coexistence, Schema CI gate, CLAUDE.md migration runbook

---

## Categories declaration table

### Q1 — Series-side profile mapping (5 entries)

| Option | Description | Selected |
|--------|-------------|----------|
| series=general; emilie=general; thomas=general; garcons=family; zoe=family | Adults on general; kids on family; no anime here. | |
| series=general; emilie=general; thomas=general; garcons=family; zoe=anime | Same as above but Zoé is anime (Japanese animation library). | ✓ |
| series=general; emilie=general; thomas=anime; garcons=family; zoe=family | Thomas as anime watcher. | |
| Other | Type a different mapping. | |

**User's choice:** Option 2.
**Notes:** Zoé's bucket on `anime` enables native Seerr `animeTags` routing for her TVDB-anime requests in Phase 10.

### Q2 — Movies-side profile mapping (5 entries)

| Option | Description | Selected |
|--------|-------------|----------|
| films=general; nouveaux-films=general; films-enfants=family; films-animation-enfants=family; films-zoe=anime | Default heuristic — kid live-action + animation on family; Zoé on anime. | ✓ |
| films=general; nouveaux-films=general; films-enfants=family; films-animation-enfants=anime; films-zoe=family | films-animation-enfants treated as anime profile. | |
| films=general; nouveaux-films=general; films-enfants=family; films-animation-enfants=family; films-zoe=family | All kid-content on family; no anime on Radarr side. | |
| Other | Type a different mapping. | |

**User's choice:** Option 1.
**Notes:** films-zoe mirrors her series-zoe being `anime`.

### Q3 — `display` label convention

| Option | Description | Selected |
|--------|-------------|----------|
| Title Case French — 'Séries', 'Séries - Émilie', 'Films - Enfants', 'Films - Zoé' | Operator-facing French with accents and ' - ' separator. | ✓ |
| Lowercase slug-mirror — 'series', 'series-emilie', ... | display == name. | |
| French operator labels with kid markers — 'Séries générales', 'Séries Émilie', ... | More descriptive. | |
| Other | Type a different convention. | |

**User's choice:** Option 1.
**Notes:** Matches existing Jellyfin library names `Séries` and `Films`.

### Q4 — `base_path` shape

| Option | Description | Selected |
|--------|-------------|----------|
| `/media/<name>` strictly (mirror the slug) | Pydantic enforces `base_path == f'/media/{name}'`. | ✓ |
| `/media/<name>` with explicit override allowed | Escape hatch for migration. | |
| Free-form absolute path under `/media/` | Maximum flexibility. | |

**User's choice:** Option 1.
**Notes:** Strict mirror — pydantic validator at config load. Makes operator runbook copy-pasteable and Phase 10 mechanical.

---

## initContainer architecture

### Q5 — Architecture choice

| Option | Description | Selected |
|--------|-------------|----------|
| Standalone Helm-hooked Job | New `templates/categories-init-job.yaml`; one Job per release. | ✓ |
| Per-controller initContainer on each /media-mounting controller | Add to sonarr+radarr+jellyfin in values.yaml (3 runs). | |
| initContainer on existing arrconf CronJob pod | Reuse arrconf's CronJob; runs every 4h, not at install. | |

**User's choice:** Option 1.
**Notes:** Single audit trail; one Job per release; no per-pod-restart noise.

### Q6 — Hook lifecycle

| Option | Description | Selected |
|--------|-------------|----------|
| `pre-install,pre-upgrade` + `hook-delete-policy: before-hook-creation,hook-succeeded` | Fires before install/upgrade; cleans previous successful Jobs. | ✓ |
| `post-install,post-upgrade` instead | Runs after apps deployed. | |
| `pre-install,pre-upgrade` only, never delete (hook-succeeded only) | Keep all Jobs for audit. | |

**User's choice:** Option 1.
**Notes:** Failed Jobs persist for debugging.

### Q7 — Job source of truth

| Option | Description | Selected |
|--------|-------------|----------|
| Render via Helm `tpl` from values.yaml | values.yaml gets a list of base_paths; Job is a pure shell loop. | ✓ |
| Job reads mounted `arrconf-config` ConfigMap and parses arrconf.yml at runtime | Single source of truth (arrconf.yml). ConfigMap chicken-and-egg on pre-install. | |
| Duplicate in BOTH places (values.yaml + arrconf.yml) | Explicit duplication; CI guard required. | |

**User's choice:** Option 1.
**Notes:** Research is explicitly tasked (Open-for-research #1) with validating whether `.Files.Get "files/arrconf.yml" | fromYaml | dig "categories"` could replace the values-yaml-driven approach with a true single-source pattern, eliminating the sync gate.

### Q8 — Log format

| Option | Description | Selected |
|--------|-------------|----------|
| JSON-line per directory | `{"event":"media_dir_ensured","path":...,"created":...,"existed":...}` matches arrconf structlog. | ✓ |
| Plain text (`mkdir -p` default) | Simple shell output. | |
| Silent (only on error) | Cleanest log noise but hard to verify SC#3. | |

**User's choice:** Option 1.
**Notes:** Anti-leak grep already tuned for arrconf's JSON-line shape — no new exception needed.

---

## initContainer image + pinning

### Q9 — Image choice

| Option | Description | Selected |
|--------|-------------|----------|
| `busybox:1.36.1` pinned | Minimal (~5MB); `mkdir`/`printf` available. | ✓ |
| `alpine:3.20` | Full ash shell + find + chown; slightly larger. | |
| Reuse `lscr.io/linuxserver/sonarr` | Already pulled; but ~500MB. | |
| Build a tiny custom image | Maximum control; 2nd image to maintain. | |

**User's choice:** Option 1.

### Q10 — Renovate annotation

| Option | Description | Selected |
|--------|-------------|----------|
| Same `# renovate: image=...` pattern above the image line | Consistent with the 10 existing images. | ✓ |
| Pin in chart template directly | Hardcode `image: busybox:1.36.1` in the template. | |
| Allow operator override via values with sane default | Default in template; values can override. | |

**User's choice:** Option 1.

### Q11 — Pod security context

| Option | Description | Selected |
|--------|-------------|----------|
| `runAsUser: 1000, runAsGroup: 1000, fsGroup: 1000` | Matches PUID/PGID on linuxserver images. | ✓ |
| Run as root, then `chown 1000:1000` | Robust against NFS root_squash. | |
| Inherit pod-level defaults | Whatever the chart gives us. | |

**User's choice:** Option 1.
**Notes:** Research is explicitly tasked (Open-for-research #2) with validating the choice against live cluster NFS export config; fallback path documented.

---

## Phase 9 / Phase 10 boundary on coexistence

### Q12 — Phase 9 scope

| Option | Description | Selected |
|--------|-------------|----------|
| Schema + initContainer only; Phase 10 implements coexistence merge | Cleanest separation. SC#4 verifiable today. | ✓ |
| Schema + initContainer + load-into-RootConfig + emit deprecation warning | Add early signal log when both forms present. | |
| Schema + initContainer + minimal qBit propagation smoke test | One-app propagation in Phase 9. | |

**User's choice:** Option 1.
**Notes:** arrconf reconcilers in Phase 9 read `categories[]` for validation only; emit zero resources from it. Phase 10 ships both propagation AND merge logic.

### Q13 — Schema strictness

| Option | Description | Selected |
|--------|-------------|----------|
| Optional, default `[]` | Mirrors `default_factory=dict` pattern of other top-level fields. | ✓ |
| Required, must be non-empty | Forces operator awareness. Breaks existing tests. | |
| Required, may be empty | Half-strict; needs `categories: []` in fixtures. | |

**User's choice:** Option 1.

### Q14 — SC#4 evidence

| Option | Description | Selected |
|--------|-------------|----------|
| Compare `arrconf dump --dry-run` before/after with production arrconf.yml | Byte-level dispositive via `byte-equivalence-diff.sh`. | ✓ |
| Run full pytest reconciler suite — if green, no regression | Indirect; tests cover cases not byte-equivalence. | |
| Manual cluster apply --dry-run + eyeball | Slow, manual, risky without byte baseline. | |

**User's choice:** Option 1.
**Notes:** `tools/scripts/byte-equivalence-diff.sh` already exists for similar checks.

---

## Schema regen CI gate

### Q15 — Gate placement

| Option | Description | Selected |
|--------|-------------|----------|
| New pytest test in `tools/arrconf/tests/test_schema_gen.py` | Runs in existing `tests.yml`. Clear failure message. | ✓ |
| Standalone bash check in `chart-lint.yml` | Keeps the check out of pytest. | |
| Both | Belt-and-suspenders; redundant. | |

**User's choice:** Option 1.
**Notes:** Research is tasked (Open-for-research #4) with confirming JSON output stability across the locked pydantic version.

---

## CLAUDE.md operator migration runbook

### Q16 — Detail level

| Option | Description | Selected |
|--------|-------------|----------|
| Detailed runbook with exact `mv` commands per category | Pre-check, mapping table, exec, post-check, rollback. | ✓ |
| High-level outline only | List steps, no exact commands. | |
| Detailed runbook + bash helper script | Runbook + `tools/scripts/migrate-to-categories.sh`. | |

**User's choice:** Option 1.
**Notes:** Per-file operator-judgement makes a bash script counter-productive; explicit decision NO script in v0.3.0.

---

## Claude's Discretion

- Pydantic file layout: `tools/arrconf/arrconf/resources/categories.py` (new top-level resource module).
- Values.yaml key shape for the Job's basePaths list — planner picks, CI sync-gate is the only constraint.
- Job resource requests/limits (chart defaults / minimal — 10m CPU / 16Mi memory).
- Job `restartPolicy: OnFailure` with `backoffLimit: 2`.
- `activeDeadlineSeconds` ≈ 120s.

## Deferred Ideas

- `tools/scripts/migrate-to-categories.sh` helper script — explicitly NOT shipped in v0.3.0 (operator-judgement per file).
- All 6-app propagation work — Phase 10.
- Operational polish bundle (selfHeal/prune, CM cruft, ruff-format, paths-filter, Renovate App, snapshot redaction, README) — Phase 11.
- SuggestArr (SEED-001), Web UI, Bazarr, flat-section deprecation — v0.4.0+.
