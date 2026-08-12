"""Schedule specifications and a small, dependency-free cron parser.

Supports the standard 5-field crontab syntax::

    ┌───────── minute        (0-59)
    │ ┌─────── hour          (0-23)
    │ │ ┌───── day of month  (1-31)
    │ │ │ ┌─── month         (1-12 or JAN-DEC)
    │ │ │ │ ┌─ day of week   (0-6, Sunday = 0, or SUN-SAT)
    │ │ │ │ │
    0 3 * * *      →  every day at 03:00 UTC

Each field accepts ``*``, ``a``, ``a-b``, ``a,b,c``, ``*/n`` and ``a-b/n``.
Like Vixie cron, when *both* day-of-month and day-of-week are restricted the
match is a union (either one firing is enough).

Deliberately not a dependency: the alternative (``croniter``) is one more thing
to install into the scraper image for ~120 lines of very testable logic.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

_MONTHS = {
    name: i
    for i, name in enumerate(
        ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), start=1
    )
}
_DAYS = {name: i for i, name in enumerate(("sun", "mon", "tue", "wed", "thu", "fri", "sat"))}

_FIELD_RANGES: tuple[tuple[int, int], ...] = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 6))
_STEP_RE = re.compile(r"^(?P<range>[^/]+)(?:/(?P<step>\d+))?$")

# Safety valve: a cron like "0 0 30 2 *" (30 February) never matches.  Rather
# than spin forever we give up after ~5 years of candidate days.
_MAX_DAY_SCAN = 366 * 5


class CronParseError(ValueError):
    """Raised when a cron expression cannot be parsed."""


def _parse_field(text: str, index: int) -> frozenset[int]:
    low, high = _FIELD_RANGES[index]
    values: set[int] = set()

    for part in text.split(","):
        part = part.strip().lower()
        if not part:
            raise CronParseError(f"empty component in field {index}: {text!r}")

        match = _STEP_RE.match(part)
        if match is None:
            raise CronParseError(f"invalid component {part!r} in field {index}")
        body = match.group("range")
        step = int(match.group("step") or 1)
        if step <= 0:
            raise CronParseError(f"step must be positive in {part!r}")

        if body == "*":
            start, end = low, high
        elif "-" in body:
            start_text, _, end_text = body.partition("-")
            start, end = _parse_value(start_text, index), _parse_value(end_text, index)
        else:
            start = end = _parse_value(body, index)
            if step > 1:  # "5/15" is read as "5-max/15", same as Vixie cron
                end = high

        if not (low <= start <= high and low <= end <= high) or start > end:
            raise CronParseError(f"component {part!r} out of range for field {index}")
        values.update(range(start, end + 1, step))

    if not values:
        raise CronParseError(f"field {index} matched no values: {text!r}")
    return frozenset(values)


def _parse_value(text: str, index: int) -> int:
    text = text.strip().lower()
    if index == 3 and text in _MONTHS:
        return _MONTHS[text]
    if index == 4 and text in _DAYS:
        return _DAYS[text]
    if text == "7" and index == 4:  # both 0 and 7 mean Sunday
        return 0
    try:
        return int(text)
    except ValueError as exc:
        raise CronParseError(f"cannot parse {text!r} in field {index}") from exc


@dataclass(frozen=True)
class CronExpression:
    """A parsed 5-field cron expression, evaluated in UTC."""

    minutes: frozenset[int]
    hours: frozenset[int]
    days_of_month: frozenset[int]
    months: frozenset[int]
    days_of_week: frozenset[int]
    dom_restricted: bool
    dow_restricted: bool
    raw: str

    @classmethod
    def parse(cls, expression: str) -> CronExpression:
        fields = expression.split()
        if len(fields) != 5:
            raise CronParseError(f"expected 5 cron fields, got {len(fields)}: {expression!r}")
        parsed = [_parse_field(text, i) for i, text in enumerate(fields)]
        return cls(
            minutes=parsed[0],
            hours=parsed[1],
            days_of_month=parsed[2],
            months=parsed[3],
            days_of_week=parsed[4],
            dom_restricted=fields[2].strip() != "*",
            dow_restricted=fields[4].strip() != "*",
            raw=expression,
        )

    def _day_matches(self, moment: datetime) -> bool:
        # Python: Monday=0..Sunday=6 → cron: Sunday=0..Saturday=6
        weekday = (moment.weekday() + 1) % 7
        dom_hit = moment.day in self.days_of_month
        dow_hit = weekday in self.days_of_week
        if self.dom_restricted and self.dow_restricted:
            return dom_hit or dow_hit
        return dom_hit and dow_hit

    def matches(self, moment: datetime) -> bool:
        return (
            moment.minute in self.minutes
            and moment.hour in self.hours
            and moment.month in self.months
            and self._day_matches(moment)
        )

    def next_after(self, after: datetime) -> datetime:
        """Return the first firing time strictly after ``after`` (UTC)."""
        moment = after.astimezone(timezone.utc).replace(second=0, microsecond=0) + timedelta(minutes=1)

        for _ in range(_MAX_DAY_SCAN):
            if moment.month not in self.months or not self._day_matches(moment):
                # Skip the whole day rather than 1440 useless minute checks.
                moment = (moment + timedelta(days=1)).replace(hour=0, minute=0)
                continue
            for _ in range(24 * 60):
                if moment.hour in self.hours and moment.minute in self.minutes:
                    return moment
                moment += timedelta(minutes=1)
                if moment.hour == 0 and moment.minute == 0:
                    break  # rolled into the next day — re-check the day fields
        raise CronParseError(f"cron expression never fires: {self.raw!r}")


# ---------------------------------------------------------------------------
# Retry policy
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RetryPolicy:
    """Exponential backoff with full-jitter, applied per scheduled run."""

    max_attempts: int = 3
    base_delay_seconds: float = 10.0
    max_delay_seconds: float = 300.0
    multiplier: float = 2.0
    jitter: float = 0.3
    """Fraction of the delay randomized away, to stop every replica and every
    source from retrying in lockstep against a struggling site."""

    def delay_for(self, attempt: int, rng: random.Random | None = None) -> float:
        """Seconds to wait before ``attempt`` (1-based: attempt 2 is the first retry)."""
        raw = self.base_delay_seconds * (self.multiplier ** max(0, attempt - 1))
        capped = min(raw, self.max_delay_seconds)
        if self.jitter <= 0:
            return capped
        uniform = rng.uniform if rng is not None else random.uniform
        return capped * (1.0 - uniform(0.0, min(self.jitter, 1.0)))


# ---------------------------------------------------------------------------
# Schedule spec
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScheduleSpec:
    """When and how a single source should run.

    Exactly one of ``cron`` / ``interval_seconds`` must be set.
    """

    source_id: str
    cron: str | None = None
    interval_seconds: float | None = None
    enabled: bool = True
    run_on_start: bool = False
    timeout_seconds: float = 1800.0
    jitter_seconds: float = 0.0
    """Random delay added before each fire, so ten sources scheduled at 03:00
    don't all hit the network in the same second."""
    retry: RetryPolicy = field(default_factory=RetryPolicy)

    def __post_init__(self) -> None:
        if bool(self.cron) == bool(self.interval_seconds):
            raise ValueError(
                f"[{self.source_id}] set exactly one of cron / interval_seconds "
                f"(got cron={self.cron!r}, interval_seconds={self.interval_seconds!r})"
            )
        if self.interval_seconds is not None and self.interval_seconds <= 0:
            raise ValueError(f"[{self.source_id}] interval_seconds must be positive")
        if self.cron:
            CronExpression.parse(self.cron)  # fail fast at config load, not at 03:00

    @property
    def cron_expression(self) -> CronExpression | None:
        return CronExpression.parse(self.cron) if self.cron else None

    def next_fire_at(self, after: datetime, rng: random.Random | None = None) -> datetime:
        """Next firing time strictly after ``after``, including jitter."""
        if self.cron:
            base = CronExpression.parse(self.cron).next_after(after)
        else:
            assert self.interval_seconds is not None  # guaranteed by __post_init__
            base = after + timedelta(seconds=self.interval_seconds)
        if self.jitter_seconds > 0:
            uniform = rng.uniform if rng is not None else random.uniform
            base += timedelta(seconds=uniform(0.0, self.jitter_seconds))
        return base

    def describe(self) -> str:
        when = f"cron={self.cron}" if self.cron else f"every {self.interval_seconds:.0f}s"
        state = "enabled" if self.enabled else "disabled"
        return f"{self.source_id}: {when} ({state}, timeout={self.timeout_seconds:.0f}s)"
