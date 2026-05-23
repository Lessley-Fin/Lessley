from __future__ import annotations

import json
import logging
import sys
from typing import List, Literal

from dotenv import load_dotenv
from pydantic import BaseModel

from lessley_deals.enrichment.llm_client import _get_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic models — mirrors the output schema defined in the system prompt
# ---------------------------------------------------------------------------

class ValidDates(BaseModel):
    start_date: str | None
    end_date: str | None
    end_note: str | None


class Eligibility(BaseModel):
    membership_required: Literal["yes", "no", "unknown"]
    membership_details: str | None
    payment_method_required: str | None
    valid_dates: ValidDates
    valid_days_of_week: List[str] | None
    valid_days_of_month: List[int] | None
    valid_hours: str | None
    minimum_purchase: str | None


class RedemptionChannels(BaseModel):
    website: Literal["yes", "no", "unknown"]
    physical_store: Literal["yes", "no", "unknown"]
    mobile_app: Literal["yes", "no", "unknown"]
    phone_order: Literal["yes", "no", "unknown"]
    delivery: Literal["yes", "no", "unknown"]
    notes: str


class Combinability(BaseModel):
    stackable_with_promotions: Literal["yes", "no", "unknown"]
    stackable_with_coupons: Literal["yes", "no", "unknown"]
    stackable_with_member_discounts: Literal["yes", "no", "unknown"]
    stackable_with_credit_card_promos: Literal["yes", "no", "unknown"]
    combinability_notes: str


class MaxUsesPerPeriod(BaseModel):
    period_days: int
    max_uses: int


class TransactionLimits(BaseModel):
    max_uses_per_transaction: int | None
    max_uses_per_period: MaxUsesPerPeriod | None


class DetailsForDisplay(BaseModel):
    included_products: List[str]
    excluded_products: List[str]
    location_restrictions: List[str]
    other_restrictions: List[str]


class OriginalHebrewEvidence(BaseModel):
    eligibility_quote: str | None
    channels_quote: str | None
    combinability_quote: str | None
    additional_quotes: List[str]


class DealConstraints(BaseModel):
    eligibility: Eligibility
    redemption_channels: RedemptionChannels
    combinability: Combinability
    transaction_limits: TransactionLimits
    details_for_display: DetailsForDisplay
    original_hebrew_evidence: OriginalHebrewEvidence


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a precise Hebrew-language deal terms analyzer. Your task is to parse Hebrew text containing terms and conditions of a promotional deal, coupon, or offer, and extract structured information about its usage rules and combinability with other deals.

## Your Responsibilities

1. Read the Hebrew text carefully - it may contain legal language, marketing copy, or both.
2. Extract only what is explicitly stated or strongly implied - do not invent restrictions.
3. When information is missing or ambiguous, mark it as "unknown" rather than guessing.
4. Always cite the original Hebrew text that supports each conclusion.
5. Output ONLY valid JSON - no preamble, no markdown fences, no commentary.

## Critical Rules

1. Hebrew evidence must be EXACT - copy character-for-character from the input. Do not paraphrase, translate, or "fix" the Hebrew.
2. If a field is not in the text, use "unknown" for yes/no fields, null for strings/objects, and [] for arrays.
3. Do NOT infer beyond the text. If the text says nothing about apps, mobile_app = "unknown", not "no".
4. Each combinability field is independent — a deal can be "yes" for promotions but "no" for coupons. This is the most important detail of the entire output.

## Key Hebrew Phrase Dictionary

### Combinability mapping (CRITICAL)
- "כפל מבצעים" / "מבצעי הרשתות" → refers to stackable_with_promotions (store sales)
- "כפל קופונים" → refers to stackable_with_coupons
- "הנחות מועדונים" / "הטבות מועדון" → refers to stackable_with_member_discounts
- "כפל הנחות" alone (no qualifier) → refers to stackable_with_promotions AND stackable_with_coupons (both)

Examples:
- "ללא כפל מבצעים" → stackable_with_promotions: no
- "אין כפל מבצעים" → stackable_with_promotions: no
- "כולל כפל מבצעים" → stackable_with_promotions: yes
- "לא כולל כפל קופונים" → stackable_with_coupons: no
- "אין כפל הנחות מועדונים" → stackable_with_member_discounts: no
- "ללא מימוש ו/או צבירה לחברי מועדון" → stackable_with_member_discounts: no
- "בנוסף לכל הנחה אחרת" → all four combinability fields: yes

### Channels (CRITICAL — purchase vs. redemption)
`redemption_channels` describes WHERE THE CUSTOMER USES (REDEEMS) THE DISCOUNT, not where they buy the voucher/coupon.
- Phrases like "רכישת תו דיגיטלי באתר/אפליקציית מועדון X" or "ניתן לרכוש את הקופון באתר ..." describe the PURCHASE flow — they are NOT evidence for redemption_channels. Ignore them.
- Only phrases that describe REDEMPTION ("למימוש", "לשימוש", "תקף ל...", "מימוש התו ב...") set redemption_channels values.
- If the text only describes where to BUY the voucher and says nothing about where to REDEEM it, all redemption_channels fields stay "unknown".

