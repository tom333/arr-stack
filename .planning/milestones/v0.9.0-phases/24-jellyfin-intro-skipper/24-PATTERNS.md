# Phase 24: Jellyfin Intro Skipper - Pattern Map

**Mapped:** 2026-05-29
**Files analyzed:** 7
**Analogs found:** 7 / 7

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `tools/arrconf/arrconf/reconcilers/jellyfin.py` | reconciler | request-response | itself (extension) | exact — extend `_reconcile_plugins()` and `_create_library()` |
| `tools/arrconf/arrconf/resources/jellyfin/plugin.py` | model | transform | itself (extension) | exact — extend `PluginEntry` |
| `tools/arrconf/arrconf/resources/jellyfin/server_config.py` | model | transform | itself (extension) | exact — `PluginRepository` pattern for new `PluginConfig` model |
| `tools/arrconf/arrconf/config.py` | config | transform | itself §519-628 | exact — `JellyfinPluginsSection` / `JellyfinLibrariesSection` pattern |
| `tools/arrconf/arrconf/generators/categories.py` | generator | transform | itself (extension) | exact — `generate_jellyfin_libraries()` |
| `charts/arr-stack/files/arrconf.yml` | config | YAML | itself §245-303 | exact — `plugins.required[]` + `server_config.plugin_repositories[]` blocks |
| `tools/arrconf/tests/test_reconcilers_jellyfin_plugin_install.py` | test | request-response | `tests/test_reconcilers_jellyfin.py` | exact — `@pytest.mark.respx` + `_mock_all_gets()` + `_make_instance()` pattern |

---

## Pattern Assignments

### `tools/arrconf/arrconf/reconcilers/jellyfin.py` (reconciler, request-response)

**Analog:** itself — three distinct extension points.

#### Extension point A: New endpoint constants (top of file, after existing constants, lines 59-77)

```python
# Existing constants to keep unchanged:
LIBRARY_VIRTUALFOLDERS_PATH = "/Library/VirtualFolders"
LIBRARY_PATHS_PATH = "/Library/VirtualFolders/Paths"
USERS_PATH = "/Users"
SYSTEM_CONFIGURATION_PATH = "/System/Configuration"
PLUGINS_PATH = "/Plugins"

# ADD:
PACKAGES_INSTALLED_PATH = "/Packages/Installed"
# PLUGIN_CONFIG_PATH template: f"/Plugins/{plugin_id}/Configuration"

# Non-actionable install states (mirrors _ACTIVE_PLUGIN_STATUSES pattern):
_ACTIVE_PLUGIN_STATUSES: frozenset[str] = frozenset({"Active", "Restart"})
# ADD (install-pending detection):
_INSTALL_PENDING_STATUSES: frozenset[str] = frozenset({"NotSupported", "Superceded"})
```

#### Extension point B: `_reconcile_plugins()` — two-run install model (lines 461-529)

The existing function signature and structure stays unchanged; the body is extended. Copy the entire existing function flow and add the install step before the enable step:

