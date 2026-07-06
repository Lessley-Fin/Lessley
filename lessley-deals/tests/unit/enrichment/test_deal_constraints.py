from __future__ import annotations

from unittest.mock import MagicMock, patch

from lessley_deals.enrichment.constaints_parser import (
    Combinability,
    DealConstraints,
    Eligibility,
    Limits,
    RedemptionChannels,
    _LlmCombinability,
    _LlmDealConstraints,
    _LlmEligibility,
    _LlmLimits,
    _LlmRedemptionChannels,
    _to_public,
    empty_constraints,
    parse_deal_constraints,
)

# --------------------------------------------------------------------------- #
# Default template                                                            #
# --------------------------------------------------------------------------- #

def test_empty_constraints_is_all_unknown_and_null() -> None:
    template = empty_constraints()
    assert template == {
        "combinability": {
            "stackable_with_store_sale": "unknown",
            "stackable_with_member_discounts": "unknown",
            "stackable_with_coupons": "unknown",
            "stackable_with_payment_discounts": "unknown",
            "stackable_with_giftcards": "unknown",
            "stackable_with_cashback": "unknown",
        },
        "limits": {
            "max_uses_per_transaction": None,
            "max_uses_per_month": None,
            "minimum_purchase": None,
        },
        "redemption_channels": {
            "website": "unknown",
            "mobile_app": "unknown",
            "physical_store": "unknown",
        },
        "eligibility": {
            "membership_required": "unknown",
            "payment_method_required": None,
        },
    }


# --------------------------------------------------------------------------- #
# Tri-state booleans                                                          #
# --------------------------------------------------------------------------- #

def test_tristate_accepts_real_booleans() -> None:
    c = Combinability(stackable_with_coupons=True, stackable_with_giftcards=False)
    assert c.stackable_with_coupons is True
    assert c.stackable_with_giftcards is False
    # Untouched fields keep the unknown sentinel.
    assert c.stackable_with_store_sale == "unknown"


def test_redemption_and_eligibility_defaults() -> None:
    assert RedemptionChannels().website == "unknown"
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
        redemption_channels=_LlmRedemptionChannels(
            website="no", mobile_app="unknown", physical_store="yes"
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
    assert comb.stackable_with_payment_discounts == "unknown"
    assert comb.stackable_with_giftcards is False
    assert comb.stackable_with_cashback == "unknown"

    # 0 from the LLM is not a valid positive limit -> None.
    assert public.limits.minimum_purchase is None
    assert public.limits.max_uses_per_transaction == 2

    assert public.redemption_channels.website is False
    assert public.redemption_channels.physical_store is True
    assert public.redemption_channels.mobile_app == "unknown"

    assert public.eligibility.membership_required is True
    assert public.eligibility.payment_method_required == "HOT club-linked credit card"


# --------------------------------------------------------------------------- #
# End-to-end (LLM mocked)                                                     #
# --------------------------------------------------------------------------- #

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
