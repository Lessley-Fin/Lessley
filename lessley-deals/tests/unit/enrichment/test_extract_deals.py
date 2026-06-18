from __future__ import annotations

from unittest.mock import MagicMock, patch

from lessley_deals.enrichment.llm_client import (
    DealDetail,
    ExtractedDeal,
    ExtractedDeals,
    extract_deals_from_content,
    extract_detail,
)


def test_extracted_deal_accepts_detail_url() -> None:
    d = ExtractedDeal(store_name="Nike", deal_description="3%", detail_url="/store/5")
    assert d.detail_url == "/store/5"


def test_extract_detail_returns_parsed_model() -> None:
    fake = DealDetail(deal_description="store blurb", terms_and_conditions="rules", coupon_code="ABC")
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(parsed=fake))]
    client = MagicMock()
    client.beta.chat.completions.parse.return_value = completion
    with patch(
        "lessley_deals.enrichment.llm_client._get_client",
        return_value=(client, "test-model"),
    ):
        out = extract_detail("page text", "extract blurb + terms")
    assert isinstance(out, DealDetail)
    assert out.deal_description == "store blurb"
    assert out.coupon_code == "ABC"


def test_extract_deals_returns_parsed_model() -> None:
    fake_parsed = ExtractedDeals(
        deals=[ExtractedDeal(store_name="Nike", deal_description="20% off", price_text="20%")]
    )
    fake_completion = MagicMock()
    fake_completion.choices = [MagicMock(message=MagicMock(parsed=fake_parsed))]
    fake_client = MagicMock()
    fake_client.beta.chat.completions.parse.return_value = fake_completion

    with patch(
        "lessley_deals.enrichment.llm_client._get_client",
        return_value=(fake_client, "test-model"),
    ):
        result = extract_deals_from_content("Nike 20% off", "Extract deals")

    assert isinstance(result, ExtractedDeals)
    assert result.deals[0].store_name == "Nike"
    # Verify deterministic call params
    _, kwargs = fake_client.beta.chat.completions.parse.call_args
    assert kwargs["temperature"] == 0.0
    assert kwargs["seed"] == 42
    assert kwargs["response_format"] is ExtractedDeals
