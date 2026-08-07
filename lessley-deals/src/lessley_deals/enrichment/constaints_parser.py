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

    Optimistic by default: when the terms are silent about a given kind of
    stacking, the field is ``True`` (assume it stacks). Only an explicit
    prohibition in the text sets a field to ``False``. Every field is
    independent — a deal can stack with store sales yet be blocked from coupons.
    """

    stackable_with_store_sale: bool = True
    stackable_with_member_discounts: bool = True
    stackable_with_coupons: bool = True
    stackable_with_payment_discounts: bool = True
    stackable_with_giftcards: bool = True
    stackable_with_cashback: bool = True


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


class StoreCoverage(BaseModel):
    """Which store types the deal applies to (its scope of coverage)."""

    is_include_outlets_stores: TriBool = "unknown"
    is_include_online_stores: TriBool = "unknown"
    is_include_physical_stores: TriBool = "unknown"


class Eligibility(BaseModel):
    membership_required: TriBool = "unknown"
    payment_method_required: str | None = None


class DealConstraints(BaseModel):
    combinability: Combinability = Combinability()
    limits: Limits = Limits()
    store_coverage: StoreCoverage = StoreCoverage()
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


class _LlmStoreCoverage(BaseModel):
    is_include_outlets_stores: _YesNo
    is_include_online_stores: _YesNo
    is_include_physical_stores: _YesNo


class _LlmEligibility(BaseModel):
    membership_required: _YesNo
    payment_method_required: str | None


class _LlmDealConstraints(BaseModel):
    combinability: _LlmCombinability
    limits: _LlmLimits
    store_coverage: _LlmStoreCoverage
    eligibility: _LlmEligibility


def _tri(value: str) -> TriBool:
    """Map a yes/no/unknown enum onto the public tri-state boolean."""
    if value == "yes":
        return True
    if value == "no":
        return False
    return "unknown"


def _tri_optimistic(value: str) -> bool:
    """Combinability mapping: default to True unless explicitly prohibited.

    "yes" and "unknown" (no information) both become True; only "no" is False.
    """
    return value != "no"


def _to_public(llm: _LlmDealConstraints) -> DealConstraints:
    """Convert the enum-based LLM output into the boolean public schema."""
    c = llm.combinability
    r = llm.store_coverage
    e = llm.eligibility
    return DealConstraints(
        combinability=Combinability(
            stackable_with_store_sale=_tri_optimistic(c.stackable_with_store_sale),
            stackable_with_member_discounts=_tri_optimistic(c.stackable_with_member_discounts),
            stackable_with_coupons=_tri_optimistic(c.stackable_with_coupons),
            stackable_with_payment_discounts=_tri_optimistic(c.stackable_with_payment_discounts),
            stackable_with_giftcards=_tri_optimistic(c.stackable_with_giftcards),
            stackable_with_cashback=_tri_optimistic(c.stackable_with_cashback),
        ),
        limits=Limits(
            max_uses_per_transaction=llm.limits.max_uses_per_transaction,
            max_uses_per_month=llm.limits.max_uses_per_month,
            minimum_purchase=llm.limits.minimum_purchase,
        ),
        store_coverage=StoreCoverage(
            is_include_outlets_stores=_tri(r.is_include_outlets_stores),
            is_include_online_stores=_tri(r.is_include_online_stores),
            is_include_physical_stores=_tri(r.is_include_physical_stores),
        ),
        eligibility=Eligibility(
            membership_required=_tri(e.membership_required),
            payment_method_required=e.payment_method_required,
        ),
    )


# ---------------------------------------------------------------------------
# System prompt
#
# Assembled from three parts by :func:`build_system_prompt`:
#
#   _BASE_SYSTEM_PROMPT  — the schema, the rules, and the Hebrew vocabulary
#                          every Israeli source shares.
#   _SOURCE_PROMPTS[id]  — one source's own terminology and quirks. Every site
#                          words the same restriction differently and leans on
#                          its own instrument (voucher / loadable card / club
#                          card), so the generic mapping alone either misses
#                          fields or mis-assigns them.
#   _FINAL_REMINDER      — output discipline, kept last so it is the closest
#                          instruction to the model's turn.
#
# A source with no entry in _SOURCE_PROMPTS just gets base + reminder, i.e.
# exactly the behaviour that existed before per-source blocks were added.
# ---------------------------------------------------------------------------

_BASE_SYSTEM_PROMPT = """\
You are a precise Hebrew-language deal terms analyzer. Your task is to parse Hebrew text containing terms and conditions of a promotional deal, coupon, or offer from an Israeli retailer, loyalty club, or credit-card benefits program (e.g. HOT / מועדון הוט, Mastercard, Behatsdaa / בהצדעה, Isracard) and extract structured information about how it may be combined with other discounts, its usage limits, which store types it covers, and who is eligible.

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
  "store_coverage": {
    "is_include_outlets_stores": "yes|no|unknown",
    "is_include_online_stores": "yes|no|unknown",
    "is_include_physical_stores": "yes|no|unknown"
  },
  "eligibility": {
    "membership_required": "yes|no|unknown",
    "payment_method_required": <string or null>
  }
}

