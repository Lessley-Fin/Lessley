"""Locating schedules.json, and the env overrides layered on top of it."""

from __future__ import annotations

import json

from lessley_deals.scheduling.config import (
    DEFAULT_CRON,
    _default_schedules_path,
    load_schedules,
)


def _write_schedules(root, entries):
    seed = root / "seed"
    seed.mkdir(parents=True, exist_ok=True)
    path = seed / "schedules.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


def test_data_dir_wins_over_the_source_tree_layout(tmp_path, monkeypatch):
    # Walking up from __file__ only resolves in a checkout. Once the package is
    # pip-installed (every container image) it lands in site-packages' parent,
    # so DEALS_DATA_DIR has to be consulted first or the file is never found.
    expected = _write_schedules(tmp_path, [])
    monkeypatch.setenv("DEALS_DATA_DIR", str(tmp_path))

    assert _default_schedules_path() == expected


def test_falls_back_to_the_source_tree_when_data_dir_has_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DEALS_DATA_DIR", str(tmp_path))  # nothing written there

    resolved = _default_schedules_path()

    assert resolved.parts[-3:] == ("data", "seed", "schedules.json")
    assert not str(resolved).startswith(str(tmp_path))


def test_missing_everywhere_reports_the_data_dir_path(tmp_path, monkeypatch):
    # The path is only used for the "no schedules file at ..." warning; it should
    # name where the operator meant to put it, not a site-packages dead end.
    monkeypatch.setenv("DEALS_DATA_DIR", str(tmp_path / "absent"))
    monkeypatch.setattr(
        "lessley_deals.scheduling.config.Path.exists", lambda self: False
    )

    assert _default_schedules_path() == tmp_path / "absent" / "seed" / "schedules.json"


def test_schedules_are_read_from_the_data_dir(tmp_path, monkeypatch):
    _write_schedules(tmp_path, [{"source_id": "hot", "cron": "0 2 1,15 * *"}])
    monkeypatch.setenv("DEALS_DATA_DIR", str(tmp_path))

    specs = load_schedules(["hot"])

    assert [s.cron for s in specs] == ["0 2 1,15 * *"]


def test_unlisted_source_gets_the_default_cron(tmp_path, monkeypatch):
    _write_schedules(tmp_path, [{"source_id": "hot", "cron": "0 2 1,15 * *"}])
    monkeypatch.setenv("DEALS_DATA_DIR", str(tmp_path))

    specs = {s.source_id: s for s in load_schedules(["hot", "newcomer"])}

    assert specs["newcomer"].cron == DEFAULT_CRON


def test_env_override_replaces_the_file_schedule(tmp_path, monkeypatch):
    _write_schedules(tmp_path, [{"source_id": "hot", "cron": "0 2 1,15 * *"}])
    monkeypatch.setenv("DEALS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DEALS_SCHEDULE_HOT", "0 */6 * * *")

    specs = load_schedules(["hot"])

    assert specs[0].cron == "0 */6 * * *"


def test_env_override_can_disable_a_source(tmp_path, monkeypatch):
    _write_schedules(tmp_path, [{"source_id": "hot", "cron": "0 2 1,15 * *"}])
    monkeypatch.setenv("DEALS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DEALS_SCHEDULE_HOT", "off")

    assert load_schedules(["hot"])[0].enabled is False
