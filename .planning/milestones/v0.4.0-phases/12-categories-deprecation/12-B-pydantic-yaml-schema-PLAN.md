---
phase: 12-categories-deprecation
plan: B
type: execute
wave: 2
depends_on: [A]
files_modified:
  - tools/arrconf/arrconf/config.py
  - tools/arrconf/arrconf/diff_cmd.py
  - tools/arrconf/arrconf/__main__.py
  - tools/arrconf/tests/test_config_validation.py
  - charts/arr-stack/files/arrconf.yml
  - schemas/arrconf-schema.json
autonomous: true
requirements:
  - REQ-categories-deprecation
mode: standard

must_haves:
  truths:
    - "`items: list[...]` field removed from the 6 generator-fed Section models in `config.py` (D-01)"
    - "`prune: bool` kept on every Section model (D-02)"
    - "Flat `items:` lists deleted from `charts/arr-stack/files/arrconf.yml` for the **11** generator-derived resources (D-01 + REQ-categories-deprecation). Note: CONTEXT Phase Boundary §2 says '12' but enumerates 11 — the enumeration is authoritative; 11 generator-derived YAML blocks are slimmed in this plan, not 12."
    - "`schemas/arrconf-schema.json` regenerated and committed; matches `arrconf schema-gen` output byte-for-byte (D-05)"
    - "`arrconf apply --config charts/arr-stack/files/arrconf.yml --dry-run` loads the new YAML without ValidationError (D-13 — pydantic `extra=forbid` confirms the new shape is valid)"
    - "New unit test `tests/test_config_validation.py::test_load_config_rejects_legacy_items_field` exercises the D-13 failure path: a YAML fragment with `sonarr.main.tags.items` MUST raise `ValidationError` with `type='extra_forbidden'`. The captured error string is the **same text** quoted verbatim in Plan D Task D.1's CLAUDE.md edit (cross-reference)."
    - "The Plan-A intra-function shim (`instance.<section>.items = derived.<field>`) is removed from `__main__.py` diff branches and `diff_cmd.py` is refactored to accept Derived dataclasses (continuation of D-03)"
  artifacts:
    - path: "tools/arrconf/arrconf/config.py"
      provides: "6 Section models without items field"
      excludes: "items: list[TagItem]|items: list[RootFolder]|items: list[DownloadClient]|items: list[RemotePathMapping]|items: list[Category]|items: list[JellyfinLibrary]"
    - path: "charts/arr-stack/files/arrconf.yml"
      provides: "Categories-driven shape — no flat items lists for 11 generator-derived resources"
    - path: "schemas/arrconf-schema.json"
      provides: "JSON Schema reflecting post-deprecation shape; matches a fresh schema-gen"
    - path: "tools/arrconf/arrconf/diff_cmd.py"
      provides: "diff_sonarr/diff_radarr/diff_qbittorrent/diff_jellyfin take Derived params"
    - path: "tools/arrconf/tests/test_config_validation.py"
      provides: "D-13 enforcement test — captures the canonical ValidationError text for CLAUDE.md docs reuse"
      contains: "test_load_config_rejects_legacy_items_field"
  key_links:
    - from: "charts/arr-stack/files/arrconf.yml"
      to: "tools/arrconf/arrconf/config.py RootConfig"
      via: "pydantic strict-load via load_config()"
      pattern: "RootConfig.model_validate"
    - from: "tools/arrconf/arrconf/config.py"
      to: "schemas/arrconf-schema.json"
      via: "arrconf schema-gen"
      pattern: "schema-gen"
    - from: "tools/arrconf/tests/test_config_validation.py::test_load_config_rejects_legacy_items_field"
      to: "CLAUDE.md ## v0.3.0 → v0.4.0 deprecation section (Plan D Task D.1)"
      via: "Plan D executor copies the captured error string verbatim from pytest -v output into the CLAUDE.md doc block"
      pattern: "extra_forbidden"
---

<objective>
Remove the `items` field from the 6 generator-fed pydantic Section models, delete the 11 corresponding flat YAML blocks from production `arrconf.yml`, regenerate the JSON Schema to match, refactor `diff_cmd.py` to accept the Derived dataclasses (so the temporary Plan-A shim in `__main__.py` diff branches can be removed), and add a unit test that exercises the D-13 failure path (legacy `items:` block raises `ValidationError`).

Purpose: After Plan B, the YAML is shape-locked to Categories-only. The `extra="forbid"` invariant turns any leftover `items:` block into a hard ValidationError at load time (D-13) — and the new unit test pins the canonical error string so Plan D's CLAUDE.md doc can quote it verbatim instead of hand-waving prose. The schema lives as the immutable source-of-truth for `# yaml-language-server: $schema=` directives.

