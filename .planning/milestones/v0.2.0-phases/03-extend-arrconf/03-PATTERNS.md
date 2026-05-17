# Phase 03: Étendre arrconf - Pattern Map

**Mapped:** 2026-05-11
**Files analyzed:** 16
**Analogs found:** 16 / 16

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tools/arrconf/arrconf/differ.py` | utility | transform | self (existing) | exact (modify) |
| `tools/arrconf/arrconf/client_base.py` | service | request-response | self (existing `SonarrClient`) | exact (modify) |
| `tools/arrconf/arrconf/config.py` | model | transform | self (existing `SonarrInstance`) | exact (modify) |
| `tools/arrconf/arrconf/reconcilers/sonarr.py` | service | CRUD | self (existing `reconcile_sonarr`) | exact (modify) |
| `tools/arrconf/arrconf/reconcilers/radarr.py` | service | CRUD | `reconcilers/sonarr.py` | exact |
| `tools/arrconf/arrconf/reconcilers/prowlarr.py` | service | CRUD | `reconcilers/sonarr.py` | role-match |
| `tools/arrconf/arrconf/resources/sonarr/indexer.py` | model | CRUD | `resources/sonarr/download_client.py` | exact |
| `tools/arrconf/arrconf/resources/sonarr/notification.py` | model | CRUD | `resources/sonarr/download_client.py` | exact |
| `tools/arrconf/arrconf/resources/sonarr/root_folder.py` | model | CRUD | `resources/sonarr/download_client.py` | role-match (simpler) |
| `tools/arrconf/arrconf/resources/sonarr/host_config.py` | model | request-response | `resources/sonarr/download_client.py` | role-match (singleton) |
| `tools/arrconf/arrconf/resources/prowlarr/__init__.py` | config | — | `resources/sonarr/__init__.py` | exact |
| `tools/arrconf/arrconf/resources/prowlarr/application.py` | model | CRUD | `resources/sonarr/download_client.py` | exact |
| `tools/arrconf/tests/test_differ.py` | test | transform | self (existing) | exact (modify) |
| `tools/arrconf/tests/test_reconcilers_sonarr.py` | test | CRUD | self (existing) | exact (modify) |
| `tools/arrconf/tests/test_reconcilers_radarr.py` | test | CRUD | `tests/test_reconcilers_sonarr.py` | exact |
| `tools/arrconf/tests/test_reconcilers_prowlarr.py` | test | CRUD | `tests/test_reconcilers_sonarr.py` | role-match |

---

## Pattern Assignments

### `tools/arrconf/arrconf/differ.py` (utility, transform — WR-01 fix)

**Analog:** self (lines 140 and 96-162)

**WR-01: Replace inline privacy tuple with module-level frozenset** (line 140 area, after `_REDACTED_VALUE`):
```python
# Add after line 32 (_REDACTED_VALUE definition):
_CREDENTIAL_PRIVACY_VALUES: frozenset[str] = frozenset(
    {"password", "userName", "apiKey", "token"}
)
```

**Replace the inline check** (currently line 140):
```python
# FROM (line 140):
if cur_privacy in ("password", "userName"):
# TO:
if cur_privacy in _CREDENTIAL_PRIVACY_VALUES:
```

**Context — existing `merge_fields_for_put` credential-omit branch** (lines 139-152):
```python
v = des_f.get("value")
if cur_privacy in ("password", "userName"):   # ← this line becomes _CREDENTIAL_PRIVACY_VALUES
    if v == "" or v is None:
        log.info(
            "merge_field_omitted_credential",
            name=des_f["name"],
            privacy=cur_privacy,
        )
        continue
    merged_fields.append(des_f)
    continue
```

**Optional: extract `execute_plan[T]` generic** (RESEARCH.md Pattern 4 — planner's call).
If extracted, insert after `merge_fields_for_put` function, before `reconcile()`:
```python
def execute_plan[T: BaseModel](
    client: ArrApiClient,
    path: str,
    plan: list[PlannedAction[T]],
    dry_run: bool,
) -> list[str]:
    """Generic ADD/UPDATE/DELETE executor (reused by all reconcilers)."""
    actions_taken: list[str] = []
    for p in plan:
        if p.action in (Action.NO_OP, Action.PRUNE_SKIP, Action.PRUNE_PROTECTED):
            continue
        if dry_run:
            log.info("dry_run_skip", action=p.action.value, name=p.name)
            continue
        if p.action == Action.ADD:
            assert p.desired is not None
            body = p.desired.model_dump(exclude_none=True, by_alias=False)
            client.post(path, json=body)
            actions_taken.append(f"add:{p.name}")
        elif p.action == Action.UPDATE:
            assert p.desired is not None
            assert p.current is not None
            assert p.current.id is not None
            body = merge_fields_for_put(p.current, p.desired)
            body["id"] = p.current.id
            client.put(path, id=p.current.id, json=body)
            actions_taken.append(f"update:{p.name}")
        elif p.action == Action.DELETE:
            assert p.current is not None
            assert p.current.id is not None
            client.delete(path, id=p.current.id)
            actions_taken.append(f"delete:{p.name}")
    return actions_taken