```python
def _reconcile_plugins(
    client: JellyfinClient,
    section: JellyfinPluginsSection,
    dry_run: bool,
) -> list[str]:
    # ... (existing preamble unchanged) ...
    current_plugins: list[dict[str, Any]] = client.get(PLUGINS_PATH)
    by_name: dict[str, dict[str, Any]] = {
        str(p["Name"]): p for p in current_plugins if p.get("Name")
    }
    by_id: dict[str, dict[str, Any]] = {str(p["Id"]): p for p in current_plugins if p.get("Id")}
    actions: list[str] = []

    for entry in section.required:
        cluster = by_id.get(entry.id) if entry.id else by_name.get(entry.name)

        # NEW: plugin absent → install step (two-run model, D-02)
        if cluster is None:
            if entry.install_guid and entry.install_version and entry.install_repo_url:
                # Attempt install (D-01 reversal of D-07-PLUGINS-01)
                if dry_run:
                    log.info("dry_run_skip", resource="plugin_install", name=entry.name)
                    actions.append(f"plugin_install:dry_run:{entry.name}")
                    continue
                client._request(
                    "POST",
                    f"{PACKAGES_INSTALLED_PATH}/{entry.name}",
                    params={
                        "assemblyGuid": entry.install_guid,
                        "version": entry.install_version,
                        "repositoryUrl": entry.install_repo_url,
                    },
                )
                log.warning(
                    "plugin_install_queued",
                    name=entry.name,
                    guid=entry.install_guid,
                    version=entry.install_version,
                    hint=(
                        "Jellyfin restart required: "
                        "kubectl rollout restart deployment/jellyfin -n selfhost"
                    ),
                )
                actions.append(f"plugin_install_queued:{entry.name}")
            else:
                # Existing warning path (no install fields set)
                log.warning("plugin_missing_skip", name=entry.name, id=entry.id, ...)
            continue

        # EXISTING: activate if not yet active (lines 499-527, unchanged)
        plugin_id: str = cluster["Id"]
        plugin_version: str = cluster["Version"]
        status: str = cluster.get("Status", "")
        if status in _ACTIVE_PLUGIN_STATUSES:
            log.info("plugin_already_active", ...)
            continue
        if dry_run:
            actions.append(f"plugin_enable:dry_run:{entry.name}")
            continue
        client._request("POST", f"{PLUGINS_PATH}/{plugin_id}/{plugin_version}/Enable")
        actions.append(f"plugin_enabled:{entry.name}")

    # NEW: plugin-config step (after enable loop, for installed+active plugins)
    for entry in section.required:
        if not entry.config:
            continue
        cluster = by_id.get(entry.id) if entry.id else by_name.get(entry.name)
        if cluster is None or cluster.get("Status") not in _ACTIVE_PLUGIN_STATUSES:
            continue  # not yet active — skip config (run N+1 after restart applies it)
        plugin_id = cluster["Id"]
        # GET current config, diff, POST if different
        # Pattern: same GET-diff-POST as _reconcile_server_config()
        cluster_config: dict[str, Any] = client.get(f"{PLUGINS_PATH}/{plugin_id}/Configuration")
        desired_config = entry.config.model_dump(exclude_none=True)
        if all(cluster_config.get(k) == v for k, v in desired_config.items()):
            log.info("plugin_config_no_op", name=entry.name)
            continue
        if dry_run:
            actions.append(f"plugin_config:dry_run:{entry.name}")
            continue
        client._request("POST", f"{PLUGINS_PATH}/{plugin_id}/Configuration", json=desired_config)
        log.info("plugin_config_applied", name=entry.name)
        actions.append(f"plugin_config_applied:{entry.name}")

    return actions
```

#### Extension point C: `_create_library()` and `generate_jellyfin_libraries()` — `EnableChapterImageExtraction`

`_create_library()` currently posts `json={}` (empty `AddVirtualFolderDto`). To enable chapter extraction the body must carry `LibraryOptions`:

```python
# CURRENT (line 149):
json={},  # AddVirtualFolderDto with LibraryOptions=null

# NEW pattern — pass LibraryOptions when desired_lib.enable_chapter_image_extraction:
json={
    "LibraryOptions": {
        "EnableChapterImageExtraction": desired_lib.enable_chapter_image_extraction,
    }
} if desired_lib.enable_chapter_image_extraction else {},
```

For existing libraries (not created this run), a new helper `_update_library_options()` follows the same pattern as `_add_missing_paths()`:

```python
def _update_library_options(
    client: JellyfinClient,
    desired_lib: JellyfinLibrary,
    cluster_lib: dict[str, Any],
    dry_run: bool,
) -> list[str]:
    """POST /Library/VirtualFolders/LibraryOptions when EnableChapterImageExtraction drifts."""
    library_options = cluster_lib.get("LibraryOptions") or {}
    cluster_value = library_options.get("EnableChapterImageExtraction", False)
    if cluster_value == desired_lib.enable_chapter_image_extraction:
        return []
    if dry_run:
        log.info("dry_run_skip", resource="library_options", name=desired_lib.name)
        return [f"library_options:dry_run:{desired_lib.name}"]
    client._request(
        "POST",
        "/Library/VirtualFolders/LibraryOptions",
        json={
            "Id": cluster_lib.get("ItemId"),
            "LibraryOptions": {
                "EnableChapterImageExtraction": desired_lib.enable_chapter_image_extraction,
            },
        },
    )
    log.info("library_options_updated", name=desired_lib.name)
    return [f"library_options_updated:{desired_lib.name}"]
```

