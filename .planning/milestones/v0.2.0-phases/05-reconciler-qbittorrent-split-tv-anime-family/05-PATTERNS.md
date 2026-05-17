# Phase 5: Reconciler qBittorrent + split tv/anime/family — Pattern Map

**Mapped:** 2026-05-14
**Files analyzed:** 26 new/touched files (12 NEW python + 6 MODIFIED python + 5 NEW tests + 3 MODIFIED tests + 6 NEW fixtures + 4 chart files + 1 schema regen + 1 snapshot dir)
**Analogs found:** 23 / 26 (3 truly net-new types: `QbittorrentClient`, `_reconcile_series_tags` editor pattern, `_reconcile_remote_path_mappings` composite-key)

---

## File Classification

### Python — arrconf source (`tools/arrconf/arrconf/`)

| New/Modified File | Status | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|--------|------|-----------|----------------|---------------|
| `arrconf/client_base.py` (appended `QbittorrentClient`) | MODIFIED | http-client (auth subclass) | request-response (cookie-auth login + form-POST) | `arrconf/client_base.py::ArrApiClient` (lines 29–98) | role-match — same get/post/delete shape, divergent auth lifecycle |
| `arrconf/reconcilers/qbittorrent.py` | NEW | reconciler (entrypoint) | CRUD (categories) + singleton (preferences) | `arrconf/reconcilers/prowlarr.py` (simplest existing reconciler — single resource list) | exact — same `reconcile_X(client, instance, dry_run) -> Result` signature, same `_execute` pattern; preferences mirrors `_reconcile_host_config` (singleton opt-in) |
| `arrconf/resources/qbittorrent/__init__.py` | NEW | package marker | n/a | `arrconf/resources/prowlarr/__init__.py` | exact |
| `arrconf/resources/qbittorrent/category.py` | NEW | pydantic resource (list item, match by `name`) | data-model | `arrconf/resources/sonarr/tag.py` (smallest two-field model with `extra="allow"`) | exact — two fields (`name`, `savePath`), `extra="allow"` for forward-compat |
| `arrconf/resources/qbittorrent/preferences.py` | NEW | pydantic resource (singleton, opt-in) | data-model | `arrconf/resources/sonarr/host_config.py` (singleton, credential-exclusion, `extra="allow"`) | role-match — same singleton shape; differs: `extra="forbid"` allowlist not allow, and no credential fields |
| `arrconf/resources/sonarr/remote_path_mapping.py` | NEW | pydantic resource (list, composite-key, no PUT) | data-model | `arrconf/resources/sonarr/root_folder.py` (no-PUT, server-derived id excluded) | exact — same "list with no PUT endpoint" shape (DELETE+ADD on update, Pitfall 1) |
| `arrconf/reconcilers/sonarr.py` (extended) | MODIFIED | reconciler (extends with 3 sub-reconcilers) | CRUD + bulk-editor + composite-key | self (existing `reconcile_sonarr`, lines 245–329) | exact — appends `_reconcile_remote_path_mappings`, tags-section list reconcile, `_reconcile_series_tags` |
| `arrconf/reconcilers/radarr.py` (extended) | MODIFIED | reconciler (mirror of Sonarr) | same as Sonarr | self (mirror of Sonarr); `arrconf/reconcilers/sonarr.py` post-modification | exact — every Sonarr addition replicates here, with `/movie/editor` and `default_tag="movies"` |
| `arrconf/config.py` (extended) | MODIFIED | pydantic config schema | data-model | self (existing sections in `config.py`, lines 33–207) | exact — new `TagsSection`/`RemotePathMappingsSection`/`SeriesTagsSection`/`MovieTagsSection`/`QbittorrentInstance`/`PreferencesSection` follow the same pattern as `DownloadClientsSection`/`IndexersSection` (extra=forbid, prune: bool, items: list[T]). `QbittorrentInstance` mirrors `ProwlarrInstance` (simplest existing instance) |
| `arrconf/__main__.py` (extended) | MODIFIED | CLI entrypoint | request-response | self (existing Prowlarr branch lines 167–190) | exact — add qBittorrent branch + extend `_VALID_APPS` |
| `arrconf/diff_cmd.py` (extended) | MODIFIED | dry-run wrapper | request-response | `arrconf/diff_cmd.py::diff_prowlarr` (lines 56–75) | exact — add `diff_qbittorrent` mirror |
| `arrconf/settings.py` (extended) | MODIFIED | env-var loader | data-model | self (existing `Settings`, lines 9–25) | exact — add `qbt_user: SecretStr \| None`, `qbt_pass: SecretStr \| None` |
| `arrconf/dump.py` (extended) | MODIFIED | YAML emitter (read-only) | streaming | `arrconf/dump.py::dump_sonarr` (lines 48–102) | exact — add `dump_qbittorrent` analogue (optional, deferred-ok per CONTEXT.md `dump` Phase 3-only) |
| `arrconf/exceptions.py` | UNCHANGED | n/a | n/a | `AuthError`, `ApiClientError`, `ReconcileError` already cover qBit auth + reconcile failures | exact |

### Python — tests (`tools/arrconf/tests/`)