Mapping (only when the phrase is in a redemption context):
- "למימוש באתר" / "מימוש אונליין" → website: yes
- "למימוש באפליקציה" / "למימוש באפליקציית" → mobile_app: yes
- "למימוש בסניפים" / "למימוש בסניפי" / "למימוש בחנות" → physical_store: yes
- "למימוש בסניפים בלבד" → physical_store: yes; website, mobile_app, delivery: no
- "לא תקף במשלוחים" / "לא כולל משלוחים" → delivery: no

### Dates and timing
- "31.12.26" → end_date: "2026-12-31"
- "תוקף X שנים ממועד הנפקתו" → end_date: null, end_note: "X years from issue date"
- "תקף ב10 בחודש בלבד" → valid_days_of_month: [10]
- "בימי ראשון עד חמישי" → valid_days_of_week: ["sunday","monday","tuesday","wednesday","thursday"]
- "עד גמר המלאי" → add to other_restrictions: "Valid while stocks last"

### Eligibility
- "בלעדי למשלמים בכרטיס אשראי X" → payment_method_required: "X credit card" (replace X with the ACTUAL card name from the text, e.g. "Mastercard credit card", "ישראכרט-הוֹט")
- "רכישת התו באמצעות כרטיס האשראי המשויך למועדון בלבד" → payment_method_required + membership_required: yes
- "לחברי מועדון בלבד" → membership_required: yes

### minimum_purchase — IMPORTANT
This field is the CUSTOMER's required spending threshold to use the deal (e.g. "minimum purchase of 200₪").
Do NOT confuse it with:
- inventory/stock counts ("מינימום 1000 שוברים במלאי", "1000 קופונים להטבה") → these refer to deal supply, not customer spending → minimum_purchase: null (and you may add a note to other_restrictions if relevant).
- the price of the voucher being sold ("רכישת תו דיגיטלי בערך נקוב של 50 ₪") → this is the voucher's face value, not a minimum purchase → minimum_purchase: null.

Only set minimum_purchase when the text explicitly requires the buyer to spend a certain amount, e.g. "ברכישה מעל 200 ש״ח" or "במינימום קנייה של 100 ש״ח".

### Transaction limits
`max_uses_per_period` is a structured object with two integer fields:
- `period_days`: the number of days that define the period (1=daily, 7=weekly, 30=monthly/calendar month, 365=yearly)
- `max_uses`: the maximum allowed redemptions in that period

Mappings:
- "ניתן לממש קוד קופון אחד בעסקה" → max_uses_per_transaction: 1
- "ניתן לממש עד X תווים בעסקה אחת" → max_uses_per_transaction: X
- "ניתן לממש עד X לחבר מועדון בחודש קלנדרי" → max_uses_per_period: {"period_days": 30, "max_uses": X}
- "עד X פעמים בשבוע" → max_uses_per_period: {"period_days": 7, "max_uses": X}
- "עד X פעמים ביום" → max_uses_per_period: {"period_days": 1, "max_uses": X}
- "עד X פעמים בשנה" → max_uses_per_period: {"period_days": 365, "max_uses": X}

## Final Reminder

- Return ONLY the JSON object.
- No ```json fences, no explanations before or after.
- Validate that your output is parseable JSON before returning.
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_deal_constraints(deal_terms: str) -> DealConstraints:
    """Parse Hebrew deal terms and conditions into structured constraint data."""
    logger.debug("Parsing deal constraints (%d chars)", len(deal_terms))

    client, model = _get_client()
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": deal_terms},
        ],
        response_format=DealConstraints,
        temperature=0.0,
        seed=42,
    )

    return completion.choices[0].message.parsed


# ---------------------------------------------------------------------------
# Quick test entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the parser against a deal JSON file, storing results in-place.

    Usage:
        python -m lessley_deals.enrichment.constaints_parser <path/to/deal.json>

    The file can be:
      - a single deal object  { "terms_and_conditions": "..." }
      - a list of deals       [{ "terms_and_conditions": "..." }, ...]
        → all items are processed; those without terms_and_conditions are skipped

    Constraints are written into a "constraints" field on each deal object and
    the file is saved in-place.
    """
    load_dotenv()

    if len(sys.argv) < 2:
        print("Usage: python -m lessley_deals.enrichment.constaints_parser <path/to/deal.json>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    is_list = isinstance(data, list)
    deals = data if is_list else [data]

    for deal in deals:
        terms = deal.get("terms_and_conditions")
        if not terms:
            print(f"Skipping deal (no terms_and_conditions): {deal.get('title') or deal.get('id', '?')}")
            continue

        print(f"Parsing deal: {deal.get('title') or deal.get('description') or deal.get('id', '?')}")
        print(f"Terms ({len(terms)} chars):\n{terms}\n")

        result = parse_deal_constraints(terms)
        deal.setdefault("discount_logic", {})["constraints"] = result.model_dump()

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Done. Constraints written in-place to: {path}")


if __name__ == "__main__":
    main()