```
If not extracted, copy `_execute()` verbatim from `reconcilers/sonarr.py` lines 74-111 into each new reconciler, adjusting type hints.

---

### `tools/arrconf/arrconf/client_base.py` (service, request-response — add RadarrClient, ProwlarrClient)

**Analog:** `client_base.py` — existing `SonarrClient` (lines 127-132)

**Imports pattern** (lines 1-26): no new imports needed; copy the existing module header.

**SonarrClient pattern to copy** (lines 127-132):
```python
class SonarrClient(_ArrV3Client):
    """Sonarr REST client."""

    api_path = "/api/v3"  # D-03: Sonarr v4+ only — no multi-version dispatch in Phase 1
    name = "sonarr"
```

**New declarations to append after `SonarrClient`**:
```python
class RadarrClient(_ArrV3Client):
    """Radarr REST client."""

    api_path = "/api/v3"
    name = "radarr"


class ProwlarrClient(_ArrV3Client):
    """Prowlarr REST client (api/v1 — different from Sonarr/Radarr v3).

    Prowlarr uses /api/v1 exclusively. Override required (Pitfall 3 in RESEARCH.md).
    """

    api_path = "/api/v1"
    name = "prowlarr"
```

---

### `tools/arrconf/arrconf/config.py` (model, transform — D-03-05 expansion)

**Analog:** self — existing `SonarrInstance`, `DownloadClientsSection`, `RootConfig` (lines 19-57)

**Imports pattern** (lines 1-17):
```python
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from ruyaml import YAML

from arrconf.exceptions import ConfigError
from arrconf.resources.sonarr.download_client import DownloadClient
```
Phase 3 adds imports for new resource models. Add after the `DownloadClient` import:
```python
from arrconf.resources.sonarr.indexer import Indexer
from arrconf.resources.sonarr.notification import Notification
from arrconf.resources.sonarr.root_folder import RootFolder
from arrconf.resources.prowlarr.application import Application
```

**Section model pattern** (copy `DownloadClientsSection` lines 19-28):
```python
class DownloadClientsSection(BaseModel):
    """A list of download_clients with opt-in prune (D-04)."""

    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(
        default=False,
        description="Opt-in deletion of unmanaged resources (D-04).",
    )
    items: list[DownloadClient] = Field(default_factory=list)
```

**New section models to add** (follow `DownloadClientsSection` verbatim, substituting type):
```python
class IndexersSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(default=False)
    items: list[Indexer] = Field(default_factory=list)


class NotificationsSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(default=False)
    items: list[Notification] = Field(default_factory=list)


class RootFoldersSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(default=False)
    items: list[RootFolder] = Field(default_factory=list)


class HostConfigSection(BaseModel):
    """Opt-in host_config reconciliation (D-03-04).

    enable=False by default — prevents accidental auth lockout (RESEARCH.md §4).
    """
    model_config = ConfigDict(extra="forbid")
    enable: bool = Field(default=False)
    # Only the safe-to-reconcile subset of host_config fields:
    authenticationMethod: str | None = None
    authenticationRequired: str | None = None
    urlBase: str | None = None
    instanceName: str | None = None


class AppsSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(default=False)
    items: list[Application] = Field(default_factory=list)
```

**`SonarrInstance` extension** (lines 30-35 — add four new fields):
```python
class SonarrInstance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_url: str = Field(description="Sonarr base URL e.g. http://sonarr.svc:8989")
    download_clients: DownloadClientsSection = Field(default_factory=DownloadClientsSection)
    # Phase 3 additions:
    indexers: IndexersSection = Field(default_factory=IndexersSection)
    notifications: NotificationsSection = Field(default_factory=NotificationsSection)
    root_folders: RootFoldersSection = Field(default_factory=RootFoldersSection)
    host_config: HostConfigSection = Field(default_factory=HostConfigSection)
```

**New instance models** (copy `SonarrInstance` shape):
```python
class RadarrInstance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_url: str = Field(description="Radarr base URL e.g. http://radarr.svc:7878")
    download_clients: DownloadClientsSection = Field(default_factory=DownloadClientsSection)
    indexers: IndexersSection = Field(default_factory=IndexersSection)
    notifications: NotificationsSection = Field(default_factory=NotificationsSection)
    root_folders: RootFoldersSection = Field(default_factory=RootFoldersSection)
    host_config: HostConfigSection = Field(default_factory=HostConfigSection)


class ProwlarrInstance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_url: str = Field(description="Prowlarr base URL e.g. http://prowlarr.svc:9696")
    apps: AppsSection = Field(default_factory=AppsSection)
```

**`RootConfig` expansion** (lines 52-57 — replace the `AppsConfig` indirection):
RESEARCH.md D-03-05 and CONTEXT.md D-03-05 both show the new `RootConfig` structure. Replace
the current `AppsConfig` + `RootConfig` with:
```python
class RootConfig(BaseModel):
    """Top-level arrconf YAML schema (root for JSON Schema generation)."""

    model_config = ConfigDict(extra="forbid")
    sonarr: dict[str, SonarrInstance] = Field(default_factory=dict)
    radarr: dict[str, RadarrInstance] = Field(default_factory=dict)
    prowlarr: dict[str, ProwlarrInstance] = Field(default_factory=dict)
