from __future__ import annotations

from unittest.mock import MagicMock, patch

from lessley_deals.enrichment.llm_client import (
    ExtractedDeal,
    ExtractedDeals,
    extract_deals_from_content,
)


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