**Dry-run convention** (lines 129-137, copy verbatim for all new steps):
```python
if dry_run:
    log.info(
        "dry_run_skip",
        resource="<resource_name>",
        name=entry.name,
        # ... relevant fields ...
    )
    actions.append(f"<resource>:dry_run:{entry.name}")
    continue
```

**Action string convention** (copy from existing lines 515, 527):
- `"plugin_enable:dry_run:{name}"` — dry-run
- `"plugin_enabled:{name}"` — applied
- New: `"plugin_install_queued:{name}"` — install POSTed, restart pending
- New: `"plugin_config_applied:{name}"` — config POSTed
- New: `"plugin_config:dry_run:{name}"` — dry-run config
- New: `"library_options_updated:{name}"` — chapter extraction updated
- New: `"library_options:dry_run:{name}"` — dry-run update

---

### `tools/arrconf/arrconf/resources/jellyfin/plugin.py` (model, transform)

**Analog:** itself (lines 1-22) + `server_config.py` `PluginRepository` (lines 22-28)

**Current `PluginEntry`** (lines 16-21):
```python
class PluginEntry(BaseModel):
    """A required-activate plugin reference (read-mostly resolver target)."""
    model_config = ConfigDict(extra="allow")
    name: str  # match key — D-07-PLUGINS-01
    id: str | None = Field(default=None)  # fallback when Name is ambiguous
```

**Extended `PluginEntry`** — add install fields + optional config block:
```python
class IntroSkipperConfig(BaseModel):
    """Intro Skipper plugin configuration (POST /Plugins/{id}/Configuration body)."""
    model_config = ConfigDict(extra="allow")
    # Fields mirror intro-skipper's config JSON keys (PascalCase)
    AutoSkip: bool = Field(default=False)           # false = show skip button only
    AutoSkipCredits: bool = Field(default=False)
    MaxParallelism: int = Field(default=1)           # D-05: concurrency=1 for single-node
    # ... additional fields as needed ...

class PluginEntry(BaseModel):
    """A required-activate plugin reference — extended with optional install fields (D-01)."""
    model_config = ConfigDict(extra="allow")
    name: str                                         # match key
    id: str | None = Field(default=None)              # fallback when Name is ambiguous
    # NEW install fields (all optional — absent = activation-only, old behavior)
    install_guid: str | None = Field(default=None,
        description="Plugin GUID for POST /Packages/Installed (e.g. c83d86bb-...)")
    install_version: str | None = Field(default=None,
        description="Pinned plugin version (e.g. '1.10.11.19')")
    install_repo_url: str | None = Field(default=None,
        description="Repository manifest URL (e.g. 'https://intro-skipper.org/manifest.json')")
    # NEW config block (optional — absent = no config management)
    config: IntroSkipperConfig | None = Field(default=None,
        description="Plugin-specific config to POST to /Plugins/{id}/Configuration")
```

**Import pattern** (line 1-5, copy):
```python
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
```

---

### `tools/arrconf/arrconf/resources/jellyfin/server_config.py` (model, transform)

**Analog:** itself (lines 1-43) — `PluginRepository` is the direct pattern for new models.

No new model needed for server_config itself. The `PluginRepository` model is already defined and already handles the Intro Skipper repo entry declaratively — JFSKIP-01 is a YAML-only change.

`SERVER_CONFIG_ALLOWLIST` in `reconcilers/jellyfin.py` (lines 66-74) does NOT need updating — `PluginRepositories` is already in the allowlist.

**For reference — `PluginRepository` shape** (lines 22-28):
```python
class PluginRepository(BaseModel):
    model_config = ConfigDict(extra="allow")
    Name: str
    Url: str
    Enabled: bool = Field(default=True)
```

The YAML entry to add for Intro Skipper follows this schema verbatim.

---

### `tools/arrconf/arrconf/config.py` (config, transform)

**Analog:** `JellyfinPluginsSection` (lines 587-605) and `JellyfinLibrariesSection` (lines 519-543).

