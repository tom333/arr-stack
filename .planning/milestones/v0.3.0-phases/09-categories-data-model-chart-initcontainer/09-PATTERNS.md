# Phase 9: Categories data model + chart initContainer — Pattern Map

**Mapped:** 2026-05-18
**Files analyzed:** 10 (5 new, 5 modified)
**Analogs found:** 10 / 10 (every file has at least a role-match analog in-repo)

## File Classification

| New/Modified File | Status | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|--------|------|-----------|----------------|---------------|
| `tools/arrconf/arrconf/resources/categories.py` | NEW | model (pydantic resource) | pure-pydantic / declarative-validation | `tools/arrconf/arrconf/resources/qbittorrent/category.py` (+ `sonarr/download_client.py` for `extra="forbid"` and field-level `pattern=`) | exact (role) — file is cross-cutting whereas analog is app-scoped (Category lives at resources/ root, not under `qbittorrent/`) |
| `tools/arrconf/tests/test_categories.py` | NEW | test (pydantic validation) | parametric-pydantic-tests | `tools/arrconf/tests/test_scope_violation.py` (parametric pattern) + `tools/arrconf/tests/test_config.py` (validation-error raises pattern) | exact (role+flow) |
| `tools/arrconf/tests/test_phase9_no_regression.py` | NEW | test (reconciler-plan regression) | frozen-fixture diff against `result.plan` tuples | `tools/arrconf/tests/test_reconcilers_sonarr.py` (uses `reconcile_sonarr(... dry_run=True).plan` introspection — same API surface the new test exercises across all 6 apps) | role-match (existing tests run per-app; the new one cross-cuts all 6 reconcilers) — see Pitfall 7 callout below |
| `tools/arrconf/tests/fixtures/phase9-baseline-plans.json` | NEW | fixture (frozen baseline) | frozen-JSON-snapshot | `tools/arrconf/tests/fixtures/*.json` family (e.g. `sonarr_downloadclient_fixture.json` — same json file convention) | role-match (existing fixtures are recorded API responses; this one is recorded plan output — same loading pattern with `json.loads(Path(...).read_text())`) |
| `charts/arr-stack/templates/categories-init-job.yaml` | NEW | chart template (Helm Job + hooks) | chart-template / `.Files.Get \| fromYaml` single-source | `charts/arr-stack/templates/arrconf-configmap.yaml` (sibling: same `metadata.namespace`/`arr-stack.labels` helper + same `.Files.Get "files/arrconf.yml"` invocation that Q1 research confirmed extensible with `\| fromYaml`) | partial (analog is a ConfigMap, target is a hooked Job) — but the **`.Files.Get` pattern** itself is exact match |
| `tools/arrconf/arrconf/config.py` | MODIFIED | model (RootConfig schema) | pure-pydantic + field add | self — lines 22–38 (`from arrconf.resources.qbittorrent.category import Category`) + lines 636–642 (`RootConfig` field declarations) | exact (in-file) |
| `charts/arr-stack/files/arrconf.yml` | MODIFIED | declarative-input (YAML data) | static YAML edit (prepend 10-entry block) | self — lines 1–14 (`# yaml-language-server:` modeline + `sonarr:` top-level) | exact (in-file) |
| `schemas/arrconf-schema.json` | MODIFIED (regenerated) | generated-artifact | byte-stable `json.dumps(..., sort_keys=True)` output | `tools/arrconf/arrconf/schema_gen.py:33` produces it — D-15 gate already enforced by `tests/test_schema_gen.py:49–61` | exact — phase 9 only needs to run the generator once and commit; no code change |
| `CLAUDE.md` | MODIFIED | documentation (operator runbook) | markdown prose + bash code blocks | self — existing "## Pattern single-instance + tags" section (lines 316–338) for placement; "## Workflow snapshot" subsection (in section "Workflow de développement") for bash-block style | exact (in-file) |
| `charts/arr-stack/values.yaml` | MODIFIED | chart values (image tag pin only) | static YAML edit (1-line bump on `arrconf.image.tag`) | self — line 451 (`tag: "0.5.0"` under `arrconf.controllers.main.containers.main.image`) | exact (in-file, single-line CF-07-CHART-PIN-LOOP follow-up) |

---

## Pattern Assignments

