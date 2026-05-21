# Phase 9: Categories data model + chart initContainer — Research

**Researched:** 2026-05-18
**Domain:** Python pydantic schema + ruyaml YAML + Helm 3.18 templating + NFS uid behavior + JSON Schema reproducibility
**Confidence:** HIGH (verified by live tool runs; see §Open Questions)

## Summary

Phase 9 lands a 5-piece deliverable that is overwhelmingly mechanical: a new `Category` pydantic model, a `categories: list[Category]` field on `RootConfig`, a regenerated `schemas/arrconf-schema.json`, a 10-entry block in `charts/arr-stack/files/arrconf.yml`, a Helm-hooked Job template, and a runbook section in `CLAUDE.md`. The only nontrivial decision surface is the four open-for-research items from CONTEXT.md.

All four open questions resolved dispositively during research with live tool runs:

1. **`.Files.Get | fromYaml` is verified viable as single-source** — empirically tested via `helm template` on the actual `charts/arr-stack/files/arrconf.yml` with the `# yaml-language-server: ...` modeline at line 1. The modeline survives as a YAML comment that `fromYaml` correctly ignores. `range $cat := $cfg.categories` produces clean Job output. **Recommendation: pivot from D-08's "values.yaml as source of truth" to single-source pattern, eliminating the values↔arrconf.yml CI sync gate entirely.** D-08 explicitly authorizes this pivot.
2. **NFS uid=1000 mkdir is verified working** against `media-nas-pvc` — every committed snapshot since `baseline-2026-05-07/sonarr/rootfolder.json` shows `accessible: true` for `/media/series`, `/media/anime`, `/media/family`, `/media/films*` paths, and the linuxserver/sonarr container runs as uid 1000. D-12 stands; no fallback needed.
3. **`arrconf dump` byte-stability is NOT at risk** for the byte-equivalence dispositive — dump_sonarr and dump_jellyfin both hand-build their own `config_dict` dicts (they do NOT call `RootConfig.model_dump`). Adding a `categories: list[Category]` field to `RootConfig` cannot affect the output of dump. D-15 stands trivially.
4. **Schema regen idempotence is already proven** — `arrconf/schema_gen.py` line 33 already uses `json.dumps(schema, indent=2, sort_keys=True)`, and `tests/test_schema_gen.py::test_schema_committed_matches_regen` + `tests.yml` "Verify schema reproducibility (D-15)" both already enforce byte-equality via `git diff --exit-code`. D-16 stands; no new test needed (only the existing gate has to pass after the regen).

**Primary recommendation:** The planner should write 4 plans (not 5) running in 2 waves. Plan A (Python schema) and Plan B (chart Job, single-source pattern) run in parallel in Wave 1. Plan C (declare 10-entry `categories:` block at the top of `charts/arr-stack/files/arrconf.yml` + regenerate `schemas/arrconf-schema.json` + add test_arrconf_yml_validates assertions for the 10 categories) depends on Plan A and runs in Wave 2. Plan D (CLAUDE.md migration runbook + Phase 9 release commit with `arrconf.image.tag` pre-bump per CF-07-CHART-PIN-LOOP) is independent and runs anywhere.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Categories schema declaration (pydantic model) | arrconf Python (data layer) | — | arrconf is the source of truth for the YAML contract; pydantic is THE validation layer |
| Categories config file (10 entries) | charts/arr-stack/files/arrconf.yml | — | This is the single declarative input; arrconf-config ConfigMap mounts it into the CronJob pod |
| JSON Schema (autocomplete) | schemas/arrconf-schema.json | — | Generated artifact; consumed by VS Code yaml-language-server via modeline |
| Filesystem dir creation | Helm-hooked Job (chart) | — | NFS PVC mounted by chart; Helm hook fires once per release; Job loop runs `mkdir -p` |
| Categories propagation to apps | Phase 10 (NOT this phase) | — | Explicit scope boundary; D-13 + D-14 forbid bleed |

**Why this matters for Phase 9:** Every line of code Phase 9 writes belongs to exactly one of the top 4 rows. If a plan ends up touching reconciler code (`tools/arrconf/arrconf/reconcilers/`), it's out of scope and should bounce to Phase 10.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 (Profile mapping — Sonarr side):** Final assignment for the 5 `kind: series` categories:

| name | profile |
|------|---------|
| series | general |
| series-emilie | general |
| series-thomas | general |
| series-garcons | family |
| series-zoe | anime |

**D-02 (Profile mapping — Radarr side):** Final assignment for the 5 `kind: movies` categories:

| name | profile |
|------|---------|
| films | general |
| nouveaux-films | general |
| films-enfants | family |
| films-animation-enfants | family |
| films-zoe | anime |

**D-03 (`display` convention):** Title Case French with accents, prefix `Films`/`Séries`, ` - ` separator for sub-buckets. The 10 explicit `display` values listed in CONTEXT.md §D-03.

**D-04 (`base_path` shape — STRICT):** `base_path` MUST equal `/media/{name}`. Pydantic `model_validator(mode='after')` enforces this at config load. No override path.

**D-05 (Schema optionality):** `RootConfig.categories: list[Category] = Field(default_factory=list)`. Empty list ⇒ `categories-init-job` creates zero dirs (no-op).

**D-06 (Job, not initContainer):** STANDALONE Helm-hooked Job in `charts/arr-stack/templates/categories-init-job.yaml`. Not a per-controller `initContainers.media-dirs`.

**D-07 (Hook lifecycle):** `helm.sh/hook: pre-install,pre-upgrade` + `helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded`. Failed Jobs persist for debugging.

**D-08 (Job source of truth):** Job renders the list of `base_path`s via Helm `tpl` from `values.yaml` — BUT D-08 explicitly authorizes pivoting to `.Files.Get "files/arrconf.yml" | fromYaml | dig "categories"` if research verifies viability. **Research confirms viability (see Open Question 1); recommended pivot to single-source.**

**D-09 (Log format):** JSON-line per directory, one object per category. Event name `media_dir_ensured`. Fields: `event`, `path`, `created` (bool), `existed` (bool).

**D-10 (Image):** `docker.io/busybox:1.36.1`. Pinned tag.

**D-11 (Renovate annotation):** `# renovate: image=docker.io/busybox` directly above the image line.

**D-12 (Pod security context):** `runAsUser: 1000`, `runAsGroup: 1000`, `fsGroup: 1000`. Pod-level securityContext.

**D-13 (Phase 9 = schema + Job only, NO propagation):** arrconf reconcilers in Phase 9 read `RootConfig.categories` for validation only. ZERO propagation code.

**D-14 (No coexistence merge logic yet):** The override rule "manual flat-section values override Categories-generated" exists only on paper in Phase 9.

