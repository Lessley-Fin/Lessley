"""The seeded club list must cover every registered scraper.

PersistStage stamps ``Deal.club_id`` from a ``source_id -> club_id`` map built
off this list, so a source without a club silently produces deals with
``club_id = None`` — nothing raises, the deals just come out unattributed.
"""

from __future__ import annotations

import json
from pathlib import Path

from lessley_deals.persistence.seeding import load_clubs
from lessley_deals.scraping.registry import SourceRegistry

SEED_CLUBS = Path(__file__).resolve().parents[3] / "data" / "seed" / "clubs.json"


def _registered_source_ids() -> list[str]:
    registry = SourceRegistry()
    # LLM-backed sites are config-driven and not always enabled; the hand-coded
    # adapters are the set that must always have a club.
    registry.register_defaults(include_llm_sites=False)
    return registry.list_all()


def test_seed_file_exists_and_parses():
    clubs = json.loads(SEED_CLUBS.read_text(encoding="utf-8"))

    assert clubs, "data/seed/clubs.json is empty"
    for club in clubs:
        assert club["id"], club
        assert club["source_id"], club
        assert club["name"], club


def test_every_registered_source_has_a_club():
    clubs = json.loads(SEED_CLUBS.read_text(encoding="utf-8"))
    by_source = {c["source_id"] for c in clubs}

    missing = sorted(set(_registered_source_ids()) - by_source)

    assert not missing, f"registered scrapers with no club entry: {missing}"


def test_club_ids_follow_the_source_id_convention():
    clubs = json.loads(SEED_CLUBS.read_text(encoding="utf-8"))

    wrong = [c["id"] for c in clubs if c["id"] != f"club_{c['source_id']}"]

    assert not wrong, f"club ids must be 'club_<source_id>': {wrong}"


def test_club_ids_and_source_ids_are_unique():
    clubs = json.loads(SEED_CLUBS.read_text(encoding="utf-8"))

    ids = [c["id"] for c in clubs]
    sources = [c["source_id"] for c in clubs]

    assert len(ids) == len(set(ids)), "duplicate club ids"
    assert len(sources) == len(set(sources)), "duplicate source_ids"


def test_load_clubs_maps_id_onto_mongo_id():
    clubs = load_clubs(SEED_CLUBS.parents[1])

    assert clubs, "load_clubs returned nothing for the real seed dir"
    for club in clubs:
        assert club["_id"], club
        # `id` must not survive alongside `_id` or Mongo stores a stale duplicate.
        assert "id" not in club, club
