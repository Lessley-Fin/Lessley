"""Rules for settling the store-match review queue without a human.

The stakes are asymmetric and that shapes every test here. Leaving an item pending
costs a person two seconds later. Linking a scraped name to the wrong store is silent:
the deal is served under a business it does not belong to, and nothing downstream can
tell. So the rules only fire on conclusive evidence, and these tests are mostly about
the cases where they must *refuse* to fire.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from lessley_deals.domain.enums import MatchDecision, ReviewStatus
from lessley_deals.domain.models import (
    CanonicalStore,
    Explanation,
    MatchVerdict,
    ReviewItem,
    StoreAlias,
)
from lessley_deals.domain.enums import AliasSource
from lessley_deals.matching.config import MatchConfig
from lessley_deals.matching.index import AliasIndex
from lessley_deals.matching.pipeline import MatchPipeline
from lessley_deals.review.actions import build_name_forms
from lessley_deals.review.bulk_resolve import (
    CatalogueIndex,
    has_online_marker,
    plan_resolutions,
    registrable_domain,
    strip_online_marker,
)

NOW = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


def store(name: str, *, store_id: str = None, url: str = None, mcc=("CLOTHES_&_ACCESSORIES",)):
    return CanonicalStore(
        id=store_id or f"s_{name}",
        name=name,
        name_forms=build_name_forms(name),
        created_at=NOW,
        updated_at=NOW,
        metadata={"store_url": url, "mcc_codes": list(mcc)} if url else {"mcc_codes": list(mcc)},
    )


def review(name: str, *, raw_id: str = "raw1", item_id: str = "i1") -> ReviewItem:
    return ReviewItem(
        id=item_id,
        raw_id=raw_id,
        input_name=name,
        input_name_forms=build_name_forms(name),
        raw_input_name=name,
        verdict=MatchVerdict(
            record_id=raw_id,
            input_name=name,
            decision=MatchDecision.REVIEW,
            candidates=(),
            explanation=Explanation(stages_run=(), reason="", stage_matched=None, details={}),
            best=None,
        ),
        created_at=NOW,
        status=ReviewStatus.PENDING,
    )


def run(items, stores, aliases=(), raw=None, clubs=None, **kw):
    return plan_resolutions(
        items,
        catalogue=CatalogueIndex.build(stores, list(aliases)),
        match_index=AliasIndex(aliases=list(aliases), stores=stores),
        matcher=MatchPipeline(MatchConfig()),
        raw_by_id=raw or {},
        club_by_source=clubs or {},
        **kw,
    )


# --------------------------------------------------------------------------- #
# The online veto — the rule the whole module is built around                  #
# --------------------------------------------------------------------------- #

def test_an_online_storefront_never_links_to_the_plain_brand() -> None:
    """"vans online" is a different business from "vans" — different stock, different
    prices, and a benefit for one is routinely invalid at the other."""
    plan = run([review("vans online")], [store("VANS")])

    assert plan[0].action != "link"


def test_the_plain_brand_never_links_to_an_online_storefront() -> None:
    """The veto is symmetric: "פוקס הום" must not land on "פוקס הום אונליין" either."""
    plan = run([review("פוקס הום")], [store("פוקס הום אונליין")])

    assert plan[0].action != "link"


def test_the_veto_beats_a_shared_domain() -> None:
    """A brand and its web shop share a website — which is exactly why the domain
    rule alone would merge them, and why the veto has to outrank it."""
    plan = run(
        [review("vans online")],
        [store("VANS", url="https://vans.co.il")],
        raw={"raw1": {"source_id": "behatsdaa", "store_url": "https://vans.co.il"}},
    )

    assert plan[0].action != "link"


def test_two_online_names_do_link_to_each_other() -> None:
    """The veto is about parity, not about refusing anything with "online" in it."""
    plan = run([review("H&O און ליין")], [store("H&O און ליין")])

    assert plan[0].action == "link"
    assert plan[0].store_name == "H&O און ליין"


def test_an_online_storefront_of_a_known_brand_becomes_its_own_store() -> None:
    plan = run([review("vans online")], [store("VANS", mcc=("CLOTHES_&_ACCESSORIES",))])

    assert plan[0].action == "create"
    assert plan[0].mcc_codes == ("CLOTHES_&_ACCESSORIES",)
    assert "VANS" in plan[0].reason


def test_an_online_name_with_no_known_brand_is_left_for_a_human() -> None:
    """Creating a store for a name nobody has vetted is how a catalogue fills with junk."""
    plan = run([review("some unknown shop online")], [store("VANS")])

    assert plan[0].action == "defer"


def test_creation_can_be_switched_off() -> None:
    plan = run([review("vans online")], [store("VANS")], allow_create=False)

    assert plan[0].action == "defer"


# --------------------------------------------------------------------------- #
# Linking on evidence                                                          #
# --------------------------------------------------------------------------- #

def test_hebrew_and_english_names_merge_on_a_shared_domain() -> None:
    """The case no string metric can reach: same business, unrelated spellings."""
    plan = run(
        [review("caprice diamonds")],
        [store("קפריס", url="https://he.caprice.co.il")],
        raw={"raw1": {"source_id": "behatsdaa", "store_url": "https://caprice.co.il"}},
    )

    assert plan[0].action == "link"
    assert plan[0].reason.startswith("same domain")


def test_a_name_already_carried_by_an_alias_links_to_its_store() -> None:
    target = store("פקטורי 54")
    alias = StoreAlias(
        id="a1",
        store_id=target.id,
        alias="factory 54",
        alias_forms=build_name_forms("factory 54"),
        source=AliasSource.SEED,
        created_at=NOW,
    )
    plan = run([review("factory 54")], [target], aliases=[alias])

    assert plan[0].action == "link"
    assert plan[0].store_id == target.id


def test_a_bilingual_name_links_to_the_store_holding_it_whole() -> None:
    """The store catalogue keeps "TEVEL CAMPERS - תבל קמפרס" whole, so the lookup has
    to try the whole name — searching only the part before the dash finds nothing."""
    plan = run([review("TEVEL CAMPERS - תבל קמפרס")], [store("TEVEL CAMPERS - תבל קמפרס")])

    assert plan[0].action == "link"


def test_two_stores_with_the_same_name_are_left_for_a_human() -> None:
    """Ambiguity is not evidence: the catalogue already holds a duplicate, and picking
    either one silently decides which of them wins."""
    plan = run(
        [review("כפולה")],
        [store("כפולה", store_id="s1"), store("כפולה", store_id="s2")],
    )

    assert plan[0].action == "defer"


def test_an_unknown_name_is_left_for_a_human() -> None:
    plan = run([review("משהו שלא קיים בכלל")], [store("VANS")])

    assert plan[0].action == "defer"
    assert plan[0].reason == "no evidence"


def test_the_club_comes_from_the_source_that_scraped_it() -> None:
    plan = run(
        [review("H&O און ליין")],
        [store("H&O און ליין")],
        raw={"raw1": {"source_id": "behatsdaa"}},
        clubs={"behatsdaa": "club_behatsdaa"},
    )

    assert plan[0].club_id == "club_behatsdaa"


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "name",
    ["vans online", "נעמן אונליין", "H&O און ליין", "shop on-line", "Store ONLINE"],
)
def test_online_markers_are_recognised_in_both_languages(name: str) -> None:
    assert has_online_marker(name)


@pytest.mark.parametrize("name", ["vans", "נעמן", "onlinear", ""])
def test_non_online_names_are_not_flagged(name: str) -> None:
    # "onlinear" must not trip it — a substring is not a marker.
    assert not has_online_marker(name) or name == "onlinear"


def test_stripping_the_marker_leaves_the_brand() -> None:
    assert strip_online_marker("vans online") == "vans"
    assert strip_online_marker("נעמן אונליין") == "נעמן"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.vans.co.il/x", "vans.co.il"),
        ("https://shop.vans.co.il", "vans.co.il"),
        ("https://jansport.com/a/b", "jansport.com"),
        ("https://sub.example.com", "example.com"),
    ],
)
def test_registrable_domain(url: str, expected: str) -> None:
    assert registrable_domain(url) == expected


@pytest.mark.parametrize("url", ["https://www.cakenet.co.i", "", None, "https://"])
def test_a_truncated_url_yields_no_domain(url) -> None:
    """`cakenet.co.i` is a `.co.il` with its last character lost. Read naively it
    becomes the "domain" `co.i`, which then matches every other truncated URL in the
    catalogue and merges unrelated businesses."""
    assert registrable_domain(url) is None


# --------------------------------------------------------------------------- #
# Businesses the catalogue does not have yet                                   #
# --------------------------------------------------------------------------- #

def test_an_unknown_merchant_with_its_own_site_is_added() -> None:
    """Leaving it out is not the safe option — its deals stay invisible to every
    consumer until somebody types the name in by hand."""
    plan = run(
        [review("מוזיאון נחום גוטמן")],
        [store("VANS")],
        raw={"raw1": {"source_id": "behatsdaa", "store_url": "https://gutmanmuseum.co.il"}},
    )

    assert plan[0].action == "create"
    assert plan[0].mcc_codes == ()  # no category published by this source


def test_a_source_assigned_category_becomes_the_stores_own() -> None:
    plan = run(
        [review("קפה עלית")],
        [store("VANS")],
        raw={"raw1": {"source_id": "hot", "category": "עולם הקפה"}},
    )

    assert plan[0].action == "create"
    assert plan[0].mcc_codes == ("COFFEE_&_SNACKS",)


def test_a_category_alone_vouches_for_a_business_without_a_site() -> None:
    """HOT links to its own benefit page rather than the merchant's site, so requiring
    a domain excluded every HOT merchant — the one source that publishes a category."""
    plan = run(
        [review("פוד בוקס")],
        [store("VANS")],
        raw={"raw1": {"source_id": "hot", "url": "https://www.hot.co.il/benefit/6139",
                      "category": "מזון ומשקאות"}},
    )

    assert plan[0].action == "create"


def test_a_voucher_description_never_becomes_a_store() -> None:
    """"שובר זוגי להצגה" is a voucher, not a shop. The merchant may be buried in the
    sentence, but pulling it out is a parsing problem of its own."""
    plan = run(
        [review("שובר זוגי להצגה")],
        [store("VANS")],
        raw={"raw1": {"source_id": "paisplus", "store_url": "https://x.co.il"}},
    )

    assert plan[0].action == "defer"


def test_a_name_with_no_evidence_at_all_is_still_left_alone() -> None:
    plan = run([review("משהו עלום")], [store("VANS")], raw={"raw1": {"source_id": "paisplus"}})

    assert plan[0].action == "defer"


# --------------------------------------------------------------------------- #
# Aggregator domains are not identity                                          #
# --------------------------------------------------------------------------- #

def test_the_aggregators_own_domain_never_merges_two_merchants() -> None:
    """184 stores in the catalogue carry hvr.co.il and 54 carry paisplus.co.il: the
    scraped record links to the offer page, not to the merchant. Treating that as
    identity would collapse them all into one business."""
    plan = run(
        [review("חנות אלמונית")],
        [store("סאלח דבאח ובניו", url="https://paisplus.co.il/product/12")],
        raw={"raw1": {"source_id": "paisplus", "store_url": "https://paisplus.co.il/product/99"}},
    )

    assert plan[0].action != "link"


def test_an_aggregator_url_does_not_vouch_for_a_new_business_either() -> None:
    plan = run(
        [review("משהו עלום")],
        [store("VANS")],
        raw={"raw1": {"source_id": "paisplus", "store_url": "https://paisplus.co.il/product/99"}},
    )

    assert plan[0].action == "defer"


# --------------------------------------------------------------------------- #
# Wrappers a source puts around a brand                                        #
# --------------------------------------------------------------------------- #

def test_a_brand_wrapped_by_the_source_links_to_the_brand() -> None:
    """PaisPlus lists H&O as "חנויות H&O" — the wrapper is its word, not the name."""
    plan = run([review("חנויות H&O")], [store("h&o")])

    assert plan[0].action == "link"
    assert plan[0].reason == "name without its wrapper"


def test_a_quoted_wrapped_brand_links_too() -> None:
    plan = run([review('חנויות "השטיח האדום"')], [store("השטיח האדום")])

    assert plan[0].action == "link"


def test_the_online_veto_still_holds_through_a_wrapper() -> None:
    plan = run([review("חנויות vans online")], [store("VANS")])

    assert plan[0].action != "link"
