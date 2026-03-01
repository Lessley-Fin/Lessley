from __future__ import annotations

import json
from typing import Any

from core.config import Settings

try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover
    AsyncOpenAI = None


class LLMNormalizer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None
        if settings.openai_api_key and AsyncOpenAI:
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def normalize_offer(self, offer: dict[str, Any]) -> dict[str, Any]:
        if not self._client:
            return self._fallback_offer(offer)

        prompt = {
            "task": "Normalize the benefit offer to consistent schema.",
            "schema": {
                "normalized_title": "string",
                "normalized_category": "string",
                "discount_type": "percent|amount|other",
                "discount_value": "number|null",
                "summary": "short Hebrew summary",
            },
            "offer": {
                "title": offer.get("title"),
                "business_name": offer.get("business_name"),
                "category": offer.get("category"),
                "benefit_value": offer.get("benefit_value"),
                "benefit_type": offer.get("benefit_type"),
                "description": offer.get("description"),
            },
        }

        try:
            response = await self._client.chat.completions.create(
                model=self.settings.openai_model,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": "Return valid JSON only. Keep Hebrew output where relevant.",
                    },
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
                temperature=0,
            )
            content = response.choices[0].message.content or "{}"
            llm_data = json.loads(content)
            offer["llm_normalized"] = llm_data
            return offer
        except Exception:
            return self._fallback_offer(offer)

    async def normalize_card(self, card: dict[str, Any]) -> dict[str, Any]:
        return card

    @staticmethod
    def _fallback_offer(offer: dict[str, Any]) -> dict[str, Any]:
        raw_title = (offer.get("title") or "").strip()
        raw_category = (offer.get("category") or "").strip()
        benefit_value = str(offer.get("benefit_value") or "")

        discount_type = "other"
        discount_value = None
        if "%" in benefit_value:
            discount_type = "percent"
            num = benefit_value.replace("%", "").strip()
            if num.replace(".", "", 1).isdigit():
                discount_value = float(num)
        elif any(ch.isdigit() for ch in benefit_value):
            discount_type = "amount"

        offer["llm_normalized"] = {
            "normalized_title": raw_title,
            "normalized_category": raw_category or "general",
            "discount_type": discount_type,
            "discount_value": discount_value,
            "summary": offer.get("description") or raw_title,
            "normalizer": "fallback",
        }
        return offer