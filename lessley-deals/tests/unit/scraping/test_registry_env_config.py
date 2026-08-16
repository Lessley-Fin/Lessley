"""Env-driven adapter configuration in the registry.

The long-running worker never parses CLI flags, so anything the CLI exposes as
an option has to be reachable from the environment or the worker simply cannot
use it.
"""

from __future__ import annotations

from lessley_deals.scraping.registry import SourceRegistry
from lessley_deals.scraping.sources.hot import BENEFIT_TYPES


def _hot(monkeypatch, **env):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    registry = SourceRegistry()
    registry.register_defaults(include_llm_sites=False)
    return registry.get("hot")


def test_hot_scrapes_every_benefit_type_by_default(monkeypatch):
    monkeypatch.delenv("HOT_FETCH_DETAILS", raising=False)

    assert _hot(monkeypatch)._benefit_types == BENEFIT_TYPES
    assert len(BENEFIT_TYPES) == 7


def test_hot_detail_fetching_is_off_unless_asked(monkeypatch):
    monkeypatch.delenv("HOT_FETCH_DETAILS", raising=False)

    # Detail fetching is an extra request per benefit — opt-in, not the default.
    assert _hot(monkeypatch)._fetch_details is False


def test_hot_fetch_details_enabled_by_env(monkeypatch):
    assert _hot(monkeypatch, HOT_FETCH_DETAILS="1")._fetch_details is True


def test_hot_fetch_details_accepts_common_truthy_spellings(monkeypatch):
    for value in ("1", "true", "TRUE", "yes", "on"):
        assert _hot(monkeypatch, HOT_FETCH_DETAILS=value)._fetch_details is True, value


def test_hot_fetch_details_rejects_falsy_spellings(monkeypatch):
    for value in ("0", "false", "no", "off", ""):
        assert _hot(monkeypatch, HOT_FETCH_DETAILS=value)._fetch_details is False, value


def test_hot_delays_are_configurable(monkeypatch):
    hot = _hot(monkeypatch, HOT_REQUEST_DELAY="3.5", HOT_DETAILS_DELAY="4")

    assert hot._request_delay == 3.5
    assert hot._details_delay == 4.0


def test_hot_delays_fall_back_when_unparseable(monkeypatch):
    # A typo in an env var must not crash the worker on startup.
    hot = _hot(monkeypatch, HOT_REQUEST_DELAY="fast", HOT_DETAILS_DELAY="-1")

    assert hot._request_delay == 1.5
    assert hot._details_delay == 2.0


def test_other_adapters_still_register(monkeypatch):
    monkeypatch.setenv("HOT_FETCH_DETAILS", "1")
    registry = SourceRegistry()
    registry.register_defaults(include_llm_sites=False)

    # Named rather than counted: a bare count says nothing about which adapter
    # went missing, and this list is the definitive answer to "what does a
    # `scrape --all` actually run".
    assert set(registry.list_all()) == {
        "behatsdaa",
        "hever_gift_card_company",
        "hever_teamim_card_store",
        "hot",
        "mastercard",
        "paisplus",
        # The cash-card programs are one source per membership tier.
        "paisplus_food_chains_regular",
        "paisplus_food_chains_vip",
        "paisplus_networks_regular",
        "paisplus_networks_vip",
        "swish",
        "topcash",
    }
