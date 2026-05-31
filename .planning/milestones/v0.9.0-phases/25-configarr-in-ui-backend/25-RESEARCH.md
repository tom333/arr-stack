# Phase 25: configarr-in-UI backend - Research

**Researched:** 2026-05-29
**Domain:** FastAPI + pydantic v2 + ruyaml round-trip IO; configarr (raydak-labs) config schema + validation modes
**Confidence:** HIGH (all claims verified against the real configarr source @ HEAD `df5792a` and the in-repo code; one D-08 escalation surfaced)

## Summary

This phase adds configarr.yml read/validate/diff/write to the arrconf-ui backend, symmetric to the existing arrconf.yml endpoints, with zero secret-leak risk through `!env`/`!secret` tag drop. The work is almost entirely **pattern-cloning** of code that already exists in `tools/arrconf-ui/`: the ruyaml IO layer (`io.py`), the FastAPI endpoint shape (`app.py`), the schema-generation mechanism (`arrconf/schema_gen.py`), and the `extra="forbid"` strictness pattern (`arrconf/config.py:45`). The genuinely new artifacts are (1) a hand-written `ConfigarrRootConfig` pydantic model living in `tools/arrconf-ui/` only (ADR-5), (2) a configarr-shape structured diff, and (3) a CI validation gate.

Two findings change the plan materially. **First (read-path bug, not in CONTEXT):** D-10 is only half-true. ruyaml's round-trip *write* path preserves `!env SONARR_API_KEY` verbatim (verified) — but the *read* path used by the existing arrconf endpoints (`_read_current()` → `json.loads(json.dumps(raw, default=str))`) **silently strips the tag**, turning `!env SONARR_API_KEY` into the bare string `"SONARR_API_KEY"`. The configarr GET and diff endpoints MUST NOT reuse that JSON-coercion helper; they must reconstruct the literal `!env SONARR_API_KEY` from the ruyaml `TaggedScalar` (mechanism documented below). SC#4 fails if the arrconf `_read_current()` shortcut is copied.

**Second (D-08, ESCALATION):** configarr v1.28.0 has **no offline/parse-only/validate-only/schema command**. `DRY_RUN=true` only suppresses *write* mutations — the sync `pipeline()` still calls `getSystemStatus()`, `loadServerCustomFormats()`, `loadQualityDefinitionFromServer()`, `getLanguages()` against a live *arr before any DRY_RUN guard. Config "validation" at startup is a TypeScript cast (`as InputConfigSchema`), not a zod runtime gate, so there is no deep config validation that runs without a live *arr. The only network-isolated-from-*arr path requires `sonarrEnabled: false` + `radarrEnabled: false`, which makes configarr a no-op (it validates nothing meaningful and still clones TRaSH/Recyclarr from GitHub). **This blocks the literal reading of SC#5/D-07. See `## BLOCKER / ESCALATION`.**