| New/Modified File | Status | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|--------|------|-----------|----------------|---------------|
| `tests/test_reconcilers_qbittorrent.py` | NEW | test (reconciler) | request-response (respx mock) | `tests/test_reconcilers_prowlarr.py` (single-resource reconciler, simplest test shape) | exact — same `respx.MockRouter` + fixture-load + `_build_X` helper pattern. login mock is new. |
| `tests/test_series_editor.py` | NEW | test (bulk editor, D-05-MIG-01) | request-response (respx) | `tests/test_reconcilers_sonarr.py::test_add_new_download_client` (lines 101–124) | role-match — closest pattern is respx PUT-body assertion; new shape: `applyTags="add"`, single-PUT-for-N-IDs |
| `tests/test_remote_path_mapping.py` | NEW | test (RPM reconciler) | request-response (respx) | `tests/test_reconcilers_sonarr.py` root_folder section (Pitfall 1 — DELETE+ADD pattern) | exact — root_folder is the closest "no-PUT resource" precedent in tests |
| `tests/conftest.py` (extended) | MODIFIED | fixture loader | data-model | self (existing pattern, lines 51–94) | exact — add `qbit_categories_fixture`, `qbit_preferences_fixture`, `sonarr_series_with_no_tags_fixture`, `radarr_movies_with_no_tags_fixture` via `_load_fixture(...)` helper |
| `tests/test_config.py` (extended) | MODIFIED | test (schema) | data-model | self (existing pattern, lines 22–80) | exact — add `test_load_config_with_qbittorrent_section` + `test_load_config_qbittorrent_prune_defaults_to_false` |
| `tests/test_cli.py` (extended) | MODIFIED | test (CLI smoke + fail-fast env-var, D-05-BOOTSTRAP-01) | request-response | `tests/test_cli.py::test_apply_missing_api_key_returns_exit_2` (lines 36–52) | exact — add `test_apply_missing_qbt_user_returns_exit_2` mirror |
| `tests/test_round_trip.py` | MODIFIED | test (dump→apply round-trip) | data-model | self (existing round-trip pattern) | exact — extend with qbit fixtures |
| `tests/test_scope_violation.py` | MODIFIED | test (frontière configarr/arrconf) | data-model | self (existing) | exact — assert qBit reconciler doesn't touch `/api/v3/qualityprofile` etc. |
| `tests/fixtures/qbittorrent/categories.json` | NEW | data fixture | data-model | `tests/fixtures/sonarr/downloadclient.json` | exact — same "GET response snapshot" shape, sanitized; capture from cluster via `snapshot.sh --apps qbittorrent` |
| `tests/fixtures/qbittorrent/preferences.json` | NEW | data fixture | data-model | `tests/fixtures/sonarr/config_host.json` | exact — singleton config snapshot, trimmed to allowlist + a few peripheral keys for realism |
| `tests/fixtures/qbittorrent/auth_login_ok.txt` | NEW | text fixture (response body) | data-model | none (truly new — qBit returns body `"Ok."` + Set-Cookie SID) | no-analog — single-line ASCII fixture |
| `tests/fixtures/sonarr/series_with_no_tags.json` | NEW | data fixture | data-model | `tests/fixtures/sonarr/downloadclient.json` shape (list of records) | exact — `GET /api/v3/series` snapshot, 8 series, all `tags: []` |
| `tests/fixtures/sonarr/series_with_tv_tag.json` | NEW | data fixture (idempotence proof) | data-model | `tests/fixtures/sonarr/edge_cases/tag_with_arrconf_managed.json` | exact — lives under `edge_cases/` per conftest.py docstring (scenario, not baseline) |
| `tests/fixtures/radarr/movie_with_no_tags.json` | NEW | data fixture | data-model | mirror of `series_with_no_tags.json` | exact |
| `tests/fixtures/sonarr/remotepathmapping.json` | NEW | data fixture | data-model | `tests/fixtures/sonarr/rootfolder.json` (short list, path-strings only) | exact |
| `tests/fixtures/radarr/remotepathmapping.json` | NEW | data fixture | data-model | mirror | exact |

### Chart side (`charts/arr-stack/`)

| New/Modified File | Status | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|--------|------|-----------|----------------|---------------|
| `charts/arr-stack/files/arrconf.yml` | MODIFIED | declarative YAML config | data-model | self (current 44-line file, only sonarr.main download_clients) | extends — adds `qbittorrent.main` block, extends `sonarr.main` + `radarr.main` with tags/root_folders/download_clients/remote_path_mappings/series_tags/movie_tags |
| `charts/arr-stack/files/configarr.yml` | MODIFIED | declarative YAML config | data-model | self (existing 327-line file — sonarr.main + radarr.main, 1 quality_profile each) | extends — adds `Anime` + `Family` profiles to each instance, extends `assign_scores_to` lists |
| `charts/arr-stack/values.yaml` | MODIFIED | Helm values | data-model | self (lines 423–478 — `arrconf` alias) | exact — single-line change: bump last element of `arrconf.controllers.main.containers.main.args` from `"sonarr,radarr,prowlarr"` (line 455) to `"sonarr,radarr,prowlarr,qbittorrent"` |
| `charts/arr-stack/values.schema.json` | REGENERATED | JSON Schema | data-model | self (via `helm-schema-gen`/losisin plugin) | exact — regenerate after values.yaml edit; commit alongside |
| `schemas/arrconf-schema.json` | REGENERATED | JSON Schema | data-model | self (via `arrconf schema-gen --output schemas/arrconf-schema.json`) | exact — regenerate after `config.py` edits; CI test `test_schema_gen` blocks if not committed |

### Snapshots (`snapshots/`)

| New/Modified File | Status | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|--------|------|-----------|----------------|---------------|
| `snapshots/before-phase-5-<date>/` | NEW | ADR-6 baseline | file-I/O | `snapshots/baseline-2026-05-07/` (existing) | exact — `tools/snapshot/snapshot.sh --output snapshots/before-phase-5-$(date +%F)/ --apps sonarr,radarr,qbittorrent` |

---

## Pattern Assignments

### `arrconf/client_base.py` — appended `QbittorrentClient` class

**Analog:** `arrconf/client_base.py::ArrApiClient` (lines 29–98) — same structural shape (`get`/`post`/`delete` helpers, `__enter__`/`__exit__`, internal `_client: httpx.Client`).

**Imports pattern** (already present, top of file lines 1–26):
```python
from __future__ import annotations
from typing import Any
import httpx
import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from arrconf.exceptions import AuthError, NotFoundError, ServerError
log = structlog.get_logger()
```

**Constructor pattern to mirror** (lines 35–49):
```python
def __init__(self, base_url: str, api_key: str, *, timeout: httpx.Timeout | None = None) -> None:
    self.base_url = base_url.rstrip("/")
    self.api_key = api_key
    self._client = httpx.Client(
        base_url=f"{self.base_url}{self.api_path}",
        headers=self.auth_headers(),
        timeout=timeout or httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0),
    )
```

**Context manager + close pattern** (lines 55–65): copy verbatim — `close()`, `__enter__`, `__exit__`.

**KEY DIVERGENCE for QbittorrentClient** (per Q1 resolution, sibling-not-subclass — RESEARCH.md lines 364–453):
- Construct takes `username: str, password: str` (NOT `api_key`).
- `__init__` performs the login HTTP call (form-encoded POST `/auth/login` with `Referer` header) using a short-lived `httpx.Client`, extracts `SID` from `r.cookies`, then constructs the long-lived `self._client` with `cookies={"SID": sid}` + `headers={"Referer": self.base_url}`.
- `AuthError` raised on `r.status_code != 200` or missing SID cookie (matches `ArrApiClient._request` line 75–76 401-handling convention).
- NO tenacity retry decorator on `get`/`post_form` — qBit doesn't exhibit the *arr 5xx flakiness and re-login-on-cookie-expired requires state machine deferred to a future phase (RESEARCH.md "Don't Hand-Roll" line 824).
- Add a `post_form(path: str, data: dict[str, str]) -> None` method for qBit's form-encoded categories + setPreferences API; `data=` param on httpx auto-URL-encodes.

**Pitfall awareness** (Pitfall 1 in RESEARCH.md line 837–842):
- ALWAYS send `headers={"Referer": self.base_url}` in BOTH login POST and subsequent calls. Without it, qBit's CSRF protection returns HTTP 403.

---

### `arrconf/reconcilers/qbittorrent.py` (NEW)

**Analog:** `arrconf/reconcilers/prowlarr.py` (195 lines — simplest existing reconciler, single primary resource).

**Imports pattern to copy** (prowlarr.py lines 31–50):
```python
from __future__ import annotations
import structlog
from arrconf.client_base import QbittorrentClient  # NEW
from arrconf.config import QbittorrentInstance     # NEW
from arrconf.differ import Action, PlannedAction, reconcile
from arrconf.exceptions import ReconcileError
from arrconf.resources.qbittorrent.category import Category
from arrconf.resources.qbittorrent.preferences import QbitPreferences
log = structlog.get_logger()
```

