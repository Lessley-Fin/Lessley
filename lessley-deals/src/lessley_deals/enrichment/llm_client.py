from __future__ import annotations

import logging
import os
from typing import List, Literal

import httpx
from openai import OpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


_client: OpenAI | None = None
_model_name: str | None = None


def _build_college_client() -> tuple[OpenAI, str]:
    base_url = os.environ["COLLEGE_API_BASE"]
    model_host = os.environ["COLLEGE_MODEL_HOST"]
    model_name = os.environ["COLLEGE_MODEL_NAME"]
    api_key = os.environ.get("COLLEGE_API_KEY") or "not-needed"

    # IP-based HTTPS with self-signed cert + Run:AI ingress requires Host header routing.
    http_client = httpx.Client(
        verify=False,
        headers={"Host": model_host},
        timeout=httpx.Timeout(120.0, connect=10.0),
    )
    client = OpenAI(base_url=base_url, api_key=api_key, http_client=http_client)
    return client, model_name


def _build_azure_client() -> tuple[OpenAI, str]:
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OpenAI_ApiKey") or ""
    if not api_key:
        raise RuntimeError(
            "No API key found. Set OPENAI_API_KEY (or OpenAI_ApiKey) in your .env file."
        )
    client = OpenAI(
        base_url="https://models.inference.ai.azure.com/",
        api_key=api_key,
    )
    return client, "gpt-4o-mini"


def _get_client() -> tuple[OpenAI, str]:
    """Return (client, model_name) tuple. Provider selected via LLM_PROVIDER env."""
    global _client, _model_name
    if _client is None:
        provider = (os.environ.get("LLM_PROVIDER") or "college").lower()
        if provider == "college":
            _client, _model_name = _build_college_client()
        elif provider == "azure":
            _client, _model_name = _build_azure_client()
        else:
            raise RuntimeError(f"Unknown LLM_PROVIDER={provider!r} (expected 'college' or 'azure')")
        logger.info("LLM client initialized: provider=%s model=%s", provider, _model_name)
    assert _model_name is not None
    return _client, _model_name


class StoreCategory(BaseModel):
    official_name: str
    mcc_codes: List[int] = Field(
        description="A ranked list of the 1 to 3 most accurate MCC codes, from most specific to least specific."
    )
    confidence_level: Literal["HIGH", "MEDIUM", "LOW"]


def get_store_category(store_name: str, store_url: str | None = None) -> StoreCategory:
    """Classify a store by name (and optional URL) and return official name, MCC codes, and confidence."""
    logger.debug("Classifying store: %s (url=%s)", store_name.strip(), store_url)

    user_content = f"Analyze and classify this store: name={store_name.strip()!r}"
    if store_url:
        user_content += f", store_url={store_url!r}"

    client, model = _get_client()
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert data normalization and financial classification engine for the Israeli brands and retail market. "
                    "Assume that the store exists but have typos or inconsistencies. Try to identify the official store name. "
                    "Process raw, messy store strings (typos, hyphens, missing spaces, domain extensions) and perform Entity Resolution. "
                    "When a store_url is provided, use the domain and path to confirm or improve the classification. "
                    "1. Return the official name of the store if you can identify it. If not, return the cleaned name with typos corrected and extraneous characters removed. "
                    "2. Provide an array of the top 1 to 3 most applicable 4-digit Merchant Category Codes (MCC). Rank the array from most specific/likely to least specific/likely. "
                    "3. Provide a confidence_level of HIGH, MEDIUM, or LOW based on how certain you are. Use HIGH if you're very certain and found a clear match, MEDIUM if fairly certain, LOW if uncertain. If you cannot classify, return LOW. "
                    "EXAMPLES: "
                    "a) Input: name='nikestore' -> official_name: 'Nike', mcc_codes: [5941, 5661, 5651]. "
                    "b) Input: name='shufersal-deal' -> official_name: 'Shufersal', mcc_codes: [5411, 5310]. "
                    "c) Input: name='ksp.co.il', store_url='https://ksp.co.il' -> official_name: 'KSP', mcc_codes: [5732, 5722]"
                ),
            },
            {"role": "user", "content": user_content},
        ],
        response_format=StoreCategory,
        temperature=0.0,
        seed=42,
    )

    return completion.choices[0].message.parsed


class ExtractedDeal(BaseModel):
    store_name: str
    deal_description: str
    price_text: str = ""
    url: str | None = None


class ExtractedDeals(BaseModel):
    deals: list[ExtractedDeal]


def extract_deals_from_content(content: str, instructions: str) -> ExtractedDeals:
    """Extract retail deals from one cleaned DOM chunk per the user's instructions."""
    client, model = _get_client()
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You extract retail deals/promotions from messy web page text. "
                    "Return ONLY deals that are clearly supported by the content; if none, "
                    "return an empty list. Each deal needs a store_name and a deal_description; "
                    "include price_text (price, percent, or '') and url when present. "
                    "Follow the user's extraction instructions."
                ),
            },
            {
                "role": "user",
                "content": f"Instructions: {instructions}\n\nPage content:\n{content}",
            },
        ],
        response_format=ExtractedDeals,
        temperature=0.0,
        seed=42,
        max_tokens=8192,  # dense pages list many deals; avoid truncating the JSON array
    )
    parsed = completion.choices[0].message.parsed
    return parsed if parsed is not None else ExtractedDeals(deals=[])