**Primary recommendation:** Build the IO/model/endpoints by cloning the existing arrconf-ui patterns, but write a **tag-preserving read helper** (not the arrconf JSON shortcut) and ship the task-zero round-trip test first. For the CI gate, escalate D-08 to the user before settling — `configarr --dry-run` does NOT satisfy "validate without connecting to live *arr."

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** `ConfigarrRootConfig` uses `extra="forbid"` — mirrors arrconf's `RootConfig` (`tools/arrconf/arrconf/config.py:45`). Unknown top-level keys are rejected, not silently passed through.
- **D-02:** Because `forbid` rejects any unmodeled key, **every** top-level key of `configarr.yml` must be modeled — including read-only sections. Editable subset (`quality_profiles`, `custom_formats`, `customFormatDefinitions`, `language`) is fully typed AND editable; `quality_definition` + `media_naming` fully typed but marked `readOnly: true`. Also model: `trashGuideUrl`, `recyclarrConfigUrl`, and any other present top-level keys.
- **D-03:** Read-only sections are **fully typed** (not opaque `dict[str,Any]`). Tradeoff: max validation strength at cost of model/schema churn. Research must map complete `quality_definition` + `media_naming` shape.
- **D-04:** `api_key` holds a `!env`/`!secret` tag reference (e.g. `!env SONARR_API_KEY`), not a literal secret. Treat as opaque string; the tag reference is safe to surface (variable name, not a secret). `api_key` marked `readOnly: true`.
- **D-05:** Build a **configarr-specific structured diff** (per-quality-profile, per-custom-format semantic grouping) — do NOT reuse `arrconf_ui/diff.py` (hard-coded to arrconf's `categories` + `APP_SECTIONS`).
- **D-06:** Diff MUST operate on round-trip data so `!env`/`!secret` tags appear as literals (`!env SONARR_API_KEY`) in output, never resolved. Hand-preserve tag literals — no resolver / `model_dump` path that drops the tag.
- **D-07:** Require **native configarr validation** as the authoritative gate — the UI's pydantic layer is NOT the authority. configarr is.
- **D-08:** configarr `--dry-run` availability in v1.28.0 is **unconfirmed** (carry-forward blocker). Research MUST find a configarr mode that validates the YAML **without connecting to live Sonarr/Radarr**. If exists → CI gate. **If NO such mode exists → STOP and escalate before settling.** Do NOT silently fall back to pydantic-only. (Ephemeral-*arr-in-CI considered and rejected as default.)
- **D-09:** Beyond task-zero round-trip test, add a **runtime guard** on `PUT /api/configarr/config`: after atomic write, re-read and assert every `!env`/`!secret` tag is byte-present; if any lost, **roll back the write and return 500**.
- **D-10:** ruyaml round-trip (`YAML(typ="rt")` in `io.py`) **already preserves `!env`/`!secret` verbatim today** (verified against real configarr.yml). Existing `io.py` read/write helpers reusable as-is for the IO layer; task-zero test expected to pass against current code; runtime guard (D-09) protects against drift.
  - **⚠️ RESEARCH AMENDMENT:** D-10 is true for the `io.py` *write* path (`write_yaml_atomic` / `dump_yaml_to_str`) and the raw `read_yaml`. It is **NOT** true for the arrconf endpoints' `_read_current()` helper in `app.py`, which JSON-coerces and drops the tag. See Pitfall 1.

### Claude's Discretion
- Endpoint wiring details, error-response shapes, schema-generation mechanics — follow existing arrconf endpoint patterns in `app.py`.
- Whether `ConfigarrRootConfig` is one file or split per-section — planner's call (KISS).

### Deferred Ideas (OUT OF SCOPE)
- None. Frontend selector/form = Phase 26 (CFGUI-04); TRaSH name-picker + Recyclarr reference = Phase 27 (CFGUI-05, CFGUI-06).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CFGUI-01 | Backend reads/validates configarr.yml symmetric to arrconf.yml | Clone `app.py` GET/PUT/schema/diff + new `ConfigarrRootConfig` model; full schema mapped in `## Standard Stack`/Code Examples |
| CFGUI-02 | `api_key` (and read-only sections) marked `readOnly: true` in JSON Schema; no secret leak | `json_schema_extra={"readOnly": True}` verified to emit `"readOnly": true`; TaggedScalar reconstruction preserves `!env` literal |
| CFGUI-03 | `ConfigarrRootConfig` lives in `tools/arrconf-ui/` ONLY (ADR-5); no `*arr` URL in arrconf-ui source | Model is hand-written local file; endpoints read/write a file only — never construct a Sonarr/Radarr URL. `base_url` is stored/echoed verbatim, never dialed |
| CFGUI-07 | CI gate validates written configarr.yml via configarr's own validator | **BLOCKED** — see `## BLOCKER / ESCALATION`. No offline configarr validate mode exists in v1.28.0 |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Read/parse configarr.yml | API / Backend (FastAPI) | — | Backend owns file IO; ruyaml round-trip in `io.py` |
| Validate configarr.yml shape | API / Backend (pydantic) | CI (pydantic gate) | pydantic gives editor-time + 422 feedback AND is the authoritative CI gate (D-08 Option C — configarr has no offline validate mode; D-07 downgraded) |
| Atomic write + anti-leak guard | API / Backend | — | `write_yaml_atomic` + D-09 re-read/rollback; never client-side |
| Structured diff | API / Backend | Browser (Phase 26 renders) | Backend computes; frontend (Phase 26) only displays |
| JSON Schema (readOnly markers) | API / Backend | Browser (Phase 26 FieldInput.svelte consumes) | Backend emits markers; frontend honors them later |
| **Actual *arr API contact** | **configarr (external, in-cluster)** | — | **NEVER arrconf-ui.** ADR-5 / SC#3 boundary — arrconf-ui touches a file, not a *arr |
| TRaSH/Recyclarr template resolution | configarr (external) | — | configarr clones the guide repos; out of arrconf-ui scope |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | >=0.115,<0.116 | HTTP endpoints | [VERIFIED: tools/arrconf-ui/pyproject.toml] already the UI framework |
| pydantic | >=2.13,<3 | `ConfigarrRootConfig` validation + JSON Schema gen | [VERIFIED: pyproject.toml] mirrors arrconf `RootConfig` |
| ruyaml | >=0.91,<0.92 | round-trip YAML, preserves `!env`/`!secret` tags | [VERIFIED: pyproject.toml + empirical test] `TaggedScalar` survives dump |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=9.0,<10 | task-zero round-trip test + endpoint tests | [VERIFIED: pyproject.toml] |
| httpx | >=0.28,<0.29 | FastAPI TestClient transport in tests | [VERIFIED: pyproject.toml] (NOT for *arr calls) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Fully-typed read-only model (D-03) | `dict[str, Any]` opaque sections | D-03 explicitly rejects this — user chose max validation strength; opaque dicts lose schema-driven UI markers in Phase 26 |
| Reconstruct `!env` from TaggedScalar | ruyaml round-trip the whole tree on every GET | Round-trip preserves bytes but GET returns JSON; you still need the literal string for the JSON body — reconstruction is unavoidable |

**Installation:** No new dependencies. All required libs are already in `tools/arrconf-ui/pyproject.toml`.

**Version verification:** configarr current release = **v1.28.0** [VERIFIED: `git ls-remote --tags github.com/raydak-labs/configarr` → v1.28.0 latest]. Matches the project's expectation. No npm/pip package to bump for arrconf-ui.

## configarr.yml Complete Schema Map (D-02 / D-03)

> Verified against the real `charts/arr-stack/files/configarr.yml` AND configarr source `src/types/config.types.ts` + `src/types/trashguide.types.ts` @ HEAD `df5792a` (v1.28.0). Because `extra="forbid"`, **every** key below must be modeled.

### Top-level keys (`InputConfigSchema`) — [VERIFIED: configarr src/types/config.types.ts:6-60]

Present in the **real file** (must be modeled, editable unless noted):
- `trashGuideUrl?: str` — present (line 18 of configarr.yml)
- `recyclarrConfigUrl?: str` — present (line 19)
- `customFormatDefinitions?: list[CustomFormatDefinition]` — present (line 24), **editable**
- `sonarr?: dict[str, ArrInstance]` — present (line 141), nested by instance key (`main`)
- `radarr?: dict[str, ArrInstance]` — present (line 306), nested by instance key (`main`)

**Not in the real file but in configarr's schema** — DECISION POINT for the planner: with `extra="forbid"` you only need to model keys that *could appear* in the file you round-trip. The real file uses only the 5 above. The full configarr top-level surface (model these as `Optional` defaulting to unset so future edits don't break, but they are NOT in the current file):
`trashRevision`, `recyclarrRevision`, `localCustomFormatsPath`, `localConfigTemplatesPath`, `enableFullGitClone`, `telemetry`, `compatibilityTrashGuide20260219Enabled`, `silenceTrashConflictWarnings`, `silenceRequiredCfGroupExclusionWarnings`, `sonarrEnabled`, `radarrEnabled`, `whisparr`/`whisparrEnabled`, `readarr`/`readarrEnabled`, `lidarr`/`lidarrEnabled`.

