# Phase 25: configarr-in-UI backend - Pattern Map

**Mapped:** 2026-05-29
**Files analyzed:** 7 (3 new, 3 modified, 1 reuse-as-is)
**Analogs found:** 7 / 7

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tools/arrconf-ui/arrconf_ui/configarr_config.py` (NEW) | model (pydantic) | transform (validate) | `tools/arrconf/arrconf/config.py` (`RootConfig` + `*Instance`) | role-match (configarr shape, arrconf strictness pattern) |
| `tools/arrconf-ui/arrconf_ui/configarr_diff.py` (NEW) | service (diff) | transform | `tools/arrconf-ui/arrconf_ui/diff.py` | reference-only (D-05 — do NOT reuse) |
| `tools/arrconf-ui/arrconf_ui/app.py` (MODIFIED — +4 endpoints) | controller (route) | request-response (CRUD-ish) | existing arrconf endpoints in same file (lines 67-152) | exact |
| `tools/arrconf-ui/arrconf_ui/locator.py` (MODIFIED — +2 resolvers) | utility (config) | file-I/O (path resolve) | existing `arrconf_yml_path` / `schema_json_path` (lines 27-34) | exact |
| `tools/arrconf-ui/arrconf_ui/io.py` (REUSE AS-IS) | utility (I/O) | file-I/O | itself — `read_yaml` / `write_yaml_atomic` | reuse verbatim (D-10) |
| `tools/arrconf-ui/tests/test_configarr_*.py` (NEW: task-zero leak test + endpoint tests) | test | request-response | `tools/arrconf-ui/tests/test_app_endpoints.py` + `test_io_roundtrip.py` + `conftest.py` | exact (mirror fixtures) |
| schema gen + CI gate (NEW: local generator + tests.yml step) | config / utility | transform | `tools/arrconf/arrconf/schema_gen.py` + `tests.yml:52-59` | role-match (do NOT touch arrconf pipeline) |

## Pattern Assignments

### `tools/arrconf-ui/arrconf_ui/configarr_config.py` (model, transform)

**Analog:** `tools/arrconf/arrconf/config.py` — for the **strictness pattern**, NOT the shape. The configarr shape is fully mapped in `25-RESEARCH.md` lines 89-196; do not re-derive it.

**`extra="forbid"` ConfigDict pattern** (config.py:45, repeated on every model — 17 occurrences). Copy this onto **every** configarr model class (D-01):
```python
from pydantic import BaseModel, ConfigDict, Field

class SomeSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
```

**Root model shape** (config.py:644-670 `RootConfig`): a top-level `BaseModel` with `extra="forbid"` and one field per top-level key. The configarr equivalent (`ConfigarrRootConfig`) models the **5 real-file top-level keys** (RESEARCH lines 95-100): `trashGuideUrl`, `recyclarrConfigUrl`, `customFormatDefinitions`, `sonarr`, `radarr`. Per-instance keyed dict mirrors arrconf's `sonarr: dict[str, SonarrInstance]`:
```python
class ConfigarrRootConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trashGuideUrl: str | None = None
    recyclarrConfigUrl: str | None = None
    customFormatDefinitions: list[CustomFormatDefinition] = Field(default_factory=list)
    sonarr: dict[str, ArrInstance] = Field(default_factory=dict)
    radarr: dict[str, ArrInstance] = Field(default_factory=dict)
```

**readOnly field marker** (RESEARCH Pattern 3, lines 273-283) — emits `"readOnly": true` in JSON Schema. Apply to `api_key`, `media_naming`, `quality_definition` (D-04, D-02):
```python
class ArrInstance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_url: str                                            # stored/echoed, NEVER dialed (SC#3)
    api_key: str = Field(json_schema_extra={"readOnly": True})
    media_naming: MediaNaming | None = Field(default=None, json_schema_extra={"readOnly": True})
    quality_definition: QualityDefinition | None = Field(default=None, json_schema_extra={"readOnly": True})
    quality_profiles: list[QualityProfile] = Field(default_factory=list)   # editable
    custom_formats: list[CustomFormat] = Field(default_factory=list)       # editable
