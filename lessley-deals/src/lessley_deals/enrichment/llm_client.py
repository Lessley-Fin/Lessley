from __future__ import annotations

import logging
import os
from typing import List, Literal

from openai import OpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OpenAI_ApiKey") or ""
        if not api_key:
            raise RuntimeError(
                "No API key found. Set OPENAI_API_KEY (or OpenAI_ApiKey) in your .env file."
            )
        _client = OpenAI(
            base_url="https://models.inference.ai.azure.com/",
            api_key=api_key,
        )
    return _client


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

    completion = _get_client().beta.chat.completions.parse(
        model="gpt-4o-mini",
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
