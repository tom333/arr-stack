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
