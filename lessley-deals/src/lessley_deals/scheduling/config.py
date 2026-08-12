"""Loading schedules from ``data/seed/schedules.json`` + environment overrides.

Precedence (last wins)::

    built-in default  →  schedules.json entry  →  DEALS_SCHEDULE_<SOURCE> env var

The env override exists so an operator can silence a misbehaving scraper in
production without a redeploy::

    DEALS_SCHEDULE_HOT="0 */6 * * *"     # re-schedule
    DEALS_SCHEDULE_BEHATSDAA="off"       # disable entirely
    DEALS_SCHEDULE_LLM_FOO="900s"        # every 15 minutes

Source ids containing characters illegal in an env var name (``llm:foo``) are
upper-cased with non-alphanumerics turned into underscores: ``LLM_FOO``.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Iterable

from lessley_deals.scheduling.schedule import RetryPolicy, ScheduleSpec

logger = logging.getLogger(__name__)

DEFAULT_CRON = "0 3 * * *"
"""Nightly at 03:00 UTC — safe default for a source with no explicit schedule."""

_ENV_PREFIX = "DEALS_SCHEDULE_"
_INTERVAL_RE = re.compile(r"^(?P<value>\d+(?:\.\d+)?)(?P<unit>[smhd])?$", re.IGNORECASE)
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def _env_key(source_id: str) -> str:
    return _ENV_PREFIX + re.sub(r"[^A-Za-z0-9]+", "_", source_id).upper()


def _default_schedules_path() -> Path:
    """Where to look for ``schedules.json``, most specific location first.

    ``DEALS_DATA_DIR`` has to come first because walking up from ``__file__``
    only works in a source checkout: once the package is pip-installed (every
    container image) that walk lands in site-packages' *parent*
    (``/usr/local/lib/python3.12/data/seed/...``) and finds nothing, so every
    source would silently fall back to :data:`DEFAULT_CRON`.

    When neither exists, the first candidate is returned so the "no schedules
    file at ..." warning names the path the operator most likely meant.
    """
    candidates: list[Path] = []
    data_dir = os.environ.get("DEALS_DATA_DIR")
    if data_dir:
        candidates.append(Path(data_dir) / "seed" / "schedules.json")
    # config.py lives at src/lessley_deals/scheduling/config.py in a checkout
    candidates.append(Path(__file__).resolve().parents[3] / "data" / "seed" / "schedules.json")

    return next((c for c in candidates if c.exists()), candidates[0])


def _parse_interval(text: str) -> float | None:
    """``"900"`` / ``"15m"`` / ``"6h"`` → seconds. None when not an interval."""
    match = _INTERVAL_RE.match(text.strip())
    if match is None:
        return None
    return float(match.group("value")) * _UNIT_SECONDS[(match.group("unit") or "s").lower()]


def _retry_from(data: dict[str, Any] | None) -> RetryPolicy:
    if not data:
        return RetryPolicy()
    return RetryPolicy(
        max_attempts=int(data.get("max_attempts", 3)),
        base_delay_seconds=float(data.get("base_delay_seconds", 10.0)),
        max_delay_seconds=float(data.get("max_delay_seconds", 300.0)),
        multiplier=float(data.get("multiplier", 2.0)),
        jitter=float(data.get("jitter", 0.3)),
    )


def _spec_from_entry(entry: dict[str, Any]) -> ScheduleSpec:
    source_id = entry["source_id"]
    cron = entry.get("cron")
    interval = entry.get("interval_seconds")
    if cron is None and interval is None:
        cron = DEFAULT_CRON
    return ScheduleSpec(
        source_id=source_id,
        cron=cron,
        interval_seconds=float(interval) if interval is not None else None,
        enabled=bool(entry.get("enabled", True)),
        run_on_start=bool(entry.get("run_on_start", False)),
        timeout_seconds=float(entry.get("timeout_seconds", 1800.0)),
        jitter_seconds=float(entry.get("jitter_seconds", 0.0)),
        retry=_retry_from(entry.get("retry")),
    )


def _apply_env_override(spec: ScheduleSpec) -> ScheduleSpec:
    """Apply ``DEALS_SCHEDULE_<SOURCE>``: ``off`` | ``<interval>`` | ``<cron>``."""
    raw = os.environ.get(_env_key(spec.source_id))
    if raw is None:
        return spec
    value = raw.strip()

    if value.lower() in ("off", "false", "0", "disabled"):
        logger.info("Source %s disabled via %s", spec.source_id, _env_key(spec.source_id))
        return ScheduleSpec(
            source_id=spec.source_id,
            cron=spec.cron,
            interval_seconds=spec.interval_seconds,
            enabled=False,
            run_on_start=False,
            timeout_seconds=spec.timeout_seconds,
            jitter_seconds=spec.jitter_seconds,
            retry=spec.retry,
        )

    interval = _parse_interval(value)
    logger.info("Source %s schedule overridden via env: %s", spec.source_id, value)
    return ScheduleSpec(
        source_id=spec.source_id,
        cron=None if interval is not None else value,
        interval_seconds=interval,
        enabled=spec.enabled,
        run_on_start=spec.run_on_start,
        timeout_seconds=spec.timeout_seconds,
        jitter_seconds=spec.jitter_seconds,
        retry=spec.retry,
    )


def load_schedules(
    known_source_ids: Iterable[str],
    path: Path | None = None,
    *,
    include_unlisted: bool = True,
) -> list[ScheduleSpec]:
    """Build the schedule list for the registered sources.

    Unknown ids in the file are dropped with a warning (a typo must not create a
    phantom source).  Registered sources missing from the file get
    :data:`DEFAULT_CRON` when ``include_unlisted`` — a newly added scraper
    therefore starts running without a config change.
    """
    known = list(known_source_ids)
    known_set = set(known)
    config_path = path or _default_schedules_path()

    entries: list[dict[str, Any]] = []
    if config_path.exists():
        try:
            loaded = json.loads(config_path.read_text(encoding="utf-8"))
            entries = loaded if isinstance(loaded, list) else []
            if not isinstance(loaded, list):
                logger.error("%s must contain a JSON array — ignoring it", config_path)
        except json.JSONDecodeError as exc:
            logger.error("Cannot parse %s (%s) — falling back to defaults", config_path, exc)
    else:
        logger.info("No schedules file at %s — using defaults for every source", config_path)

    specs: dict[str, ScheduleSpec] = {}
    for entry in entries:
        if "_comment" in entry and "source_id" not in entry:
            continue  # JSON has no comments; a `_comment` object is the idiom
        source_id = entry.get("source_id")
        if not source_id:
            logger.warning("Schedule entry without source_id ignored: %s", entry)
            continue
        if source_id not in known_set:
            logger.warning("Schedule for unknown source %r ignored", source_id)
            continue
        try:
            specs[source_id] = _spec_from_entry(entry)
        except (ValueError, KeyError) as exc:
            logger.error("Invalid schedule for %s: %s — source will not run", source_id, exc)

    if include_unlisted:
        for source_id in known:
            specs.setdefault(source_id, _spec_from_entry({"source_id": source_id}))

    return [_apply_env_override(spec) for spec in (specs[sid] for sid in known if sid in specs)]
