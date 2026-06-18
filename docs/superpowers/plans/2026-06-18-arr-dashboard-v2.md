# arr-dashboard V2.0 Implementation Plan (import action)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a serialized, oauth2-protected "import" corrective action to the arr-dashboard so the operator fixes `non-importe` / `deja-possede-regrab` rows in one click — forcing Sonarr/Radarr to import the existing downloaded file (Copy, preserving the seed).

**Architecture:** Extend the existing `arr-dashboard` FastAPI+Svelte service (V1 read-only, shipped v0.32.0) with a write layer: `POST /api/actions/import` enqueues a job; a single background worker runs imports strictly one-at-a-time (no concurrent cross-fs copies → no NAS meltdown); `GET /api/actions` exposes queue state. The service gets an oauth2-proxy ingress. New arrconf client write-methods drive the arr `ManualImport` command.

**Tech Stack:** Python 3.13, FastAPI, httpx (arrconf clients), pydantic v2, pytest+respx, asyncio, uv. Svelte 5. Helm bjw-s/app-template. Reference: `docs/superpowers/specs/2026-06-18-arr-dashboard-v2-design.md`.

**Branch:** `feat/arr-dashboard-v2` (the V2 spec commit lives here).

---

## File Structure

```
tools/arrconf/arrconf/client_base.py        # MODIFY: add manual_import_candidates + manual_import on _ArrV3Client
tools/arrconf/tests/test_client_read_methods.py  # MODIFY: respx tests for the 2 new methods

tools/arr-dashboard/arr_dashboard/
  models.py        # MODIFY: Download.size; Row.arr_id; + new ActionJob model
  correlate.py     # MODIFY: set Download.size (from qBit size) + Row.arr_id (arr id)
  actions.py       # CREATE: ActionJob states + ImportQueue (serialized worker + job list)
  import_runner.py # CREATE: perform_import(row, client) — resolve file → ManualImport Copy → poll
  app.py           # MODIFY: POST /api/actions/import, GET /api/actions, wire queue+worker in lifespan
tools/arr-dashboard/tests/
  test_models.py        # MODIFY: ActionJob + new fields
  test_correlate.py     # MODIFY: arr_id + size assertions
  test_actions.py       # CREATE: queue serialization + state machine (fake perform)
  test_import_runner.py # CREATE: perform_import with respx-mocked arr
  test_app.py           # MODIFY: action endpoints (confirm gate, enqueue, list)

tools/arr-dashboard/web/src/
  api.ts                     # MODIFY: Download.size; postImport(); getActions(); ActionJob type
  lib/ImportButton.svelte    # CREATE
  lib/ConfirmDialog.svelte   # CREATE
  lib/ActionsPanel.svelte    # CREATE
  App.svelte                 # MODIFY: wire button + dialog + panel

charts/arr-stack/values.yaml # MODIFY: add ingress block to arr-dashboard + co-bump arrconf & arr-dashboard image tags (at release)
```

**Before starting, read:** `tools/arrconf/arrconf/client_base.py` (confirm `_ArrV3Client`, `.get(path)` returns parsed JSON, `.post(path, json)` signature), the V1 modules above (exact field names: `Download(infohash,name,state,progress,category,tracker,save_path)`, `Row(key,title,year,type,requested_by,request_status,arr_app,monitored,has_file,quality,downloads,disk_paths,in_jellyfin,chain,flags)`, `correlate` passes base→queue→seerr→jellyfin→flags, `app.py create_app(*, cache, settings, start_refresher)` + lifespan starts `refresher_loop`), and the `sonarr:` ingress block in `charts/arr-stack/values.yaml` (lines ~31-48) to mirror.

---

## Phase 1 — arrconf write-methods

Run from `tools/arrconf/`.

### Task 1: `manual_import_candidates`

**Files:** Modify `arrconf/client_base.py` (`_ArrV3Client`); Test `tests/test_client_read_methods.py`.

- [ ] **Step 1: Write the failing test** (append):

```python
@respx.mock
def test_radarr_manual_import_candidates():
    respx.get("http://r:7878/api/v3/manualimport").mock(
        return_value=httpx.Response(200, json=[
            {"path": "/data/x/M.mkv", "movie": {"id": 42}, "quality": {}, "rejections": []}]))
    client = RadarrClient("http://r:7878", "key")
    out = client.manual_import_candidates("/data/x")
    assert out[0]["movie"]["id"] == 42
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_client_read_methods.py::test_radarr_manual_import_candidates -v`
Expected: FAIL — `AttributeError: ... 'manual_import_candidates'`

