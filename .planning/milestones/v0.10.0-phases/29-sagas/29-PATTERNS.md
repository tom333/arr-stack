# Phase 29: Sagas — Pattern Map

**Mapped:** 2026-05-31
**Files analyzed:** 8 new/modified files
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `tools/arrconf/arrconf/intent_config.py` | model | CRUD (schema tighten) | itself — `CrossSeedConfig` block (lines 26-51) | exact |
| `tools/arrconf/arrconf/resources/radarr/collection.py` | model | CRUD | `tools/arrconf/arrconf/resources/sonarr/root_folder.py` | exact (same pattern: id + read-only excludes) |
| `tools/arrconf/arrconf/generators/sagas.py` | utility | transform | `tools/arrconf/arrconf/generators/categories.py` | exact |
| `tools/arrconf/arrconf/reconcilers/radarr.py` (new fn) | service | request-response | itself — `_reconcile_list_resource`, `_execute`, `_reconcile_movie_tags` | exact |
| `tools/arrconf/arrconf/reconcilers/jellyfin.py` (new fn) | service | request-response | itself — `_reconcile_libraries` (Pitfall 16-1), `_reconcile_plugins` (two-run) | exact |
| `tools/arrconf/arrconf/__main__.py` (apply wiring) | controller | request-response | itself — Jellyfin branch (lines 442-472) | exact |
| `tools/arrconf/tests/test_*sagas*.py` | test | request-response | `tests/test_reconcilers_radarr.py`, `tests/test_reconcilers_jellyfin_plugin_install.py` | exact |
| `schemas/intent-schema.json` | config | transform | itself (regenerated via `arrconf intent-schema-gen`) | exact |

---

## Pattern Assignments

### `tools/arrconf/arrconf/intent_config.py` — tighten `SagaEntry` (model, schema)

**Analog:** the same file, `CrossSeedConfig` block (lines 26-51)

**Current stub to replace** (`intent_config.py` lines 64-76):
```python
class SagaEntry(BaseModel):
    # relaxed until P29 locks the schema — do NOT tighten here
    model_config = ConfigDict(extra="allow")
    name: str = Field(description="Saga name. Full schema locked in Phase 29 (SAGAS).")
```

**Imports pattern** (lines 1-24, copy as-is — only `Literal` and `model_validator` need adding):
```python
from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from ruyaml import YAML
from arrconf.exceptions import ConfigError
```
Add `from typing import Literal` alongside the existing `from __future__ import annotations`.

**Locked SagaEntry pattern** (replace lines 64-76 entirely):
```python
class SagaEntry(BaseModel):
    """A single saga declaration (Phase 29 locked schema — D-02).

    kind=movies: tmdb_collection REQUIRED; profile + root REQUIRED; items ignored.
    kind=series: items OPTIONAL (exact series titles for Jellyfin BoxSet); profile/root/tmdb_collection unused.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Saga display name; also the Jellyfin BoxSet name for series.")
    kind: Literal["movies", "series"] = Field(description="Discriminator.")
    tmdb_collection: int | None = Field(
        default=None,
        description="TMDB collection id. Required when kind=movies.",
    )
    profile: str = Field(
        default="",
        description="Radarr quality profile name. Required when kind=movies.",
    )
    root: str = Field(
        default="",
        description="Radarr root folder path. Required when kind=movies.",
    )
    items: list[str] | None = Field(
        default=None,
        description="Series titles for Jellyfin BoxSet membership. kind=series only.",
    )

    @model_validator(mode="after")
    def check_kind_constraints(self) -> "SagaEntry":
        if self.kind == "movies" and self.tmdb_collection is None:
            raise ValueError("tmdb_collection is required when kind=movies")
        if self.kind == "movies" and not self.profile:
            raise ValueError("profile is required when kind=movies")
        if self.kind == "movies" and not self.root:
            raise ValueError("root is required when kind=movies")
        return self
```

