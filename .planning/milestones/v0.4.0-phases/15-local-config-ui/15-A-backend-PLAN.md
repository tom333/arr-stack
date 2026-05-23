---
phase: 15-local-config-ui
plan: 15-A
type: execute
wave: 1
depends_on: []
files_modified:
  - tools/arrconf-ui/pyproject.toml
  - tools/arrconf-ui/arrconf_ui/__init__.py
  - tools/arrconf-ui/arrconf_ui/__main__.py
  - tools/arrconf-ui/arrconf_ui/app.py
  - tools/arrconf-ui/arrconf_ui/io.py
  - tools/arrconf-ui/arrconf_ui/diff.py
  - tools/arrconf-ui/arrconf_ui/locator.py
  - tools/arrconf-ui/tests/__init__.py
  - tools/arrconf-ui/tests/conftest.py
  - tools/arrconf-ui/tests/test_io_roundtrip.py
  - tools/arrconf-ui/tests/test_diff.py
  - tools/arrconf-ui/tests/test_app_endpoints.py
  - tools/arrconf-ui/tests/test_locator.py
  - tools/arrconf-ui/tests/test_cli.py
autonomous: true
requirements:
  - REQ-local-config-ui-backend
  - REQ-local-config-ui-packaging
tags:
  - python
  - fastapi
  - pydantic
  - ruyaml

must_haves:
  truths:
    - "`uv run arrconf-ui` from repo root starts uvicorn on 127.0.0.1:8765 and prints `INFO: Local config UI ready at http://localhost:8765` (SC#1)."
    - "`GET /api/config` returns 200 with the parsed RootConfig as JSON (matches `charts/arr-stack/files/arrconf.yml`) (SC#2)."
    - "`PUT /api/config` with valid payload returns 200 with semantic diff structure AND writes arrconf.yml preserving comments/blank lines/key ordering (SC#4)."
    - "`PUT /api/config` with invalid payload returns 422 with pydantic error structure verbatim (SC#5)."
    - "`GET /api/schema` returns 200 with the JSON Schema (Draft 2020-12) content (drives D-13 schema-driven UI)."
    - "`POST /api/diff` accepts a pending RootConfig payload and returns the semantic diff WITHOUT writing the file (preview, D-07)."
    - "Atomic write: writing to arrconf.yml uses `tempfile.NamedTemporaryFile + os.replace` so a crash mid-write does NOT corrupt the file."
    - "Server binds 127.0.0.1 only — pytest asserts the host string is exactly `127.0.0.1` (D-04)."
    - "Triad passes: `cd tools/arrconf-ui && uv run ruff format --check . && uv run ruff check . && uv run mypy . && uv run pytest -v` exits 0."
  artifacts:
    - path: tools/arrconf-ui/pyproject.toml
      provides: "Sibling Python package (mirrors tools/arrconf/pyproject.toml ruff+mypy+pytest config); declares `arrconf-ui = arrconf_ui.__main__:app` console script."
    - path: tools/arrconf-ui/arrconf_ui/app.py
      provides: "FastAPI application with 4 endpoints (GET /api/config, PUT /api/config, GET /api/schema, POST /api/diff) + StaticFiles mount placeholder for Plan 15-B."
    - path: tools/arrconf-ui/arrconf_ui/io.py
      provides: "ruyaml round-trip read + atomic write of arrconf.yml (tempfile.NamedTemporaryFile + os.replace)."
    - path: tools/arrconf-ui/arrconf_ui/diff.py
      provides: "Semantic diff comparator producing `{section: {added, modified, removed}}` per D-07."
    - path: tools/arrconf-ui/arrconf_ui/__main__.py
      provides: "Typer CLI: `arrconf-ui [--port 8765] [--no-browser]`. Default port 8765 (D-12). Auto-opens browser via webbrowser.open()."
    - path: tools/arrconf-ui/arrconf_ui/locator.py
      provides: "Locator function `repo_root()` + `arrconf_yml_path()` — walks up from package install to find repo root + charts/arr-stack/files/arrconf.yml."
    - path: tools/arrconf-ui/tests/
      provides: "pytest suite ≥ 20 tests covering round-trip, diff, endpoints, locator, CLI bind."
  key_links:
    - from: "tools/arrconf-ui/arrconf_ui/app.py"
      to: "arrconf.config.RootConfig.model_validate"
      via: "import + call in PUT handler"
      pattern: "from arrconf.config import"
    - from: "tools/arrconf-ui/arrconf_ui/io.py"
      to: "ruyaml.YAML(typ='rt')"
      via: "round-trip type preserves comments/order"
      pattern: "YAML\\(typ=['\\\"]rt['\\\"]\\)"
    - from: "tools/arrconf-ui/arrconf_ui/__main__.py"
      to: "uvicorn.run(app, host='127.0.0.1', port=...)"
      via: "Typer command body"
      pattern: "host=['\\\"]127\\.0\\.0\\.1['\\\"]"
    - from: "tools/arrconf-ui/arrconf_ui/diff.py"
      to: "categories[].name match key"
      via: "stable identifier for added/removed/modified detection per D-07"
      pattern: "category\\.name|by_name"
---

<objective>
Build the `tools/arrconf-ui/` Python sibling package that ships the FastAPI backend for the Phase 15 local config UI: 4 REST endpoints (GET config, PUT config, GET schema, POST diff), pydantic validation, ruyaml round-trip with atomic write, semantic diff comparator, Typer CLI launcher.

Purpose: Backend MUST be fully verifiable end-to-end via curl/httpx BEFORE Plan 15-B (Svelte frontend) starts. Plan 15-A closes when the triad passes + all 4 endpoints respond correctly + a manual `uv run arrconf-ui` smoke test confirms 127.0.0.1:8765 + browser auto-open + the actual `charts/arr-stack/files/arrconf.yml` round-trips cleanly.

Output: 14 files under `tools/arrconf-ui/` (1 pyproject.toml + 6 package modules + 7 test modules). NO modifications to `tools/arrconf/arrconf/` (read-only import), NO modifications to `charts/` or `schemas/`. No `arrconf.image.tag` co-bump (D-11).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/15-local-config-ui/15-CONTEXT.md
@.planning/phases/15-local-config-ui/15-UI-SPEC.md
@CLAUDE.md
@tools/arrconf/pyproject.toml
@tools/arrconf/arrconf/config.py
@tools/arrconf/arrconf/__main__.py
@tools/arrconf/arrconf/dump.py
@tools/arrconf/arrconf/schema_gen.py
@charts/arr-stack/files/arrconf.yml
@schemas/arrconf-schema.json

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from tools/arrconf/arrconf/. -->
<!-- DO NOT re-explore the codebase — use these directly. -->

From `tools/arrconf/arrconf/config.py`:

```python
class RootConfig(BaseModel):
    """Top-level arrconf YAML schema (root for JSON Schema generation)."""
    model_config = ConfigDict(extra="forbid")
    categories: list[MediaCategory] = Field(default_factory=list)
    sonarr: dict[str, SonarrInstance] = Field(default_factory=dict)
    radarr: dict[str, RadarrInstance] = Field(default_factory=dict)
    prowlarr: dict[str, ProwlarrInstance] = Field(default_factory=dict)
    qbittorrent: dict[str, QbittorrentInstance] = Field(default_factory=dict)
    seerr: dict[str, SeerrInstance] = Field(default_factory=dict)
    jellyfin: dict[str, JellyfinInstance] = Field(default_factory=dict)

def load_config(path: Path) -> RootConfig:
    """Load + validate. Raises ConfigError (mapped to CLI exit code 2)."""

class MediaCategory(BaseModel):
    # from arrconf/resources/categories.py
    name: str  # kebab-case slug, stable match key
    kind: Literal["series", "movies"]
    profile: Literal["general", "anime", "family"]
    display: str
    base_path: str  # absolute path under /media
```

From `tools/arrconf/arrconf/schema_gen.py`:

```python
class Draft202012Generator(GenerateJsonSchema):
    schema_dialect = "https://json-schema.org/draft/2020-12/schema"
    def generate(self, schema, mode="validation"): ...

def write_schema(output_path: Path) -> None:
    """Write JSON Schema reproducibly (sort_keys=True)."""
    schema = RootConfig.model_json_schema(schema_generator=Draft202012Generator)
    output_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
```

From `tools/arrconf/arrconf/exceptions.py`:

```python
class ConfigError(Exception): ...  # raised by load_config for missing file / parse / validation
```

From `tools/arrconf/arrconf/dump.py` (ruyaml round-trip pattern reference):

```python
from ruyaml import YAML
# Round-trip type preserves comments + blank lines + key order.
# yaml = YAML(typ="rt") is the correct choice for save-flow.
# yaml = YAML(typ="safe") is what load_config uses (no comments needed for validation).
```

Repo-root locator pattern (Phase 15 must mirror this — D-12):

```python
# From CONTEXT D-12:
# tools/arrconf-ui/arrconf_ui/__main__.py:
#   Path(__file__).parents[3]  →  repo root
# Walking: __file__ = .../tools/arrconf-ui/arrconf_ui/__main__.py
#   parents[0] = .../tools/arrconf-ui/arrconf_ui
#   parents[1] = .../tools/arrconf-ui
#   parents[2] = .../tools
#   parents[3] = .../arr-stack (repo root)
```

Phase 14 SuggestArr-coupling field paths (D-09 — surfaced as visual hint in Plan 15-B, but the backend MUST treat these fields exactly like any other field — NO special validation, NO read-only flag):

