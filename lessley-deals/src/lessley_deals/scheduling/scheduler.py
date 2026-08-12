"""SchedulerService — one independent asyncio loop per source.

    ┌─ loop(hot)         sleep → fire → SourceRunner ─┐
    ┌─ loop(mastercard)  sleep → fire → SourceRunner ─┤→ semaphore(max_concurrency)
    └─ loop(behatsdaa)   sleep → fire → SourceRunner ─┘

Why a loop per source instead of one global tick:

* sources are genuinely independent — a slow Selenium-based source must not
  delay a 2-second JSON fetch;
* a source's next fire time is computed *after* its previous run finishes, so a
  run that overruns its interval can never pile up on itself;
* cancelling one loop (source disabled at runtime) touches nothing else.

Concurrency is bounded by a shared semaphore so ten sources firing at 03:00
don't open ten headless browsers at once.  Shutdown is cooperative: SIGTERM sets
an event, sleeping loops wake immediately, in-flight runs get a grace period,
and only then are they cancelled.
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Sequence

from lessley_deals.scheduling.runner import SourceRunner
from lessley_deals.scheduling.schedule import ScheduleSpec

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(
        self,
        specs: Sequence[ScheduleSpec],
        runner: SourceRunner,
        max_concurrency: int = 3,
        shutdown_grace_seconds: float = 30.0,
        rng: random.Random | None = None,
    ) -> None:
        self._specs = [s for s in specs if s.enabled]
        self._skipped = [s for s in specs if not s.enabled]
        self._runner = runner
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._shutdown = asyncio.Event()
        self._grace = shutdown_grace_seconds
        self._rng = rng or random.Random()
        self._tasks: list[asyncio.Task[None]] = []
        self._in_flight: set[str] = set()

    # ------------------------------------------------------------------ #
    # lifecycle                                                          #
    # ------------------------------------------------------------------ #

    async def start(self) -> None:
        """Run until :meth:`request_shutdown` is called."""
        if not self._specs:
            logger.warning("Scheduler started with no enabled sources — nothing to do")
            return

        logger.info("Scheduler starting with %d source(s):", len(self._specs))
        for spec in self._specs:
            logger.info("  • %s", spec.describe())
        for spec in self._skipped:
            logger.info("  • %s (skipped)", spec.source_id)

        self._tasks = [
            asyncio.create_task(self._source_loop(spec), name=f"scheduler:{spec.source_id}")
            for spec in self._specs
        ]
        await self._shutdown.wait()
        await self._drain()

    def request_shutdown(self) -> None:
        """Signal-handler friendly: never blocks, safe to call twice."""
        if not self._shutdown.is_set():
            logger.info("Shutdown requested — waking all source loops")
            self._shutdown.set()

    async def _drain(self) -> None:
        """Give in-flight runs a grace period, then cancel what is left."""
        if not self._tasks:
            return
        if self._in_flight:
            logger.info(
                "Waiting up to %.0fs for in-flight sources: %s",
                self._grace, ", ".join(sorted(self._in_flight)),
            )
        done, pending = await asyncio.wait(self._tasks, timeout=self._grace)
        for task in pending:
            logger.warning("Cancelling %s — grace period elapsed", task.get_name())
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        logger.info("Scheduler stopped (%d loop(s) finished cleanly)", len(done))

    # ------------------------------------------------------------------ #
    # per-source loop                                                    #
    # ------------------------------------------------------------------ #

    async def _source_loop(self, spec: ScheduleSpec) -> None:
        try:
            if spec.run_on_start:
                await self._fire(spec, trigger="startup")

            while not self._shutdown.is_set():
                now = datetime.now(timezone.utc)
                next_fire = spec.next_fire_at(now, self._rng)
                delay = max(0.0, (next_fire - now).total_seconds())
                logger.info(
                    "Next run for %s at %s (in %.0fs)",
                    spec.source_id, next_fire.isoformat(timespec="seconds"), delay,
                )
                if await self._sleep_or_shutdown(delay):
                    return  # shutdown won the race
                await self._fire(spec, trigger="schedule")
        except asyncio.CancelledError:
            logger.info("Source loop %s cancelled", spec.source_id)
            raise
        except Exception:
            # A crashing loop must not silently take one source offline for the
            # lifetime of the container — log loudly; the supervisor restarts us.
            logger.exception("Source loop %s crashed", spec.source_id)
            raise

    async def _fire(self, spec: ScheduleSpec, trigger: str) -> None:
        """Run one iteration under the global concurrency limit."""
        async with self._semaphore:
            if self._shutdown.is_set() and trigger == "schedule":
                return
            self._in_flight.add(spec.source_id)
            try:
                await self._runner.run(spec, trigger=trigger)
            except asyncio.CancelledError:
                raise
            except Exception:
                # SourceRunner already journals and logs failures; this is the
                # last line of defence so one source can never kill the loop.
                logger.exception("Unhandled error running %s", spec.source_id)
            finally:
                self._in_flight.discard(spec.source_id)

    async def _sleep_or_shutdown(self, seconds: float) -> bool:
        """Sleep, but wake immediately on shutdown. Returns True if shutting down."""
        if seconds <= 0:
            return self._shutdown.is_set()
        try:
            await asyncio.wait_for(self._shutdown.wait(), timeout=seconds)
            return True
        except TimeoutError:
            return False

    # ------------------------------------------------------------------ #
    # introspection                                                      #
    # ------------------------------------------------------------------ #

    @property
    def in_flight(self) -> frozenset[str]:
        return frozenset(self._in_flight)

    def next_fire_times(self, now: datetime | None = None) -> dict[str, datetime]:
        """Preview the schedule — used by ``deals schedule --list`` and health checks."""
        moment = now or datetime.now(timezone.utc)
        return {spec.source_id: spec.next_fire_at(moment) for spec in self._specs}
