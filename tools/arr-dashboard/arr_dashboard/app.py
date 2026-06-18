import asyncio
import contextlib
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from arr_dashboard.actions import ImportQueue
from arr_dashboard.cache import SnapshotCache, refresher_loop
from arr_dashboard.import_runner import perform_import
from arr_dashboard.models import ActionJob
from arr_dashboard.settings import Settings, load_settings
from arr_dashboard.sources import build_clients

_DIST = Path(__file__).parent.parent / "web" / "dist"


def create_app(
    *,
    cache: SnapshotCache | None = None,
    settings: Settings | None = None,
    start_refresher: bool = True,
) -> FastAPI:
    cache = cache or SnapshotCache()

    async def _perform(job: ActionJob) -> None:
        snap = cache.get()
        row = next((r for r in snap.rows if r.key == job.key), None)
        if row is None:
            raise RuntimeError(f"{job.key}: row gone")
        clients = build_clients(settings or load_settings())
        client = clients.get(row.arr_app) if row.arr_app else None
        if client is None:
            raise RuntimeError(f"{job.key}: no client for {row.arr_app}")
        await asyncio.to_thread(perform_import, row, client)

    queue = ImportQueue(_perform)

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        tasks: list[asyncio.Task[None]] = []
        if start_refresher:
            tasks.append(asyncio.create_task(refresher_loop(settings or load_settings(), cache)))
        tasks.append(asyncio.create_task(queue.run()))
        yield
        for t in tasks:
            t.cancel()

    app = FastAPI(title="arr-dashboard", lifespan=lifespan)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/dashboard")
    def dashboard() -> dict[str, Any]:
        return cache.get().model_dump(mode="json")

    @app.get("/api/dashboard/{key}")
    def dashboard_detail(key: str) -> dict[str, Any]:
        for row in cache.get().rows:
            if row.key == key:
                return row.model_dump(mode="json")
        return {"error": "not found", "key": key}

    @app.post("/api/actions/import")
    def enqueue_import(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
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
    def list_actions() -> list[dict[str, Any]]:
        return [j.model_dump(mode="json") for j in queue.jobs()]

    if _DIST.is_dir():
        app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="web")

    return app