**Result dataclass pattern** (prowlarr.py lines 55–66, mirror exactly):
```python
@dataclass
class QbittorrentResult:
    """Result of a qBittorrent reconcile run (mirrors ProwlarrResult)."""
    plan: list[PlannedAction[Category]] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)
```

**Categories reconcile (CRUD list, match by name)** — copy `_execute` pattern from prowlarr.py lines 109–160, with these substitutions:
- `client.post(APPLICATIONS_PATH, json=body)` → `client.post_form("/torrents/createCategory", data={"category": p.name, "savePath": p.desired.savePath})` (form-encoded, NOT JSON).
- `client.put(APPLICATIONS_PATH, id=p.current.id, json=body)` → `client.post_form("/torrents/editCategory", data={"category": p.name, "savePath": p.desired.savePath})` (qBit lacks PUT; edit is POST).
- `client.delete(APPLICATIONS_PATH, id=p.current.id)` → `client.post_form("/torrents/removeCategories", data={"categories": p.name})` (bulk-delete form, single name).
- Drop `forceSave` references (qBit-irrelevant).

**Normalize qBit dict-response to list pattern** (RESEARCH.md Pattern 2, lines 455–479):
```python
def _fetch_current_categories(client: QbittorrentClient) -> list[Category]:
    raw = client.get("/torrents/categories")  # dict keyed by name
    return [Category.model_validate(v) for v in raw.values()]
```

**Preferences singleton reconcile (opt-in)** — copy `_reconcile_host_config` pattern from sonarr.py lines 182–242 with these substitutions:
- `if not section.enable: log.info("qbit_preferences_reconcile_skipped"); return` (mirror line 203–205).
- `raw = client.get("/app/preferences")` (mirror line 207).
- Diff: `diffs = {k: v for k, v in desired_dump.items() if current_raw.get(k) != v}` (simpler than `diff_models` because preferences is dict-of-scalars, not pydantic-vs-pydantic).
- Apply: `client.post_form("/app/setPreferences", data={"json": json.dumps(diffs)})` — Pitfall 4 (booleans MUST be JSON-typed not stringified, RESEARCH.md lines 858–864).