**`JellyfinPluginsSection` extension** — no new section class needed; the existing class already holds `required: list[PluginEntry]`. The `PluginEntry` model gains the new install/config fields (see plugin.py above). The `extra="forbid"` on `JellyfinPluginsSection` itself is correct and stays.

**`JellyfinLibrariesSection` extension** — add `enable_chapter_image_extraction` field:

```python
class JellyfinLibrariesSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enable: bool = Field(default=True, ...)
    prune: bool = Field(default=False, ...)
    # NEW — D-06 uniform chapter extraction on all 10 libs
    enable_chapter_image_extraction: bool = Field(
        default=False,
        description=(
            "When True, EnableChapterImageExtraction=true is passed to LibraryOptions "
            "on all 10 Category libs. Uniform across all libs (D-06 simplicity)."
        ),
    )
```

**`JellyfinInstance` model** (lines 608-628): no change needed — `libraries` and `plugins` fields already point to the right section types.

**Import pattern** (copy from top of config.py, existing):
```python
from pydantic import BaseModel, ConfigDict, Field
```

**`PluginRepository` import** (already at top of config.py, line ~36 area):
```python
from arrconf.resources.jellyfin.server_config import PluginRepository
```

New import to add:
```python
from arrconf.resources.jellyfin.plugin import IntroSkipperConfig, PluginEntry
```

---

### `tools/arrconf/arrconf/generators/categories.py` (generator, transform)

**Analog:** `generate_jellyfin_libraries()` (lines 199-220) — pure extension.

**Current function** (lines 199-220):
```python
def generate_jellyfin_libraries(cfg: RootConfig) -> list[JellyfinLibrary]:
    return [
        JellyfinLibrary(
            name=c.display,
            collection_type=_KIND_TO_COLLECTION_TYPE[c.kind],
            paths=[c.base_path],
        )
        for c in cfg.categories
    ]
```

**Extended function** — add `enable_chapter_image_extraction` field when `JellyfinLibrary` gains it:
```python
def generate_jellyfin_libraries(cfg: RootConfig) -> list[JellyfinLibrary]:
    """REQ-jellyfin-categories-as-libs + D-06 chapter extraction (Phase 24).

    Phase 24 adds EnableChapterImageExtraction=True uniformly on all 10 libs (D-06).
    Flows from generator → JellyfinLibrary.enable_chapter_image_extraction →
    _create_library() POST body / _update_library_options() for existing libs.
    """
    return [
        JellyfinLibrary(
            name=c.display,
            collection_type=_KIND_TO_COLLECTION_TYPE[c.kind],
            paths=[c.base_path],
            enable_chapter_image_extraction=True,  # D-06: uniform, all 10 libs
        )
        for c in cfg.categories
    ]
```

`JellyfinLibrary` needs a new field `enable_chapter_image_extraction: bool = Field(default=False)`. The model uses `extra="allow"` so adding it is non-breaking.

---

### `charts/arr-stack/files/arrconf.yml` (config, YAML)

**Analog:** itself, current `jellyfin.main` block (lines 245-303 of arrconf.yml).

**Add to `server_config.plugin_repositories[]`** (after existing Jellyfin Stable entry, line 293):
```yaml
server_config:
  plugin_repositories:
    - Name: "Jellyfin Stable"
      Url: "https://repo.jellyfin.org/files/plugin/manifest.json"
      Enabled: true
    # D-03 (JFSKIP-01): Intro Skipper manifest — set-by-URL idempotent via _server_config_equivalent()
    - Name: "Intro Skipper"
      Url: "https://intro-skipper.org/manifest.json"
      Enabled: true
```

**Add to `plugins.required[]`** (after existing plugin list, line 303):
```yaml
plugins:
  enable: true
  required:
    - name: "TMDb"
    - name: "OMDb"
    - name: "MusicBrainz"
    - name: "AudioDB"
    - name: "Studio Images"
    - name: "Kodi Sync Queue"
    # D-01 (JFSKIP-02): Intro Skipper install + config (two-run model per D-02)
    - name: "Intro Skipper"
      install_guid: "c83d86bb-a1e0-4c35-a113-e2101cf4ee6b"
      install_version: "1.10.11.19"
      install_repo_url: "https://intro-skipper.org/manifest.json"
      config:
        AutoSkip: false          # show skip button; do NOT auto-skip (PROJECT.md Out of Scope)
        AutoSkipCredits: false
        MaxParallelism: 1        # D-05: off-peak concurrency cap for single-node MicroK8s
```

