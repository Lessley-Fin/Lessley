"""Concurrency, isolation and graceful shutdown of the scheduler loops."""

from __future__ import annotations

import asyncio
from typing import Any

from lessley_deals.scheduling.runner import JobResult, SourceRunner
from lessley_deals.scheduling.schedule import RetryPolicy, ScheduleSpec
from lessley_deals.scheduling.scheduler import SchedulerService
from tests.unit.scheduling.test_runner import FakeJournal, FakeLock

NO_RETRY = RetryPolicy(max_attempts=1, base_delay_seconds=0.001, jitter=0)


def spec(source_id: str, **overrides: Any) -> ScheduleSpec:
    defaults: dict[str, Any] = {
        "source_id": source_id,
        "interval_seconds": 3600,   # far away: only run_on_start fires in tests
        "run_on_start": True,
        "timeout_seconds": 5,
        "retry": NO_RETRY,
    }
    defaults.update(overrides)
    return ScheduleSpec(**defaults)


def runner_for(job: Any) -> SourceRunner:
    return SourceRunner(job, FakeJournal(), FakeLock())


async def run_briefly(scheduler: SchedulerService, seconds: float = 0.2) -> None:
    task = asyncio.create_task(scheduler.start())
    await asyncio.sleep(seconds)
    scheduler.request_shutdown()
    await asyncio.wait_for(task, timeout=5)


async def test_sources_run_concurrently_not_sequentially() -> None:
    concurrent = 0
    peak = 0

    async def job(source_id: str, run_id: str) -> JobResult:
        nonlocal concurrent, peak
        concurrent += 1
        peak = max(peak, concurrent)
        await asyncio.sleep(0.05)
        concurrent -= 1
        return JobResult(ok=True)

    scheduler = SchedulerService(
        specs=[spec(f"src{i}") for i in range(4)],
        runner=runner_for(job),
        max_concurrency=4,
    )
    await run_briefly(scheduler)

    assert peak == 4, f"expected 4 sources in flight, peaked at {peak}"


async def test_max_concurrency_is_enforced() -> None:
    concurrent = 0
    peak = 0

    async def job(source_id: str, run_id: str) -> JobResult:
        nonlocal concurrent, peak
        concurrent += 1
        peak = max(peak, concurrent)
        await asyncio.sleep(0.05)
        concurrent -= 1
        return JobResult(ok=True)

    scheduler = SchedulerService(
        specs=[spec(f"src{i}") for i in range(6)],
        runner=runner_for(job),
        max_concurrency=2,
    )
    await run_briefly(scheduler, seconds=0.3)

    assert peak <= 2


async def test_one_failing_source_does_not_stop_the_others() -> None:
    completed: list[str] = []

    async def job(source_id: str, run_id: str) -> JobResult:
        if source_id == "broken":
            raise RuntimeError("this source is down")
        completed.append(source_id)
        return JobResult(ok=True)

    scheduler = SchedulerService(
        specs=[spec("broken"), spec("healthy1"), spec("healthy2")],
        runner=runner_for(job),
        max_concurrency=3,
    )
    await run_briefly(scheduler)

    assert sorted(completed) == ["healthy1", "healthy2"]


async def test_disabled_sources_never_run() -> None:
    ran: list[str] = []

    async def job(source_id: str, run_id: str) -> JobResult:
        ran.append(source_id)
        return JobResult(ok=True)

    scheduler = SchedulerService(
        specs=[spec("on"), spec("off", enabled=False)],
        runner=runner_for(job),
    )
    await run_briefly(scheduler)

    assert ran == ["on"]


async def test_shutdown_waits_for_in_flight_runs() -> None:
    finished = False

    async def job(source_id: str, run_id: str) -> JobResult:
        nonlocal finished
        await asyncio.sleep(0.15)
        finished = True
        return JobResult(ok=True)

    scheduler = SchedulerService(
        specs=[spec("slow")], runner=runner_for(job), shutdown_grace_seconds=5
    )
    task = asyncio.create_task(scheduler.start())
    await asyncio.sleep(0.02)          # let the run start
    scheduler.request_shutdown()       # ...then ask to stop mid-run
    await asyncio.wait_for(task, timeout=5)

    assert finished, "shutdown cut an in-flight run short"


async def test_shutdown_cancels_runs_that_overrun_the_grace_period() -> None:
    async def job(source_id: str, run_id: str) -> JobResult:
        await asyncio.sleep(30)
        return JobResult(ok=True)

    scheduler = SchedulerService(
        specs=[spec("stuck", timeout_seconds=60)],
        runner=runner_for(job),
        shutdown_grace_seconds=0.05,
    )
    task = asyncio.create_task(scheduler.start())
    await asyncio.sleep(0.02)
    scheduler.request_shutdown()

    await asyncio.wait_for(task, timeout=5)  # must not hang


async def test_next_fire_times_lists_every_enabled_source() -> None:
    scheduler = SchedulerService(
        specs=[spec("a", run_on_start=False), spec("b", run_on_start=False),
               spec("c", enabled=False)],
        runner=runner_for(lambda *_: JobResult(ok=True)),
    )
    assert sorted(scheduler.next_fire_times()) == ["a", "b"]