**Top-level reconcile_qbittorrent** — copy the topological-order skeleton from `reconcile_sonarr` (sonarr.py lines 245–329) with:
- Step 1: NO managed-tag (qBit categories don't carry tags — R-05 in RESEARCH.md line 952). Skip `_ensure_managed_tag`.
- Step 2: `_reconcile_categories` (CRUD list, match by name).
- Step 3: `_reconcile_preferences` (singleton, opt-in).
- Return `QbittorrentResult(plan=cat_plan, actions_taken=actions_taken)`.

---

### `arrconf/resources/qbittorrent/category.py` (NEW)

**Analog:** `arrconf/resources/sonarr/tag.py` (lines 12–17) — simplest existing two-field pydantic model with `extra="allow"`.

**Excerpt to copy** (tag.py lines 12–17):
```python
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field

class Tag(BaseModel):
    model_config = ConfigDict(extra="allow")  # API-parsing model — forward-compat
    id: int | None = Field(default=None, exclude=True, description="...")
    label: str = Field(description="Tag display name (matching key, ...)")
```

**Adaptation** (RESEARCH.md Pattern 2 line 470–479):
```python
class Category(BaseModel):
    model_config = ConfigDict(extra="allow")  # qBit may add download_path in future
    name: str = Field(description="Category name (match key).")
    savePath: str = Field(default="", description="Save path inside qBit container view.")
```

**Pitfall 3** (RESEARCH.md lines 851–856): `savePath: str = Field(default="")` is fine for GET parsing; for POST bodies the reconciler MUST send the explicit string (empty != `/data/anime`).

---

### `arrconf/resources/qbittorrent/preferences.py` (NEW)

**Analog:** `arrconf/resources/sonarr/host_config.py` (lines 22–51) — singleton config object with `extra="allow"` and credential-exclusion.

**Excerpt to mirror** (host_config.py docstring + fields):
```python
class HostConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    authenticationMethod: str | None = None
    # ... writable fields ...
    id: int | None = Field(default=None, exclude=True)
    apiKey: str | None = Field(default=None, exclude=True)
```

**Adaptation** (RESEARCH.md Pattern 3 line 497–506 — STRICTER `extra="forbid"` allowlist):
```python
class QbitPreferences(BaseModel):
    """qBit setPreferences allowlist — exactly 4 keys managed by arrconf.

    Mirror of HostConfig singleton pattern (D-03-04) but with extra="forbid"
    instead of extra="allow" — qBit preferences has ~80 keys, most operator-
    owned. Adding more keys to arrconf scope requires an explicit decision.
    """
    model_config = ConfigDict(extra="forbid")
    category_changed_tmm_enabled: bool | None = None
    torrent_changed_tmm_enabled: bool | None = None
    auto_tmm_enabled: bool | None = None
    save_path: str | None = None
```

---

### `arrconf/resources/sonarr/remote_path_mapping.py` (NEW)

**Analog:** `arrconf/resources/sonarr/root_folder.py` (lines 21–31) — "no PUT endpoint" resource with server-derived `id` excluded.

**Excerpt to copy verbatim** (root_folder.py lines 21–31):
```python
class RootFolder(BaseModel):
    """A Sonarr/Radarr root folder. ``path`` is the stable identity (D-03-01)."""
    model_config = ConfigDict(extra="allow")
    path: str = Field(description="Filesystem path (match key for reconcile()).")
    id: int | None = Field(default=None, exclude=True)
    accessible: bool | None = Field(default=None, exclude=True)
    freeSpace: int | None = Field(default=None, exclude=True)
    unmappedFolders: list[Any] | None = Field(default=None, exclude=True)
```

**Adaptation** (RESEARCH.md lines 617–622):
```python
class RemotePathMapping(BaseModel):
    """Sonarr/Radarr Remote Path Mapping — list resource, NO PUT (Pitfall 1).

    Matched by composite key (host, remotePath). Path changes produce
    DELETE+ADD via the differ — same shape as RootFolder.
    """
    model_config = ConfigDict(extra="allow")
    host: str = Field(description="Download client host (e.g. 'qbittorrent.selfhost.svc.cluster.local').")
    remotePath: str = Field(description="qBit-side path; MUST end with '/' (Pitfall 6).")
    localPath: str = Field(description="Sonarr/Radarr-side path; MUST end with '/' (Pitfall 6).")
    id: int | None = Field(default=None, exclude=True)
```

**Pitfall 6** (RESEARCH.md lines 872–878): both `remotePath` AND `localPath` MUST end with `/` — Sonarr does literal prefix-match string replacement.

---

### `arrconf/reconcilers/sonarr.py` (MODIFIED — extend existing)

**Self-analog:** `reconcile_sonarr` (lines 245–329) — the existing topological order is extended with new steps.

**New imports to add at top:**
```python
from arrconf.resources.sonarr.remote_path_mapping import RemotePathMapping
```

**New constants near line 50–56:**
```python
SERIES_PATH = "/series"
SERIES_EDITOR_PATH = "/series/editor"
REMOTE_PATH_MAPPING_PATH = "/remotepathmapping"
```

**New sub-reconciler `_reconcile_remote_path_mappings`** — RESEARCH.md Pattern 6 (lines 713–748):

Closest analog inside the same file: `_reconcile_list_resource` (lines 146–179) — BUT the composite-key matching means the existing helper doesn't apply directly. Write a small bespoke function that uses tuples `(host, remotePath)` for matching, DELETE+ADD on update (no PUT endpoint), opt-in prune.

Skeleton (RESEARCH.md lines 720–748):
```python
def _reconcile_remote_path_mappings(
    client: SonarrClient,
    items: list[RemotePathMapping],
    prune: bool,
    dry_run: bool,
) -> list[str]:
    raw = client.get(REMOTE_PATH_MAPPING_PATH)
    current = [RemotePathMapping.model_validate(x) for x in raw]
    cur_by_key = {(c.host, c.remotePath): c for c in current}
    des_by_key = {(d.host, d.remotePath): d for d in items}
    actions: list[str] = []
    for k, des in des_by_key.items():
        cur = cur_by_key.get(k)
        if cur is None:
            if dry_run:
                log.info("dry_run_skip", action="add", resource="rpm", key=k)
            else:
                client.post(REMOTE_PATH_MAPPING_PATH, json=des.model_dump(exclude_none=True))
            actions.append(f"add:{k[0]}|{k[1]}")
        elif cur.localPath != des.localPath:
            # No PUT endpoint — DELETE + ADD
            if dry_run:
                log.info("dry_run_skip", action="update_via_delete_add", key=k)
            else:
                client.delete(REMOTE_PATH_MAPPING_PATH, id=cur.id)  # cur.id guaranteed non-None
                client.post(REMOTE_PATH_MAPPING_PATH, json=des.model_dump(exclude_none=True))
            actions.append(f"update:{k[0]}|{k[1]}")
    if prune:
        for k, cur in cur_by_key.items():
            if k not in des_by_key:
                if dry_run:
                    log.info("dry_run_skip", action="delete", key=k)
                else:
                    client.delete(REMOTE_PATH_MAPPING_PATH, id=cur.id)
                actions.append(f"delete:{k[0]}|{k[1]}")
    return actions
```

**New sub-reconciler `_reconcile_series_tags`** (D-05-MIG-01) — RESEARCH.md Pattern 5 (lines 656–707).

Closest analog: there is NONE inside the file — this is a genuinely new pattern (bulk editor PUT, not a list-resource reconcile). The closest shape is `_reconcile_host_config` (lines 182–242) for the opt-in gating, but the API call is `PUT /series/editor` not `PUT /config/host/{id}`.

Skeleton:
```python
def _reconcile_series_tags(
    client: SonarrClient,
    section: SeriesTagsSection,
    all_tags: list[Tag],  # passed in from caller — already fetched
    dry_run: bool,
) -> list[str]:
    if not section.enable:
        log.info("series_tags_reconcile_skipped")
        return []
    default_tag = next((t for t in all_tags if t.label == section.default_tag), None)
    if default_tag is None or default_tag.id is None:
        raise ReconcileError(
            f"series_tags: default tag '{section.default_tag}' not found — "
            "declare it in instance.tags.items so it's reconciled first"
        )
    raw_series = client.get(SERIES_PATH)
    untagged_ids = [s["id"] for s in raw_series if not s.get("tags")]
    if not untagged_ids:
        log.info("series_tags_no_op")
        return []
    if dry_run:
        log.info("dry_run_skip", resource="series_tags", count=len(untagged_ids))
        return [f"series_tags:dry_run:{len(untagged_ids)}"]
    body = {
        "seriesIds": untagged_ids,
        "tags": [default_tag.id],
        "applyTags": "add",
        "moveFiles": False,
        "deleteFiles": False,
    }
    # Use _request directly because client.put() requires (path, id, json) signature
    # and editor uses path-without-id (PUT /series/editor, not PUT /series/editor/{id}).
    client._request("PUT", SERIES_EDITOR_PATH, json=body)
    log.info("series_tags_applied", count=len(untagged_ids), tag_id=default_tag.id)
    return [f"series_tags:applied:{len(untagged_ids)}"]
```

**Pitfall 5** (RESEARCH.md lines 866–870): editor returns HTTP 202 Accepted (async). `_request`'s `raise_for_status()` accepts 2xx — already correct.

**Wiring `reconcile_sonarr` (D-05-ORDER-01 invariant — RESEARCH.md line 133–137):**

Insert new steps in this EXACT order inside `reconcile_sonarr` (lines 245–329):

1. `_ensure_managed_tag` — UNCHANGED (line 256).
2. NEW: `_reconcile_list_resource(client, TAG_PATH, ..., Tag, instance.tags.items, match_key="label", ...)` — declares `tv`, `anime`, `family` tags. Must run BEFORE download_clients so tag IDs exist for resolution.
3. Indexers — UNCHANGED.
4. Root folders — UNCHANGED (just add the new items to the list).
5. NEW: `_reconcile_remote_path_mappings(client, instance.remote_path_mappings.items, prune=..., dry_run=...)`.
6. Download clients — UNCHANGED logic; YAML-side adds the 3 entries with `tags: [<id>]`. **Note** (RESEARCH.md line 653): the YAML uses string labels `[tv]`; the reconciler must resolve label→id BEFORE diff. Closest analog: how `_ensure_managed_tag_in_desired` (lines 88–95) stamps the managed tag — extend with label-resolution from the `all_tags` list.
7. Notifications — UNCHANGED.
8. Host config — UNCHANGED.
9. NEW: `_reconcile_series_tags(client, instance.series_tags, all_tags=<from step 2>, dry_run=...)`. MUST be after download_clients per D-05-ORDER-01.

---

### `arrconf/reconcilers/radarr.py` (MODIFIED — mirror of Sonarr)

**Self-analog:** `reconcile_radarr` (lines 216–295), which itself mirrors `reconcile_sonarr` per the file's own docstring (lines 13–18 — "This file intentionally mirrors the Sonarr reconciler verbatim").

**All Sonarr extensions mirror here verbatim with these substitutions:**
- `_reconcile_series_tags` → `_reconcile_movie_tags`.
- `SERIES_PATH = "/series"` → `MOVIE_PATH = "/movie"`.
- `SERIES_EDITOR_PATH = "/series/editor"` → `MOVIE_EDITOR_PATH = "/movie/editor"`.
- editor body `seriesIds` → `movieIds`; `addImportListExclusion` → `addImportExclusion` (RESEARCH.md line 231 — minor schema divergence).
- `SeriesTagsSection` → `MovieTagsSection`; `default_tag="tv"` → `default_tag="movies"`.

Remote path mapping reconciler is byte-equivalent to Sonarr's (shared resource model `arrconf/resources/sonarr/remote_path_mapping.py` is re-used).

---

### `arrconf/config.py` (MODIFIED — extend existing schema)

**Self-analog:** existing sections (`DownloadClientsSection`/`IndexersSection`/`NotificationsSection`/`RootFoldersSection` at lines 33–69, `HostConfigSection` at lines 72–101, `ProwlarrInstance` at lines 178–187, `RootConfig` at lines 195–206).

**TagsSection / RemotePathMappingsSection — mirror of DownloadClientsSection** (lines 33–41):
```python
class TagsSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(default=False, description="Opt-in prune (D-04). NEVER set true — see Pitfall 8.")
    items: list[TagItem] = Field(default_factory=list)

class RemotePathMappingsSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(default=False, description="Opt-in prune (D-04).")
    items: list[RemotePathMapping] = Field(default_factory=list)
```

**TagItem — simplest new type** (mirror of `AppEntry` shape at lines 104–129, simpler):
```python
class TagItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(description="Tag display label (e.g. 'tv', 'anime', 'family').")
```

**SeriesTagsSection / MovieTagsSection — mirror of HostConfigSection opt-in pattern** (lines 72–101):
```python
class SeriesTagsSection(BaseModel):
    """D-05-MIG-01 retroactive default-tag for un-tagged series."""
    model_config = ConfigDict(extra="forbid")
    enable: bool = Field(default=True, description="Phase 5 default-ON (core functionality).")
    default_tag: str = Field(default="tv", description="Label of the tag to add to un-tagged series.")

class MovieTagsSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enable: bool = Field(default=True)
    default_tag: str = Field(default="movies")
```

**PreferencesSection — opt-in singleton like HostConfigSection**:
```python
class PreferencesSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enable: bool = Field(default=False, description="Opt-in (default OFF, mirror of host_config D-03-04).")
    values: QbitPreferences = Field(default_factory=QbitPreferences)
```

**CategoriesSection** (mirror of DownloadClientsSection):
```python
class CategoriesSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(default=False, description="Opt-in prune. NEVER set true — cleanuparr depends on cleanuparr-unlinked category (R-04).")
    items: list[Category] = Field(default_factory=list)
```

**QbittorrentInstance — mirror of ProwlarrInstance** (lines 178–187) — the simplest existing instance, single primary section:
```python
class QbittorrentInstance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_url: str = Field(description="qBittorrent base URL e.g. http://qbittorrent.svc:8080")
    categories: CategoriesSection = Field(default_factory=CategoriesSection)
    preferences: PreferencesSection = Field(default_factory=PreferencesSection)
```

**Extend SonarrInstance / RadarrInstance** (lines 145–175):
```python
class SonarrInstance(BaseModel):
    # ... existing fields ...
    tags: TagsSection = Field(default_factory=TagsSection)                                        # NEW
    remote_path_mappings: RemotePathMappingsSection = Field(default_factory=RemotePathMappingsSection)  # NEW
    series_tags: SeriesTagsSection = Field(default_factory=SeriesTagsSection)                     # NEW

class RadarrInstance(BaseModel):
    # ... existing fields ...
    tags: TagsSection = Field(default_factory=TagsSection)
    remote_path_mappings: RemotePathMappingsSection = Field(default_factory=RemotePathMappingsSection)
    movie_tags: MovieTagsSection = Field(default_factory=MovieTagsSection)
```

**Extend RootConfig** (lines 195–206):
```python
class RootConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sonarr: dict[str, SonarrInstance] = Field(default_factory=dict)
    radarr: dict[str, RadarrInstance] = Field(default_factory=dict)
    prowlarr: dict[str, ProwlarrInstance] = Field(default_factory=dict)
    qbittorrent: dict[str, QbittorrentInstance] = Field(default_factory=dict)  # NEW
```

---

### `arrconf/__main__.py` (MODIFIED — add qBittorrent branch + fail-fast)

**Self-analog:** existing Prowlarr branch at lines 167–190 (apply) + lines 295–309 (diff).

**`_VALID_APPS` bump (line 42):**
```python
_VALID_APPS: frozenset[str] = frozenset({"sonarr", "radarr", "prowlarr", "qbittorrent"})
```

**Excerpt to copy and adapt** (lines 167–190 — Prowlarr branch):
```python
if "prowlarr" in targets and "main" in root.prowlarr:
    prowlarr_instance = root.prowlarr["main"]
    if not settings.prowlarr_api_key:
        log.error("missing_api_key", app="prowlarr", env_var="PROWLARR_API_KEY")
        raise typer.Exit(code=2)
    prowlarr_api_key = settings.prowlarr_api_key.get_secret_value()
    try:
        prowlarr_client = ProwlarrClient(base_url=prowlarr_instance.base_url, api_key=prowlarr_api_key)
        prowlarr_result = reconcile_prowlarr(...)
        # ...
    except (ApiClientError, ReconcileError) as e:
        log.error("app_failed", app="prowlarr", error=str(e))
        failures.append("prowlarr")
```

**Adaptation for qBittorrent (D-05-BOOTSTRAP-01 fail-fast — two env vars instead of one):**
```python
if "qbittorrent" in targets and "main" in root.qbittorrent:
    qbit_instance = root.qbittorrent["main"]
    if not settings.qbt_user or not settings.qbt_pass:
        log.error(
            "missing_env_vars",
            app="qbittorrent",
            missing=[k for k, v in (("QBT_USER", settings.qbt_user), ("QBT_PASS", settings.qbt_pass)) if not v],
        )
        raise typer.Exit(code=2)
    try:
        qbit_client = QbittorrentClient(
            base_url=qbit_instance.base_url,
            username=settings.qbt_user.get_secret_value(),
            password=settings.qbt_pass.get_secret_value(),
        )
        qbit_result = reconcile_qbittorrent(qbit_client, qbit_instance, dry_run=dry_run or settings.arrconf_dry_run)
        # ... mirror prowlarr log_event pattern ...
    except (ApiClientError, ReconcileError) as e:
        log.error("app_failed", app="qbittorrent", error=str(e))
        failures.append("qbittorrent")
```

**Mirror the same shape in `diff` (lines 295–309) and `dump` (if `dump_qbittorrent` is added).**

---

### `arrconf/diff_cmd.py` (MODIFIED — add diff_qbittorrent)

**Analog:** `diff_prowlarr` (lines 56–75) — simplest existing diff wrapper.

**Excerpt to copy verbatim** (lines 56–75):
```python
def diff_prowlarr(client: ProwlarrClient, root_config: RootConfig) -> int:
    if "main" not in root_config.prowlarr:
        log.warning("no_prowlarr_config", hint="prowlarr.main missing in YAML")
        return 0
    result = reconcile_prowlarr(client, root_config.prowlarr["main"], dry_run=True)
    non_noop = [p for p in result.plan if p.action != Action.NO_OP]
    if not non_noop:
        log.info("no_drift", apps=["prowlarr"])
        return 0
    for p in non_noop:
        log.info("drift", action=p.action.value, name=p.name, diff_fields=p.diff_fields)
    return 3
```

**Adaptation:** s/prowlarr/qbittorrent/ + import `QbittorrentClient` and `reconcile_qbittorrent`.

---

### `arrconf/settings.py` (MODIFIED — add QBT_USER / QBT_PASS)

**Analog:** existing `Settings` class (lines 9–25).

**Excerpt to extend** (lines 21–25):
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)
    sonarr_api_key: SecretStr | None = None
    radarr_api_key: SecretStr | None = None
    prowlarr_api_key: SecretStr | None = None
    qbt_user: SecretStr | None = None     # NEW — QBT_USER
    qbt_pass: SecretStr | None = None     # NEW — QBT_PASS
    arrconf_log_level: str = "INFO"
    arrconf_dry_run: bool = False
