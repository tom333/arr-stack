---
phase: 09-categories-data-model-chart-initcontainer
plan: 09-A-python-schema
type: execute
wave: 1
depends_on: []
files_modified:
  - tools/arrconf/arrconf/resources/categories.py
  - tools/arrconf/arrconf/config.py
  - tools/arrconf/tests/test_categories.py
  - schemas/arrconf-schema.json
autonomous: true
requirements:
  - REQ-categories-schema
requirements_addressed:
  - REQ-categories-schema
tags:
  - python
  - pydantic
  - schema

must_haves:
  truths:
    - "RootConfig.categories: list[Category] = Field(default_factory=list) field exists and parses zero-or-more Category entries."
    - "A new Category model with extra='forbid', kebab-case name regex, Literal['movies','series'] for kind, Literal['general','anime','family'] for profile, plus a model_validator(mode='after') enforcing base_path == f'/media/{name}' (D-04)."
    - "schemas/arrconf-schema.json is regenerated and matches a fresh arrconf schema-gen byte-for-byte."
    - "tools/arrconf/tests/test_categories.py exists and exercises happy-path + every invariant violation; uv run pytest tests/test_categories.py -x exits 0."
    - "D-16: the schema-staleness CI gate already exists (tools/arrconf/tests/test_schema_gen.py::test_schema_committed_matches_regen + tests.yml step 'Verify schema reproducibility'); Plan A regenerates schemas/arrconf-schema.json so the existing gate passes — no NEW gate code is shipped (D-16 implementation surface is regen + commit only, per 09-RESEARCH.md Q4 'ALREADY SOLVED')."
  artifacts:
    - path: "tools/arrconf/arrconf/resources/categories.py"
      provides: "Category model + Kind/Profile Literal aliases + base_path invariant validator"
      contains: "class Category(BaseModel)"
    - path: "tools/arrconf/arrconf/config.py"
      provides: "RootConfig.categories field"
      contains: "categories: list[MediaCategory]"
    - path: "tools/arrconf/tests/test_categories.py"
      provides: "Parametric pydantic validation tests"
      min_lines: 80
    - path: "schemas/arrconf-schema.json"
      provides: "Regenerated JSON Schema with the Category type"
      contains: "Category"
  key_links:
    - from: "tools/arrconf/arrconf/config.py"
      to: "tools/arrconf/arrconf/resources/categories.py"
      via: "from arrconf.resources.categories import Category as MediaCategory (alias to avoid collision with the existing qBit Category import at config.py:28)"
      pattern: "from arrconf\\.resources\\.categories import Category"
    - from: "tools/arrconf/arrconf/schema_gen.py"
      to: "schemas/arrconf-schema.json"
      via: "RootConfig.model_json_schema() -> json.dumps(sort_keys=True) (existing pipeline at schema_gen.py:33)"
      pattern: "model_json_schema"
---

<objective>
Land the pydantic `Category` resource model, the `RootConfig.categories` field, the regenerated JSON Schema, and parametric unit tests for every Category invariant.

Purpose: Stand up the **data contract** Phase 10's 6-app propagation will compile against. Without this plan, no other Phase 9 plan can validate `categories[]` content in `arrconf.yml` (Plan C) and no Phase 10 plan can read a typed `RootConfig.categories` list.

Output:
- `tools/arrconf/arrconf/resources/categories.py` (NEW — `Category` model + `Kind`/`Profile` Literal aliases + base_path validator)
- `tools/arrconf/arrconf/config.py` (MODIFIED — 1 import + 1 `RootConfig` field + class-docstring paragraph)
- `tools/arrconf/tests/test_categories.py` (NEW — parametric tests covering D-01..D-04 + D-05 invariants)
- `schemas/arrconf-schema.json` (REGENERATED — committed delta is the new `Category` type definition)