```

**Pitfalls (from RESEARCH):** `MediaNaming` is ONE type with all sonarr+radarr keys Optional (Pitfall 5); `specifications[].fields` = `dict[str, Any]` — do not constrain `.value` (Pitfall 4); `upgrade` block needs `@model_validator(mode="after")` for the allowed=true conditional-required (Pitfall 3, KISS over discriminated union). `extra="forbid"` model scope = real-file subset (Pitfall 2 / Assumption A1 — flagged Open Question, confirm in planning).

**ADR-5 boundary:** This file lives in `tools/arrconf-ui/arrconf_ui/` ONLY — NEVER `tools/arrconf/`. No `*arr` URL constructed or dialed anywhere (SC#3).

---

### `tools/arrconf-ui/arrconf_ui/app.py` (controller, request-response) — MODIFY: +4 endpoints

**Analog:** the existing arrconf endpoints in the SAME file (lines 67-152). Clone them symmetrically, swapping `RootConfig`→`ConfigarrRootConfig`, `arrconf_yml_path`→`configarr_yml_path`, `diff_configs`→`configarr_diff`, and `_read_current`→`_tagged_to_literal` (CRITICAL — see Shared Patterns / Pitfall 1).

**GET pattern** (clone of `get_config` lines 67-82). The 422-on-invalid-but-don't-500 branch (lines 73-81) is reused verbatim — operator may have hand-edited the file:
```python
detail = json.loads(json.dumps(e.errors(), default=str))   # normalizes non-serializable ctx (app.py:77)
return JSONResponse(status_code=422, content={"detail": detail, "raw": <literal>})
```

**PUT pattern** (clone of `put_config` lines 84-130). The shallow-merge-into-ruyaml-tree pattern (lines 107-118) is the prime analog — it preserves comments AND leaves `TaggedScalar` nodes physically untouched (the safest anti-leak design, RESEARCH Pattern 2 lines 261-270):
```python
target = read_yaml(configarr_yml_path())                    # ruyaml CommentedMap, tags intact
for top_key in ("trashGuideUrl", "recyclarrConfigUrl", "customFormatDefinitions", "sonarr", "radarr"):
    if top_key in payload:
        target[top_key] = payload[top_key]
write_yaml_atomic(configarr_yml_path(), target)
```
Then layer the **D-09 runtime guard** on top (RESEARCH lines 363-373): capture `before_bytes`, re-read after write, assert `!env`/`!secret` occurrence counts survived; on loss, `write_bytes(before_bytes)` rollback + `HTTPException(500)`.

**POST /diff pattern** (clone of `post_diff` lines 132-141) — stateless, MUST NOT write.

**GET /schema pattern** (clone of `get_schema` lines 143-152) — reads the committed `configarr-schema.json`, 404 if missing.

**Validation 422 shape on PUT** (lines 88-97): `RootConfig.model_validate(payload)` wrapped in try/except `ValidationError` → same `json.loads(json.dumps(e.errors(), default=str))` normalization.

---

### `tools/arrconf-ui/arrconf_ui/configarr_diff.py` (service, transform) — NEW

**Analog:** `tools/arrconf-ui/arrconf_ui/diff.py` — **reference for STRUCTURE only, do NOT import/reuse** (D-05). It is hard-coded to arrconf's shape: `APP_SECTIONS = ("sonarr","radarr","prowlarr","qbittorrent","seerr","jellyfin")` (diff.py:28) + a top-level `categories` list matched by name (diff.py:72-83). configarr has no `categories` and a different per-instance shape.

**Reusable helpers to copy/adapt** from diff.py:
- `_list_to_index(items, key)` (lines 31-33) — index a list by stable key; adapt for `quality_profiles[]` matched by `name` and `custom_formats[]` matched by `name`/`trash_id` (per-quality-profile / per-custom-format semantic grouping, D-05).
- `_flatten_paths` / `_changed_field_paths` (lines 36-58) — dotted-path leaf diff; reusable as-is for field-level comparison within a profile.
- The return-shape contract (module docstring lines 13-20): empty change-sets STILL present so the frontend hides them; predictable shape.
- `has_changes(diff)` (lines 102-112) — adapt the key-iteration to the configarr top-level keys.

**CRITICAL (D-06):** the diff MUST run on the **tag-literal** data (output of `_tagged_to_literal`), NEVER a `model_dump`/resolver path. Any dump that touches `api_key` drops the `!env` tag → SC#4 failure (RESEARCH Anti-Patterns line 292). The `before` snapshot comes from `_tagged_to_literal(read_yaml(...))`, the `after` is the payload (already tag-literal strings).

---

### `tools/arrconf-ui/arrconf_ui/locator.py` (utility, file-I/O) — MODIFY: +2 resolvers

**Analog:** `arrconf_yml_path()` (lines 27-29) and `schema_json_path()` (lines 32-34) in the SAME file. Add two siblings using the existing `repo_root()` (lines 14-24):
```python
def configarr_yml_path() -> Path:
    return repo_root() / "charts" / "arr-stack" / "files" / "configarr.yml"