```

---

### `tests/test_reconcilers_qbittorrent.py` (NEW)

**Analog:** `tests/test_reconcilers_prowlarr.py` (lines 1–120 read — single-resource reconciler, simplest test shape).

**Imports + fixture loading pattern to copy** (lines 1–40):
```python
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import pytest
import respx

from arrconf.client_base import QbittorrentClient
from arrconf.config import (
    CategoriesSection, PreferencesSection, QbitPreferences,
    QbittorrentInstance, RootConfig,
)
from arrconf.differ import Action
from arrconf.reconcilers.qbittorrent import QbittorrentResult, reconcile_qbittorrent
from arrconf.resources.qbittorrent.category import Category

QBIT_BASE = "http://qbittorrent.test"
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "qbittorrent"
```

**Login mock pattern (NEW — no analog inside the file):**
```python
def _mock_qbit_login(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{QBIT_BASE}/api/v2/auth/login").mock(
        return_value=httpx.Response(
            200,
            text="Ok.",
            headers={"set-cookie": "SID=fake-sid-token; HttpOnly; SameSite=Strict; path=/"},
        )
    )
```

**Per-scenario test pattern** — copy `test_add_new_application` from prowlarr test (lines 101–124):
```python
@pytest.mark.respx(base_url=f"{QBIT_BASE}/api/v2", assert_all_called=False)
def test_add_new_category(respx_mock: respx.MockRouter) -> None:
    _mock_qbit_login(respx_mock)
    respx_mock.get("/torrents/categories").mock(return_value=httpx.Response(200, json={}))
    create_route = respx_mock.post("/torrents/createCategory").mock(return_value=httpx.Response(200))

    instance = QbittorrentInstance(
        base_url=QBIT_BASE,
        categories=CategoriesSection(prune=False, items=[Category(name="sonarr-tv", savePath="/data/series")]),
    )
    client = QbittorrentClient(base_url=QBIT_BASE, username="admin", password="secret")
    reconcile_qbittorrent(client, instance, dry_run=False)
    assert create_route.call_count == 1
    body = create_route.calls.last.request.content.decode()
    assert "category=sonarr-tv" in body and "savePath=%2Fdata%2Fseries" in body  # URL-encoded form