### `tools/arrconf/arrconf/resources/categories.py` (NEW — model, pure-pydantic)

**Primary analog:** `tools/arrconf/arrconf/resources/qbittorrent/category.py` (entire file — 27 lines)
**Secondary analog (for `model_validator` + `pattern=`):** `tools/arrconf/arrconf/resources/sonarr/download_client.py`

**Module-docstring + `from __future__` + imports pattern** (qbittorrent/category.py:1-6):
```python
"""qBittorrent category — Phase 5 D-05-QBT-02 resource."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
```
→ Phase 9 file adds `Literal` (for `Kind` / `Profile` enums) and `model_validator`:
```python
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
```

**`extra="forbid"` + `BaseModel` class pattern** (qbittorrent/category.py:8-26):
```python
class Category(BaseModel):
    """A qBittorrent category (POST /api/v2/torrents/createCategory).
    ...
    """

    model_config = ConfigDict(extra="allow")  # NOTE: qBit uses "allow"; Phase 9 uses "forbid"
    name: str = Field(description="Category name (stable match key for differ).")
    savePath: str = Field(
        default="",
        description="qBit-side path where torrents in this category land. "
        "MUST be explicit (e.g. /data/anime), never empty.",
    )
```
→ Phase 9 uses `extra="forbid"` (CONTEXT.md "Established Patterns" §"Top-level YAML keys") and `Field(pattern=...)` for the kebab-case slug validator (RESEARCH.md "Don't Hand-Roll" row 2 — `pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$"`).

**`Literal` enums pattern — D-01/D-02 closed sets** (download_client.py:51-53 for the `Literal` idiom):
```python
protocol: Literal["torrent", "usenet"] = Field(
    description="Download protocol — must match implementation."
)
```
→ Phase 9 hoists `Literal` to module-level type aliases for re-use in tests + future Phase 10 propagators:
```python
Kind = Literal["movies", "series"]
Profile = Literal["general", "anime", "family"]
```

**`model_validator(mode="after")` pattern** — no existing analog in `resources/`; the closest precedent in-repo is at `tools/arrconf/arrconf/config.py` (search confirmed: 0 hits in `arrconf/resources/`). Phase 9 introduces the first `@model_validator(mode="after")` in the resources package. The pydantic v2 idiom is documented in RESEARCH.md §Pattern 1 (lines 525-533):
```python
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

---

### `tools/arrconf/tests/test_categories.py` (NEW — test, parametric-pydantic)

**Primary analog (parametric structure):** `tools/arrconf/tests/test_scope_violation.py:76-117`
**Secondary analog (`pytest.raises(ValidationError)` shape):** `tools/arrconf/tests/test_config.py:73-97`

**Parametric `pytest.mark.parametrize` pattern** (test_scope_violation.py:76-81):
```python
@pytest.mark.parametrize("module", FRONTIERE_MODULES, ids=lambda m: m.__name__.split(".")[-1])
def test_scope_violation_raised_with_configarr_message(module: ModuleType) -> None:
    """Each frontière module raises ScopeViolationError mentioning configarr.yml (D-12)."""
    with pytest.raises(ScopeViolationError, match=r"configarr\.yml"):
        module.reconcile(client=None, config=None, dry_run=False)
```
→ Phase 9 mirrors this for each invariant: `test_name_must_be_kebab_case`, `test_kind_must_be_movies_or_series`, `test_profile_must_be_general_anime_or_family`, `test_base_path_must_equal_media_slash_name`. Each parametrized with the 10 production Category dicts as happy-path inputs + a list of malformed dicts for the failure paths.

**`pytest.raises` for pydantic validation pattern** (test_config.py:73-82):
```python
def test_load_config_validation_error_returns_exit_2(tmp_path: Path) -> None:
    """Schema-violating YAML raises ConfigError (mapped to CLI exit 2)."""
    cfg = tmp_path / "cfg.yml"
    # `bogus: 99` is not in DownloadClientsSection schema (extra="forbid")
    cfg.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "    download_clients:\n      prune: false\n      bogus: 99\n"
    )
    with pytest.raises(ConfigError, match=r"validation error"):
        load_config(cfg)