def configarr_schema_json_path() -> Path:
    return repo_root() / "schemas" / "configarr-schema.json"
```
`repo_root()` (`parents[3]` walk) is reused unchanged — `configarr.yml` is co-located with `arrconf.yml` (Assumption A3, verified).

---

### `tools/arrconf-ui/arrconf_ui/io.py` (utility, I/O) — REUSE AS-IS

**No changes.** `read_yaml` (lines 33-37), `write_yaml_atomic` (lines 48-82), `dump_yaml_to_str` (lines 40-45) are reused verbatim (D-10). `_yaml()` builds `YAML(typ="rt")` which preserves `!env`/`!secret` TaggedScalars on the WRITE path (verified). The atomic recipe (tmp-in-same-dir + `os.fsync` + `os.replace`, lines 55-81) is the foundation the D-09 guard sits on top of.

> ⚠️ `io.py` is safe; the leak risk is NOT here — it is in `app.py:_read_current()`. See Shared Patterns / Pitfall 1.

---

### `tools/arrconf-ui/tests/test_configarr_*.py` (test) — NEW

**Analogs:** `test_app_endpoints.py`, `test_io_roundtrip.py`, `conftest.py` (all in `tools/arrconf-ui/tests/`).

**Sandbox fixture pattern** (conftest.py:22-44) — copy the canonical file to `tmp_path`, monkeypatch BOTH the locator module AND the `app` module re-export (the double-patch on lines 32-33 / 42-43 is mandatory because `app.py` imports the symbol by name). Add a `sandboxed_configarr_yml` fixture cloning this exactly:
```python
monkeypatch.setattr("arrconf_ui.locator.configarr_yml_path", fake_path)
monkeypatch.setattr("arrconf_ui.app.configarr_yml_path", fake_path)
```

**Endpoint test pattern** (test_app_endpoints.py): `TestClient(create_app())` fixture (lines 14-17); GET-returns-200-with-keys (lines 20-34); PUT-writes-and-returns-diff with file-content assertion (lines 44-66); invalid-payload-422 + file-NOT-written (lines 69-89); POST-diff-does-not-write (lines 92-110).

**Task-zero anti-leak round-trip test (ships FIRST, CFGUI-01):** mirror `test_modeline_preserved_on_round_trip` / `test_dump_yaml_to_str_is_utf8` (test_io_roundtrip.py:10-15, 52-58) but assert the `!env` literal survives:
```python
# GET body MUST contain the literal, not the bare var name
assert resp.json()["sonarr"]["main"]["api_key"] == "!env SONARR_API_KEY"
# round-trip write MUST keep both tags byte-present
content = sandboxed_configarr_yml.read_text("utf-8")
assert "!env SONARR_API_KEY" in content and "!env RADARR_API_KEY" in content
```
Warning sign to test against (Pitfall 1): a response containing `"api_key": "SONARR_API_KEY"` (bare) = FAIL.

---

### Schema generation + CI gate (config/utility) — NEW

**Analog:** `tools/arrconf/arrconf/schema_gen.py` (the `Draft202012Generator` + reproducible-write pattern) and the CI step `tests.yml:52-59`.

**Generator** (schema_gen.py:14-33) — write a SIBLING in `tools/arrconf-ui/` (do NOT touch arrconf's pipeline, ADR-5). Copy `Draft202012Generator` (forces `$schema` Draft 2020-12, lines 14-27) and `write_schema` (reproducible `json.dumps(..., indent=2, sort_keys=True)`, line 33), swapping `RootConfig` → `ConfigarrRootConfig`, output → `schemas/configarr-schema.json`.

**CI reproducibility gate** (tests.yml:52-59 "Verify schema reproducibility (D-15)") — mirror the `git diff --exit-code` drift check for `schemas/configarr-schema.json`.

**CI validation gate (CFGUI-07):** D-08 RESOLVED → **Option C, pydantic-only** (CONTEXT D-08). The gate is `ConfigarrRootConfig.model_validate` run against the written `configarr.yml` in the existing `arrconf-ui-backend` job (tests.yml:86-118, `working-directory: tools/arrconf-ui`, runs `mypy .` + `pytest -q`). Do NOT spin up *arr containers; do NOT invoke configarr in CI (RESEARCH BLOCKER block lines 375-396).

---

## Shared Patterns

### Tag-preserving read — the SC#4-CRITICAL replacement for `_read_current()`
**Source (anti-pattern):** `app.py:38-56` `_read_current()` does `json.loads(json.dumps(raw, default=str))` (line 56). For a `TaggedScalar`, `str(node)` returns only `.value` → `!env SONARR_API_KEY` becomes bare `"SONARR_API_KEY"`. **Cloning this for configarr GET/diff = SC#4 failure** (RESEARCH Pitfall 1, lines 308-313).
**Apply to:** every configarr GET endpoint and every diff `before` snapshot.
**Replacement** (RESEARCH Pattern 1, lines 242-258):
```python
from ruyaml.comments import TaggedScalar

