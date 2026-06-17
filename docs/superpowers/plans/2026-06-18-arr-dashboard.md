# arr-dashboard V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `arr-dashboard`, a read-only in-cluster service showing one row per media title across the full lifecycle (Seerr request → Sonarr/Radarr grab → qBit download → import → Jellyfin), flagging duplicates and broken chains.

**Architecture:** New standalone FastAPI + Svelte 5 service under `tools/arr-dashboard/`. Reuses the `arrconf` library's HTTP clients (env-key auth via `arrconf-env`). A background refresher recomputes a correlated snapshot every 30s; the API serves it from memory. The correlation logic is a pure function tested in isolation. arrconf-ui is untouched.

**Tech Stack:** Python 3.13, FastAPI, httpx (via arrconf clients), pydantic v2, pytest + respx, ruff, mypy, uv. Frontend: Svelte 5 + Vite. Helm `bjw-s/app-template`. Reference design: `docs/superpowers/specs/2026-06-18-arr-dashboard-design.md`.

**Branch:** `feat/arr-dashboard` (already created; the spec commit lives here).

---

## File Structure

```
tools/arr-dashboard/
  pyproject.toml                       # package metadata, deps, ruff/mypy config (mirror tools/arrconf-ui)
  Dockerfile                           # multi-stage (node build web → python runtime), USER 1000:1000
  arr_dashboard/
    __init__.py
    __main__.py                        # uvicorn entrypoint
    settings.py                        # Settings model + load_settings() from env
    models.py                          # Download, ChainHealth, Row, Snapshot
    correlate.py                       # correlate(sources, generated_at, stale) -> Snapshot  (PURE)
    sources.py                         # fetch_all(settings) -> (Sources, stale_sources)  (I/O, reuses arrconf clients)
    cache.py                           # SnapshotCache + refresher_loop()
    app.py                             # create_app(): GET /api/dashboard, /api/dashboard/{key}, /healthz, static web/dist
  tests/
    __init__.py
    conftest.py                        # shared fixture builders
    test_correlate.py                  # core: add/dup/owned-regrab/broken-chain/unimported/ok
    test_sources.py                    # respx-mocked fetch + graceful degradation
    test_app.py                        # endpoint shape + degraded snapshot
  web/                                 # Svelte 5 (mirror tools/arrconf-ui/web structure)
    package.json, vite.config.ts, svelte.config.js, index.html
    src/main.ts, src/App.svelte, src/api.ts, src/lib/*.svelte, src/i18n/fr.ts

tools/arrconf/arrconf/client_base.py   # MODIFY: add list_queue / list_torrents / list_requests / list_items read-methods

.github/workflows/arr-dashboard-image.yml   # NEW image build (mirror arrconf-mcp-image.yml)
.github/workflows/tests.yml                  # MODIFY: add arr-dashboard test job
.github/workflows/chart-lint.yml             # MODIFY: add arr-dashboard to alias-unpack loop + dispatch
charts/arr-stack/Chart.yaml                  # MODIFY: add app-template alias arr-dashboard
charts/arr-stack/Chart.lock                  # regenerated
charts/arr-stack/values.yaml                 # MODIFY: arr-dashboard block
README.md                                    # MODIFY: alias-unpack loop list
```

**Before starting:** read these for exact patterns/signatures:
- `tools/arrconf/arrconf/client_base.py` — client classes, `.get(path)` signature, auth, exception types.
- `tools/arrconf-ui/pyproject.toml`, `tools/arrconf-ui/Dockerfile`, `tools/arrconf-ui/arrconf_ui/__main__.py`, `tools/arrconf-ui/arrconf_ui/app.py` — service/FastAPI/static-mount/uvicorn pattern.
- `tools/arrconf-ui/web/` — Svelte 5 structure (runes, api.ts, i18n, Vite, dark theme, IBM Plex).
- `charts/arr-stack/values.yaml` `arrconf-mcp:` block — ClusterIP + envFrom arrconf-env + healthz probes pattern (added recently).
- `charts/arr-stack/Chart.yaml` — alias dependency entries; `.github/workflows/arrconf-mcp-image.yml` — image+dispatch pattern.

---

## Phase 1 — Reusable read-methods on arrconf clients

Thin GET wrappers added to existing clients in `tools/arrconf/arrconf/client_base.py`. Run all commands from `tools/arrconf/`.

### Task 1: qBittorrent `list_torrents`

**Files:**
- Modify: `tools/arrconf/arrconf/client_base.py` (QbittorrentClient class)
- Test: `tools/arrconf/tests/test_client_read_methods.py`

- [ ] **Step 1: Write the failing test**

Create `tools/arrconf/tests/test_client_read_methods.py`:

```python
import respx
import httpx
from arrconf.client_base import QbittorrentClient


@respx.mock
def test_qbit_list_torrents_returns_list():
    # qBit login happens in __init__; mock it + the info endpoint
    respx.post("http://qb:8080/api/v2/auth/login").mock(
        return_value=httpx.Response(200, text="Ok.", headers={"set-cookie": "SID=abc"})
    )
    respx.get("http://qb:8080/api/v2/torrents/info").mock(
        return_value=httpx.Response(200, json=[{"hash": "AB", "name": "X", "state": "stalledUP",
                                                "progress": 1.0, "category": "radarr-movies",
                                                "save_path": "/data/x", "tracker": "http://t/announce"}])
    )
    client = QbittorrentClient("http://qb:8080", "u", "p")
    out = client.list_torrents()
    assert isinstance(out, list)
    assert out[0]["hash"] == "AB"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_client_read_methods.py::test_qbit_list_torrents_returns_list -v`
Expected: FAIL with `AttributeError: 'QbittorrentClient' object has no attribute 'list_torrents'`

- [ ] **Step 3: Implement**

In `client_base.py`, inside `QbittorrentClient`, add (uses the existing `.get(path)` that returns parsed JSON):

```python
    def list_torrents(self) -> list[dict]:
        """All torrents with state/progress/category/save_path (GET /torrents/info)."""
        return self.get("/torrents/info")
```

> If `QbittorrentClient.get()` returns an `httpx.Response` rather than parsed JSON, use `self.get("/torrents/info").json()`. Verify against the class before writing.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_client_read_methods.py::test_qbit_list_torrents_returns_list -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/arrconf/arrconf/client_base.py tools/arrconf/tests/test_client_read_methods.py
git commit -m "feat(arrconf): QbittorrentClient.list_torrents read-method"
```

### Task 2: Sonarr/Radarr `list_queue`

**Files:**
- Modify: `tools/arrconf/arrconf/client_base.py` (the v3 client / SonarrClient + RadarrClient)
- Test: `tools/arrconf/tests/test_client_read_methods.py`

- [ ] **Step 1: Write the failing test** (append to the test file)

```python
from arrconf.client_base import RadarrClient


@respx.mock
def test_radarr_list_queue():
    respx.get("http://r:7878/api/v3/queue").mock(
        return_value=httpx.Response(200, json={"records": [
            {"id": 1, "movieId": 42, "title": "M", "status": "downloading",
             "downloadId": "ABCDEF", "trackedDownloadStatus": "ok"}]})
    )
    client = RadarrClient("http://r:7878", "key")
    out = client.list_queue()
    assert out[0]["downloadId"] == "ABCDEF"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_client_read_methods.py::test_radarr_list_queue -v`
Expected: FAIL with `AttributeError: ... 'list_queue'`

- [ ] **Step 3: Implement**

Add to the shared v3 client mixin (`_ArrV3Client`) so Sonarr+Radarr both inherit:

```python
    def list_queue(self) -> list[dict]:
        """Active download queue (GET /queue). Returns the records list."""
        data = self.get("/queue?pageSize=1000&includeUnknownMovieItems=true")
        return data.get("records", data) if isinstance(data, dict) else data
```

> Sonarr's param is `includeUnknownSeriesItems`; the extra unknown-Radarr param is harmless to Sonarr but if a 400 occurs, drop the `includeUnknown*` query — `/queue?pageSize=1000` is sufficient. Confirm during impl.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_client_read_methods.py::test_radarr_list_queue -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/arrconf/arrconf/client_base.py tools/arrconf/tests/test_client_read_methods.py
git commit -m "feat(arrconf): _ArrV3Client.list_queue read-method"
```

