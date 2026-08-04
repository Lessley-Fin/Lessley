"""Retry, timeout, locking and journaling behaviour of the SourceRunner."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from lessley_deals.domain.enums import RunStatus
from lessley_deals.scheduling.journal import RunRecord
from lessley_deals.scheduling.runner import JobResult, SourceRunner
from lessley_deals.scheduling.schedule import RetryPolicy, ScheduleSpec

FAST_RETRY = RetryPolicy(max_attempts=3, base_delay_seconds=0.001, jitter=0)


class FakeJournal:
    """Snapshots each record on write — the runner reuses one mutable RunRecord
    per attempt, exactly as a real (serializing) journal would see it."""

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def record(self, run: RunRecord) -> None:
        self.records.append(run.to_dict())

    def recent(self, source_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        return []

    def last_success(self, source_id: str) -> dict[str, Any] | None:
        return None

    @property
    def final_statuses(self) -> list[str]:
        return [r["status"] for r in self.records if r["status"] != str(RunStatus.RUNNING)]


class FakeLock:
    def __init__(self, available: bool = True) -> None:
        self.available = available
        self.acquired = 0
        self.released = 0
        self.renewed = 0

    def acquire(self, key: str, ttl_seconds: float) -> str | None:
        if not self.available:
            return None
        self.acquired += 1
        return "token"

    def renew(self, key: str, token: str, ttl_seconds: float) -> bool:
        self.renewed += 1
        return True

    def release(self, key: str, token: str) -> None:
        self.released += 1


def spec(**overrides: Any) -> ScheduleSpec:
    defaults: dict[str, Any] = {
        "source_id": "hot",
        "interval_seconds": 60,
        "timeout_seconds": 5,
        "retry": FAST_RETRY,
    }
    defaults.update(overrides)
    return ScheduleSpec(**defaults)


async def test_successful_run_is_journaled_with_counters() -> None:
    async def job(source_id: str, run_id: str) -> JobResult:
        return JobResult(ok=True, scraped_records=42, deals_new=3, deals_expired=1)

    journal, lock = FakeJournal(), FakeLock()
    record = await SourceRunner(job, journal, lock).run(spec())

    assert record.status is RunStatus.SUCCESS
    assert record.deals_new == 3 and record.deals_expired == 1
    assert lock.acquired == 1 and lock.released == 1


async def test_transient_failure_is_retried_then_succeeds() -> None:
    attempts = 0

    async def job(source_id: str, run_id: str) -> JobResult:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("boom")
        return JobResult(ok=True)

    journal = FakeJournal()
    record = await SourceRunner(job, journal, FakeLock()).run(spec())

    assert attempts == 3
    assert record.status is RunStatus.SUCCESS
    assert record.attempt == 3
    assert journal.final_statuses == [
        str(RunStatus.FAILED),
        str(RunStatus.FAILED),
        str(RunStatus.SUCCESS),
    ]


async def test_permanent_failure_stops_at_max_attempts() -> None:
    attempts = 0

    async def job(source_id: str, run_id: str) -> JobResult:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("still broken")

    record = await SourceRunner(job, FakeJournal(), FakeLock()).run(spec())

    assert attempts == 3
    assert record.status is RunStatus.FAILED
    assert "still broken" in (record.error or "")


async def test_hanging_source_is_timed_out() -> None:
    async def job(source_id: str, run_id: str) -> JobResult:
        await asyncio.sleep(10)
        return JobResult(ok=True)

    record = await SourceRunner(
        job, FakeJournal(), FakeLock()
    ).run(spec(timeout_seconds=0.02, retry=RetryPolicy(max_attempts=1)))

    assert record.status is RunStatus.FAILED
    assert "timed out" in (record.error or "")


async def test_partial_result_is_not_retried() -> None:
    """`ok=False` means the scraper ran and reported problems — retrying the
    whole source would just hammer a site that already answered."""
    calls = 0

    async def job(source_id: str, run_id: str) -> JobResult:
        nonlocal calls
        calls += 1
        return JobResult(ok=False, errors=["3 pages failed"])

    record = await SourceRunner(job, FakeJournal(), FakeLock()).run(spec())

    assert calls == 1
    assert record.status is RunStatus.PARTIAL
    assert record.error == "3 pages failed"


async def test_run_is_skipped_when_another_worker_holds_the_lock() -> None:
    called = False

    async def job(source_id: str, run_id: str) -> JobResult:
        nonlocal called
        called = True
        return JobResult(ok=True)

    lock = FakeLock(available=False)
    record = await SourceRunner(job, FakeJournal(), lock).run(spec())

    assert not called
    assert record.status is RunStatus.SKIPPED
    assert lock.released == 0


async def test_lock_is_released_even_when_the_job_explodes() -> None:
    async def job(source_id: str, run_id: str) -> JobResult:
        raise RuntimeError("kaboom")

    lock = FakeLock()
    await SourceRunner(job, FakeJournal(), lock).run(spec(retry=RetryPolicy(max_attempts=1)))

    assert lock.released == 1


async def test_lease_is_renewed_while_backing_off() -> None:
    async def job(source_id: str, run_id: str) -> JobResult:
        raise ConnectionError("boom")

    lock = FakeLock()
    await SourceRunner(job, FakeJournal(), lock).run(spec())

    assert lock.renewed == 2  # once before each of the two retries


async def test_cancellation_propagates_and_is_journaled() -> None:
    async def job(source_id: str, run_id: str) -> JobResult:
        await asyncio.sleep(10)
        return JobResult(ok=True)

    journal, lock = FakeJournal(), FakeLock()
    runner = SourceRunner(job, journal, lock)
    task = asyncio.create_task(runner.run(spec(timeout_seconds=30)))
    await asyncio.sleep(0.05)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert journal.records[-1]["error"] == "cancelled (shutdown)"
    assert lock.released == 1