**Add to `libraries:` section** (D-06 chapter extraction):
```yaml
libraries:
  enable: true
  prune: false
  enable_chapter_image_extraction: true  # D-06: uniform on all 10 Category libs
```

---

### `tools/arrconf/tests/test_reconcilers_jellyfin_plugin_install.py` (test, request-response)

**Analog:** `tests/test_reconcilers_jellyfin.py` — copy the entire fixture/helper scaffold verbatim.

**Imports pattern** (lines 1-36 of existing test file):
```python
from __future__ import annotations
import copy
import json
from typing import Any
import httpx
import pytest
import respx
from arrconf.client_base import JellyfinClient
from arrconf.config import (
    JellyfinInstance,
    JellyfinLibrariesSection,
    JellyfinPluginsSection,
    JellyfinServerConfigSection,
    JellyfinUsersSection,
)
from arrconf.reconcilers.jellyfin import reconcile_jellyfin
from arrconf.resources.jellyfin import (
    JellyfinLibrary,
    JellyfinUserPolicy,
    PluginEntry,
    PluginRepository,
)
```

**Test base URL + fixture constants** (lines 38-49):
```python
JELLYFIN_BASE = "http://jellyfin.test:8096"
INTRO_SKIPPER_GUID = "c83d86bb-a1e0-4c35-a113-e2101cf4ee6b"
INTRO_SKIPPER_VERSION = "1.10.11.19"
INTRO_SKIPPER_REPO = "https://intro-skipper.org/manifest.json"
```

**`_mock_all_gets()` helper pattern** (lines 248-273) — copy wholesale; extend the `plugins` default fixture to include the pre-install state (plugin absent) and post-install state (plugin present, Active):
```python
# Fixture for "plugin absent" state (pre-install, Run N):
def _plugins_no_intro_skipper() -> list[dict[str, Any]]:
    return [
        {"Name": "TMDb", "Id": "...", "Version": "...", "Status": "Active"},
        # ... other plugins ...
        # Intro Skipper deliberately absent
    ]

# Fixture for "plugin present, Active" state (post-restart, Run N+1):
def _plugins_with_intro_skipper_active() -> list[dict[str, Any]]:
    return [
        {"Name": "TMDb", "Id": "...", "Version": "...", "Status": "Active"},
        {
            "Name": "Intro Skipper",
            "Id": INTRO_SKIPPER_GUID,
            "Version": INTRO_SKIPPER_VERSION,
            "Status": "Active",
        },
    ]
```

**respx route registration pattern** (lines 319-367, `@pytest.mark.respx` variant):
```python
@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_plugin_install_queued_when_absent(
    respx_mock: respx.MockRouter,
    jellyfin_library_virtualfolders_fixture: list[dict[str, Any]],
    # ... all 5 Jellyfin fixture args ...
) -> None:
    """D-01/D-02: POST /Packages/Installed fired when plugin absent; action=plugin_install_queued."""
    install_route = respx_mock.post(
        url__regex=rf"/Packages/Installed/Intro Skipper"
    ).mock(return_value=httpx.Response(204))

    _mock_all_gets(respx_mock, plugins=_plugins_no_intro_skipper(), ...)

    result = reconcile_jellyfin(client, instance, _DEFAULT_LIBRARIES, dry_run=False)

    assert install_route.called
    assert "plugin_install_queued:Intro Skipper" in result.actions_taken
    # Verify query params:
    req = install_route.calls[0].request
    assert req.url.params["assemblyGuid"] == INTRO_SKIPPER_GUID
    assert req.url.params["version"] == INTRO_SKIPPER_VERSION
    assert req.url.params["repositoryUrl"] == INTRO_SKIPPER_REPO
```