D-NN coverage (locked decisions implemented):
- **D-01, D-02** — `profile` Literal enum closes the 5x2 mapping (`general`/`anime`/`family`); the 10 production assignments live in `arrconf.yml` (Plan C) but the *enum closure* is Plan A.
- **D-04** — STRICT `base_path == /media/{name}` invariant, pydantic `model_validator(mode='after')`.
- **D-05** — `RootConfig.categories: list[Category] = Field(default_factory=list)` — optional, defaults to `[]`, mirrors sibling `default_factory=dict` semantics.
- **D-13** — Reconcilers are NOT touched. `RootConfig.categories` is parsed but never consumed by any reconciler in Phase 9.
- **D-16** — Existing CI gate at `tests/test_schema_gen.py::test_schema_committed_matches_regen` enforces the regenerated `schemas/arrconf-schema.json` is committed (no new gate code needed; only run the regen and commit).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/09-categories-data-model-chart-initcontainer/09-CONTEXT.md
@.planning/phases/09-categories-data-model-chart-initcontainer/09-RESEARCH.md
@.planning/phases/09-categories-data-model-chart-initcontainer/09-PATTERNS.md
@.planning/phases/09-categories-data-model-chart-initcontainer/09-VALIDATION.md
@tools/arrconf/arrconf/resources/qbittorrent/category.py
@tools/arrconf/arrconf/resources/sonarr/download_client.py
@tools/arrconf/arrconf/config.py
@tools/arrconf/arrconf/schema_gen.py
@tools/arrconf/tests/test_scope_violation.py
@tools/arrconf/tests/test_config.py
@tools/arrconf/tests/test_schema_gen.py

<interfaces>
<!-- Reference shape — Phase 9's Category mirrors qbittorrent.Category but lives at the resources/ root because it is cross-cutting. -->

From `tools/arrconf/arrconf/resources/qbittorrent/category.py` (lines 1-26):

```python
"""qBittorrent category — Phase 5 D-05-QBT-02 resource."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Category(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str = Field(description="...")
    savePath: str = Field(default="", description="...")
```

From `tools/arrconf/arrconf/resources/sonarr/download_client.py` (Literal idiom at lines 51-53):

```python
protocol: Literal["torrent", "usenet"] = Field(
    description="Download protocol — must match implementation."
)
```

From `tools/arrconf/arrconf/config.py` (current state — lines 22-38 + 621-642):

```python
# line 28 — existing import that collides with the new top-level Category:
from arrconf.resources.qbittorrent.category import Category

# RootConfig class body (lines 621-642):
class RootConfig(BaseModel):
    """Top-level arrconf YAML schema (root for JSON Schema generation)."""
    model_config = ConfigDict(extra="forbid")
    sonarr: dict[str, SonarrInstance] = Field(default_factory=dict)
    radarr: dict[str, RadarrInstance] = Field(default_factory=dict)
    prowlarr: dict[str, ProwlarrInstance] = Field(default_factory=dict)
    qbittorrent: dict[str, QbittorrentInstance] = Field(default_factory=dict)
    seerr: dict[str, SeerrInstance] = Field(default_factory=dict)
    jellyfin: dict[str, JellyfinInstance] = Field(default_factory=dict)
```

**NAME COLLISION (CRITICAL — per 09-PATTERNS.md lines 287-300):** The existing import `from arrconf.resources.qbittorrent.category import Category` at `config.py:28` MUST be preserved as-is. The new top-level `Category` MUST be imported aliased:

```python
from arrconf.resources.categories import Category as MediaCategory
```

This is Option A from 09-PATTERNS.md (minimal blast radius — only the new field declaration uses `MediaCategory`; no existing reference is renamed).

From `tools/arrconf/arrconf/schema_gen.py:33` (the regen pipeline — DO NOT modify):

```python
def write_schema(output_path: Path) -> None:
    schema = RootConfig.model_json_schema(schema_generator=Draft202012Generator)
    output_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
```

From `tools/arrconf/tests/test_schema_gen.py:49-61` (the existing D-16 CI gate — DO NOT modify):

