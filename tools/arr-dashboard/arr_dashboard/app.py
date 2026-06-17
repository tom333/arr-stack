import asyncio
import contextlib
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from arr_dashboard.cache import SnapshotCache, refresher_loop
from arr_dashboard.settings import Settings, load_settings

_DIST = Path(__file__).parent.parent / "web" / "dist"


def create_app(
    *,
    cache: SnapshotCache | None = None,
    settings: Settings | None = None,
    start_refresher: bool = True,
) -> FastAPI:
    cache = cache or SnapshotCache()

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        task: asyncio.Task[None] | None = None
        if start_refresher:
            task = asyncio.create_task(refresher_loop(settings or load_settings(), cache))
        yield
        if task:
            task.cancel()

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

    if _DIST.is_dir():
        app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="web")

    return app