```
→ For pure-pydantic tests (not going through `load_config`), Phase 9 uses `pytest.raises(pydantic.ValidationError, match=r"...")` directly on `Category(**bad_dict)`.

---

### `tools/arrconf/tests/test_phase9_no_regression.py` (NEW — reconciler-plan regression dispositive)

**Primary analog:** `tools/arrconf/tests/test_reconcilers_sonarr.py` (all `result.plan` introspection sites; specifically lines 104-109 for the no-op assertion shape)

**Plan introspection pattern** (test_reconcilers_sonarr.py:104-109):
```python
client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
result = reconcile_sonarr(client, instance, dry_run=False)

assert all(p.action == Action.NO_OP for p in result.plan if p.desired is not None)
assert post_route.call_count == 0
assert put_route.call_count == 0
assert delete_route.call_count == 0
```

**`SonarrResult.plan` data class** (arrconf/reconcilers/sonarr.py:81-87 — the shape that gets frozen):
```python
@dataclass
class SonarrResult:
    """Result of a Sonarr reconcile run."""

    plan: list[PlannedAction[DownloadClient]] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)
    managed_tag_id: int | None = None
```

**`PlannedAction` shape — what gets serialized to the frozen JSON fixture** (arrconf/differ.py:51-70):
```python
class Action(Enum):
    ADD = "add"
    UPDATE = "update"
    DELETE = "delete"
    NO_OP = "no-op"
    PRUNE_SKIP = "prune-skip"
    PRUNE_PROTECTED = "prune-protected"

@dataclass
class PlannedAction[T: BaseModel]:
    action: Action
    name: str
    current: T | None
    desired: T | None
    diff_fields: list[str]
```

**Concrete dispositive shape (per RESEARCH.md Q3 lines 301-308):**
```python
# Pseudo-code from RESEARCH.md — the planner translates to actual pytest:
def test_dry_run_plan_unchanged_when_categories_absent():
    cfg = load_config("charts/arr-stack/files/arrconf.yml")
    # ... run reconcile_<app>(client, instance, dry_run=True) on each
    # ... assert produced plans match a frozen baseline file in
    #     tests/fixtures/phase9-baseline-plans.json
```
The test compares `[(p.action.value, p.name, sorted(p.diff_fields)) for p in result.plan]` (tuple-projection — avoids pydantic model identity issues) against the frozen fixture.

**Pitfall 7 callout — DO NOT USE `tools/scripts/byte-equivalence-diff.sh`:**
RESEARCH.md §Pitfall 7 (line 717+) + §Q3 (line 310) are explicit:
> CONTEXT.md §D-15 references `tools/scripts/byte-equivalence-diff.sh` for the Phase 9 SC#4 dispositive. But that script is for `helm template` output diff (`kubectl apply --dry-run=client` round-trip), NOT for `arrconf dump` output diff.

The SC#4 dispositive is a **pytest** that walks `result.plan` across all 6 reconcilers and diffs against the frozen fixture — NOT a shell harness wrapping `arrconf dump`.

---

### `tools/arrconf/tests/fixtures/phase9-baseline-plans.json` (NEW — frozen baseline)

**Primary analog:** `tools/arrconf/tests/fixtures/sonarr_*.json` family — same dir, same convention (recorded JSON, loaded via `json.loads(Path(...).read_text())`).

**Generation procedure (one-off, before the test is committed):**
1. Check out `main` immediately before any `RootConfig.categories` code lands.
2. Run the reconciler-plan walker against `charts/arr-stack/files/arrconf.yml` (without categories block — i.e. current v0.2.0 state).
3. Serialize the plan list of every reconciler into a sorted JSON dict keyed by `(app, resource_kind, name)`.
4. Commit as `tools/arrconf/tests/fixtures/phase9-baseline-plans.json`.

Once the Phase 9 code (RootConfig.categories + arrconf.yml categories block) lands, re-running the walker against the **same v0.2.0-shaped arrconf.yml** (with categories stripped — synthetic input) MUST produce the same tuples → diff is empty → SC#4 holds.

The fixture file is read-only after first commit. If a future Phase 10 changes plan output, the fixture is regenerated **and** SC#4 is re-evaluated against the new baseline.

---

### `charts/arr-stack/templates/categories-init-job.yaml` (NEW — Helm Job + hooks)

**Primary analog:** `charts/arr-stack/templates/arrconf-configmap.yaml` (entire file — 11 lines)
**Secondary analog (image + securityContext + media-nas-pvc):** `charts/arr-stack/values.yaml` lines 50-70 (sonarr persistence) + lines 17-24 (image with renovate annotation)

**ConfigMap-template precedent — `.Files.Get` + `arr-stack.labels` helper + `metadata.namespace`** (arrconf-configmap.yaml:1-11 — the FULL file):
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: arrconf-config
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "arr-stack.labels" . | nindent 4 }}
data:
  arrconf.yml: |
    {{- .Files.Get "files/arrconf.yml" | nindent 4 }}
```
→ Phase 9 Job template reuses ALL THREE patterns:
1. `namespace: {{ .Release.Namespace }}` (line 5)
2. `labels: {{- include "arr-stack.labels" . | nindent 4 }}` (lines 6-7)
3. `{{ .Files.Get "files/arrconf.yml" ... }}` (line 10) — RESEARCH.md Q1 dispositively confirmed that piping through `| fromYaml` works in Helm 3.18 against this exact file.