```

**Mandatory tests** (RESEARCH.md Validation Architecture lines 1093–1117):
- `test_login_with_referer_header` (Pitfall 1).
- `test_login_failure_raises_authError`.
- `test_create_six_categories_with_correct_savepaths` (SC#2).
- `test_categories_match_by_name`.
- `test_categories_no_op_when_in_sync` (idempotence / SC#5).
- `test_prune_false_keeps_unmanaged_categories` (R-04: don't delete cleanuparr-unlinked).
- `test_preferences_singleton_opt_in_skip_when_disabled` (mirror `_reconcile_host_config` skip test).
- `test_preferences_allowlist_only_4_keys` (Q2 resolution).
- `test_preferences_no_op_when_in_sync`.
- `test_setpreferences_uses_json_boolean_not_quoted` (Pitfall 4).

---

### `tests/test_series_editor.py` (NEW — D-05-MIG-01 bulk tagging)

**Analog:** `tests/test_reconcilers_sonarr.py::test_add_new_download_client` (lines 101–124 — closest "respx PUT-body assertion" pattern).

**Tests required (RESEARCH.md Validation Architecture lines 1110–1117 + Pattern 5 line 711):**
- `test_series_editor_adds_default_tag_to_untagged_series` — given 8 series with `tags: []`, after apply 8 series have `tags: [<tv_id>]`. Assert single PUT call to `/series/editor` with `seriesIds=[1,2,...,8]`, `applyTags="add"`.
- `test_series_editor_idempotent_when_all_tagged` — given 8 series with `tags: [<tv_id>]`, no PUT issued (R-02 mitigation: post-tagging idempotence).
- `test_series_editor_preserves_existing_manual_tags` — given a series with `tags: [99]` (operator custom tag), after apply `tags: [99, <tv_id>]` (R-02 — `applyTags: "add"` preserves).
- `test_series_editor_does_not_move_files` — assert PUT body has `"moveFiles": false, "deleteFiles": false`.
- `test_series_editor_dry_run_emits_no_put` (mirror of every other reconciler test's dry-run branch).
- `test_series_editor_skipped_when_section_disabled` (mirror of `_reconcile_host_config` opt-in skip).
- Mirror `test_movie_editor_*` for Radarr.

---

### `tests/test_remote_path_mapping.py` (NEW)

**Analog:** root-folder section of `tests/test_reconcilers_sonarr.py` (Pitfall 1 — DELETE+ADD pattern).

**Tests required:**
- `test_rpm_add_new_mapping` — single POST per new entry.
- `test_rpm_delete_plus_add_on_localpath_change` — assert DELETE then POST (NOT PUT — Pattern 6 line 715).
- `test_rpm_no_op_when_in_sync` (idempotence).
- `test_rpm_match_by_host_and_remote_path_tuple` (composite-key matching).
- `test_rpm_trailing_slash_invariant` (Pitfall 6) — both `remotePath` and `localPath` end with `/`.
- `test_rpm_prune_false_keeps_existing_mapping` (R-04 mitigation).

---

### `tests/conftest.py` (MODIFIED — extend with qBit + series fixtures)

**Analog:** existing `conftest.py` (lines 51–94) — `_load_fixture` helper pattern.

**Excerpt to copy** (lines 51–58):
```python
@pytest.fixture
def sonarr_downloadclient_fixture() -> list[dict[str, Any]]:
    """Sonarr GET /api/v3/downloadclient response (1 qBit client, redacted)."""
    return _load_fixture("sonarr/downloadclient.json")
```

**Adaptations to add:**
```python
@pytest.fixture
def qbit_categories_fixture() -> dict[str, Any]:
    """qBit GET /api/v2/torrents/categories — dict keyed by category name."""
    return _load_fixture("qbittorrent/categories.json")

@pytest.fixture
def qbit_preferences_fixture() -> dict[str, Any]:
    """qBit GET /api/v2/app/preferences — singleton (trimmed to allowlist + peripheral keys)."""
    return _load_fixture("qbittorrent/preferences.json")

@pytest.fixture
def sonarr_series_with_no_tags_fixture() -> list[dict[str, Any]]:
    """Sonarr GET /api/v3/series — 8 series, all tags=[] (D-05-MIG-01 starting state)."""
    return _load_fixture("sonarr/series_with_no_tags.json")

