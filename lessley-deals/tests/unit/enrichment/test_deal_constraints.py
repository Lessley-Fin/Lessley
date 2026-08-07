from __future__ import annotations

from unittest.mock import MagicMock, patch

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
