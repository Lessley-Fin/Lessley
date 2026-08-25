"""
Missed savings: which shops running a deal could this purchase have been made at.

Alternatives used to be chosen by MCC category, which meant any of the thousands of shops
selling that kind of thing. They are now chosen by *name*, so the answer is about where the
user actually shopped. The bar is deliberately lower than the strict matcher's: landing on
another café is useful, landing on a car park is not.
"""

import pytest

from itertools import combinations
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from models.transaction import (
    AmountDetail,
    MerchantAddress,
    Transaction,
    TransactionAmount,
    TransactionCategory,
)
from config.constants import SHOP_MATCH
from services.insights_service import InsightsService
from services.reference_data_repository import ReferenceDataRepository
from services.utils.store_identity import build_identities
from services.utils.store_similarity import DealShopFinder, EXACT, SIMILAR, STRONG


def _store(store_id, name, categories=()):
    return SimpleNamespace(
        store_id=store_id,
        name=name,
        metadata=SimpleNamespace(mcc_codes=list(categories), official_name=None),
    )


def _alias(store_id, alias):
    return SimpleNamespace(store_id=store_id, alias=alias)


def _deal(store_id, title="Half price"):
    return SimpleNamespace(deal_id=f"d-{store_id}", store_id=store_id, title=title)


def _club(club_id, store_ids):
    return SimpleNamespace(club_id=club_id, name=f"Club {club_id}", stores=list(store_ids))


def _tx(tx_id="t1", merchant="קפה קפה", category_code="5812", charged=100.0,
        sub="RESTAURANT", town=None, account=None):
    return Transaction(
        id=tx_id,
        accountId=account,
        categoryCode=category_code,
        merchantName=merchant,
        merchantAddress=MerchantAddress(townName=town) if town else None,
        category=TransactionCategory(sub=sub),
        # `charged` reads as "spent this much", but the feed signs a purchase negative and a
        # refund positive — and the insights now rely on that sign to tell the two apart.
        amount=TransactionAmount(chargedAmount=AmountDetail(amount=-abs(charged), currency="ILS")),
    )


# A stand-in catalogue.
#
# The filler is not padding. Rarity decides every verdict here, and it is a log ratio, so a
# word's share of a 200-shop fixture is *not* the thing to match — its resulting rarity is.
# 'קפה' sits in 136 of the 8,612 real shops and scores about 0.45; these counts land each
# word within ~0.02 of that, which is what keeps the thresholds meaning the same thing here
# as they do in production.
STORE_COUNT = 200
COMMON_WORD_COUNTS = {"קפה": 18, "פיצה": 18, "מסעדה": 11, "פרחים": 8, "בר": 12}


def _world(stores=(), aliases=(), clubs=None, without_deals=()):
    """A repository holding these shops, every one of them running a deal unless said."""
    stores = list(stores)
    counter = 0
    for word, appearances in COMMON_WORD_COUNTS.items():
        for _ in range(appearances):
            counter += 1
            stores.append(_store(f"filler-{counter}", f"{word} יחיד{counter}"))
    while len(stores) < STORE_COUNT:
        counter += 1
        stores.append(_store(f"filler-{counter}", f"חנות{counter} יחידה{counter}"))

    skip = set(without_deals)
    deals_by_store = {
        store.store_id: [_deal(store.store_id)]
        for store in stores
        if store.store_id not in skip
    }

    repo = ReferenceDataRepository()
    repo._stores = {store.store_id: store for store in stores}
    repo._deals_by_store = deals_by_store
    repo._clubs = clubs if clubs is not None else {
        "c1": _club("c1", [store.store_id for store in stores])
    }
    repo._identities = build_identities(stores, aliases, deals_by_store)
    repo._identity_of_store = {
        store_id: identity.store_id
        for identity in repo._identities.values()
        for store_id in identity.store_ids
    }
    repo._deal_shops = DealShopFinder(list(repo._identities.values()))
    repo._loaded = True
    return repo


def _service(repo) -> InsightsService:
    mcc = MagicMock()
    mcc.get_mcc_by_id = lambda code: {"5812": "RESTAURANT", "5411": "GROCERIES"}.get(str(code), "N/A")
    return InsightsService(
        open_finance_service=MagicMock(),
        files_service=MagicMock(),
        publisher_service=MagicMock(),
        user_repository=MagicMock(),
        reference_data_repository=repo,
        mcc_service=mcc,
    )


