from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from lessley_deals.enrichment.constaints_parser import (
    Combinability,
    DealConstraints,
    Eligibility,
    Limits,
    StoreCoverage,
    _LlmCombinability,
    _LlmDealConstraints,
    _LlmEligibility,
    _LlmLimits,
    _LlmStoreCoverage,
    _to_public,
    build_system_prompt,
    empty_constraints,
    parse_deal_constraints,
    supported_source_prompts,
)

# --------------------------------------------------------------------------- #
# Default template                                                            #
# --------------------------------------------------------------------------- #

def test_empty_constraints_is_all_unknown_and_null() -> None:
    template = empty_constraints()
    assert template == {
        "combinability": {
            "stackable_with_store_sale": True,
            "stackable_with_member_discounts": True,
            "stackable_with_coupons": True,
            "stackable_with_payment_discounts": True,
            "stackable_with_giftcards": True,
            "stackable_with_cashback": True,
        },
        "limits": {
            "max_uses_per_transaction": None,
            "max_uses_per_month": None,
            "minimum_purchase": None,
        },
        "store_coverage": {
            "is_include_outlets_stores": "unknown",
            "is_include_online_stores": "unknown",
            "is_include_physical_stores": "unknown",
        },
        "eligibility": {
            "membership_required": "unknown",
            "payment_method_required": None,
        },
    }


# --------------------------------------------------------------------------- #
# Tri-state booleans                                                          #
# --------------------------------------------------------------------------- #

def test_combinability_defaults_to_true() -> None:
    c = Combinability(stackable_with_coupons=True, stackable_with_giftcards=False)
    assert c.stackable_with_coupons is True
    assert c.stackable_with_giftcards is False
    # Untouched combinability fields default to True (optimistic).
    assert c.stackable_with_store_sale is True


def test_store_coverage_and_eligibility_defaults() -> None:
    assert StoreCoverage().is_include_online_stores == "unknown"
    e = Eligibility()
    assert e.membership_required == "unknown"
    assert e.payment_method_required is None


# --------------------------------------------------------------------------- #
# Positive-integer limits                                                     #
# --------------------------------------------------------------------------- #

def test_limits_accept_positive_integers() -> None:
    limits = Limits(max_uses_per_transaction=2, max_uses_per_month=5, minimum_purchase=200)
    assert limits.max_uses_per_transaction == 2
    assert limits.max_uses_per_month == 5
    assert limits.minimum_purchase == 200


def test_limits_reject_zero_and_negative() -> None:
    limits = Limits(max_uses_per_transaction=0, max_uses_per_month=-3, minimum_purchase=-1)
    assert limits.max_uses_per_transaction is None
    assert limits.max_uses_per_month is None
    assert limits.minimum_purchase is None


def test_limits_none_stays_none() -> None:
    limits = Limits()
    assert limits.max_uses_per_transaction is None
    assert limits.max_uses_per_month is None
    assert limits.minimum_purchase is None


# --------------------------------------------------------------------------- #
# Enum -> boolean conversion                                                  #
# --------------------------------------------------------------------------- #

def _llm_constraints(**overrides: object) -> _LlmDealConstraints:
    base = _LlmDealConstraints(
        combinability=_LlmCombinability(
            stackable_with_store_sale="yes",
            stackable_with_member_discounts="yes",
            stackable_with_coupons="no",
            stackable_with_payment_discounts="unknown",
            stackable_with_giftcards="no",
            stackable_with_cashback="unknown",
        ),
        limits=_LlmLimits(
            max_uses_per_transaction=2,
            max_uses_per_month=None,
            minimum_purchase=0,  # invalid -> should collapse to None
        ),
        store_coverage=_LlmStoreCoverage(
            is_include_outlets_stores="no",
            is_include_online_stores="no",
            is_include_physical_stores="yes",
        ),
        eligibility=_LlmEligibility(
            membership_required="yes",
            payment_method_required="HOT club-linked credit card",
        ),
    )
    return base.model_copy(update=overrides)


def test_to_public_maps_enums_to_booleans() -> None:
    public = _to_public(_llm_constraints())
    assert isinstance(public, DealConstraints)

    comb = public.combinability
    assert comb.stackable_with_store_sale is True
    assert comb.stackable_with_member_discounts is True
    assert comb.stackable_with_coupons is False
    # "unknown" from the LLM maps to True (optimistic combinability default).
    assert comb.stackable_with_payment_discounts is True
    assert comb.stackable_with_giftcards is False
    assert comb.stackable_with_cashback is True

    # 0 from the LLM is not a valid positive limit -> None.
    assert public.limits.minimum_purchase is None
    assert public.limits.max_uses_per_transaction == 2

    assert public.store_coverage.is_include_online_stores is False
    assert public.store_coverage.is_include_physical_stores is True
    assert public.store_coverage.is_include_outlets_stores is False

    assert public.eligibility.membership_required is True
    assert public.eligibility.payment_method_required == "HOT club-linked credit card"


# --------------------------------------------------------------------------- #
# Per-source prompt assembly                                                  #
# --------------------------------------------------------------------------- #

