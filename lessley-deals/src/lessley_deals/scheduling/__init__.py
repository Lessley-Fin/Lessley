"""Scheduling: independent, concurrent, retrying execution of every scraper.

Public surface::

    ScheduleSpec / RetryPolicy / CronExpression   – when a source runs
    load_schedules                                – config file + env overrides
    SourceRunner                                  – retry, timeout, lock, journal
    SchedulerService                              – one asyncio loop per source
    run_service                                   – the worker process entrypoint
"""

from lessley_deals.scheduling.config import load_schedules
from lessley_deals.scheduling.journal import RunJournal, RunRecord
from lessley_deals.scheduling.locks import MongoLeaseLock, NullRunLock, RunLock
from lessley_deals.scheduling.runner import JobResult, SourceJob, SourceRunner
from lessley_deals.scheduling.schedule import (
    CronExpression,
    CronParseError,
    RetryPolicy,
    ScheduleSpec,
)
from lessley_deals.scheduling.scheduler import SchedulerService

__all__ = [
    "CronExpression",
    "CronParseError",
    "JobResult",
    "MongoLeaseLock",
    "NullRunLock",
    "RetryPolicy",
    "RunJournal",
    "RunLock",
    "RunRecord",
    "ScheduleSpec",
    "SchedulerService",
    "SourceJob",
    "SourceRunner",
    "load_schedules",
]