**`arr-stack.labels` helper definition (read-only)** (`_helpers.tpl:1-10`):
```yaml
{{/*
Common labels for arr-stack umbrella-owned objects (ConfigMaps for arrconf + configarr).
Per-alias app-template renders carry their own labels — this helper applies only
to objects authored directly in charts/arr-stack/templates/.
*/}}
{{- define "arr-stack.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: arr-stack
{{- end }}
```
The new Job uses this same helper — NO new helper needed (RESEARCH.md line 615: "use `{{ .Release.Name }}-categories-init` directly. Recommended: hardcode the latter to minimize chart surface" — i.e. no new `arr-stack.fullname` helper either).

**Renovate annotation + image-pin pattern** (values.yaml:17-20 — sonarr image pin):
```yaml
image:
  # renovate: image=lscr.io/linuxserver/sonarr
  repository: lscr.io/linuxserver/sonarr
  tag: "4.0.17"
```
→ Phase 9 places the same annotation directly above the busybox image (D-11):
```yaml
# renovate: image=docker.io/busybox
image: busybox:1.36.1
```
(Note: in a Job spec the value is a single `image:` string, not a `repository:`/`tag:` split — but the `# renovate: image=...` annotation form is identical and `customManagers` in Renovate's config already matches both shapes.)

**`media-nas-pvc` volume mount pattern** (values.yaml:65-70 — sonarr media volume):
```yaml
media:
  # NAS NFS — destination finale des séries
  type: persistentVolumeClaim
  existingClaim: media-nas-pvc
  globalMounts:
    - path: /media
```
→ Phase 9 Job uses raw K8s spec (not app-template DSL), so it expands to (RESEARCH.md §Pattern 3 lines 605-611):
```yaml
volumeMounts:
  - name: media
    mountPath: /media
volumes:
  - name: media
    persistentVolumeClaim:
      claimName: media-nas-pvc
```

**Helm-hook annotations (D-07)** — no existing in-repo analog; first hooked Job in the chart. The shape comes from RESEARCH.md §Pattern 3 lines 565-568:
```yaml
annotations:
  "helm.sh/hook": pre-install,pre-upgrade
  "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
  "helm.sh/hook-weight": "0"
```

---

### `tools/arrconf/arrconf/config.py` (MODIFIED — add 1 import + 1 field)

**Primary analog:** self — config.py:28 (existing `Category` import for qBit) + config.py:621-642 (existing `RootConfig` class)

**Import-add pattern (BEWARE NAME COLLISION)** — config.py:28 already does:
```python
from arrconf.resources.qbittorrent.category import Category
```
→ Phase 9 introduces a SECOND `Category` symbol from `arrconf.resources.categories`. The import MUST alias to avoid collision. Two acceptable forms (planner picks):
```python
# Option A — alias the new one:
from arrconf.resources.categories import Category as MediaCategory

# Option B — alias the old qBit one (more invasive, touches every existing reference):
from arrconf.resources.qbittorrent.category import Category as QbitCategory
from arrconf.resources.categories import Category
```
Option A minimizes blast radius (only the new field declaration uses the new symbol; nothing else needs renaming). Final pick is Claude's discretion per CONTEXT.md.

**Field-add pattern** (config.py:636-642 — `RootConfig` class body):
```python
class RootConfig(BaseModel):
    """Top-level arrconf YAML schema (root for JSON Schema generation).
    ...
    """

    model_config = ConfigDict(extra="forbid")
    sonarr: dict[str, SonarrInstance] = Field(default_factory=dict)
    radarr: dict[str, RadarrInstance] = Field(default_factory=dict)
    prowlarr: dict[str, ProwlarrInstance] = Field(default_factory=dict)
    qbittorrent: dict[str, QbittorrentInstance] = Field(default_factory=dict)
    seerr: dict[str, SeerrInstance] = Field(default_factory=dict)
    jellyfin: dict[str, JellyfinInstance] = Field(default_factory=dict)
```
→ Phase 9 adds (RESEARCH.md §Pattern 2 — "FIRST field" recommendation, line 545):
```python
class RootConfig(BaseModel):
    """...

    Phase 9 (D-05): adds top-level ``categories`` list — cross-cutting,
    drives Phase 10 propagation to qBit/Sonarr/Radarr/configarr/Seerr/Jellyfin.
    """

    model_config = ConfigDict(extra="forbid")
    categories: list[MediaCategory] = Field(default_factory=list)  # NEW — FIRST field
    sonarr: dict[str, SonarrInstance] = Field(default_factory=dict)
    # ... rest unchanged
```
The `default_factory=list` mirrors the `default_factory=dict` pattern of all sibling fields — same optionality semantics (CONTEXT.md D-05).

**Class-docstring update pattern** — add a "Phase 9 (D-05)" paragraph to the existing docstring (lines 622-635) mirroring the prior "Phase 3", "Phase 5 (D-05-QBT-02)", "Phase 6 (D-06-SCOPE-01)", "Phase 7 (D-07-INSTANCE-01)" pattern. Single-line update, append.

---

### `charts/arr-stack/files/arrconf.yml` (MODIFIED — prepend 10-entry block)

**Primary analog:** self — current file header (lines 1-2: modeline + blank line) + first top-level key (line 3: `sonarr:`)

**Modeline + first-key pattern** (arrconf.yml:1-3):
```yaml
# yaml-language-server: $schema=../../../schemas/arrconf-schema.json

sonarr:
  main:
    base_url: http://sonarr.selfhost.svc.cluster.local:8989
```
→ Phase 9 inserts the 10-entry `categories:` block between line 2 (blank) and line 3 (`sonarr:`). Exact content is CONTEXT.md §Specifics lines 351-401 (verbatim — planner copies the YAML literal). The modeline + blank line are preserved unchanged.

---

### `schemas/arrconf-schema.json` (MODIFIED — regenerated)

**No analog to copy from — this file is generated, not authored.**

The generator is `tools/arrconf/arrconf/schema_gen.py:33` (from RESEARCH.md Q4 line 329):
```python
def write_schema(output_path: Path) -> None:
    """Write JSON Schema reproducibly (sort_keys=True for D-15 git diff check)."""
    schema = RootConfig.model_json_schema(schema_generator=Draft202012Generator)
    output_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
```

The CI gate that enforces freshness is `tools/arrconf/tests/test_schema_gen.py:49-61` (existing — Phase 9 does NOT add to this file):
```python
def test_schema_committed_matches_regen(tmp_path: Path) -> None:
    """The committed schemas/arrconf-schema.json must match a fresh regen (D-15 CI gate)."""
    committed = Path(__file__).parent.parent.parent.parent / "schemas/arrconf-schema.json"
    if not committed.exists():
        return  # Pre-commit run before schema-gen has been wired
    out = tmp_path / "regen.json"
    write_schema(out)
    assert committed.read_bytes() == out.read_bytes(), (
        "schemas/arrconf-schema.json drifted from regen output. "
        "Run `cd tools/arrconf && uv run arrconf schema-gen "
        "--output ../../schemas/arrconf-schema.json` and commit."
    )