```
Note: the current `RootConfig.apps: AppsConfig` indirection is dropped. The `__main__.py` caller
must be updated to access `config.sonarr["main"]` instead of `config.apps.sonarr.main`. Check
`__main__.py` and `diff_cmd.py` for callers before finalizing.

---

### `tools/arrconf/arrconf/reconcilers/sonarr.py` (service, CRUD — extend with 4 new resource types)

**Analog:** self (lines 1-151) — add new reconcile helpers following `_execute` pattern

**Module-level constants to add** (after existing constants at lines 28-30):
```python
INDEXER_PATH = "/indexer"
NOTIFICATION_PATH = "/notification"
ROOT_FOLDER_PATH = "/rootfolder"
HOST_CONFIG_PATH = "/config/host"
```

**New imports to add** (after existing imports at lines 20-26):
```python
from arrconf.config import HostConfigSection, IndexersSection, NotificationsSection, RootFoldersSection
from arrconf.differ import diff_models
from arrconf.resources.sonarr.indexer import Indexer
from arrconf.resources.sonarr.notification import Notification
from arrconf.resources.sonarr.root_folder import RootFolder
from arrconf.resources.sonarr.host_config import HostConfig
```

**List-resource reconcile helper pattern** (copy `_execute` + `reconcile()` call from lines 74-144):
```python
def _reconcile_list_resource[T: BaseModel](
    client: SonarrClient,
    path: str,
    current_raw: list[dict[str, Any]],
    model_cls: type[T],
    desired: list[T],
    match_key: str,
    prune: bool,
    managed_tag_id: int | None,
    dry_run: bool,
) -> list[str]:
    current = [model_cls.model_validate(x) for x in current_raw]
    plan = reconcile(
        current=current,
        desired=desired,
        match_key=match_key,
        prune=prune,
        managed_tag_id=managed_tag_id,
    )
    return _execute(client, path, plan, dry_run)
```

**Singleton host_config reconcile helper** (RESEARCH.md Pattern 2):
```python
def _reconcile_host_config(
    client: SonarrClient,
    section: HostConfigSection,
    dry_run: bool,
) -> None:
    if not section.enable:
        log.info("host_config_reconcile_skipped")
        return
    raw = client.get(HOST_CONFIG_PATH)
    current = HostConfig.model_validate(raw)
    # Build desired HostConfig from section's writable fields only:
    desired = HostConfig.model_validate(section.model_dump(exclude_none=True, exclude={"enable"}))
    diffs = diff_models(current, desired)
    if not diffs:
        log.info("host_config_no_op")
        return
    if dry_run:
        log.info("dry_run_skip", action="update", resource="host_config", diff_fields=diffs)
        return
    body = merge_fields_for_put(current, desired)
    body["id"] = current.id   # re-inject after merge strips read-only fields (Pitfall 4)
    client.put(HOST_CONFIG_PATH, id=current.id, json=body)