**load_intent pattern** (lines 98-116, unchanged — copy verbatim as the error-handling pattern):
```python
def load_intent(path: Path) -> IntentConfig:
    if not path.exists():
        raise ConfigError(f"Intent file not found: {path}")
    yaml = YAML(typ="safe")
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.load(f) or {}
    except Exception as e:
        raise ConfigError(f"YAML parse error in {path}: {e}") from e
    try:
        cfg = IntentConfig.model_validate(raw)
    except ValidationError as e:
        raise ConfigError(f"Intent validation error in {path}: {e}") from e
    return cfg
```

---

### `tools/arrconf/arrconf/resources/radarr/collection.py` (NEW, model, CRUD)

**Analog:** `tools/arrconf/arrconf/resources/sonarr/root_folder.py` (lines 1-31)

**Pattern:** `extra="allow"` (API returns extra fields like `movies[]`, `images[]`); reconciled fields are plain attrs; read-only/server-computed fields use `Field(default=None, exclude=True)`.

**Imports pattern** (mirror root_folder.py lines 1-18):
```python
"""Radarr CollectionResource pydantic schema (Phase 29 — SAGAS-02).

Matched by ``tmdbId`` (stable identity — see D-03).
GET /api/v3/collection → PUT /api/v3/collection/{id} on drift.
No POST endpoint (Radarr auto-discovers collections when ≥1 member movie exists).

Read-only / server-computed fields excluded so diff_models does NOT flag them.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
```

**Core schema pattern**:
```python
class CollectionResource(BaseModel):
    """A Radarr auto-discovered collection. ``tmdbId`` is the stable match key."""

    model_config = ConfigDict(extra="allow")

    # Stable identity (match key for reconcile — analogous to RootFolder.path)
    tmdbId: int = Field(description="TMDB collection id. Match key.")

    # Reconciled fields (arrconf owns these — PUT on drift)
    monitored: bool = Field(default=True)
    qualityProfileId: int = Field(default=0)
    rootFolderPath: str = Field(default="")
    searchOnAdd: bool = Field(default=True)
    minimumAvailability: str = Field(default="released")

    # Server-assigned / read-only — excluded from diff to avoid spurious UPDATE
    id: int | None = Field(default=None, exclude=True)
    title: str | None = Field(default=None, exclude=True)
    sortTitle: str | None = Field(default=None, exclude=True)
    missingMovies: int | None = Field(default=None, exclude=True)
    movies: list | None = Field(default=None, exclude=True)
    images: list | None = Field(default=None, exclude=True)
    tags: list | None = Field(default=None, exclude=True)
```

**Key rule:** The `id` field must be `exclude=True` for diff purposes (same as `RootFolder.id`) but MUST be re-injected in the PUT body (Pitfall 4 / Pitfall 1 from Radarr reconciler). Retrieve from raw cluster dict: `body["id"] = cluster["id"]`.

---

### `tools/arrconf/arrconf/generators/sagas.py` (NEW, utility, transform)

**Analog:** `tools/arrconf/arrconf/generators/categories.py` (entire file)

**Imports pattern** (mirror categories.py lines 1-27):
```python
"""Phase 29 saga generators — pure-function module (D-01 / INTENT-02).

Expands ``IntentConfig.sagas`` into per-app desired resources for
Radarr Collections and Jellyfin BoxSets.

Key invariants:
- No I/O, no httpx, no client calls.
- mypy --strict-compliant signatures throughout.
- kind=movies → Radarr Collections desired-state only (tmdbboxsets handles Jellyfin presentation).
- kind=series → Jellyfin BoxSet desired-state + Sonarr arrconf-managed tag list.
"""

from __future__ import annotations

from dataclasses import dataclass

from arrconf.intent_config import SagaEntry
```

**Typed container pattern** (mirror `SonarrDerived` / `RadarrDerived` dataclasses in categories.py lines 49-68):
```python
@dataclass
class SagasDesiredState:
    """Container for generated saga desired-state (D-01)."""
    radarr_collections: list[dict]      # desired fields for each kind=movies saga
    series_boxsets: list[SagaEntry]     # kind=series entries for Jellyfin BoxSet reconcile
    series_tag_titles: list[str]        # series titles needing arrconf-managed Sonarr tag
```

