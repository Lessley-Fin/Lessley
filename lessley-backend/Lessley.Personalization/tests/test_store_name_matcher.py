"""
Matching a card-feed merchant name to a shop.

Every case here is a real merchant name from production transaction data, paired with the
shop it should or should not resolve to. The ones marked as regressions are names the old
`token_set_ratio` matcher got wrong with full confidence.
"""

from types import SimpleNamespace

import pytest

from services.utils.store_index import StoreIndex
from services.utils.store_name_matcher import (
    AMBIGUOUS,
    EXACT,
    MATCHED,
    NO_MATCH,
    QUERY_NOT_EXPLAINED,
    STORE_NOT_EXPLAINED,
    match_store,
)
from services.utils.store_text import normalize, script_groups, strip_town, tokenize


def _store(store_id: str, name: str, official_name: str | None = None):
    return SimpleNamespace(
        store_id=store_id,
        name=name,
        metadata=SimpleNamespace(official_name=official_name, mcc_codes=[], image_urls=[], store_url=None),
    )


# A stand-in store list.
#
# The filler is not padding. Rarity is the entire basis of matching, so a trade word has
# to be as common *in proportion* here as it is in the real list — 'סופר' appears in 29 of
# 7,646 real shops, and repeating it 12 times in a list of 200 would make it seventeen
# times commoner than it really is, which quietly changes every verdict below.
# These counts put each word within ~0.02 of its real rarity.
STORE_COUNT = 200
COMMON_WORD_COUNTS = {
    "קפה": 15, "פיצה": 9, "מסעדה": 5, "עיצוב": 8,
    "שיער": 11, "סופר": 6, "פארמ": 5, "מרקט": 6,
}


def _build_index(*stores):
    filler = []
    counter = 0
    for word, appearances in COMMON_WORD_COUNTS.items():
        for _ in range(appearances):
            counter += 1
            filler.append(_store(f"filler-{counter}", f"{word} יחיד{counter}"))
    while len(filler) + len(stores) < STORE_COUNT:
        counter += 1
        filler.append(_store(f"filler-{counter}", f"חנות{counter} יחידה{counter}"))
    return StoreIndex(list(stores) + filler)


# ── The rules, one at a time ──────────────────────────────────────────────────


def test_store_coverage_rejects_when_the_shops_own_brand_word_is_missing():
    """
    Regression: 'נאור סקה עיצוב שיער' used to come back as 'דן עיצוב שיער' at 87/100.

    The two names share only 'עיצוב שיער' — a trade, not a name — while 'דן', the word
    that actually names the shop, is nowhere in the merchant string.
    """
    dan = _store("dan", "דן עיצוב שיער")
    index = _build_index(dan)

    result = match_store("נאור סקה עיצוב שיער", None, index)

    assert result.status == NO_MATCH
    assert result.store is None
    assert result.rejected_by in (STORE_NOT_EXPLAINED, QUERY_NOT_EXPLAINED)


def test_query_coverage_rejects_even_when_the_shop_name_is_fully_covered():
    """
    Regression: 'קפה ברלין' used to come back as 'קפה קפה' at 100/100.

    This one matters because the shop's side looks perfect — every word of 'קפה קפה' is
    present. It is the merchant's side that gives it away: 'ברלין' is what names this
    business and the shop cannot account for it at all.
    """
    cafe_cafe = _store("cafecafe", "קפה קפה")
    # 'ברלין' has to be a word the store list knows, as it is in production — otherwise a
    # different rule turns this down and the test stops testing what it claims to.
    berlin_hotel = _store("berlin", "מלון ברלין")
    index = _build_index(cafe_cafe, berlin_hotel)

    result = match_store("קפה ברלין", None, index)

    assert result.status == NO_MATCH
    assert result.rejected_by == QUERY_NOT_EXPLAINED


def test_a_branch_town_does_not_let_one_shop_answer_for_another():
    """'יקבי קיסריה' and 'יקבי בנימינה' are different wineries that share a trade word."""
    binyamina = _store("binyamina", "יקבי בנימינה")
    index = _build_index(binyamina)

    result = match_store("יקבי קיסריה", None, index)

    assert result.status == NO_MATCH


def test_each_word_answers_for_only_one_other():
    """
    Without one-to-one pairing the single merchant word 'פארמ' answers for *both* words of
    'פארמר פארם', which then outscores the shop actually being described.
    """
    super_pharm = _store("superpharm", "סופר פארמ")
    farmer_pharm = _store("farmer", "פארמר פארמ")
    index = _build_index(super_pharm, farmer_pharm)

    result = match_store("סופר פארם קניון ערים", None, index)

    assert result.status == MATCHED
    assert result.store.store_id == "superpharm"