```

**`reconcile_sonarr` extension** — append calls in order after `download_clients` (current line 144):
```python
# Phase 3 additions — ordered: tags (done) → indexers → root_folders → download_clients → notifications → host_config
_reconcile_list_resource(
    client, INDEXER_PATH,
    client.get(INDEXER_PATH), Indexer,
    instance.indexers.items, "name", instance.indexers.prune, managed_tag.id, dry_run,
)
_reconcile_list_resource(
    client, ROOT_FOLDER_PATH,
    client.get(ROOT_FOLDER_PATH), RootFolder,
    instance.root_folders.items, "path", instance.root_folders.prune, None, dry_run,
)
# (download_clients reconcile already present)
_reconcile_list_resource(
    client, NOTIFICATION_PATH,
    client.get(NOTIFICATION_PATH), Notification,
    instance.notifications.items, "name", instance.notifications.prune, managed_tag.id, dry_run,
)
_reconcile_host_config(client, instance.host_config, dry_run)
```

---

### `tools/arrconf/arrconf/reconcilers/radarr.py` (service, CRUD — new file, full parity)

**Analog:** `tools/arrconf/arrconf/reconcilers/sonarr.py` (full file)

**Module docstring and imports pattern** (sonarr.py lines 1-26):
```python
"""Radarr reconciler — Phase 3 scope: download_clients, indexers, notifications,
root_folders, host_config (opt-in gated, D-03-01).

Topological order (RESEARCH.md §10):
1. Ensure the ``arrconf-managed`` tag exists.
2. Reconcile ``indexers`` (read-mostly alignment).
3. Reconcile ``root_folders`` (match_key="path", no managed_tag).
4. Reconcile ``download_clients`` with managed-tag protection.
5. Reconcile ``notifications``.
6. Reconcile ``host_config`` (opt-in, D-03-04 — last due to destructive potential).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

from arrconf.client_base import RadarrClient
from arrconf.config import RadarrInstance
from arrconf.differ import Action, PlannedAction, diff_models, merge_fields_for_put, reconcile
from arrconf.resources.sonarr.download_client import DownloadClient
from arrconf.resources.sonarr.indexer import Indexer
from arrconf.resources.sonarr.notification import Notification
from arrconf.resources.sonarr.root_folder import RootFolder
from arrconf.resources.sonarr.host_config import HostConfig
from arrconf.resources.sonarr.tag import Tag
```

**Result dataclass pattern** (sonarr.py lines 34-40):
```python
@dataclass
class RadarrResult:
    """Result of a Radarr reconcile run."""

    actions_taken: list[str] = field(default_factory=list)
    managed_tag_id: int | None = None
```

**`_ensure_managed_tag` pattern** (sonarr.py lines 43-61 — copy verbatim, change type hint from `SonarrClient` to `RadarrClient`):
```python
def _ensure_managed_tag(client: RadarrClient, dry_run: bool) -> Tag:
    # ... verbatim from sonarr.py lines 43-61 ...
```

**`_execute` pattern** (sonarr.py lines 74-111): If `execute_plan` is NOT extracted to `differ.py`, copy `_execute` verbatim with `SonarrClient` → `RadarrClient` type hint. If extracted, import and use `execute_plan` directly.

**`reconcile_radarr` function** — mirrors `reconcile_sonarr` (sonarr.py lines 114-150):
```python
def reconcile_radarr(
    client: RadarrClient,
    instance: RadarrInstance,
    dry_run: bool,
) -> RadarrResult:
    """Reconcile a Radarr instance (full parity with Sonarr — D-03-01)."""
    managed_tag = _ensure_managed_tag(client, dry_run)
    managed_tag_id = managed_tag.id if managed_tag.id is not None else DRY_RUN_TAG_SENTINEL_ID

    # Reconcile in topological order (RESEARCH.md §10):
    # 1. indexers (read-mostly, Prowlarr-synced)
    # 2. root_folders (match by path)
    # 3. download_clients (managed tag protection)
    # 4. notifications
    # 5. host_config (last — destructive potential)
    ...
```

**ScopeViolationError guard** — same guard as Sonarr. Radarr shares the same configarr-owned endpoints. Add a `resources/radarr/quality_profile.py` that mirrors `resources/sonarr/quality_profile.py` exactly, OR add the Radarr quality_profile import to `test_scope_violation.py`'s `FRONTIERE_MODULES`. RESEARCH.md §8 suggests reusing the Sonarr module directly since endpoints are path-identical.

---

### `tools/arrconf/arrconf/reconcilers/prowlarr.py` (service, CRUD — new file, app sync only)

**Analog:** `tools/arrconf/arrconf/reconcilers/sonarr.py` (role-match; simpler — no managed tag, no download_clients)

**Imports pattern** (key differences from sonarr.py):
```python
import os

from arrconf.client_base import ProwlarrClient
from arrconf.config import ProwlarrInstance
from arrconf.differ import Action, PlannedAction, merge_fields_for_put, reconcile
from arrconf.exceptions import ReconcileError
from arrconf.resources.prowlarr.application import Application
from arrconf.resources.sonarr.download_client import FieldKV  # reuse FieldKV — DO NOT duplicate
```

**`reconcile_prowlarr` key logic** (RESEARCH.md Pattern 3 / Pitfall 5):
```python
APP_PATH = "/applications"

def reconcile_prowlarr(
    client: ProwlarrClient,
    instance: ProwlarrInstance,
    dry_run: bool,
) -> list[str]:
    """Reconcile Prowlarr app connections (D-03-02: app sync only)."""
    raw_current = client.get(APP_PATH)
    current_apps = [Application.model_validate(x) for x in raw_current]

    desired_apps: list[Application] = []
    for app_cfg in instance.apps.items:
        api_key = os.environ.get(app_cfg.api_key_env)
        if not api_key:
            raise ReconcileError(
                f"prowlarr: env var '{app_cfg.api_key_env}' is not set "
                f"(required for app '{app_cfg.name}')"
            )
        # Build the Application with apiKey injected into fields[]:
        app = Application(
            name=app_cfg.name,
            implementation=app_cfg.type.capitalize() + "...",  # planner fills implementation lookup
            configContract=...,
            syncLevel=app_cfg.sync_level,
            fields=[
                FieldKV(name="prowlarrUrl", value=...),  # planner fills from instance.base_url
                FieldKV(name="baseUrl", value=app_cfg.base_url),
                FieldKV(name="apiKey", value=api_key),
            ],
        )
        desired_apps.append(app)

    plan = reconcile(
        current=current_apps,
        desired=desired_apps,
        match_key="name",
        prune=instance.apps.prune,
        managed_tag_id=None,  # prowlarr apps have no managed tag concept
    )
    return _execute(client, APP_PATH, plan, dry_run)
```

---

### `tools/arrconf/arrconf/resources/sonarr/indexer.py` (model, CRUD — replace stub)

**Analog:** `tools/arrconf/arrconf/resources/sonarr/download_client.py` (exact pattern)

**Full module pattern** (copy `DownloadClient` structure from download_client.py lines 1-79, substitute fields):
```python
"""Sonarr/Radarr Indexer pydantic schema.