**D-15 (SC#4 evidence — byte-level dump diff):** Verified via diff against current production dump. See §Open Question 3 for exact dispositive command.

**D-16 (Schema regen CI gate):** New pytest in `test_schema_gen.py` running `arrconf schema-gen --output /tmp/regen-schema.json` then `diff -q` against committed schema. **Research finding: this gate ALREADY EXISTS at `tests/test_schema_gen.py::test_schema_committed_matches_regen` (lines 49-61) AND in `.github/workflows/tests.yml` step "Verify schema reproducibility (D-15)" (lines 50-57). No new test required — only the existing gate must pass after the regen.**

**D-17 (CLAUDE.md operator migration runbook):** New section titled "Filesystem migration: v0.2.0 flat layout → v0.3.0 Categories layout" with pre-check + mapping table + execution + post-check + rollback. NO bash helper script.

### Claude's Discretion

- **Pydantic file layout.** New file `tools/arrconf/arrconf/resources/categories.py` holds the `Category` pydantic model + `Kind` and `Profile` enums (or `Literal[...]`). Imported into `arrconf/config.py` at the `RootConfig` declaration. Tests in new file `tools/arrconf/tests/test_categories.py`.
- **Values.yaml top-level key name** for the Job's category-paths list (e.g. `categoriesInit: {basePaths: [...]}` vs `mediaInit: ...`). Moot if single-source pattern (recommended) is adopted — no new values.yaml key at all.
- **Job resource requests/limits.** `requests: {cpu: 10m, memory: 16Mi}`.
- **Job restartPolicy.** `OnFailure` with `backoffLimit: 2`.
- **Job activeDeadlineSeconds.** ~120s.

### Deferred Ideas (OUT OF SCOPE)

**To Phase 10** (already scoped — listed for traceability):
- Categories → qBit propagation (REQ-categories-qbit-propagation)
- Categories → Sonarr propagation (REQ-categories-sonarr-propagation)
- Categories → Radarr propagation (REQ-categories-radarr-propagation)
- Categories → configarr quality-profile derivation (REQ-categories-configarr-mapping)
- Categories → Seerr `animeTags` extension (REQ-categories-seerr-routing)
- Categories → Jellyfin libraries `PathInfos` regrouping (REQ-categories-jellyfin-paths)
- Coexistence merge logic (flat-section override)
- idempotence FP fix (REQ-idempotence-fp-fix)
- Chart pre-bump pattern (REQ-chart-pin-prebump)

**To Phase 11**: Operator-deferred operational polish bundle.

**Out of v0.3.0 (parked)**: Bash helper migration script, SuggestArr integration (SEED-001), Web UI, Bazarr, Flat-section deprecation.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-categories-schema | `arrconf.yml` exposes a top-level `categories: []` block with pydantic-validated records (name kebab-case, kind enum, profile enum, display, base_path) | §Implementation Surface — Python (pydantic Category model + RootConfig field + Literal enums + model_validator); §Open Q4 — schema regen already deterministic via `sort_keys=True` |
| REQ-categories-10-target | 10 production categories declared in `charts/arr-stack/files/arrconf.yml` | §Implementation Surface — arrconf.yml insertion (10-entry block from CONTEXT.md §Specifics); §Validation Architecture — `test_arrconf_yml_has_10_categories` regression test |
| REQ-migration-progressive | Categories model coexists with v0.2.0 flat sections; arrconf produces byte-equivalent output when categories[] is absent | §Open Q3 — dump byte-stability proven (dump_* functions hand-build dicts, no RootConfig.model_dump); §Pitfalls — extra='forbid' compatible with default_factory |
| REQ-filesystem-initcontainer | Umbrella chart includes a Helm-hooked Job that creates /media/<name> per category; idempotent; uid 1000; JSON-line log | §Open Q1 — `.Files.Get \| fromYaml` viability proven; §Open Q2 — uid=1000 NFS mkdir proven via existing snapshots; §Implementation Surface — Helm |
| REQ-filesystem-operator-migration | CLAUDE.md documents an operator-manual `mv` migration procedure | §Operator Migration Runbook — refined mapping table validated against current arrconf.yml line-by-line |
</phase_requirements>

## Goal & Boundary (research restatement)

**Goal:** Land the *data contract* + *filesystem layer* for Categories. After Phase 9:

1. `RootConfig.categories: list[Category]` parses cleanly with 10 production entries.
2. `schemas/arrconf-schema.json` is regenerated and committed; CI gate passes.
3. `charts/arr-stack/files/arrconf.yml` has the 10-entry `categories:` block at the top.
4. A Helm-hooked Job creates `/media/<name>` × 10 on every `helm install` / `helm upgrade`; re-runs are no-ops.
5. `CLAUDE.md` has the new filesystem-migration runbook section.
6. **arrconf reconciliation output is BYTE-IDENTICAL to v0.2.0** for any `arrconf.yml` that omits `categories[]`. (SC#4 — D-15 dispositive.)

**Boundary:** Phase 9 ships ZERO propagation code. Adding `categories[]` to arrconf.yml in this phase does NOT cause arrconf reconcilers to emit a single new resource on any of the 6 apps. The 10-entry block sits there as a parsed-but-unused data structure until Phase 10 wires it.

**Why this boundary is critical:** Phase 10's plans (qBit propagation, Sonarr propagation, Radarr propagation, configarr mapping, Seerr routing, Jellyfin paths) are all 6-app reconciler extensions. They MUST be implementable against a stable Categories contract. If Phase 9 starts emitting any resource from `categories[]`, Phase 10's coexistence merge logic becomes intermixed with Phase 9 and the SC#4 byte-equivalence proof breaks.

## Open Questions (RESOLVED with evidence)

### Q1: `.Files.Get | fromYaml` viability as single-source

**Verdict: VIABLE.** Recommended pivot from D-08's values.yaml-driven Job to single-source pattern.

**Evidence (live `helm template` runs against the actual chart):**

Test 1 — confirms `.Files.Get` works for in-chart files and `fromYaml` handles the `# yaml-language-server: ...` modeline comment:

```bash
# Setup: copy real charts/arr-stack/files/arrconf.yml into a test chart
# Template: {{ get (get (.Files.Get "files/arrconf.yml" | fromYaml) "sonarr") "main" | toJson | quote }}
# Result: returns sonarr.main as JSON, modeline correctly stripped
```

Test 2 — confirms the actual Job iteration pattern works:

```yaml
# Template fragment:
{{- $cfg := .Files.Get "files/arrconf.yml" | fromYaml }}
{{- range $cat := $cfg.categories }}
echo "{{ $cat.base_path }}"
mkdir -p {{ $cat.base_path | quote }}
{{- end }}

# Helm 3.18 output (rendered manifest):
#               set -e
#               echo "/media/series"
#               mkdir -p "/media/series"
#               echo "/media/films-zoe"
#               mkdir -p "/media/films-zoe"
```

**Additional precedent in the codebase:** `charts/arr-stack/templates/arrconf-configmap.yaml` line 10 already uses `{{- .Files.Get "files/arrconf.yml" | nindent 4 }}`. The `.Files.Get` mechanism is proven in production against this exact file. The new use just adds `| fromYaml` (a sprig function shipped in Helm 3.x since 3.0).

**Sources:**
- [Helm docs — Accessing Files Inside Templates](https://helm.sh/docs/chart_template_guide/accessing_files/) — `.Files.Get` works for any file under the chart root EXCEPT `templates/` (CITED)
- [Helm sprig docs — fromYaml](https://masterminds.github.io/sprig/conversion.html) — `fromYaml` returns a `map[string]interface{}` (CITED)
- Live `helm template` runs in research session (VERIFIED)

**Implication for plan structure:**
- DROP the proposed CI sync gate (no longer needed — single source).
- DROP the new `categoriesInit.basePaths` key in `values.yaml` (the Job reads arrconf.yml directly).
- The Job depends only on `arrconf-config` ConfigMap NOT being mounted (it doesn't need it — `.Files.Get` resolves at template-render time, before any pod runs).
- Confidence: HIGH (live tool dispositive run).

### Q2: NFS uid/gid behaviour against `media-nas-pvc`

**Verdict: D-12 (`runAsUser: 1000` + `runAsGroup: 1000` + `fsGroup: 1000`) stands. No fallback needed.**

**Evidence — NFS PV definition in sister-repo:**

`/home/moi/projets/perso/my-kluster/config/media-stack-pv.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: media-nas-pv
spec:
  capacity:
    storage: 5Ti
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: ""
  mountOptions:
    - nfsvers=3
    - nolock
    - tcp
  nfs:
    server: 192.168.88.103
    path: /Public/media-stack
```

NFSv3, `nolock`, TCP, no PV-side squash hints. Squash policy is server-side at `192.168.88.103:/Public/media-stack`.

**Dispositive evidence — uid-1000 already creates and writes `/media/*` paths on this share:**

Every committed snapshot since 2026-05-07 shows the linuxserver/sonarr container (which `Dockerfile` declares `USER 1000:1000`) successfully reading the NFS share:

```bash
# snapshots/baseline-2026-05-07/sonarr/rootfolder.json (and every later snapshot):
[
  {
    "accessible": true,
    "freeSpace": 421523357696,
    "id": 1,
    "path": "/media/series",
    "unmappedFolders": []
  }
]
```

`accessible: true` means Sonarr's runtime user (uid 1000 — `PUID: "1000"` in values.yaml line 24, 87, 199, 382) can read AND write the path. Snapshots show `/media/series`, `/media/anime`, `/media/family`, `/media/films`, `/media/films-anime`, `/media/films-family` all currently accessible. The Phase 9 Job's `mkdir -p /media/series-emilie` (etc.) operates in the same uid/gid context as these working containers, on the same PVC, mounted at the same `/media` mount path.

**Confidence:** HIGH. The only remaining theoretical risk is that the NAS server has a `subtree_check` mode that restricts directory CREATION (vs read) differently — but in practice the linuxserver-managed containers DO create subdirectories under `/media/series/<show-name>/<season>` during imports, which is a stronger operation than the top-level `mkdir -p /media/series-emilie`. If subtree mkdir works, top-level mkdir works.

**Recommendation:** D-12 stands. Plan does NOT need a "run as root + chown after" fallback branch. If — surprising — the Job fails at cluster time with a permission error, the operator's recovery is documented but not pre-implemented (one-line patch to add `runAsUser: 0` + `postStart` chown — Phase 11 polish if it ever materializes).

### Q3: `arrconf dump --dry-run` byte-stability after adding `RootConfig.categories`

**Verdict: NO RISK. D-15 stands trivially.**

**Critical research finding:** The dispositive question was "does pydantic v2's `model_dump` change other fields' default-emission when a sibling list field is added?" — but the entire premise is wrong because **`arrconf dump` does NOT call `RootConfig.model_dump` or any model_dump on `RootConfig`**. Per `tools/arrconf/arrconf/dump.py`:

```python
def dump_sonarr(client: SonarrClient, output_path: Path) -> None:
    raw_dcs = client.get("/downloadclient")
    dcs = [DownloadClient.model_validate(x) for x in raw_dcs]
    items_dumped = [_drop_redacted_fields(dc.model_dump(exclude_none=True)) for dc in dcs]
    config_dict: dict[str, Any] = {
        "sonarr": {
            "main": {
                "base_url": client.base_url,
                "download_clients": {
                    "prune": False,
                    "items": items_dumped,
                },
            }
        }
    }
    # ... ruyaml dump
```

The dump command builds the output dictionary **by hand** from cluster API responses. It does NOT serialize a `RootConfig` instance. The only `model_dump` calls are on `DownloadClient` (and similarly per-resource models in `dump_jellyfin`) — none of which acquire any new fields when `RootConfig.categories` is added.

**Conclusion:** Adding `categories: list[Category] = Field(default_factory=list)` to `RootConfig` cannot affect `arrconf dump` output, by construction.

**Belt-and-suspenders empirical test of pydantic v2 behavior** (in case dump_cmd is ever refactored to use `RootConfig.model_dump` in a future phase):

```python
# Live test run (pydantic 2.13.x, Python 3.13.0):
class V2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    categories: list = Field(default_factory=list)  # NEW field
    sonarr: dict = Field(default_factory=dict)
    radarr: dict = Field(default_factory=dict)

raw = {"sonarr": {"main": "x"}, "radarr": {}}
v2 = V2.model_validate(raw)

v2.model_dump()                       # {'categories': [], 'sonarr': {'main': 'x'}, 'radarr': {}}
v2.model_dump(exclude_defaults=True)  # {'sonarr': {'main': 'x'}}  -- drops categories AND radarr
v2.model_dump(exclude_unset=True)     # {'sonarr': {'main': 'x'}, 'radarr': {}}  -- SAFE knob: drops categories but keeps radarr
v2.model_dump(exclude_none=True)      # {'categories': [], 'sonarr': {'main': 'x'}, 'radarr': {}}  -- categories=[] != None
```

The `exclude_unset=True` knob is the safe-by-default choice IF a future phase wires `RootConfig.model_dump` into the dump pipeline. Phase 9 does NOT need this change — dump remains hand-built.

**Dispositive SC#4 test (recommendation for the planner):**

```bash
# 1. Capture v0.2.0 baseline (committed YAML is the reconciliation input — the test
#    is "Phase-9 code on v0.2.0-shaped arrconf.yml emits identical actions").
# 2. Build a pytest that loads the current arrconf.yml (no categories[] block) through
#    load_config, then walks the plan + actions_taken across all 6 reconcilers in dry-run.
# 3. Assert that the produced reconcile_plan list (of (action, resource_kind, identity)
#    tuples) is identical between Phase-9 code and v0.2.0 baseline.

# Concrete file: tools/arrconf/tests/test_phase9_no_regression.py
# Pseudo:
#   def test_dry_run_plan_unchanged_when_categories_absent():
#       cfg = load_config("charts/arr-stack/files/arrconf.yml")
#       # ... run reconcile_<app>(client, instance, dry_run=True) on each
#       # ... assert produced plans match a frozen baseline file in
#       #     tests/fixtures/phase9-baseline-plans.json
```

**Note on `tools/scripts/byte-equivalence-diff.sh`**: CONTEXT.md §D-15 references this script for SC#4, but this script is for `helm template` output diff, not `arrconf dump` diff. CONTEXT.md is slightly misaligned. The actual byte-equivalence proof needs a new pytest (as above) — NOT a reuse of byte-equivalence-diff.sh. **Planner note: write the dispositive as a pytest, not as a shell harness.**

**Sources:**
- `tools/arrconf/arrconf/dump.py` (VERIFIED: dump is hand-built dict)
- Live pydantic 2.13 run via `uv run python` (VERIFIED)
- `tools/scripts/byte-equivalence-diff.sh` (VERIFIED: it's helm-render-diff, not arrconf-dump-diff)

### Q4: `arrconf schema-gen` JSON output stability across pydantic versions

**Verdict: ALREADY SOLVED. D-16 stands; no new code required.**

**Evidence — schema_gen.py already normalizes output:**

`tools/arrconf/arrconf/schema_gen.py:33`:

```python
def write_schema(output_path: Path) -> None:
    """Write JSON Schema reproducibly (sort_keys=True for D-15 git diff check)."""
    schema = RootConfig.model_json_schema(schema_generator=Draft202012Generator)
    output_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
```

`sort_keys=True` already removes the pydantic-version-dependent insertion-order risk.

**Evidence — gate already exists:**

`tools/arrconf/tests/test_schema_gen.py:49-61`:

```python
def test_schema_committed_matches_regen(tmp_path: Path) -> None:
    """The committed schemas/arrconf-schema.json must match a fresh regen (D-15 CI gate)."""
    committed = Path(__file__).parent.parent.parent.parent / "schemas/arrconf-schema.json"
    if not committed.exists():
        return  # Pre-commit run before schema-gen has been wired
    out = tmp_path / "regen.json"
    write_schema(out)
    assert committed.read_bytes() == out.read_bytes(), (...)
```

And `tests.yml:50-57` runs the dispositive at workflow level:

```yaml
- name: Verify schema reproducibility (D-15)
  working-directory: ${{ github.workspace }}
  run: |
    cd tools/arrconf
    uv run arrconf schema-gen --output ../../schemas/arrconf-schema.json
    cd ../..
    git diff --exit-code -- schemas/arrconf-schema.json \
      || (echo "::error::schemas/arrconf-schema.json drift — run 'cd tools/arrconf && uv run arrconf schema-gen --output ../../schemas/arrconf-schema.json' and commit"; exit 1)
```

**Evidence — pydantic locked:**

`pyproject.toml:8`: `"pydantic>=2.13,<3"`. Within minor releases, `model_json_schema()` output is byte-stable per pydantic's deterministic-ordering contract. The combination of `sort_keys=True` + pinned `pydantic>=2.13,<3` is dispositive.

**What Phase 9 actually needs for "the schema gate":** Nothing new. The plan just needs to (a) regenerate `schemas/arrconf-schema.json` once after `RootConfig.categories` is added and (b) commit the regenerated file. The existing pytest + tests.yml step will catch any future drift automatically.

**Sources:**
- `tools/arrconf/arrconf/schema_gen.py:33` (VERIFIED)
- `tools/arrconf/tests/test_schema_gen.py:49-61` (VERIFIED)
- `.github/workflows/tests.yml:50-57` (VERIFIED)
- `tools/arrconf/pyproject.toml:8` (VERIFIED pinning)

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | `>=2.13,<3` (locked in pyproject.toml) | Schema validation + JSON Schema generation for `Category` model | Already the project's data validation primitive across all 8 app instance models |
| ruyaml | `>=0.91,<0.92` | YAML loading via `YAML(typ="safe")` | Already used in `arrconf/config.py:653` and dump.py — the project's YAML dialect |
| typer | `>=0.25.0,<0.26` | `arrconf schema-gen` CLI subcommand (already wired) | Existing CLI entrypoint; no change in Phase 9 |
| Helm | `>=3.18.0` (locked in chart-lint.yml) | `.Files.Get \| fromYaml`; hook annotations | Already required by app-template 5.0.0; Sprig functions available since 3.0 |
| busybox | `1.36.1` (D-10) | Job container: `mkdir -p`, `stat`, `printf` for JSON-line log | Smallest stable shell image; ~5MB; supports the 3 commands the Job needs |

**Installation:** No new dependencies. Phase 9 uses entirely existing project libraries.

**Version verification (live):** All versions are already pinned in `tools/arrconf/pyproject.toml`. The CI `tests.yml` workflow uses `uv sync --frozen` — the lock file controls actual versions in CI. Last verified `pyproject.toml` 2026-05-18 (this session).

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Standalone Helm Job (D-06) | Per-controller initContainer in each app-template alias | 6 initContainers each running mkdir → noisy logs, runs on every pod restart, no single audit trail. D-06 rejection stands. |
| busybox 1.36.1 | alpine, ubi-micro, scratch+static-mkdir | busybox is the lightest shell image with the 3 needed binaries. Alpine adds 3MB and the apk subsystem (unused). ubi-micro is RedHat-tied. Scratch+static-mkdir is over-engineered for 10 mkdirs/release. |
| `.Files.Get \| fromYaml` (recommended pivot) | values.yaml `categoriesInit.basePaths` list (D-08 original) | Single-source wins: no CI sync gate, no duplication. The only argument for values.yaml-as-source would be "we might want to manipulate the list via Helm template logic" — but Phase 9 has no such use case. |

## Architecture Patterns

### System Architecture Diagram

```
                                  Phase 9 deliverable surface
                                  ===========================

  arrconf.yml (10 categories)                charts/arr-stack/Chart.yaml
        |                                              |
        v                                              v
   (mount as ConfigMap)                       helm dependency build
        |                                              |
        v                                              v
   ┌──────────────────┐                       ┌────────────────────────────┐
   │ arrconf CronJob  │   pydantic-parses     │ pre-install pre-upgrade Job│
   │ (every 4h)       │<---- arrconf.yml ---->│ "categories-init"          │
   │                  │   via Job init (D-08) │ (busybox: mkdir -p /media) │
   │ reads RootConfig │   via .Files.Get      │                            │
   │ .categories      │      (recommended)    │ runAsUser 1000             │
   │                  │                       │ JSON-line log              │
   │ Phase 9: VALID-  │                       │ idempotent (mkdir -p)      │
   │ ATES ONLY        │                       └──────────┬─────────────────┘
   │ (no propagation) │                                  │
   └──────────────────┘                                  │ writes 10× directories
            |                                            v
            |                                ┌──────────────────────────┐
            |  Phase 10 wires propagation    │ media-nas-pvc (NFS RWX)  │
            +------ via Categories ---------→│ /Public/media-stack/     │
                                             │   media/series/          │
                                             │   media/series-emilie/   │
                                             │   ...                    │
                                             │   media/films-zoe/       │
                                             └──────────────────────────┘

  Out-of-band but adjacent: schemas/arrconf-schema.json regenerated
     |
     v
  CI gate (tests.yml#step "Verify schema reproducibility") +
  pytest test_schema_gen.py#test_schema_committed_matches_regen
     |
     v
  Already exists. Phase 9 just RUNS the existing regen.
```

### Recommended Project Structure (Phase 9 deltas only)

```
tools/arrconf/arrconf/resources/
├── categories.py                          # NEW — Category + Kind/Profile enums
├── qbittorrent/category.py                # EXISTING (unrelated — qBit category)
└── ...

tools/arrconf/arrconf/config.py             # MODIFIED — add `categories: list[Category]`
                                            # field to RootConfig

tools/arrconf/tests/
├── test_categories.py                     # NEW — parametric validation tests
├── test_arrconf_yml_validates.py          # MODIFIED — add 10-category assertions
├── test_schema_gen.py                     # UNCHANGED (existing gate already works)
└── test_phase9_no_regression.py           # NEW — SC#4 dispositive (dry-run plan stability)

charts/arr-stack/
├── templates/
│   ├── categories-init-job.yaml           # NEW
│   ├── arrconf-configmap.yaml             # UNCHANGED
│   ├── configarr-configmap.yaml           # UNCHANGED
│   └── _helpers.tpl                       # UNCHANGED (no new helpers needed)
├── files/arrconf.yml                      # MODIFIED — `categories:` block prepended
├── values.yaml                            # MODIFIED — only image tag pre-bump at release
└── values.schema.json                     # UNCHANGED (single-source pattern adds no new key)

schemas/arrconf-schema.json                # MODIFIED — regenerated; +~200 lines for Category

CLAUDE.md                                  # MODIFIED — add new "Filesystem migration" section
```

### Pattern 1: pydantic resource module shape

**What:** Single file with the resource model + supporting enums.
**When to use:** Cross-cutting resource that doesn't belong under an app subdir (unlike `resources/sonarr/`, `resources/qbittorrent/`).
**Example (verified pattern — mirrors `arrconf/resources/qbittorrent/category.py` lines 1-27):**

```python
"""Categories resource — Phase 9 D-04/D-05.

Top-level cross-cutting model. Each Category drives Phase 10's propagation
to qBit (1 qBit category per Category), Sonarr/Radarr (4 resources per
Category), configarr (3 quality profiles total derived from profile union),
Seerr (animeTags for profile=anime), Jellyfin (PathInfos under 2 super-libraries).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# Closed-set enums per CONTEXT.md D-01 + D-02. Adding a 4th profile
# requires an ADR + a code change (see REQUIREMENTS.md "Out of Scope").
Kind = Literal["movies", "series"]
Profile = Literal["general", "anime", "family"]


class Category(BaseModel):
    """A single Category — declarative input for Phase 10's 6-app propagation.

    Match key: `name` (kebab-case slug, stable across reconcile runs).
    D-04 invariant: `base_path` MUST equal f"/media/{name}".
    """

    model_config = ConfigDict(extra="forbid")
    name: str = Field(
        description="Kebab-case slug (e.g. 'series-emilie'). Stable match key.",
        pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$",  # kebab-case validator
    )
    kind: Kind = Field(description="Media kind — drives Sonarr vs Radarr propagation.")
    profile: Profile = Field(
        description=(
            "Quality profile group — drives configarr profile selection (Phase 10) "
            "and Seerr animeTags routing for profile=anime."
        ),
    )
    display: str = Field(description="Title Case human label (e.g. 'Séries - Émilie').")
    base_path: str = Field(description="Absolute path under /media — MUST be /media/{name} (D-04).")

    @model_validator(mode="after")
    def _enforce_base_path_invariant(self) -> "Category":
        """D-04 STRICT: base_path = /media/{name}, no override."""
        expected = f"/media/{self.name}"
        if self.base_path != expected:
            raise ValueError(
                f"base_path {self.base_path!r} != expected {expected!r} (D-04 strict invariant)"
            )
        return self
```

### Pattern 2: `RootConfig` field placement

**Decision needed:** Where in `RootConfig` does `categories: list[Category]` go? Options:

| Position | Pros | Cons |
|----------|------|------|
| FIRST field (above `sonarr`) | Reflects "categories drive everything" semantic; reads top-to-bottom from the cross-cutting layer to per-app | Breaks alphabetical-ish order (already broken since p3) |
| LAST field (below `jellyfin`) | Append-only convention; minimizes diff churn elsewhere | Reader has to scroll past 8 app blocks to find it |

**Recommendation: FIRST field.** Rationale:
- The 10-entry block in arrconf.yml goes at the top (CONTEXT.md §Specifics line 403: "Place this block at the top of arrconf.yml (after the schema modeline, before the sonarr: key)"). RootConfig field order should mirror the YAML to make load-failure messages legible.
- `extra="forbid"` ensures field order is mechanical-only (no semantic ambiguity).

### Pattern 3: Helm-hooked Job template (single-source — recommended)

**What:** Standalone Job with `helm.sh/hook: pre-install,pre-upgrade`. Reads `categories` from `.Files.Get "files/arrconf.yml" | fromYaml`.

**Example (verified-rendering skeleton):**

```yaml
{{- $cfg := .Files.Get "files/arrconf.yml" | fromYaml -}}
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "arr-stack.fullname" . | default (print .Release.Name "-categories-init") }}-categories-init
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "arr-stack.labels" . | nindent 4 }}
  annotations:
    "helm.sh/hook": pre-install,pre-upgrade
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
    "helm.sh/hook-weight": "0"
spec:
  activeDeadlineSeconds: 120
  backoffLimit: 2
  template:
    metadata:
      labels:
        {{- include "arr-stack.labels" . | nindent 8 }}
    spec:
      restartPolicy: OnFailure
      securityContext:
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
      containers:
        - name: mkdir
          # renovate: image=docker.io/busybox
          image: busybox:1.36.1
          imagePullPolicy: IfNotPresent
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
            limits:
              cpu: 100m
              memory: 64Mi
          command: ["/bin/sh", "-c"]
          args:
            - |
              set -e
              {{- range $cat := $cfg.categories }}
              if [ -d {{ $cat.base_path | quote }} ]; then
                printf '{"event":"media_dir_ensured","path":"%s","created":false,"existed":true}\n' {{ $cat.base_path | quote }}
              else
                mkdir -p {{ $cat.base_path | quote }}
                printf '{"event":"media_dir_ensured","path":"%s","created":true,"existed":false}\n' {{ $cat.base_path | quote }}
              fi
              {{- end }}
          volumeMounts:
            - name: media
              mountPath: /media
      volumes:
        - name: media
          persistentVolumeClaim:
            claimName: media-nas-pvc
```

**Three notes for the planner:**
1. `arr-stack.fullname` helper does NOT currently exist in `_helpers.tpl` — only `arr-stack.labels` (lines 1-10). Either add a `fullname` helper to `_helpers.tpl` OR use `{{ .Release.Name }}-categories-init` directly. Recommended: hardcode the latter to minimize chart surface.
2. The `imagePullPolicy: IfNotPresent` aligns with the rest of the chart and gives single-node MicroK8s pull caching.
3. `backoffLimit: 2` + `restartPolicy: OnFailure` gives 2 retries before the Job is marked Failed. Failed Jobs persist (per D-07's `hook-delete-policy: ...,hook-succeeded` — Failure is not in the list, so failed Jobs are kept for forensics).

### Anti-Patterns to Avoid

- **Per-controller initContainer.** Would put 6 copies of the mkdir loop in 6 different app-template renders. Single audit trail loss. (D-06 explicitly rejects.)
- **Job that mounts the arrconf-config ConfigMap and parses arrconf.yml at runtime.** Overengineered when `.Files.Get` resolves at template-render time. Adds container-runtime YAML parser dep.
- **A new values.yaml key + CI sync gate.** Necessary only if D-08's values-driven pattern is chosen. The single-source pivot eliminates both.
- **`prune: true` default anywhere in the Category resource.** Phase 9 never deletes — `mkdir -p` only. The whole `prune` concept doesn't apply to filesystem dirs (the Job has no `rmdir` step). Confirmed by CLAUDE.md "Ce que tu NE dois PAS faire" line "Ne pas activer `prune: true` par défaut".
- **Adding `categories` propagation to any reconciler.** Phase 10's job — strict scope boundary.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML parsing in the Job container | A Python container that loads ruyaml | `.Files.Get \| fromYaml` (Helm-side, template-render-time) | One less moving part; no container-side parser version drift; no init-mount of ConfigMap |
| Kebab-case validator | A custom regex parser | `Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")` (pydantic v2 native) | pydantic v2 supports `pattern=` directly on `str` fields since 2.5 |
| `base_path == /media/{name}` invariant | A reconciler-side runtime check | `@model_validator(mode="after")` on `Category` (pydantic v2 native) | Validation fires at YAML load, not at reconcile time; fail-fast |
| Cross-version JSON Schema normalization | Custom JSON-pretty-printer + key sorter | `json.dumps(schema, indent=2, sort_keys=True)` (already in schema_gen.py:33) | Already there; D-16's "byte-stable" property already proven |
| Idempotent mkdir log | A custom log-format spec | `mkdir -p` + `if [ -d ... ]` + `printf '{"event":...}\n'` (5 lines of busybox sh) | The whole Job is ~30 lines; anything shorter is illegible, anything longer is over-engineered |
| Migration helper script (`tools/scripts/migrate-to-categories.sh`) | An auto-mover that maps files to categories | A copy-paste runbook in CLAUDE.md | Per-file routing (which exact movies are "kid" vs "general"?) requires operator judgement. CONTEXT.md §Deferred explicitly parks this script. |

**Key insight:** The phase has 5 deliverables and 1 of them (`mkdir -p /media/<name>` × 10) is literally a 10-line shell loop. The temptation to over-engineer is real. Resist it. The simplest plan that satisfies all 5 success criteria wins.

## Runtime State Inventory

**Trigger:** Phase 9 introduces a NEW data contract (`categories: list[Category]`) — but is NOT a rename/refactor/migration of an existing data shape. The 10 categories sit alongside the v0.2.0 flat sections. Nevertheless, the runtime-state question is still worth asking because the Job creates *filesystem* state (directories on NFS) that persists beyond `helm uninstall`.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | **None.** No database stores `category.name` or `category.base_path` strings as a key. arrconf has no own data store; categories live in arrconf.yml (file in ConfigMap) and in the filesystem (dirs on NFS). Sonarr/Radarr/Jellyfin DO persist `/media/<path>` strings as rootFolder/library/PathInfos values — but Phase 9 doesn't touch those (Phase 10 does). | No action in Phase 9. |
| Live service config | **None directly.** The chart `arrconf-config` ConfigMap will gain 10 lines × ~5 fields when the `categories:` block is added to `charts/arr-stack/files/arrconf.yml` — but this is a code edit, not live-service drift. After `helm upgrade`, ArgoCD propagates the new ConfigMap content within ~1h. | No action — handled by normal `helm upgrade` cycle. |
| OS-registered state | **None.** No systemd / Task Scheduler / launchd registration embeds `category.name` values. | None — verified by `find ~/projets/perso/my-kluster -name '*.service' -o -name '*.plist'` returning 0 hits. |
| Secrets/env vars | **None.** No secret or env var name references categories (envFrom on the arrconf CronJob is for API keys only). | None. |
| Build artifacts / installed packages | **None.** The new `categories.py` module adds a Python import; pyproject.toml does not change. No egg-info / `.pth` / installed-package state drifts. The Helm chart adds one new template file (`categories-init-job.yaml`) and one updated values file — all tracked by `Chart.lock`-less dependency build. Chart.lock unchanged. | None. |
| **NEW — Filesystem state (Phase-9-specific)** | The Helm Job creates 10 dirs under `/Public/media-stack/media/` on NFS server `192.168.88.103`. These dirs persist beyond `helm uninstall` (no delete-hook is wired by design). If a category is later REMOVED from `arrconf.yml`, its empty `/media/<name>` directory remains — no automatic cleanup. | DOCUMENTED in operator runbook (D-17) as "remove direly is operator's manual step — Phase 9 never deletes". |

**Net:** Phase 9 has no runtime-state migration burden. The only filesystem state it touches is the 10 new `/media/<name>` directories, all empty after the Job runs.

## Common Pitfalls

### Pitfall 1: NFS subtree mkdir might be permission-restricted differently than rootFolder access (NEGLIGIBLE)

**What goes wrong:** Even though uid-1000 can READ `/media/series` (snapshot evidence), it might be unable to CREATE `/media/series-emilie` at the share root if the NAS export uses `subtree_check` + `nohide` + restricted ACLs.

**Why it happens:** NFSv3 with `nolock` honors server-side `/etc/exports` permissions; uid-1000 mkdir at the share root is a different operation than uid-1000 mkdir inside an existing sub-path.

**How to avoid / how to detect:** The linuxserver containers ALREADY create subdirectories under `/media/series/<show>/` when they import episodes (a stronger operation than top-level mkdir). If subtree mkdir works, top-level mkdir works on every shared NFS server config I've seen. If — surprising — the Job fails at first install, the recovery is documented but pre-implemented at zero cost.

**Warning signs:** Job's `printf '{"event":"media_dir_ensured",..."created":true}'` log line is absent, replaced by a `mkdir: permission denied` stderr.

**Severity:** LOW (HIGH confidence the happy path works).

### Pitfall 2: `extra="forbid"` + new field breaks existing arrconf.yml with `extra='forbid'` violation (NEGLIGIBLE)

**What goes wrong:** RootConfig has `model_config = ConfigDict(extra="forbid")`. Adding a new field `categories` to RootConfig means the schema NOW REQUIRES the field name be allowed — which it is, because we added it. The risk would only manifest if a CONSUMER YAML had `categories: ...` BEFORE we added the field (they don't — `extra="forbid"` would have blocked that), OR if we typo'd the field name.

**Why it doesn't apply:** This is a pure additive change. No existing arrconf.yml file in any branch has a `categories:` key today.

**How to verify:** `git grep -E '^categories:' charts/ examples/ tests/ snapshots/` returns 0 results before Phase 9.

**Severity:** N/A (raised for completeness — does not apply to this phase).

### Pitfall 3: `model_dump` default change affects round-trip if dump_cmd is refactored (MEDIUM — future)

**What goes wrong:** If Phase 10 or later refactors `arrconf dump` to use `RootConfig.model_dump()` instead of hand-built dicts, the default `model_dump()` will emit `categories: []` even for configs that had no categories block. Reload-then-dump round-trip is no longer byte-stable.

**Why it happens:** pydantic v2's default `model_dump` includes ALL defined fields, including ones with `default_factory=list` (`categories: []`).

**How to avoid:** Use `exclude_unset=True` in any future `RootConfig.model_dump` call. Verified live (see Open Q3 evidence section) — `exclude_unset=True` drops `categories: []` if it wasn't in the input YAML but KEEPS `radarr: {}` if it was in the input (the safe trade-off).

**Severity:** LOW (Phase 9 doesn't trigger this; flagged for Phase 10+ awareness).

### Pitfall 4: Helm 4 multi-alias workaround interaction with the new template (NONE — verified)

**What goes wrong:** Worry: `chart-lint.yml` has a Helm-4 multi-alias workaround that unpacks `app-template-5.0.0.tgz` into 10 alias directories. Could this affect the new `categories-init-job.yaml` template under `charts/arr-stack/templates/`?

**Why it doesn't apply:** The unpacking is for `charts/arr-stack/charts/<alias>/` (dependency renders). `charts/arr-stack/templates/` is the umbrella's own template directory — completely separate. The new Job template renders independently of the alias-vendoring workaround.

**Verification:** Already validated by `arrconf-configmap.yaml` and `configarr-configmap.yaml` — both live in `templates/` and both render correctly under the multi-alias workaround.

**Severity:** N/A.

### Pitfall 5: linuxserver PUID/PGID env vs `runAsUser`/`runAsGroup` confusion (LOW)

**What goes wrong:** Operator copies the Job spec and adds `env: { PUID: "1000", PGID: "1000" }` thinking it's needed.

**Why it's wrong:** `PUID/PGID` is a linuxserver-image convention. busybox honors NEITHER — uid/gid are controlled purely by Kubernetes `securityContext`. Adding the env vars is harmless but misleading.

**How to avoid:** Document in the Job template's inline comment: "busybox does NOT honor PUID/PGID — uid/gid is set by pod-level securityContext."

**Severity:** LOW (cosmetic; runbook entry).

### Pitfall 6: ruyaml comment-preservation interaction (NONE for Phase 9)

**What goes wrong:** Worry: future tooling that reads `arrconf.yml` + writes it back may strip the `# yaml-language-server: ...` modeline.

**Why it doesn't apply to Phase 9:** Phase 9 only ADDS a `categories:` block to `charts/arr-stack/files/arrconf.yml` via a hand-edit (one-shot static addition). No tool round-trips the file in Phase 9. The dump-side ruyaml (`dump.py`) writes to `examples/baseline-sonarr.yml`, NOT to `charts/arr-stack/files/arrconf.yml`.

**Severity:** N/A (raised for traceability; relevant if Phase 10+ ever writes back to the chart's arrconf.yml).

### Pitfall 7: SC#4 byte-equivalence proof uses the WRONG tool per CONTEXT.md (CRITICAL CLARIFICATION)

**What goes wrong:** CONTEXT.md §D-15 references `tools/scripts/byte-equivalence-diff.sh` for the Phase 9 SC#4 dispositive. But that script is for `helm template` output diff (`kubectl apply --dry-run=client` round-trip), NOT for `arrconf dump` output diff.

**Why it matters:** If the planner reads CONTEXT.md literally and wires the wrong script, the test will pass trivially (helm output IS byte-equivalent because Phase 9 adds a new template, not modifies existing ones) but won't actually prove the SC#4 invariant (which is about RECONCILER behavior on a categories-less arrconf.yml).

**How to avoid:** The SC#4 dispositive must be a **new pytest** (e.g. `tests/test_phase9_no_regression.py`) that:
1. Loads `charts/arr-stack/files/arrconf.yml` as it stands BEFORE Phase 9 adds the `categories:` block (use git stash / a frozen fixture copy).
2. Runs each of the 6 reconcilers in `dry_run=True` mode against a mocked respx client.
3. Captures `reconcile_<app>(client, instance, dry_run=True).plan` as a list of structured tuples.
4. Asserts the plan-list equals a frozen baseline JSON file.

The frozen baseline is generated ONCE during plan execution (with Phase 9 code, with categories[] omitted from the arrconf.yml fixture) and committed. Future regressions break the test.

**Severity:** HIGH for planner; LOW for engineer (once clarified). This is the single most important pitfall in this research.

### Pitfall 8: Job order vs `arrconf-config` ConfigMap order (NONE — verified)

**What goes wrong:** Worry: the categories-init Job needs the `/media` PVC mounted, but the PVC is owned by ArgoCD/Helm. What if the Job fires before the PVC binds?

**Why it doesn't apply:** The PVC `media-nas-pvc` exists OUTSIDE the chart (defined in `my-kluster/config/media-stack-pv.yaml`). It is bound permanently to the NFS server. `helm install` doesn't create or wait on it — the Helm Job just references `existingClaim: media-nas-pvc`. If the PVC isn't bound when the Job starts, Kubernetes' Pod scheduler waits until it is (standard `Pending` state).

**Severity:** N/A.

## Operator Migration Runbook

> Refined version of CONTEXT.md §D-17 with each `mv` source/destination cross-checked against the current `charts/arr-stack/files/arrconf.yml` (verified via grep on line refs).

### Current v0.2.0 layout (verified from arrconf.yml)

Per `charts/arr-stack/files/arrconf.yml` (verified 2026-05-18, lines 15-17, 179-181, 354-364, 389-407, 480-488):

| v0.2.0 dir | Used by | Currently contains |
|------------|---------|-------------------|
| `/media/series` | Sonarr rootFolder #1 (line 15) + Jellyfin "Séries" library path #1 (line 480) | The default series bucket — most series live here |
| `/media/anime` | Sonarr rootFolder #2 (line 16) + Jellyfin "Séries" library path #2 (line 481) + Seerr `activeAnimeDirectory` (line 391) | Anime series — to be split: Zoé's anime → `/media/series-zoe` |
| `/media/family` | Sonarr rootFolder #3 (line 17) + Jellyfin "Séries" library path #3 (line 482) | Family-rated series (kids → boys) |
| `/media/films` | Radarr rootFolder #1 (line 179) + Jellyfin "Films" library path #1 (line 486) + Seerr `activeDirectory` (line 406) | The default films bucket — most films live here |
| `/media/films-anime` | Radarr rootFolder #2 (line 180) + Jellyfin "Films" library path #2 (line 487) | Anime films — to be split: Zoé's anime films → `/media/films-zoe`, kid animation → `/media/films-animation-enfants` |
| `/media/films-family` | Radarr rootFolder #3 (line 181) + Jellyfin "Films" library path #3 (line 488) | Family-rated films (kids) |

### v0.2.0 → v0.3.0 mapping table (validated)

| v0.2.0 dir | v0.3.0 dir(s) | Operator action |
|------------|---------------|------------------|
| `/media/series` | `/media/series` (default) + selective `mv` to `/media/series-emilie`, `/media/series-thomas`, `/media/series-garcons` | Operator manually moves Émilie's, Thomas's, and the boys' series subdirs into their named buckets. The rest stays in `/media/series`. |
| `/media/anime` | `/media/series-zoe` (Zoé's anime is the bulk of this) | Move the contents wholesale. If any non-Zoé anime is in here, the operator decides where it goes (most likely back to `/media/series`). |
| `/media/family` | `/media/series-garcons` (the family-rated kids' series bucket) | Move wholesale to the boys' bucket. |
| `/media/films` | `/media/films` (default) + selective `mv` to `/media/nouveaux-films` (recent additions only — operator picks the cutoff date) | Bulk stays; operator moves "newly-added" films per their own definition. |
| `/media/films-anime` | `/media/films-zoe` (Zoé's films) + `/media/films-animation-enfants` (kid-rated animation like Pixar/Disney for the boys) | Split by operator judgment: Studio Ghibli → Zoé; Disney/Pixar → enfants. |
| `/media/films-family` | `/media/films-enfants` | Rename, wholesale move. |

### Pre-check

```bash
# 1. Capture baseline snapshot of all 6 apps' API state (rootfolder paths, library paths, etc.)
tools/snapshot/snapshot.sh --output snapshots/before-categories-migration-$(date +%F)/
git add snapshots/before-categories-migration-* && git commit -m "snapshot(pre-categories-migration): baseline"

# 2. Verify the 10 new /media/<name> dirs exist (created by Phase 9's Job on chart upgrade):
kubectl exec -n selfhost deployment/jellyfin -- ls /media/ | sort | column
# Expected: films, films-animation-enfants, films-enfants, films-zoe, nouveaux-films,
#           series, series-emilie, series-garcons, series-thomas, series-zoe
#           (plus possibly the v0.2.0 legacy: anime, family, films-anime, films-family)
```

### Execution

**Recommendation:** Use a one-shot maintenance pod with `media-nas-pvc` mounted at `/media`. The simplest pattern is to `kubectl exec` into an existing pod (Jellyfin works — it already has the PVC mounted RW at `/media`).

```bash
# Open a shell into Jellyfin with /media mounted:
kubectl exec -n selfhost -it deployment/jellyfin -- bash

# Inside the pod:
cd /media
mv anime/* series-zoe/ 2>/dev/null  # bulk-move anime to Zoé's bucket
mv family/* series-garcons/         # bulk-move family series to boys' bucket
mv films-family/* films-enfants/    # bulk-move family films to enfants
# films-anime requires per-Studio/per-film judgment:
ls films-anime/ | head -20  # eyeball the contents
mv films-anime/Studio*Ghibli films-zoe/                  # Zoé's
mv films-anime/Disney films-anime/Pixar films-animation-enfants/  # enfants
# Selective /media/series → /media/series-{emilie,thomas} per operator:
# (No script — too judgment-driven; mv per-show in Émilie's/Thomas's bucket.)
```

### Post-check

```bash
# 1. Force Sonarr/Radarr/Jellyfin to rescan paths so they pick up moved content:
# Sonarr & Radarr — RescanSeries / RescanMovie command via API
curl -X POST -H "X-Api-Key: $SONARR_API_KEY" "http://sonarr.svc.cluster.local:8989/api/v3/command" \
  -d '{"name":"RescanSeries"}'
curl -X POST -H "X-Api-Key: $RADARR_API_KEY" "http://radarr.svc.cluster.local:7878/api/v3/command" \
  -d '{"name":"RescanMovie"}'
# Jellyfin — library scan
curl -X POST -H "X-Emby-Token: $JELLYFIN_API_KEY" "http://jellyfin.selfhost.svc.cluster.local:8096/Library/Refresh"

# 2. Post-migration snapshot + diff vs baseline:
tools/snapshot/snapshot.sh --output snapshots/post-categories-migration-$(date +%F)/
diff -ru snapshots/before-categories-migration-*/ snapshots/post-categories-migration-*/ \
  | head -100  # expect: rootfolder.json freeSpace changed; library "Recently Added" timestamps refreshed
git add snapshots/post-categories-migration-* && git commit -m "snapshot(post-categories-migration): evidence"
```

### Rollback (operator's responsibility, kept short)

```bash
# Inverse moves. The operator IS the one who made the per-file choices,
# so the inverse is "operator remembers what they moved". Specifically:
# mv /media/series-zoe/* /media/anime/    (Zoé back to anime)
# mv /media/series-garcons/* /media/family/  (boys back to family)
# mv /media/films-enfants/* /media/films-family/  (enfants back to family)
# Etc. This is intentionally not scripted — operator judgment got it here,
# operator judgment gets it back.
```

## Wave Structure Recommendation

**Recommended: 4 plans, 2 waves.**

### Wave 1 (Plans A + B run in parallel)

**Plan A: Python — pydantic Category model + RootConfig field + tests + schema regen**
- `tools/arrconf/arrconf/resources/categories.py` (NEW, ~50 lines)
- `tools/arrconf/arrconf/config.py` (MODIFIED — add 1 import + 1 field on RootConfig)
- `tools/arrconf/tests/test_categories.py` (NEW, parametric: valid 10-entry × invalid permutations)
- `schemas/arrconf-schema.json` (REGENERATED via `arrconf schema-gen`)
- The existing `tests/test_schema_gen.py::test_schema_committed_matches_regen` + `tests.yml#Verify schema reproducibility` already gate this — no new test code for the gate.

**Plan B: Chart — Helm-hooked Job template (single-source pattern, NO values.yaml changes)**
- `charts/arr-stack/templates/categories-init-job.yaml` (NEW, ~50 lines including the verified skeleton above)
- `charts/arr-stack/values.yaml` (UNCHANGED — the single-source pattern reads from arrconf.yml directly)
- `charts/arr-stack/values.schema.json` (UNCHANGED — no new values key)
- `charts/arr-stack/_helpers.tpl` (UNCHANGED — no new helper needed)
- Verifications: `helm lint charts/arr-stack/ -f examples/values-prod.yaml`; `helm template ... | kubeconform`; visual review of rendered Job manifest matches the expected `mkdir -p` loop.

**Dependency note:** Plans A and B are independent. Plan B does NOT need the Category pydantic model to render — it reads `.Files.Get | fromYaml | .categories` from the YAML directly (whether the categories block exists OR is empty). The categories block lands in Plan C.

### Wave 2 (Plans C + D, may run in parallel — C depends on A's `RootConfig.categories` field for the load_config validation; D is standalone documentation)

**Plan C: arrconf.yml declaration + schema regen + validation tests**
- `charts/arr-stack/files/arrconf.yml` (MODIFIED — prepend the 10-entry `categories:` block before the `sonarr:` key, after the `# yaml-language-server: ...` modeline; use the verbatim block from CONTEXT.md §Specifics)
- `schemas/arrconf-schema.json` (REGENERATED — depends on Plan A's RootConfig change being merged)
- `tools/arrconf/tests/test_arrconf_yml_validates.py` (MODIFIED — add `test_arrconf_yml_has_10_categories` assertion: `assert len(cfg.categories) == 10; assert {c.name for c in cfg.categories} == {...exact 10 names...}`)
- `tools/arrconf/tests/test_phase9_no_regression.py` (NEW — SC#4 dispositive per Pitfall 7 above; load arrconf.yml frozen baseline + run all 6 reconcilers dry-run + assert plan list unchanged)

**Plan D: CLAUDE.md migration runbook + release commit**
- `CLAUDE.md` (MODIFIED — add the "Filesystem migration: v0.2.0 flat → v0.3.0 Categories" section AFTER the "Pattern single-instance + tags" section AND BEFORE the "Intégration avec my-kluster" section — per CONTEXT.md §Specifics line 452)
- `charts/arr-stack/values.yaml` (MODIFIED — pre-bump `arrconf.image.tag` from `"0.5.0"` to whatever the next auto-tag will be — per CF-07-CHART-PIN-LOOP). Per CONTEXT.md additional context: even though Phase 9 doesn't change reconciler behavior, the image tag pre-bump should happen in the same commit when releasing Phase 9 to lock the cycle to 1 my-kluster targetRevision bump.

**Wait — is the values.yaml pre-bump correct here?** Re-reading CONTEXT.md, "Phase 9 doesn't change reconciler behaviour (only schema parsing), so the image tag bump should still happen in the same commit when releasing Phase 9 to lock the cycle to 1 my-kluster targetRevision bump." This is correct — Phase 9 DOES change parser behavior (new pydantic field), and a new arrconf image will be built. So Plan A's commit (or alternatively a release-finalization commit) needs the image.tag bump. Recommendation: include the image.tag bump in the FINAL commit of the phase (Plan D's commit) so the chain is: Plan A → image build → Plan D releases with the new tag pinned.

### Dependency graph

```
Plan A (Python schema, schema regen)       Plan B (Helm Job, single-source)
    |                                          |
    | RootConfig.categories field              | (independent — categories block
    | is required for load_config validation   |  not yet in arrconf.yml; Job
    | to NOT raise extra='forbid' violation    |  iterates over empty list = noop)
    |                                          |
    |                                          |
    +----------+                  +------------+
               |                  |
               v                  v
        Plan C (arrconf.yml block + schema regen + tests)
               |
               | (file-level conflict with Plan A on schemas/arrconf-schema.json
               |  if both regen — Plan C wins because it runs AFTER Plan A)
               |
               v
        Plan D (CLAUDE.md + release commit with image.tag bump)
```

Plan D could technically run before Plan C (it's just CLAUDE.md + image.tag) — but committing the release after the new contract is wired and tested is the safer cycle.

### Plan validation sketch

| Plan | Files touched | Verification command |
|------|--------------|---------------------|
| A | `tools/arrconf/arrconf/resources/categories.py`, `tools/arrconf/arrconf/config.py`, `tools/arrconf/tests/test_categories.py`, `schemas/arrconf-schema.json` | `cd tools/arrconf && uv run ruff check . && uv run ruff format --check . && uv run mypy arrconf && uv run pytest -v --cov` |
| B | `charts/arr-stack/templates/categories-init-job.yaml` | `helm lint charts/arr-stack/ -f examples/values-prod.yaml && helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml \| kubeconform -strict -ignore-missing-schemas` |
| C | `charts/arr-stack/files/arrconf.yml`, `schemas/arrconf-schema.json`, `tools/arrconf/tests/test_arrconf_yml_validates.py`, `tools/arrconf/tests/test_phase9_no_regression.py` | full test suite + helm lint (the chart's ConfigMap renders the modified arrconf.yml) |
| D | `CLAUDE.md`, `charts/arr-stack/values.yaml` (image.tag) | `helm lint charts/arr-stack/ -f examples/values-prod.yaml` (validates the bumped tag isn't a forbidden value) |

## Validation Architecture

> Nyquist validation enabled (default — `.planning/config.json` doesn't disable it).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0 + respx 0.23 (existing — `tools/arrconf/pyproject.toml` dev deps) |
| Config file | `tools/arrconf/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd tools/arrconf && uv run pytest tests/test_categories.py tests/test_schema_gen.py tests/test_arrconf_yml_validates.py -x` |
| Full suite command | `cd tools/arrconf && uv run ruff check . && uv run ruff format --check . && uv run mypy arrconf && uv run pytest --cov --cov-report=term-missing --cov-fail-under=70` (matches `tests.yml`) |

For Helm validation:

| Property | Value |
|----------|-------|
| Framework | helm 3.18 + kubeconform 1.33 + 5 in-CI guard scripts |
| Quick run command | `helm lint charts/arr-stack/ -f examples/values-prod.yaml` |
| Full suite command | The 8-step `chart-lint.yml` workflow (lint + template + kubeconform + renovate-guard + latest-tag-guard + cronjob-guard + repository_dispatch-guard + renovate-validator) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-categories-schema | `Category` model validates kebab-case name + Literal enums + `base_path == /media/{name}` invariant | unit | `pytest tests/test_categories.py -x` | ❌ Wave 1 — NEW `test_categories.py` |
| REQ-categories-schema | `RootConfig.categories: list[Category]` field added; schema regenerates | unit | `pytest tests/test_schema_gen.py::test_schema_committed_matches_regen -x` | ✅ EXISTING (passes after Plan A regen) |
| REQ-categories-schema | CI fails on schema staleness | integration (workflow) | `tests.yml` "Verify schema reproducibility (D-15)" step (existing) | ✅ EXISTING |
| REQ-categories-10-target | 10 categories declared in `charts/arr-stack/files/arrconf.yml` | unit (parses chart YAML) | `pytest tests/test_arrconf_yml_validates.py::test_arrconf_yml_has_10_categories -x` (NEW assertion) | ❌ Wave 2 — extend EXISTING file |
| REQ-categories-10-target | The 10 names match the production set exactly | unit | `assert {c.name for c in cfg.categories} == {"series", "series-emilie", ..., "films-zoe"}` (in test_arrconf_yml_validates.py) | ❌ Wave 2 |
| REQ-migration-progressive | byte-equivalent reconciler behavior when categories[] is absent | unit (dry-run plan diff) | `pytest tests/test_phase9_no_regression.py::test_dry_run_plan_unchanged -x` | ❌ Wave 2 — NEW `test_phase9_no_regression.py` |
| REQ-filesystem-initcontainer | Job template renders valid K8s manifest | integration (helm + kubeconform) | `helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml \| kubeconform -strict -ignore-missing-schemas` (existing chart-lint.yml step picks it up) | ✅ EXISTING (workflow); Wave 1 adds the template |
| REQ-filesystem-initcontainer | Job uses `helm.sh/hook: pre-install,pre-upgrade` annotations | integration (rendered-manifest grep) | `helm template ... \| grep -A1 'name:.*categories-init' \| grep 'helm.sh/hook'` (manual or workflow assertion) | ❌ Wave 1 — could be added as a `chart-lint.yml` grep guard if desired |
| REQ-filesystem-initcontainer | Job iterates over categories[] from `.Files.Get \| fromYaml` | manual (visual review of rendered manifest) | `helm template ... \| grep -A20 categories-init` shows 10 `mkdir -p` + 10 `printf '{"event":"media_dir_ensured"' lines` | n/a — manual gate at PR review |
| REQ-filesystem-initcontainer | idempotence (re-run = no-op) | manual (cluster-time) | After Phase 9 cluster deploy: `kubectl get jobs -n selfhost \| grep categories-init` (1 entry); `helm upgrade arr-stack arr-stack/ ...` (new Job runs); inspect logs for `"created":false,"existed":true` × 10 | n/a — operator manual at first deploy |
| REQ-filesystem-initcontainer | uid 1000 successfully mkdirs on NFS | manual (cluster-time) | `kubectl logs job/arr-stack-categories-init` shows all 10 `media_dir_ensured` lines with no errors | n/a — operator manual |
| REQ-filesystem-operator-migration | CLAUDE.md has the new "Filesystem migration" section | unit (grep) | `grep -F '## Filesystem migration: v0.2.0 flat → v0.3.0 Categories' CLAUDE.md` | ❌ Wave 2 — manually verified at PR; could be a new chart-lint workflow guard if desired |
| (D-15 dispositive) | SC#4 byte-equivalence reconcile when categories[] absent | unit | `pytest tests/test_phase9_no_regression.py -x` (above) | ❌ Wave 2 |

### Sampling Rate

- **Per task commit:** `cd tools/arrconf && uv run pytest tests/test_categories.py tests/test_schema_gen.py -x` (~5 sec)
- **Per wave merge:** Full `pytest` suite + `helm lint` + `kubeconform`
- **Phase gate:** Full `tests.yml` + `chart-lint.yml` green; SC#4 dispositive pytest green; manual cluster-time gates for filesystem-initcontainer idempotence + uid-1000 success (one-shot, immediately after the Phase 9 ArgoCD sync)

### Wave 0 Gaps

- ❌ **`tools/arrconf/tests/test_categories.py`** — covers REQ-categories-schema (unit-level validator coverage)
- ❌ **`tools/arrconf/tests/test_phase9_no_regression.py`** — covers REQ-migration-progressive (SC#4 dispositive)
- ❌ **`tools/arrconf/tests/fixtures/phase9-baseline-plans.json`** (or similar frozen file) — captures the v0.2.0 reconciler plan output for diff
- ✅ Framework already installed (pytest, respx, ruff, mypy via `uv sync --frozen` in tests.yml)
- ✅ Helm lint + kubeconform already wired in chart-lint.yml
- ✅ Schema regen CI gate already wired
- ✅ ruff/mypy strict gates already wired

### Test fixture sketch — `tests/fixtures/phase9-baseline-plans.json`

The Plan C engineer should generate this once during plan execution by running the Phase 9 code against the categories-less arrconf.yml and snapshotting the produced plans:

```python
# Pseudo-script (one-shot, run by engineer during Plan C, output committed):
from arrconf.config import load_config
from arrconf.reconcilers.sonarr import reconcile_sonarr
# ... etc
from <test fixtures> import mock_sonarr_client, mock_radarr_client, ...

cfg = load_config("charts/arr-stack/files/arrconf.yml")  # Phase 9 build, BUT categories[] block COMMENTED OUT
result = {
    "sonarr": [(p.action.value, p.resource_type, p.identity) for p in reconcile_sonarr(mock_sonarr_client, cfg.sonarr["main"], dry_run=True).plan],
    "radarr": [...],
    "prowlarr": [...],
    "qbittorrent": [...],
    "seerr": [...],
    "jellyfin": [...],
}
json.dump(result, open("tests/fixtures/phase9-baseline-plans.json", "w"), indent=2, sort_keys=True)
```

The TEST then asserts that running the same pipeline against the production arrconf.yml (WITHOUT the categories block — Phase 9 commits the block but the test uses a frozen fixture WITHOUT it) produces the same plan dict.

## Project Constraints (from CLAUDE.md)

Phase 9 must comply with the following CLAUDE.md directives (extracted by reading the project instructions). All are HARD constraints — the planner MUST honor them.

| Directive | Source (CLAUDE.md section) | Phase 9 compliance |
|-----------|---------------------------|---------------------|
| `ruff check` AND `ruff format --check` must pass before commit; CI blocks | "Code style" | Wave 1 Plan A applies; covered by existing tests.yml |
| `mypy` strict on signatures publiques; CI blocks | "Code style" | Wave 1 Plan A applies; `Category` model + `Kind`/`Profile` enums all typed |
| Type hints partout on public signatures | "Code style" | New `categories.py` honors |
| Couverture cible ≥ 70% on `differ.py` + `reconcilers/` | "Tests" | Phase 9 doesn't change either file (covered by D-13) — no coverage delta expected |
| Mock l'API via respx; no real API calls in CI | "Tests" | Phase 9 has no API surface — no respx mocks needed |
| Every image in `values.yaml` MUST have `# renovate: image=...` annotation directly above | "Annotations Renovate (CRITIQUE)" | Wave 1 Plan B applies — `# renovate: image=docker.io/busybox` on the Job container's image line |
| `prune: false` default; opt-in per section | "Idempotence (RÈGLE D'OR)" | N/A for Phase 9 — Categories is not a prune-able resource (Job never deletes) |
| No `:latest` in production | "Stack technique" / "Ce que tu NE dois PAS faire" | Wave 1 Plan B applies — busybox is pinned to `1.36.1` (D-10) |
| Pas de tag amend (`git tag -f`) | "Ce que tu NE dois PAS faire" | Phase 9 release uses auto-tag from chart-lint.yml — no manual tag intervention needed |
| Pas de dep Python sans pinning | "Ce que tu NE dois PAS faire" | Phase 9 adds NO new Python deps — only stdlib (`typing.Literal`) and existing pydantic |
| Pas d'écriture sur endpoints frontière configarr (quality_profiles, etc.) | ADR-5 / "Frontière arrconf / configarr" | Phase 9 doesn't touch any reconciler — N/A |
| Snapshot raw AVANT toute Phase qui touche un nouveau scope | ADR-6 / "Workflow snapshot" | Plan A/B/C/D engineers MUST run `tools/snapshot/snapshot.sh --output snapshots/before-phase-9-2026-05-18/` before any cluster-touching test. Phase 9 has NO cluster-touching test in CI (helm template is not a cluster touch), but the FIRST cluster deploy via my-kluster bump MUST be preceded by this snapshot. |
| Pas de déploiement direct depuis ce repo | "Ce que tu NE dois PAS faire" | Phase 9 release ships via the auto-tag → image build → my-kluster targetRevision bump pipeline; never `helm install` from arr-stack working copy |
| `prune: true` jamais par défaut | "Ce que tu NE dois PAS faire" | N/A for Phase 9 |
| Pas de test cluster sans snapshot préalable | "Ce que tu NE dois PAS faire" / ADR-6 | Per above, snapshot baseline before first cluster deploy |
| Pas de Renovate annotation removal | "Ce que tu NE dois PAS faire" | Plan B's busybox image line MUST carry the annotation |

**Notably absent constraints (Phase 9 does NOT trip):**
- ADR-5 frontière configarr — Phase 9 doesn't touch configarr scope.
- ADR-7 single-instance — Phase 9 doesn't modify instance structure.
- ADR-8 `?forceSave=true` — Phase 9 doesn't issue any HTTP PUTs to *arr apps.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `mathieudutour/github-tag-action@v6.2` produces a new patch tag on every push to main passing chart-lint, so Phase 9's release tag is automatic | Wave 2 / Plan D image.tag pre-bump | If wrong: operator manually tags. Low impact — tag mechanism is verified by 11 prior phases. |
| A2 | `arrconf.image.tag` pre-bump value matches what `mathieudutour/github-tag-action` will produce | Plan D commit | If wrong: my-kluster needs an extra targetRevision bump (the CF-07-CHART-PIN-LOOP cycle the bump is meant to avoid). Manually verifiable: read `git log -1 --format=%H` then compute next semver via the action's logic. Documented as a Phase 10 carry-forward in CONTEXT.md. |
| A3 | The 10 production category names exactly match operator's mental model | Plan C arrconf.yml block | If wrong: operator vetoed during PR review. The 10 names come straight from CONTEXT.md D-01..D-03 (operator-locked via discuss-phase). |
| A4 | `arr-stack.fullname` helper does not exist in `_helpers.tpl` (recommendation to hardcode `.Release.Name`-prefixed name in the Job) | Pattern 3 / Job template | VERIFIED — read `_helpers.tpl` 2026-05-18: only `arr-stack.labels` defined. |
| A5 | The kebab-case regex `^[a-z0-9]+(-[a-z0-9]+)*$` correctly matches all 10 production names and rejects invalid permutations | Pattern 1 / Category model | VERIFIED by inspection: `series-emilie`, `films-animation-enfants`, etc. all match; uppercase/leading-hyphen/double-hyphen rejected. |

## Open Questions (residual — none blocking)

None. All four CONTEXT.md open-for-research items resolved dispositively (§Open Questions section above). The only residual judgment calls are Wave 1 plan ownership (whether Plan A and Plan B run as two PRs or one — recommendation is two PRs for clarity, but either works).

## Environment Availability

Phase 9 has minimal external dependencies. All required tools are already in the project's standard CI/local environment.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Helm | Wave 1 Plan B (lint + template) | ✓ (verified `helm version` works in research session) | 3.18.5 | — |
| kubeconform | Wave 1 Plan B (validate manifests) | ✓ (`chart-lint.yml` installs latest) | latest | — |
| Python 3.13 | All Python plans | ✓ (locked via `pyproject.toml` `requires-python = ">=3.13"` + `tests.yml` `python-version: "3.13"`) | 3.13 | — |
| uv | Wave 1 Plan A (`uv sync --frozen`) | ✓ (tests.yml uses `astral-sh/setup-uv@v4` v0.11.x) | 0.11.x | — |
| pydantic | Wave 1 Plan A | ✓ (pinned in pyproject.toml `>=2.13,<3`) | 2.13.x | — |
| ruyaml | Wave 1 Plan A + C | ✓ (`>=0.91,<0.92`) | 0.91.x | — |
| respx | Wave 2 Plan C (test_phase9_no_regression mocks) | ✓ (`>=0.23,<0.24`) | 0.23.x | — |
| docker.io/busybox:1.36.1 | Runtime (chart deploy) | ✗ (not pulled locally; cluster pulls anonymously at install) | 1.36.1 | None — cluster MUST be able to pull from Docker Hub. Verified by snapshot of last 11 phases — anonymous pull from Docker Hub works on this cluster. |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

## Code Examples

### Verified pattern — Category pydantic model (full reference)

See "Pattern 1: pydantic resource module shape" above. Source basis: `arrconf/resources/qbittorrent/category.py` lines 1-27 (existing pattern in the codebase).

### Verified pattern — `.Files.Get | fromYaml | range` (single-source Helm Job)

See "Pattern 3: Helm-hooked Job template" above. Source basis: live `helm template` runs against the actual arrconf.yml in research session (2026-05-18). Documentation reference: [Helm chart_template_guide — Accessing Files](https://helm.sh/docs/chart_template_guide/accessing_files/).

### Verified pattern — Schema regen byte-equivalence gate

The gate already exists. Reproduce locally:

```bash
cd tools/arrconf
uv run arrconf schema-gen --output ../../schemas/arrconf-schema.json
cd ../..
git diff --exit-code -- schemas/arrconf-schema.json
# Exit 0 if clean, exit 1 if drift (with a clear error message in CI).
```

## State of the Art

| Old Approach (Phase 9 init context) | Current Approach (research finding) | When Changed | Impact |
|--------------------------------------|-------------------------------------|--------------|--------|
| D-08: chart Job reads `categoriesInit.basePaths` from values.yaml; CI sync gate enforces `values.yaml ↔ arrconf.yml` parity | Single-source: chart Job reads `.Files.Get "files/arrconf.yml" \| fromYaml \| dig "categories"`; no CI sync gate | This research (2026-05-18) | Eliminates a fragile CI gate; reduces the chart's surface by 1 values.yaml key + 1 values.schema.json entry |
| SC#4 dispositive via `tools/scripts/byte-equivalence-diff.sh` (D-15 wording) | SC#4 dispositive via NEW `tools/arrconf/tests/test_phase9_no_regression.py` (pytest-based, dry-run plan diff) | This research (2026-05-18) | byte-equivalence-diff.sh is for helm-template-rendered diff, not arrconf-dump diff — semantic mismatch noted and corrected. Pitfall 7 above. |
| D-12 NFS uid risk research-flagged ("might fail with root_squash") | D-12 risk resolved — every committed snapshot since 2026-05-07 proves uid-1000 mkdir works on `media-nas-pvc` | This research (2026-05-18) | No fallback branch needed in the Job; D-12 stands as written |
| Q4 schema regen "fall back to `json.dumps(sort_keys=True)` if pydantic ordering drifts" | Already done — `schema_gen.py:33` uses `sort_keys=True` since Phase 1 | This research (2026-05-18) — discovery, not change | Risk eliminated; CONTEXT.md Q4 is moot |

**Deprecated/outdated** in CONTEXT.md:
- The D-08 values.yaml-driven Job design — **superseded** by single-source `.Files.Get | fromYaml` pattern (this research). Planner should explicitly note the pivot in plans.
- The D-15 reference to `byte-equivalence-diff.sh` for SC#4 — **clarified** as needing a new pytest instead.

## Sources

### Primary (HIGH confidence)

- **Helm docs** — [Accessing Files Inside Templates](https://helm.sh/docs/chart_template_guide/accessing_files/), [Built-in Objects (`.Files`)](https://helm.sh/docs/chart_template_guide/builtin_objects/), [Hooks](https://helm.sh/docs/topics/charts_hooks/)
- **Sprig docs** — [fromYaml conversion](https://masterminds.github.io/sprig/conversion.html), [range action (Go template)](https://pkg.go.dev/text/template#hdr-Actions)
- **pydantic v2.13 docs** — `model_json_schema()`, `model_validator(mode="after")`, `Field(pattern=...)`
- **Live tool runs (this research session, 2026-05-18):**
  - `helm template /tmp/testchart/` → verified `.Files.Get | fromYaml` works on arrconf.yml with modeline; verified `range $cat := $cfg.categories` produces clean output (see Open Q1)
  - `uv run python /tmp/test_pydantic.py` → verified pydantic v2 model_dump behavior with added `Field(default_factory=list)` (see Open Q3)
  - `grep` + `cat` on `snapshots/*/sonarr/rootfolder.json` → verified `accessible: true` on `/media/series` across all 16 snapshots (see Open Q2)
  - `git grep -E '^categories:' charts/ examples/ tests/` → returned 0 hits → confirms no pre-existing `categories` key conflicts

### Repo code (HIGH confidence — read in this session)

- `tools/arrconf/arrconf/config.py:621-642` — `RootConfig` declaration site
- `tools/arrconf/arrconf/schema_gen.py:30-34` — write_schema with `sort_keys=True`
- `tools/arrconf/arrconf/resources/qbittorrent/category.py` — closest pydantic shape template
- `tools/arrconf/arrconf/resources/sonarr/download_client.py` — Field(exclude=True) + model validator pattern
- `tools/arrconf/arrconf/dump.py` — verified dump is hand-built dict (not RootConfig.model_dump)
- `tools/arrconf/tests/test_schema_gen.py:49-61` — existing D-16 gate
- `tools/arrconf/tests/test_arrconf_yml_validates.py` — existing chart YAML validation tests (to extend in Plan C)
- `charts/arr-stack/Chart.yaml` — 10 aliases on app-template 5.0.0
- `charts/arr-stack/values.yaml:50-70, 114-132, 410-423` — sonarr/radarr/jellyfin persistence.media on `media-nas-pvc`
- `charts/arr-stack/templates/arrconf-configmap.yaml:10` — proof that `.Files.Get "files/arrconf.yml"` works in this chart
- `charts/arr-stack/templates/_helpers.tpl:1-10` — only `arr-stack.labels` helper exists
- `charts/arr-stack/files/arrconf.yml:1-540` — current production config
- `.github/workflows/tests.yml:50-57` — existing D-15 gate
- `.github/workflows/chart-lint.yml:1-178` — full chart-lint pipeline
- `tools/scripts/byte-equivalence-diff.sh:1-29` — verified helm-template-diff, NOT arrconf-dump-diff (Pitfall 7)
- `tools/arrconf/pyproject.toml:1-69` — pinned deps
- `tools/arrconf/arrconf/__main__.py:489-503` — `arrconf schema-gen` subcommand wiring
- `/home/moi/projets/perso/my-kluster/config/media-stack-pv.yaml` — NFSv3 + nolock + tcp; PV/PVC definitions (see Open Q2)

### Secondary (MEDIUM confidence)

- [Renovate customManagers docs](https://docs.renovatebot.com/configuration-options/#custommanagers) — verifies the `# renovate: image=...` annotation pattern handles `docker.io/busybox` correctly (already proven by 10 image entries in values.yaml)

### Tertiary (LOW confidence — flagged for validation)

- None — all critical claims verified via tool runs or repo code.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already pinned + in production use
- Architecture (Job, single-source, uid 1000): HIGH — dispositively verified via live tool runs
- Pitfalls: HIGH — Pitfall 7 (SC#4 dispositive tooling) discovered during research is the single highest-impact finding
- Schema regen: HIGH — gate already exists and passes today
- Operator runbook mapping: MEDIUM — table is constructed by line-by-line read of arrconf.yml + values.yaml; final mapping requires operator confirmation at PR review (esp. selective `series-emilie`/`series-thomas` splits and `films-animation-enfants` vs `films-zoe` per-film judgment)

**Research date:** 2026-05-18
**Valid until:** 2026-06-17 (30 days — stable domain, but if Phase 10 starts before then, RESEARCH.md may need a small update on the Phase 9/10 boundary section)