# ── Finding the shop itself ───────────────────────────────────────────────────


def test_finds_the_shop_the_user_actually_bought_from():
    repo = _world([_store("s1", "סטימצקי", ["BOOKS_&_GAMES"])])
    shops = repo.find_deal_shops("סטימצקי G כפר סבא", "כפר סבא", "BOOKS_&_GAMES")

    assert shops[0].identity.name == "סטימצקי"
    assert shops[0].is_confident


def test_an_identical_name_is_an_exact_match():
    repo = _world([_store("s1", "פיצה אקסטרים")])
    assert repo.find_deal_shops("פיצה אקסטרים")[0].band == EXACT


def test_the_branch_town_is_not_treated_as_part_of_the_name():
    repo = _world([_store("s1", "גולדה")])
    assert repo.find_deal_shops("גולדה G כפר סבא", "כפר סבא")[0].identity.name == "גולדה"


def test_a_latin_town_is_stripped_too():
    """The feed writes the town in Latin on roughly a third of rows; Hebrew never matches it."""
    repo = _world([_store("s1", "גולדה")])
    assert repo.find_deal_shops("גולדה G כפר סבא", "KFAR SABA")[0].identity.name == "גולדה"


def test_a_mall_in_the_merchant_name_does_not_block_the_match():
    repo = _world([_store("s1", "צומת ספרים")])
    assert repo.find_deal_shops("צומת ספרים עזריאלי")[0].identity.name == "צומת ספרים"


# ── Somewhere merely similar ──────────────────────────────────────────────────


def test_a_shared_trade_word_is_offered_as_somewhere_similar():
    """'קפה ברלין' is not 'קפה קפה', but both sell coffee and one of them has a coupon."""
    repo = _world([_store("s1", "קפה קפה", ["COFFEE_&_SNACKS"])])

    match = repo.find_deal_shops("קפה ברלין", None, "RESTAURANT")[0]

    assert match.identity.name == "קפה קפה"
    assert match.band == SIMILAR
    assert not match.is_confident, "a lookalike must never be reported as the shop itself"


def test_two_shops_naming_different_trades_are_never_the_same_shop():
    """
    Regression: 'קפה רוטשילד' came back as 'פיצה רוטשילד' as though it were the shop itself.

    They share a street name, and each says plainly what it sells — one coffee, the other
    pizza. Worth offering, since both sell food, but not as where the user actually was.
    """
    repo = _world([_store("s1", "פיצה רוטשילד", ["RESTAURANT"])])

    match = repo.find_deal_shops("קהל נכבד - קפה רוטשילד", "ראשון לציון", "RESTAURANT")[0]

    assert match.identity.name == "פיצה רוטשילד"
    assert match.band == SIMILAR
    assert not match.is_confident


def test_a_name_that_is_only_a_trade_word_matches_nothing():
    """Bare 'מסעדה' describes a category, and would otherwise match every restaurant."""
    repo = _world([_store("s1", "מסעדה steakwood")])
    assert repo.find_deal_shops("מסעדה", None, "RESTAURANT") == []


# ── The category safety net ───────────────────────────────────────────────────


def test_a_plainly_different_line_of_business_is_turned_down():
    """A car park is not a clothes shop, however much the one word they share suggests it."""
    repo = _world([_store("s1", "יעקבי", ["CLOTHES_&_ACCESSORIES"])])
    assert repo.find_deal_shops("חניוני יעקבי", None, "TRANSPORT_OTHER") == []


def test_the_category_never_overrules_more_than_one_shared_word():
    """
    Regression: 'זר פור יו אינטרנט' went to 'קאר פור יו'.

    The bank files it under BUSINESS_EXPENSES, which disagrees with the florist's own tags —
    so the right shop was turned down while a car service tagged only 'SHOPPING_OTHER' sailed
    through on a weaker match. Silence must never beat a real category.
    """
    repo = _world([
        _store("s1", "זר פור יו", ["GROCERIES"]),
        _store("s2", "קאר פור יו", ["SHOPPING_OTHER"]),
    ])

    assert repo.find_deal_shops("זר פור יו אינטרנט", None, "BUSINESS_EXPENSES")[0].identity.name == "זר פור יו"


def test_an_uninformative_tag_never_turns_a_shop_down():
    """SHOPPING_OTHER is on half the catalogue; it says nothing about what a shop sells."""
    repo = _world([_store("s1", "גולדה", ["SHOPPING_OTHER"])])
    assert repo.find_deal_shops("גולדה מזרח", None, "RESTAURANT")