Output: `config.py` slimmer by 6 `items` fields; `arrconf.yml` shorter (every Categories-derived flat block deleted); `schemas/arrconf-schema.json` regenerated and committed; `diff_cmd.py` entry-point signatures aligned with the reconciler signatures from Plan A; new `tests/test_config_validation.py` with the D-13 dispositive test.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/phases/12-categories-deprecation/12-CONTEXT.md
@CLAUDE.md
@tools/arrconf/arrconf/config.py
@tools/arrconf/arrconf/__main__.py
@tools/arrconf/arrconf/diff_cmd.py
@tools/arrconf/arrconf/schema_gen.py
@charts/arr-stack/files/arrconf.yml
@schemas/arrconf-schema.json
@.planning/phases/12-categories-deprecation/12-A-reconciler-refactor-PLAN.md
@.planning/phases/12-categories-deprecation/12-A-reconciler-refactor-SUMMARY.md

<interfaces>
<!-- Section models BEFORE deprecation (from config.py current state) — verify before editing -->

```python
# Models to slim (remove `items` field, keep `prune`)
class TagsSection(BaseModel):
    prune: bool
    items: list[TagItem]    # DELETE this line

class RootFoldersSection(BaseModel):
    prune: bool
    items: list[RootFolder]    # DELETE this line

class DownloadClientsSection(BaseModel):
    prune: bool
    items: list[DownloadClient]    # DELETE this line

class RemotePathMappingsSection(BaseModel):
    prune: bool
    items: list[RemotePathMapping]    # DELETE this line

class CategoriesSection(BaseModel):  # qBittorrent
    prune: bool
    items: list[Category]    # DELETE this line

class JellyfinLibrariesSection(BaseModel):
    enable: bool
    prune: bool
    items: list[JellyfinLibrary]    # DELETE this line

# Models NOT touched (still carry items because they hold operator-edited resources, NOT generator-derived):
# - IndexersSection (operator declares indexer routing)
# - NotificationsSection (operator declares notifications)
# - AppsSection (Prowlarr — operator declares which Sonarr/Radarr instances Prowlarr should sync to)
# - ContentRoutingSection (genre-keyword rules — operator-managed)
# - SeriesTagsSection / MovieTagsSection (already itemless; carry enable + default_tag)
# - HostConfigSection / PreferencesSection / JellyfinUsersSection / JellyfinServerConfigSection /
#   JellyfinPluginsSection / SeerrSonarrServiceSection / SeerrRadarrServiceSection /
#   SeerrUsersSection / SeerrMainSettingsSection (no items field already)
```

<!-- YAML flat sections to delete from charts/arr-stack/files/arrconf.yml (verbatim section paths) -->

Sections to delete (the `items:` list under each — the parent Section dict survives with just `prune: false`). **Authoritative count = 11**, NOT 12 (CONTEXT Phase Boundary §2 inflates by one when introducing the topic but enumerates 11 in the same paragraph). The enumeration below is canonical:

1. `sonarr.main.tags.items`
2. `sonarr.main.root_folders.items`
3. `sonarr.main.download_clients.items`
4. `sonarr.main.remote_path_mappings.items`
5. `radarr.main.tags.items`
6. `radarr.main.root_folders.items`
7. `radarr.main.download_clients.items`
8. `radarr.main.remote_path_mappings.items`
9. `qbittorrent.main.categories.items`
10. `seerr.main.sonarr_service.animeTags` (the list itself — animeTags is a `list[int]` on `SeerrSonarrServiceSection`, NOT an `items:` list)
11. `jellyfin.main.libraries.items`

Verify post-edit via grep that no `items:` block remains under generator-derived sections.

<!-- Sections to KEEP in arrconf.yml (operator-owned, generator does NOT produce these): -->

- `sonarr.main.indexers.items` (operator-owned)
- `sonarr.main.notifications.items` (operator-owned)
- `radarr.main.indexers.items` (operator-owned)
- `radarr.main.notifications.items` (operator-owned)
- `prowlarr.main.apps.items` (Prowlarr app-sync — operator-owned)
- `jellyfin.main.plugins.required` (NOT named `items` — different field name, but lives on PluginsSection; operator-owned)
- `seerr.main.sonarr_service.tags` (non-anime routing — operator-owned single-list `list[int]`)
- `seerr.main.radarr_service.tags` (operator-owned)

<!-- diff_cmd.py entry-point signatures to refactor (after Plan A, these still rely on the Plan-A shim — Plan B removes the shim by passing Derived through diff_cmd) -->

```python
# diff_cmd.py — POST-Plan-B signatures
def diff_sonarr(client: SonarrClient, root: RootConfig, derived: SonarrDerived) -> int: ...
def diff_radarr(client: RadarrClient, root: RootConfig, derived: RadarrDerived) -> int: ...
def diff_qbittorrent(client: QbittorrentClient, root: RootConfig, categories: list[Category]) -> int: ...
def diff_jellyfin(client: JellyfinClient, root: RootConfig, libraries: list[JellyfinLibrary]) -> int: ...
def diff_prowlarr(client: ProwlarrClient, root: RootConfig) -> int:   # UNCHANGED — no Categories derivation
```

