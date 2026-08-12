"""Clubs get the shops they actually have deals at.

Both club-aware features read ``club.stores``: recommendations score "how many of this
club's shops sell what the user buys", and missed-savings picks alternatives per club. The
field is filled incrementally by the scraping pipeline, so a database whose clubs were
imported rather than scraped has it empty on every club — and the failure is silent, since
``recommend_clubs`` simply drops clubs with no stores and returns an empty list.

``_attach_club_stores`` derives the relation from the deals already loaded instead.
"""

from types import SimpleNamespace

from services.reference_data_repository import ReferenceDataRepository


def _deal(deal_id: str, club_id: str | None, store_id: str) -> SimpleNamespace:
    return SimpleNamespace(deal_id=deal_id, club_id=club_id, store_id=store_id)


def _repo(clubs: dict, deals: dict) -> ReferenceDataRepository:
    repo = ReferenceDataRepository()
    repo._clubs = clubs
    repo._deals_by_id = deals
    repo._loaded = True
    return repo


def test_clubs_with_no_stores_are_filled_from_their_deals():
    clubs = {"club_hot": SimpleNamespace(club_id="club_hot", name="HOT", stores=[])}
    deals = {
        "d1": _deal("d1", "club_hot", "s1"),
        "d2": _deal("d2", "club_hot", "s2"),
        "d3": _deal("d3", "club_hot", "s1"),  # same store twice — counted once
    }

    _repo(clubs, deals)._attach_club_stores()

    assert clubs["club_hot"].stores == ["s1", "s2"]


def test_an_existing_store_membership_is_kept_and_unioned():
    # A curated membership must never be lost by deriving.
    clubs = {"c1": SimpleNamespace(club_id="c1", name="Club", stores=["curated"])}
    deals = {"d1": _deal("d1", "c1", "from_deal")}

    _repo(clubs, deals)._attach_club_stores()

    assert clubs["c1"].stores == ["curated", "from_deal"]


def test_a_club_with_no_deals_is_left_untouched():
    clubs = {
        "with_deals": SimpleNamespace(club_id="with_deals", name="A", stores=[]),
        "no_deals": SimpleNamespace(club_id="no_deals", name="B", stores=["kept"]),
    }
    deals = {"d1": _deal("d1", "with_deals", "s1")}

    _repo(clubs, deals)._attach_club_stores()

    assert clubs["with_deals"].stores == ["s1"]
    assert clubs["no_deals"].stores == ["kept"]


def test_deals_without_a_club_are_ignored():
    clubs = {"c1": SimpleNamespace(club_id="c1", name="Club", stores=[])}
    deals = {"orphan": _deal("orphan", None, "s1"), "d1": _deal("d1", "c1", "s2")}

    _repo(clubs, deals)._attach_club_stores()

    assert clubs["c1"].stores == ["s2"]


def test_a_deal_naming_an_unknown_club_does_not_raise():
    clubs = {"c1": SimpleNamespace(club_id="c1", name="Club", stores=[])}
    deals = {"d1": _deal("d1", "club_that_does_not_exist", "s1")}

    _repo(clubs, deals)._attach_club_stores()

    assert clubs["c1"].stores == []


def test_recommendations_become_possible_after_deriving():
    # The end-to-end shape of the bug: identical inputs, empty club.stores, and the club
    # scores total_stores=0 — which recommend_clubs filters out entirely.
    club = SimpleNamespace(club_id="club_hot", name="HOT", stores=[])
    repo = _repo({"club_hot": club}, {"d1": _deal("d1", "club_hot", "s1")})

    assert len(club.stores) == 0  # before: nothing to score, so no recommendation

    repo._attach_club_stores()

    assert len(club.stores) == 1  # after: the club can be scored