### Task 3: Seerr `list_requests`

**Files:**
- Modify: `tools/arrconf/arrconf/client_base.py` (SeerrClient)
- Test: `tools/arrconf/tests/test_client_read_methods.py`

- [ ] **Step 1: Write the failing test**

```python
from arrconf.client_base import SeerrClient


@respx.mock
def test_seerr_list_requests():
    respx.get("http://s:5055/api/v1/request").mock(
        return_value=httpx.Response(200, json={"results": [
            {"id": 7, "type": "movie", "status": 2,
             "media": {"tmdbId": 42, "tvdbId": None},
             "requestedBy": {"displayName": "Thomas"}}]})
    )
    client = SeerrClient("http://s:5055", "key")
    out = client.list_requests()
    assert out[0]["media"]["tmdbId"] == 42
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_client_read_methods.py::test_seerr_list_requests -v`
Expected: FAIL with `AttributeError: ... 'list_requests'`

- [ ] **Step 3: Implement**

```python
    def list_requests(self) -> list[dict]:
        """User requests (GET /request). Returns the results list."""
        data = self.get("/request?take=200&sort=added")
        return data.get("results", []) if isinstance(data, dict) else data
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_client_read_methods.py::test_seerr_list_requests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/arrconf/arrconf/client_base.py tools/arrconf/tests/test_client_read_methods.py
git commit -m "feat(arrconf): SeerrClient.list_requests read-method"
```

### Task 4: Jellyfin `list_items`

**Files:**
- Modify: `tools/arrconf/arrconf/client_base.py` (JellyfinClient)
- Test: `tools/arrconf/tests/test_client_read_methods.py`

- [ ] **Step 1: Write the failing test**

```python
from arrconf.client_base import JellyfinClient


@respx.mock
def test_jellyfin_list_items():
    respx.get("http://j:8096/Items").mock(
        return_value=httpx.Response(200, json={"Items": [
            {"Name": "Ratatouille", "Type": "Movie", "ProviderIds": {"Tmdb": "2062"}}]})
    )
    client = JellyfinClient("http://j:8096", "key")
    out = client.list_items()
    assert out[0]["ProviderIds"]["Tmdb"] == "2062"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_client_read_methods.py::test_jellyfin_list_items -v`
Expected: FAIL with `AttributeError: ... 'list_items'`

- [ ] **Step 3: Implement**

```python
    def list_items(self) -> list[dict]:
        """Library items with provider IDs (GET /Items). Returns the Items list."""
        data = self.get("/Items?Recursive=true&IncludeItemTypes=Movie,Series&Fields=ProviderIds")
        return data.get("Items", []) if isinstance(data, dict) else data
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_client_read_methods.py::test_jellyfin_list_items -v`
Expected: PASS

- [ ] **Step 5: Run the arrconf triad + commit**

Run: `uv run ruff format --check . && uv run ruff check . && uv run mypy arrconf`
Expected: all pass.

```bash
git add tools/arrconf/arrconf/client_base.py tools/arrconf/tests/test_client_read_methods.py
git commit -m "feat(arrconf): JellyfinClient.list_items read-method"
```

> Note: do NOT bump `charts/arr-stack/values.yaml#arrconf.image.tag` yet — these methods only get used in-cluster once arr-dashboard ships. The co-bump applies when this reaches main; bundle it with the final release.

---

## Phase 2 — Package scaffold, settings, models

Run commands from `tools/arr-dashboard/` unless noted.

### Task 5: Scaffold the package

**Files:**
- Create: `tools/arr-dashboard/pyproject.toml`, `arr_dashboard/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Create `tools/arr-dashboard/pyproject.toml`** (mirror `tools/arrconf-ui/pyproject.toml`; depend on the local arrconf package for clients)

```toml
[project]
name = "arr-dashboard"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic>=2.9",
    "httpx>=0.27",
    "arrconf",
]

[tool.uv.sources]
arrconf = { path = "../arrconf", editable = true }

[dependency-groups]
dev = ["pytest>=8", "pytest-cov>=5", "respx>=0.21", "ruff>=0.6", "mypy>=1.11"]

[tool.ruff]
line-length = 100

[tool.mypy]
strict = true

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 2: Create empty `arr_dashboard/__init__.py` and `tests/__init__.py`**

```bash
mkdir -p tools/arr-dashboard/arr_dashboard tools/arr-dashboard/tests
: > tools/arr-dashboard/arr_dashboard/__init__.py
: > tools/arr-dashboard/tests/__init__.py
```

- [ ] **Step 3: Sync deps**

Run: `cd tools/arr-dashboard && uv sync`
Expected: resolves, installs arrconf editable.

- [ ] **Step 4: Commit**

```bash
git add tools/arr-dashboard/pyproject.toml tools/arr-dashboard/arr_dashboard/__init__.py tools/arr-dashboard/tests/__init__.py tools/arr-dashboard/uv.lock
git commit -m "chore(arr-dashboard): scaffold package"
```

### Task 6: Models

**Files:**
- Create: `tools/arr-dashboard/arr_dashboard/models.py`
- Test: `tools/arr-dashboard/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
from arr_dashboard.models import Row, Download, ChainHealth, Snapshot


def test_row_defaults_and_serialization():
    row = Row(key="tmdb:42", title="M", type="movie",
              chain=ChainHealth(requested=True, grabbed=True, downloaded=True,
                                imported=False, in_jellyfin=False))
    dumped = row.model_dump()
    assert dumped["downloads"] == []
    assert dumped["flags"] == []
    assert dumped["chain"]["imported"] is False


def test_snapshot_holds_rows():
    snap = Snapshot(rows=[], generated_at="2026-06-18T00:00:00Z", stale_sources=["jellyfin"])
    assert snap.stale_sources == ["jellyfin"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arr_dashboard.models'`

- [ ] **Step 3: Implement `arr_dashboard/models.py`**

```python
from typing import Literal
from pydantic import BaseModel, Field


class Download(BaseModel):
    infohash: str
    name: str
    state: str
    progress: float
    category: str | None = None
    tracker: str | None = None
    save_path: str | None = None


class ChainHealth(BaseModel):
    requested: bool = False
    grabbed: bool = False
    downloaded: bool = False
    imported: bool = False
    in_jellyfin: bool = False


class Row(BaseModel):
    key: str
    title: str
    year: int | None = None
    type: Literal["movie", "series"]
    requested_by: str | None = None
    request_status: str | None = None
    arr_app: Literal["sonarr", "radarr"] | None = None
    monitored: bool | None = None
    has_file: bool | None = None
    quality: str | None = None
    downloads: list[Download] = Field(default_factory=list)
    disk_paths: list[str] = Field(default_factory=list)
    in_jellyfin: bool = False
    chain: ChainHealth = Field(default_factory=ChainHealth)
    flags: list[str] = Field(default_factory=list)


class Snapshot(BaseModel):
    rows: list[Row] = Field(default_factory=list)
    generated_at: str | None = None
    stale_sources: list[str] = Field(default_factory=list)
    initializing: bool = False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/models.py tools/arr-dashboard/tests/test_models.py
git commit -m "feat(arr-dashboard): Row/Download/ChainHealth/Snapshot models"
```

### Task 7: Settings

**Files:**
- Create: `tools/arr-dashboard/arr_dashboard/settings.py`
- Test: `tools/arr-dashboard/tests/test_settings.py`

- [ ] **Step 1: Write the failing test**

```python
from arr_dashboard.settings import load_settings


def test_load_settings_defaults(monkeypatch):
    for k in list(__import__("os").environ):
        if k.endswith("_URL") or k.endswith("_API_KEY") or k.startswith("QBT_"):
            monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("RADARR_API_KEY", "rk")
    s = load_settings()
    assert s.radarr_url.endswith(":7878")
    assert s.radarr_api_key == "rk"
    assert s.refresh_seconds == 30
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_settings.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arr_dashboard.settings'`

- [ ] **Step 3: Implement `arr_dashboard/settings.py`**