## Critical Rules

1. Numbers are ALWAYS positive whole integers or null. Never a string, never a decimal, never 0.
2. yes/no/unknown fields: use "unknown" (not "no") when the text is silent. "no" requires an explicit prohibition.
3. Do NOT infer beyond the text. If the text says nothing about outlet stores, is_include_outlets_stores = "unknown".
4. Each combinability field is independent — a deal can be "yes" for store sales but "no" for coupons.
5. Combinability is OPTIMISTIC: when the text is silent about a kind of stacking, answer "unknown" (it is stored as stackable=true). Only use "no" when the text explicitly prohibits that stacking.

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

## Store coverage — WHICH store types the deal applies to (CRITICAL)

`store_coverage` = the TYPES OF STORES where the deal is valid. This is about the deal's scope
(are outlet branches in? is the online shop in? are regular branches in?), NOT where the customer
buys the voucher. "yes" = that store type IS included; "no" = explicitly EXCLUDED; "unknown" = silent.

- is_include_outlets_stores → outlet / surplus branches ("חנויות עודפים", "אאוטלט", "חנויות העודפים")
- is_include_online_stores → the retailer's e-commerce / online shop ("אתר הסחר", "אתר האינטרנט", "אונליין", "החנות המקוונת")
- is_include_physical_stores → the retailer's regular physical branches ("סניפים", "בחנות", "בקופות הסניפים")

Mapping:
- "תקף בסניפים" / "למימוש בקופות הסניפים" / "בחנות" → is_include_physical_stores: yes
- "תקף גם באתר" / "כולל אתר האינטרנט" / "למימוש אונליין" → is_include_online_stores: yes
- "לא ניתן למימוש באתר הסחר" / "לא תקף באתר" → is_include_online_stores: no
- "לא ניתן לממש בחנויות העודפים" / "לא כולל חנויות עודפים" → is_include_outlets_stores: no
- "תקף בסניפים בלבד" → is_include_physical_stores: yes; is_include_online_stores: no; is_include_outlets_stores: no
- Do NOT infer coverage from the PURCHASE channel ("רכישת תו דיגיטלי באתר מועדון הוט" is where you BUY the voucher — it does not make is_include_online_stores yes).

## Limits

- "ניתן לממש קוד/שובר אחד בעסקה" → max_uses_per_transaction: 1
- "ניתן לממש עד X שוברים/תווים בעסקה" → max_uses_per_transaction: X
- "עד X לחבר מועדון בחודש קלנדרי" / "עד X בחודש" → max_uses_per_month: X
- Limits stated for other periods (per day / per week / per year) have no field here → leave max_uses_per_month: null.
- minimum_purchase = the customer's required spend threshold in ₪, e.g. "ברכישה מעל 200 ש״ח" → 200; "במינימום קנייה של 100 ש״ח" → 100.
  Do NOT confuse it with: stock/supply counts ("מינימום 1000 שוברים במלאי") or the voucher's face value ("תו דיגיטלי בערך נקוב של 50 ₪"). Those → minimum_purchase: null.