**Recommendation [ASSUMED — confirm with user]:** Model exactly the 5 real-file keys + the per-instance fields actually used. `extra="forbid"` rejecting `whisparr` etc. is *correct* for this project (those *arrs are explicitly out of scope per CLAUDE.md/PROJECT.md). If the user ever wants to add `sonarrEnabled`/`radarrEnabled` (needed if D-08 escalation lands on the disabled-instance gate), those two keys must be added. This is a real tension — flagged in Open Questions.

### Per-instance shape (`sonarr.main` / `radarr.main`) — [VERIFIED: config.types.ts:185-318]

Fields present in the **real file**:
- `base_url: str` — **NOTE: this is a *arr URL string stored in the file.** ADR-5/SC#3 says no *arr URL appears in arrconf-ui *source*; storing/echoing the value read from the file is fine — the prohibition is on arrconf-ui *constructing or dialing* a URL. The model field holds the string; nothing calls it.
- `api_key: str` — holds `!env SONARR_API_KEY` TaggedScalar; **`readOnly: true`** (D-04/CFGUI-02)
- `media_naming?: MediaNaming` — present; **`readOnly: true`** (D-02)
- `quality_definition?: QualityDefinition` — present; **`readOnly: true`** (D-02)
- `quality_profiles: list[QualityProfile]` — present; **editable**
- `custom_formats?: list[CustomFormat]` — present; **editable**

Other per-instance fields in configarr's schema (NOT in real file; model only if you want forward-compat — same `extra="forbid"` tension as above): `enabled`, `delete_unmanaged_custom_formats`, `delete_unmanaged_quality_profiles`, `include`, `custom_format_groups`, `trash_cfgroup_config`, `media_management`, `ui_config`, `media_naming_api`, `renameQualityProfiles`, `cloneQualityProfiles`, `metadata_profiles`, `delete_unmanaged_metadata_profiles`, `root_folders`, `delay_profiles`, `download_clients`.

### `media_naming` (readOnly, fully typed) — [VERIFIED: config.types.ts:386-403]
```
MediaNaming:
  # radarr keys
  folder?: str
  movie?: { rename?: bool, standard?: str }
  # sonarr keys
  series?: str
  season?: str
  episodes?: { rename?: bool, standard?: str, daily?: str, anime?: str }
```
Both sonarr (series/season/episodes) and radarr (folder/movie) keys live in the SAME type (configarr does not split them). Real file confirms: Sonarr uses `series/season/episodes` (line 146), Radarr uses `folder/movie` (line 311). Model all keys Optional.

### `quality_definition` (readOnly, fully typed) — [VERIFIED: config.types.ts:212-217 + trashguide.types.ts:3-9]
```
QualityDefinition:
  type?: str                 # "series" | "movie" (free string in schema)
  preferred_ratio?: float    # 0.0-1.0 (not in real file)
  qualities?: list[QualityDefQuality]

QualityDefQuality:           # TrashQualityDefinitionQuality
  quality: str
  title?: str
  min: float
  preferred: float
  max: float
```
Real file confirms `type` + `qualities[]` with `quality/min/preferred/max` (lines 155-191). `title` and top-level `preferred_ratio` absent in real file but in schema — model Optional.

### `quality_profiles[]` (editable, fully typed) — [VERIFIED: config.types.ts:405-436]
```
QualityProfile:
  name: str
  reset_unmatched_scores?: { enabled: bool, except?: list[str] }
  upgrade?:                  # discriminated-ish union on `allowed`
    allowed: bool
    until_quality?: str      # required when allowed=true
    until_score?: int        # required when allowed=true
    min_format_score?: int
  min_format_score?: int
  score_set?: str
  quality_sort?: str
  language?: str             # editable per D-02
  qualities?: list[{ name: str, qualities?: list[str], enabled?: bool }]
```
Real file confirms (lines 194-269). The `upgrade` union (allowed:true requires `until_quality`+`until_score`; allowed:false makes them optional) is a strict-typing nicety — a single model with all-Optional + a `model_validator` is simpler (KISS) than two union members.