def test_generic_prompt_carries_schema_and_output_discipline() -> None:
    prompt = build_system_prompt()
    assert "stackable_with_store_sale" in prompt
    assert "Return ONLY the JSON object" in prompt
    assert "SOURCE-SPECIFIC RULES" not in prompt


def test_unknown_source_falls_back_to_the_generic_prompt() -> None:
    assert build_system_prompt("no_such_source") == build_system_prompt()
    assert build_system_prompt("") == build_system_prompt(None)


def test_behatsdaa_block_is_inserted_before_the_final_reminder() -> None:
    prompt = build_system_prompt("behatsdaa")
    assert "SOURCE-SPECIFIC RULES — Behatsdaa" in prompt
    # Output discipline must stay the last thing the model reads.
    assert prompt.index("SOURCE-SPECIFIC RULES") < prompt.index("Return ONLY the JSON object")
    # And the shared schema must still be there.
    assert "is_include_outlets_stores" in prompt


def test_behatsdaa_block_pins_the_rules_this_source_gets_wrong_by_default() -> None:
    prompt = build_system_prompt("behatsdaa")
    # A shekel ceiling has no field in the schema — the most likely failure is
    # it leaking into max_uses_per_transaction or minimum_purchase.
    assert "סכום מקסימלי למימוש בעסקה" in prompt
    assert "never max_uses_per_transaction" in prompt
    # The wallet's monthly load cap is not a monthly usage count.
    assert "ניתן לטעון עד 1000 ₪ לחודש" in prompt
    # Outlet branches are in scope when only the assortment is narrowed.
    assert "בסניפי עודפים ניתן לממש על קולקציה חדשה בלבד" in prompt
    # Delivery/take-away must not be read as the retailer's web shop.
    assert "not \"online stores\"" in prompt


def test_behatsdaa_is_a_supported_source() -> None:
    assert "behatsdaa" in supported_source_prompts()


# --------------------------------------------------------------------------- #
# Per-source blocks — each pins the mapping that source gets wrong by default  #
# --------------------------------------------------------------------------- #

_BLOCKED_SOURCES = (
    "behatsdaa",
    "hot",
    "hever_gift_card_company",
    "hever_teamim_card_store",
    "paisplus",
    # The cash-card programs are one source per membership tier; both tiers of
    # a program share its block, since only the bracket numbers differ.
    "paisplus_networks_regular",
    "paisplus_networks_vip",
    "paisplus_food_chains_regular",
    "paisplus_food_chains_vip",
    "mastercard",
    "topcash",
)


def test_every_scraped_source_has_its_own_terminology_block() -> None:
    assert set(supported_source_prompts()) == set(_BLOCKED_SOURCES)


def test_every_block_keeps_the_schema_and_output_discipline_intact() -> None:
    for source in _BLOCKED_SOURCES:
        prompt = build_system_prompt(source)
        assert "SOURCE-SPECIFIC RULES" in prompt, source
        assert "is_include_outlets_stores" in prompt, source
        # Output discipline must stay the last thing the model reads.
        assert prompt.index("SOURCE-SPECIFIC RULES") < prompt.index(
            "Return ONLY the JSON object"
        ), source


def test_hot_block_pins_per_member_caps_apart_from_per_transaction() -> None:
    prompt = build_system_prompt("hot")
    # HOT's signature number caps vouchers per PERSON, which has no field. The
    # likely failure is it landing in max_uses_per_transaction.
    assert "מוגבל לתו 1 לעמית מועדון (ת.ז.)" in prompt
    # ...but the same cap WITH a monthly window is a real max_uses_per_month.
    assert "מוגבל ל-2 קופונים לעמית בחודש" in prompt
    assert "max_uses_per_month: 2" in prompt
    assert "Decide by the TIME WINDOW" in prompt
    # The statement-credit boilerplate prohibits nothing — it must stay unknown.
    assert "It prohibits NOTHING" in prompt
    # Buying the voucher on the club site is not the merchant's web shop.
    assert "where the voucher is BOUGHT" in prompt


def test_hever_blocks_pin_the_tiered_load_sentence_as_economics() -> None:
    for source in ("hever_gift_card_company", "hever_teamim_card_store"):
        prompt = build_system_prompt(source)
        assert "ECONOMICS, not a restriction" in prompt, source
        # The load tiers must not become minimum_purchase.
        assert "never produces minimum_purchase" in prompt, source
        # A shekel spend ceiling is not a limit.
        assert "עד 1,000 ש\"ח לעסקה" in prompt, source
    # Only the restaurant card claims physical stores from a dine-in phrase.
    assert "ישיבה במסעדה" in build_system_prompt("hever_teamim_card_store")


def test_paisplus_block_separates_voucher_counts_from_shekel_ceilings() -> None:
    prompt = build_system_prompt("paisplus")
    # A genuine count DOES map here — unlike the loadable sources.
    assert "ניתן לממש עד 2 תווי קנייה בעסקה אחת" in prompt
    assert "max_uses_per_transaction: 2" in prompt
    # ...but a shekel ceiling still does not.
    assert "ניתן לממש את תווי הקנייה בסכום של עד 2000 ₪ לעסקה" in prompt
    # The source ships this typo; the model must read it as normal stacking.
    assert "כולל כפלמבצעים" in prompt