## Eligibility

- "לחברי מועדון בלבד" / voucher purchasable only with the club-linked card → membership_required: yes
- "בלעדי למשלמים בכרטיס אשראי X" / "בכרטיס האשראי המשויך למועדון X" → payment_method_required: describe the card/club in English using the ACTUAL name in the text (e.g. "HOT club-linked credit card", "Isracard", "Mastercard"), AND membership_required: yes when club membership is implied.
- If no specific payment instrument is required → payment_method_required: null.
"""


_BEHATSDAA_PROMPT = """\
# SOURCE-SPECIFIC RULES — Behatsdaa / בהצדעה (loadable wallet)

These rules OVERRIDE the generic guidance above wherever the two disagree.

## What this source is

Behatsdaa is a closed members' club. The benefit is not a voucher — it is a
**loadable prepaid card** (``הכרטיס הנטען`` / ``ארנק``): the member loads money
onto a wallet, receives a flat percentage off the load, and then spends the
loaded balance at the accepting chain. So "the card" and "the payment method"
are the same object, and the discount is already realised at load time.

The terms text you receive has up to four blocks, in this order:

1. ``הגבלות והחרגות כלליות (הכרטיס הנטען):`` — the card's site-wide rules.
   These apply to EVERY Behatsdaa deal.
2. ``מגבלות ספציפיות לרשת <chain>:`` — that one chain's own rules. **Present
   only for some chains, and always wins over block 1 on any field it
   addresses.**
3. Free-text wallet notes (usually absent).
4. A closing sentence: ``ניתן לטעון עד <N> ₪ לחודש דרך ארנק "<wallet>" ולקבל
   <P>% הנחה, לשימוש ברשת <chain>.`` This is the deal's **economics**, not a
   restriction. Read it only for the wallet name and the chain name.

## Baseline from block 1 (assume these unless block 2 says otherwise)

Block 1 is boilerplate and will be near-identical on every deal. Resolve it
once, like this — these are known facts for this source, not guesses:

| Block-1 phrase | Field | Value |
|---|---|---|
| ``לא כולל חנויות עודפים`` | is_include_outlets_stores | no |
| ``הכסף הנטען אינו מיועד לרכישה באתרי הרשתות ... אלא רק בסניפי הרשתות`` | is_include_online_stores | no |
| (same phrase, ``רק בסניפי הרשתות``) | is_include_physical_stores | yes |
| ``הכרטיס כולל כפל מבצעים והנחות (גם בסוף עונה)`` | stackable_with_store_sale | yes |
| ``לא כולל הנחות חברי מועדון`` | stackable_with_member_discounts | no |
| ``וצבירת נקודות של הרשת`` | stackable_with_cashback | no |
| ``לא ניתן לרכוש כרטיסי גיפט כארד באמצעות הכרטיס הנטען`` | stackable_with_giftcards | no |

Also always true for this source:
- membership_required: yes — the wallet is only loadable by a Behatsdaa member.
- payment_method_required: "Behatsdaa prepaid wallet". If the wallet name in
  the closing sentence names a specific card (e.g. ``כרטיס פייטר``), use that
  instead: "Behatsdaa Fighter card".

Leave stackable_with_coupons and stackable_with_payment_discounts as "unknown"
unless the text actually mentions coupons / a billing-time discount. Block 1
says nothing about either.

## Block-2 overrides (chain-specific — these WIN)

Stacking:
- ``כולל כפל מבצעים לחברי מועדון`` / ``כולל חברי מועדון`` /
  ``כולל מבצעים ומבצעי מועדון (לחברי מועדון)`` → stackable_with_member_discounts: **yes**
