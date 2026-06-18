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


@pytest.mark.asyncio
async def test_enqueue_carries_size_and_run_sets_started_at():
    async def perform(job):
        pass

    q = ImportQueue(perform)
    worker = asyncio.create_task(q.run())
    j = q.enqueue("tmdb:1", "A", "radarr", size_bytes=4096)
    assert j.size_bytes == 4096
    await asyncio.sleep(0.05)
    assert j.started_at is not None  # ISO timestamp set when the worker picked it up
    assert j.state == "done"
    worker.cancel()