**Generator function pattern** (mirror `generate_sonarr_resources` lines 135-164):
```python
def generate_sagas_desired(sagas: list[SagaEntry]) -> SagasDesiredState:
    """D-01: SagaEntry list → per-app desired resources (pure, no I/O)."""
    movie_sagas = [s for s in sagas if s.kind == "movies"]
    series_sagas = [s for s in sagas if s.kind == "series"]

    radarr_collections = [
        {
            "tmdb_collection": s.tmdb_collection,
            "profile": s.profile,
            "root": s.root,
            "name": s.name,
        }
        for s in movie_sagas
    ]
    series_titles = [
        title
        for s in series_sagas
        for title in (s.items or [])
    ]
    return SagasDesiredState(
        radarr_collections=radarr_collections,
        series_boxsets=series_sagas,
        series_tag_titles=series_titles,
    )
```

**Export pattern** — add to `generators/__init__.py` (mirror lines 12-32 of that file):
```python
from arrconf.generators.sagas import SagasDesiredState, generate_sagas_desired

__all__ = [
    ...,  # existing exports
    "SagasDesiredState",
    "generate_sagas_desired",
]
```

---

### `tools/arrconf/arrconf/reconcilers/radarr.py` — new `reconcile_radarr_collections()` fn (service, request-response)

**Analogs:**
- `_reconcile_movie_tags` (lines 302-366) — direct dict-level field comparison without `diff_models`, uses `client._request("PUT", ...)` when the endpoint doesn't match `client.put(path, id, json)` signature
- `_execute` (lines 130-166) — dry_run skip + action string pattern
- `_ensure_managed_tag` (lines 104-117) — GET-then-match idiom

**Path constants to add** (mirror lines 83-91):
```python
COLLECTION_PATH = "/collection"
QUALITY_PROFILE_PATH = "/qualityprofile"
```

**Core reconcile function pattern** — explicit field-compare (NOT `diff_models`/`reconcile()` because CollectionResource is matched by `tmdbId` not a list-resource interface):
```python
def reconcile_radarr_collections(
    client: RadarrClient,
    sagas: list[SagaEntry],
    dry_run: bool,
) -> list[str]:
    """Reconcile Radarr Collections from kind=movies sagas (SAGAS-02).

    GET-match by tmdbId, PUT only on drift. Absent collections → log warning + skip (D-03).
    profile name → qualityProfileId via GET /qualityprofile name-match (D-06 / ConfigError if missing).
    Second run with no drift = 0 PUT calls (strict idempotence — D-07).
    """
    movie_sagas = [s for s in sagas if s.kind == "movies"]
    if not movie_sagas:
        return []

    # Resolve quality profile names → ids (read-only GET, no side effects)
    raw_qp = client.get(QUALITY_PROFILE_PATH)
    qp_by_name: dict[str, int] = {qp["name"]: qp["id"] for qp in raw_qp}

    # GET all collections, index by tmdbId (bulk fetch — mirrors _reconcile_content_tags pattern)
    raw_collections = client.get(COLLECTION_PATH)
    by_tmdb_id: dict[int, dict] = {c["tmdbId"]: c for c in raw_collections}

    actions: list[str] = []

    for saga in movie_sagas:
        assert saga.tmdb_collection is not None  # enforced by pydantic model_validator
        cluster = by_tmdb_id.get(saga.tmdb_collection)

        if cluster is None:
            # D-03: Radarr auto-discovers collections only when ≥1 member movie present
            log.warning(
                "collection_absent_skip",
                tmdb_collection=saga.tmdb_collection,
                saga_name=saga.name,
                hint="Add at least one movie from this collection to Radarr first",
            )
            continue

        if saga.profile not in qp_by_name:
            raise ConfigError(f"quality profile '{saga.profile}' not found in Radarr")
        quality_profile_id = qp_by_name[saga.profile]

        desired = {
            "monitored": True,
            "qualityProfileId": quality_profile_id,
            "rootFolderPath": saga.root,
            "searchOnAdd": True,
            "minimumAvailability": "released",
        }
        drift_fields = {k for k, v in desired.items() if cluster.get(k) != v}

        if not drift_fields:
            log.info("collection_no_op", saga_name=saga.name, tmdb_id=saga.tmdb_collection)
            continue

        if dry_run:
            log.info(
                "dry_run_skip",
                resource="collection",
                saga_name=saga.name,
                drift=sorted(drift_fields),
            )
            actions.append(f"collection:dry_run:{saga.name}")
            continue

        # Pitfall 1 (from radarr.py): start from cluster state, override desired fields,
        # re-inject id (Pitfall 4 pattern — same as _reconcile_host_config lines 244-252)
        body = dict(cluster)
        body.update(desired)
        body["id"] = cluster["id"]
        # PUT /api/v3/collection/{id} — use client._request (no forceSave param needed)
        client._request("PUT", f"{COLLECTION_PATH}/{cluster['id']}", json=body)
        log.info(
            "collection_updated",
            saga_name=saga.name,
            tmdb_id=saga.tmdb_collection,
            drift=sorted(drift_fields),
        )
        actions.append(f"collection:updated:{saga.name}")

    return actions
```

