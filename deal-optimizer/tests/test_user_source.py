"""Resolving the caller's loyalty programs from the identity the edge verified.

Eligibility is the one input a client must not be able to supply, so this is the seam
that decides which deals a user is offered. The mapping goes club id -> source_id via the
``clubs`` collection, because the ``club_``-prefix convention is hand-maintained and a club
that broke it would silently prune the deals its own members are entitled to.
"""

from __future__ import annotations

import pytest

from deal_optimizer.user_source import club_source_ids, load_user_clubs, member_source_ids_for


class FakeCollection:
    def __init__(self, docs: list[dict]) -> None:
        self.docs = docs
        self.queries: list[dict] = []

    def find_one(self, query: dict, projection: dict | None = None):
        self.queries.append(query)
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in query.items()):
                return doc
        return None

    def find(self, query: dict, projection: dict | None = None):
        self.queries.append(query)
        wanted: set = set()
        for clause in query.get("$or", []):
            for value in clause.values():
                wanted.update(value.get("$in", []))
        return iter([d for d in self.docs if d.get("_id") in wanted or d.get("id") in wanted])


class FakeDb:
    def __init__(self, users: list[dict], clubs: list[dict]) -> None:
        self.collections = {"users": FakeCollection(users), "clubs": FakeCollection(clubs)}

    def __getitem__(self, name: str) -> FakeCollection:
        return self.collections[name]


USERS = [{"NormalizedEmail": "USER@EXAMPLE.COM", "Clubs": ["club_hot", "club_mastercard"]}]
CLUBS = [
    {"_id": "club_hot", "source_id": "hot"},
    {"_id": "club_mastercard", "source_id": "mastercard"},
    {"_id": "club_hever_gift_card_company", "source_id": "hever_gift_card_company"},
]


# ── Reading the user ──────────────────────────────────────────────────────────

def test_clubs_are_read_for_the_normalized_email():
    db = FakeDb(USERS, CLUBS)

    assert load_user_clubs("user@example.com", db) == ["club_hot", "club_mastercard"]
    # ASP.NET Identity stores the uppercased address; Personalization keys on it the same way.
    assert db["users"].queries[0] == {"NormalizedEmail": "USER@EXAMPLE.COM"}


@pytest.mark.parametrize("email", [" user@example.com ", "User@Example.com"])
def test_the_email_is_trimmed_and_upcased(email):
    assert load_user_clubs(email, FakeDb(USERS, CLUBS)) == ["club_hot", "club_mastercard"]


def test_an_unknown_user_is_none_not_empty():
    # The distinction the endpoint turns into a 404 rather than pricing optimistically.
    assert load_user_clubs("nobody@example.com", FakeDb(USERS, CLUBS)) is None


def test_a_user_who_joined_nothing_is_an_empty_list():
    db = FakeDb([{"NormalizedEmail": "U@E.COM", "Clubs": []}], CLUBS)

    assert load_user_clubs("u@e.com", db) == []


def test_a_missing_clubs_field_is_an_empty_list():
    db = FakeDb([{"NormalizedEmail": "U@E.COM"}], CLUBS)

    assert load_user_clubs("u@e.com", db) == []


# ── Mapping club ids to source_ids ────────────────────────────────────────────

def test_source_ids_come_from_the_clubs_collection():
    assert club_source_ids(["club_hot", "club_mastercard"], FakeDb(USERS, CLUBS)) == ["hot", "mastercard"]


def test_a_club_keyed_on_id_rather_than_underscore_id_still_resolves():
    # Rows imported from main/resources/clubs.json keep the business key in `id`.
    db = FakeDb(USERS, [{"_id": "objectid-ish", "id": "club_hot", "source_id": "hot"}])

    assert club_source_ids(["club_hot"], db) == ["hot"]


def test_a_source_id_that_is_not_the_stripped_prefix_is_honoured():
    # The reason this is a lookup and not string surgery: nothing guarantees the id
    # convention, and guessing would prune deals the member is entitled to.
    db = FakeDb(USERS, [{"_id": "club_hot", "source_id": "hot_israel_benefits"}])

    assert club_source_ids(["club_hot"], db) == ["hot_israel_benefits"]


def test_a_club_missing_from_the_collection_falls_back_to_the_prefix():
    db = FakeDb(USERS, CLUBS)

    assert club_source_ids(["club_unlisted"], db) == ["unlisted"]


def test_a_bare_source_id_passes_through():
    assert club_source_ids(["topcash"], FakeDb(USERS, CLUBS)) == ["topcash"]


def test_duplicates_collapse():
    db = FakeDb(USERS, CLUBS)

    assert club_source_ids(["club_hot", "club_hot", "hot"], db) == ["hot"]


def test_no_clubs_needs_no_lookup():
    db = FakeDb(USERS, CLUBS)

    assert club_source_ids([], db) == []
    assert db["clubs"].queries == []


# ── The two combined ──────────────────────────────────────────────────────────

def test_member_source_ids_for_resolves_end_to_end():
    assert member_source_ids_for("user@example.com", FakeDb(USERS, CLUBS)) == ["hot", "mastercard"]


def test_member_source_ids_for_keeps_none_for_an_unknown_user():
    assert member_source_ids_for("nobody@example.com", FakeDb(USERS, CLUBS)) is None


def test_member_source_ids_for_keeps_empty_for_a_club_less_user():
    # [] must survive as [] — it prunes, where None would open every gated deal.
    db = FakeDb([{"NormalizedEmail": "U@E.COM", "Clubs": []}], CLUBS)

    assert member_source_ids_for("u@e.com", db) == []
