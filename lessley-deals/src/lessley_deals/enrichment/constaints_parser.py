from __future__ import annotations

import json
import logging
import sys
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, field_validator

from lessley_deals.enrichment.llm_client import _get_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public storage schema — the exact shape written onto ``Deal.constraints``.
#
# Tri-state fields resolve to a real boolean (True / False) once the terms
# make the answer explicit, and stay the sentinel string ``"unknown"`` while
# undetermined.  Numeric limits are positive whole integers or ``None``.
# ---------------------------------------------------------------------------

# True / False when known, "unknown" until the text says otherwise.
TriBool = bool | Literal["unknown"]


class Combinability(BaseModel):
    """Whether the deal stacks with each other kind of discount.

    Every field is independent — a deal can stack with store sales yet be
    blocked from stacking with coupons.
    """

    stackable_with_store_sale: TriBool = "unknown"
    stackable_with_member_discounts: TriBool = "unknown"
    stackable_with_coupons: TriBool = "unknown"
    stackable_with_payment_discounts: TriBool = "unknown"
    stackable_with_giftcards: TriBool = "unknown"
    stackable_with_cashback: TriBool = "unknown"


class Limits(BaseModel):
    """Numeric usage limits. Each value is a positive whole integer or None."""

    max_uses_per_transaction: int | None = None
    max_uses_per_month: int | None = None
    minimum_purchase: int | None = None

    @field_validator(
        "max_uses_per_transaction",
        "max_uses_per_month",
        "minimum_purchase",
        mode="after",
    )
    @classmethod
    def _positive_int_or_none(cls, value: int | None) -> int | None:
        # A limit only makes sense as a positive whole number. Anything else
        # (0, negatives, a stray float) collapses to "no limit" → None.
        if value is None:
            return None
        try:
            ivalue = int(value)
        except (TypeError, ValueError):
            return None
        return ivalue if ivalue > 0 else None


class RedemptionChannels(BaseModel):
    """Where the customer REDEEMS the discount (not where they buy it)."""

    website: TriBool = "unknown"
    mobile_app: TriBool = "unknown"
    physical_store: TriBool = "unknown"


class Eligibility(BaseModel):
    membership_required: TriBool = "unknown"
    payment_method_required: str | None = None


class DealConstraints(BaseModel):
    combinability: Combinability = Combinability()
    limits: Limits = Limits()
    redemption_channels: RedemptionChannels = RedemptionChannels()
    eligibility: Eligibility = Eligibility()


def empty_constraints() -> dict[str, object]:
    """Return the default all-``unknown`` / all-``null`` constraints template."""
    return DealConstraints().model_dump()


# ---------------------------------------------------------------------------
# LLM-facing schema — uses plain yes/no/unknown enums, which every
# OpenAI-compatible structured-output provider handles reliably.  Converted
# to the boolean public schema by ``_to_public`` below.
# ---------------------------------------------------------------------------

_YesNo = Literal["yes", "no", "unknown"]


class _LlmCombinability(BaseModel):
    stackable_with_store_sale: _YesNo
    stackable_with_member_discounts: _YesNo
    stackable_with_coupons: _YesNo
    stackable_with_payment_discounts: _YesNo
    stackable_with_giftcards: _YesNo
    stackable_with_cashback: _YesNo


class _LlmLimits(BaseModel):
    max_uses_per_transaction: int | None
    max_uses_per_month: int | None
    minimum_purchase: int | None


class _LlmRedemptionChannels(BaseModel):
    website: _YesNo
    mobile_app: _YesNo
    physical_store: _YesNo


class _LlmEligibility(BaseModel):
    membership_required: _YesNo
    payment_method_required: str | None


class _LlmDealConstraints(BaseModel):
    combinability: _LlmCombinability
    limits: _LlmLimits
    redemption_channels: _LlmRedemptionChannels
    eligibility: _LlmEligibility


def _tri(value: str) -> TriBool:
    """Map a yes/no/unknown enum onto the public tri-state boolean."""
    if value == "yes":
        return True
    if value == "no":
        return False
    return "unknown"


