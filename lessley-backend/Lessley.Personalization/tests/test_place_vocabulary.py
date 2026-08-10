"""
Learning which words name a place rather than a shop.

The distinction cannot be read off the store list — 'עזריאלי' and 'קסטרו' each appear in a
couple of shop names and look alike from there. It shows up in how the words *behave*
across merchant names: a mall attaches itself to many unrelated shops, a brand does not.
"""

from types import SimpleNamespace

from services.utils.place_vocabulary import PlaceVocabulary
from services.utils.store_index import StoreIndex


def _store(store_id: str, name: str):
    return SimpleNamespace(
        store_id=store_id,
        name=name,
        metadata=SimpleNamespace(official_name=None, mcc_codes=[], image_urls=[], store_url=None),
    )


def _index():
    stores = [_store("castro", "קסטרו"), _store("golf", "גולף"), _store("lalin", "ללין")]
    stores += [_store(f"f{n}", f"חנות{n} יחידה{n}") for n in range(200)]
    return StoreIndex(stores)


def test_a_word_attached_to_many_unrelated_shops_is_a_place():
    merchant_names = [
        "קסטרו קניון ערים",
        "גולף קניון ערים",
        "ללין קניון ערים",
    ]

    vocabulary = PlaceVocabulary.learn_from_merchant_names(merchant_names, _index())

    assert "קניונ" in vocabulary
    assert "ערימ" in vocabulary


def test_a_brand_is_never_mistaken_for_a_place_however_often_it_is_visited():
    """
    The same shop visited over and over is one piece of evidence, not many. Counting
    transactions instead of distinct names would turn a user's regular haunt into a
    "place" and quietly stop it ever matching again.
    """
    merchant_names = ["קסטרו כפר סבא"] * 20

    vocabulary = PlaceVocabulary.learn_from_merchant_names(merchant_names, _index())

    assert "קסטרו" not in vocabulary


def test_a_word_common_in_the_store_list_is_left_alone():
    """A word that lots of *shops* are called is the store list's business, not a place."""
    stores = [_store(f"cafe{n}", f"קפה מקום{n}") for n in range(30)]
    stores += [_store(f"f{n}", f"חנות{n} יחידה{n}") for n in range(100)]
    index = StoreIndex(stores)

    vocabulary = PlaceVocabulary.learn_from_merchant_names(
        ["קפה אלף", "קפה בית", "קפה גימל", "קפה דלת"], index
    )

    assert "קפה" not in vocabulary


def test_an_untaught_vocabulary_changes_nothing():
    vocabulary = PlaceVocabulary()

    assert len(vocabulary) == 0
    assert vocabulary.strip(["קסטרו", "קניונ"]) == ["קסטרו", "קניונ"]


def test_a_name_made_only_of_place_words_is_left_alone():
    """Stripping everything would lose the transaction; better to keep what we have."""
    vocabulary = PlaceVocabulary({"קניונ", "ערימ"})

    assert vocabulary.strip(["קניונ", "ערימ"]) == ["קניונ", "ערימ"]
    assert vocabulary.strip(["קסטרו", "קניונ"]) == ["קסטרו"]