def _tagged_to_literal(node):
    if isinstance(node, TaggedScalar):
        return f"{node.tag.value} {node.value}"   # -> "!env SONARR_API_KEY"
    if isinstance(node, dict):
        return {k: _tagged_to_literal(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_tagged_to_literal(v) for v in node]
    return node
# NEVER: json.loads(json.dumps(raw, default=str))   <-- drops the tag
```

### `extra="forbid"` strictness
**Source:** `tools/arrconf/arrconf/config.py:45` (and 16 other occurrences). `model_config = ConfigDict(extra="forbid")`.
**Apply to:** every `ConfigarrRootConfig` model class (D-01). Unknown keys → 422, not silent pass-through.

### Atomic write + D-09 anti-leak guard
**Source:** `io.py:48-82` (`write_yaml_atomic` — tmp + fsync + os.replace) + RESEARCH lines 363-373 (D-09 guard).
**Apply to:** the `PUT /api/configarr/config` write path. Shallow-merge editable keys into the on-disk ruyaml tree (app.py:107-118 analog) → `write_yaml_atomic` → re-read → assert tag counts → rollback `write_bytes(before)` + 500 on loss.

### 422 error normalization
**Source:** `app.py:77` / `app.py:93` — `json.loads(json.dumps(e.errors(), default=str))`. Handles non-JSON-serializable `ctx` from `model_validator` ValueErrors.
**Apply to:** all configarr GET (on-disk invalid) and PUT (payload invalid) handlers.

### Reproducible JSON Schema generation
**Source:** `schema_gen.py:14-33` — `Draft202012Generator` + `json.dumps(..., sort_keys=True)`.
**Apply to:** the new local configarr schema generator (sibling in `tools/arrconf-ui/`, NOT arrconf's).

### Sandboxed-file test fixture (double monkeypatch)
**Source:** `conftest.py:22-44`. Patch BOTH `arrconf_ui.locator.<path_fn>` AND `arrconf_ui.app.<path_fn>` — `app.py` imports the symbol by name (line 33), so patching only the locator misses it.
**Apply to:** all configarr endpoint + leak tests.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| — | — | — | None. Every file has a same-repo analog; the only genuinely novel logic is `_tagged_to_literal` (~10 lines, RESEARCH Pattern 1) and the configarr-shape grouping in `configarr_diff.py` (structure cloned from `diff.py`). |

## Metadata

**Analog search scope:** `tools/arrconf-ui/arrconf_ui/`, `tools/arrconf-ui/tests/`, `tools/arrconf/arrconf/`, `.github/workflows/tests.yml`, `charts/arr-stack/files/configarr.yml`
**Files scanned:** app.py, io.py, locator.py, diff.py, config.py, schema_gen.py, test_app_endpoints.py, test_io_roundtrip.py, conftest.py, tests.yml, configarr.yml
**Pattern extraction date:** 2026-05-29