```python
import os
from pydantic import BaseModel

_SVC = "selfhost.svc.cluster.local"


class Settings(BaseModel):
    sonarr_url: str
    radarr_url: str
    qbittorrent_url: str
    seerr_url: str
    jellyfin_url: str
    sonarr_api_key: str | None
    radarr_api_key: str | None
    seerr_api_key: str | None
    jellyfin_api_key: str | None
    qbt_user: str | None
    qbt_pass: str | None
    refresh_seconds: int = 30
    bind: str = "0.0.0.0:8080"


def load_settings() -> Settings:
    e = os.environ.get
    return Settings(
        sonarr_url=e("SONARR_URL", f"http://sonarr.{_SVC}:8989"),
        radarr_url=e("RADARR_URL", f"http://radarr.{_SVC}:7878"),
        qbittorrent_url=e("QBITTORRENT_URL", f"http://qbittorrent.{_SVC}:8080"),
        seerr_url=e("SEERR_URL", f"http://seerr.{_SVC}:5055"),
        jellyfin_url=e("JELLYFIN_URL", f"http://jellyfin.{_SVC}:8096"),
        sonarr_api_key=e("SONARR_API_KEY"),
        radarr_api_key=e("RADARR_API_KEY"),
        seerr_api_key=e("SEERR_API_KEY"),
        jellyfin_api_key=e("JELLYFIN_API_KEY"),
        qbt_user=e("QBT_USER"),
        qbt_pass=e("QBT_PASS"),
        refresh_seconds=int(e("DASHBOARD_REFRESH_SECONDS", "30")),
        bind=e("DASHBOARD_BIND", "0.0.0.0:8080"),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_settings.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/settings.py tools/arr-dashboard/tests/test_settings.py
git commit -m "feat(arr-dashboard): env-driven Settings"
```

---

## Phase 3 — Correlation engine (the core)

Pure function. `correlate(sources, generated_at, stale_sources) -> Snapshot`. `sources` is a dict with keys: `radarr_movies`, `sonarr_series`, `radarr_queue`, `sonarr_queue`, `qbit_torrents`, `seerr_requests`, `jellyfin_items` (each a list of raw dicts; missing/failed source → empty list).

### Task 8: Keying + base rows from arr (movies + series)

**Files:**
- Create: `tools/arr-dashboard/arr_dashboard/correlate.py`
- Create: `tools/arr-dashboard/tests/conftest.py`
- Test: `tools/arr-dashboard/tests/test_correlate.py`

- [ ] **Step 1: Write `tests/conftest.py` (fixture builder helpers)**

```python
def sources(**overrides):
    base = {
        "radarr_movies": [], "sonarr_series": [], "radarr_queue": [], "sonarr_queue": [],
        "qbit_torrents": [], "seerr_requests": [], "jellyfin_items": [],
    }
    base.update(overrides)
    return base
```

- [ ] **Step 2: Write the failing test**

```python
from arr_dashboard.correlate import correlate
from tests.conftest import sources


def test_radarr_movie_becomes_row():
    src = sources(radarr_movies=[
        {"id": 1, "title": "Ratatouille", "year": 2007, "tmdbId": 2062,
         "hasFile": True, "monitored": True,
         "movieFile": {"path": "/media/films/Ratatouille.mkv"}}])
    snap = correlate(src, "2026-06-18T00:00:00Z", [])
    row = snap.rows[0]
    assert row.key == "tmdb:2062"
    assert row.type == "movie"
    assert row.arr_app == "radarr"
    assert row.has_file is True
    assert row.disk_paths == ["/media/films/Ratatouille.mkv"]
    assert row.chain.imported is True


def test_sonarr_series_becomes_row():
    src = sources(sonarr_series=[
        {"id": 9, "title": "Supernatural", "year": 2005, "tvdbId": 78901,
         "monitored": True,
         "statistics": {"episodeCount": 22, "episodeFileCount": 22}}])
    snap = correlate(src, "t", [])
    row = snap.rows[0]
    assert row.key == "tvdb:78901"
    assert row.type == "series"
    assert row.has_file is True   # all episodes present
    assert row.chain.imported is True
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_correlate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arr_dashboard.correlate'`

- [ ] **Step 4: Implement the base of `arr_dashboard/correlate.py`**

```python
from arr_dashboard.models import ChainHealth, Download, Row, Snapshot


def _movie_row(m: dict) -> Row:
    path = (m.get("movieFile") or {}).get("path")
    has_file = bool(m.get("hasFile"))
    return Row(
        key=f"tmdb:{m['tmdbId']}",
        title=m.get("title", "?"),
        year=m.get("year"),
        type="movie",
        arr_app="radarr",
        monitored=m.get("monitored"),
        has_file=has_file,
        disk_paths=[path] if path else [],
        chain=ChainHealth(imported=has_file),
    )


def _series_row(s: dict) -> Row:
    st = s.get("statistics") or {}
    total = st.get("episodeCount", 0)
    have = st.get("episodeFileCount", 0)
    has_file = total > 0 and have >= total
    return Row(
        key=f"tvdb:{s['tvdbId']}",
        title=s.get("title", "?"),
        year=s.get("year"),
        type="series",
        arr_app="sonarr",
        monitored=s.get("monitored"),
        has_file=has_file,
        chain=ChainHealth(imported=has_file),
    )


def correlate(sources: dict, generated_at: str, stale_sources: list[str]) -> Snapshot:
    rows: dict[str, Row] = {}
    for m in sources.get("radarr_movies", []):
        if m.get("tmdbId"):
            r = _movie_row(m)
            rows[r.key] = r
    for s in sources.get("sonarr_series", []):
        if s.get("tvdbId"):
            r = _series_row(s)
            rows[r.key] = r
    return Snapshot(rows=list(rows.values()), generated_at=generated_at, stale_sources=stale_sources)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_correlate.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/correlate.py tools/arr-dashboard/tests/conftest.py tools/arr-dashboard/tests/test_correlate.py
git commit -m "feat(arr-dashboard): correlate base rows from arr movies/series"
```

### Task 9: Attach downloads (qBit via queue link) + grabbed/downloaded chain

**Files:**
- Modify: `tools/arr-dashboard/arr_dashboard/correlate.py`
- Test: `tools/arr-dashboard/tests/test_correlate.py`

- [ ] **Step 1: Write the failing test**

```python
def test_download_linked_via_queue_sets_chain():
    src = sources(
        radarr_movies=[{"id": 1, "title": "M", "tmdbId": 42, "hasFile": False, "monitored": True}],
        radarr_queue=[{"movieId": 1, "downloadId": "ABCDEF", "trackedDownloadStatus": "ok"}],
        qbit_torrents=[{"hash": "abcdef", "name": "M.2025.mkv", "state": "downloading",
                        "progress": 0.5, "category": "radarr-movies",
                        "save_path": "/data/x", "tracker": "http://t/announce"}])
    snap = correlate(src, "t", [])
    row = snap.rows[0]
    assert len(row.downloads) == 1
    assert row.downloads[0].infohash == "abcdef"
    assert row.chain.grabbed is True
    assert row.chain.downloaded is False   # progress 0.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_correlate.py::test_download_linked_via_queue_sets_chain -v`
Expected: FAIL (downloads empty, grabbed False)

- [ ] **Step 3: Implement** — extend `correlate` after building base rows:

```python
def _torrent_index(qbit: list[dict]) -> dict[str, dict]:
    return {t["hash"].lower(): t for t in qbit if t.get("hash")}


def _to_download(t: dict) -> Download:
    return Download(
        infohash=t["hash"].lower(),
        name=t.get("name", "?"),
        state=t.get("state", "?"),
        progress=float(t.get("progress", 0.0)),
        category=t.get("category"),
        tracker=(t.get("tracker") or None),
        save_path=t.get("save_path"),
    )
```

Then inside `correlate`, after rows are built and before returning, add an arr-id → row lookup and walk the queues:

