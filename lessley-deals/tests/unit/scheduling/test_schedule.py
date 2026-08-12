"""Cron parsing, next-fire computation and retry backoff."""

from __future__ import annotations

import random
from datetime import datetime, timezone

import pytest

from lessley_deals.scheduling.schedule import (
    CronExpression,
    CronParseError,
    RetryPolicy,
    ScheduleSpec,
)

MONDAY_NOON = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)  # a Monday


@pytest.mark.parametrize(
    "expression,expected",
    [
        ("0 3 * * *", datetime(2026, 1, 6, 3, 0, tzinfo=timezone.utc)),      # tomorrow 03:00
        ("*/15 * * * *", datetime(2026, 1, 5, 12, 15, tzinfo=timezone.utc)),  # next quarter
        ("0 13 * * *", datetime(2026, 1, 5, 13, 0, tzinfo=timezone.utc)),     # later today
        ("0 4 1 * *", datetime(2026, 2, 1, 4, 0, tzinfo=timezone.utc)),       # 1st of next month
        ("0 5 * * 0", datetime(2026, 1, 11, 5, 0, tzinfo=timezone.utc)),      # next Sunday
        ("30 2 * * 1-5", datetime(2026, 1, 6, 2, 30, tzinfo=timezone.utc)),   # weekdays
        ("0 0 1 jan *", datetime(2027, 1, 1, 0, 0, tzinfo=timezone.utc)),     # month by name
    ],
)
def test_next_after(expression: str, expected: datetime) -> None:
    assert CronExpression.parse(expression).next_after(MONDAY_NOON) == expected


def test_next_after_is_strict() -> None:
    """Firing exactly now must return the *next* occurrence, never now again —
    otherwise a fast run would loop on itself."""
    at_noon = CronExpression.parse("0 12 * * *")
    assert at_noon.next_after(MONDAY_NOON) == datetime(2026, 1, 6, 12, 0, tzinfo=timezone.utc)


def test_day_of_month_and_day_of_week_are_a_union() -> None:
    """Vixie cron semantics: "1st of the month OR any Friday"."""
    expression = CronExpression.parse("0 0 1 * 5")
    assert expression.matches(datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc))   # 1st (a Sunday)
    assert expression.matches(datetime(2026, 3, 6, 0, 0, tzinfo=timezone.utc))   # a Friday
    assert not expression.matches(datetime(2026, 3, 4, 0, 0, tzinfo=timezone.utc))


@pytest.mark.parametrize(
    "bad",
    ["0 3 * *", "60 * * * *", "* 25 * * *", "0 3 * * 9", "a b c d e", "*/0 * * * *"],
)
def test_invalid_expressions_are_rejected(bad: str) -> None:
    with pytest.raises(CronParseError):
        CronExpression.parse(bad)


def test_bad_cron_fails_at_config_time_not_at_runtime() -> None:
    """A typo must break startup loudly, not silently skip a source at 03:00."""
    with pytest.raises(CronParseError):
        ScheduleSpec(source_id="hot", cron="0 99 * * *")


def test_exactly_one_of_cron_or_interval() -> None:
    with pytest.raises(ValueError):
        ScheduleSpec(source_id="hot")
    with pytest.raises(ValueError):
        ScheduleSpec(source_id="hot", cron="0 3 * * *", interval_seconds=60)


def test_interval_schedule() -> None:
    spec = ScheduleSpec(source_id="hot", interval_seconds=900)
    assert (spec.next_fire_at(MONDAY_NOON) - MONDAY_NOON).total_seconds() == 900


def test_jitter_is_bounded_and_forward_only() -> None:
    spec = ScheduleSpec(source_id="hot", interval_seconds=600, jitter_seconds=60)
    rng = random.Random(7)
    for _ in range(50):
        offset = (spec.next_fire_at(MONDAY_NOON, rng) - MONDAY_NOON).total_seconds()
        assert 600 <= offset <= 660


def test_backoff_grows_and_is_capped() -> None:
    policy = RetryPolicy(base_delay_seconds=10, multiplier=2, max_delay_seconds=100, jitter=0)
    assert [policy.delay_for(i) for i in range(1, 6)] == [10, 20, 40, 80, 100]


def test_jittered_backoff_never_exceeds_the_cap() -> None:
    policy = RetryPolicy(base_delay_seconds=10, multiplier=2, max_delay_seconds=100, jitter=0.3)
    rng = random.Random(1)
    for attempt in range(1, 8):
        delay = policy.delay_for(attempt, rng)
        assert 0 < delay <= 100