**`@respx.mock` standalone pattern** (lines 1117-1149) — for tests that only exercise one function:
```python
@respx.mock
def test_plugin_install_idempotent_when_already_present() -> None:
    """Run N+1: plugin present → no install POST, goes to enable/config path."""
    respx.get(f"{JELLYFIN_BASE}/Plugins").mock(
        return_value=httpx.Response(200, json=_plugins_with_intro_skipper_active())
    )
    install_route = respx.post(url__regex=rf"{JELLYFIN_BASE}/Packages/Installed/.*").mock(
        return_value=httpx.Response(204)
    )
    # ... test body ...
    assert install_route.called is False
```

**Dry-run assertion pattern** (lines 987-995):
```python
result = reconcile_jellyfin(client, instance, _DEFAULT_LIBRARIES, dry_run=True)
for action in result.actions_taken:
    assert "dry_run" in action, f"Unexpected non-dry-run action in dry_run mode: {action}"
```

**Body capture pattern** (lines 515-520, used for verifying POST body content):
```python
captured_body: dict[str, Any] = {}

def capture_post(request: httpx.Request) -> httpx.Response:
    nonlocal captured_body
    captured_body = json.loads(request.content)
    return httpx.Response(204)

respx_mock.post("/Plugins/...").mock(side_effect=capture_post)
```

**Required test cases for plugin install (copy pattern from existing tests):**
1. `test_plugin_install_queued_when_absent` — Run N: absent → POST /Packages/Installed, action=`plugin_install_queued`
2. `test_plugin_install_idempotent_when_present` — Run N+1: present → no install POST
3. `test_plugin_install_no_action_when_install_fields_absent` — PluginEntry without install fields → existing `plugin_missing_skip` warning path
4. `test_plugin_install_dry_run_no_post` — dry_run=True → zero writes
5. `test_plugin_config_applied_when_plugin_active` — config block present + plugin Active → GET+POST /Plugins/{id}/Configuration
6. `test_plugin_config_no_op_when_already_matches` — config matches cluster → no POST
7. `test_plugin_config_skipped_when_plugin_not_active` — plugin present but not Active (post-install, pre-restart) → skip config
8. `test_chapter_extraction_enabled_on_library_create` — new lib with enable_chapter_image_extraction=True → POST /Library/VirtualFolders body has LibraryOptions
9. `test_chapter_extraction_update_existing_library` — existing lib, cluster=False, desired=True → POST /Library/VirtualFolders/LibraryOptions
10. `test_chapter_extraction_no_op_when_already_enabled` — existing lib, cluster=True, desired=True → no update POST

---

## Shared Patterns

### Authentication (JellyfinClient — all Jellyfin endpoint calls)
**Source:** `tools/arrconf/arrconf/client_base.py` (JellyfinClient class)
**Apply to:** All new `client._request()` calls in `_reconcile_plugins()` and helpers
```python
# JellyfinClient uses MediaBrowser token header, NOT X-Api-Key:
# Authorization: MediaBrowser Token="<key>", Client="arrconf", Device="arrconf", ...
# client._request("POST", path, params={...}, json={...}) — matches existing calls
```

### Idempotence: GET-diff-POST (server_config pattern)
**Source:** `tools/arrconf/arrconf/reconcilers/jellyfin.py` lines 408-458
**Apply to:** `_update_library_options()` helper and plugin config POST
```python
# Pattern: GET cluster → compare against desired → POST only on diff
cluster_config: dict[str, Any] = client.get(SYSTEM_CONFIGURATION_PATH)
merged: dict[str, Any] = dict(cluster_config)
# ... apply desired fields ...
if _server_config_equivalent(cluster_config, merged):
    log.info("server_config_no_op")
    return []
client._request("POST", SYSTEM_CONFIGURATION_PATH, json=merged)
```

### Error handling (implicit via client_base)
**Source:** `tools/arrconf/arrconf/client_base.py` + `tools/arrconf/arrconf/exceptions.py`
**Apply to:** All new `client._request()` calls
No explicit try/except needed in reconcilers — `ArrApiClient._request()` raises `NotFoundError`, `AuthError`, `ServerError` which propagate upward. Exception to this: the `_prune_libraries()` helper (lines 273-285) wraps DELETE in `try/except NotFoundError` — copy that pattern only for Pitfall 16-2-equivalent cases.

