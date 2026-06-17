import asyncio
import logging
from datetime import UTC, datetime

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
    now = datetime.now(UTC).isoformat()
    return correlate(src, now, stale)


async def refresher_loop(settings: Settings, cache: SnapshotCache) -> None:
    while True:
        try:
            cache.set(await asyncio.to_thread(build_snapshot, settings))
        except Exception as exc:  # never let the loop die
            log.error("refresh failed: %s", exc)
        await asyncio.sleep(settings.refresh_seconds)