**Wiring into `reconcile_radarr()`** — add as step 11 AFTER all existing steps (mirrors the step_begin log pattern at lines 491-597):
```python
# Step 11: Saga Collections — MUST run after all existing steps (sagas reference
# quality profiles that configarr owns; we read but never write them — ADR-5 safe).
# Only called from __main__.py when intent_cfg is present (D-01).
```
The function is called from `__main__.py` directly (not from inside `reconcile_radarr`), keeping the saga data path separate from the `arrconf.yml` path.

**Import to add** (mirror existing imports block lines 44-80):
```python
from arrconf.intent_config import SagaEntry
from arrconf.exceptions import ConfigError  # already imported
```

---

### `tools/arrconf/arrconf/reconcilers/jellyfin.py` — new `_reconcile_sagas_boxsets()` fn (service, request-response)

**Analogs:**
- `_reconcile_libraries` (lines 328-381) — Pitfall 16-1 GET-before-POST name check; `by_name` dict snapshot pattern
- `_reconcile_plugins` (lines 503-625) — `client._request("POST", ...)` with params; dry_run branch; action string pattern
- `_add_missing_paths` (lines 166-202) — idempotent add-only loop pattern

**Path constants to add** (mirror lines 59-64):
```python
ITEMS_PATH = "/Items"
COLLECTIONS_PATH = "/Collections"
```