```python
    by_arr_id = {("radarr", m["id"]): rows[f"tmdb:{m['tmdbId']}"]
                 for m in sources.get("radarr_movies", []) if m.get("tmdbId")}
    by_arr_id.update({("sonarr", s["id"]): rows[f"tvdb:{s['tvdbId']}"]
                      for s in sources.get("sonarr_series", []) if s.get("tvdbId")})
    tindex = _torrent_index(sources.get("qbit_torrents", []))

    for app, qkey, idkey in [("radarr", "radarr_queue", "movieId"),
                             ("sonarr", "sonarr_queue", "seriesId")]:
        for q in sources.get(qkey, []):
            row = by_arr_id.get((app, q.get(idkey)))
            if not row:
                continue
            row.chain.grabbed = True
            dl_id = (q.get("downloadId") or "").lower()
            t = tindex.get(dl_id)
            if t:
                d = _to_download(t)
                row.downloads.append(d)
                if d.progress >= 1.0:
                    row.chain.downloaded = True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_correlate.py -v`
Expected: PASS (all)

- [ ] **Step 5: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/correlate.py tools/arr-dashboard/tests/test_correlate.py
git commit -m "feat(arr-dashboard): link qBit downloads via arr queue + grabbed/downloaded chain"
```

### Task 10: Seerr requests → requested chain

**Files:**
- Modify: `tools/arr-dashboard/arr_dashboard/correlate.py`
- Test: `tools/arr-dashboard/tests/test_correlate.py`

- [ ] **Step 1: Write the failing test**

```python
def test_seerr_request_sets_requested_and_requester():
    src = sources(
        radarr_movies=[{"id": 1, "title": "M", "tmdbId": 42, "hasFile": False, "monitored": True}],
        seerr_requests=[{"id": 7, "type": "movie", "status": 2,
                         "media": {"tmdbId": 42}, "requestedBy": {"displayName": "Thomas"}}])
    snap = correlate(src, "t", [])
    row = snap.rows[0]
    assert row.chain.requested is True
    assert row.requested_by == "Thomas"
    assert row.request_status == "approved"


def test_seerr_request_with_no_arr_item_creates_pending_row():
    src = sources(seerr_requests=[{"id": 8, "type": "movie", "status": 1,
                                   "media": {"tmdbId": 99}, "requestedBy": {"displayName": "Emilie"}}])
    snap = correlate(src, "t", [])
    row = [r for r in snap.rows if r.key == "tmdb:99"][0]
    assert row.chain.requested is True
    assert row.chain.grabbed is False
    assert row.request_status == "pending"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_correlate.py::test_seerr_request_sets_requested_and_requester tests/test_correlate.py::test_seerr_request_with_no_arr_item_creates_pending_row -v`
Expected: FAIL

- [ ] **Step 3: Implement** — add a Seerr status map + a pass that matches by tmdb/tvdb, creating a stub row if none exists:

```python
_SEERR_STATUS = {1: "pending", 2: "approved", 3: "declined", 4: "partially-available", 5: "available"}


def _seerr_key(req: dict) -> str | None:
    media = req.get("media") or {}
    if req.get("type") == "movie" and media.get("tmdbId"):
        return f"tmdb:{media['tmdbId']}"
    if req.get("type") in ("tv", "series") and media.get("tvdbId"):
        return f"tvdb:{media['tvdbId']}"
    if media.get("tmdbId"):
        return f"tmdb:{media['tmdbId']}"
    return None
```

Then in `correlate`, after the queue pass:

```python
    for req in sources.get("seerr_requests", []):
        key = _seerr_key(req)
        if not key:
            continue
        row = rows.get(key)
        if row is None:
            row = Row(key=key, title=(req.get("media") or {}).get("title", key),
                      type="movie" if key.startswith("tmdb:") else "series")
            rows[key] = row
        row.chain.requested = True
        row.requested_by = (req.get("requestedBy") or {}).get("displayName")
        row.request_status = _SEERR_STATUS.get(req.get("status"), str(req.get("status")))
```

> Note: this pass adds to `rows` after the `by_arr_id`/queue passes used `rows`. Keep the ordering: base rows → queue/download → seerr. The stub row carries no arr_app (request not yet picked up).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_correlate.py -v`
Expected: PASS (all)

- [ ] **Step 5: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/correlate.py tools/arr-dashboard/tests/test_correlate.py
git commit -m "feat(arr-dashboard): correlate Seerr requests + pending stub rows"
```

### Task 11: Jellyfin presence → in_jellyfin chain

**Files:**
- Modify: `tools/arr-dashboard/arr_dashboard/correlate.py`
- Test: `tools/arr-dashboard/tests/test_correlate.py`

- [ ] **Step 1: Write the failing test**

```python
def test_jellyfin_presence_sets_in_jellyfin():
    src = sources(
        radarr_movies=[{"id": 1, "title": "Ratatouille", "tmdbId": 2062,
                        "hasFile": True, "monitored": True,
                        "movieFile": {"path": "/media/films/Ratatouille.mkv"}}],
        jellyfin_items=[{"Name": "Ratatouille", "Type": "Movie", "ProviderIds": {"Tmdb": "2062"}}])
    snap = correlate(src, "t", [])
    row = snap.rows[0]
    assert row.in_jellyfin is True
    assert row.chain.in_jellyfin is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_correlate.py::test_jellyfin_presence_sets_in_jellyfin -v`
Expected: FAIL (in_jellyfin False)

- [ ] **Step 3: Implement** — build a Jellyfin key set, then mark rows:

```python
def _jellyfin_keys(items: list[dict]) -> set[str]:
    keys = set()
    for it in items:
        pid = it.get("ProviderIds") or {}
        tmdb = pid.get("Tmdb") or pid.get("tmdb")
        tvdb = pid.get("Tvdb") or pid.get("tvdb")
        if tmdb:
            keys.add(f"tmdb:{tmdb}")
        if tvdb:
            keys.add(f"tvdb:{tvdb}")
    return keys
```

In `correlate`, after the seerr pass:

```python
    jf_keys = _jellyfin_keys(sources.get("jellyfin_items", []))
    for row in rows.values():
        if row.key in jf_keys:
            row.in_jellyfin = True
            row.chain.in_jellyfin = True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_correlate.py -v`
Expected: PASS (all)

- [ ] **Step 5: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/correlate.py tools/arr-dashboard/tests/test_correlate.py
git commit -m "feat(arr-dashboard): mark Jellyfin presence (chain end)"
```

### Task 12: Flags + problem-first sort

**Files:**
- Modify: `tools/arr-dashboard/arr_dashboard/correlate.py`
- Test: `tools/arr-dashboard/tests/test_correlate.py`