def test_neighbouring_categories_are_not_a_disagreement():
    repo = _world([_store("s1", "הבורקס", ["COFFEE_&_SNACKS"])])
    assert repo.find_deal_shops("הבורקס ה- 108", None, "RESTAURANT")


# ── One brand, however many rows the catalogue holds ──────────────────────────


def test_twin_rows_are_folded_together_and_pool_their_deals():
    """'fox' and 'פוקס' are one shop; their deals must not be split across two ids."""
    repo = _world(
        [_store("s1", "פוקס"), _store("s2", "fox")],
        aliases=[_alias("s1", "fox")],
    )

    match = repo.find_deal_shops("פוקס - ב\"ב כ\"ס", "כפר סבא")[0]

    assert match.identity.store_ids == {"s1", "s2"}
    assert len(match.deals) == 2


def test_an_alias_claiming_two_shops_never_fuses_them():
    """'Royal - רויאל' sits on both ROYAL CARE and ROYAL LIGHT — a review slip, not evidence."""
    repo = _world(
        [_store("s1", "ROYAL CARE"), _store("s2", "ROYAL LIGHT"), _store("s3", "רויאל")],
        aliases=[_alias("s1", "רויאל"), _alias("s2", "רויאל")],
    )

    identities = [i for i in repo._identities.values() if len(i.store_ids) > 1]
    assert identities == []


def test_an_alias_reaches_a_shop_filed_under_its_english_name():
    """The feed is Hebrew; 'pizza hut' is not. The alias is the only bridge."""
    repo = _world([_store("s1", "pizza hut")], aliases=[_alias("s1", "פיצה האט")])
    assert repo.find_deal_shops("פיצה האט המושבה הגרמ", "חיפה")[0].identity.store_id == "s1"


# ── What reaches the user ──────────────────────────────────────


def _club_card_tx(tx_id="t1", merchant="סטימצקי", price=80.0, sub="RESTAURANT"):
    """
    A purchase a club's own נטען card paid for, exactly as the feed reports one.

    Settled, and the card was never billed: the merchant recorded the sale, the loaded card
    covered it, and no money left the bank. That is the whole signature — there is no field
    naming the club, which is why nothing downstream may claim to.
    """
    transaction = _tx(tx_id, merchant=merchant, sub=sub)
    transaction.status = "BOOKED"
    transaction.amount = TransactionAmount(
        originalAmount=AmountDetail(amount=-abs(price), currency="ILS"),
        chargedAmount=AmountDetail(amount=None, currency="ILS"),
    )
    return transaction


def _merchants(answer, band):
    """The merchants under one band, or an empty list when the band did not surface."""
    for row in answer.missed.bands:
        if row.band == band:
            return row.merchants
    return []


def _band(answer, band):
    for row in answer.missed.bands:
        if row.band == band:
            return row
    return None


def test_shops_without_a_deal_are_never_offered():
    repo = _world([_store("s1", "סטימצקי")], without_deals={"s1"})
    assert repo.find_deal_shops("סטימצקי כפר סבא") == []


def test_a_shop_outside_the_users_clubs_is_dropped():
    """The deal exists, but a user who is not in the club cannot use it."""
    repo = _world(
        [_store("s1", "סטימצקי")],
        clubs={"c1": _club("c1", ["s1"]), "c2": _club("c2", [])},
    )
    service = _service(repo)

    assert service.savings_opportunities([_tx(merchant="סטימצקי")], user_club_ids=["c1"]).missed.purchase_count == 1
    assert service.savings_opportunities([_tx(merchant="סטימצקי")], user_club_ids=["c2"]).missed.purchase_count == 0


def _distinct_names(count):
    """Names too unalike to fuzzy-match each other, so each shop matches on its own word."""
    letters = "אבגדהוזחטיכלמנסעפצקרשת"
    return ["".join(combo) for combo in list(combinations(letters, 4))[:count]]


def test_every_shop_a_purchase_could_have_been_made_at_is_returned():
    """No trimming to a handful — a shop with a coupon is worth showing."""
    words = _distinct_names(8)
    repo = _world([_store(f"shop{i}", word) for i, word in enumerate(words)])

    shops = repo.find_deal_shops(" ".join(words))

    assert len(shops) == len(words)
    assert all(shop.band == STRONG for shop in shops)