```
→ Phase 9 procedure: after `RootConfig.categories` lands, run `cd tools/arrconf && uv run arrconf schema-gen --output ../../schemas/arrconf-schema.json` ONCE and commit the regenerated file. No additional gate code needed (D-16).

---

### `CLAUDE.md` (MODIFIED — append new section)

**Primary analog:** self — existing "## Pattern single-instance + tags" section (lines 316-338) for placement; existing "## Workflow snapshot" subsection (under "## Workflow de développement", around line 261) for bash-code-block style.

**Section-header + bash-block pattern** — verified by reading existing CLAUDE.md sections. Standard structure: `## <Title>` heading, opening paragraph, then ` ```bash ` fenced blocks for copy-paste commands. The migration runbook should follow CONTEXT.md §D-17 exactly:
1. **Pre-check** (snapshot baseline command — reuses existing `tools/snapshot/snapshot.sh` pattern documented in CLAUDE.md "Workflow snapshot" lines ~230-265)
2. **Mapping table** (6 rows — CONTEXT.md §D-17 lines 211-217 lists the v0.2.0 → v0.3.0 dir mapping)
3. **Execution** (`kubectl exec` + `mv` commands)
4. **Post-check** (Sonarr/Radarr rescan POST + snapshot diff)
5. **Rollback** (inverse `mv` — kept brief)