- `seerr.main.sonarr_service.activeAnimeProfileId`
- `seerr.main.sonarr_service.activeProfileId`
- `seerr.main.sonarr_service.activeAnimeDirectory`
- `seerr.main.sonarr_service.activeDirectory`
- `seerr.main.radarr_service.activeProfileId`
- `seerr.main.radarr_service.activeDirectory`
- `categories[name="films-zoe"].base_path`
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Bootstrap `tools/arrconf-ui/` package (pyproject + IO + diff modules + locator)</name>
  <files>
    tools/arrconf-ui/pyproject.toml,
    tools/arrconf-ui/arrconf_ui/__init__.py,
    tools/arrconf-ui/arrconf_ui/locator.py,
    tools/arrconf-ui/arrconf_ui/io.py,
    tools/arrconf-ui/arrconf_ui/diff.py
  </files>
  <read_first>
    - .planning/phases/15-local-config-ui/15-CONTEXT.md (D-01, D-05, D-07, D-11, D-12 + Claude's Discretion atomic-write recipe)
    - tools/arrconf/pyproject.toml (mirror ruff+mypy+pytest config verbatim; bump only what differs)
    - tools/arrconf/arrconf/dump.py (ruyaml round-trip reference — `YAML(typ='rt')`, NOT `typ='safe'`)
    - tools/arrconf/arrconf/config.py (RootConfig + MediaCategory shape — what diff.py compares)
    - tools/arrconf/arrconf/exceptions.py (ConfigError pattern — mirror in arrconf_ui)
    - charts/arr-stack/files/arrconf.yml (the file being round-tripped; preserves yaml-language-server modeline on line 1)
  </read_first>
  <action>
Create the sibling Python package skeleton.

**1.1 — `tools/arrconf-ui/pyproject.toml`** (mirrors arrconf's config — same ruff/mypy/pytest baseline, different name + deps):

```toml
[project]
name = "arrconf-ui"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
  "arrconf",                         # editable install of sibling package — provides RootConfig + load_config
  "fastapi>=0.115,<0.116",
  "uvicorn[standard]>=0.32,<0.33",
  "typer>=0.25.0,<0.26",
  "pydantic>=2.13,<3",
  "ruyaml>=0.91,<0.92",
  "structlog>=25.5,<26",
]

[project.scripts]
arrconf-ui = "arrconf_ui.__main__:app"

[dependency-groups]
dev = [
  "pytest>=9.0,<10",
  "pytest-cov>=7.1,<8",
  "httpx>=0.28.0,<0.29",
  "ruff>=0.15,<0.16",
  "mypy>=2.0,<3",
]

[tool.uv.sources]
arrconf = { path = "../arrconf", editable = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "N", "D"]
ignore = ["D203", "D213"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["D", "N802"]
"arrconf_ui/__main__.py" = ["B008"]  # typer.Option(...) in defaults is canonical typer

[tool.mypy]
python_version = "3.13"
strict = true
warn_unused_ignores = true
disallow_untyped_defs = true

[[tool.mypy.overrides]]
module = ["ruyaml.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
addopts = "-v --strict-markers"
testpaths = ["tests"]
```

**1.2 — `tools/arrconf-ui/arrconf_ui/__init__.py`** (single line):

```python
"""arrconf-ui — local web UI for editing charts/arr-stack/files/arrconf.yml (Phase 15)."""
```

**1.3 — `tools/arrconf-ui/arrconf_ui/locator.py`** (repo root + arrconf.yml path resolution per D-12):

```python
"""Repo-root + arrconf.yml path locator (D-12).

The console script `arrconf-ui` is launched from anywhere; this module walks
the filesystem from the installed package location to find the repo root
(the parent of `tools/arrconf-ui/`) and the canonical arrconf.yml under
`charts/arr-stack/files/arrconf.yml`.
"""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    """Return the arr-stack repo root.

    Walks `parents[3]` from this file:
        tools/arrconf-ui/arrconf_ui/locator.py
        parents[0] = tools/arrconf-ui/arrconf_ui
        parents[1] = tools/arrconf-ui
        parents[2] = tools
        parents[3] = <repo root>
    """
    return Path(__file__).resolve().parents[3]


def arrconf_yml_path() -> Path:
    """Return the canonical path to charts/arr-stack/files/arrconf.yml."""
    return repo_root() / "charts" / "arr-stack" / "files" / "arrconf.yml"


def schema_json_path() -> Path:
    """Return the canonical path to schemas/arrconf-schema.json."""
    return repo_root() / "schemas" / "arrconf-schema.json"
```

**1.4 — `tools/arrconf-ui/arrconf_ui/io.py`** (ruyaml round-trip + atomic write):

```python
"""ruyaml round-trip read + atomic write of arrconf.yml (D-05).

Uses `YAML(typ='rt')` (round-trip) NOT `typ='safe'` — preserves comments,
blank lines, and key ordering when writing back. The pydantic validation
happens separately in app.py (PUT handler); this module is pure IO.

Atomic write recipe (D-05 Claude's Discretion):
    1. Write to NamedTemporaryFile in the SAME directory as arrconf.yml.
    2. os.replace(tmp, target) — atomic on POSIX same-filesystem.
    3. On any exception: tmp is cleaned up by the context manager.
"""

from __future__ import annotations

import os
import tempfile
from io import StringIO
from pathlib import Path
from typing import Any

from ruyaml import YAML


def _yaml() -> YAML:
    """Return a configured round-trip YAML parser/emitter."""
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 4096  # avoid line wrapping that breaks long URLs
    return yaml


def read_yaml(path: Path) -> Any:
    """Read a YAML file with round-trip type. Returns ruyaml CommentedMap/CommentedSeq."""
    yaml = _yaml()
    with path.open("r", encoding="utf-8") as f:
        return yaml.load(f)


def dump_yaml_to_str(data: Any) -> str:
    """Dump ruyaml data structure to a UTF-8 string (used for tests + diff preview)."""
    yaml = _yaml()
    buf = StringIO()
    yaml.dump(data, buf)
    return buf.getvalue()


def write_yaml_atomic(path: Path, data: Any) -> None:
    """Atomically write YAML data to ``path``.

    Writes to a temp file in the SAME directory (so os.replace is atomic on
    the same filesystem), then os.replace() swaps it in. On exception the
    temp file is cleaned up by NamedTemporaryFile's context manager.
    """
    yaml = _yaml()
    target_dir = path.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    # delete=False because we close the file before os.replace (Windows-safe
    # pattern; also POSIX-safe). The except branch unlinks on failure.
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(target_dir),
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    try:
        yaml.dump(data, tmp)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        os.replace(tmp.name, path)
    except Exception:
        tmp.close()
        try:
            os.unlink(tmp.name)
        except FileNotFoundError:
            pass
        raise
```

**1.5 — `tools/arrconf-ui/arrconf_ui/diff.py`** (semantic diff per D-07):

```python
"""Semantic diff comparator for arrconf.yml (D-07).

Produces a structured object suitable for the frontend to render as
"3 categories added, 2 modified, 1 removed" + per-section changed-field
lists. NOT a unified-diff text dump.

Comparison rules:
- top-level `categories` list: matched by `name` (stable identifier per
  MediaCategory.name docstring "Kebab-case slug. Stable match key.").
- per-app dicts (sonarr/radarr/...): matched by instance key (`main`).
  For each instance, recursively compare fields; flag any path whose
  value differs.
- Returns a dict shape:
    {
      "categories": {"added": [name, ...], "modified": [name, ...], "removed": [name, ...]},
      "sonarr.main": {"changed_fields": ["dotted.path", ...]},
      ...
    }
  Sections with zero changes are STILL present (empty arrays) — the
  frontend hides them. Keep the shape predictable.
"""

from __future__ import annotations

from typing import Any

# Top-level keys whose contents we compare per-section.
APP_SECTIONS = ("sonarr", "radarr", "prowlarr", "qbittorrent", "seerr", "jellyfin")


def _list_to_index(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    """Index a list of dicts by a stable key (e.g., category.name)."""
    return {item[key]: item for item in items if key in item}


def _flatten_paths(prefix: str, value: Any) -> dict[str, Any]:
    """Walk a nested dict/list and return a flat {dotted.path: leaf_value}."""
    out: dict[str, Any] = {}
    if isinstance(value, dict):
        for k, v in value.items():
            out.update(_flatten_paths(f"{prefix}.{k}" if prefix else k, v))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            out.update(_flatten_paths(f"{prefix}[{i}]", v))
    else:
        out[prefix] = value
    return out


def _changed_field_paths(before: Any, after: Any, prefix: str = "") -> list[str]:
    """Return dotted-path list of leaves whose value differs."""
    before_flat = _flatten_paths(prefix, before)
    after_flat = _flatten_paths(prefix, after)
    paths: list[str] = []
    for key in sorted(set(before_flat) | set(after_flat)):
        if before_flat.get(key) != after_flat.get(key):
            paths.append(key)
    return paths


def diff_configs(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Compute semantic diff between two RootConfig JSON dicts.

    Both inputs are the output of `RootConfig.model_dump(mode='json')` or
    equivalent (plain dicts; no pydantic objects).

    Returns a dict per D-07 (see module docstring for shape).
    """
    out: dict[str, Any] = {}

    # categories list (matched by name)
    cat_before = _list_to_index(before.get("categories", []) or [], key="name")
    cat_after = _list_to_index(after.get("categories", []) or [], key="name")
    added_names = sorted(set(cat_after) - set(cat_before))
    removed_names = sorted(set(cat_before) - set(cat_after))
    modified_names = sorted(
        name
        for name in set(cat_before) & set(cat_after)
        if cat_before[name] != cat_after[name]
    )
    out["categories"] = {
        "added": added_names,
        "modified": modified_names,
        "removed": removed_names,
    }

    # per-app sections (sonarr/radarr/...): one entry per instance key
    for section in APP_SECTIONS:
        b_section = before.get(section, {}) or {}
        a_section = after.get(section, {}) or {}
        all_instances = sorted(set(b_section) | set(a_section))
        for instance in all_instances:
            label = f"{section}.{instance}"
            changed = _changed_field_paths(
                b_section.get(instance, {}),
                a_section.get(instance, {}),
                prefix=label,
            )
            out[label] = {"changed_fields": changed}

    return out


def has_changes(diff: dict[str, Any]) -> bool:
    """Return True if the diff contains any non-empty change set."""
    cats = diff.get("categories", {})
    if cats.get("added") or cats.get("modified") or cats.get("removed"):
        return True
    for k, v in diff.items():
        if k == "categories":
            continue
        if isinstance(v, dict) and v.get("changed_fields"):
            return True
    return False
```
  </action>
  <verify>
    <automated>
cd /data/projets/perso/arr-stack/tools/arrconf-ui && uv sync && uv run python -c "from arrconf_ui.io import read_yaml, write_yaml_atomic, dump_yaml_to_str; from arrconf_ui.diff import diff_configs, has_changes; from arrconf_ui.locator import repo_root, arrconf_yml_path; assert arrconf_yml_path().exists(), arrconf_yml_path(); data = read_yaml(arrconf_yml_path()); rt = dump_yaml_to_str(data); assert 'yaml-language-server' in rt, 'modeline lost'; assert 'sonarr' in data, 'parse failed'; print('OK io+locator+diff importable, arrconf.yml round-trips')"
    </automated>
  </verify>
  <acceptance_criteria>
    - `tools/arrconf-ui/pyproject.toml` exists with `arrconf-ui = arrconf_ui.__main__:app` console script.
    - `tools/arrconf-ui/arrconf_ui/{__init__.py,locator.py,io.py,diff.py}` all exist.
    - `uv sync` from `tools/arrconf-ui/` succeeds (resolves arrconf as editable sibling).
    - `arrconf_ui.locator.arrconf_yml_path()` returns a path that exists.
    - `read_yaml(arrconf_yml_path())` parses without exception and preserves the `# yaml-language-server:` modeline when round-tripped.
    - `diff_configs({}, {})` returns a dict with `categories` key + 6 app-section keys (all empty).
    - `has_changes(diff_configs({}, {}))` returns False.
    - `grep -E "YAML\(typ=['\"]rt['\"]\)" tools/arrconf-ui/arrconf_ui/io.py` returns at least 1 match (round-trip type used, NOT safe).
    - `grep -E "os\.replace" tools/arrconf-ui/arrconf_ui/io.py` returns at least 1 match (atomic write present).
  </acceptance_criteria>
  <done>
    Package skeleton boots; ruyaml round-trip preserves modeline; atomic write helper present; semantic diff comparator importable.
  </done>
</task>

<task type="auto">
  <name>Task 2: FastAPI app + 4 endpoints + pytest API contract + diff tests + round-trip tests</name>
  <files>
    tools/arrconf-ui/arrconf_ui/app.py,
    tools/arrconf-ui/tests/__init__.py,
    tools/arrconf-ui/tests/conftest.py,
    tools/arrconf-ui/tests/test_io_roundtrip.py,
    tools/arrconf-ui/tests/test_diff.py,
    tools/arrconf-ui/tests/test_app_endpoints.py,
    tools/arrconf-ui/tests/test_locator.py
  </files>
  <read_first>
    - .planning/phases/15-local-config-ui/15-CONTEXT.md (D-02, D-04, D-05, D-06, D-07 — endpoint contracts + atomic write + validation timing)
    - .planning/phases/15-local-config-ui/15-UI-SPEC.md (§"API Integration" — frontend ↔ backend contract)
    - tools/arrconf/arrconf/config.py (RootConfig.model_validate signature + raises ValidationError; load_config raises ConfigError)
    - tools/arrconf/tests/conftest.py (pytest fixture pattern reference)
    - tools/arrconf-ui/arrconf_ui/io.py (created in Task 1 — read_yaml, write_yaml_atomic)
    - tools/arrconf-ui/arrconf_ui/diff.py (created in Task 1 — diff_configs)
    - charts/arr-stack/files/arrconf.yml (the canonical input the tests load)
    - schemas/arrconf-schema.json (returned verbatim by GET /api/schema)
  </read_first>
  <action>
Wire the FastAPI app with the 4 D-02 endpoints + the pytest suite that drives them via TestClient. NO actual file modification in tests (use tmp_path + fixture-copied arrconf.yml).

**2.1 — `tools/arrconf-ui/arrconf_ui/app.py`** (the FastAPI application):

```python
"""FastAPI application — 4 endpoints + StaticFiles mount placeholder (D-02).

Endpoints:
- GET  /api/config  — read arrconf.yml → RootConfig.model_dump(mode='json')
- PUT  /api/config  — validate body via RootConfig.model_validate → atomic write → return diff summary
- GET  /api/schema  — return schemas/arrconf-schema.json content (drives D-13 schema-driven UI)
- POST /api/diff    — stateless preview: accept pending RootConfig, return diff vs on-disk

StaticFiles mount at `/` is enabled if `tools/arrconf-ui/web/dist/` exists.
Plan 15-B builds this directory; until then the mount is skipped (404 on /).

Error contract (D-06 validation on Save only):
- 404: arrconf.yml missing
- 422: pydantic ValidationError → returned with `detail` array (loc/msg/type)
- 500: anything else
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import structlog
from arrconf.config import RootConfig
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from arrconf_ui.diff import diff_configs, has_changes
from arrconf_ui.io import read_yaml, write_yaml_atomic
from arrconf_ui.locator import arrconf_yml_path, repo_root, schema_json_path

log = structlog.get_logger()


def _read_current() -> dict[str, Any]:
    """Read arrconf.yml as a plain Python dict (ruyaml CommentedMap → dict via JSON round-trip).

    Why JSON round-trip: pydantic.model_validate handles ruyaml CommentedMap
    via the Mapping protocol BUT ruyaml's tagged scalar types (e.g., dates,
    quoted-empty-string preservation) can leak through model_dump. Going via
    `json.loads(json.dumps(...))` normalizes to plain Python primitives.
    NOT used for the WRITE path — write_yaml_atomic takes the ruyaml object
    directly to preserve comments.
    """
    path = arrconf_yml_path()
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"arrconf.yml not found at {path}",
        )
    raw = read_yaml(path)
    # ruyaml CommentedMap → plain dict (drops comments — fine for read endpoint)
    return json.loads(json.dumps(raw, default=str))


def create_app() -> FastAPI:
    """Application factory — kept separate so tests can instantiate fresh apps."""
    app = FastAPI(
        title="arrconf-ui",
        description="Local config editor for charts/arr-stack/files/arrconf.yml",
        version="0.1.0",
    )

    @app.get("/api/config")
    def get_config() -> dict[str, Any]:
        """Return arrconf.yml parsed + validated as JSON (RootConfig.model_dump)."""
        raw = _read_current()
        try:
            validated = RootConfig.model_validate(raw)
        except ValidationError as e:
            # On-disk file is invalid — surface the errors but DON'T 500
            # (operator may have edited the file manually).
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": e.errors(), "raw": raw},
            )
        return validated.model_dump(mode="json")

    @app.put("/api/config")
    def put_config(payload: dict[str, Any]) -> dict[str, Any]:
        """Validate payload → atomic write → return semantic diff (D-06 + D-05)."""
        try:
            RootConfig.model_validate(payload)
        except ValidationError as e:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": e.errors()},
            )
        before = _read_current()
        # Compute diff BEFORE write so the response reflects what was written.
        diff = diff_configs(before, payload)
        # Atomic write: read the current ruyaml CommentedMap to preserve
        # comments, then SHALLOW-MERGE the payload into it so unedited
        # top-level keys (and their comments) are unchanged.
        # NOTE: this is a deliberate first-pass impl. If a future phase needs
        # per-key comment preservation on edited keys, revisit (Phase 15
        # ships with the "comments preserved on unedited keys" baseline).
        target = read_yaml(arrconf_yml_path())
        for top_key in (
            "categories",
            "sonarr",
            "radarr",
            "prowlarr",
            "qbittorrent",
            "seerr",
            "jellyfin",
        ):
            if top_key in payload:
                target[top_key] = payload[top_key]
        write_yaml_atomic(arrconf_yml_path(), target)
        log.info(
            "config_saved",
            has_changes=has_changes(diff),
            changed_sections=[k for k, v in diff.items()
                              if (k == "categories" and (v.get("added") or v.get("modified") or v.get("removed")))
                              or (k != "categories" and v.get("changed_fields"))],
        )
        return {"diff": diff, "has_changes": has_changes(diff)}

    @app.post("/api/diff")
    def post_diff(payload: dict[str, Any]) -> dict[str, Any]:
        """Stateless preview: return diff between payload and on-disk arrconf.yml.

        Used by the frontend to power the diff panel BEFORE the operator
        commits the Save action.
        """
        before = _read_current()
        diff = diff_configs(before, payload)
        return {"diff": diff, "has_changes": has_changes(diff)}

    @app.get("/api/schema")
    def get_schema() -> dict[str, Any]:
        """Return the committed JSON Schema (drives D-13 schema-driven UI)."""
        path = schema_json_path()
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schema file not found at {path}",
            )
        return json.loads(path.read_text(encoding="utf-8"))

    # StaticFiles mount (Plan 15-B builds tools/arrconf-ui/web/dist/).
    # Mounted LAST so /api/* routes take precedence.
    dist = repo_root() / "tools" / "arrconf-ui" / "web" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="ui")
    return app


# Module-level instance for ASGI consumers (uvicorn arrconf_ui.app:app)
app = create_app()

# Quiet uvicorn access logs that obscure structlog output during dev.
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
```

**2.2 — `tools/arrconf-ui/tests/__init__.py`** (empty file — marks tests as a package):

```python
```

**2.3 — `tools/arrconf-ui/tests/conftest.py`** (shared fixtures: tmp arrconf.yml + monkeypatched locator):

```python
"""Shared pytest fixtures.

Pattern: every test that mutates arrconf.yml copies the canonical file to
a tmp_path and monkeypatches `arrconf_ui.locator.arrconf_yml_path` to point
at the copy. This guarantees tests NEVER touch the real
charts/arr-stack/files/arrconf.yml.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

from arrconf_ui.locator import arrconf_yml_path

REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_ARRCONF_YML = REPO_ROOT / "charts" / "arr-stack" / "files" / "arrconf.yml"
CANONICAL_SCHEMA_JSON = REPO_ROOT / "schemas" / "arrconf-schema.json"


@pytest.fixture
def sandboxed_arrconf_yml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Copy the canonical arrconf.yml to tmp_path; patch locator to return the copy."""
    target = tmp_path / "arrconf.yml"
    shutil.copy(CANONICAL_ARRCONF_YML, target)

    def fake_path() -> Path:
        return target

    # Patch the locator module's symbol used by io+app.
    monkeypatch.setattr("arrconf_ui.locator.arrconf_yml_path", fake_path)
    monkeypatch.setattr("arrconf_ui.app.arrconf_yml_path", fake_path)
    yield target


@pytest.fixture
def sandboxed_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Copy the canonical schema to tmp_path; patch locator."""
    target = tmp_path / "arrconf-schema.json"
    shutil.copy(CANONICAL_SCHEMA_JSON, target)
    monkeypatch.setattr("arrconf_ui.locator.schema_json_path", lambda: target)
    monkeypatch.setattr("arrconf_ui.app.schema_json_path", lambda: target)
    yield target
```

**2.4 — `tools/arrconf-ui/tests/test_io_roundtrip.py`** (ruyaml round-trip preservation):

```python
"""ruyaml round-trip MUST preserve comments + blank lines + modeline."""

from __future__ import annotations

from pathlib import Path

from arrconf_ui.io import dump_yaml_to_str, read_yaml, write_yaml_atomic


def test_modeline_preserved_on_round_trip(sandboxed_arrconf_yml: Path) -> None:
    data = read_yaml(sandboxed_arrconf_yml)
    write_yaml_atomic(sandboxed_arrconf_yml, data)
    content = sandboxed_arrconf_yml.read_text(encoding="utf-8")
    # Line 1 of canonical arrconf.yml is `# yaml-language-server: $schema=...`
    assert content.splitlines()[0].startswith("# yaml-language-server:")


def test_phase_6_section_comments_preserved(sandboxed_arrconf_yml: Path) -> None:
    """The Phase 6 Seerr comment block (D-06-SCOPE-01 ...) survives round-trip."""
    data = read_yaml(sandboxed_arrconf_yml)
    write_yaml_atomic(sandboxed_arrconf_yml, data)
    content = sandboxed_arrconf_yml.read_text(encoding="utf-8")
    # Spot-check: comments on lines we know exist.
    assert "D-06-SCOPE-01" in content
    assert "D-07-INSTANCE-01" in content
    assert "ADR-8" in content


def test_atomic_write_no_corruption_on_failure(tmp_path: Path) -> None:
    """If write fails mid-stream, original file MUST be intact."""
    target = tmp_path / "arrconf.yml"
    target.write_text("categories: []\n", encoding="utf-8")
    original_mtime = target.stat().st_mtime

    # Try to dump an object that cannot be serialized; atomic write must
    # NOT clobber the original file.
    class Unserializable:
        pass

    try:
        write_yaml_atomic(target, {"bad": Unserializable()})
    except Exception:
        pass

    # File still exists with original content.
    assert target.read_text(encoding="utf-8") == "categories: []\n"

    # No leftover .tmp files.
    tmp_files = list(tmp_path.glob(".arrconf.yml.*.tmp"))
    assert tmp_files == [], f"leaked tmp files: {tmp_files}"


def test_dump_yaml_to_str_is_utf8(sandboxed_arrconf_yml: Path) -> None:
    """Émilie / Garçons / Zoé accented strings survive dump."""
    data = read_yaml(sandboxed_arrconf_yml)
    out = dump_yaml_to_str(data)
    assert "Émilie" in out
    assert "Garçons" in out
    assert "Zoé" in out
```

**2.5 — `tools/arrconf-ui/tests/test_diff.py`** (semantic diff comparator):

```python
"""Semantic diff: 7 cases covering categories add/remove/modify + per-section changes."""

from __future__ import annotations

from typing import Any

from arrconf_ui.diff import diff_configs, has_changes


def _base() -> dict[str, Any]:
    return {
        "categories": [
            {"name": "series", "kind": "series", "profile": "general",
             "display": "Séries", "base_path": "/media/series"},
            {"name": "films", "kind": "movies", "profile": "general",
             "display": "Films", "base_path": "/media/films"},
        ],
        "sonarr": {"main": {"base_url": "http://sonarr:8989", "tags": {"prune": False}}},
        "radarr": {"main": {"base_url": "http://radarr:7878"}},
        "prowlarr": {},
        "qbittorrent": {},
        "seerr": {},
        "jellyfin": {},
    }


def test_empty_diff_when_identical() -> None:
    a = _base()
    b = _base()
    diff = diff_configs(a, b)
    assert diff["categories"] == {"added": [], "modified": [], "removed": []}
    for section in ("sonarr.main", "radarr.main"):
        assert diff[section]["changed_fields"] == []
    assert has_changes(diff) is False


def test_category_added() -> None:
    a = _base()
    b = _base()
    b["categories"].append(
        {"name": "series-zoe", "kind": "series", "profile": "anime",
         "display": "Séries - Zoé", "base_path": "/media/series-zoe"}
    )
    diff = diff_configs(a, b)
    assert diff["categories"]["added"] == ["series-zoe"]
    assert diff["categories"]["modified"] == []
    assert diff["categories"]["removed"] == []
    assert has_changes(diff) is True


def test_category_removed() -> None:
    a = _base()
    b = _base()
    b["categories"] = [c for c in b["categories"] if c["name"] != "films"]
    diff = diff_configs(a, b)
    assert diff["categories"]["removed"] == ["films"]


def test_category_modified() -> None:
    a = _base()
    b = _base()
    b["categories"][0]["display"] = "Séries v2"
    diff = diff_configs(a, b)
    assert diff["categories"]["modified"] == ["series"]


def test_sonarr_field_changed() -> None:
    a = _base()
    b = _base()
    b["sonarr"]["main"]["tags"]["prune"] = True
    diff = diff_configs(a, b)
    assert "sonarr.main.tags.prune" in diff["sonarr.main"]["changed_fields"]


def test_categories_reordered_no_change() -> None:
    """Reordering same categories (matched by name) MUST NOT register as modified."""
    a = _base()
    b = _base()
    b["categories"] = list(reversed(b["categories"]))
    diff = diff_configs(a, b)
    assert diff["categories"]["added"] == []
    assert diff["categories"]["modified"] == []
    assert diff["categories"]["removed"] == []


def test_new_section_added() -> None:
    """Adding a qbittorrent.main where there was none shows up as changed_fields."""
    a = _base()
    b = _base()
    b["qbittorrent"]["main"] = {"base_url": "http://qbit:8080"}
    diff = diff_configs(a, b)
    assert "qbittorrent.main.base_url" in diff["qbittorrent.main"]["changed_fields"]
```

**2.6 — `tools/arrconf-ui/tests/test_app_endpoints.py`** (FastAPI TestClient contract):

```python
"""FastAPI endpoint contracts — GET/PUT/POST/GET on /api/* (D-02)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from arrconf_ui.app import create_app


@pytest.fixture
def client(sandboxed_arrconf_yml: Path, sandboxed_schema: Path) -> TestClient:
    """Fresh app instance with patched locators."""
    return TestClient(create_app())


def test_get_config_returns_200_with_top_level_keys(client: TestClient) -> None:
    resp = client.get("/api/config")
    assert resp.status_code == 200
    body = resp.json()
    # All 7 top-level RootConfig keys present.
    assert "categories" in body
    assert "sonarr" in body
    assert "radarr" in body
    assert "prowlarr" in body
    assert "qbittorrent" in body
    assert "seerr" in body
    assert "jellyfin" in body
    # The canonical arrconf.yml has ≥ 1 category.
    assert len(body["categories"]) >= 1


def test_get_schema_returns_json_schema(client: TestClient) -> None:
    resp = client.get("/api/schema")
    assert resp.status_code == 200
    schema = resp.json()
    assert schema["$schema"].startswith("https://json-schema.org/draft/2020-12/")
    assert "RootConfig" in schema.get("title", "") or "$defs" in schema


def test_put_config_with_valid_payload_writes_and_returns_diff(
    client: TestClient, sandboxed_arrconf_yml: Path
) -> None:
    # Load current → modify one field → PUT → assert file was updated.
    current = client.get("/api/config").json()
    new_payload = json.loads(json.dumps(current))  # deep copy via JSON
    # Add a new test category.
    new_payload["categories"].append({
        "name": "test-roundtrip",
        "kind": "series",
        "profile": "general",
        "display": "Test Round-trip",
        "base_path": "/media/test-roundtrip",
    })
    resp = client.put("/api/config", json=new_payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["has_changes"] is True
    assert "test-roundtrip" in body["diff"]["categories"]["added"]
    # File was actually written.
    assert "test-roundtrip" in sandboxed_arrconf_yml.read_text(encoding="utf-8")


def test_put_config_with_invalid_payload_returns_422(
    client: TestClient, sandboxed_arrconf_yml: Path
) -> None:
    bad = {"categories": [{"name": "x", "kind": "INVALID_KIND",
                            "profile": "general", "display": "X", "base_path": "/media/x"}]}
    resp = client.put("/api/config", json=bad)
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert "detail" in body
    assert isinstance(body["detail"], list)
    # File was NOT written — original content intact.
    assert "INVALID_KIND" not in sandboxed_arrconf_yml.read_text(encoding="utf-8")


def test_post_diff_does_not_write(client: TestClient, sandboxed_arrconf_yml: Path) -> None:
    """POST /api/diff is stateless — MUST NOT write the file."""
    original = sandboxed_arrconf_yml.read_text(encoding="utf-8")
    current = client.get("/api/config").json()
    current["categories"].append({
        "name": "preview-only", "kind": "series", "profile": "general",
        "display": "Preview", "base_path": "/media/preview-only",
    })
    resp = client.post("/api/diff", json=current)
    assert resp.status_code == 200
    body = resp.json()
    assert "preview-only" in body["diff"]["categories"]["added"]
    # File NOT modified.
    assert sandboxed_arrconf_yml.read_text(encoding="utf-8") == original


def test_phase_14_suggestarr_coupled_fields_remain_editable(client: TestClient) -> None:
    """D-09 fields MUST be plain fields on the backend — no special read-only.

    The 7 fields surface as visual badges in the FRONTEND only (Plan 15-B).
    The backend treats them as ordinary editable fields.
    """
    current = client.get("/api/config").json()
    # Edit the canonical D-09 fields.
    current["seerr"]["main"]["sonarr_service"]["activeAnimeProfileId"] = 999
    current["seerr"]["main"]["sonarr_service"]["activeProfileId"] = 999
    current["seerr"]["main"]["sonarr_service"]["activeAnimeDirectory"] = "/media/anime-new"
    current["seerr"]["main"]["sonarr_service"]["activeDirectory"] = "/media/series-new"
    current["seerr"]["main"]["radarr_service"]["activeProfileId"] = 999
    current["seerr"]["main"]["radarr_service"]["activeDirectory"] = "/media/films-new"
    # categories[name="films-zoe"].base_path
    for cat in current["categories"]:
        if cat["name"] == "films-zoe":
            cat["base_path"] = "/media/films-zoe-new"
    resp = client.put("/api/config", json=current)
    assert resp.status_code == 200, resp.text
    # All edits flowed through.
    saved = client.get("/api/config").json()
    assert saved["seerr"]["main"]["sonarr_service"]["activeAnimeProfileId"] == 999
    assert saved["seerr"]["main"]["radarr_service"]["activeProfileId"] == 999
```

**2.7 — `tools/arrconf-ui/tests/test_locator.py`** (repo root + path resolution):

```python
"""Repo-root + arrconf.yml + schema path locator (D-12)."""

from __future__ import annotations

from pathlib import Path

from arrconf_ui.locator import arrconf_yml_path, repo_root, schema_json_path


def test_repo_root_contains_pyproject() -> None:
    root = repo_root()
    assert (root / "tools" / "arrconf").is_dir()
    assert (root / "tools" / "arrconf-ui").is_dir()
    assert (root / "charts" / "arr-stack").is_dir()


def test_arrconf_yml_path_exists() -> None:
    p = arrconf_yml_path()
    assert p.exists()
    assert p.name == "arrconf.yml"
    assert p.parent.name == "files"


def test_schema_json_path_exists() -> None:
    p = schema_json_path()
    assert p.exists()
    assert p.name == "arrconf-schema.json"


def test_paths_are_absolute() -> None:
    assert arrconf_yml_path().is_absolute()
    assert schema_json_path().is_absolute()
    assert repo_root().is_absolute()
```
  </action>
  <verify>
    <automated>
cd /data/projets/perso/arr-stack/tools/arrconf-ui && uv run pytest tests/test_io_roundtrip.py tests/test_diff.py tests/test_app_endpoints.py tests/test_locator.py -v
    </automated>
  </verify>
  <acceptance_criteria>
    - All 4 endpoint tests in `test_app_endpoints.py` pass: GET /api/config (200 with 7 top-level keys), GET /api/schema (200 with $schema Draft 2020-12), PUT /api/config valid (200 + file written + diff returned), PUT /api/config invalid (422 + file NOT written), POST /api/diff (200 + file NOT modified), Phase 14 D-09 fields editable.
    - All 4 round-trip tests pass: modeline preserved, Phase 6/7 comments preserved, atomic write doesn't corrupt on failure, UTF-8 accents preserved.
    - All 7 diff tests pass: empty-diff, category-added, category-removed, category-modified, sonarr-field-changed, categories-reordered-no-change, new-section-added.
    - All 4 locator tests pass.
    - `grep -E "host=['\"]127\\.0\\.0\\.1['\"]" tools/arrconf-ui/arrconf_ui/app.py` returns 0 matches (the bind happens in `__main__.py` — Task 3 — NOT in app.py which is ASGI-pure).
    - `grep -rn "0\\.0\\.0\\.0" tools/arrconf-ui/` returns 0 matches (D-04 enforcement).
  </acceptance_criteria>
  <done>
    FastAPI app + 4 endpoints + ≥ 20 tests passing. Backend is fully testable end-to-end via TestClient.
  </done>
</task>

<task type="auto">
  <name>Task 3: Typer CLI launcher + bind/browser test + final triad pass</name>
  <files>
    tools/arrconf-ui/arrconf_ui/__main__.py,
    tools/arrconf-ui/tests/test_cli.py
  </files>
  <read_first>
    - .planning/phases/15-local-config-ui/15-CONTEXT.md (D-12 — launch UX: `arrconf-ui [--port 8765] [--no-browser]`, default port 8765, webbrowser.open(), structlog INFO message, SIGINT clean shutdown)
    - tools/arrconf/arrconf/__main__.py (typer.Typer pattern reference: `app = typer.Typer(name=..., help=..., no_args_is_help=True)` + `@app.command()`)
    - tools/arrconf-ui/pyproject.toml (created Task 1 — `arrconf-ui = arrconf_ui.__main__:app`)
    - tools/arrconf-ui/arrconf_ui/app.py (created Task 2 — module-level `app = create_app()`)
  </read_first>
  <action>
**3.1 — `tools/arrconf-ui/arrconf_ui/__main__.py`** (Typer CLI per D-12):

```python
"""arrconf-ui CLI entrypoint — `arrconf-ui [--port 8765] [--no-browser]` (D-12).

Behavior:
1. Locate the repo root via locator.repo_root().
2. Locate charts/arr-stack/files/arrconf.yml — fail fast if missing.
3. Start uvicorn on 127.0.0.1:{port} (NEVER 0.0.0.0 — D-04).
4. Unless --no-browser: webbrowser.open() the URL after a short startup delay.
5. Log `INFO: Local config UI ready at http://localhost:{port}` so the
   operator sees the URL even with --no-browser.
6. SIGINT exits cleanly (uvicorn handles this).

Default port: 8765 (D-12 — fixed for muscle memory; overridable via flag
or ARRCONF_UI_PORT env var).
"""

from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from typing import Annotated

import structlog
import typer
import uvicorn

from arrconf_ui.locator import arrconf_yml_path

log = structlog.get_logger()

DEFAULT_PORT = 8765
HOST = "127.0.0.1"  # D-04 — NEVER change to 0.0.0.0

app = typer.Typer(
    name="arrconf-ui",
    help="Local web UI for editing charts/arr-stack/files/arrconf.yml (Phase 15).",
    no_args_is_help=False,
    add_completion=False,
)


def _resolve_port(port: int | None) -> int:
    """Port resolution: CLI flag → env var → default 8765."""
    if port is not None:
        return port
    env = os.environ.get("ARRCONF_UI_PORT")
    if env:
        try:
            return int(env)
        except ValueError:
            log.warning("invalid_port_env", value=env, fallback=DEFAULT_PORT)
    return DEFAULT_PORT


def _open_browser_delayed(url: str, delay_s: float = 0.6) -> None:
    """Open the system browser after uvicorn is ready."""
    def _open() -> None:
        time.sleep(delay_s)
        webbrowser.open(url)

    threading.Thread(target=_open, daemon=True).start()


@app.command()
def main(
    port: Annotated[
        int | None,
        typer.Option("--port", "-p", help=f"TCP port (default: {DEFAULT_PORT}, env: ARRCONF_UI_PORT)."),
    ] = None,
    no_browser: Annotated[
        bool,
        typer.Option("--no-browser", help="Do not auto-open the system browser."),
    ] = False,
) -> None:
    """Start the local config UI on 127.0.0.1.

    Logs the URL to stdout so the operator sees it even with --no-browser.
    """
    yml = arrconf_yml_path()
    if not yml.exists():
        typer.echo(f"ERROR: arrconf.yml not found at {yml}", err=True)
        raise typer.Exit(code=2)

    resolved_port = _resolve_port(port)
    url = f"http://localhost:{resolved_port}"
    typer.echo(f"INFO: Local config UI ready at {url}")
    typer.echo(f"INFO: Editing {yml}")

    if not no_browser:
        _open_browser_delayed(url)

    # uvicorn.run is blocking and handles SIGINT cleanly.
    uvicorn.run(
        "arrconf_ui.app:app",
        host=HOST,
        port=resolved_port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    app()
```

**3.2 — `tools/arrconf-ui/tests/test_cli.py`** (CLI contract — port resolution + bind assertions, NO actual server start):

```python
"""CLI contract: port resolution, default port 8765, host 127.0.0.1 (D-04 + D-12)."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from arrconf_ui.__main__ import DEFAULT_PORT, HOST, _resolve_port, app


def test_default_port_is_8765() -> None:
    """D-12: default port 8765 (fixed for muscle memory)."""
    assert DEFAULT_PORT == 8765


def test_host_is_loopback_only() -> None:
    """D-04: bind 127.0.0.1 only, NEVER 0.0.0.0."""
    assert HOST == "127.0.0.1"
    assert HOST != "0.0.0.0"


def test_resolve_port_cli_flag_wins() -> None:
    """CLI --port wins over env var + default."""
    with patch.dict(os.environ, {"ARRCONF_UI_PORT": "9999"}):
        assert _resolve_port(1234) == 1234


def test_resolve_port_env_var_used_when_no_flag() -> None:
    with patch.dict(os.environ, {"ARRCONF_UI_PORT": "9999"}):
        assert _resolve_port(None) == 9999


def test_resolve_port_invalid_env_falls_back_to_default() -> None:
    with patch.dict(os.environ, {"ARRCONF_UI_PORT": "not_a_port"}):
        assert _resolve_port(None) == DEFAULT_PORT


def test_resolve_port_default_when_nothing_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARRCONF_UI_PORT", raising=False)
    assert _resolve_port(None) == DEFAULT_PORT


def test_cli_help_works() -> None:
    """The typer app has a help text and a `main` command registered."""
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Local web UI" in result.output or "config UI" in result.output.lower()


def test_cli_missing_arrconf_yml_exits_2(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """If arrconf.yml is missing, CLI exits with code 2 BEFORE binding."""
    from typer.testing import CliRunner

    missing = tmp_path / "does-not-exist.yml"
    monkeypatch.setattr("arrconf_ui.__main__.arrconf_yml_path", lambda: missing)
    runner = CliRunner()
    result = runner.invoke(app, ["--no-browser", "--port", "0"])
    assert result.exit_code == 2
    assert "ERROR" in result.output
```

**3.3 — Run the FULL triad locally to confirm zero warnings/errors:**

```bash
cd /data/projets/perso/arr-stack/tools/arrconf-ui
uv sync
uv run ruff format --check .
uv run ruff check .
uv run mypy .
uv run pytest -v
```

The triad MUST exit 0 on every step before this task is `done`. Any ruff format issue → run `uv run ruff format .` to autofix, re-run `--check`, commit.
  </action>
  <verify>
    <automated>
cd /data/projets/perso/arr-stack/tools/arrconf-ui && uv run ruff format --check . && uv run ruff check . && uv run mypy . && uv run pytest -v && grep -E "DEFAULT_PORT\s*=\s*8765" arrconf_ui/__main__.py && grep -E "HOST\s*=\s*['\"]127\\.0\\.0\\.1['\"]" arrconf_ui/__main__.py && ! grep -rn "0\\.0\\.0\\.0" arrconf_ui/ tests/
    </automated>
  </verify>
  <acceptance_criteria>
    - `uv run ruff format --check .` exits 0.
    - `uv run ruff check .` exits 0.
    - `uv run mypy .` exits 0 (strict mode — no `Any` leaks except where ignored via `tool.mypy.overrides` for `ruyaml.*`).
    - `uv run pytest -v` exits 0; ≥ 25 tests collected across 5 test files; 0 failures.
    - `grep -E "DEFAULT_PORT\\s*=\\s*8765" tools/arrconf-ui/arrconf_ui/__main__.py` returns 1 match (D-12 default port).
    - `grep -E "HOST\\s*=\\s*['\"]127\\.0\\.0\\.1['\"]" tools/arrconf-ui/arrconf_ui/__main__.py` returns 1 match (D-04 bind).
    - `grep -rn "0\\.0\\.0\\.0" tools/arrconf-ui/arrconf_ui/ tools/arrconf-ui/tests/` returns 0 matches (D-04 enforcement).
    - `grep -E "webbrowser\\.open" tools/arrconf-ui/arrconf_ui/__main__.py` returns 1 match (D-12 auto-open).
    - `uv run arrconf-ui --help` exits 0 and prints "Local web UI".
  </acceptance_criteria>
  <done>
    Backend is launchable via `uv run arrconf-ui` (Plan 15-B can build against the contract). Triad is green. ≥ 25 tests pass.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| operator-browser → FastAPI (loopback) | localhost-only, no auth (D-04). Only the operator can reach the server. |
| FastAPI → arrconf.yml (filesystem) | Atomic write via tempfile.NamedTemporaryFile + os.replace (D-05). |
| FastAPI → arrconf.config.RootConfig | pydantic ValidationError → 422 (D-06). |

## STRIDE Threat Register

`security_enforcement` is not declared in init context (treated as enabled by default per planner policy).

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-15-A-01 | S (Spoofing) | FastAPI bind | accept | D-04 — loopback only, no remote callers; single-tenant homelab posture matches Phase 13/14 architecture. |
| T-15-A-02 | T (Tampering) | arrconf.yml writes | mitigate | `write_yaml_atomic` uses tempfile.NamedTemporaryFile in SAME directory + os.replace (atomic on POSIX same-fs). `test_atomic_write_no_corruption_on_failure` asserts no clobber on serializer exception. |
| T-15-A-03 | R (Repudiation) | Save action | accept | Git is the audit log (operator does `git diff` + commit + push manually per D-05). No UI-side logging beyond `structlog.info("config_saved", ...)`. |
| T-15-A-04 | I (Info disclosure) | GET /api/config | accept | Localhost-only (D-04). No secrets in arrconf.yml — secrets live in `arrconf-env` SealedSecret (out of UI scope per CLAUDE.md "Aucune lecture de fichier de secrets"). |
| T-15-A-05 | D (DoS) | PUT /api/config | accept | Single-operator; rate-limiting absent by design. Pydantic validation on a small dict is O(ms). |
| T-15-A-06 | E (Elevation) | StaticFiles mount | mitigate | StaticFiles is mounted AFTER `/api/*` routes (FastAPI route precedence) AND only if `tools/arrconf-ui/web/dist/` exists. Plan 15-B controls the dist directory; no path traversal vector since FastAPI's StaticFiles uses Starlette's safe path handling. |
| T-15-A-07 | T | Pydantic 422 leaks pydantic internals | accept | `e.errors()` returns the public Pydantic error format (loc, msg, type, input) — designed for client display per Pydantic docs. No secrets. |
| T-15-A-08 | I | Atomic-write tmp files persist on crash | mitigate | NamedTemporaryFile with `prefix=.arrconf.yml.` lives in `charts/arr-stack/files/`. Test `test_atomic_write_no_corruption_on_failure` asserts cleanup. Operator-visible filename pattern (`.arrconf.yml.*.tmp`) — easy to spot + delete. |
</threat_model>

<verification>
**Phase-level checks (Plan 15-A close):**

1. `cd tools/arrconf-ui && uv run ruff format --check . && uv run ruff check . && uv run mypy . && uv run pytest -v` exits 0.
2. `uv run arrconf-ui --no-browser --port 8765` (in another terminal) starts the server; `curl -s http://localhost:8765/api/config | jq '.categories | length'` returns ≥ 1; `curl -s http://localhost:8765/api/schema | jq '."$schema"'` returns `"https://json-schema.org/draft/2020-12/schema"`; SIGINT shuts down cleanly.
3. `grep -rn "0\.0\.0\.0" tools/arrconf-ui/` returns 0 matches (D-04).
4. Git status: 14 new files staged under `tools/arrconf-ui/`; ZERO files modified under `tools/arrconf/`, `charts/`, or `schemas/`.
5. `grep -E "arrconf\\.image\\.tag" charts/arr-stack/values.yaml` shows the SAME value as before the PR (D-11 — no co-bump).
</verification>

<success_criteria>
**Plan 15-A is complete when:**

- All 14 files created (1 pyproject + 6 arrconf_ui modules + 7 tests).
- Triad green (ruff format check + ruff check + mypy strict + pytest).
- ≥ 25 tests passing across `test_io_roundtrip.py`, `test_diff.py`, `test_app_endpoints.py`, `test_locator.py`, `test_cli.py`.
- Manual smoke: `uv run arrconf-ui --no-browser` starts on 127.0.0.1:8765; all 4 endpoints respond per contract.
- ZERO modifications to `tools/arrconf/`, `charts/`, `schemas/`.
- ZERO `arrconf.image.tag` bumps in `charts/arr-stack/values.yaml` (D-11).
- All 7 must-haves.truths verified.
- All 8 STRIDE threats addressed with disposition + mitigation/accept rationale.
</success_criteria>

<output>
After completion, create `.planning/phases/15-local-config-ui/15-A-SUMMARY.md` capturing:

- All 14 files created with line counts.
- Triad exit codes (each step).
- pytest summary (tests collected / passed / failed / coverage if computed).
- Manual smoke test output (3 curl commands + structlog output).
- Confirmation that `tools/arrconf/`, `charts/`, `schemas/` were not modified (`git diff --stat` excerpt).
- D-11 confirmation: `charts/arr-stack/values.yaml#arrconf.image.tag` unchanged.
- Hand-off note to Plan 15-B: "Backend running on 127.0.0.1:8765, endpoint contract validated. Plan 15-B can `npm run dev` with Vite proxy targeting :8765 per CONTEXT Claude's Discretion."
</output>