@pytest.fixture
def sonarr_series_with_tv_tag_fixture() -> list[dict[str, Any]]:
    """Sonarr GET /api/v3/series — 8 series, all tags=[<tv_id>] (D-05-MIG-01 idempotence proof)."""
    return _load_fixture("sonarr/edge_cases/series_with_tv_tag.json")

@pytest.fixture
def radarr_movie_with_no_tags_fixture() -> list[dict[str, Any]]:
    """Radarr GET /api/v3/movie — 11 movies, all tags=[]."""
    return _load_fixture("radarr/movie_with_no_tags.json")

@pytest.fixture
def sonarr_remotepathmapping_fixture() -> list[dict[str, Any]]:
    """Sonarr GET /api/v3/remotepathmapping — 1 existing entry (/data/complete/ → /data/torrents/complete/)."""
    return _load_fixture("sonarr/remotepathmapping.json")
```

---

### `tests/test_cli.py` (MODIFIED — D-05-BOOTSTRAP-01 fail-fast tests)

**Analog:** `tests/test_cli.py::test_apply_missing_api_key_returns_exit_2` (lines 36–52).

**Excerpt to copy and adapt** (lines 36–52):
```python
def test_apply_missing_api_key_returns_exit_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = tmp_path / "cfg.yml"
    cfg.write_text("sonarr:\n  main:\n    base_url: http://sonarr.test\n    ...")
    monkeypatch.delenv("SONARR_API_KEY", raising=False)
    result = runner.invoke(app, ["--config", str(cfg), "apply"])
    assert result.exit_code == 2
    assert "missing_api_key" in result.stdout