### `custom_formats[]` (editable) — [VERIFIED: config.types.ts:61-68]
```
CustomFormat:
  trash_ids?: list[str]
  quality_profiles?: [...]      # DEPRECATED in configarr — do NOT surface
  assign_scores_to?: list[{ name: str, score?: int, use_default_score?: bool }]
```
Real file uses `trash_ids` + `assign_scores_to` only (lines 271-298). Model both; `quality_profiles` is deprecated — omit (the real file doesn't use it; `extra="forbid"` will reject it, which is desirable).

### `customFormatDefinitions[]` (editable) — [VERIFIED: real file + common.types.ts:43-52 + trashguide.types.ts:31-38]
configarr's type is `(TrashCF | ConfigarrCF)[]` = `(TrashCFMeta | ConfigarrCFMeta) & ImportCF`. The **real file** uses the TRaSH-meta variant. Modeled shape (matches lines 24-132 verbatim):
```
CustomFormatDefinition:
  trash_id: str                          # (TrashCFMeta) — real file uses this
  trash_scores?: { default?: int, ... }  # dict of named score sets
  trash_regex?: str
  trash_description?: str
  # configarr-meta variant (NOT in real file): configarr_id, configarr_scores
  # ImportCF fields (the *arr CF resource shape, minus specifications):
  name: str
  includeCustomFormatWhenRenaming?: bool
  specifications: list[Specification]

Specification:                           # *arr CF specification
  name: str
  implementation: str                    # e.g. ReleaseTitleSpecification, ResolutionSpecification
  negate?: bool
  required?: bool
  fields: dict[str, Any] | { value: Any }  # value type varies (str regex OR int resolution)
```
**Important:** `specifications[].fields.value` is `str` for `ReleaseTitleSpecification` but `int` (2160) for `ResolutionSpecification` (real file lines 39 vs 132). Model `fields` as `dict[str, Any]` or `value: int | str` — do NOT over-constrain or valid files break.

## Architecture Patterns

### System Architecture Diagram

```
                     arrconf-ui backend (tools/arrconf-ui/)
                     ─────────────────────────────────────
 operator (LAN) ──▶ GET  /api/configarr/config ──▶ read_yaml(configarr.yml)
                                                    │  (ruyaml CommentedMap, TaggedScalars intact)
                                                    ▼
                                          tag-preserving serializer ──▶ JSON
                                          (reconstruct "!env X" literal)   │  ◀── api_key shows "!env SONARR_API_KEY"
                                                                           ▼  never a resolved secret
 operator (LAN) ──▶ PUT  /api/configarr/config ──▶ ConfigarrRootConfig.model_validate(payload)
                                              │ 422 on invalid
                                              ▼ valid
                                   read on-disk ruyaml ──▶ shallow-merge edited top-keys
                                              ▼            (preserve comments + TaggedScalars)
                                   write_yaml_atomic (tmp + fsync + os.replace)
                                              ▼
                                   D-09 GUARD: re-read, assert every !env/!secret byte-present
                                              │ tag lost? ──▶ rollback + 500
                                              ▼ ok ──▶ return structured diff
 operator (LAN) ──▶ POST /api/configarr/diff ──▶ configarr-shape structured diff (tag literals preserved)
 operator (LAN) ──▶ GET  /api/configarr/schema ──▶ ConfigarrRootConfig.model_json_schema() (readOnly markers)

 ── BOUNDARY (ADR-5 / SC#3) ───────────────────────────────────────────────
 arrconf-ui NEVER calls Sonarr/Radarr. configarr (separate in-cluster CronJob)
 reads the SAME configarr.yml and is the only thing that dials the *arr APIs.
```

### Recommended Project Structure
```
tools/arrconf-ui/arrconf_ui/
├── configarr_config.py   # NEW — ConfigarrRootConfig pydantic model (ADR-5: HERE, never tools/arrconf/)
├── configarr_io.py       # NEW (or reuse io.py) — tag-preserving read→JSON helper + TaggedScalar reconstruction
├── configarr_diff.py     # NEW — configarr-shape structured diff (D-05)
├── io.py                 # REUSE as-is for write_yaml_atomic / read_yaml (D-10)
├── locator.py            # EXTEND — add configarr_yml_path() + configarr_schema_json_path()
└── app.py                # EXTEND — register 4 /api/configarr/* endpoints alongside arrconf ones
schemas/
└── configarr-schema.json # NEW — generated from ConfigarrRootConfig (do NOT touch arrconf-schema.json pipeline)
```

### Pattern 1: Tag-preserving read (the SC#4-critical replacement for `_read_current`)
**What:** Convert ruyaml CommentedMap → JSON-safe dict while reconstructing `!env X` / `!secret X` as the literal string, instead of dropping the tag.
**When to use:** Every configarr GET and diff `before` snapshot.
```python
# Source: empirically verified against ruyaml 0.91 + real configarr.yml
from ruyaml.comments import TaggedScalar

def _tagged_to_literal(node):
    # TaggedScalar.tag.value == "!env"; .value == "SONARR_API_KEY"
    if isinstance(node, TaggedScalar):
        return f"{node.tag.value} {node.value}"        # -> "!env SONARR_API_KEY"
    if isinstance(node, dict):
        return {k: _tagged_to_literal(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_tagged_to_literal(v) for v in node]
    return node
# NEVER do: json.loads(json.dumps(raw, default=str))  <-- drops the tag (see Pitfall 1)
```

### Pattern 2: Write-back reconstructing a TaggedScalar from a literal
**What:** On PUT, if the payload carries `"!env SONARR_API_KEY"` as a string and the field is `readOnly`, you generally re-use the on-disk ruyaml node unchanged (shallow-merge only edited keys). If you must write a tag value, rebuild it.
```python
# Source: empirically verified
from ruyaml.comments import TaggedScalar
ts = TaggedScalar(value="SONARR_API_KEY", style=None)
ts.yaml_set_tag("!env")
# dumps as: api_key: !env SONARR_API_KEY
```
**Preferred (KISS):** Because `api_key`/`media_naming`/`quality_definition` are `readOnly`, the PUT path should shallow-merge only the editable top-level keys into the on-disk ruyaml tree (exactly like `app.py:107-119` does for arrconf) — leaving the TaggedScalar nodes physically untouched. This is the safest anti-leak design and makes the D-09 guard a belt-and-suspenders check.

### Pattern 3: readOnly JSON Schema marker
```python
# Source: empirically verified — emits "readOnly": true in the property schema
from pydantic import BaseModel, ConfigDict, Field

class ArrInstance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_url: str
    api_key: str = Field(json_schema_extra={"readOnly": True})
    media_naming: MediaNaming | None = Field(default=None, json_schema_extra={"readOnly": True})
    quality_definition: QualityDefinition | None = Field(default=None, json_schema_extra={"readOnly": True})
```
Reuse `schema_gen.Draft202012Generator` pattern (sort_keys reproducible write) for the configarr schema. Do NOT modify `arrconf/schema_gen.py` (ADR-5 — that lives in `tools/arrconf/`); write a sibling generator in `tools/arrconf-ui/`.

### Anti-Patterns to Avoid
- **Reusing `_read_current()` from `app.py`** for configarr GET/diff: drops `!env` tags → SC#4 failure. (Pitfall 1.)
- **Reusing `arrconf_ui/diff.py`** for configarr: hard-coded to `categories` + `APP_SECTIONS`; cannot diff configarr shape (D-05).
- **Putting `ConfigarrRootConfig` in `tools/arrconf/`**: violates ADR-5. Lives in `tools/arrconf-ui/` only.
- **Constructing/dialing a *arr URL** anywhere in arrconf-ui: violates SC#3. `base_url` is stored/echoed, never called.
- **Over-constraining `specifications[].fields.value`** to `str`: ResolutionSpecification uses int 2160 → valid file rejected.
- **`model_dump()` of the api_key field for the diff**: any dump path that goes through the resolved string drops the tag. The diff must run on the round-trip (tag-literal) data (D-06).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic YAML write | custom tmp+rename | `arrconf_ui.io.write_yaml_atomic` | Already tmp-in-same-dir + fsync + os.replace, leak-tested (D-10) |
| Tag-preserving round-trip | custom YAML emitter | `ruyaml YAML(typ="rt")` via `io.py._yaml()` | TaggedScalar dump verified verbatim |
| JSON Schema Draft 2020-12 | hand-written schema | `model_json_schema(schema_generator=Draft202012Generator)` | mirrors arrconf; reproducible sort_keys for git-diff CI gate |
| Endpoint scaffolding | new FastAPI app | clone `app.py` GET/PUT/schema/diff handlers | symmetry is the requirement (CFGUI-01) |
| 422 error shape | custom error model | `json.loads(json.dumps(e.errors(), default=str))` pattern from `app.py:93` | already handles non-serializable ctx |

**Key insight:** This phase is ~90% disciplined cloning of existing, tested arrconf-ui code. The only genuinely novel logic is the configarr-shape diff and the tag-literal reconstruction — and the latter is ~10 lines.

## Common Pitfalls

### Pitfall 1: The arrconf `_read_current()` JSON shortcut silently strips `!env`/`!secret` tags
**What goes wrong:** `app.py:_read_current()` does `json.loads(json.dumps(raw, default=str))`. For a `TaggedScalar`, `str(node)` returns only `.value` — so `!env SONARR_API_KEY` becomes the bare string `"SONARR_API_KEY"`. If you clone this for configarr GET/diff, SC#4 fails: the diff shows `SONARR_API_KEY` (a bare var name that *looks* like it could be a value), and the `!env` semantics are lost on round-trip through the API.
**Why it happens:** D-10 only verified the *write* path (`write_yaml_atomic`); nobody verified the *read→JSON* path for configarr because arrconf.yml had no tags worth surfacing.
**How to avoid:** Use the `_tagged_to_literal()` helper (Pattern 1), not the JSON-coercion shortcut. Add a test asserting `GET /api/configarr/config` JSON body contains the literal `!env SONARR_API_KEY`.
**Warning signs:** A diff or GET response containing `"api_key": "SONARR_API_KEY"` instead of `"api_key": "!env SONARR_API_KEY"`.
**Confidence:** HIGH — empirically reproduced (see metadata).

### Pitfall 2: `extra="forbid"` rejects configarr keys not in the real file
**What goes wrong:** configarr's schema has ~20 top-level keys + ~18 per-instance keys; the real file uses 5 + 6. If you model the full configarr surface, fine; if you model only the real-file subset and configarr later adds a key the user wants (e.g. `sonarrEnabled` for the D-08 escalation), `forbid` 422s a legitimate edit.
**Why it happens:** D-03 chose exhaustive typing; "exhaustive" is ambiguous — exhaustive vs. *the file* or vs. *configarr's full schema*?
**How to avoid:** Decide scope explicitly with the user (Open Question 1). Recommended: model the real-file subset + leave a documented extension point. If the D-08 escalation lands on disabled-instance validation, you MUST add `sonarrEnabled`/`radarrEnabled`.
**Warning signs:** 422 on a hand-edit that configarr itself accepts → the pydantic model is stricter than configarr (which D-07 says is *not* the authority).

### Pitfall 3: The `upgrade` block is a conditional-required union
**What goes wrong:** When `allowed: true`, configarr requires `until_quality` + `until_score`; when `allowed: false` they are optional. A naive all-Optional model accepts an `allowed:true` profile missing `until_quality` that configarr would reject.
**How to avoid:** Either a pydantic discriminated union, or a single model + `@model_validator(mode="after")` requiring the two fields when `allowed`. KISS favors the validator. (Note D-07: configarr is the authority anyway — don't agonize over matching its exact required-ness; match it "well enough" and let the CI gate catch the rest.)

### Pitfall 4: `specifications[].fields.value` polymorphism
**What goes wrong:** Modeling `value: str` breaks `ResolutionSpecification` (value=2160 int). The real file has both.
**How to avoid:** `fields: dict[str, Any]` (simplest, KISS) or `value: int | str`. Do not constrain further.

### Pitfall 5: configarr `media_naming` mixes sonarr + radarr keys in one type
**What goes wrong:** Splitting into SonarrMediaNaming/RadarrMediaNaming over-models it; configarr uses one type with all keys Optional. A Sonarr instance with `series` and a Radarr instance with `folder` both validate against the same `MediaNaming` model.
**How to avoid:** One `MediaNaming` model, all fields Optional, matching configarr `MediaNamingType`.

## Code Examples

### Endpoint registration (clone of arrconf, symmetric) — Source: tools/arrconf-ui/arrconf_ui/app.py
```python
@app.get("/api/configarr/config")
def get_configarr_config():
    raw = read_yaml(configarr_yml_path())          # ruyaml, tags intact
    literal = _tagged_to_literal(raw)               # !env preserved as literal
    try:
        validated = ConfigarrRootConfig.model_validate(literal)
    except ValidationError as e:
        detail = json.loads(json.dumps(e.errors(), default=str))
        return JSONResponse(422, {"detail": detail, "raw": literal})
    return validated.model_dump(mode="json")        # NOTE: ensure api_key dump keeps the literal

@app.put("/api/configarr/config")
def put_configarr_config(payload: dict):
    ConfigarrRootConfig.model_validate(payload)      # 422 on invalid
    target = read_yaml(configarr_yml_path())         # preserve comments + TaggedScalars
    for k in ("trashGuideUrl","recyclarrConfigUrl","customFormatDefinitions","sonarr","radarr"):
        if k in payload: target[k] = payload[k]      # shallow-merge editable keys
    write_yaml_atomic(configarr_yml_path(), target)
    # --- D-09 runtime guard ---
    after = configarr_yml_path().read_text("utf-8")
    for tag in ("!env","!secret"):
        # assert each tag count survived (compare against pre-write byte counts)
        ...                                          # rollback + raise 500 on loss
    return {"diff": configarr_diff(...), "has_changes": ...}
```

### D-09 byte-presence guard (anti-leak, defense-in-depth)
```python
# Capture tag occurrences BEFORE write, re-read AFTER, assert >= .
# Roll back by restoring the pre-write bytes (you already read `target`/original text).
before_bytes = configarr_yml_path().read_bytes()
# ... write ...
after_text = configarr_yml_path().read_text("utf-8")
if after_text.count("!env") < expected_env or after_text.count("!secret") < expected_secret:
    configarr_yml_path().write_bytes(before_bytes)   # rollback
    raise HTTPException(500, "anti-leak guard: !env/!secret tag lost on write")
```

## BLOCKER / ESCALATION — D-08 / CFGUI-07 (configarr native validation gate)

**Status: BLOCKED. configarr v1.28.0 has no offline config-validation mode. Escalate to user before settling on the CI gate.**

### What was verified (HIGH confidence, configarr source @ `df5792a`, v1.28.0)
1. **`DRY_RUN=true` does NOT validate offline.** It only suppresses *write* mutations. The `pipeline()` (src/index.ts:38-) unconditionally calls `api.getSystemStatus()`, `loadServerCustomFormats()`, `loadQualityDefinitionFromServer()`, `api.getLanguages()` — all live *arr HTTP — BEFORE the first DRY_RUN guard. [VERIFIED: src/index.ts:38-48, 102, 156, 420]
2. **There is no `validate` / `--check` / `--schema` / parse-only CLI command.** configarr's only entry is `tsx src/index.ts` (npm `start`); no `bin`, no subcommands. [VERIFIED: package.json scripts/bin]
3. **Startup config "validation" is a TypeScript cast, not a runtime gate.** `getConfig()` does `yaml.parse(...) as InputConfigSchema` then `transformConfig()`. There is no zod `.parse()` on the full config — so an invalid config is NOT caught at parse time; errors surface only when the live API is hit during sync. [VERIFIED: src/config.ts:95-117]
4. **The only *arr-network-free path is `sonarrEnabled: false` + `radarrEnabled: false`** (or per-instance `enabled: false`). With those, `runArrType` short-circuits before `configureApi()`. BUT: (a) configarr then validates essentially *nothing* about the profiles/CFs (it skips the whole pipeline), and (b) `run()` still calls `cloneRecyclarrTemplateRepo()` + `cloneTrashRepo()` — **network to GitHub** — before the arr loop. So even this path is not hermetic and provides ~zero validation value. [VERIFIED: src/index.ts:381, 423-460]

**Conclusion:** No configarr mode validates `configarr.yml`'s structure/semantics without a live Sonarr/Radarr. D-07 ("native configarr validation as the authoritative gate") cannot be satisfied as literally written by any offline invocation.

### Options to present to the user (do NOT pick silently)

| # | Option | Hermetic? | Validation strength | Cost |
|---|--------|-----------|--------------------|------|
| A | **Ephemeral *arr-in-CI** (spin up sonarr+radarr containers, seed API keys, run configarr DRY_RUN against them) | No (needs containers + GitHub clone) | HIGH — exercises configarr's real sync logic end-to-end against the written file | High CI complexity; previously *considered & rejected as default* — only revisit if user accepts |
| B | **`sonarrEnabled:false` + `radarrEnabled:false` smoke run** (configarr parses the file, clones guides, exits clean) | No (GitHub clone) | LOW — proves the file parses + tags resolve via `!env`, but skips profile/CF semantic validation | Low; but adds `sonarrEnabled`/`radarrEnabled` keys to the model (Pitfall 2). Weak gate. |
| C | **pydantic-only gate** (the `ConfigarrRootConfig.model_validate` in CI, no configarr at all) | Yes | MEDIUM — strict shape validation, but D-07 explicitly says pydantic is NOT the authority | Lowest; **contradicts D-07** — only acceptable if user downgrades D-07 |
| D | **Hybrid:** pydantic gate in CI now + file an upstream configarr feature request for an offline `validate` command; revisit when it lands | Yes | MEDIUM now | Low; honest about the gap |

**Researcher recommendation (for the orchestrator to relay, not to auto-apply):** Option A is the only thing that satisfies D-07's letter, at real CI cost. If the user will not pay that cost, the honest fallback is **C or D** with an explicit, user-acknowledged downgrade of D-07 (pydantic becomes the gate). Option B is a trap — it looks like "native configarr validation" but validates almost nothing. The orchestrator MUST escalate this choice; do not let the planner default to pydantic-only silently.

## Runtime State Inventory

> This is a code/config phase (new endpoints + model + tests + CI). No data migration, no live-service reconfiguration. Inventory included for completeness.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — phase reads/writes `configarr.yml` (a git-tracked file), no DB | None |
| Live service config | configarr CronJob (in-cluster) consumes the SAME `charts/arr-stack/files/configarr.yml` via ConfigMap. arrconf-ui edits the file in-repo; deployment is unchanged by this phase (no chart change required for the backend itself). | None — verified: arrconf-ui edits the source file; configarr picks it up via the existing ConfigMap mount on next ArgoCD sync |
| OS-registered state | None | None |
| Secrets/env vars | `SONARR_API_KEY` / `RADARR_API_KEY` referenced via `!env` in configarr.yml. These are configarr's runtime env (injected in-cluster), NOT read by arrconf-ui. arrconf-ui only surfaces the `!env NAME` *literal*, never the value. | None — arrconf-ui must NOT read these env vars |
| Build artifacts | New `schemas/configarr-schema.json` generated artifact (commit it; add a CI reproducibility check mirroring arrconf's "Verify schema reproducibility (D-15)" step) | Generate + commit; add CI diff-check |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| configarr separate `recyclarr` CFs only | TRaSH cf-groups + `custom_format_groups` + `trash_cfgroup_config` | v1.28.0 (since v1.12 experimental) | Real file doesn't use cf-groups; model only what the file uses |
| `quality_profiles` under CF entry (`custom_formats[].quality_profiles`) | `assign_scores_to` | configarr deprecated `quality_profiles` | Model `assign_scores_to`; omit deprecated `quality_profiles` (real file uses the new key) |

**Deprecated/outdated:**
- `custom_formats[].quality_profiles` — replaced by `assign_scores_to`. Do not model/surface.

## Project Constraints (from CLAUDE.md)

- **Triade Python before commit (gates CI):** `uv run ruff format --check . && uv run ruff check . && uv run mypy .` from `tools/arrconf-ui/`. CI runs the exact same in the `arrconf-ui-backend` job. [VERIFIED: .github/workflows/tests.yml:108-118]
- **mypy gate scope:** the `arrconf-ui-backend` job runs `mypy .` (whole package, including tests) — stricter than arrconf's `mypy arrconf`. New code must be clean under `mypy .`. [VERIFIED: tests.yml:115]
- **No secrets committed:** `!env`/`!secret` are variable-name references, safe; never write a resolved key.
- **ADR-5 frontier:** `ConfigarrRootConfig` in `tools/arrconf-ui/` ONLY, never `tools/arrconf/`. No *arr API URL constructed/dialed in arrconf-ui source (SC#3).
- **No release co-bump:** this phase touches only `tools/arrconf-ui/**` (+ `schemas/configarr-schema.json` + `.github/workflows/`), NOT `tools/arrconf/**` → **do NOT bump `arrconf.image.tag`** (CLAUDE.md "Exception" rule). arrconf-ui changes are CI-isolated from the chart auto-tag (D-17-WORKFLOW-01).
- **Pin dependencies:** no new deps needed; if any added, pin in `pyproject.toml`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Model the real-file top-level subset (5 keys) + used per-instance fields, NOT configarr's full ~20-key surface | Schema Map / Pitfall 2 | If user wants forward-compat or the D-08 escalation needs `sonarrEnabled`/`radarrEnabled`, `extra="forbid"` 422s legit edits. LOW-MEDIUM — easily extended, but must be a conscious choice |
| A2 | configarr is the authority and the pydantic model need not perfectly match configarr's conditional-required rules (e.g. `upgrade` union) | Pitfall 3 | If user wants pydantic to be a strong gate (esp. if D-08 lands on Option C), the model must replicate configarr's required-ness more faithfully. MEDIUM |
| A3 | The backend edits the in-repo `configarr.yml`; no chart/ConfigMap change needed for the endpoints | Runtime State Inventory | If arrconf-ui runs from a path where `configarr.yml` isn't co-located (locator resolves repo root), path resolution must be verified. LOW — locator already finds repo root |

## Open Questions (RESOLVED)

1. **Model scope: real-file subset vs. configarr's full schema?**
   - What we know: real file uses 5 top-level + 6 per-instance keys; configarr has ~20 + ~18. `extra="forbid"` rejects unmodeled keys.
   - **RESOLVED (planner Assumption A1):** minimal real-file model (5 top-level / 6 per-instance) + documented extension point. `extra="forbid"` rejects out-of-scope *arrs, aligned with PROJECT.md. No `sonarrEnabled`/`radarrEnabled` keys added (D-08 Option B rejected).

2. **D-08 CI gate choice (BLOCKER) — see escalation block.**
   - What we know: no offline configarr validate mode exists.
   - **RESOLVED (user escalation 2026-05-29 → Option C):** pydantic-only CI gate. `ConfigarrRootConfig.model_validate` against the written file in the existing `arrconf-ui-backend` job. No ephemeral *arr containers, no configarr invocation. D-07 downgraded (pydantic = authoritative gate), user-acknowledged. See `25-CONTEXT.md` D-07/D-08.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | arrconf-ui triade + tests | ✓ | (project standard) | — |
| ruyaml | tag-preserving IO | ✓ | 0.91.x (pinned) | — |
| pydantic | model + schema gen | ✓ | 2.13.x (pinned) | — |
| Node/npm | (frontend — Phase 26, not this phase) | n/a | — | — |
| configarr (npx/container) | CI gate (CFGUI-07) IF Option A/B chosen | ✗ in CI by default | v1.28.0 image exists (ghcr) | **Blocked — see escalation**; container image `ghcr.io/raydak-labs/configarr` available if Option A taken |
| Sonarr/Radarr (live or ephemeral) | configarr native validation (Option A only) | ✗ | — | **None offline — root of the D-08 blocker** |

**Missing dependencies with no fallback:**
- A *arr instance (live or ephemeral) reachable by configarr — required for any *genuinely native* configarr validation. This is the D-08 blocker.

**Missing dependencies with fallback:**
- configarr itself in CI — only needed if Option A/B; fallback is pydantic gate (Option C/D), pending user decision.

## Sources

### Primary (HIGH confidence)
- configarr source @ HEAD `df5792a9` (v1.28.0): `src/index.ts` (pipeline/run/runArrType — DRY_RUN + connection ordering), `src/env.ts` (env vars, DRY_RUN semantics), `src/config.ts` (getConfig — cast not zod-validate), `src/types/config.types.ts` (full InputConfigSchema + InputConfigArrInstance + MediaNaming + QualityProfile + CustomFormat), `src/types/common.types.ts` + `src/types/trashguide.types.ts` (CF definition shapes) — cloned & read directly
- `git ls-remote --tags github.com/raydak-labs/configarr` → latest tag **v1.28.0**
- In-repo code (read directly): `tools/arrconf-ui/arrconf_ui/{io.py,app.py,diff.py,locator.py}`, `tools/arrconf/arrconf/{config.py,schema_gen.py}`, `charts/arr-stack/files/configarr.yml`, `.github/workflows/tests.yml`, `tools/arrconf-ui/{pyproject.toml,tests/test_io_roundtrip.py}`
- Empirical ruyaml tests (run in the project's uv env): TaggedScalar dump preserves `!env SONARR_API_KEY` verbatim; `json.dumps(..., default=str)` drops the tag to bare value; `TaggedScalar.tag.value`/`.value` reconstruction; `Field(json_schema_extra={"readOnly": True})` emits `"readOnly": true`

### Secondary (MEDIUM confidence)
- configarr docs https://configarr.de/docs/ (config-file, kubernetes install) — corroborate `!env`/`!secret`/`!file` tags + CronJob deployment; no offline-validate command documented (consistent with source)

### Tertiary (LOW confidence)
- None relied upon.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all deps already pinned in pyproject.toml; nothing new
- configarr schema map (D-02/D-03): HIGH — read directly from configarr v1.28.0 source + cross-checked against the real file line-by-line
- `!env`/`!secret` tag mechanics (D-06/D-09/D-10): HIGH — empirically reproduced, including the read-path bug (Pitfall 1)
- D-08 validation gate: HIGH on the *finding* (no offline mode exists), but the *decision* is BLOCKED pending user escalation
- Pitfalls: HIGH (1,4,5 empirically/source-verified; 2,3 are design tensions, flagged as assumptions)

**Research date:** 2026-05-29
**Valid until:** 2026-06-28 (configarr is fast-moving — re-verify the validate-mode finding if configarr releases > v1.28.0 before planning; an offline `validate` command would change the D-08 escalation outcome)