**Core new function pattern** — GET-before-POST idempotence (Pitfall 16-1 mirror):
```python
def _reconcile_sagas_boxsets(
    client: JellyfinClient,
    series_sagas: list[SagaEntry],
    dry_run: bool,
) -> list[str]:
    """Reconcile series-saga Jellyfin BoxSets (SAGAS-04).

    Idempotent contract:
    - POST /Collections is NOT idempotent alone → MUST check existing by name first
      (mirrors Pitfall 16-1 from _reconcile_libraries lines 354-367).
    - POST /Collections/{id}/Items IS idempotent (Jellyfin AddToCollectionAsync
      skips already-linked items by id check).
    - Best-effort: unresolved titles log warning + skip (ADR-9 spirit).
    """
    if not series_sagas:
        return []

    # Step 1: GET existing BoxSets — snapshot by name (Pitfall 16-1 mirror)
    raw_response = client.get(
        ITEMS_PATH,
        params={"includeItemTypes": "BoxSet", "recursive": "true", "fields": "Name,ProviderIds"},
    )
    existing_by_name: dict[str, str] = {
        item["Name"]: str(item["Id"])
        for item in raw_response.get("Items", [])
        if item.get("Name") and item.get("Id")
    }

    actions: list[str] = []
    for saga in series_sagas:
        # Step 2: Resolve member titles → Jellyfin item GUIDs
        resolved_ids: list[str] = []
        for title in (saga.items or []):
            results = client.get(
                ITEMS_PATH,
                params={
                    "includeItemTypes": "Series",
                    "recursive": "true",
                    "searchTerm": title,
                    "fields": "Name,ProviderIds",
                },
            )
            exact = next(
                (item for item in results.get("Items", []) if item.get("Name") == title),
                None,
            )
            if exact is None:
                log.warning(
                    "series_saga_member_unresolved",
                    saga_name=saga.name,
                    title=title,
                    hint="Check that the title in intent.yml matches Jellyfin library exactly",
                )
                continue
            resolved_ids.append(str(exact["Id"]))

        # Step 3: Create or idempotent-add
        if saga.name not in existing_by_name:
            # Pitfall 16-1 mirror: name absent → safe to POST /Collections
            if dry_run:
                log.info("dry_run_skip", resource="saga_boxset_create", saga_name=saga.name)
                actions.append(f"saga_boxset:dry_run_create:{saga.name}")
                continue
            client._request(
                "POST",
                COLLECTIONS_PATH,
                params={"name": saga.name, "ids": ",".join(resolved_ids)},
            )
            log.info("saga_boxset_created", saga_name=saga.name, member_count=len(resolved_ids))
            actions.append(f"saga_boxset:created:{saga.name}")
        else:
            # BoxSet exists: POST /{id}/Items is idempotent (add-only, skips existing)
            collection_id = existing_by_name[saga.name]
            if not resolved_ids:
                log.info("saga_boxset_no_op", saga_name=saga.name)
                continue
            if dry_run:
                log.info("dry_run_skip", resource="saga_boxset_items", saga_name=saga.name)
                actions.append(f"saga_boxset:dry_run_items:{saga.name}")
                continue
            client._request(
                "POST",
                f"{COLLECTIONS_PATH}/{collection_id}/Items",
                params={"ids": ",".join(resolved_ids)},
            )
            log.info("saga_boxset_items_added", saga_name=saga.name, member_count=len(resolved_ids))
            actions.append(f"saga_boxset:items_added:{saga.name}")

    return actions
```

**Import to add**:
```python
from arrconf.intent_config import SagaEntry
```

**Wiring into `reconcile_jellyfin()`** — the function is called from `__main__.py` directly (not from `reconcile_jellyfin`) to keep the intent data path clean from the config data path. The `_reconcile_sagas_boxsets` function is a standalone helper in `jellyfin.py`.

**`_reconcile_plugins` client._request pattern** (lines 543-560) — exact shape to copy for POST /Collections:
```python
client._request(
    "POST",
    f"{PACKAGES_INSTALLED_PATH}/{entry.name}",
    params={
        "assemblyGuid": entry.install_guid,
        "version": entry.install_version,
        "repositoryUrl": entry.install_repo_url,
    },
)
```

**`client.get()` with params** — `_reconcile_sagas_boxsets` calls `client.get(path, params={...})`. Verify `ArrApiClient.get` passes `**kwargs` to `_request` (line 95: `return self._request("GET", path, **kwargs).json()`). The `params` kwarg threads through to httpx — confirmed pattern used in `_reconcile_libraries` line 353.

---

### `tools/arrconf/arrconf/__main__.py` — apply-time intent.yml wiring (controller, request-response)

**Analog:** the Jellyfin branch (lines 442-472) + the callback (lines 178-196)