### Structlog event pattern
**Source:** `tools/arrconf/arrconf/reconcilers/jellyfin.py` throughout
**Apply to:** All new log events
```python
log.info("step_begin", step="plugins", step_index=4)   # existing — step index stays 4
log.info("plugin_already_active", name=entry.name, status=status)
log.warning("plugin_install_queued", name=entry.name, guid=..., hint="kubectl rollout restart ...")
log.info("plugin_config_applied", name=entry.name)
log.info("library_options_updated", name=desired_lib.name)
```

### Topological order invariant (D-07-ORDER-01)
**Source:** `tools/arrconf/arrconf/reconcilers/jellyfin.py` lines 532-556
**Apply to:** `reconcile_jellyfin()` function — do NOT change the call order
```python
actions_taken += _reconcile_libraries(client, instance.libraries, libraries, dry_run)
actions_taken += _reconcile_users(client, instance.users, dry_run)
actions_taken += _reconcile_server_config(client, instance.server_config, dry_run)
actions_taken += _reconcile_plugins(client, instance.plugins, dry_run)
# step_index values: 1, 2, 3, 4 — must remain stable (regression test contract)
```

### pydantic `extra="forbid"` on section models
**Source:** `tools/arrconf/arrconf/config.py` lines 532, 553, 573, 594
**Apply to:** Any new `*Section` pydantic class in config.py
```python
model_config = ConfigDict(extra="forbid")   # catches YAML typos at load time
```

### `extra="allow"` on resource/leaf models
**Source:** `tools/arrconf/arrconf/resources/jellyfin/plugin.py` line 19
**Source:** `tools/arrconf/arrconf/resources/jellyfin/server_config.py` line 25
**Apply to:** `IntroSkipperConfig` and extended `PluginEntry` leaf models
```python
model_config = ConfigDict(extra="allow")   # forward-compat for new Jellyfin API fields
```

---

## No Analog Found

All files have close analogs. No files require RESEARCH.md patterns as primary source — all patterns are derived directly from the existing Jellyfin reconciler codebase.

---

## Critical Constraints (from PITFALLS.md + CONTEXT.md)

| Constraint | Source | Implementation impact |
|---|---|---|
| Two-run model — no same-run enable after install | PITFALLS B3, D-02 | `_reconcile_plugins()`: if install POST just fired → append `plugin_install_queued` and `continue` (skip enable/config in same run) |
| Version REQUIRED in enable path | PITFALLS §Pitfall 5, reconciler lines 518-519 | `POST /Plugins/{plugin_id}/{plugin_version}/Enable` — copy verbatim |
| `POST /Packages/Installed` query params, not body | STACK.md §B2 | `params={assemblyGuid, version, repositoryUrl}`, `json=None` |
| `EnableChapterImageExtraction` in LibraryOptions, NOT /System/Configuration | STACK.md §B4 | Separate endpoint `POST /Library/VirtualFolders/LibraryOptions`, body: `{Id, LibraryOptions: {EnableChapterImageExtraction: true}}` |
| Server config POST is full-REPLACE (Pitfall 1) | reconciler lines 449-451 | Never modify `_reconcile_server_config()` — plugin repo addition is YAML-only |
| NEVER automate Jellyfin pod restart from arrconf | PITFALLS B3, B4 | Only log `plugin_install_queued` warning with `hint: kubectl rollout restart ...` |
| AutoSkip = false (PROJECT.md Out of Scope) | CONTEXT.md `<deferred>` | `IntroSkipperConfig.AutoSkip = false` hardcoded in YAML default |
| co-bump `arrconf.image.tag` (minor bump — new feature) | CLAUDE.md "Release pin co-bump pattern" | Same commit that adds Python code must bump `charts/arr-stack/values.yaml#arrconf.image.tag` minor |

---

## Metadata

**Analog search scope:** `tools/arrconf/arrconf/reconcilers/`, `tools/arrconf/arrconf/resources/jellyfin/`, `tools/arrconf/arrconf/config.py`, `tools/arrconf/arrconf/generators/`, `tools/arrconf/tests/`
**Files scanned:** 7 source files + 1 test file + conftest.py fixtures
**Pattern extraction date:** 2026-05-29
