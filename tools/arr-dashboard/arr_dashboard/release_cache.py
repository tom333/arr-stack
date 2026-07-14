"""1-hour TTL cache for the release list, with manual invalidation (force refresh).

Uses a monotonic clock injected as a callable so tests stay deterministic without
patching time. Default clock is time.monotonic."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any


class ReleaseCache:
    def __init__(
        self, ttl_seconds: int = 3600, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._value: Any = None
        self._stamp: float = -1e18
        self._lock = threading.Lock()

    def get(self, build: Callable[[], Any]) -> Any:
        with self._lock:
            now = self._clock()
            if self._value is None or (now - self._stamp) >= self._ttl:
                self._value = build()
                self._stamp = now
            return self._value

    def invalidate(self) -> None:
        with self._lock:
            self._value = None
            self._stamp = -1e18