Matched by ``name`` (D-20). Read-only fields excluded from diff/dump (D-21).
``fields[]`` uses FieldKV from download_client — do NOT re-declare.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from arrconf.resources.sonarr.download_client import FieldKV


class Indexer(BaseModel):
    """A Sonarr/Radarr indexer entry (created by Prowlarr sync, not by arrconf directly).

    WR-01 must be applied to differ.py before this model is used in reconcile()
    to prevent apiKey credential fields from being written back.
    """

    model_config = ConfigDict(extra="allow")

    name: str
    enable: bool = Field(default=True)
    enableRss: bool = Field(default=True)
    enableAutomaticSearch: bool = Field(default=True)
    enableInteractiveSearch: bool = Field(default=True)
    implementation: str
    configContract: str
    fields: list[FieldKV] = Field(default_factory=list)
    tags: list[int] = Field(default_factory=list)
    downloadClientId: int = Field(default=0)
    # Read-only (D-21):
    id: int | None = Field(default=None, exclude=True)
    implementationName: str | None = Field(default=None, exclude=True)
    infoLink: str | None = Field(default=None, exclude=True)
```

---

### `tools/arrconf/arrconf/resources/sonarr/notification.py` (model, CRUD — replace stub)

**Analog:** `tools/arrconf/arrconf/resources/sonarr/download_client.py` (exact pattern)

**Full module pattern**:
```python
"""Sonarr/Radarr Notification pydantic schema.

Uses ``extra="allow"`` to handle app-specific event trigger fields
(``onSeriesAdd`` for Sonarr, ``onMovieAdded`` for Radarr) without a model split.
``supportsOn*`` fields are read-only server capabilities — excluded from diff/dump.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from arrconf.resources.sonarr.download_client import FieldKV


class Notification(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    enable: bool = Field(default=True)
    implementation: str
    configContract: str
    fields: list[FieldKV] = Field(default_factory=list)
    tags: list[int] = Field(default_factory=list)
    includeHealthWarnings: bool = Field(default=False)
    # on* event triggers handled by extra="allow" (app-specific variant names)
    # Read-only (D-21):
    id: int | None = Field(default=None, exclude=True)
    implementationName: str | None = Field(default=None, exclude=True)
    infoLink: str | None = Field(default=None, exclude=True)
```

---

### `tools/arrconf/arrconf/resources/sonarr/root_folder.py` (model, CRUD — replace stub)

**Analog:** `tools/arrconf/arrconf/resources/sonarr/download_client.py` (simpler — no `fields[]`)

**Full module pattern**:
```python
"""Sonarr/Radarr RootFolder pydantic schema.

Matched by ``path`` (not ``name`` — Pitfall 1 in RESEARCH.md). No UPDATE endpoint
exists — path changes result in DELETE + ADD. Cluster-derived fields are excluded
to prevent spurious UPDATE plans (Pitfall 1 in RESEARCH.md §Common Pitfalls).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RootFolder(BaseModel):
    model_config = ConfigDict(extra="allow")

    path: str  # match_key for reconcile()
    # Server-derived read-only fields (D-21) — must be excluded to avoid spurious UPDATE:
    id: int | None = Field(default=None, exclude=True)
    accessible: bool | None = Field(default=None, exclude=True)
    freeSpace: int | None = Field(default=None, exclude=True)
    unmappedFolders: list[Any] | None = Field(default=None, exclude=True)
```

---

### `tools/arrconf/arrconf/resources/sonarr/host_config.py` (model, request-response — replace stub)

**Analog:** `tools/arrconf/arrconf/resources/sonarr/download_client.py` (role-match — singleton, no `fields[]`)

**Full module pattern** (RESEARCH.md §4 / Critical Implementation Detail #4):
```python
"""Sonarr/Radarr HostConfig pydantic schema — singleton GET/PUT.

Credential fields (apiKey, password) are excluded with ``exclude=True`` — they
must NEVER appear in diff or PUT body (Pitfall 4 / D-03-04 / RESEARCH.md §4).
The reconciler checks ``HostConfigSection.enable`` before calling this model.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class HostConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    # Writable fields (safe to reconcile):
    authenticationMethod: str | None = None
    authenticationRequired: str | None = None
    bindAddress: str | None = None
    port: int | None = None
    urlBase: str | None = None
    instanceName: str | None = None
    # Credential / read-only — NEVER write back (D-03-04):
    id: int | None = Field(default=None, exclude=True)
    apiKey: str | None = Field(default=None, exclude=True)
    password: str | None = Field(default=None, exclude=True)
    passwordConfirmation: str | None = Field(default=None, exclude=True)
    username: str | None = Field(default=None, exclude=True)
    branch: str | None = Field(default=None, exclude=True)
```

---

### `tools/arrconf/arrconf/resources/prowlarr/__init__.py` (config — new package init)

**Analog:** `tools/arrconf/arrconf/resources/sonarr/__init__.py` (lines 1-7)

**Full file pattern**:
```python
"""Prowlarr resource pydantic models."""

from arrconf.resources.prowlarr.application import Application

__all__ = ["Application"]
```

---

### `tools/arrconf/arrconf/resources/prowlarr/application.py` (model, CRUD — new file)

**Analog:** `tools/arrconf/arrconf/resources/sonarr/download_client.py` (exact shape)

**Full module pattern** (RESEARCH.md Pattern 3):
```python
"""Prowlarr Application pydantic schema.