```python
def test_schema_committed_matches_regen(tmp_path: Path) -> None:
    committed = Path(__file__).parent.parent.parent.parent / "schemas/arrconf-schema.json"
    if not committed.exists():
        return
    out = tmp_path / "regen.json"
    write_schema(out)
    assert committed.read_bytes() == out.read_bytes()
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task A1: Author the Category pydantic model + Kind/Profile enums in tools/arrconf/arrconf/resources/categories.py</name>
  <files>tools/arrconf/arrconf/resources/categories.py</files>
  <read_first>
    - tools/arrconf/arrconf/resources/qbittorrent/category.py (entire file — primary analog; per 09-PATTERNS.md line 28)
    - tools/arrconf/arrconf/resources/sonarr/download_client.py (lines 51-53 for `Literal[...]` idiom; per 09-PATTERNS.md line 64)
    - .planning/phases/09-categories-data-model-chart-initcontainer/09-CONTEXT.md (decisions D-01, D-02, D-04, D-05 — the locked field shape)
    - .planning/phases/09-categories-data-model-chart-initcontainer/09-PATTERNS.md (Pattern 1 — `pydantic resource module shape`)
    - .planning/phases/09-categories-data-model-chart-initcontainer/09-RESEARCH.md §"Pattern 1: pydantic resource module shape" (the verified-pattern code block at lines 481-533)
  </read_first>
  <behavior>
    - Valid input: `{"name": "series-emilie", "kind": "series", "profile": "general", "display": "Séries - Émilie", "base_path": "/media/series-emilie"}` parses cleanly into a `Category` instance.
    - Invalid `name`: `"Series_Emilie"` (underscore + uppercase) raises `pydantic.ValidationError` with the kebab-case regex in the message.
    - Invalid `kind`: `"music"` raises `ValidationError`.
    - Invalid `profile`: `"documentary"` raises `ValidationError`.
    - Invalid `base_path`: `"/media/series-emilie-typo"` (when `name="series-emilie"`) raises `ValueError` containing `"D-04 strict invariant"`.
    - Extra field: `{"name": "x", "kind": "movies", "profile": "general", "display": "X", "base_path": "/media/x", "rogue": "field"}` raises `ValidationError` because `extra='forbid'`.
  </behavior>
  <action>
    Create the new file `tools/arrconf/arrconf/resources/categories.py` with the exact code below (verbatim from 09-RESEARCH.md §Pattern 1, verified-pattern code block at lines 481-533):

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

        Match key: ``name`` (kebab-case slug, stable across reconcile runs).
        D-04 invariant: ``base_path`` MUST equal ``f"/media/{name}"``.
        """

        model_config = ConfigDict(extra="forbid")
        name: str = Field(
            description="Kebab-case slug (e.g. 'series-emilie'). Stable match key.",
            pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$",
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

    Notes on what is locked vs. discretion:
    - `model_config = ConfigDict(extra="forbid")` — locked (D-04; aligns with `RootConfig`).
    - `name` regex `^[a-z0-9]+(-[a-z0-9]+)*$` — locked (kebab-case, no consecutive hyphens, no leading/trailing hyphens, no underscores or uppercase). This is the STRIDE-Tampering mitigation: blocks path-traversal payloads like `../etc/passwd` from ever reaching the Plan-B Helm Job.
    - `Kind` / `Profile` exposed as MODULE-LEVEL type aliases (not nested) so Phase 10's propagators can re-import them.
    - `model_validator(mode="after")` raises `ValueError` (NOT `AssertionError`) — pydantic catches both, but `ValueError` is the project convention.

    After writing, run `cd tools/arrconf && uv run ruff check arrconf/resources/categories.py && uv run ruff format --check arrconf/resources/categories.py && uv run mypy arrconf/resources/categories.py` — all three MUST exit 0 before considering the task complete (CLAUDE.md "Conventions développement" + CF-07-RUFF-FORMAT-CI carry-forward).
  </action>
  <verify>
    <automated>cd tools/arrconf && uv run ruff check arrconf/resources/categories.py && uv run ruff format --check arrconf/resources/categories.py && uv run mypy arrconf/resources/categories.py && uv run python -c "from arrconf.resources.categories import Category, Kind, Profile; c = Category(name='series-emilie', kind='series', profile='general', display='Series - Emilie', base_path='/media/series-emilie'); print('OK', c.name, c.kind, c.profile)"</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tools/arrconf/arrconf/resources/categories.py` exits 0
    - `grep -F 'class Category(BaseModel):' tools/arrconf/arrconf/resources/categories.py` exits 0
    - `grep -F 'extra="forbid"' tools/arrconf/arrconf/resources/categories.py` exits 0
    - `grep -F '@model_validator(mode="after")' tools/arrconf/arrconf/resources/categories.py` exits 0
    - `grep -F '"/media/{self.name}"' tools/arrconf/arrconf/resources/categories.py` exits 0
    - `grep -E 'Kind = Literal\["movies", "series"\]' tools/arrconf/arrconf/resources/categories.py` exits 0
    - `grep -E 'Profile = Literal\["general", "anime", "family"\]' tools/arrconf/arrconf/resources/categories.py` exits 0
    - `grep -F 'pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$"' tools/arrconf/arrconf/resources/categories.py` exits 0
    - `cd tools/arrconf && uv run mypy arrconf/resources/categories.py` exits 0
    - `cd tools/arrconf && uv run ruff format --check arrconf/resources/categories.py` exits 0
  </acceptance_criteria>
  <done>
    `tools/arrconf/arrconf/resources/categories.py` exists. The 10 production category dicts from 09-CONTEXT.md §Specifics each parse to a `Category` instance via `Category(**d)`. Invalid permutations (wrong enum, base_path mismatch, kebab-case violation, extra field) raise `pydantic.ValidationError`. `ruff check`, `ruff format --check`, and `mypy` all green on the new file.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task A2: Wire RootConfig.categories field in tools/arrconf/arrconf/config.py (with import alias to avoid Category name collision)</name>
  <files>tools/arrconf/arrconf/config.py</files>
  <read_first>
    - tools/arrconf/arrconf/config.py (full file, especially lines 22-38 imports block + lines 621-642 RootConfig class body)
    - tools/arrconf/arrconf/resources/categories.py (the `Category` class authored in Task A1)
    - .planning/phases/09-categories-data-model-chart-initcontainer/09-PATTERNS.md lines 287-330 — "Import-add pattern (BEWARE NAME COLLISION)" + "Field-add pattern"
    - .planning/phases/09-categories-data-model-chart-initcontainer/09-CONTEXT.md (D-05 — Field optionality + default_factory=list semantics; D-13 — reconcilers MUST NOT touch this field)
    - .planning/phases/09-categories-data-model-chart-initcontainer/09-RESEARCH.md §"Pattern 2: RootConfig field placement" — FIRST field is recommended (mirrors arrconf.yml top-of-file placement)
  </read_first>
  <behavior>
    - `from arrconf.config import RootConfig; "categories" in RootConfig.model_fields` returns `True`.
    - `RootConfig().categories` returns `[]` (default empty list, mirrors `RootConfig().sonarr == {}` semantics).
    - `RootConfig(categories=[{"name": "x", "kind": "movies", "profile": "general", "display": "X", "base_path": "/media/x"}])` validates and produces a `Category` instance in `.categories[0]`.
    - The existing `Category` import at line 28 (qBit) still resolves to `arrconf.resources.qbittorrent.category.Category` — no existing test or code path breaks.
  </behavior>
  <action>
    Two edits to `tools/arrconf/arrconf/config.py`:

    **Edit 1 — add the aliased import.** In the imports block (somewhere near the existing line 28 `from arrconf.resources.qbittorrent.category import Category`), ADD a new line:

    ```python
    from arrconf.resources.categories import Category as MediaCategory
    ```

    Use `Category as MediaCategory` (Option A from 09-PATTERNS.md line 294) to minimize blast radius — the existing qBit `Category` symbol stays unchanged and no other reference in the file needs to be renamed.

    **Edit 2 — add the `categories` field to `RootConfig`** at line ~636 (the class body that currently starts `sonarr: dict[str, SonarrInstance] = ...`). Insert `categories: list[MediaCategory] = Field(default_factory=list)` as the **FIRST** field (above `sonarr`), per 09-RESEARCH.md §"Pattern 2: RootConfig field placement" — FIRST field mirrors the YAML top-of-file placement that Plan C will produce.

    Update the `RootConfig` class docstring to append a phase paragraph (mirrors existing "Phase 3", "Phase 5 (D-05-QBT-02)", "Phase 6 (D-06-SCOPE-01)", "Phase 7 (D-07-INSTANCE-01)" pattern):

    ```
    Phase 9 (D-05): adds top-level ``categories`` list — cross-cutting,
    drives Phase 10 propagation to qBit/Sonarr/Radarr/configarr/Seerr/Jellyfin.
    ```

    Final shape of the class body (lines that change):

    ```python
    class RootConfig(BaseModel):
        """Top-level arrconf YAML schema (root for JSON Schema generation).
        ...

        Phase 9 (D-05): adds top-level ``categories`` list — cross-cutting,
        drives Phase 10 propagation to qBit/Sonarr/Radarr/configarr/Seerr/Jellyfin.
        """

        model_config = ConfigDict(extra="forbid")
        categories: list[MediaCategory] = Field(default_factory=list)
        sonarr: dict[str, SonarrInstance] = Field(default_factory=dict)
        radarr: dict[str, RadarrInstance] = Field(default_factory=dict)
        prowlarr: dict[str, ProwlarrInstance] = Field(default_factory=dict)
        qbittorrent: dict[str, QbittorrentInstance] = Field(default_factory=dict)
        seerr: dict[str, SeerrInstance] = Field(default_factory=dict)
        jellyfin: dict[str, JellyfinInstance] = Field(default_factory=dict)
    ```

    Do NOT modify any reconciler, dump, or differ code — Phase 9 (D-13) is strict that reconcilers do not yet read this field.

    After editing, run `cd tools/arrconf && uv run ruff check arrconf/config.py && uv run ruff format --check arrconf/config.py && uv run mypy arrconf/config.py` — all three MUST exit 0.
  </action>
  <verify>
    <automated>cd tools/arrconf && uv run ruff check arrconf/config.py && uv run ruff format --check arrconf/config.py && uv run mypy arrconf/config.py && uv run python -c "from arrconf.config import RootConfig; from arrconf.resources.qbittorrent.category import Category as QbitCat; assert 'categories' in RootConfig.model_fields; assert RootConfig().categories == []; r = RootConfig(categories=[{'name':'films-zoe','kind':'movies','profile':'anime','display':'Films - Zoe','base_path':'/media/films-zoe'}]); assert r.categories[0].name == 'films-zoe'; print('OK qBit Category preserved:', QbitCat.__name__)"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -F 'from arrconf.resources.categories import Category as MediaCategory' tools/arrconf/arrconf/config.py` exits 0
    - `grep -F 'from arrconf.resources.qbittorrent.category import Category' tools/arrconf/arrconf/config.py` exits 0 (UNCHANGED — still present)
    - `grep -F 'categories: list[MediaCategory] = Field(default_factory=list)' tools/arrconf/arrconf/config.py` exits 0
    - `grep -F 'Phase 9 (D-05): adds top-level' tools/arrconf/arrconf/config.py` exits 0
    - `cd tools/arrconf && uv run python -c 'from arrconf.config import RootConfig; assert "categories" in RootConfig.model_fields'` exits 0
    - `cd tools/arrconf && uv run mypy arrconf/config.py` exits 0
    - `cd tools/arrconf && uv run ruff format --check arrconf/config.py` exits 0
    - `cd tools/arrconf && uv run pytest tests/test_config.py -x` exits 0 (no existing test regressed)
  </acceptance_criteria>
  <done>
    `RootConfig` exposes `categories: list[Category]` (alias `MediaCategory`) as the first field. The existing qBit `Category` import is preserved (no rename ripple). All existing tests in `test_config.py` continue to pass. `ruff` + `mypy` green on `config.py`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task A3: Author parametric tests in tools/arrconf/tests/test_categories.py + regenerate schemas/arrconf-schema.json</name>
  <files>tools/arrconf/tests/test_categories.py, schemas/arrconf-schema.json</files>
  <read_first>
    - tools/arrconf/tests/test_scope_violation.py (lines 76-117 — parametric structure template, per 09-PATTERNS.md line 94)
    - tools/arrconf/tests/test_config.py (lines 73-97 — `pytest.raises(ValidationError, match=...)` shape, per 09-PATTERNS.md line 105)
    - tools/arrconf/arrconf/resources/categories.py (the model authored in A1 — the unit under test)
    - .planning/phases/09-categories-data-model-chart-initcontainer/09-CONTEXT.md §Specifics (the EXACT 10-entry block — happy-path inputs)
    - .planning/phases/09-categories-data-model-chart-initcontainer/09-VALIDATION.md "Wave 0 Requirements" — bullet 1 enumerates the test cases required
  </read_first>
  <behavior>
    The test file MUST cover at least these parametric cases:
    - **Happy path** (parametrized over the 10 production category dicts from 09-CONTEXT.md §Specifics lines 350-401): each dict instantiates `Category` cleanly; `.name`, `.kind`, `.profile`, `.display`, `.base_path` round-trip.
    - **Kebab-case `name` violations** (parametrized): `"Series_Emilie"`, `"SERIES"`, `"series--emilie"` (double hyphen), `"-series"` (leading hyphen), `"series-"` (trailing hyphen), `"séries"` (non-ASCII) each raise `ValidationError`.
    - **`kind` enum violations**: `"music"`, `"shorts"`, `"books"`, `""` (empty string) each raise `ValidationError`.
    - **`profile` enum violations**: `"documentary"`, `"general "` (trailing space), `""` each raise `ValidationError`.
    - **`base_path` invariant violations** (D-04): `name="x"` + `base_path="/media/y"` raises `ValueError` whose string representation contains `"D-04 strict invariant"`; `name="x"` + `base_path="/data/x"` (wrong prefix) raises with the same marker; `name="x"` + `base_path="/media/x/sub"` (extra path component) raises.
    - **`extra='forbid'`**: a dict with all 5 valid fields + `"rogue": "field"` raises `ValidationError`.
    - **Missing required field**: a dict missing `name` (or any of the 5 fields) raises `ValidationError`.

    After all tests are green, the schema regen MUST also be byte-clean: `cd tools/arrconf && uv run arrconf schema-gen --output ../../schemas/arrconf-schema.json && git diff --exit-code schemas/arrconf-schema.json` exits 0 (i.e. running regen again is a no-op once committed).
  </behavior>
  <action>
    **Sub-step 1 — write the test file.** Create `tools/arrconf/tests/test_categories.py` with the structure below. Use `pytest.mark.parametrize` (per the analog at `test_scope_violation.py:76-117`) and `pytest.raises(ValidationError, match=...)` (per the analog at `test_config.py:73-82`):

    ```python
    """Tests for Category pydantic model — Phase 9 D-01/D-02/D-04/D-05 invariants.

    Requirements covered: REQ-categories-schema.
    """

    from __future__ import annotations

    import pytest
    from pydantic import ValidationError

    from arrconf.resources.categories import Category

    # The 10 production categories (verbatim from 09-CONTEXT.md §Specifics)
    PRODUCTION_CATEGORIES = [
        {"name": "series", "kind": "series", "profile": "general", "display": "Séries", "base_path": "/media/series"},
        {"name": "series-emilie", "kind": "series", "profile": "general", "display": "Séries - Émilie", "base_path": "/media/series-emilie"},
        {"name": "series-thomas", "kind": "series", "profile": "general", "display": "Séries - Thomas", "base_path": "/media/series-thomas"},
        {"name": "series-garcons", "kind": "series", "profile": "family", "display": "Séries - Garçons", "base_path": "/media/series-garcons"},
        {"name": "series-zoe", "kind": "series", "profile": "anime", "display": "Séries - Zoé", "base_path": "/media/series-zoe"},
        {"name": "films", "kind": "movies", "profile": "general", "display": "Films", "base_path": "/media/films"},
        {"name": "nouveaux-films", "kind": "movies", "profile": "general", "display": "Nouveaux Films", "base_path": "/media/nouveaux-films"},
        {"name": "films-enfants", "kind": "movies", "profile": "family", "display": "Films - Enfants", "base_path": "/media/films-enfants"},
        {"name": "films-animation-enfants", "kind": "movies", "profile": "family", "display": "Films - Animation Enfants", "base_path": "/media/films-animation-enfants"},
        {"name": "films-zoe", "kind": "movies", "profile": "anime", "display": "Films - Zoé", "base_path": "/media/films-zoe"},
    ]


    @pytest.mark.parametrize("data", PRODUCTION_CATEGORIES, ids=lambda d: d["name"])
    def test_production_categories_validate(data: dict) -> None:
        """All 10 production categories must parse cleanly (D-01/D-02/D-03/D-04 conjunction)."""
        cat = Category(**data)
        assert cat.name == data["name"]
        assert cat.kind == data["kind"]
        assert cat.profile == data["profile"]
        assert cat.display == data["display"]
        assert cat.base_path == data["base_path"]


    @pytest.mark.parametrize(
        "bad_name",
        ["Series_Emilie", "SERIES", "series--emilie", "-series", "series-", "séries", "series emilie", ""],
    )
    def test_kebab_case_name_violations(bad_name: str) -> None:
        """Non-kebab-case names must be rejected by the pattern= validator."""
        with pytest.raises(ValidationError, match="String should match pattern"):
            Category(name=bad_name, kind="series", profile="general", display="X", base_path=f"/media/{bad_name}")


    @pytest.mark.parametrize("bad_kind", ["music", "shorts", "books", "", "Movies"])
    def test_kind_enum_violations(bad_kind: str) -> None:
        """Only 'movies' or 'series' (Literal) — D-01/D-02."""
        with pytest.raises(ValidationError):
            Category(name="x", kind=bad_kind, profile="general", display="X", base_path="/media/x")


    @pytest.mark.parametrize("bad_profile", ["documentary", "kids", "", "General"])
    def test_profile_enum_violations(bad_profile: str) -> None:
        """Only 'general'/'anime'/'family' (Literal) — D-01/D-02."""
        with pytest.raises(ValidationError):
            Category(name="x", kind="movies", profile=bad_profile, display="X", base_path="/media/x")


    @pytest.mark.parametrize(
        "name,bad_base_path",
        [
            ("x", "/media/y"),
            ("x", "/data/x"),
            ("x", "/media/x/sub"),
            ("series-emilie", "/media/series_emilie"),
        ],
    )
    def test_base_path_invariant_violations(name: str, bad_base_path: str) -> None:
        """D-04: base_path MUST equal /media/{name}."""
        with pytest.raises(ValidationError, match="D-04 strict invariant"):
            Category(name=name, kind="movies", profile="general", display="X", base_path=bad_base_path)


    def test_extra_forbid() -> None:
        """extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            Category(
                name="x",
                kind="movies",
                profile="general",
                display="X",
                base_path="/media/x",
                rogue="field",  # type: ignore[call-arg]
            )


    @pytest.mark.parametrize("missing_field", ["name", "kind", "profile", "display", "base_path"])
    def test_missing_required_field(missing_field: str) -> None:
        """Every field is required (no defaults)."""
        data = {"name": "x", "kind": "movies", "profile": "general", "display": "X", "base_path": "/media/x"}
        del data[missing_field]
        with pytest.raises(ValidationError, match=r"Field required|missing"):
            Category(**data)
    ```

    **Sub-step 2 — regenerate the JSON Schema.** Once Tasks A1 + A2 are complete AND `test_categories.py` is green, run:

    ```bash
    cd tools/arrconf && uv run arrconf schema-gen --output ../../schemas/arrconf-schema.json
    ```

    Commit the regenerated `schemas/arrconf-schema.json` as part of the same commit as A1+A2+A3 (atomicity: schema must match RootConfig at every commit boundary, per D-16 and the existing CI gate at `test_schema_gen.py::test_schema_committed_matches_regen`).

    **Sub-step 3 — verify the gate.** Run `cd tools/arrconf && uv run pytest tests/test_categories.py tests/test_schema_gen.py -x -v` — both files MUST pass.

    Do NOT modify `tools/arrconf/arrconf/schema_gen.py` or `tools/arrconf/tests/test_schema_gen.py`. The existing pipeline + gate already handles the regen correctly (09-RESEARCH.md Q4 verdict: "ALREADY SOLVED").

    After everything is green: `cd tools/arrconf && uv run ruff check tests/test_categories.py && uv run ruff format --check tests/test_categories.py && uv run mypy tests/test_categories.py` MUST exit 0.
  </action>
  <verify>
    <automated>cd tools/arrconf && uv run ruff check tests/test_categories.py && uv run ruff format --check tests/test_categories.py && uv run mypy tests/test_categories.py && uv run pytest tests/test_categories.py tests/test_schema_gen.py -x -v</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tools/arrconf/tests/test_categories.py` exits 0
    - `grep -F 'PRODUCTION_CATEGORIES = [' tools/arrconf/tests/test_categories.py` exits 0
    - `grep -c '"name":' tools/arrconf/tests/test_categories.py` returns at least 10 (the 10 production entries)
    - `grep -F 'def test_production_categories_validate' tools/arrconf/tests/test_categories.py` exits 0
    - `grep -F 'def test_kebab_case_name_violations' tools/arrconf/tests/test_categories.py` exits 0
    - `grep -F 'def test_base_path_invariant_violations' tools/arrconf/tests/test_categories.py` exits 0
    - `grep -F 'D-04 strict invariant' tools/arrconf/tests/test_categories.py` exits 0
    - `cd tools/arrconf && uv run pytest tests/test_categories.py -x` exits 0
    - `cd tools/arrconf && uv run pytest tests/test_schema_gen.py::test_schema_committed_matches_regen -x` exits 0 (regen matches committed file byte-for-byte)
    - `cd tools/arrconf && uv run arrconf schema-gen --output /tmp/regen-schema.json && diff -q schemas/arrconf-schema.json /tmp/regen-schema.json` exits 0
    - `grep -F '"Category"' schemas/arrconf-schema.json` exits 0 (Category type appears in the regenerated schema)
    - `grep -F '"categories"' schemas/arrconf-schema.json` exits 0 (RootConfig.categories field appears)
  </acceptance_criteria>
  <done>
    `test_categories.py` has at least 7 parametric test functions covering happy-path + every invariant violation. `schemas/arrconf-schema.json` is regenerated and committed. The existing D-16 CI gate (`test_schema_gen.py::test_schema_committed_matches_regen`) passes. `ruff check`, `ruff format --check`, `mypy`, and the full `tests/test_categories.py` suite are green.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| YAML file → Python (pydantic load) | `charts/arr-stack/files/arrconf.yml` is operator-edited and committed to git. `categories[].name` flows from operator input through pydantic into Plan B's Helm Job, where it is interpolated into a `mkdir -p` shell command. |
| Python module → JSON Schema → IDE | The generated schema is consumed by VS Code's yaml-language-server for autocomplete. Untrusted operators cannot inject into this surface (the schema is regenerated from in-repo Python code only). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-09A-01 | Tampering | `Category.name` field → Plan B Helm Job `mkdir -p {{ $cat.base_path \| quote }}` | mitigate | Pydantic `Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")` rejects every non-kebab-case input AT YAML LOAD. Path-traversal payloads like `../etc/passwd`, `..`, `foo/bar`, leading/trailing/double hyphens, uppercase, and non-ASCII are all blocked before they reach the Job. The `model_validator(mode="after")` further enforces `base_path == f"/media/{name}"` — no operator-controlled string can land outside `/media/`. |
| T-09A-02 | Tampering | `Category.kind` / `Category.profile` → downstream Phase 10 propagators | mitigate | `Literal["movies", "series"]` and `Literal["general", "anime", "family"]` close the value sets at the type level. Adding a 4th value requires a code change + ADR (explicitly out of scope per REQUIREMENTS.md). |
| T-09A-03 | Repudiation | Schema regen drift | mitigate | Existing CI gate `tests/test_schema_gen.py::test_schema_committed_matches_regen` + `tests.yml` step "Verify schema reproducibility (D-15)" enforce byte-equality. Any drift fails CI with a fix command in the error message. |
| T-09A-04 | Information Disclosure | New `Category` model touches secrets | N/A | The model has no secret fields. `name`, `kind`, `profile`, `display`, `base_path` are all operator-public configuration. |
| T-09A-05 | Denial of Service | Maliciously large `categories[]` list crashes pydantic | accept | Operator-only input via committed YAML; no untrusted ingress. The 10 production entries are static. Pydantic v2 parses thousands of dicts in milliseconds. Realistic bound (< 100 entries) is well within performance budget. |
| T-09A-06 | Elevation of Privilege | New Python module loads code at import | N/A | Pure pydantic; no `eval`, no `exec`, no `subprocess`, no I/O. The module body is dataclass-shaped. |
| T-09A-07 | Spoofing | Schema autocomplete in IDE displays wrong field hints | accept | The schema is regenerated from in-repo Python; spoofing requires malicious commits caught by code review. |

**Zero HIGH-severity unmitigated threats.** The dominant threat is T-09A-01 (Tampering) and it is fully mitigated by the kebab-case regex + base_path invariant — both enforced at the YAML-load boundary, BEFORE Plan B's Helm Job sees any string.
</threat_model>

<verification>
After all 3 tasks complete:

```bash
# Lint + type
cd tools/arrconf && uv run ruff check . && uv run ruff format --check . && uv run mypy arrconf

# Plan A test scope
cd tools/arrconf && uv run pytest tests/test_categories.py tests/test_schema_gen.py tests/test_config.py -x

# Full Python suite (regression guard for sibling code)
cd tools/arrconf && uv run pytest -x --cov --cov-report=term-missing --cov-fail-under=70

# Schema byte-equivalence with fresh regen
cd tools/arrconf && uv run arrconf schema-gen --output /tmp/regen.json && diff -q ../../schemas/arrconf-schema.json /tmp/regen.json
```

All five commands MUST exit 0. If `pytest -x` fails outside Plan A's scope (e.g. a reconciler test broke), the cause is almost certainly the `Category` import collision — verify Edit 1 of Task A2 used `Category as MediaCategory` (Option A) and did NOT rename the qBit import.
</verification>

<success_criteria>
- `RootConfig.categories: list[Category]` field present and defaulting to `[]` (verified by Python one-liner in Task A2 verify).
- `Category` model with `extra='forbid'`, kebab-case `name` regex, Literal enums for `kind` + `profile`, and the `base_path == /media/{name}` `model_validator(mode='after')` (verified by Task A1 grep + Task A3 pytest).
- 10 production category dicts from 09-CONTEXT.md §Specifics each parse cleanly through `Category(**d)` (Task A3 `test_production_categories_validate`).
- `schemas/arrconf-schema.json` regenerated and committed; `test_schema_gen.py::test_schema_committed_matches_regen` green (existing D-16 gate).
- Full Python test suite green (no regression in `test_config.py`, `test_dump.py`, `test_reconcilers_*` — D-13 boundary preserved).
- `ruff check`, `ruff format --check`, `mypy` all green on every modified file.
</success_criteria>

<output>
After completion, create `.planning/phases/09-categories-data-model-chart-initcontainer/09-A-python-schema-SUMMARY.md` with the standard summary template covering:
- Tasks executed (A1/A2/A3) with file diffs
- D-NN coverage table (D-01, D-02, D-04, D-05, D-13, D-16)
- Test results (pytest output snippets)
- Schema regen evidence (diff -q exit code, schemas/arrconf-schema.json line count delta)
- Any deviations from the planned `Category as MediaCategory` import strategy (there should be none)
- Pointer to Plan C (which depends on this plan's `Category` model being importable)
</output>