**Step 1: Add `--intent` option to `main()` callback** (mirror `--config` at lines 179-196):
```python
@app.callback()
def main(
    ctx: typer.Context,
    config: Path = typer.Option(
        Path("/etc/arrconf/arrconf.yml"),
        "--config",
        "-c",
        help="Path to arrconf YAML config",
    ),
    intent: Path = typer.Option(           # NEW
        Path("/etc/arrconf/intent.yml"),
        "--intent",
        "-i",
        help="Path to intent.yml (sagas, tools). Optional — skipped if absent.",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        "-l",
        envvar="ARRCONF_LOG_LEVEL",
    ),
) -> None:
    configure_logging(log_level)
    ctx.obj = {"config_path": config, "intent_path": intent}   # add intent_path
```

**Step 2: Load intent at the top of `apply()`** (after `load_config` at line 208, mirror the ConfigError pattern lines 208-214):
```python
@app.command()
def apply(ctx: typer.Context, apps: str | None = ..., dry_run: bool = ...) -> None:
    log = structlog.get_logger()
    try:
        root = load_config(ctx.obj["config_path"])
    except ConfigError as e:
        ...

    # NEW: load intent (optional — backward-compatible; absent intent.yml = no sagas)
    intent_path: Path = ctx.obj["intent_path"]
    intent_cfg: IntentConfig | None = None
    if intent_path.exists():
        try:
            intent_cfg = load_intent(intent_path)
        except ConfigError as e:
            log.error("intent_config_error", error=str(e))
            raise typer.Exit(code=2) from e
```

**Step 3: Saga branches AFTER all existing app branches** (after Jellyfin block lines 442-472, before `if failures:` at line 474):
```python
    # Phase 29: Saga branches — run AFTER all existing app branches (D-07 ordering)
    if intent_cfg is not None and intent_cfg.sagas:
        # SAGAS-02: Radarr Collections reconcile (kind=movies only)
        if "radarr" in targets and "main" in root.radarr and settings.radarr_api_key:
            try:
                from arrconf.reconcilers.radarr import reconcile_radarr_collections  # noqa: PLC0415
                radarr_saga_client = RadarrClient(
                    base_url=root.radarr["main"].base_url,
                    api_key=settings.radarr_api_key.get_secret_value(),
                )
                saga_actions = reconcile_radarr_collections(
                    radarr_saga_client,
                    intent_cfg.sagas,
                    dry_run=dry_run or settings.arrconf_dry_run,
                )
                log.info("apply_complete", app="radarr_collections", actions=saga_actions)
            except (ApiClientError, ReconcileError) as e:
                log.error("app_failed", app="radarr_collections", error=str(e))
                failures.append("radarr_collections")

        # SAGAS-04: Jellyfin series BoxSets
        if "jellyfin" in targets and "main" in root.jellyfin and settings.jellyfin_api_key:
            try:
                from arrconf.reconcilers.jellyfin import _reconcile_sagas_boxsets  # noqa: PLC0415
                jellyfin_saga_client = JellyfinClient(
                    base_url=root.jellyfin["main"].base_url,
                    api_key=settings.jellyfin_api_key.get_secret_value(),
                )
                series_sagas = [s for s in intent_cfg.sagas if s.kind == "series"]
                saga_box_actions = _reconcile_sagas_boxsets(
                    jellyfin_saga_client,
                    series_sagas,
                    dry_run=dry_run or settings.arrconf_dry_run,
                )
                log.info("apply_complete", app="jellyfin_sagas", actions=saga_box_actions)
            except (ApiClientError, ReconcileError) as e:
                log.error("app_failed", app="jellyfin_sagas", error=str(e))
                failures.append("jellyfin_sagas")
```

**Import to add at top** (mirrors line 37):
```python
from arrconf.intent_config import IntentConfig, load_intent   # IntentConfig is new
```

**Note:** `load_intent` is already imported at line 37; add `IntentConfig` to the same import.

---

### `tools/arrconf/tests/test_*sagas*.py` — new test files (test, request-response)

**Analog:** `tests/test_reconcilers_radarr.py` (entire file) + `tests/test_reconcilers_jellyfin_plugin_install.py` (entire file)