- [ ] **Step 3: Implement** (in `_ArrV3Client`, mirror the Phase-1 typed pattern):

```python
    def manual_import_candidates(self, folder: str) -> list[dict[str, Any]]:
        """Importable file candidates under a download folder (GET /manualimport)."""
        import urllib.parse

        q = urllib.parse.quote(folder)
        data: list[dict[str, Any]] = self.get(f"/manualimport?folder={q}&filterExistingFiles=true")
        return data or []
```

> `Any` is already imported in client_base from Phase 1; if not, add `from typing import Any`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_client_read_methods.py::test_radarr_manual_import_candidates -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/arrconf/arrconf/client_base.py tools/arrconf/tests/test_client_read_methods.py
git commit -m "feat(arrconf): _ArrV3Client.manual_import_candidates"
```

### Task 2: `manual_import`

**Files:** Modify `arrconf/client_base.py`; Test `tests/test_client_read_methods.py`.

- [ ] **Step 1: Write the failing test** (append):

```python
@respx.mock
def test_radarr_manual_import_posts_copy_command():
    route = respx.post("http://r:7878/api/v3/command").mock(
        return_value=httpx.Response(201, json={"id": 99, "name": "ManualImport", "status": "started"}))
    client = RadarrClient("http://r:7878", "key")
    out = client.manual_import([{"path": "/data/x/M.mkv", "movieId": 42}], mode="Copy")
    assert out["id"] == 99
    body = json.loads(route.calls.last.request.content)
    assert body["name"] == "ManualImport"
    assert body["importMode"] == "Copy"
    assert body["files"][0]["movieId"] == 42
```

> Add `import json` at the top of the test file if not present.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_client_read_methods.py::test_radarr_manual_import_posts_copy_command -v`
Expected: FAIL — `AttributeError: ... 'manual_import'`

- [ ] **Step 3: Implement** (verify `self.post(path, json_body)` is the real base signature first; adapt if it differs):

```python
    def manual_import(self, files: list[dict[str, Any]], mode: str = "Copy") -> dict[str, Any]:
        """Trigger a ManualImport command (Copy by default — never Move; preserves seeds)."""
        result: dict[str, Any] = self.post(
            "/command", {"name": "ManualImport", "importMode": mode, "files": files}
        )
        return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_client_read_methods.py::test_radarr_manual_import_posts_copy_command -v`
Expected: PASS

- [ ] **Step 5: Triad + commit**

Run: `uv run ruff format --check . && uv run ruff check . && uv run mypy arrconf`
Expected: pass.

```bash
git add tools/arrconf/arrconf/client_base.py tools/arrconf/tests/test_client_read_methods.py
git commit -m "feat(arrconf): _ArrV3Client.manual_import (Copy command)"
```

---

## Phase 2 — Model + correlate additions

Run from `tools/arr-dashboard/`.

### Task 3: `Download.size`, `Row.arr_id`, `ActionJob`

**Files:** Modify `arr_dashboard/models.py`; Test `tests/test_models.py`.

- [ ] **Step 1: Write the failing test** (append to `tests/test_models.py`):

```python
from arr_dashboard.models import ActionJob


def test_download_has_size():
    from arr_dashboard.models import Download
    d = Download(infohash="a", name="x", state="downloading", progress=0.5, size=123)
    assert d.size == 123


def test_row_has_arr_id():
    from arr_dashboard.models import Row, ChainHealth
    r = Row(key="tmdb:1", title="M", type="movie", arr_id=42, chain=ChainHealth())
    assert r.arr_id == 42


def test_action_job_defaults():
    j = ActionJob(key="tmdb:1", title="M", app="radarr")
    assert j.state == "queued"
    assert j.message is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'ActionJob'` (and size/arr_id errors)

- [ ] **Step 3: Implement** — in `arr_dashboard/models.py`:

Add `size: int | None = None` to `Download`. Add `arr_id: int | None = None` to `Row`. Add:

```python
class ActionJob(BaseModel):
    key: str
    title: str
    app: Literal["radarr", "sonarr"]
    state: Literal["queued", "running", "done", "failed"] = "queued"
    message: str | None = None
    enqueued_at: str | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/models.py tools/arr-dashboard/tests/test_models.py
git commit -m "feat(arr-dashboard): Download.size, Row.arr_id, ActionJob model"
```

### Task 4: `correlate` populates `arr_id` + `size`

**Files:** Modify `arr_dashboard/correlate.py`; Test `tests/test_correlate.py`.

- [ ] **Step 1: Write the failing test** (append):

```python
def test_correlate_sets_arr_id_and_download_size():
    src = sources(
        radarr_movies=[{"id": 7, "title": "M", "tmdbId": 42, "hasFile": False, "monitored": True}],
        radarr_queue=[{"movieId": 7, "downloadId": "ABC"}],
        qbit_torrents=[{"hash": "abc", "name": "M.mkv", "state": "downloading",
                        "progress": 0.5, "size": 4096}])
    row = [r for r in correlate(src, "t", []).rows if r.key == "tmdb:42"][0]
    assert row.arr_id == 7
    assert row.downloads[0].size == 4096
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_correlate.py::test_correlate_sets_arr_id_and_download_size -v`
Expected: FAIL (arr_id None / size None)

- [ ] **Step 3: Implement** — in `correlate.py`:

In `_movie_row`, add `arr_id=m["id"]` to the `Row(...)`. In `_series_row`, add `arr_id=s["id"]`. In `_to_download`, add `size=t.get("size")` to the `Download(...)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_correlate.py -v`
Expected: PASS (all)

- [ ] **Step 5: Triad + commit**

Run: `uv run ruff format --check . && uv run ruff check . && uv run mypy arr_dashboard`

```bash
git add tools/arr-dashboard/arr_dashboard/correlate.py tools/arr-dashboard/tests/test_correlate.py
git commit -m "feat(arr-dashboard): correlate populates arr_id + download size"
```

---

## Phase 3 — Serialized import queue

### Task 5: `ImportQueue` (state machine + serialization)

**Files:** Create `arr_dashboard/actions.py`; Test `tests/test_actions.py`.

- [ ] **Step 1: Write the failing test**:

```python
import asyncio
import pytest
from arr_dashboard.actions import ImportQueue


@pytest.mark.asyncio
async def test_queue_runs_jobs_serially_and_tracks_state():
    started: list[str] = []
    release = asyncio.Event()

    async def perform(job):
        started.append(job.key)
        await release.wait()  # block first job until we let go

    q = ImportQueue(perform)
    worker = asyncio.create_task(q.run())
    j1 = q.enqueue("tmdb:1", "A", "radarr")
    j2 = q.enqueue("tmdb:2", "B", "radarr")
    await asyncio.sleep(0.05)
    # only the first job is running; second still queued (serialization)
    assert j1.state == "running"
    assert j2.state == "queued"
    assert started == ["tmdb:1"]
    release.set()
    await asyncio.sleep(0.05)
    assert j1.state == "done"
    assert j2.state == "done"
    worker.cancel()


@pytest.mark.asyncio
async def test_failed_job_does_not_block_queue():
    async def perform(job):
        if job.key == "tmdb:1":
            raise RuntimeError("boom")

    q = ImportQueue(perform)
    worker = asyncio.create_task(q.run())
    j1 = q.enqueue("tmdb:1", "A", "radarr")
    j2 = q.enqueue("tmdb:2", "B", "radarr")
    await asyncio.sleep(0.05)
    assert j1.state == "failed"
    assert "boom" in (j1.message or "")
    assert j2.state == "done"
    worker.cancel()
```

> Add `pytest-asyncio` to the dev deps + `asyncio_mode = "auto"` (or mark) — check `pyproject.toml`; if absent, add `pytest-asyncio` to `[dependency-groups] dev` and `[tool.pytest.ini_options] asyncio_mode = "auto"`, then `uv sync`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_actions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'arr_dashboard.actions'`

- [ ] **Step 3: Implement** `arr_dashboard/actions.py`:

```python
import asyncio
from collections.abc import Awaitable, Callable
from arr_dashboard.models import ActionJob