- ``אין כפל הנחות מועדונים`` / ``לא כולל מבצעי מועדון`` /
  ``לא כולל מבצעים לחברי מועדון הרשת`` → stackable_with_member_discounts: no
- ``לא כולל כפל מבצעים`` / ``אין כפל מבצעים`` / ``ללא כפל הנחות ומבצעים`` →
  stackable_with_store_sale: **no** (this reverses the block-1 baseline)
- ``ממחיר מחירון`` ("off list price" — typical for culture venues) →
  stackable_with_store_sale: no. Combined with
  ``לא כולל כפל מבצעים והנחות`` → also stackable_with_coupons: no.
- ``כולל כפל מבצעי ספקים`` → stackable_with_store_sale: yes
- ``לא ניתן לרכוש תווי שי`` / ``לא כולל רכישה/טעינה של כרטיס מתנה`` /
  ``קניית שוברי מתנה`` excluded → stackable_with_giftcards: no

Store coverage:
- ``בסניפי עודפים ניתן לממש על קולקציה חדשה בלבד`` → is_include_outlets_stores:
  **yes**. Outlet branches ARE in scope here; the sentence only narrows *what*
  may be bought there. Same for ``תקף לכל סניפי הרשת כולל עודפים``.
- ``לא כולל חנויות עודפים`` (restated per chain) → is_include_outlets_stores: no
- ``אתר + סניפים`` / ``ניתן לרכוש ... גם באתר האונליין`` /
  ``הפעילות דרך האתר הייעודי בלבד`` → is_include_online_stores: **yes**
- ``לא כולל אתר הסחר האלקטרוני`` / ``לא כולל אתר הסחר`` /
  ``לא ניתן לקנות ב-ON LINE`` / ``לא תקף באתר אונליין`` /
  ``לא ניתן לרכוש דרך האתר`` / ``הזמנות און ליין באתר`` excluded →
  is_include_online_stores: no
- ``תקף בסניפי הרשת בלבד`` / ``תקף לסניפים בלבד`` → is_include_physical_stores:
  yes; is_include_online_stores: no

**Online-chain exception (important).** Some wallets and chains are explicitly
online: the wallet may be named ``בהצדעה - מזון + אתרי אונליין``, or the chain
name in the closing sentence may end in ``אונליין`` / ``און ליין`` / ``online``
(e.g. ``ויקטורי אונליין``, ``נעמן אונליין``, ``SIMMONS online``). When either
is true, the deal IS for the web shop: is_include_online_stores: **yes**, and
is_include_physical_stores: "unknown" unless the text names branches too. Do
not let block 1's ``רק בסניפי הרשתות`` override the chain's own identity.

## Limits — shekel ceilings are NOT limits (read this twice)

This source's single most common restriction is a **per-transaction spend
ceiling**. There is NO field for it. Every one of these leaves ALL THREE
numeric fields null:

- ``עד 1,000 ש"ח לעסקה`` · ``עד 1000 שח לעסקה`` · ``עד 750 ₪ לעסקה``
- ``סכום מקסימלי למימוש בעסקה - 500 ₪``
- ``מוגבל למימוש עד 2,000 ₪ בעסקה`` · ``מוגבל ל-1,000 ₪ בקנייה``
- ``ניתן לממש עד לסכום של 1,000 ש"ח`` · ``ניתן לנצל עד 600 ₪ בעסקה``
- ``ניתן לפרוק עד 1000 ₪ לעסקה`` · ``ניתן לממש עד 500 ₪ ברשת``
- ``ניתן להשתמש בכרטיס עד 50% משווי העסקה``
- ``מגבלת שימוש של 500 שח בכרטיס בהזמנה``

A shekel amount is a CEILING on spend. It is never max_uses_per_transaction
(which counts cards/vouchers, not shekels) and never minimum_purchase (which
is a floor the customer must reach). If in doubt about a shekel figure: null.

Likewise the wallet's monthly load cap in the closing sentence —
``ניתן לטעון עד 1000 ₪ לחודש`` — is how much may be LOADED, not how many times
the deal may be used and not a required spend. max_uses_per_month: null,
minimum_purchase: null.