- [ ] **Step 1: Write the failing tests** (the spec's six cases)

```python
def _row_by_key(snap, key):
    return [r for r in snap.rows if r.key == key][0]


def test_flag_duplicate_two_downloads():
    src = sources(
        radarr_movies=[{"id": 1, "title": "M", "tmdbId": 42, "hasFile": False, "monitored": True}],
        radarr_queue=[{"movieId": 1, "downloadId": "AAA"}, {"movieId": 1, "downloadId": "BBB"}],
        qbit_torrents=[{"hash": "aaa", "name": "v1", "state": "downloading", "progress": 0.3},
                       {"hash": "bbb", "name": "v2", "state": "downloading", "progress": 0.1}])
    snap = correlate(src, "t", [])
    assert "doublon" in _row_by_key(snap, "tmdb:42").flags


def test_flag_owned_but_regrab():
    src = sources(
        radarr_movies=[{"id": 1, "title": "M", "tmdbId": 42, "hasFile": False, "monitored": True}],
        radarr_queue=[{"movieId": 1, "downloadId": "AAA"}],
        qbit_torrents=[{"hash": "aaa", "name": "v", "state": "downloading", "progress": 0.3}])
    snap = correlate(src, "t", [])
    assert "deja-possede-regrab" in _row_by_key(snap, "tmdb:42").flags


def test_flag_non_importe():
    src = sources(
        radarr_movies=[{"id": 1, "title": "M", "tmdbId": 42, "hasFile": False, "monitored": True}],
        radarr_queue=[{"movieId": 1, "downloadId": "AAA"}],
        qbit_torrents=[{"hash": "aaa", "name": "v", "state": "stalledUP",
                        "progress": 1.0, "save_path": "/data/x"}])
    snap = correlate(src, "t", [])
    flags = _row_by_key(snap, "tmdb:42").flags
    assert "non-importe" in flags


def test_flag_bloque():
    src = sources(
        radarr_movies=[{"id": 1, "title": "M", "tmdbId": 42, "hasFile": False, "monitored": True}],
        radarr_queue=[{"movieId": 1, "downloadId": "AAA"}],
        qbit_torrents=[{"hash": "aaa", "name": "v", "state": "missingFiles", "progress": 0.9}])
    snap = correlate(src, "t", [])
    assert "bloque" in _row_by_key(snap, "tmdb:42").flags


def test_flag_pas_dans_jellyfin():
    src = sources(radarr_movies=[{"id": 1, "title": "M", "tmdbId": 42, "hasFile": True,
                                  "monitored": True, "movieFile": {"path": "/media/x.mkv"}}])
    snap = correlate(src, "t", [])
    assert "pas-dans-jellyfin" in _row_by_key(snap, "tmdb:42").flags


def test_flag_ok_full_chain():
    src = sources(
        radarr_movies=[{"id": 1, "title": "M", "tmdbId": 42, "hasFile": True, "monitored": True,
                        "movieFile": {"path": "/media/x.mkv"}}],
        seerr_requests=[{"type": "movie", "status": 5, "media": {"tmdbId": 42},
                         "requestedBy": {"displayName": "T"}}],
        jellyfin_items=[{"Type": "Movie", "ProviderIds": {"Tmdb": "42"}}])
    snap = correlate(src, "t", [])
    row = _row_by_key(snap, "tmdb:42")
    assert row.flags == ["ok"]


def test_problem_rows_sorted_first():
    src = sources(radarr_movies=[
        {"id": 1, "title": "Good", "tmdbId": 1, "hasFile": True, "monitored": True,
         "movieFile": {"path": "/media/g.mkv"}},
        {"id": 2, "title": "Dup", "tmdbId": 2, "hasFile": False, "monitored": True}],
        radarr_queue=[{"movieId": 2, "downloadId": "AAA"}, {"movieId": 2, "downloadId": "BBB"}],
        qbit_torrents=[{"hash": "aaa", "name": "a", "state": "downloading", "progress": 0.1},
                       {"hash": "bbb", "name": "b", "state": "downloading", "progress": 0.1}],
        jellyfin_items=[{"Type": "Movie", "ProviderIds": {"Tmdb": "1"}}])
    snap = correlate(src, "t", [])
    assert snap.rows[0].key == "tmdb:2"   # problem first
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_correlate.py -v -k "flag or sorted"`
Expected: FAIL

- [ ] **Step 3: Implement** — add a flag computation + sort at the end of `correlate`, before constructing the Snapshot:

```python
def _compute_flags(row: Row) -> list[str]:
    flags: list[str] = []
    owned_evidence = bool(row.downloads) or bool(row.disk_paths)
    if len(row.downloads) > 1:
        flags.append("doublon")
    if row.has_file is False and owned_evidence:
        flags.append("deja-possede-regrab")
    if row.has_file is False and any(d.progress >= 1.0 for d in row.downloads):
        flags.append("non-importe")
    if any(d.state in ("stalledDL", "missingFiles", "error") for d in row.downloads):
        flags.append("bloque")
    if row.chain.imported and not row.chain.in_jellyfin:
        flags.append("pas-dans-jellyfin")
    if not flags and row.chain.imported and row.chain.in_jellyfin:
        flags.append("ok")
    return flags


def _sort_key(row: Row) -> tuple:
    is_ok = row.flags == ["ok"]
    return (is_ok, -len(row.flags), row.title.lower())
```

Then at the end of `correlate`:

```python
    for row in rows.values():
        row.flags = _compute_flags(row)
    ordered = sorted(rows.values(), key=_sort_key)
    return Snapshot(rows=ordered, generated_at=generated_at, stale_sources=stale_sources)
```

(Replace the previous `return Snapshot(...)`.)

- [ ] **Step 4: Run the full correlate suite**

Run: `uv run pytest tests/test_correlate.py -v`
Expected: PASS (all)

- [ ] **Step 5: Triad + commit**

Run: `uv run ruff format --check . && uv run ruff check . && uv run mypy arr_dashboard`
Expected: pass.

```bash
git add tools/arr-dashboard/arr_dashboard/correlate.py tools/arr-dashboard/tests/test_correlate.py
git commit -m "feat(arr-dashboard): flags (dup/owned-regrab/non-importe/bloque/pas-jellyfin/ok) + problem-first sort"
```

---

## Phase 4 — Sources (I/O) + cache/refresher

### Task 13: `sources.fetch_all` with graceful degradation

**Files:**
- Create: `tools/arr-dashboard/arr_dashboard/sources.py`
- Test: `tools/arr-dashboard/tests/test_sources.py`

- [ ] **Step 1: Write the failing test** (respx-mock the live endpoints; one source fails → stale)

```python
import httpx
import respx
from arr_dashboard.settings import Settings
from arr_dashboard.sources import fetch_all


def _settings():
    return Settings(
        sonarr_url="http://sonarr:8989", radarr_url="http://radarr:7878",
        qbittorrent_url="http://qb:8080", seerr_url="http://seerr:5055",
        jellyfin_url="http://jf:8096", sonarr_api_key="k", radarr_api_key="k",
        seerr_api_key="k", jellyfin_api_key="k", qbt_user="u", qbt_pass="p")


@respx.mock
def test_fetch_all_marks_failed_source_stale():
    respx.get("http://radarr:7878/api/v3/movie").mock(return_value=httpx.Response(200, json=[{"id": 1, "tmdbId": 42, "title": "M"}]))
    respx.get("http://radarr:7878/api/v3/queue").mock(return_value=httpx.Response(200, json={"records": []}))
    respx.get("http://sonarr:8989/api/v3/series").mock(return_value=httpx.Response(200, json=[]))
    respx.get("http://sonarr:8989/api/v3/queue").mock(return_value=httpx.Response(200, json={"records": []}))
    respx.post("http://qb:8080/api/v2/auth/login").mock(return_value=httpx.Response(200, text="Ok.", headers={"set-cookie": "SID=x"}))
    respx.get("http://qb:8080/api/v2/torrents/info").mock(return_value=httpx.Response(200, json=[]))
    respx.get("http://seerr:5055/api/v1/request").mock(return_value=httpx.Response(200, json={"results": []}))
    # Jellyfin DOWN
    respx.get("http://jf:8096/Items").mock(return_value=httpx.Response(500))

    src, stale = fetch_all(_settings())
    assert src["radarr_movies"][0]["tmdbId"] == 42
    assert "jellyfin" in stale
    assert src["jellyfin_items"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_sources.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arr_dashboard.sources'`

- [ ] **Step 3: Implement `arr_dashboard/sources.py`** — construct arrconf clients, fetch each source in its own try/except, collecting stale names. (Verify client constructor signatures against `client_base.py`; adjust if Sonarr uses a different method name for `/series` — use `.get("/series")` if no named method.)

```python
import logging
from arrconf.client_base import (
    JellyfinClient, QbittorrentClient, RadarrClient, SonarrClient, SeerrClient,
)
from arr_dashboard.settings import Settings

log = logging.getLogger("arr_dashboard.sources")
EMPTY = {
    "radarr_movies": [], "sonarr_series": [], "radarr_queue": [], "sonarr_queue": [],
    "qbit_torrents": [], "seerr_requests": [], "jellyfin_items": [],
}


def _safe(name: str, fn, stale: list[str]):
    try:
        return fn()
    except Exception as exc:  # graceful degradation: one source down != dashboard down
        log.warning("source %s failed: %s", name, exc)
        stale.append(name)
        return None


def fetch_all(settings: Settings) -> tuple[dict, list[str]]:
    src = dict(EMPTY)
    stale: list[str] = []

    if settings.radarr_api_key:
        radarr = RadarrClient(settings.radarr_url, settings.radarr_api_key)
        src["radarr_movies"] = _safe("radarr", lambda: radarr.get("/movie"), stale) or []
        src["radarr_queue"] = _safe("radarr_queue", lambda: radarr.list_queue(), stale) or []
    if settings.sonarr_api_key:
        sonarr = SonarrClient(settings.sonarr_url, settings.sonarr_api_key)
        src["sonarr_series"] = _safe("sonarr", lambda: sonarr.get("/series"), stale) or []
        src["sonarr_queue"] = _safe("sonarr_queue", lambda: sonarr.list_queue(), stale) or []
    if settings.qbt_user:
        src["qbit_torrents"] = _safe(
            "qbittorrent",
            lambda: QbittorrentClient(settings.qbittorrent_url, settings.qbt_user, settings.qbt_pass).list_torrents(),
            stale) or []
    if settings.seerr_api_key:
        seerr = SeerrClient(settings.seerr_url, settings.seerr_api_key)
        src["seerr_requests"] = _safe("seerr", lambda: seerr.list_requests(), stale) or []
    if settings.jellyfin_api_key:
        jf = JellyfinClient(settings.jellyfin_url, settings.jellyfin_api_key)
        src["jellyfin_items"] = _safe("jellyfin", lambda: jf.list_items(), stale) or []

    return src, stale
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_sources.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/sources.py tools/arr-dashboard/tests/test_sources.py
git commit -m "feat(arr-dashboard): fetch_all sources with graceful degradation"
```

### Task 14: SnapshotCache + refresher

**Files:**
- Create: `tools/arr-dashboard/arr_dashboard/cache.py`
- Test: `tools/arr-dashboard/tests/test_cache.py`

- [ ] **Step 1: Write the failing test**

```python
from arr_dashboard.cache import SnapshotCache
from arr_dashboard.models import Snapshot


def test_cache_starts_initializing_then_stores():
    cache = SnapshotCache()
    assert cache.get().initializing is True
    cache.set(Snapshot(rows=[], generated_at="t"))
    assert cache.get().initializing is False
    assert cache.get().generated_at == "t"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cache.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arr_dashboard.cache'`

- [ ] **Step 3: Implement `arr_dashboard/cache.py`**

```python
import asyncio
import logging
from datetime import datetime, timezone
from arr_dashboard.correlate import correlate
from arr_dashboard.models import Snapshot
from arr_dashboard.settings import Settings
from arr_dashboard.sources import fetch_all

log = logging.getLogger("arr_dashboard.cache")


class SnapshotCache:
    def __init__(self) -> None:
        self._snapshot = Snapshot(initializing=True)

    def get(self) -> Snapshot:
        return self._snapshot

    def set(self, snapshot: Snapshot) -> None:
        self._snapshot = snapshot


def build_snapshot(settings: Settings) -> Snapshot:
    src, stale = fetch_all(settings)
    now = datetime.now(timezone.utc).isoformat()
    return correlate(src, now, stale)


async def refresher_loop(settings: Settings, cache: SnapshotCache) -> None:
    while True:
        try:
            cache.set(await asyncio.to_thread(build_snapshot, settings))
        except Exception as exc:  # never let the loop die
            log.error("refresh failed: %s", exc)
        await asyncio.sleep(settings.refresh_seconds)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cache.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/cache.py tools/arr-dashboard/tests/test_cache.py
git commit -m "feat(arr-dashboard): SnapshotCache + 30s refresher loop"
```

---

## Phase 5 — FastAPI app

### Task 15: App endpoints + startup refresher + static mount

**Files:**
- Create: `tools/arr-dashboard/arr_dashboard/app.py`, `tools/arr-dashboard/arr_dashboard/__main__.py`
- Test: `tools/arr-dashboard/tests/test_app.py`

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient
from arr_dashboard.app import create_app
from arr_dashboard.cache import SnapshotCache
from arr_dashboard.models import Row, Snapshot, ChainHealth


def test_dashboard_endpoint_serves_cache():
    cache = SnapshotCache()
    cache.set(Snapshot(rows=[Row(key="tmdb:1", title="M", type="movie",
                                 chain=ChainHealth(), flags=["ok"])],
                       generated_at="t", stale_sources=["jellyfin"]))
    app = create_app(cache=cache, start_refresher=False)
    client = TestClient(app)
    r = client.get("/api/dashboard")
    assert r.status_code == 200
    body = r.json()
    assert body["rows"][0]["key"] == "tmdb:1"
    assert body["stale_sources"] == ["jellyfin"]


def test_healthz():
    app = create_app(cache=SnapshotCache(), start_refresher=False)
    assert TestClient(app).get("/healthz").status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_app.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arr_dashboard.app'`

- [ ] **Step 3: Implement `arr_dashboard/app.py`** (mirror arrconf-ui's static-mount approach; guard the dist mount so tests pass without a built frontend)

```python
import asyncio
import contextlib
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from arr_dashboard.cache import SnapshotCache, refresher_loop
from arr_dashboard.settings import Settings, load_settings

_DIST = Path(__file__).parent.parent / "web" / "dist"


def create_app(*, cache: SnapshotCache | None = None, settings: Settings | None = None,
               start_refresher: bool = True) -> FastAPI:
    cache = cache or SnapshotCache()

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        task = None
        if start_refresher:
            task = asyncio.create_task(refresher_loop(settings or load_settings(), cache))
        yield
        if task:
            task.cancel()

    app = FastAPI(title="arr-dashboard", lifespan=lifespan)

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/api/dashboard")
    def dashboard() -> dict:
        return cache.get().model_dump(mode="json")

    @app.get("/api/dashboard/{key}")
    def dashboard_detail(key: str) -> dict:
        for row in cache.get().rows:
            if row.key == key:
                return row.model_dump(mode="json")
        return {"error": "not found", "key": key}

    if _DIST.is_dir():
        app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="web")

    return app
```

- [ ] **Step 4: Create `arr_dashboard/__main__.py`**

```python
import uvicorn
from arr_dashboard.app import create_app
from arr_dashboard.settings import load_settings


def main() -> None:
    settings = load_settings()
    host, _, port = settings.bind.partition(":")
    uvicorn.run(create_app(settings=settings), host=host or "0.0.0.0", port=int(port or "8080"))


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests + triad + commit**

Run: `uv run pytest -v && uv run ruff format --check . && uv run ruff check . && uv run mypy arr_dashboard`
Expected: all pass (full suite green).

```bash
git add tools/arr-dashboard/arr_dashboard/app.py tools/arr-dashboard/arr_dashboard/__main__.py tools/arr-dashboard/tests/test_app.py
git commit -m "feat(arr-dashboard): FastAPI app, endpoints, startup refresher, static mount"
```

---

## Phase 6 — Frontend (Svelte 5, read-only)

Mirror `tools/arrconf-ui/web/` exactly for tooling (Vite, svelte.config, package.json, IBM Plex, dark theme, FR i18n). The dashboard UI is a single table view; no schema-driven forms.

### Task 16: Scaffold web build (copy arrconf-ui tooling)

**Files:**
- Create: `tools/arr-dashboard/web/package.json`, `vite.config.ts`, `svelte.config.js`, `index.html`, `src/main.ts`

- [ ] **Step 1:** Copy the Vite/Svelte tooling files from `tools/arrconf-ui/web/` (package.json deps, vite.config.ts, svelte.config.js, index.html, src/main.ts), changing only the app title to "arr-dashboard". Build must output to `web/dist/` (match arrconf-ui's `build.outDir`).

- [ ] **Step 2: Verify build tooling installs**

Run: `cd tools/arr-dashboard/web && npm install && npm run build`
Expected: produces `web/dist/index.html` (even with a placeholder App).

- [ ] **Step 3: Commit**

```bash
git add tools/arr-dashboard/web/package.json tools/arr-dashboard/web/vite.config.ts tools/arr-dashboard/web/svelte.config.js tools/arr-dashboard/web/index.html tools/arr-dashboard/web/src/main.ts
git commit -m "chore(arr-dashboard): web build tooling (mirror arrconf-ui)"
```

### Task 17: API client + types

**Files:**
- Create: `tools/arr-dashboard/web/src/api.ts`

- [ ] **Step 1: Implement `src/api.ts`** (mirror arrconf-ui's fetch wrapper)

```typescript
export interface ChainHealth { requested: boolean; grabbed: boolean; downloaded: boolean; imported: boolean; in_jellyfin: boolean; }
export interface Download { infohash: string; name: string; state: string; progress: number; category: string | null; tracker: string | null; save_path: string | null; }
export interface Row {
  key: string; title: string; year: number | null; type: "movie" | "series";
  requested_by: string | null; request_status: string | null;
  arr_app: string | null; monitored: boolean | null; has_file: boolean | null; quality: string | null;
  downloads: Download[]; disk_paths: string[]; in_jellyfin: boolean; chain: ChainHealth; flags: string[];
}
export interface Snapshot { rows: Row[]; generated_at: string | null; stale_sources: string[]; initializing: boolean; }

export async function getDashboard(): Promise<Snapshot> {
  const res = await fetch("/api/dashboard");
  if (!res.ok) throw new Error(`dashboard ${res.status}`);
  return res.json();
}
```

- [ ] **Step 2: Commit**

```bash
git add tools/arr-dashboard/web/src/api.ts
git commit -m "feat(arr-dashboard): web api client + types"
```

### Task 18: Dashboard table view

**Files:**
- Create: `tools/arr-dashboard/web/src/App.svelte`, `src/lib/ChainPastilles.svelte`, `src/lib/RowDetail.svelte`, `src/i18n/fr.ts`

- [ ] **Step 1: Implement `src/lib/ChainPastilles.svelte`** (the 5-pastille chain indicator)

```svelte
<script lang="ts">
  import type { ChainHealth } from "../api";
  let { chain, flags }: { chain: ChainHealth; flags: string[] } = $props();
  const steps = $derived([
    { on: chain.requested, label: "demandé" },
    { on: chain.grabbed, label: "grab" },
    { on: chain.downloaded, label: "download" },
    { on: chain.imported, label: "importé" },
    { on: chain.in_jellyfin, label: "jellyfin" },
  ]);
  const broken = $derived(flags.length > 0 && !flags.includes("ok"));
</script>

<span class="chain" class:broken>
  {#each steps as s}
    <span class="dot" class:on={s.on} title={s.label}>{s.on ? "✓" : "○"}</span>
  {/each}
</span>

<style>
  .chain { font-family: "IBM Plex Mono", monospace; letter-spacing: 1px; }
  .dot { opacity: 0.4; }
  .dot.on { opacity: 1; color: #4ade80; }
  .broken .dot:not(.on) { color: #f87171; opacity: 0.9; }
</style>
```

- [ ] **Step 2: Implement `src/App.svelte`** (table, problems-first already sorted by backend, filter toggle, 30s poll, stale banner)

```svelte
<script lang="ts">
  import { getDashboard, type Snapshot, type Row } from "./api";
  import ChainPastilles from "./lib/ChainPastilles.svelte";
  import RowDetail from "./lib/RowDetail.svelte";

  let snap: Snapshot | null = $state(null);
  let error: string | null = $state(null);
  let problemsOnly = $state(true);
  let expanded: string | null = $state(null);

  async function refresh() {
    try { snap = await getDashboard(); error = null; }
    catch (e) { error = String(e); }
  }
  $effect(() => { refresh(); const id = setInterval(refresh, 30000); return () => clearInterval(id); });

  const visible = $derived(
    !snap ? [] : snap.rows.filter((r: Row) => !problemsOnly || !(r.flags.length === 1 && r.flags[0] === "ok")));
</script>

<header>
  <h1>arr-dashboard</h1>
  <label><input type="checkbox" bind:checked={problemsOnly} /> Problèmes seulement</label>
  {#if snap?.stale_sources?.length}<span class="stale">⚠ sources indisponibles: {snap.stale_sources.join(", ")}</span>{/if}
</header>

{#if error}<p class="err">{error}</p>{/if}
{#if snap?.initializing}<p>Initialisation…</p>{/if}

<table>
  <thead><tr><th>Chaîne</th><th>Titre</th><th>Demandé</th><th>Download</th><th>Disque</th><th>Jellyfin</th><th>Flags</th></tr></thead>
  <tbody>
    {#each visible as row (row.key)}
      <tr onclick={() => expanded = expanded === row.key ? null : row.key}>
        <td><ChainPastilles chain={row.chain} flags={row.flags} /></td>
        <td>{row.title}{#if row.year} ({row.year}){/if}</td>
        <td>{row.requested_by ?? "—"}</td>
        <td>{#if row.downloads.length}{row.downloads.length > 1 ? `${row.downloads.length} torrents` : `${Math.round(row.downloads[0].progress * 100)}% ${row.downloads[0].tracker ?? ""}`}{:else}—{/if}</td>
        <td>{row.disk_paths.length ? (row.disk_paths[0].startsWith("/media") ? "/media" : "/data") : "✗"}</td>
        <td>{row.in_jellyfin ? "✓" : "✗"}</td>
        <td class="flags">{row.flags.join(", ")}</td>
      </tr>
      {#if expanded === row.key}<tr><td colspan="7"><RowDetail {row} /></td></tr>{/if}
    {/each}
  </tbody>
</table>

<style>
  :global(body) { background: #0f1115; color: #e5e7eb; font-family: "IBM Plex Sans", sans-serif; }
  header { display: flex; gap: 1.5rem; align-items: center; padding: 1rem; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 0.4rem 0.7rem; border-bottom: 1px solid #1f2430; }
  tbody tr { cursor: pointer; }
  tbody tr:hover { background: #161a22; }
  .flags { color: #fbbf24; }
  .stale { color: #f87171; }
  .err { color: #f87171; padding: 0 1rem; }
</style>
```

- [ ] **Step 3: Implement `src/lib/RowDetail.svelte`** (expandable detail: hashes, paths, ids, flag reasons)

```svelte
<script lang="ts">
  import type { Row } from "../api";
  let { row }: { row: Row } = $props();
</script>

<div class="detail">
  <div><strong>key</strong> {row.key} · <strong>arr</strong> {row.arr_app ?? "—"} · <strong>quality</strong> {row.quality ?? "—"} · <strong>monitored</strong> {row.monitored} · <strong>hasFile</strong> {row.has_file}</div>
  {#if row.downloads.length}
    <div><strong>downloads:</strong>
      <ul>{#each row.downloads as d}<li>{d.name} — {d.state} {Math.round(d.progress * 100)}% [{d.category ?? "?"}] {d.infohash}</li>{/each}</ul>
    </div>
  {/if}
  {#if row.disk_paths.length}<div><strong>disque:</strong> {row.disk_paths.join(", ")}</div>{/if}
</div>

<style>.detail { font-family: "IBM Plex Mono", monospace; font-size: 0.8rem; padding: 0.5rem 1rem; color: #9ca3af; } ul { margin: 0.2rem 0; }</style>
```

- [ ] **Step 4: Create `src/i18n/fr.ts`** (mirror arrconf-ui; strings are inline-French above, so this can be a minimal stub for parity)

```typescript
export const fr = {
  problemsOnly: "Problèmes seulement",
  staleSources: "sources indisponibles",
  initializing: "Initialisation…",
};
```

- [ ] **Step 5: Build + commit**

Run: `cd tools/arr-dashboard/web && npm run build`
Expected: `web/dist/` regenerated, no TypeScript/Svelte errors.

```bash
git add tools/arr-dashboard/web/src/
git commit -m "feat(arr-dashboard): read-only dashboard table + chain pastilles + row detail"
```

---

## Phase 7 — Containerization, chart, CI

### Task 19: Dockerfile

**Files:**
- Create: `tools/arr-dashboard/Dockerfile`

- [ ] **Step 1: Implement** (multi-stage: node builds web, python runtime; mirror `tools/arrconf-ui/Dockerfile`; the python stage must `pip install ../arrconf` or vendor it — copy the arrconf package into the build context)

```dockerfile
# syntax=docker/dockerfile:1
FROM node:22-slim AS web
WORKDIR /web
COPY tools/arr-dashboard/web/package*.json ./
RUN npm ci
COPY tools/arr-dashboard/web/ ./
RUN npm run build

FROM python:3.13-slim AS runtime
RUN pip install --no-cache-dir uv
WORKDIR /app
# arrconf is a path dependency; copy it into the image build context (build from repo root)
COPY tools/arrconf/ /arrconf/
COPY tools/arr-dashboard/pyproject.toml tools/arr-dashboard/uv.lock ./
COPY tools/arr-dashboard/arr_dashboard/ ./arr_dashboard/
COPY --from=web /web/dist/ ./web/dist/
RUN uv sync --no-dev --frozen
USER 1000:1000
EXPOSE 8080
CMD ["uv", "run", "python", "-m", "arr_dashboard"]
```

> The `[tool.uv.sources] arrconf = { path = "../arrconf" }` resolves to `/arrconf` here — adjust the relative path or use an absolute path env so `uv sync` finds it at `/arrconf`. Build context = repo root (`docker build -f tools/arr-dashboard/Dockerfile .`). Verify the arrconf path resolution during the first build and fix the source path accordingly.

- [ ] **Step 2: Build locally to verify**

Run: `docker build -f tools/arr-dashboard/Dockerfile -t arr-dashboard:dev .`
Expected: image builds; `docker run --rm -p 8080:8080 arr-dashboard:dev` then `curl localhost:8080/healthz` → `{"status":"ok"}`.

- [ ] **Step 3: Commit**

```bash
git add tools/arr-dashboard/Dockerfile
git commit -m "build(arr-dashboard): multi-stage Dockerfile"
```

### Task 20: Image build workflow

**Files:**
- Create: `.github/workflows/arr-dashboard-image.yml` (mirror `.github/workflows/arrconf-mcp-image.yml`)

- [ ] **Step 1: Implement** — copy `arrconf-mcp-image.yml`, changing: image name → `ghcr.io/tom333/arr-stack-arr-dashboard`, Dockerfile path → `tools/arr-dashboard/Dockerfile`, build context → repo root, path filter → `tools/arr-dashboard/**` and `tools/arrconf/**` (since it vendors arrconf), and the `repository_dispatch` event_type → `arr-dashboard-image-build` consuming `github.event.client_payload.tag` for ref + semver (exactly like arrconf-mcp).

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/arr-dashboard-image.yml
git commit -m "ci(arr-dashboard): GHCR image build workflow"
```

### Task 21: tests.yml job

**Files:**
- Modify: `.github/workflows/tests.yml`

- [ ] **Step 1: Add a job** `arr-dashboard` mirroring the `arrconf-ui-backend` job: `cd tools/arr-dashboard`, `uv sync`, run `uv run ruff format --check . && uv run ruff check . && uv run mypy arr_dashboard && uv run pytest --cov=arr_dashboard --cov-fail-under=70`. Add a frontend build job mirroring `arrconf-ui-frontend` (`cd tools/arr-dashboard/web && npm ci && npm run build`).

- [ ] **Step 2: Verify YAML** locally: `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/tests.yml'))"` → no error.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/tests.yml
git commit -m "ci(arr-dashboard): test + frontend-build jobs"
```

### Task 22: Chart alias + values + alias-unpack loop

**Files:**
- Modify: `charts/arr-stack/Chart.yaml`, `charts/arr-stack/Chart.lock`, `charts/arr-stack/values.yaml`, `.github/workflows/chart-lint.yml`, `README.md`

- [ ] **Step 1: Add the alias** to `charts/arr-stack/Chart.yaml` dependencies (mirror the `arrconf-mcp` alias entry):

```yaml
  - name: app-template
    alias: arr-dashboard
    version: 5.0.0
    repository: https://bjw-s-labs.github.io/helm-charts
```

- [ ] **Step 2: Regenerate the lock**

Run: `helm dependency update charts/arr-stack/`
Expected: `Chart.lock` updated, no error.

- [ ] **Step 3: Add the values block** to `charts/arr-stack/values.yaml` (mirror the `arrconf-mcp:` block: ClusterIP, envFrom arrconf-env, /healthz probes; add the URL env defaults; renovate annotation):

```yaml
arr-dashboard:
  controllers:
    main:
      containers:
        main:
          image:
            # renovate: image=ghcr.io/tom333/arr-stack-arr-dashboard
            repository: ghcr.io/tom333/arr-stack-arr-dashboard
            tag: 0.1.0
          env:
            DASHBOARD_REFRESH_SECONDS: "30"
            DASHBOARD_BIND: "0.0.0.0:8080"
          envFrom:
            - secretRef:
                name: arrconf-env
          probes:
            liveness:
              enabled: true
              custom: true
              spec:
                httpGet: { path: /healthz, port: 8080 }
            readiness:
              enabled: true
              custom: true
              spec:
                httpGet: { path: /healthz, port: 8080 }
  service:
    main:
      controller: main
      ports:
        http:
          port: 8080
```

> Match the exact app-template 5.0.0 schema used by the `arrconf-mcp` block already in this file — copy its structure verbatim and change names/image/env. Do not invent fields.

- [ ] **Step 4: Add `arr-dashboard` to the alias-unpack loop** in `.github/workflows/chart-lint.yml` and the README "Vérification locale" loop (the `for alias in sonarr radarr … arrconf configarr arrconf-mcp` list → append `arr-dashboard`).

- [ ] **Step 5: Verify chart renders**

Run (from repo root, after the alias-unpack workaround):
```bash
helm dependency build charts/arr-stack/
tar -xzf charts/arr-stack/charts/app-template-5.0.0.tgz -C charts/arr-stack/charts/
for a in sonarr radarr prowlarr qbittorrent cleanuparr seerr flaresolverr jellyfin arrconf configarr arrconf-mcp arr-dashboard; do
  [ ! -d "charts/arr-stack/charts/$a" ] && cp -r charts/arr-stack/charts/app-template "charts/arr-stack/charts/$a"
done
helm template charts/arr-stack/ -f examples/values-prod.yaml | kubeconform -strict -ignore-missing-schemas
```
Expected: renders, kubeconform passes, an `arr-dashboard` Deployment + Service present.

- [ ] **Step 6: Commit**

```bash
git add charts/arr-stack/Chart.yaml charts/arr-stack/Chart.lock charts/arr-stack/values.yaml .github/workflows/chart-lint.yml README.md
git commit -m "feat(chart): ship arr-dashboard (alias + values + CI unpack)"
```

---

## Phase 8 — Finalize

### Task 23: Full local verification + finishing

- [ ] **Step 1: arrconf triad (read-methods)**

Run: `cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy arrconf && uv run pytest -q`
Expected: pass.

- [ ] **Step 2: arr-dashboard triad + tests + coverage**

Run: `cd tools/arr-dashboard && uv run ruff format --check . && uv run ruff check . && uv run mypy arr_dashboard && uv run pytest --cov=arr_dashboard --cov-report=term-missing`
Expected: pass; `correlate.py` ≥90%, overall ≥70%.

- [ ] **Step 3: Frontend build**

Run: `cd tools/arr-dashboard/web && npm run build`
Expected: clean build.

- [ ] **Step 4: Chart render** (as Task 22 Step 5) — passes.

- [ ] **Step 5: Finish the branch**

Use **superpowers:finishing-a-development-branch**: verify tests pass, then present merge/PR options. Do NOT push to `main` directly (auto-tagger + Renovate fire on push). Prefer a PR. The arrconf image co-bump + the release tag for `arr-dashboard:0.1.0` are handled at release time per the repo's "Accumulated-bumps escape hatch" (push main → wait for chart-lint `tag` job → push the final `vX.Y.Z` tag so GHCR builds the image the values.yaml expects).

---

## Notes for the implementer

- **No secrets in code/repo.** All keys come from env (`arrconf-env`). Tests use fake keys.
- **Mirror, don't invent.** For Dockerfile, chart values, CI jobs, and Svelte tooling, copy the working `arrconf-ui` / `arrconf-mcp` equivalents and adapt names. Verify the exact app-template 5.0.0 values schema against the existing `arrconf-mcp:` block.
- **Verify client signatures** in `tools/arrconf/arrconf/client_base.py` before writing Phase 1 — adjust `.get()` JSON-vs-Response handling and constructor args to match reality.
- **Series granularity is series-level in V1** (episode rollup via statistics). Per-episode rows = V2.
- **Actions are V2** — the rows already carry infohashes + arr ids + paths needed to act later.
```