**File header + imports pattern** (copy from `test_reconcilers_radarr.py` lines 1-49):
```python
"""Tests for arrconf.reconcilers.radarr.reconcile_radarr_collections — SAGAS-02.

All HTTP mocked via respx. Coverage gate enforced via pyproject.toml.
Fixtures loaded inline (no conftest.py changes — keeps plans parallelizable).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
import structlog.testing

from arrconf.client_base import RadarrClient
from arrconf.intent_config import SagaEntry
from arrconf.reconcilers.radarr import reconcile_radarr_collections

RADARR_BASE = "http://radarr.test"
```

**respx mock pattern for GET /collection** (mirror `_mock_radarr_gets` lines 62-95):
```python
@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_collection_no_op_when_fields_match(respx_mock: respx.MockRouter) -> None:
    respx_mock.get("/collection").mock(
        return_value=httpx.Response(200, json=[FIXTURE_COLLECTION])
    )
    respx_mock.get("/qualityprofile").mock(
        return_value=httpx.Response(200, json=[{"id": 3, "name": "MULTi.VF"}])
    )
    # No PUT expected — assert_all_called=False + no put route registered
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    saga = SagaEntry(name="James Bond", kind="movies", tmdb_collection=645,
                     profile="MULTi.VF", root="/media/films")
    actions = reconcile_radarr_collections(client, [saga], dry_run=False)
    assert actions == []
```

**respx mock pattern for PUT /collection/{id}** (mirror `test_update_existing_download_client_uses_forceSave` lines 151-179):
```python
@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_collection_put_on_drift(respx_mock: respx.MockRouter) -> None:
    drifted = dict(FIXTURE_COLLECTION)
    drifted["monitored"] = False   # drift
    respx_mock.get("/collection").mock(return_value=httpx.Response(200, json=[drifted]))
    respx_mock.get("/qualityprofile").mock(
        return_value=httpx.Response(200, json=[{"id": 3, "name": "MULTi.VF"}])
    )
    put_route = respx_mock.put(
        url__regex=rf"^{RADARR_BASE}/api/v3/collection/\d+(?:\?.*)?$"
    ).mock(return_value=httpx.Response(202, json={"id": 1}))

    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    saga = SagaEntry(name="James Bond", kind="movies", tmdb_collection=645,
                     profile="MULTi.VF", root="/media/films")
    actions = reconcile_radarr_collections(client, [saga], dry_run=False)
    assert put_route.call_count == 1
    assert any("updated" in a for a in actions)
```

**Jellyfin BoxSet respx pattern** (mirror `test_reconcilers_jellyfin_plugin_install.py` lines 1-45 for boilerplate; then):
```python
JELLYFIN_BASE = "http://jellyfin.test:8096"

@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_boxset_created_when_absent(respx_mock: respx.MockRouter) -> None:
    # GET /Items?includeItemTypes=BoxSet → empty
    respx_mock.get("/Items").mock(
        return_value=httpx.Response(200, json={"Items": [], "TotalRecordCount": 0})
    )
    # POST /Collections → created
    post_route = respx_mock.post("/Collections").mock(
        return_value=httpx.Response(200, json={"Id": "aabbccdd-..."})
    )
    client = JellyfinClient(base_url=JELLYFIN_BASE, api_key="fake")
    saga = SagaEntry(name="Star Wars", kind="series", items=[])
    actions = _reconcile_sagas_boxsets(client, [saga], dry_run=False)
    assert post_route.call_count == 1
    assert any("created" in a for a in actions)
```

**Fixture file location pattern** (mirror `FIXTURE_ROOT` line 45):
```python
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "radarr"
# For collection: tests/fixtures/radarr/collection.json
```

**Fixture template** (from RESEARCH.md — use this JSON in `tests/fixtures/radarr/collection.json`):
```json
{
  "id": 1,
  "title": "James Bond Collection",
  "sortTitle": "james bond collection",
  "tmdbId": 645,
  "monitored": true,
  "qualityProfileId": 3,
  "rootFolderPath": "/media/films",
  "searchOnAdd": true,
  "minimumAvailability": "released",
  "missingMovies": 0,
  "movies": [],
  "tags": [],
  "images": []
}
```