Genuine counts DO map:
- ``ניתן לממש 2 שוברים בלבד לשולחן/עסקה`` → max_uses_per_transaction: 2
- ``ניתן לממש שובר אחד בלבד לשולחן`` → max_uses_per_transaction: 1
- ``לא ניתן לממש יותר מכרטיס אחד לעסקה`` → max_uses_per_transaction: 1
- ``ניתן לשלם עם כרטיס אחד פר עסקה`` → max_uses_per_transaction: 1
- ``לא ניתן לממש מספר כרטיסים באותה הזמנה`` → max_uses_per_transaction: 1

## Has no field — do NOT force these anywhere

This page is full of operational detail that the schema does not model. Record
nothing for it; in particular do not bend it into store_coverage or limits.

- Meal/timing exclusions: ``לא כולל עסקיות`` · ``ארוחות עסקיות`` ·
  ``לא תקף ב-HAPPY HOUR`` · ``שעות שמחות`` · ``ארוחת ילדים`` ·
  ``אכול כפי יכולתך`` · ``חול המועד`` · ``ערבי חג``
- Channel/venue detail that is NOT the retailer's web shop:
  ``לא תקף במשלוחים`` · ``TAKE AWAY`` · ``תקף בישיבה בלבד`` ·
  ``לא ניתן לפצל שולחנות`` · ``הזמנות טלפוניות``. Delivery and take-away are
  not "online stores" — leave is_include_online_stores alone for these.
- Kashrut: ``כשר`` · ``כשר מהדרין``
- Named branch inclusions/exclusions: ``לא תקף בסניף רמון`` ·
  ``תקף לסניפים: קצרין, צפת, נהריה`` · ``לא תקף בסניפי זכיין``. A franchise
  branch (``זכיין``) is NOT an outlet store — do not touch
  is_include_outlets_stores for it.
- Product-category exclusions: ``לא כולל מחלקת חשמל`` · ``מוצרי פיינל סייל`` ·
  ``שטיחים`` · ``מוצרי LIMITED`` · ``גיימינג`` · ``סיגריות ואלכוהול`` ·
  ``ספרי לימוד`` · ``רכישת סדרות מעצבים``
- Booking mechanics and policies: ``לאחר רכישה חובה ליצור קשר`` ·
  ``בתיאום מראש בלבד`` · ``לא תקף דרך סוכנים כדוגמת בוקינג`` ·
  ``מדיניות ביטולים`` · ``בכפוף להצגת תעודה מזהה``
- Quantity floors that are not money: ``מינימום הזמנה הוא לזוג`` →
  minimum_purchase stays null.

## Worked example

Terms::

    הגבלות והחרגות כלליות (הכרטיס הנטען):
    - לא כולל חנויות עודפים
    - הכרטיס כולל כפל מבצעים והנחות (גם בסוף עונה) לא כולל הנחות חברי מועדון וצבירת נקודות של הרשת
    - הכסף הנטען אינו מיועד לרכישה באתרי הרשתות המופיעות ברשימה, אלא רק בסניפי הרשתות
    - לא ניתן לרכוש כרטיסי גיפט כארד באמצעות הכרטיס הנטען

    מגבלות ספציפיות לרשת ACE:
    - אין כפל הנחות מועדונים.
    - לא כולל : אתר הסחר האלקטרוני, שטיחים, אלקטרוניקה, מוצרי LIMITED.
    - סכום מקסימלי למימוש בעסקה- 500 ₪

    ניתן לטעון עד 1000 ₪ לחודש דרך ארנק "רשתות בהצדעה 15%" ולקבל 15% הנחה, לשימוש ברשת ACE.