def test_two_equally_good_shops_produce_no_answer():
    """When a name genuinely fits two shops, naming one of them is a coin toss."""
    index = _build_index(_store("safari-a", "ספארי"), _store("safari-b", "ספארי"))

    result = match_store("ספארי רמת גן", "רמת גן", index)

    assert result.status == NO_MATCH
    assert result.rejected_by == AMBIGUOUS


# ── The town signal ───────────────────────────────────────────────────────────


def test_the_transactions_own_town_is_not_treated_as_part_of_the_name():
    steimatzky = _store("steimatzky", "סטימצקי")
    index = _build_index(steimatzky)

    result = match_store("סטימצקי G כפר סבא", "כפר סבא", index)

    assert result.status == MATCHED
    assert result.store.store_id == "steimatzky"


def test_a_town_truncated_by_the_feed_is_still_recognised():
    """Feeds cut off around 20 characters, leaving 'הוד השרון' as a bare 'הו'."""
    super_pharm = _store("superpharm", "סופר פארמ")
    index = _build_index(super_pharm)

    result = match_store("סופר פארם הנשיאים הו", "הוד השרון", index)

    assert result.status == MATCHED
    assert result.store.store_id == "superpharm"


def test_a_shop_may_still_carry_the_town_in_its_own_name():
    """
    The town is dropped from what the merchant is *called*, not from the words available
    for matching — otherwise a shop named after its town can no longer match on it.
    """
    lagoon = _store("lagoon", "VERT לגון נתניה")
    index = _build_index(lagoon)

    result = match_store("לגון נתניה", "נתניה", index)

    assert result.status == MATCHED
    assert result.store.store_id == "lagoon"


# ── Name forms ────────────────────────────────────────────────────────────────


def test_a_shop_written_in_two_scripts_matches_on_either():
    golda = _store("golda", "גולדה - Golda")
    index = _build_index(golda)

    assert match_store("גולדה מזרח", "ראשון לציון", index).store.store_id == "golda"


def test_the_english_official_name_is_matched_too():
    herbology = _store("herbology", 'עיל"מ', official_name="Herbology")
    index = _build_index(herbology)

    assert match_store("HERBOLOGY", None, index).store.store_id == "herbology"


def test_an_exact_name_is_taken_at_face_value():
    index = _build_index(_store("wolt", "Wolt"))

    result = match_store("WOLT", None, index)

    assert result.status == EXACT
    assert result.store.store_id == "wolt"


def test_a_shop_of_two_ordinary_words_still_matches_as_a_whole():
    """
    Neither 'סופר' nor 'פארם' identifies anything alone, so the usual "share a rare word"
    test would throw this away. The brand is in having both.
    """
    index = _build_index(_store("superpharm", "סופר פארמ"))

    assert match_store("סופר פארם פקר", None, index).store.store_id == "superpharm"


def test_a_merchant_we_have_no_shop_for_matches_nothing():
    index = _build_index(_store("steimatzky", "סטימצקי"))

    assert match_store("שופרסל דיל", "כפר סבא", index).status == NO_MATCH


@pytest.mark.parametrize("merchant_name", [None, "", "   ", "-"])
def test_empty_and_junk_names_are_handled(merchant_name):
    index = _build_index(_store("steimatzky", "סטימצקי"))

    assert match_store(merchant_name, None, index).status == NO_MATCH


# ── Text handling ─────────────────────────────────────────────────────────────


def test_a_geresh_keeps_its_word_in_one_piece():
    """Splitting on the apostrophe turns ג'ירף into two unusable scraps."""
    assert normalize("ג'ירף") == "גירפ"
    assert tokenize(normalize("ג'ירף")) == ["גירפ"]


def test_final_letters_are_folded_so_either_spelling_matches():
    assert normalize("סופר פארם") == normalize("סופר פארמ")


def test_branch_and_terminal_numbers_are_dropped_but_real_ones_kept():
    assert "123" not in normalize("STARBUCKS #123")
    assert "7" in normalize("7-Eleven")


def test_a_name_written_in_two_scripts_splits_into_two():
    assert script_groups(["גולדה", "golda"]) == [["גולדה"], ["golda"]]


def test_a_name_made_only_of_its_town_is_left_alone():
    """Stripping everything would lose the transaction; better to keep what we have."""
    assert strip_town(["נתניה"], "נתניה") == ["נתניה"]