```

**Adaptations:**
- `test_apply_missing_qbt_user_returns_exit_2` — YAML has `qbittorrent.main`, env-var unset, expect exit 2 + `missing_env_vars` in stdout.
- `test_apply_missing_qbt_pass_returns_exit_2`.
- `test_help_lists_qbittorrent_in_apps_option` — verify `qbittorrent` appears as a valid value for `--apps`.

---

### `tests/test_config.py` (MODIFIED)

**Analog:** `tests/test_config.py::test_load_config_happy_path_all_three_apps` (lines 45–69).

**Excerpt to copy and adapt** (lines 45–69):
```python
def test_load_config_happy_path_all_three_apps(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg.yml"
    cfg.write_text("sonarr:\n  main:\n    base_url: http://sonarr.test\n  ...")
    result = load_config(cfg)
    assert "main" in result.sonarr
```

**Adaptations:**
- `test_load_config_with_qbittorrent_main_section` (Phase 5 D-05).
- `test_load_config_qbittorrent_prune_defaults_to_false` (R-04 mitigation).
- `test_load_config_qbittorrent_preferences_extra_forbid_rejects_unknown_key` (Q2 allowlist enforcement).
- `test_load_config_sonarr_with_tags_section`.
- `test_load_config_sonarr_with_remote_path_mappings_section`.
- `test_load_config_sonarr_series_tags_defaults_enabled_with_tv` (D-05-MIG-01 default).

---

### `charts/arr-stack/files/arrconf.yml` (MODIFIED)

**Self-analog:** existing 44-line file (single sonarr.main download_clients block).

**Existing pattern to follow** (lines 1–44):
```yaml
sonarr:
  main:
    base_url: http://sonarr.selfhost.svc.cluster.local:8989
    download_clients:
      prune: false
      items:
        - name: qBittorrent
          ...
```

**Adaptations** (RESEARCH.md Pattern 4 lines 538–603) — extend with:
- `qbittorrent.main: { base_url, categories: { items: [6 entries with explicit savePath] }, preferences: { enable: false, values: {} } }`.
- `sonarr.main.tags: { items: [tv, anime, family] }`.
- `sonarr.main.root_folders.items: [/media/series (existing), /media/anime, /media/family]`.
- `sonarr.main.download_clients.items: [3 entries: qBittorrent - TV/Anime/Family, each with distinct tvCategory + tags: [<label>]]`. **NOTE:** the 3 entries each carry a tag-LABEL (string) in `tags:` — the reconciler resolves label→id at apply (Pattern 4 commentary line 653).
- `sonarr.main.remote_path_mappings.items: [4 entries — /data/complete/, /data/series/, /data/anime/, /data/family/, each with localPath = /data/torrents/<...>/]`.
- `sonarr.main.series_tags: { enable: true, default_tag: tv }`.
- Mirror for `radarr.main` with `default_tag: movies`, root folders `/media/films` (KEPT per D-05-PATHS-01), `/media/films-anime`, `/media/films-family`, qBit categories `radarr-movies → /data/films`, `radarr-anime → /data/films-anime`, `radarr-family → /data/films-family`.

---

### `charts/arr-stack/files/configarr.yml` (MODIFIED)

**Self-analog:** existing 327-line file (sonarr.main + radarr.main, 1 quality_profile each — `MULTi.VF` blocks at lines 187–210 and 284–307).

**Existing quality_profiles pattern to copy** (lines 187–210):
```yaml
quality_profiles:
  - name: MULTi.VF
    reset_unmatched_scores:
      enabled: true
    upgrade:
      allowed: true
      until_quality: Bluray-1080p
      until_score: 2000
      min_format_score: 50
    min_format_score: 0
    quality_sort: top
    qualities:
      - name: Bluray-1080p
      - name: WEB 1080p
        qualities: [WEBDL-1080p, WEBRip-1080p]
      - ...
```

**Adaptations** (RESEARCH.md Pattern 7 lines 753–804):
- Append `Anime` profile (TRaSH-Guides anime template — recyclarr `sonarr-v4-quality-profile-1080p-french-anime-multi` for Sonarr; hand-rolled mirror of MULTi.VF for Radarr per Q9/A6).
- Append `Family` profile — **byte-equivalent clone of MULTi.VF** (D-05-FAM-01).
- Extend `custom_formats` blocks (lines 212–230 and 309–327) with per-profile `assign_scores_to` arrays. Pattern: explicit `score:` override per profile entry (Q5 resolution / pattern (1) at line 297). VOSTFR score deltas: `MULTi.VF: -10000`, `Anime: +50`, `Family: -10000`.

---

### `charts/arr-stack/values.yaml` (MODIFIED — single line)

**Self-analog:** existing `arrconf` alias (lines 423–477).

**Excerpt to bump** (line 455):
```yaml
          args:
            - "--config"
            - "/app/config/arrconf.yml"
            - "apply"
            - "--apps"
            - "sonarr,radarr,prowlarr"   # ← BUMP THIS to "sonarr,radarr,prowlarr,qbittorrent"
```

D-05-ARGS-01.

---

### `snapshots/before-phase-5-<date>/` (NEW)

**Analog:** existing `snapshots/baseline-2026-05-07/`.

**Command** (CLAUDE.md "Workflow snapshot" section + RESEARCH.md SC#1 line 1096):
```bash
tools/snapshot/snapshot.sh --output snapshots/before-phase-5-$(date +%F)/ --apps sonarr,radarr,qbittorrent
```

Committed to Git per CLAUDE.md "Discipline" (no `.gitignore`).

---

## Shared Patterns

### Cross-cutting: structlog logging convention

**Source:** `arrconf/reconcilers/sonarr.py` lines 29 + 46.
**Apply to:** every new reconciler + every new sub-reconciler in modified reconcilers.
```python
import structlog
log = structlog.get_logger()
# ... emit named events with kwargs ...
log.info("plan_action", action="add", name=name)
log.info("dry_run_skip", action=p.action.value, name=p.name)
log.info("series_tags_no_op")
log.error("missing_env_vars", app="qbittorrent", missing=[...])
```

### Cross-cutting: respx test pattern

**Source:** `tests/test_reconcilers_sonarr.py` lines 67–98 (`test_dump_apply_no_op`) — defines the canonical "mock all GET endpoints + assert zero write calls" idempotence proof.
**Apply to:** every new test file in Phase 5.
```python
@pytest.mark.respx(base_url="http://<app>.test/api/v<N>", assert_all_called=False)
def test_X(respx_mock: respx.MockRouter, <fixture>: ...) -> None:
    # Mock all GET endpoints the reconciler touches
    respx_mock.get("/foo").mock(return_value=httpx.Response(200, json=<fixture>))
    # ... build instance + invoke reconciler ...
    # Assert NO writes when state matches
    assert post_route.call_count == 0
    assert put_route.call_count == 0
    assert delete_route.call_count == 0
```

### Cross-cutting: opt-in singleton pattern (D-03-04)

**Source:** `arrconf/reconcilers/sonarr.py::_reconcile_host_config` (lines 182–242).
**Apply to:** `_reconcile_preferences` (qBit), `_reconcile_series_tags` (Sonarr), `_reconcile_movie_tags` (Radarr).
```python
def _reconcile_X(client, section, dry_run):
    if not section.enable:
        log.info("X_reconcile_skipped")
        return
    raw = client.get(X_PATH)
    # ... diff + dry-run guard + apply ...
```

### Cross-cutting: idempotence rule (CLAUDE.md "RÈGLE D'OR")

**Source:** `arrconf/differ.py::reconcile` (lines 237–286).
**Apply to:** every new reconciler. Re-run with identical input → identical plan → all NO_OP. Test asserts: `assert all(p.action == Action.NO_OP for p in result.plan if p.desired is not None)`.

### Cross-cutting: prune-false default + `extra='forbid'` on sections

**Source:** every existing section in `arrconf/config.py` (lines 33–69).
**Apply to:** every new section (`CategoriesSection`, `TagsSection`, `RemotePathMappingsSection`, `PreferencesSection`, `SeriesTagsSection`, `MovieTagsSection`). R-04 mitigation: `prune: false` schema default is the type-level safety net.

### Cross-cutting: fail-fast env-var validation (D-05-BOOTSTRAP-01)

**Source:** `arrconf/__main__.py::apply` Sonarr branch (lines 125–127), Prowlarr branch (lines 169–171).
**Apply to:** every new app branch in `apply` / `diff` / `dump` for qBittorrent.
```python
if not settings.<env>:
    log.error("missing_api_key", app="<app>", env_var="<ENV>")
    raise typer.Exit(code=2)
```

### Cross-cutting: re-inject `id` after `merge_fields_for_put` (Pitfall 4)

**Source:** `arrconf/reconcilers/sonarr.py::_execute` line 133–135 + `_reconcile_host_config` lines 230–234.
**Apply to:** every UPDATE branch in new reconcilers that uses `merge_fields_for_put`. **NOT** applicable to qBittorrent reconciler (form-encoded, no `merge_fields_for_put`). **IS** applicable to extended Sonarr/Radarr download_client reconciliation when the 3 new download clients get UPDATEd later (existing pattern, no change).

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `arrconf/client_base.py::QbittorrentClient` (the auth lifecycle) | http-client (login-then-cookie) | request-response | qBit's `POST /auth/login` → Set-Cookie → re-use cookie flow has no precedent in the existing codebase — every existing client uses static `X-Api-Key` header at construct time. Planner should reference RESEARCH.md §"Pattern 1: qBit Cookie Auth via QbittorrentClient(ArrApiClient) subclass" (lines 364–453) for the sketch. |
| `_reconcile_series_tags` / `_reconcile_movie_tags` (the `/editor` bulk PUT itself) | reconciler (bulk-editor) | request-response (bulk) | The closest in-tree shape (opt-in singleton via `_reconcile_host_config`) gives only the opt-in / dry-run / GET-diff scaffolding. The bulk PUT to `/series/editor` (HTTP 202, no path-id, payload schema `{seriesIds, tags, applyTags, moveFiles, deleteFiles}`) is genuinely new. Planner references RESEARCH.md Pattern 5 (lines 656–711) for the sketch + Pitfall 5 (line 866) for the 202-handling note. |
| `_reconcile_remote_path_mappings` (composite-key matching `(host, remotePath)`) | reconciler (no-PUT list) | CRUD | The closest in-tree precedent is `RootFolder` (single-key `path`, DELETE+ADD on update). The composite-key `(host, remotePath)` matching doesn't fit `differ.reconcile`'s `match_key: str` signature — Planner writes a small bespoke loop (RESEARCH.md Pattern 6, lines 720–748) inside `sonarr.py` / `radarr.py`. **Optional follow-up:** generalize `differ.reconcile` to accept a callable `match_key` — deferred per the same "no new abstractions" rule that kept `_reconcile_list_resource` shared rather than upstreaming into `differ.py`. |

---

## Metadata

**Analog search scope:**
- `tools/arrconf/arrconf/` (28 .py files, full read on 8 most relevant: `client_base.py`, `config.py`, `differ.py`, `__main__.py`, `diff_cmd.py`, `dump.py`, `settings.py`, `exceptions.py`).
- `tools/arrconf/arrconf/reconcilers/` (3 files — sonarr, radarr, prowlarr — all fully read).
- `tools/arrconf/arrconf/resources/sonarr/` (8 .py files — relevant: `download_client.py`, `root_folder.py`, `tag.py`, `host_config.py`, `indexer.py` read).
- `tools/arrconf/arrconf/resources/prowlarr/application.py` read.
- `tools/arrconf/tests/conftest.py` + 1st 130 lines of `test_reconcilers_sonarr.py` + 1st 120 lines of `test_reconcilers_prowlarr.py` + `test_config.py` + 1st 60 lines of `test_cli.py` read.
- `charts/arr-stack/files/arrconf.yml` (44 lines, full).
- `charts/arr-stack/files/configarr.yml` (read excerpts at lines 1–100, 150–210, 200–328).
- `charts/arr-stack/values.yaml` (read excerpt around `arrconf:` and `qbittorrent:` aliases).

**Files scanned (read fully or via targeted Read offset/limit):** 18.

**Pattern extraction date:** 2026-05-14.

---

*Phase: 05-reconciler-qbittorrent-split-tv-anime-family*
*Pattern map produced for gsd-planner — every new/touched file lists its analog file (with line numbers) and the concrete code excerpts to copy. Three genuinely-new patterns flagged in §No Analog Found point the planner at RESEARCH.md sections for the sketches.*