Correct output::

    {"combinability": {"stackable_with_store_sale": "yes",
                       "stackable_with_member_discounts": "no",
                       "stackable_with_coupons": "unknown",
                       "stackable_with_payment_discounts": "unknown",
                       "stackable_with_giftcards": "no",
                       "stackable_with_cashback": "no"},
     "limits": {"max_uses_per_transaction": null,
                "max_uses_per_month": null,
                "minimum_purchase": null},
     "store_coverage": {"is_include_outlets_stores": "no",
                        "is_include_online_stores": "no",
                        "is_include_physical_stores": "yes"},
     "eligibility": {"membership_required": "yes",
                     "payment_method_required": "Behatsdaa prepaid wallet"}}

Note what is absent: the 500 ₪ ceiling, the 1000 ₪ monthly load cap, and the
excluded product categories produce no numbers at all.
"""


# Keyed by ``source_id`` as registered in ``scraping/registry.py``.
_SOURCE_PROMPTS: dict[str, str] = {
    "behatsdaa": _BEHATSDAA_PROMPT,
}


_FINAL_REMINDER = """\
## Final Reminder

- Return ONLY the JSON object. No ```json fences, no explanations.
- Every field must be present. Validate that your output is parseable JSON before returning.
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_system_prompt(source_id: str | None = None) -> str:
    """Assemble the system prompt, adding *source_id*'s terminology block.

    An unknown or missing ``source_id`` yields base + reminder, so a new
    scraper works before anyone writes a block for it.
    """
    source_block = _SOURCE_PROMPTS.get(source_id or "")
    parts = [_BASE_SYSTEM_PROMPT, source_block, _FINAL_REMINDER]
    return "\n".join(p for p in parts if p)


def supported_source_prompts() -> tuple[str, ...]:
    """Source ids that have their own terminology block."""
    return tuple(sorted(_SOURCE_PROMPTS))


def parse_deal_constraints(deal_terms: str, source_id: str | None = None) -> DealConstraints:
    """Parse Hebrew deal terms and conditions into structured constraint data.

    The LLM emits yes/no/unknown enums; the result is converted into the
    boolean public :class:`DealConstraints` schema (True / False / "unknown"
    for tri-state fields, positive-int or None for limits).

    Args:
        deal_terms: The raw Hebrew terms text.
        source_id: Scraper source the deal came from. Selects that source's
            terminology block; ``None`` or unknown falls back to the generic
            prompt.
    """
    logger.debug(
        "Parsing deal constraints (%d chars, source=%s)", len(deal_terms), source_id or "generic"
    )

    client, model = _get_client()
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": build_system_prompt(source_id)},
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

    Each deal's ``source_id`` (when present) selects that source's terminology
    block; pass one explicitly as the second argument to override it, which is
    the quickest way to A/B a source block against the generic prompt::

        python -m lessley_deals.enrichment.constaints_parser deal.json behatsdaa

    Constraints are written into a top-level "constraints" field on each deal
    object and the file is saved in-place.
    """
    load_dotenv()

    if len(sys.argv) < 2:
        print(
            "Usage: python -m lessley_deals.enrichment.constaints_parser "
            "<path/to/deal.json> [source_id]"
        )
        print(f"Sources with their own prompt block: {', '.join(supported_source_prompts())}")
        sys.exit(1)

    path = sys.argv[1]
    source_override = sys.argv[2] if len(sys.argv) > 2 else None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    is_list = isinstance(data, list)
    deals = data if is_list else [data]

    for deal in deals:
        terms = deal.get("terms_and_conditions")
        if not terms:
            print(f"Skipping deal (no terms_and_conditions): {deal.get('title') or deal.get('id', '?')}")
            continue

        source_id = source_override or deal.get("source_id")
        print(f"Parsing deal: {deal.get('title') or deal.get('deal_description') or deal.get('id', '?')}")
        print(f"Source: {source_id or 'generic'}")
        print(f"Terms ({len(terms)} chars):\n{terms}\n")

        result = parse_deal_constraints(terms, source_id)
        deal["constraints"] = result.model_dump()

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Done. Constraints written in-place to: {path}")


if __name__ == "__main__":
    main()