class ImportQueue:
    """FIFO queue with a single worker → imports run strictly one at a time."""

    def __init__(self, perform: Callable[[ActionJob], Awaitable[None]]) -> None:
        self._perform = perform
        self._queue: asyncio.Queue[ActionJob] = asyncio.Queue()
        self._jobs: list[ActionJob] = []

    def enqueue(self, key: str, title: str, app: str) -> ActionJob:
        job = ActionJob(key=key, title=title, app=app)  # type: ignore[arg-type]
        self._jobs.append(job)
        self._queue.put_nowait(job)
        return job

    def jobs(self) -> list[ActionJob]:
        return list(self._jobs)

    async def run(self) -> None:
        while True:
            job = await self._queue.get()
            job.state = "running"
            try:
                await self._perform(job)
                job.state = "done"
            except Exception as exc:  # one failure must not kill the worker
                job.state = "failed"
                job.message = str(exc)
            finally:
                self._queue.task_done()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_actions.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/actions.py tools/arr-dashboard/tests/test_actions.py tools/arr-dashboard/pyproject.toml tools/arr-dashboard/uv.lock
git commit -m "feat(arr-dashboard): serialized ImportQueue with job state machine"
```

---

## Phase 4 — Import runner (arr ManualImport)

### Task 6: `perform_import`

**Files:** Create `arr_dashboard/import_runner.py`; Test `tests/test_import_runner.py`.

- [ ] **Step 1: Write the failing test**:

```python
import httpx
import respx
from arr_dashboard.import_runner import perform_import
from arr_dashboard.models import Download, Row, ChainHealth
from arrconf.client_base import RadarrClient


def _row():
    return Row(key="tmdb:42", title="M", type="movie", arr_app="radarr", arr_id=7,
               has_file=False, chain=ChainHealth(),
               downloads=[Download(infohash="abc", name="M.mkv", state="stalledUP",
                                   progress=1.0, save_path="/data/x", size=4096)])


@respx.mock
def test_perform_import_copies_matching_file():
    respx.get("http://r:7878/api/v3/manualimport").mock(return_value=httpx.Response(200, json=[
        {"path": "/data/x/M.mkv", "movie": {"id": 7}, "quality": {"q": 1}, "languages": [], "rejections": []},
        {"path": "/data/x/other.mkv", "movie": {"id": 999}, "quality": {}, "languages": [], "rejections": []}]))
    cmd = respx.post("http://r:7878/api/v3/command").mock(
        return_value=httpx.Response(201, json={"id": 5, "status": "started"}))
    respx.get("http://r:7878/api/v3/command/5").mock(
        return_value=httpx.Response(200, json={"id": 5, "status": "completed"}))

    perform_import(_row(), RadarrClient("http://r:7878", "key"))

    import json
    body = json.loads(cmd.calls.last.request.content)
    assert body["importMode"] == "Copy"
    assert [f["movieId"] for f in body["files"]] == [7]  # only the matching file


