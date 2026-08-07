"""
The missed-savings calculation: for each purchase, which shops in the user's own clubs
were running a deal on the same kind of thing.

This chain had no direct coverage before — it was only ever reached through mocks.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from models.transaction import AmountDetail, Transaction, TransactionAmount, TransactionCategory
from services.insights_service import MAX_ALTERNATIVE_STORES_PER_CLUB, InsightsService
from services.reference_data_repository import ReferenceDataRepository


def _store(store_id, categories):
    return SimpleNamespace(store_id=store_id, name=f"Shop {store_id}", metadata=SimpleNamespace(mcc_codes=categories))


def _club(club_id, store_ids):
    return SimpleNamespace(club_id=club_id, name=f"Club {club_id}", stores=store_ids)


def _tx(tx_id="t1", category_code="5411", charged=100.0, merchant="SUPER", sub="GROCERIES"):
    return Transaction(
        id=tx_id,
        categoryCode=category_code,
        merchantName=merchant,
        category=TransactionCategory(sub=sub),
        amount=TransactionAmount(chargedAmount=AmountDetail(amount=charged)),
    )


def _reference_data(clubs, stores, stores_by_category, stores_with_deals):
    repo = ReferenceDataRepository()
    repo._clubs = clubs
    repo._stores = stores
    repo._stores_by_category = stores_by_category
    repo._deals_by_store = {store_id: [SimpleNamespace(deal_id=f"d-{store_id}")] for store_id in stores_with_deals}
    repo._loaded = True
    return repo


def _service(repo) -> InsightsService:
    mcc = MagicMock()
    mcc.get_mcc_by_id = lambda code: {"5411": "GROCERIES", "5812": "RESTAURANT"}.get(str(code), "N/A")
    return InsightsService(
        open_finance_service=MagicMock(),
        files_service=MagicMock(),
        publisher_service=MagicMock(),
        user_repository=MagicMock(),
        reference_data_repository=repo,
        mcc_service=mcc,
    )


def _grocery_world():
    """Two grocery shops; only s1 is running a deal. Club c1 has s1, club c2 has s2."""
    s1, s2 = _store("s1", ["GROCERIES"]), _store("s2", ["GROCERIES"])
    return _reference_data(
        clubs={"c1": _club("c1", ["s1"]), "c2": _club("c2", ["s2"])},
        stores={"s1": s1, "s2": s2},
        stores_by_category={"GROCERIES": [s1, s2]},
        stores_with_deals={"s1"},
    )


def test_finds_a_deal_in_a_club_the_user_belongs_to():
    service = _service(_grocery_world())

    insights = service.missed_savings([_tx()], user_club_ids=["c1"])

    assert len(insights) == 1
    insight = insights[0]
    assert insight.transaction_id == "t1"
    assert insight.had_discount is True
    assert insight.store_name == "SUPER"
    assert insight.mcc_code == "GROCERIES"
    assert insight.mcc_description == "GROCERIES"
    assert insight.amount == 100.0

    assert len(insight.missed_store_discont) == 1
    missed = insight.missed_store_discont[0]
    assert missed.club_id == "c1"
    assert missed.store_count == 1
    assert [s.store_id for s in missed.missed_store] == ["s1"]


def test_ignores_clubs_the_user_has_not_joined():
    # s2 is the only shop in c2, and it has no deal — but the user is not in c2 anyway.
    service = _service(_grocery_world())

    insights = service.missed_savings([_tx()], user_club_ids=["c2"])

    assert insights[0].had_discount is False
    assert insights[0].missed_store_discont == []


def test_no_clubs_means_nothing_was_missed():
    service = _service(_grocery_world())

    insights = service.missed_savings([_tx()], user_club_ids=[])

    assert insights[0].had_discount is False


def test_shops_without_an_active_deal_are_not_offered():
    s1 = _store("s1", ["GROCERIES"])
    repo = _reference_data(
        clubs={"c1": _club("c1", ["s1"])},
        stores={"s1": s1},
        stores_by_category={"GROCERIES": [s1]},
        stores_with_deals=set(),  # nobody is running a deal
    )
    service = _service(repo)

    insights = service.missed_savings([_tx()], user_club_ids=["c1"])

    assert insights[0].had_discount is False


def test_purchases_without_an_id_or_category_are_skipped():
    service = _service(_grocery_world())

    transactions = [
        _tx(tx_id=None),
        _tx(tx_id="t2", category_code=None),
        _tx(tx_id="t3"),
    ]

    insights = service.missed_savings(transactions, user_club_ids=["c1"])

    assert [i.transaction_id for i in insights] == ["t3"]


def test_unknown_category_yields_no_alternatives():
    service = _service(_grocery_world())

    insights = service.missed_savings([_tx(category_code="9999")], user_club_ids=["c1"])

    assert insights[0].mcc_code == "N/A"
    assert insights[0].had_discount is False


def test_a_club_never_offers_more_than_ten_shops():
    many = [_store(f"s{i}", ["GROCERIES"]) for i in range(25)]
    repo = _reference_data(
        clubs={"c1": _club("c1", [s.store_id for s in many])},
        stores={s.store_id: s for s in many},
        stores_by_category={"GROCERIES": many},
        stores_with_deals={s.store_id for s in many},
    )
    service = _service(repo)

    insights = service.missed_savings([_tx()], user_club_ids=["c1"])

    missed = insights[0].missed_store_discont[0]
    assert missed.store_count == MAX_ALTERNATIVE_STORES_PER_CLUB
    assert len(missed.missed_store) == MAX_ALTERNATIVE_STORES_PER_CLUB


def test_no_transactions_returns_nothing():
    service = _service(_grocery_world())

    assert service.missed_savings([], user_club_ids=["c1"]) == []


def test_falls_back_to_the_original_amount_when_nothing_was_charged():
    service = _service(_grocery_world())
    transaction = _tx()
    transaction.amount = TransactionAmount(originalAmount=AmountDetail(amount=42.5))

    insights = service.missed_savings([transaction], user_club_ids=["c1"])

    assert insights[0].amount == 42.5