def _to_public(llm: _LlmDealConstraints) -> DealConstraints:
    """Convert the enum-based LLM output into the boolean public schema."""
    c = llm.combinability
    r = llm.redemption_channels
    e = llm.eligibility
    return DealConstraints(
        combinability=Combinability(
            stackable_with_store_sale=_tri(c.stackable_with_store_sale),
            stackable_with_member_discounts=_tri(c.stackable_with_member_discounts),
            stackable_with_coupons=_tri(c.stackable_with_coupons),
            stackable_with_payment_discounts=_tri(c.stackable_with_payment_discounts),
            stackable_with_giftcards=_tri(c.stackable_with_giftcards),
            stackable_with_cashback=_tri(c.stackable_with_cashback),
        ),
        limits=Limits(
            max_uses_per_transaction=llm.limits.max_uses_per_transaction,
            max_uses_per_month=llm.limits.max_uses_per_month,
            minimum_purchase=llm.limits.minimum_purchase,
        ),
        redemption_channels=RedemptionChannels(
            website=_tri(r.website),
            mobile_app=_tri(r.mobile_app),
            physical_store=_tri(r.physical_store),
        ),
        eligibility=Eligibility(
            membership_required=_tri(e.membership_required),
            payment_method_required=e.payment_method_required,
        ),
    )


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a precise Hebrew-language deal terms analyzer. Your task is to parse Hebrew text containing terms and conditions of a promotional deal, coupon, or offer (from the Israeli loyalty club "מועדון הוט"/HOT) and extract structured information about how it may be combined with other discounts, its usage limits, where it is redeemed, and who is eligible.

## Your Responsibilities

1. Read the Hebrew text carefully - it may contain legal language, marketing copy, or both.
2. Extract only what is explicitly stated or strongly implied - do not invent restrictions.
3. When information is missing or ambiguous, use "unknown" (for yes/no fields) or null (for numbers/strings) rather than guessing.
4. Output ONLY valid JSON - no preamble, no markdown fences, no commentary.

## Output schema (all fields REQUIRED)

{
  "combinability": {
    "stackable_with_store_sale": "yes|no|unknown",
    "stackable_with_member_discounts": "yes|no|unknown",
    "stackable_with_coupons": "yes|no|unknown",
    "stackable_with_payment_discounts": "yes|no|unknown",
    "stackable_with_giftcards": "yes|no|unknown",
    "stackable_with_cashback": "yes|no|unknown"
  },
  "limits": {
    "max_uses_per_transaction": <positive integer or null>,
    "max_uses_per_month": <positive integer or null>,
    "minimum_purchase": <positive integer or null>
  },
  "redemption_channels": {
    "website": "yes|no|unknown",
    "mobile_app": "yes|no|unknown",
    "physical_store": "yes|no|unknown"
  },
  "eligibility": {
    "membership_required": "yes|no|unknown",
    "payment_method_required": <string or null>
  }
}

## Critical Rules

1. Numbers are ALWAYS positive whole integers or null. Never a string, never a decimal, never 0.
2. yes/no/unknown fields: use "unknown" (not "no") when the text is silent. "no" requires an explicit prohibition.
3. Do NOT infer beyond the text. If the text says nothing about the app, mobile_app = "unknown".
4. Each combinability field is independent — a deal can be "yes" for store sales but "no" for coupons.

## Combinability — Hebrew phrase mapping (CRITICAL)

- "כפל מבצעים" / "מבצעי הרשתות" / "מבצעי הרשת" → stackable_with_store_sale
- "כפל קופונים" → stackable_with_coupons
- "הנחות מועדון" / "הטבות מועדון" / "הנחת חבר מועדון" → stackable_with_member_discounts
- "הנחה במעמד החיוב" / "הנחת אשראי" / "כפל הנחת תשלום" → stackable_with_payment_discounts
- "תווי קניה" / "תו קניה" / "כרטיס מתנה" / "שוברים" / "גיפט קארד" → stackable_with_giftcards
- "צבירה" / "קאשבק" / "cashback" / "זיכוי/צבירה למועדון" → stackable_with_cashback
- "כפל הנחות" alone (no qualifier) → set BOTH stackable_with_store_sale AND stackable_with_coupons