@respx.mock
def test_perform_import_raises_when_no_match():
    respx.get("http://r:7878/api/v3/manualimport").mock(return_value=httpx.Response(200, json=[
        {"path": "/data/x/other.mkv", "movie": {"id": 999}, "rejections": []}]))
    import pytest
    with pytest.raises(Exception):
        perform_import(_row(), RadarrClient("http://r:7878", "key"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_import_runner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'arr_dashboard.import_runner'`

- [ ] **Step 3: Implement** `arr_dashboard/import_runner.py`:

```python
import time
from typing import Any
from arr_dashboard.models import Row


class ImportError_(Exception):
    pass


def perform_import(row: Row, client: Any) -> None:
    """Force-import the row's downloaded file into the arr library (Copy).

    Raises on no matching candidate or on command failure/timeout.
    """
    if not row.downloads or not row.downloads[0].save_path or row.arr_id is None:
        raise ImportError_(f"{row.key}: no importable download")
    folder = row.downloads[0].save_path
    candidates = client.manual_import_candidates(folder)

    files: list[dict[str, Any]] = []
    for c in candidates:
        if c.get("rejections"):
            continue
        if row.type == "movie":
            if (c.get("movie") or {}).get("id") == row.arr_id:
                files.append({"path": c["path"], "movieId": row.arr_id,
                              "quality": c.get("quality"), "languages": c.get("languages", []),
                              "releaseGroup": c.get("releaseGroup", "")})
        else:
            if (c.get("series") or {}).get("id") == row.arr_id and c.get("episodes"):
                files.append({"path": c["path"], "seriesId": row.arr_id,
                              "episodeIds": [e["id"] for e in c["episodes"]],
                              "quality": c.get("quality"), "languages": c.get("languages", []),
                              "releaseGroup": c.get("releaseGroup", "")})
    if not files:
        raise ImportError_(f"{row.key}: no matching importable file in {folder}")

    cmd = client.manual_import(files, mode="Copy")
    cmd_id = cmd.get("id")
    for _ in range(120):  # ~10 min budget (slow NAS); poll every 5s
        status = client.get(f"/command/{cmd_id}").get("status")
        if status == "completed":
            return
        if status == "failed":
            raise ImportError_(f"{row.key}: arr ManualImport failed")
        time.sleep(5)
    raise ImportError_(f"{row.key}: import timed out")
```

> In tests the poll returns `completed` on the first call so `time.sleep` isn't hit. If the test process is slow, that's fine. Confirm `client.get("/command/5")` returns parsed JSON (it does, per Phase-1 verification).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_import_runner.py -v`
Expected: PASS

- [ ] **Step 5: Triad + commit**

Run: `uv run ruff format --check . && uv run ruff check . && uv run mypy arr_dashboard`

```bash
git add tools/arr-dashboard/arr_dashboard/import_runner.py tools/arr-dashboard/tests/test_import_runner.py
git commit -m "feat(arr-dashboard): perform_import — ManualImport Copy matched by arr_id + poll"
```

---

## Phase 5 — Action endpoints + wiring

### Task 7: `POST /api/actions/import` + `GET /api/actions` + lifespan worker

**Files:** Modify `arr_dashboard/app.py`; Test `tests/test_app.py`.

- [ ] **Step 1: Write the failing test** (append to `tests/test_app.py`):

```python
def test_import_action_requires_confirm_and_enqueues():
    from arr_dashboard.cache import SnapshotCache
    from arr_dashboard.models import Snapshot, Row, ChainHealth, Download
    cache = SnapshotCache()
    cache.set(Snapshot(rows=[Row(key="tmdb:42", title="M", type="movie", arr_app="radarr",
                                 arr_id=7, has_file=False, chain=ChainHealth(),
                                 downloads=[Download(infohash="a", name="M.mkv", state="stalledUP",
                                                     progress=1.0, save_path="/data/x", size=4096)],
                                 flags=["non-importe"])], generated_at="t"))
    app = create_app(cache=cache, start_refresher=False)
    client = TestClient(app)

    # missing confirm → 400
    assert client.post("/api/actions/import", json={"key": "tmdb:42"}).status_code == 400
    # unknown key → 404
    assert client.post("/api/actions/import", json={"key": "tmdb:999", "confirm": True}).status_code == 404
    # valid → queued
    r = client.post("/api/actions/import", json={"key": "tmdb:42", "confirm": True})
    assert r.status_code == 200
    assert r.json()["state"] == "queued"
    # listed
    actions = client.get("/api/actions").json()
    assert any(a["key"] == "tmdb:42" for a in actions)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_app.py -v`
Expected: FAIL (404/400 routes not defined → 404 for the route itself / KeyError)

- [ ] **Step 3: Implement** — in `app.py`:

Add imports + build clients + queue. In `create_app`, before defining routes:

```python
    from arr_dashboard.actions import ImportQueue
    from arr_dashboard.import_runner import perform_import
    from arr_dashboard.sources import build_clients  # see note below
    from fastapi import Body, HTTPException
    import asyncio

    _settings = settings  # may be None in tests; resolve lazily for the worker

    async def _perform(job):
        snap = cache.get()
        row = next((r for r in snap.rows if r.key == job.key), None)
        if row is None:
            raise RuntimeError(f"{job.key}: row gone")
        clients = build_clients(_settings or load_settings())
        client = clients.get(row.arr_app)
        if client is None:
            raise RuntimeError(f"{job.key}: no client for {row.arr_app}")
        await asyncio.to_thread(perform_import, row, client)

    queue = ImportQueue(_perform)
```

Extend the lifespan to also start the queue worker:

```python
        tasks = []
        if start_refresher:
            tasks.append(asyncio.create_task(refresher_loop(settings or load_settings(), cache)))
        tasks.append(asyncio.create_task(queue.run()))
        yield
        for t in tasks:
            t.cancel()
```

Add routes:

```python
    @app.post("/api/actions/import")
    def enqueue_import(payload: dict = Body(...)) -> dict:
        if payload.get("confirm") is not True:
            raise HTTPException(status_code=400, detail="confirm:true required")
        key = payload.get("key")
        row = next((r for r in cache.get().rows if r.key == key), None)
        if row is None:
            raise HTTPException(status_code=404, detail="row not found")
        if not row.downloads or row.arr_id is None or row.arr_app is None:
            raise HTTPException(status_code=400, detail="row has no importable download")
        job = queue.enqueue(row.key, row.title, row.arr_app)
        return job.model_dump(mode="json")

    @app.get("/api/actions")
    def list_actions() -> list:
        return [j.model_dump(mode="json") for j in queue.jobs()]
```

Add a `build_clients(settings) -> dict[str, Any]` helper in `sources.py` (refactor: `fetch_all` already constructs clients — extract the construction):

```python
def build_clients(settings: Settings) -> dict[str, object]:
    clients: dict[str, object] = {}
    if settings.radarr_api_key:
        clients["radarr"] = RadarrClient(settings.radarr_url, settings.radarr_api_key)
    if settings.sonarr_api_key:
        clients["sonarr"] = SonarrClient(settings.sonarr_url, settings.sonarr_api_key)
    return clients
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_app.py -v`
Expected: PASS

- [ ] **Step 5: Full triad + suite + commit**

Run: `uv run ruff format --check . && uv run ruff check . && uv run mypy arr_dashboard && uv run pytest --cov=arr_dashboard --cov-report=term-missing`
Expected: all pass; queue/runner modules well covered.

```bash
git add tools/arr-dashboard/arr_dashboard/app.py tools/arr-dashboard/arr_dashboard/sources.py tools/arr-dashboard/tests/test_app.py
git commit -m "feat(arr-dashboard): import action endpoints + serialized worker wiring"
```

---

## Phase 6 — Frontend (import button + confirm + actions panel)

Mirror V1 Svelte conventions. Run from `tools/arr-dashboard/web/`.

### Task 8: api.ts — types + calls

**Files:** Modify `web/src/api.ts`.

- [ ] **Step 1:** Add `size: number | null` to the `Download` interface. Add:

```typescript
export interface ActionJob { key: string; title: string; app: string; state: "queued" | "running" | "done" | "failed"; message: string | null; }

export async function postImport(key: string): Promise<ActionJob> {
  const res = await fetch("/api/actions/import", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key, confirm: true }),
  });
  if (!res.ok) throw new Error(`import ${res.status}`);
  return res.json();
}

export async function getActions(): Promise<ActionJob[]> {
  const res = await fetch("/api/actions");
  if (!res.ok) throw new Error(`actions ${res.status}`);
  return res.json();
}
```

- [ ] **Step 2: Build + commit**

Run: `npm run build` (expect clean)

```bash
git add tools/arr-dashboard/web/src/api.ts
git commit -m "feat(arr-dashboard): web api — postImport, getActions, Download.size"
```

### Task 9: ConfirmDialog + ImportButton + ActionsPanel

**Files:** Create `web/src/lib/{ConfirmDialog,ImportButton,ActionsPanel}.svelte`.

- [ ] **Step 1: `ConfirmDialog.svelte`**:

```svelte
<script lang="ts">
  let { title, detail, onConfirm, onCancel }: { title: string; detail: string; onConfirm: () => void; onCancel: () => void } = $props();
</script>

<div class="overlay" onclick={onCancel}>
  <div class="box" onclick={(e) => e.stopPropagation()}>
    <h3>{title}</h3>
    <p class="detail">{detail}</p>
    <p class="warn">⚠ copie NFS — peut ralentir Jellyfin</p>
    <div class="btns"><button onclick={onCancel}>Annuler</button><button class="go" onclick={onConfirm}>Confirmer</button></div>
  </div>
</div>

<style>
  .overlay { position: fixed; inset: 0; background: #000a; display: grid; place-items: center; }
  .box { background: #161a22; padding: 1.2rem; border-radius: 8px; max-width: 480px; }
  .warn { color: #fbbf24; } .detail { color: #9ca3af; font-family: "IBM Plex Mono", monospace; font-size: .8rem; }
  .btns { display: flex; gap: .6rem; justify-content: flex-end; margin-top: 1rem; }
  .go { background: #4ade80; color: #06281a; border: 0; padding: .4rem .9rem; border-radius: 4px; }
</style>
```

- [ ] **Step 2: `ImportButton.svelte`** (shows for importable rows; opens dialog):

```svelte
<script lang="ts">
  import type { Row } from "../api";
  import ConfirmDialog from "./ConfirmDialog.svelte";
  import { postImport } from "../api";
  let { row, pending }: { row: Row; pending: boolean } = $props();
  let open = $state(false);
  const sizeGB = $derived(row.downloads[0]?.size ? (row.downloads[0].size / 1e9).toFixed(2) : "?");
  async function confirm() { open = false; await postImport(row.key); }
</script>

{#if pending}
  <span class="badge">import…</span>
{:else}
  <button onclick={() => (open = true)}>Importer</button>
{/if}
{#if open}
  <ConfirmDialog title={`Importer ${row.title}`} detail={`${row.downloads[0]?.name ?? ""} — ${sizeGB} GB`}
    onConfirm={confirm} onCancel={() => (open = false)} />
{/if}

<style>.badge { color: #60a5fa; } button { background: #2563eb; color: #fff; border: 0; padding: .25rem .6rem; border-radius: 4px; cursor: pointer; }</style>
```

- [ ] **Step 3: `ActionsPanel.svelte`** (polls getActions):

```svelte
<script lang="ts">
  import { getActions, type ActionJob } from "../api";
  let jobs: ActionJob[] = $state([]);
  $effect(() => { const f = async () => { try { jobs = await getActions(); } catch {} }; f(); const id = setInterval(f, 3000); return () => clearInterval(id); });
  const active = $derived(jobs.filter((j) => j.state === "queued" || j.state === "running"));
  const failed = $derived(jobs.filter((j) => j.state === "failed"));
</script>

{#if active.length || failed.length}
  <div class="panel">
    {#if active.length}<span>⏳ {active.length} import(s) en cours/file</span>{/if}
    {#each failed as j}<span class="f" title={j.message ?? ""}>✗ {j.title}</span>{/each}
  </div>
{/if}

<style>.panel { display: flex; gap: 1rem; padding: .4rem 1rem; background: #161a22; font-size: .85rem; } .f { color: #f87171; }</style>
```

> `pending` for a row = an active job exists with that key. App.svelte computes it from the ActionsPanel's jobs or its own getActions poll; keep it simple — App.svelte does one `getActions` poll and passes a `Set<string>` of active keys down to each ImportButton. Retry = the failed badge's title carries the message; a click re-calls postImport (add an onclick to the `.f` span calling postImport(key)).

- [ ] **Step 4: Build + commit**

Run: `npm run build` (expect clean; `npm run check` 0 errors)

```bash
git add tools/arr-dashboard/web/src/lib/
git commit -m "feat(arr-dashboard): ConfirmDialog + ImportButton + ActionsPanel"
```

### Task 10: Wire into App.svelte

**Files:** Modify `web/src/App.svelte`.

- [ ] **Step 1:** Add an `getActions` poll producing `activeKeys: Set<string>` (keys with state queued/running). Add an **Actions** column to the table; for rows whose `flags` include `non-importe` or `deja-possede-regrab`, render `<ImportButton {row} pending={activeKeys.has(row.key)} />`; otherwise empty. Mount `<ActionsPanel />` under the header. Import the three components.

```svelte
  import ImportButton from "./lib/ImportButton.svelte";
  import ActionsPanel from "./lib/ActionsPanel.svelte";
  import { getActions } from "./api";
  let activeKeys = $state(new Set<string>());
  $effect(() => { const f = async () => { try { const j = await getActions(); activeKeys = new Set(j.filter(x => x.state==='queued'||x.state==='running').map(x => x.key)); } catch {} }; f(); const id = setInterval(f, 3000); return () => clearInterval(id); });
  const importable = (r) => r.flags.includes("non-importe") || r.flags.includes("deja-possede-regrab");
```

Add `<th>Action</th>` to the header row and a cell:
```svelte
        <td>{#if importable(row)}<ImportButton {row} pending={activeKeys.has(row.key)} />{/if}</td>
```

- [ ] **Step 2: Build + check + commit**

Run: `npm run build && npm run check`
Expected: clean, 0 errors.

```bash
git add tools/arr-dashboard/web/src/App.svelte
git commit -m "feat(arr-dashboard): wire import action into dashboard table"
```

---

## Phase 7 — Deploy (ingress + release)

### Task 11: oauth2 ingress on arr-dashboard

**Files:** Modify `charts/arr-stack/values.yaml`.

- [ ] **Step 1:** In the `arr-dashboard:` block, add an `ingress` section mirroring the `sonarr:` block (lines ~31-48), host `arr-dashboard.tgu.ovh`, tls secret `arr-dashboard-tls`:

```yaml
  ingress:
    main:
      className: nginx
      annotations:
        cert-manager.io/cluster-issuer: "letsencrypt-prod"
        traefik.ingress.kubernetes.io/router.middlewares: "selfhost-oauth2-forwardauth@kubernetescrd"
      hosts:
        - host: arr-dashboard.tgu.ovh
          paths:
            - path: /
              pathType: Prefix
              service:
                identifier: main
                port: http
      tls:
        - secretName: arr-dashboard-tls
          hosts:
            - arr-dashboard.tgu.ovh
```

- [ ] **Step 2: Verify chart renders** (alias-unpack workaround as in V1, then):

Run: `helm template charts/arr-stack/ -f examples/values-prod.yaml | kubeconform -strict -ignore-missing-schemas`
Expected: renders an `arr-dashboard` Ingress + Service + Deployment; kubeconform passes.
Also confirm the renovate-annotation guard + customManagers `>=14` guard still pass (helm lint).

- [ ] **Step 3: Commit**

```bash
git add charts/arr-stack/values.yaml
git commit -m "feat(chart): expose arr-dashboard via oauth2-proxy ingress (arr-dashboard.tgu.ovh)"
```

### Task 12: Co-bump image tags (at release)

**Files:** Modify `charts/arr-stack/values.yaml`.

- [ ] **Step 1: Determine release version.** Last tag is `v0.32.0`; commits are `feat:` → auto-tag minor → **v0.33.0**. Set BOTH `arrconf.image.tag` and `arr-dashboard.image.tag` to `0.33.0` (arrconf code changed in Phase 1 → rebuild; arr-dashboard code changed → rebuild).

- [ ] **Step 2: Commit**

```bash
git add charts/arr-stack/values.yaml
git commit -m "feat(release): pin arrconf + arr-dashboard images to 0.33.0 (arr-dashboard V2 import action)"
```

---

## Phase 8 — Finalize

### Task 13: Full verification + finishing

- [ ] **Step 1: arrconf triad + tests** — `cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy arrconf && uv run pytest -q` (the 4 known pre-existing failures are acceptable; no NEW failures).
- [ ] **Step 2: arr-dashboard triad + coverage** — `cd tools/arr-dashboard && uv run ruff format --check . && uv run ruff check . && uv run mypy arr_dashboard && uv run pytest --cov=arr_dashboard` (≥70% overall; actions+import_runner well covered).
- [ ] **Step 3: Frontend** — `cd tools/arr-dashboard/web && npm run build && npm run check` (clean).
- [ ] **Step 4: Chart render** — as Task 11 Step 2.
- [ ] **Step 5:** Use **superpowers:finishing-a-development-branch**: verify tests, present merge/PR options. On merge-to-prod, follow the V1 release flow exactly (push main → chart-lint auto-tags v0.33.0 + dispatches all 3 image builds → verify `arrconf:0.33.0` + `arr-dashboard:0.33.0` on GHCR via anon manifest → bump my-kluster `targetRevision` → v0.33.0). Confirm `arr-dashboard.tgu.ovh` DNS resolves.

---

## Notes for the implementer

- **No secrets** in code/tests (fake keys; oauth2 handled by the ingress, not the app).
- **Copy only** — `manual_import` defaults to `mode="Copy"`; never pass `Move` (would delete the seed).
- **Verify arrconf client signatures** (`.get` returns JSON, `.post(path, json)`) before Phase 1.
- **Mirror, don't invent** the ingress block (copy sonarr's) and the V1 Svelte/CI patterns.
- **Serialization is the safety contract** — one import at a time; never parallelize the worker.
- **V2.1** (doublon/bloque/jellyfin-scan + grab cancel) is out of scope; show those flags without buttons.
```