@pytest.mark.parametrize("source_id", ["paisplus_networks_regular", "paisplus_networks_vip"])
def test_paisplus_networks_block_inverts_the_default_store_coverage(source_id: str) -> None:
    prompt = build_system_prompt(source_id)
    # This source excludes branches — the opposite of the branch-based sources.
    assert "ניתן למימוש באתר בלבד" in prompt
    assert "is_include_physical_stores: no" in prompt
    # The balance-vs-basket instruction is not a spend floor.
    assert "NOT minimum_purchase" in prompt


@pytest.mark.parametrize("source_id", ["paisplus_food_chains_regular", "paisplus_food_chains_vip"])
def test_paisplus_food_block_keeps_self_checkout_out_of_store_coverage(source_id: str) -> None:
    prompt = build_system_prompt(source_id)
    assert "לא ניתן לשלם בקופות עצמיות" in prompt
    assert "self-checkout is a register type" in prompt
    assert "Do NOT set is_include_physical_stores to \"no\" for it" in prompt


def test_mastercard_block_pins_day_of_month_apart_from_monthly_limit() -> None:
    prompt = build_system_prompt("mastercard")
    # "ב-10 בחודש" is a date, and the obvious failure is max_uses_per_month: 10.
    assert "תקף ב-10 וב-11 בחודש בלבד" in prompt
    assert "max_uses_per_month stays **null**" in prompt
    # A payment network is not a club — membership must not be inferred.
    assert "not a members' club" in prompt


def test_topcash_block_pins_store_coverage_to_online_only() -> None:
    prompt = build_system_prompt("topcash")
    # Cashback is only ever earned on a tracked click into the merchant's web
    # shop, so all three coverage fields are a constant -- never read from the
    # terms, never "unknown".
    assert "TopCash is ONLINE-ONLY" in prompt
    assert '"is_include_outlets_stores": "no"' in prompt
    assert '"is_include_online_stores": "yes"' in prompt
    assert '"is_include_physical_stores": "no"' in prompt
    assert "These three values are CONSTANT" in prompt
    assert 'Never emit "unknown" for' in prompt
    # Brand copy naming branches is the known failure mode -- it must not flip
    # is_include_physical_stores.
    assert "40 סניפים" in prompt


def test_topcash_block_claims_membership_and_maps_cashback_blockers() -> None:
    prompt = build_system_prompt("topcash")
    # An account and a TopCash click-through are always required.
    assert "membership_required: **yes**" in prompt
    # Payout waiting periods must not become numbers.
    assert "These are days, not limits" in prompt
    # Exclusions that DO line up with a field.
    assert "stackable_with_giftcards: no" in prompt


# --------------------------------------------------------------------------- #
# End-to-end (LLM mocked)                                                     #
# --------------------------------------------------------------------------- #

def test_parse_deal_constraints_sends_the_sources_prompt() -> None:
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(parsed=_llm_constraints()))]
    client = MagicMock()
    client.beta.chat.completions.parse.return_value = completion

    with patch(
        "lessley_deals.enrichment.constaints_parser._get_client",
        return_value=(client, "test-model"),
    ):
        parse_deal_constraints("תנאים", "behatsdaa")

    _, kwargs = client.beta.chat.completions.parse.call_args
    system, user = kwargs["messages"]
    assert "SOURCE-SPECIFIC RULES — Behatsdaa" in system["content"]
    assert user["content"] == "תנאים"

def test_parse_deal_constraints_uses_deterministic_params_and_converts() -> None:
    fake_parsed = _llm_constraints()
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(parsed=fake_parsed))]
    client = MagicMock()
    client.beta.chat.completions.parse.return_value = completion

    with patch(
        "lessley_deals.enrichment.constaints_parser._get_client",
        return_value=(client, "test-model"),
    ):
        result = parse_deal_constraints("כולל כפל מבצעים והנחות. ניתן לממש עד 2 שוברים בעסקה.")

    assert isinstance(result, DealConstraints)
    assert result.combinability.stackable_with_store_sale is True
    assert result.limits.max_uses_per_transaction == 2

    _, kwargs = client.beta.chat.completions.parse.call_args
    assert kwargs["temperature"] == 0.0
    assert kwargs["seed"] == 42
    assert kwargs["response_format"] is _LlmDealConstraints


def test_parse_deal_constraints_raises_when_llm_returns_none() -> None:
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(parsed=None))]
    client = MagicMock()
    client.beta.chat.completions.parse.return_value = completion

    with patch(
        "lessley_deals.enrichment.constaints_parser._get_client",
        return_value=(client, "test-model"),
    ):
        try:
            parse_deal_constraints("terms")
        except RuntimeError:
            return
    raise AssertionError("expected RuntimeError when LLM returns no parsed output")