**Placement (CONTEXT.md §Specifics line 452):** AFTER `"## Pattern single-instance + tags"` (line 316) and BEFORE `"## Intégration avec my-kluster"` (line 339).

**Title (CONTEXT.md §Specifics line 452):** `"## Filesystem migration: v0.2.0 flat → v0.3.0 Categories"` (NOTE — the planner subtask hint uses `→` but CONTEXT specifies the literal title; both forms are interchangeable for the planner's plan-step text).

---

### `charts/arr-stack/values.yaml` (MODIFIED — single-line image tag bump)

**Primary analog:** self — line 451 (`tag: "0.5.0"`) in the `arrconf.controllers.main.containers.main.image` block (lines 446-452):
```yaml
containers:
  main:
    image:
      # renovate: image=ghcr.io/tom333/arr-stack-arrconf
      repository: ghcr.io/tom333/arr-stack-arrconf
      tag: "0.5.0"
      pullPolicy: IfNotPresent
```
→ Phase 9 bumps `tag: "0.5.0"` → `tag: "<next-auto-tag>"` (per RESEARCH.md "Plan D" CF-07-CHART-PIN-LOOP — the auto-tag the chart-lint workflow will create on merge). This is a one-line edit; no structural changes elsewhere in the file.

**IMPORTANT:** Phase 9 does NOT add a `categoriesInit.basePaths` key under `arrconf:` or anywhere else in `values.yaml`. RESEARCH.md Q1 dispositively pivoted from D-08's values.yaml-driven Job to the single-source `.Files.Get | fromYaml` pattern, which reads `categories[]` directly from `files/arrconf.yml` at template-render time. The Job template self-resolves; no new values key needed; no CI sync gate needed.

---

## Shared Patterns

### Pydantic resource conventions

**Source:** `tools/arrconf/arrconf/resources/qbittorrent/category.py` + `tools/arrconf/arrconf/resources/sonarr/download_client.py`
**Apply to:** `tools/arrconf/arrconf/resources/categories.py`

- `from __future__ import annotations` at module top
- Module-docstring with phase-decision references (e.g. "Phase 9 D-04/D-05")
- `model_config = ConfigDict(extra="forbid")` (D-04 strict — RootConfig already enforces this)
- `Field(description="...")` on every public field (REQ-yaml-autocomplete — surfaces as VS Code hover tooltips per `test_schema_gen.py:33-46`)
- `Literal[...]` type aliases at module scope for closed-set enums (D-01/D-02)
- `@model_validator(mode="after")` for cross-field invariants (D-04 `base_path == /media/{name}`)

### Test file conventions

**Source:** `tools/arrconf/tests/test_scope_violation.py` + `tools/arrconf/tests/test_config.py`
**Apply to:** `tools/arrconf/tests/test_categories.py`, `tools/arrconf/tests/test_phase9_no_regression.py`

- `from __future__ import annotations` at module top
- Module-docstring naming the requirement IDs (e.g. "REQ-categories-schema", "D-04")
- `@pytest.mark.parametrize("module", ..., ids=lambda m: ...)` for invariant tables
- `with pytest.raises(ValidationError, match=r"...")` for failure-path assertions
- Fixtures live in `tools/arrconf/tests/fixtures/<app>_<resource>.json` (JSON) — Phase 9 fixture `phase9-baseline-plans.json` follows the same naming convention even though it's a baseline-plan snapshot, not a recorded API response

### Helm chart template conventions

**Source:** `charts/arr-stack/templates/arrconf-configmap.yaml` + `_helpers.tpl`
**Apply to:** `charts/arr-stack/templates/categories-init-job.yaml`

- `metadata.namespace: {{ .Release.Namespace }}`
- `metadata.labels: {{- include "arr-stack.labels" . | nindent 4 }}`
- `.Files.Get "files/<name>.yml"` for in-chart file reads (RESEARCH.md Q1 confirms `| fromYaml` works)
- No `arr-stack.fullname` helper needed — use `{{ .Release.Name }}-categories-init` directly (RESEARCH.md line 615)
- File lives at `charts/arr-stack/templates/<app>-<resource>.yaml` per CLAUDE.md "Templates custom" line ~177

### Renovate annotation placement

**Source:** `charts/arr-stack/values.yaml` (11 existing instances — sonarr line 17, radarr line 82, ... arrconf line 449)
**Apply to:** the new busybox image line in `templates/categories-init-job.yaml`

```yaml
# renovate: image=<full-image-ref>
<image-field>: <image-ref>:<tag>
```
The comment goes DIRECTLY ABOVE the image-pin line, no blank line between. Verified pattern in every existing image declaration. CLAUDE.md "Conventions Helm — umbrella chart" §"Annotations Renovate (CRITIQUE)" enforces this.

### Schema regeneration discipline

**Source:** `tools/arrconf/arrconf/schema_gen.py:33` + `tools/arrconf/tests/test_schema_gen.py:49-61` + `.github/workflows/tests.yml:50-57`
**Apply to:** Phase 9 procedure (NOT a code add — operator discipline only)

- After any `RootConfig` field change: run `cd tools/arrconf && uv run arrconf schema-gen --output ../../schemas/arrconf-schema.json`
- `diff -q` (byte-strict) is dispositive because `sort_keys=True` + pinned `pydantic>=2.13,<3` is byte-stable across runs (RESEARCH.md Q4)
- The CI workflow (`tests.yml:50-57`) re-runs the generator and `git diff --exit-code` blocks merge on drift — Phase 9 does NOT need a new gate

---

## No Analog Found

| File | Reason | Mitigation |
|------|--------|------------|
| `tools/arrconf/tests/test_phase9_no_regression.py` (cross-app reconciler-plan walker) | All existing reconciler tests are scoped to a single app + use mocked HTTP per `pytest.mark.respx`. The new test walks plan output across 6 reconcilers from a single arrconf.yml input — no precedent for the cross-cutting "load arrconf.yml + invoke all 6 reconcilers in dry-run + collect plans" pattern. | Follow RESEARCH.md Q3 pseudo-code (lines 301-308); base each per-app call on the existing `test_reconcilers_<app>.py` setup (respx mocks for GET endpoints + `dry_run=True`). Planner authors a small helper `_dry_run_all_apps(cfg) -> dict[str, list[PlanTuple]]` and the test asserts equality with the frozen fixture. |
| `charts/arr-stack/templates/categories-init-job.yaml` (Helm-hooked Job) | Existing umbrella chart has only ConfigMap custom templates — first `Job` template authored directly under `templates/`. The bjw-s app-template aliases produce all other Jobs (the two CronJobs for arrconf + configarr). | Use RESEARCH.md §Pattern 3 skeleton (lines 555-612) verbatim as the starting point; rely on `helm template` + `kubeconform` in chart-lint.yml to validate the manifest shape. |

---

## Metadata

**Analog search scope:**
- `tools/arrconf/arrconf/resources/` (qbittorrent, sonarr, radarr, prowlarr, seerr, jellyfin subdirs)
- `tools/arrconf/arrconf/config.py` + `tools/arrconf/arrconf/schema_gen.py` + `tools/arrconf/arrconf/reconcilers/`
- `tools/arrconf/tests/` (23 existing test files)
- `charts/arr-stack/templates/` (3 existing files)
- `charts/arr-stack/files/` + `charts/arr-stack/values.yaml`
- `tools/scripts/` (2 helper scripts — confirmed `byte-equivalence-diff.sh` is helm-template-only per Pitfall 7)
- `CLAUDE.md` (existing section structure for the new migration runbook)

**Files scanned:** ~40 (10 reads + ~30 grep/glob)
**Pattern extraction date:** 2026-05-18