def test_a_band_is_capped_so_one_feed_cannot_return_thousands():
    words = _distinct_names(60)
    repo = _world([_store(f"shop{i}", word) for i, word in enumerate(words)])
    service = _service(repo)

    # 60 purchases at 60 distinct merchants, so the cap bites on merchants rather than shops.
    answer = service.savings_opportunities(
        [_tx(f"t{i}", merchant=word) for i, word in enumerate(words)], user_club_ids=["c1"]
    )

    counted = sum(len(row.merchants) for row in answer.missed.bands)
    assert counted <= SHOP_MATCH.MAX_SHOPS * len(answer.missed.bands)
    for row in answer.missed.bands:
        assert len(row.merchants) <= SHOP_MATCH.MAX_SHOPS


def test_a_capped_band_still_totals_only_what_it_returned():
    """
    A subtotal must never describe rows the client was not given.

    The cap is applied first and the total taken from what survives, so a user adding up the
    merchants on screen lands on the figure above them.
    """
    words = _distinct_names(60)
    repo = _world([_store(f"shop{i}", word) for i, word in enumerate(words)])
    service = _service(repo)

    answer = service.savings_opportunities(
        [_tx(f"t{i}", merchant=word, charged=10.0) for i, word in enumerate(words)],
        user_club_ids=["c1"],
    )

    for row in answer.missed.bands:
        assert row.total_amount == pytest.approx(sum(m.amount for m in row.merchants))
        assert row.purchase_count == sum(m.purchase_count for m in row.merchants)


def test_purchases_without_an_id_are_skipped():
    repo = _world([_store("s1", "סטימצקי")])
    service = _service(repo)

    answer = service.savings_opportunities(
        [_tx(tx_id=None), _tx(tx_id="t3", merchant="סטימצקי")], user_club_ids=["c1"]
    )

    ids = [p.transaction_id for row in answer.missed.bands for m in row.merchants for p in m.purchases]
    assert ids == ["t3"]


def test_falls_back_to_the_original_amount_when_nothing_was_charged():
    service = _service(_world([_store("s1", "סטימצקי")]))
    transaction = _tx(merchant="סטימצקי")
    # How a not-yet-billed row really arrives: the charged node is there with its currency,
    # only the amount is blank. Still PENDING, so the charge is coming — not a club card.
    transaction.amount = TransactionAmount(
        originalAmount=AmountDetail(amount=-42.5, currency="ILS"),
        chargedAmount=AmountDetail(amount=None, currency="ILS"),
    )

    answer = service.savings_opportunities([transaction], user_club_ids=["c1"])
    assert answer.missed.total_amount == 42.5


# ── Gathered by merchant, counted once ────────────────────────────────


def test_every_purchase_at_one_merchant_is_gathered_under_it():
    repo = _world([_store("s1", "קפה קפה", ["COFFEE_&_SNACKS"])])
    service = _service(repo)

    answer = service.savings_opportunities(
        [
            _tx("t1", merchant="קפה קפה", charged=30.0),
            _tx("t2", merchant="קפה קפה", charged=20.0),
            _tx("t3", merchant="סטימצקי", charged=99.0),  # nothing to offer
        ],
        user_club_ids=["c1"],
    )

    merchants = _merchants(answer, EXACT)
    assert len(merchants) == 1
    assert merchants[0].merchant_name == "קפה קפה"
    assert merchants[0].purchase_count == 2
    assert merchants[0].amount == 50.0


def test_a_purchase_matching_several_bands_is_counted_once_under_the_strongest():
    """
    The bug a user hit: one coffee matching the café itself and a lookalike was counted twice.

    Reported per shop it appeared under both; the tabs then added up to more than the headline,
    with nothing on screen to explain the gap. It belongs to its strongest match, and there only.
    """
    repo = _world([_store("s1", "קפה קפה", ["COFFEE_&_SNACKS"]), _store("s2", "קפה ברלין")])
    service = _service(repo)

    answer = service.savings_opportunities(
        [_tx("t1", merchant="קפה קפה", charged=30.0)], user_club_ids=["c1"]
    )

    assert answer.missed.purchase_count == 1
    assert answer.missed.total_amount == 30.0
    assert _band(answer, EXACT).purchase_count == 1
    assert _band(answer, SIMILAR) is None, "the weaker reading must not carry the purchase too"