Examples:
- "כולל כפל מבצעים והנחות" → stackable_with_store_sale: yes, stackable_with_member_discounts: yes
- "ללא כפל מבצעים" / "אין כפל מבצעים" → stackable_with_store_sale: no
- "לא כולל כפל קופונים" → stackable_with_coupons: no
- "אין כפל הנחות מועדון" / "ללא מימוש ו/או צבירה לחברי מועדון" → stackable_with_member_discounts: no
- "לא ניתן לרכוש כרטיס מתנה באמצעות השובר" → stackable_with_giftcards: no
- "בנוסף לכל הנחה אחרת" → all six combinability fields: yes

## Channels — purchase vs. redemption (CRITICAL)

`redemption_channels` = WHERE THE CUSTOMER USES (REDEEMS) THE DISCOUNT, not where they buy the voucher/coupon.
- Phrases like "רכישת תו דיגיטלי באתר/אפליקציית מועדון הוט" describe the PURCHASE flow — they are NOT evidence for redemption_channels. Ignore them.
- Only phrases describing REDEMPTION ("למימוש", "לשימוש", "תקף ל...", "מימוש התו ב...", "בקופות הסניפים") set redemption_channels.
- If the text only says where to BUY and nothing about where to REDEEM, all redemption_channels stay "unknown".

Mapping (redemption context only):
- "למימוש באתר" / "מימוש אונליין" → website: yes
- "למימוש באפליקציה" / "באפליקציית ...למימוש" → mobile_app: yes
- "למימוש בסניפים" / "בקופות הסניפים" / "בחנות" → physical_store: yes
- "בסניפים בלבד" → physical_store: yes; website: no; mobile_app: no
- "לא ניתן למימוש באתר" / "לא ניתן למימוש באתר הסחר" → website: no

## Limits

- "ניתן לממש קוד/שובר אחד בעסקה" → max_uses_per_transaction: 1
- "ניתן לממש עד X שוברים/תווים בעסקה" → max_uses_per_transaction: X
- "עד X לחבר מועדון בחודש קלנדרי" / "עד X בחודש" → max_uses_per_month: X
- Limits stated for other periods (per day / per week / per year) have no field here → leave max_uses_per_month: null.
- minimum_purchase = the customer's required spend threshold in ₪, e.g. "ברכישה מעל 200 ש״ח" → 200; "במינימום קנייה של 100 ש״ח" → 100.
  Do NOT confuse it with: stock/supply counts ("מינימום 1000 שוברים במלאי") or the voucher's face value ("תו דיגיטלי בערך נקוב של 50 ₪"). Those → minimum_purchase: null.

## Eligibility

- "לחברי מועדון בלבד" / voucher purchasable only with the club-linked card → membership_required: yes
- "בלעדי למשלמים בכרטיס אשראי X" / "בכרטיס האשראי המשויך למועדון הוט" → payment_method_required: describe the card in English (e.g. "HOT club-linked credit card"), AND membership_required: yes when club membership is implied.
- If no specific payment instrument is required → payment_method_required: null.

## Final Reminder

- Return ONLY the JSON object. No ```json fences, no explanations.
- Every field must be present. Validate that your output is parseable JSON before returning.
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_deal_constraints(deal_terms: str) -> DealConstraints:
    """Parse Hebrew deal terms and conditions into structured constraint data.

    The LLM emits yes/no/unknown enums; the result is converted into the
    boolean public :class:`DealConstraints` schema (True / False / "unknown"
    for tri-state fields, positive-int or None for limits).
    """
    logger.debug("Parsing deal constraints (%d chars)", len(deal_terms))

    client, model = _get_client()
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": deal_terms},
        ],
        response_format=_LlmDealConstraints,
        temperature=0.0,
        seed=42,
    )

    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("LLM returned no parseable constraints")
    return _to_public(parsed)


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

    Constraints are written into a top-level "constraints" field on each deal
    object and the file is saved in-place.
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

        print(f"Parsing deal: {deal.get('title') or deal.get('deal_description') or deal.get('id', '?')}")
        print(f"Terms ({len(terms)} chars):\n{terms}\n")

        result = parse_deal_constraints(terms)
        deal["constraints"] = result.model_dump()

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Done. Constraints written in-place to: {path}")


if __name__ == "__main__":
    main()