<!-- D-13 unit test contract (new file: tools/arrconf/tests/test_config_validation.py) -->

```python
# tools/arrconf/tests/test_config_validation.py — NEW FILE in Plan B
"""D-13 dispositive: confirms `extra="forbid"` on Section models rejects legacy
v0.3.0 YAML shape (flat `*.items` blocks under generator-fed sections).

The exact error string captured by this test is the **canonical** sample
quoted verbatim in CLAUDE.md's `## v0.3.0 → v0.4.0 deprecation` section
(Plan D Task D.1). Do not edit the test's assertions without updating
the doc — they are intentionally coupled.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from arrconf.config import RootConfig  # or whichever top-level model load_config() uses


def test_load_config_rejects_legacy_items_field() -> None:
    """A YAML fragment with legacy sonarr.main.tags.items must raise
    ValidationError(type='extra_forbidden') after Plan B removes the items field.

    The plan's executor MUST capture the exc.errors() output and paste it
    into CLAUDE.md's deprecation section verbatim (see Plan D Task D.1)."""

    # Minimal RootConfig fixture: keep required scaffolding small but valid,
    # except for the one offending field. The exact shape depends on
    # RootConfig's required-fields tree — executor inspects load_config()
    # to determine the minimal valid surrounding dict, then injects the
    # offending key under sonarr.main.tags.items.
    legacy_shape = {
        # ... minimal-valid scaffolding produced by inspecting RootConfig ...
        "sonarr": {
            "main": {
                # ... required SonarrInstance scaffolding ...
                "tags": {
                    "prune": False,
                    "items": [{"label": "tv"}],   # ← D-13 trigger: legacy v0.3.0 field
                },
            }
        },
    }

    with pytest.raises(ValidationError) as exc_info:
        RootConfig.model_validate(legacy_shape)

    # At least one error in the chain must be extra_forbidden on the items field
    errors = exc_info.value.errors()
    extra_forbidden = [e for e in errors if e["type"] == "extra_forbidden"]
    assert extra_forbidden, f"expected extra_forbidden error, got: {errors}"

    # The error's location must point at the items field — anchors the CLAUDE.md
    # "field-path resolution" claim.
    paths = [tuple(e["loc"]) for e in extra_forbidden]
    assert any("items" in p for p in paths), f"items not in any error loc: {paths}"
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task B.1: Slim pydantic Section models — remove `items` field from 6 generator-fed Sections</name>
  <files>tools/arrconf/arrconf/config.py</files>
  <read_first>
    - tools/arrconf/arrconf/config.py (full file — Sections to modify are: TagsSection L134-142, RootFoldersSection L74-83, DownloadClientsSection L47-55, RemotePathMappingsSection L145-157, CategoriesSection L236-249, JellyfinLibrariesSection L529-552)
    - tools/arrconf/arrconf/generators/categories.py (to confirm which resource types the generators emit — these are exactly the resource types whose Section models lose `items`)
    - .planning/phases/12-categories-deprecation/12-A-reconciler-refactor-SUMMARY.md (verify Plan A landed and reconcilers no longer depend on `instance.<section>.items` after the intra-function shim is removed)
  </read_first>
  <action>
    Edit `tools/arrconf/arrconf/config.py`. For each of the 6 models listed in `<interfaces>`, delete the `items: list[...] = Field(default_factory=list)` line (or its multi-line equivalent for JellyfinLibrariesSection which has a longer description). Keep `prune: bool = Field(default=False, ...)`. Keep `model_config = ConfigDict(extra="forbid")` (verified: every Section already has `ConfigDict(extra="forbid")` — this is the D-13 trust gate). Keep any other field that is NOT `items` (e.g. JellyfinLibrariesSection's `enable: bool` survives).

    Concretely, the 6 lines/blocks to delete:

    ```python
    # DownloadClientsSection (around line 55)
    items: list[DownloadClient] = Field(default_factory=list)

    # IndexersSection — DO NOT TOUCH (operator-owned, not generator-derived)

    # NotificationsSection — DO NOT TOUCH (operator-owned)

    # RootFoldersSection (around line 83)
    items: list[RootFolder] = Field(default_factory=list)

    # TagsSection (around line 142)
    items: list[TagItem] = Field(default_factory=list)

    # RemotePathMappingsSection (around line 157)
    items: list[RemotePathMapping] = Field(default_factory=list)

    # CategoriesSection (around line 249)
    items: list[Category] = Field(default_factory=list)

    # JellyfinLibrariesSection (around lines 546-552, multi-line)
    items: list[JellyfinLibrary] = Field(
        default_factory=list,
        description=(...),
    )
    ```

    Also clean up imports that become unused: at the top of `config.py`, imports that are now ONLY referenced by the deleted `items` field annotations will become unused. After editing the models, check:
    - `from arrconf.resources.qbittorrent.category import Category` — still used by `CategoriesSection` reference? The annotation is gone; `Category` may now be unused. If `grep -c "Category" tools/arrconf/arrconf/config.py` returns 1 (just the import line), delete the import.
    - `from arrconf.resources.sonarr.download_client import DownloadClient` — same check. May still be referenced by `SeerrSonarrServiceSection` etc. — grep first.
    - Similar for `RemotePathMapping`, `RootFolder`, `JellyfinLibrary` (the type is still used in the generator dataclass, but not necessarily in config.py).
    Only delete imports that become genuinely unused; ruff will flag them on the Triade run.
  </action>
  <verify>
    <automated>
      cd /data/projets/perso/arr-stack && \
      python3 -c "
import re, sys
src = open('tools/arrconf/arrconf/config.py').read()
banned = ['items: list[TagItem]', 'items: list[RootFolder]', 'items: list[DownloadClient]', 'items: list[RemotePathMapping]', 'items: list[Category]', 'items: list[JellyfinLibrary]']
fail = [b for b in banned if b in src]
if fail:
    print('STILL PRESENT:', fail); sys.exit(1)
# Confirm prune: bool survives on all 6 sections
required = ['class TagsSection', 'class RootFoldersSection', 'class DownloadClientsSection', 'class RemotePathMappingsSection', 'class CategoriesSection', 'class JellyfinLibrariesSection']
for r in required:
    if r not in src:
        print('MISSING CLASS:', r); sys.exit(2)
print('OK')
" && \
      cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy . && echo "TRIADE OK"
    </automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "items: list\[TagItem\]" tools/arrconf/arrconf/config.py` exits 1 (no match)
    - `grep -q "items: list\[RootFolder\]" tools/arrconf/arrconf/config.py` exits 1
    - `grep -q "items: list\[DownloadClient\]" tools/arrconf/arrconf/config.py` exits 1
    - `grep -q "items: list\[RemotePathMapping\]" tools/arrconf/arrconf/config.py` exits 1
    - `grep -q "items: list\[Category\]" tools/arrconf/arrconf/config.py` exits 1
    - `grep -q "items: list\[JellyfinLibrary\]" tools/arrconf/arrconf/config.py` exits 1
    - `grep -c "^class TagsSection\|^class RootFoldersSection\|^class DownloadClientsSection\|^class RemotePathMappingsSection\|^class CategoriesSection\|^class JellyfinLibrariesSection" tools/arrconf/arrconf/config.py` returns 6
    - `grep -c "prune: bool" tools/arrconf/arrconf/config.py` returns at least 9 (operator-owned sections also have prune — see IndexersSection, NotificationsSection, AppsSection, SeerrUsersSection)
    - `cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy .` exits 0
  </acceptance_criteria>
  <done>6 generator-fed Section models no longer carry an `items` field; `prune: bool` survives on each; Triade Python green; pydantic still loads (no runtime regression).</done>
</task>

<task type="auto">
  <name>Task B.2: Add D-13 dispositive unit test — `test_load_config_rejects_legacy_items_field`</name>
  <files>tools/arrconf/tests/test_config_validation.py</files>
  <read_first>
    - tools/arrconf/arrconf/config.py (post-Task-B.1 — confirm the 6 Section models no longer carry `items` AND `ConfigDict(extra="forbid")` is still in place on each)
    - tools/arrconf/arrconf/config.py — locate `load_config()` or `RootConfig.model_validate()` entry point + inspect `RootConfig`'s required-fields tree to determine the minimal valid scaffolding for the YAML fragment in the test
    - tools/arrconf/tests/conftest.py (existing fixtures — reuse if a minimal-valid root config fixture exists; otherwise build inline)
  </read_first>
  <action>
    Create the new file `tools/arrconf/tests/test_config_validation.py` using the template in `<interfaces>` above as the skeleton. The minimal-valid YAML scaffolding must be inferred from `RootConfig`'s required fields (look for `Field(...)` without `default` or `default_factory`).

    Steps:
    1. Read `tools/arrconf/arrconf/config.py` to identify all required (no-default) fields on `RootConfig` and its required sub-models.
    2. Build a minimal-valid `dict[str, Any]` that satisfies those required fields.
    3. Inject the offending key `sonarr.main.tags.items = [{"label": "tv"}]` — this triggers the D-13 enforcement because Plan B's Task B.1 removed `items` from `TagsSection`.
    4. Use `pytest.raises(ValidationError)` to capture the exception.
    5. Assert at least one error has `type == "extra_forbidden"` and the error's `loc` contains `"items"`.
    6. After implementing the test, run it locally and copy the EXACT output of `cd tools/arrconf && uv run pytest tests/test_config_validation.py::test_load_config_rejects_legacy_items_field -v 2>&1 | head -40` — paste this output into the SUMMARY of Plan B (the SUMMARY is consumed by Plan D Task D.1 which copies the error block verbatim into CLAUDE.md, so the SUMMARY's "captured ValidationError output" section is the cross-plan handoff).

    **If the minimal-valid scaffolding is non-trivial** (RootConfig has many required sub-models), the alternative is to load `charts/arr-stack/files/arrconf.yml` directly via `load_config()` and inject the offending key only into the loaded dict — but `arrconf.yml` is itself post-Plan-B-edited by Task B.3, creating a chicken-and-egg ordering issue if this test runs in CI before B.3 lands. **Mitigation:** keep the test inline-scaffolded (no file dependency), so test ordering inside this plan is irrelevant.

    No edits to other files in this task.
  </action>
  <verify>
    <automated>
      cd /data/projets/perso/arr-stack && \
      test -f tools/arrconf/tests/test_config_validation.py && \
      cd tools/arrconf && uv run pytest tests/test_config_validation.py::test_load_config_rejects_legacy_items_field -v && echo "D-13 TEST GREEN" ; \
      uv run ruff format --check tests/test_config_validation.py && uv run ruff check tests/test_config_validation.py && uv run mypy tests/test_config_validation.py && echo "TRIADE OK"
    </automated>
  </verify>
  <acceptance_criteria>
    - `test -f tools/arrconf/tests/test_config_validation.py` exits 0 (file exists)
    - `grep -q "def test_load_config_rejects_legacy_items_field" tools/arrconf/tests/test_config_validation.py` exits 0
    - `grep -q "extra_forbidden" tools/arrconf/tests/test_config_validation.py` exits 0
    - `cd tools/arrconf && uv run pytest tests/test_config_validation.py::test_load_config_rejects_legacy_items_field -v` exits 0
    - Triade Python on the new file: `cd tools/arrconf && uv run ruff format --check tests/test_config_validation.py && uv run ruff check tests/test_config_validation.py && uv run mypy tests/test_config_validation.py` exits 0
    - The captured pytest -v output is recorded in `12-B-pydantic-yaml-schema-SUMMARY.md` under a `## Captured D-13 ValidationError` heading (for Plan D Task D.1 to consume verbatim)
  </acceptance_criteria>
  <done>D-13 enforcement now has a single dispositive test; the test passes; the captured error string is committed in the plan's SUMMARY for Plan D's CLAUDE.md edit to reference verbatim.</done>
</task>

<task type="auto">
  <name>Task B.3: Delete flat YAML sections from arrconf.yml + regenerate schema + refactor diff_cmd.py + remove Plan-A shim</name>
  <files>
    charts/arr-stack/files/arrconf.yml,
    schemas/arrconf-schema.json,
    tools/arrconf/arrconf/diff_cmd.py,
    tools/arrconf/arrconf/__main__.py
  </files>
  <read_first>
    - charts/arr-stack/files/arrconf.yml (full file — ~592 lines; locate each section listed in `<interfaces>` and delete only the `items:` sub-block, keep the parent block with `prune: false`)
    - tools/arrconf/arrconf/diff_cmd.py (full file — to refactor diff_* entry points)
    - tools/arrconf/arrconf/__main__.py (full file post-Plan-A — to remove the diff-branch Plan-A shim once diff_cmd accepts Derived params)
    - tools/arrconf/arrconf/schema_gen.py (the schema export function — confirm `write_schema` writes from `RootConfig.model_json_schema()`)
    - .github/workflows/tests.yml (lines 50-57 — schema-drift CI check already exists; the CI re-runs `arrconf schema-gen` and `git diff --exit-code` on the schema, so our regen must be reproducible)
  </read_first>
  <action>
    Four file operations:

    **(1) `charts/arr-stack/files/arrconf.yml` — delete 11 flat blocks:**

    For each of the 11 sections enumerated in `<interfaces>`, remove the `items:` key and its list contents. The parent dict block (e.g. `tags:`, `root_folders:`) MUST survive with `prune: false` retained. Example transformation:

    BEFORE (lines 58-63):
    ```yaml
        tags:
          prune: false
          items:
            - label: tv
            - label: anime
            - label: family
    ```
    AFTER:
    ```yaml
        tags:
          prune: false
    ```

    For `seerr.main.sonarr_service.animeTags` — it's not under `items:` but is a top-level `list[int]` on the section. Delete the line `animeTags: [...]` from the YAML. Keep `tags: [...]` (operator-owned non-anime routing).

    For `jellyfin.main.libraries`, the section also has `enable: true` and `prune: false` — keep both, delete only the `items:` block.

    Be DOUBLY careful NOT to delete operator-owned blocks:
    - KEEP `sonarr.main.indexers.items` (indexer list)
    - KEEP `sonarr.main.notifications.items`
    - KEEP `radarr.main.indexers.items`
    - KEEP `radarr.main.notifications.items`
    - KEEP `prowlarr.main.apps.items`
    - KEEP `jellyfin.main.plugins.required` (plugins are activation-only, operator declares which to enable)
    - KEEP `seerr.main.sonarr_service.tags` (non-anime routing — operator-owned)
    - KEEP `seerr.main.radarr_service.tags`

    After edits, run `cd tools/arrconf && uv run arrconf apply --config ../../charts/arr-stack/files/arrconf.yml --dry-run --apps sonarr 2>&1 | head -5` and confirm no `ValidationError` appears. (This tests pydantic load; the actual reconcile call will fail later in the chain due to missing API key — that's fine, we're checking that config validation passes.)

    **(2) Regenerate `schemas/arrconf-schema.json`:**

    ```bash
    cd /data/projets/perso/arr-stack && cd tools/arrconf && uv run arrconf schema-gen --output ../../schemas/arrconf-schema.json
    ```

    Then verify reproducibility (mirrors CI):
    ```bash
    cd tools/arrconf && uv run arrconf schema-gen --output /tmp/regen-schema.json && diff /data/projets/perso/arr-stack/schemas/arrconf-schema.json /tmp/regen-schema.json
    ```
    (Exit 0 → deterministic.)

    Confirm the regenerated schema NO LONGER references `items` arrays for the 6 deprecated sections (search for the dotted path or the BaseModel name in `$defs`). The schema MUST still reference `items` for IndexersSection / NotificationsSection / AppsSection (operator-owned).

    **(3) Refactor `tools/arrconf/arrconf/diff_cmd.py` to accept Derived params:**

    Read `diff_cmd.py` first to confirm signature shape, then update:
    - `def diff_sonarr(client, root)` → `def diff_sonarr(client, root, derived: SonarrDerived)`. Inside, replace every read of `instance.tags.items`, `instance.root_folders.items`, `instance.download_clients.items`, `instance.remote_path_mappings.items` with `derived.tags`, etc. — OR apply the same intra-function shim as Plan A (`instance.tags.items = derived.tags` at top of function body). The shim approach is preferred to minimise diff against the existing differ.py callers.

    **CRITICAL EDGE CASE:** After Plan B deletes the `items` field from the pydantic models, assigning `instance.tags.items = derived.tags` will raise `ValueError: "TagsSection" object has no field "items"` because `extra="forbid"` blocks dynamic attribute assignment. The fix: inside `diff_sonarr` (and the reconciler entry points refactored in Plan A), replace the shim with direct local-variable use instead:

    ```python
    # diff_cmd.py::diff_sonarr — POST-Plan-B body shape
    def diff_sonarr(client: SonarrClient, root: RootConfig, derived: SonarrDerived) -> int:
        instance = root.sonarr["main"]
        # Use derived directly — NOT instance.tags.items (field removed in Plan B)
        tags_desired = derived.tags
        root_folders_desired = derived.root_folders
        download_clients_desired = derived.download_clients
        rpm_desired = derived.remote_path_mappings
        # ... existing diff logic, but pass the local names into the internal helpers ...
    ```

    **The same applies to the Plan-A reconciler entry-point shim:** when Plan B lands, the executor MUST audit reconciler files (sonarr.py / radarr.py / qbittorrent.py / jellyfin.py / seerr.py) and replace the Plan-A shim assignment with local-variable use. The pattern:

    Plan-A shim (to be removed):
    ```python
    def reconcile_sonarr(client, instance, derived: SonarrDerived, *, dry_run):
        instance.tags.items = derived.tags  # ← Plan-A shim — REMOVE
        ...
    ```
    Plan-B replacement (direct use of derived in internal helper calls):
    ```python
    def reconcile_sonarr(client, instance, derived: SonarrDerived, *, dry_run):
        # No shim — use derived.<field> at the call sites of internal helpers
        ...
        _reconcile_tags(client, derived.tags, instance.tags.prune, ...)  # was: instance.tags.items
        ...
    ```

    The internal helpers (`_reconcile_tags`, `_reconcile_list_resource`, etc.) already accept the items as parameters — only the lookup in the entry point changes.

    **(4) Remove the Plan-A diff-branch shim from `__main__.py`:**

    In the diff branches in `__main__.py` (sonarr/radarr/qbit/jellyfin/seerr), the Plan-A shim (`instance.tags.items = derived.tags`) becomes illegal once Plan B removes the `.items` field. Replace each shim with a pass of the Derived dataclass into the new `diff_*` entry point:

    Sonarr diff branch:
    ```python
    sonarr_diff_derived = generate_sonarr_resources(root)
    # No shim — diff_sonarr now takes derived as 3rd arg
    code = diff_sonarr(client, root, sonarr_diff_derived)
    ```
    (Same pattern for radarr/qbit/jellyfin diff branches.)

    Seerr diff branch: `seerr_diff_instance.sonarr_service.animeTags = diff_resolved_anime_ids` is also illegal once Plan B removes `animeTags` — BUT `animeTags` is a field on `SeerrSonarrServiceSection`, NOT an `items` list. **Audit this:** does Plan B delete `animeTags` from `SeerrSonarrServiceSection`? Looking at CONTEXT D-01 + D-13, the YAML field `seerr.main.sonarr_service.animeTags` is deleted, but the pydantic field `SeerrSonarrServiceSection.animeTags` MUST remain (the reconciler still needs the resolved list[int] to call Seerr's API). So `SeerrSonarrServiceSection.animeTags` stays as `list[int]` with `default_factory=list` — only its appearance in the YAML is deleted. The Plan-A shim `seerr_diff_instance.sonarr_service.animeTags = diff_resolved_anime_ids` therefore remains LEGAL — but the cleaner refactor is to pass `diff_resolved_anime_ids` directly into `diff_seerr` if it exists (currently it does not — Seerr diff is deferred per `diff_not_implemented` log line). For Plan B, just remove the shim assignment in the seerr diff branch and add a comment noting that Plan-A's resolved_anime_ids is unused until diff_seerr exists.

    Per CLAUDE.md Triade Python pre-commit:
    ```bash
    cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy .
    ```
  </action>
  <verify>
    <automated>
      cd /data/projets/perso/arr-stack && \
      ! yq '.sonarr.main.tags.items' charts/arr-stack/files/arrconf.yml | grep -qE '^\s*-' ; \
      ! yq '.sonarr.main.root_folders.items' charts/arr-stack/files/arrconf.yml | grep -qE '^\s*-' ; \
      ! yq '.sonarr.main.download_clients.items' charts/arr-stack/files/arrconf.yml | grep -qE '^\s*-' ; \
      ! yq '.sonarr.main.remote_path_mappings.items' charts/arr-stack/files/arrconf.yml | grep -qE '^\s*-' ; \
      ! yq '.radarr.main.tags.items' charts/arr-stack/files/arrconf.yml | grep -qE '^\s*-' ; \
      ! yq '.radarr.main.root_folders.items' charts/arr-stack/files/arrconf.yml | grep -qE '^\s*-' ; \
      ! yq '.radarr.main.download_clients.items' charts/arr-stack/files/arrconf.yml | grep -qE '^\s*-' ; \
      ! yq '.radarr.main.remote_path_mappings.items' charts/arr-stack/files/arrconf.yml | grep -qE '^\s*-' ; \
      ! yq '.qbittorrent.main.categories.items' charts/arr-stack/files/arrconf.yml | grep -qE '^\s*-' ; \
      ! yq '.seerr.main.sonarr_service.animeTags' charts/arr-stack/files/arrconf.yml | grep -qE '^\s*-' ; \
      ! yq '.jellyfin.main.libraries.items' charts/arr-stack/files/arrconf.yml | grep -qE '^\s*-' ; \
      yq '.sonarr.main.indexers.items | length' charts/arr-stack/files/arrconf.yml | grep -qE '^[1-9]' ; \
      yq '.prowlarr.main.apps.items | length' charts/arr-stack/files/arrconf.yml | grep -qE '^[1-9]' ; \
      cd tools/arrconf && uv run arrconf schema-gen --output /tmp/12B-regen.json && diff -q /data/projets/perso/arr-stack/schemas/arrconf-schema.json /tmp/12B-regen.json && \
      cd /data/projets/perso/arr-stack && \
      cd tools/arrconf && uv run python -c "from arrconf.config import load_config; from pathlib import Path; root = load_config(Path('/data/projets/perso/arr-stack/charts/arr-stack/files/arrconf.yml')); assert len(root.categories) == 10, f'categories count: {len(root.categories)}'; print('LOAD OK')" && \
      uv run ruff format --check . && uv run ruff check . && uv run mypy . && echo "TRIADE OK"
    </automated>
  </verify>
  <acceptance_criteria>
    - For each of the 11 deleted-section YAML paths in `<interfaces>`: `yq '<path>' charts/arr-stack/files/arrconf.yml` returns `null` or empty (no list items)
    - `yq '.sonarr.main.indexers.items | length' charts/arr-stack/files/arrconf.yml` returns a number ≥ 1 (operator-owned section survives)
    - `yq '.prowlarr.main.apps.items | length' charts/arr-stack/files/arrconf.yml` returns a number ≥ 1
    - `yq '.sonarr.main.tags.prune' charts/arr-stack/files/arrconf.yml` returns `false` (prune key survives even with items gone)
    - `cd tools/arrconf && uv run arrconf schema-gen --output /tmp/regen.json && diff schemas/arrconf-schema.json /tmp/regen.json` exits 0 (schema reproducible per CI line 56)
    - `grep -q '"items"' schemas/arrconf-schema.json | head -5` still has matches (operator-owned Section models retain items)
    - The python `load_config()` call in `<verify>` prints `LOAD OK` (10 categories — confirms YAML still loads under the new shape)
    - `grep -c "instance.tags.items = " tools/arrconf/arrconf/__main__.py` returns 0 (Plan-A shim removed)
    - `grep -q "def diff_sonarr.*derived: SonarrDerived" tools/arrconf/arrconf/diff_cmd.py` exits 0
    - Triade Python green: `cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy .` exits 0
  </acceptance_criteria>
  <done>YAML stripped of 11 generator-derived flat blocks; pydantic confirms the new shape loads cleanly; schema regenerated and CI-reproducible; diff_cmd.py and reconciler internals no longer touch `.items` on Section models that no longer have it; Triade Python green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| YAML → pydantic load_config | Schema validation hardens; old YAML with `items:` now hits `ValidationError` (D-13 enforcement) |
| schemas/arrconf-schema.json → yaml-language-server | Operator editor consumes the schema for in-editor validation. Stale schema = false-positive editor errors. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-12B-01 | Tampering | arrconf.yml editor flow | mitigate | `extra="forbid"` on Section models rejects unknown fields; old-shape YAML cannot silently survive (D-13). The new `test_load_config_rejects_legacy_items_field` test pins the contract. |
| T-12B-02 | Information Disclosure | schema regen | accept | JSON Schema contains no secrets; output goes to public path `schemas/arrconf-schema.json` already committed. |
| T-12B-03 | Denial of Service | apply path on operator's legacy fork | mitigate | Clear ValidationError points at the dead field path; CLAUDE.md deprecation section (Plan D) gives the fix command. The error text quoted in CLAUDE.md is the literal output of the D-13 unit test (captured during Plan B execution, copied verbatim into the doc). |
| T-12B-04 | Spoofing | None applicable | n/a | YAML edits land via PR review; chart pull from GHCR uses anonymous read (ADR-3) — no impersonation vector introduced. |
| T-12B-05 | Repudiation | schema regen reproducibility | mitigate | CI `tests.yml:54-57` already enforces `git diff --exit-code` against a fresh `arrconf schema-gen` — non-reproducible schema fails CI. |
</threat_model>

<verification>
- `cd tools/arrconf && uv run pytest tests/ -k "not (sweep_manual_override_path or per_resource_override_tags_only or per_resource_override_rpm_only or manual_override_wins or animetags_merge_manual_wins or animetags_merge_empty_manual_uses_generated)" --tb=short -x` exits 0
- `cd tools/arrconf && uv run pytest tests/test_config_validation.py::test_load_config_rejects_legacy_items_field -v` exits 0 (D-13 dispositive)
- `cd tools/arrconf && uv run arrconf apply --config /data/projets/perso/arr-stack/charts/arr-stack/files/arrconf.yml --dry-run 2>&1 | tail -20` shows NO `ValidationError` (may show `missing_api_key` exit 2 — that's fine, it confirms YAML validation passed)
- `cd tools/arrconf && uv run arrconf schema-gen --output /tmp/regen.json && diff schemas/arrconf-schema.json /tmp/regen.json` exits 0
</verification>

<success_criteria>
- SC#2 (flat sections deleted; schema regen confirms simplified shape) — SATISFIED.
- SC#5 (dry-run plan_action shape unchanged) — structurally enabled; Plan E validates against live cluster.
- D-01, D-02, D-05, D-13 all closed in this plan (D-13 closure includes the unit-test enforcement, not just the runtime behaviour).
</success_criteria>

<output>
After completion, create `.planning/phases/12-categories-deprecation/12-B-pydantic-yaml-schema-SUMMARY.md` documenting:
- Per-section confirmation that `items` was deleted from the 6 generator-fed Section models
- The pre/post line counts of `charts/arr-stack/files/arrconf.yml` (expected: ~592 → ~400 lines)
- Schema regen byte-diff (must be `diff schemas/arrconf-schema.json /tmp/regen.json` exit 0)
- Confirmation that `diff_cmd.py` signature now matches Plan A's reconciler signatures
- **A `## Captured D-13 ValidationError` section** with the verbatim output of `cd tools/arrconf && uv run pytest tests/test_config_validation.py::test_load_config_rejects_legacy_items_field -v 2>&1 | head -40` — this is the canonical error string Plan D Task D.1 quotes verbatim in CLAUDE.md (do NOT paraphrase or hand-edit; copy the literal terminal output)
- Confirmation Triade Python is green
</output>
</content>
</invoke>