def test_the_bands_always_add_up_to_the_headline():
    """
    The invariant the whole shape exists for, over a feed built to overlap as much as possible.

    Every purchase names a café and a bookshop, so several match at several strengths at once.
    """
    repo = _world([
        _store("s1", "קפה קפה", ["COFFEE_&_SNACKS"]),
        _store("s2", "קפה ברלין"),
        _store("s3", "סטימצקי", ["BOOKS_&_GAMES"]),
    ])
    service = _service(repo)

    answer = service.savings_opportunities(
        [
            _tx("t1", merchant="קפה קפה", charged=30.0),
            _tx("t2", merchant="קפה ברלין", charged=20.0),
            _tx("t3", merchant="סטימצקי כפר סבא", charged=99.0, sub="BOOKS_&_GAMES"),
        ],
        user_club_ids=["c1"],
    )

    assert answer.missed.total_amount == pytest.approx(sum(b.total_amount for b in answer.missed.bands))
    assert answer.missed.purchase_count == sum(b.purchase_count for b in answer.missed.bands)

    # And no transaction id appears under two bands.
    seen = [p.transaction_id for b in answer.missed.bands for m in b.merchants for p in m.purchases]
    assert len(seen) == len(set(seen))


def test_returns_nothing_without_transactions():
    answer = _service(_world([_store("s1", "סטימצקי")])).savings_opportunities([])
    assert answer.missed.total_amount == 0
    assert answer.applied.total_amount == 0
    assert answer.missed.bands == []


# ── Purchases the club card already paid for ──────────────────────────


def test_a_purchase_on_the_club_card_is_never_a_missed_saving():
    """The whole point: paying with the club's own card is the opposite of missing out."""
    service = _service(_world([_store("s1", "סטימצקי")]))

    answer = service.savings_opportunities(
        [_club_card_tx("t1", merchant="סטימצקי", price=80.0)], user_club_ids=["c1"]
    )

    assert answer.missed.purchase_count == 0
    assert answer.missed.total_amount == 0
    assert answer.applied.purchase_count == 1
    assert answer.applied.total_amount == 80.0
    assert answer.applied.merchants[0].merchant_name == "סטימצקי"


def test_a_club_card_purchase_counts_even_where_the_catalogue_knows_no_shop():
    """
    The card is the evidence, not the match.

    A נטען card only spends at the club's own shops, so a purchase on one took the discount
    whether or not our catalogue happens to carry that shop. Dropping it for want of a match
    would hide a saving the user really made.
    """
    service = _service(_world([_store("s1", "סטימצקי")]))

    answer = service.savings_opportunities(
        [_club_card_tx("t1", merchant="שום חנות שאין לנו", price=55.0)], user_club_ids=["c1"]
    )

    assert answer.applied.purchase_count == 1
    assert answer.applied.total_amount == 55.0


def test_the_same_merchant_on_an_ordinary_card_is_still_missed():
    service = _service(_world([_store("s1", "סטימצקי")]))

    answer = service.savings_opportunities(
        [
            _club_card_tx("t1", merchant="סטימצקי", price=80.0),
            _tx("t2", merchant="סטימצקי", charged=20.0),
        ],
        user_club_ids=["c1"],
    )

    assert answer.applied.total_amount == 80.0
    assert answer.missed.total_amount == 20.0
    assert answer.missed.purchase_count == 1


def test_a_club_card_merchant_never_claims_to_know_which_club_paid():
    """
    The feed says no money left the account. It does not say whose card it was.

    Naming a club here would be a guess dressed as a fact, and the screen would repeat it.
    """
    service = _service(_world([_store("s1", "סטימצקי")]))

    answer = service.savings_opportunities(
        [_club_card_tx("t1", merchant="סטימצקי")], user_club_ids=["c1"]
    )

    assert answer.applied.merchants[0].club_ids == []


def test_a_refund_is_neither_missed_nor_applied():
    """Money coming back is not a purchase, so it never had a deal to miss."""
    service = _service(_world([_store("s1", "סטימצקי")]))
    refund = _tx("t1", merchant="סטימצקי")
    refund.amount = TransactionAmount(
        originalAmount=AmountDetail(amount=-29.21, currency="ILS"),
        chargedAmount=AmountDetail(amount=29.21, currency="ILS"),
    )

    answer = service.savings_opportunities([refund], user_club_ids=["c1"])

    assert answer.missed.purchase_count == 0
    assert answer.applied.purchase_count == 0