---

## Shared Patterns

### Structured logging (apply to all new reconciler functions)
**Source:** `tools/arrconf/arrconf/reconcilers/radarr.py` lines 81, 107-117
```python
import structlog
log = structlog.get_logger()

# no-op
log.info("collection_no_op", saga_name=saga.name, tmdb_id=saga.tmdb_collection)
# warning
log.warning("collection_absent_skip", tmdb_collection=..., saga_name=..., hint="...")
# dry-run skip
log.info("dry_run_skip", resource="collection", saga_name=saga.name, drift=sorted(drift_fields))
# action taken
log.info("collection_updated", saga_name=saga.name, tmdb_id=..., drift=...)
```

### Error handling — ConfigError for missing profile (apply to `reconcile_radarr_collections`)
**Source:** `tools/arrconf/arrconf/reconcilers/radarr.py` lines 343-347
```python
from arrconf.exceptions import ConfigError

if saga.profile not in qp_by_name:
    raise ConfigError(f"quality profile '{saga.profile}' not found in Radarr")
```

### Action string format (apply to all new reconciler functions)
**Source:** `tools/arrconf/arrconf/reconcilers/radarr.py` lines 151-165
```python
actions_taken.append(f"add:{p.name}")       # existing pattern
actions.append(f"collection:updated:{saga.name}")  # new pattern for sagas
actions.append(f"saga_boxset:created:{saga.name}")
```

### dry_run gate (apply to every mutating call)
**Source:** `tools/arrconf/arrconf/reconcilers/radarr.py` lines 144-146
```python
if dry_run:
    log.info("dry_run_skip", action=p.action.value, name=p.name)
    continue
```

### client._request for endpoints without `client.put(path, id, json)` shape
**Source:** `tools/arrconf/arrconf/reconcilers/radarr.py` line 364
```python
client._request("PUT", MOVIE_EDITOR_PATH, json=body)
# For collections PUT:
client._request("PUT", f"{COLLECTION_PATH}/{cluster['id']}", json=body)
# For Jellyfin POST:
client._request("POST", COLLECTIONS_PATH, params={"name": saga.name, "ids": ","join(ids)})
```

### Two-run plugin model — tmdbboxsets wiring (SAGAS-03)
**Source:** `tools/arrconf/arrconf/reconcilers/jellyfin.py` lines 503-625
No new code needed. Add the tmdbboxsets entry to `arrconf.yml` `jellyfin.main.plugins.required`:
```yaml
- name: "TMDb Box Sets"
  install_guid: "bc4aad2e-d3d0-4725-a5e2-fd07949e5b42"
  install_version: "13.0.0.0"
  install_repo_url: "https://repo.jellyfin.org/files/plugin/manifest.json"
```
The existing `_reconcile_plugins` handles install (Run N) → enable (Run N+1) automatically.

### ConfigDict(extra="forbid") on SagaEntry
**Source:** `tools/arrconf/arrconf/intent_config.py` lines 29, 54, 86
Every top-level IntentConfig model uses `extra="forbid"`. SagaEntry must switch from P28's `extra="allow"` to `extra="forbid"`.

---

## No Analog Found

No files are without an analog — all 8 files have exact or near-exact analogs within the codebase.

---

## Metadata

**Analog search scope:** `tools/arrconf/arrconf/`, `tools/arrconf/tests/`
**Files scanned:** 15 (intent_config.py, generators/categories.py, generators/__init__.py, reconcilers/radarr.py, reconcilers/jellyfin.py, __main__.py, resources/radarr/quality_profile.py, resources/radarr/__init__.py, resources/sonarr/root_folder.py, resources/jellyfin/plugin.py, tests/test_reconcilers_radarr.py, tests/test_reconcilers_jellyfin_plugin_install.py, tests/test_client_base_4xx_logging.py, client_base.py, generators/intent.py)
**Pattern extraction date:** 2026-05-31
