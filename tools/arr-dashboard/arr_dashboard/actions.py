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