Prowlarr ``/api/v1/applications`` returns the same ``fields[]`` structure as
Sonarr's download_clients. ``FieldKV`` is imported from download_client.py —
do NOT redeclare it (RESEARCH.md anti-pattern).

Matched by ``name`` (D-03-03). The ``apiKey`` field in ``fields[]`` carries
privacy="apiKey" — WR-01 fix in differ.py must be applied before this model
is used in reconcile() to prevent credential passthrough.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from arrconf.resources.sonarr.download_client import FieldKV


class Application(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    enable: bool = Field(default=True)
    implementation: str
    configContract: str
    syncLevel: str = Field(default="fullSync")  # "fullSync" | "addOnly" | "disabled"
    fields: list[FieldKV] = Field(default_factory=list)
    tags: list[int] = Field(default_factory=list)
    # Read-only (D-21):
    id: int | None = Field(default=None, exclude=True)
    implementationName: str | None = Field(default=None, exclude=True)
    infoLink: str | None = Field(default=None, exclude=True)
```

---

### `tools/arrconf/tests/test_differ.py` (test, transform — IN-02 fix + WR-01 test)

**Analog:** self (lines 387-416 — existing credential rotation test)

**IN-02 fix** (line 12 — add `FieldKV` to module-level import):
```python
# FROM (line 12):
from arrconf.resources.sonarr.download_client import DownloadClient
# TO:
from arrconf.resources.sonarr.download_client import DownloadClient, FieldKV
```
Then remove the intra-function import at line 400:
```python
# DELETE this line (currently line 400):
from arrconf.resources.sonarr.download_client import FieldKV
```

**New WR-01 test to add** (after `test_merge_fields_passes_through_non_empty_credential_value_for_rotation`):
```python
def test_merge_fields_omits_api_key_privacy_field() -> None:
    """WR-01: apiKey privacy value must be omitted by _CREDENTIAL_PRIVACY_VALUES."""
    cur = _dc(
        "sonarr-indexer",
        fields=[FieldKV(name="apiKey", value="***REDACTED***", privacy="apiKey")],
    )
    des = _dc(
        "sonarr-indexer",
        fields=[FieldKV(name="apiKey", value="", privacy="apiKey")],
    )
    result = merge_fields_for_put(cur, des)
    field_names = {f["name"] for f in result["fields"]}
    assert "apiKey" not in field_names, (
        "WR-01: privacy=apiKey field must be OMITTED from PUT body"
    )


def test_merge_fields_omits_token_privacy_field() -> None:
    """WR-01: token privacy value must be omitted by _CREDENTIAL_PRIVACY_VALUES."""
    cur = _dc(
        "webhook-notif",
        fields=[FieldKV(name="token", value="***REDACTED***", privacy="token")],
    )
    des = _dc(
        "webhook-notif",
        fields=[FieldKV(name="token", value="", privacy="token")],
    )
    result = merge_fields_for_put(cur, des)
    field_names = {f["name"] for f in result["fields"]}
    assert "token" not in field_names, (
        "WR-01: privacy=token field must be OMITTED from PUT body"
    )
```

---

### `tools/arrconf/tests/test_reconcilers_sonarr.py` (test, CRUD — extend with new resource cases)

**Analog:** self (lines 67-91 — `test_add_new_download_client` as template for new resource add tests)

**Base URL and decorator pattern** (used on every test, lines 32 / 67):
```python
@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_add_new_<resource>(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
```

**Mock URL regex pattern for PUT** (lines 103-105 — CRITICAL: allow optional query string):
```python
respx_mock.put(
    url__regex=r"^http://sonarr\.test/api/v3/<resource>/\d+(?:\?.*)?$"
).mock(return_value=httpx.Response(200, json={"id": 1, "name": "..."}))
```

**New conftest fixtures to add** (`tests/conftest.py`):
```python
@pytest.fixture
def sonarr_indexer_fixture() -> list[dict[str, Any]]:
    return json.loads((FIXTURE_ROOT / "sonarr/indexer.json").read_text())

@pytest.fixture
def sonarr_notification_fixture() -> list[dict[str, Any]]:
    return json.loads((FIXTURE_ROOT / "sonarr/notification.json").read_text())

@pytest.fixture
def sonarr_rootfolder_fixture() -> list[dict[str, Any]]:
    return json.loads((FIXTURE_ROOT / "sonarr/rootfolder.json").read_text())

@pytest.fixture
def sonarr_hostconfig_fixture() -> dict[str, Any]:
    return json.loads((FIXTURE_ROOT / "sonarr/config_host.json").read_text())
```

**host_config opt-in gate test** (new pattern — singleton, not list):
```python
@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_host_config_skipped_when_enable_false(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """D-03-04: host_config with enable=False → no GET /config/host called."""
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=sonarr_tag_managed_fixture))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=[]))
    get_host_route = respx_mock.get("/config/host")

    instance = SonarrInstance(
        base_url="http://sonarr.test",
        host_config=HostConfigSection(enable=False),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(client, instance, dry_run=False)

    assert get_host_route.call_count == 0
```

---

### `tools/arrconf/tests/test_reconcilers_radarr.py` (test, CRUD — new file)

**Analog:** `tools/arrconf/tests/test_reconcilers_sonarr.py` (full file)

**Imports pattern** (sonarr test lines 1-19, substitute Radarr):
```python
"""Tests for arrconf.reconcilers.radarr.reconcile_radarr — REQ-app-coverage."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from arrconf.client_base import RadarrClient
from arrconf.config import DownloadClientsSection, RadarrInstance
from arrconf.differ import Action
from arrconf.reconcilers.radarr import reconcile_radarr
from arrconf.resources.sonarr.download_client import DownloadClient
```

**Base URL constant** (different from Sonarr):
```python
RADARR_BASE = "http://radarr.test"
# All @pytest.mark.respx(base_url="http://radarr.test/api/v3", ...)
```

**Test structure per resource type** — replicate the six cases from sonarr tests for each of: download_clients, indexers, root_folders, notifications, host_config:
- `test_add_new_<resource>`
- `test_update_existing_<resource>`
- `test_<resource>_no_op`
- `test_<resource>_prune_skip_default`
- `test_<resource>_dry_run`
- `test_host_config_skipped_when_enable_false` (host_config only)

**respx regex pattern** — same as sonarr tests (Pitfall 7):
```python
url__regex=r"^http://radarr\.test/api/v3/<resource>/\d+(?:\?.*)?$"
```

---

### `tools/arrconf/tests/test_reconcilers_prowlarr.py` (test, CRUD — new file)

**Analog:** `tools/arrconf/tests/test_reconcilers_sonarr.py` (role-match — simpler, no managed tag)

**Imports pattern**:
```python
"""Tests for arrconf.reconcilers.prowlarr.reconcile_prowlarr — REQ-app-coverage."""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import patch

import httpx
import pytest
import respx

from arrconf.client_base import ProwlarrClient
from arrconf.config import ProwlarrInstance, AppsSection
from arrconf.differ import Action
from arrconf.reconcilers.prowlarr import reconcile_prowlarr
from arrconf.resources.prowlarr.application import Application
```

**Key difference from sonarr tests — Prowlarr uses /api/v1**:
```python
@pytest.mark.respx(base_url="http://prowlarr.test/api/v1", assert_all_called=False)
def test_prowlarr_uses_api_v1_path(
    respx_mock: respx.MockRouter,
) -> None:
    """Pitfall 3: ProwlarrClient must request /api/v1/applications, not /api/v3/."""
    get_route = respx_mock.get("/applications").mock(return_value=httpx.Response(200, json=[]))
    with patch.dict(os.environ, {"SONARR_API_KEY": "test-key"}):
        client = ProwlarrClient(base_url="http://prowlarr.test", api_key="fake")
        # reconcile_prowlarr call...
    assert get_route.call_count == 1
    assert "/api/v1/applications" in str(get_route.calls.last.request.url)
```

**API key env injection test** (Pitfall 5):
```python
def test_missing_api_key_env_raises_reconcile_error(
    respx_mock: respx.MockRouter,
) -> None:
    """Pitfall 5: missing env var for api_key_env raises ReconcileError before any PUT."""
    respx_mock.get("/applications").mock(return_value=httpx.Response(200, json=[]))
    # Do NOT set SONARR_API_KEY in env
    instance = ProwlarrInstance(
        base_url="http://prowlarr.test",
        apps=AppsSection(items=[...]),  # app with api_key_env="SONARR_API_KEY"
    )
    from arrconf.exceptions import ReconcileError
    with pytest.raises(ReconcileError, match="SONARR_API_KEY"):
        reconcile_prowlarr(client, instance, dry_run=False)
```

**conftest fixture to add**:
```python
@pytest.fixture
def prowlarr_applications_fixture() -> list[dict[str, Any]]:
    return json.loads((FIXTURE_ROOT / "prowlarr/applications.json").read_text())
```

---

## Shared Patterns

### 1. Pydantic Resource Model Structure
**Source:** `tools/arrconf/arrconf/resources/sonarr/download_client.py` lines 39-79
**Apply to:** All new resource models (`Indexer`, `Notification`, `RootFolder`, `HostConfig`, `Application`)

Key rules:
- `model_config = ConfigDict(extra="allow")` on all API-parsing models
- `fields: list[FieldKV]` for `fields[]`-bearing resources — import `FieldKV` from `download_client.py`, never re-declare
- All server-assigned read-only fields: `Field(default=None, exclude=True)` — this makes `model_dump(exclude_none=True)` automatically skip them in PUT bodies
- `id` is always `exclude=True`

### 2. respx Mock URL Regex for PUT with forceSave
**Source:** `tools/arrconf/tests/test_reconcilers_sonarr.py` lines 103-105
**Apply to:** ALL UPDATE tests in all three reconciler test files

```python
respx_mock.put(
    url__regex=r"^http://<app>\.test/api/v3/<resource>/\d+(?:\?.*)?$"
).mock(return_value=httpx.Response(200, json={"id": 1, "name": "..."}))
```
The `(?:\?.*)?$` suffix is mandatory — PUT carries `?forceSave=true` (Pitfall 7).

### 3. `_ensure_managed_tag` Pattern
**Source:** `tools/arrconf/arrconf/reconcilers/sonarr.py` lines 43-61
**Apply to:** `reconcilers/radarr.py` (copy verbatim, change `SonarrClient` → `RadarrClient`)
**NOT applied to:** `reconcilers/prowlarr.py` (Prowlarr has no managed-tag concept)

### 4. `_execute` / `execute_plan` Generic Executor
**Source:** `tools/arrconf/arrconf/reconcilers/sonarr.py` lines 74-111
**Apply to:** All three reconcilers — either via extraction to `differ.py` or verbatim copy per-reconciler
**Critical:** `body["id"] = p.current.id` re-injection at line 103 must be preserved (Pitfall 4)

### 5. ScopeViolationError Guard
**Source:** `tools/arrconf/arrconf/resources/sonarr/quality_profile.py` lines 1-17
**Apply to:** Any `resources/radarr/quality_profile.py` (and related frontière modules) if created
**Test extension:** `tests/test_scope_violation.py` `FRONTIERE_MODULES` list must include Radarr equivalents

### 6. Structured Logging Event Names
**Source:** `tools/arrconf/arrconf/reconcilers/sonarr.py` lines 52, 57, 59 + `differ.py` lines 190-211
**Apply to:** All new reconcilers and the `_reconcile_host_config` helper

Convention:
- `log.info("managed_tag_found", id=...)` — present tense for facts
- `log.info("plan_action", action="add", name=...)` — from `differ.py` (don't re-log in reconcilers)
- `log.info("dry_run_skip", action=..., name=...)` — standard dry-run format
- `log.info("host_config_reconcile_skipped")` — skip events use `_skipped` suffix
- Event VALUES are metadata-only — no credential values in log payloads (T-02.2-08-01)

### 7. `pyproject.toml` Coverage Source Update
**Source:** `tools/arrconf/pyproject.toml` line 57
**Apply to:** After radarr.py and prowlarr.py are created

```toml
# FROM:
source = ["arrconf.differ", "arrconf.reconcilers.sonarr"]
# TO:
source = ["arrconf.differ", "arrconf.reconcilers.sonarr", "arrconf.reconcilers.radarr", "arrconf.reconcilers.prowlarr"]
```

---

## No Analog Found

All files have close analogs. No entries in this section.

---

## Fixture Files Needed (New)

These JSON fixtures do not yet exist and must be created from live snapshots:

| Fixture Path | Source Snapshot | Notes |
|---|---|---|
| `tests/fixtures/sonarr/indexer.json` | `snapshots/baseline-2026-05-07/sonarr/indexer.json` | Sanitize apiKey fields → `***REDACTED***` |
| `tests/fixtures/sonarr/notification.json` | `snapshots/baseline-2026-05-07/sonarr/notification.json` | Sanitize credential fields |
| `tests/fixtures/sonarr/rootfolder.json` | `snapshots/baseline-2026-05-07/sonarr/rootfolder.json` | No secrets |
| `tests/fixtures/sonarr/config_host.json` | `snapshots/baseline-2026-05-07/sonarr/config_host.json` | Sanitize apiKey, password |
| `tests/fixtures/radarr/downloadclient.json` | `snapshots/baseline-2026-05-07/radarr/downloadclient.json` | Same shape as Sonarr |
| `tests/fixtures/radarr/indexer.json` | `snapshots/baseline-2026-05-07/radarr/indexer.json` | Same shape as Sonarr |
| `tests/fixtures/radarr/notification.json` | `snapshots/baseline-2026-05-07/radarr/notification.json` | Note Radarr-specific `on*` fields |
| `tests/fixtures/radarr/rootfolder.json` | `snapshots/baseline-2026-05-07/radarr/rootfolder.json` | Same shape as Sonarr |
| `tests/fixtures/radarr/config_host.json` | `snapshots/baseline-2026-05-07/radarr/config_host.json` | Sanitize credentials |
| `tests/fixtures/prowlarr/applications.json` | `snapshots/baseline-2026-05-07/prowlarr/applications.json` | Sanitize apiKey fields |

All fixture files follow the naming convention `<app>_<resource>.json` OR are placed under `fixtures/<app>/` subdirectory (current sonarr pattern). Use the subdirectory layout (current convention: `fixtures/sonarr/downloadclient.json`).

---

## Metadata

**Analog search scope:** `tools/arrconf/arrconf/` and `tools/arrconf/tests/`
**Files scanned:** 23 source files + 6 fixture files + 2 snapshot directories
**Pattern extraction date:** 2026-05-11
**Snapshot references verified:** `snapshots/baseline-2026-05-07/sonarr/`, `snapshots/before-phase-2-2026-05-08/radarr/`
