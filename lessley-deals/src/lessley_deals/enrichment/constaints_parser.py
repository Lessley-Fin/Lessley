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


_HOT_PROMPT = """\
# SOURCE-SPECIFIC RULES — HOT / מועדון הוט (credit-card club)

These rules OVERRIDE the generic guidance above wherever the two disagree.

## What this source is

מועדון הוט is a credit-card club. Membership is expressed through a
club-linked credit card (``כרטיס אשראי המשויך למועדון הוט`` — issued as
``ישראכרט הוט`` or ``אמריקן אקספרס הוט``), so nearly every deal implies both
``membership_required: yes`` and a ``payment_method_required``. Three different
instruments appear, and they need different readings:

### 1. Statement-credit discount (by far the most common)

    ההנחה בחיוב תינתן אוטומטית למשלמים בכרטיס אשראי המשויך למועדון הוט,
    במעמד חיוב החשבון. הנחה זו ניתנת על הסכום המשולם בפועל בכרטיס האשראי.
    את ההנחה ניתן יהיה לראות בפרטי חיוב כרטיס האשראי (סטייטמנט) ...

This text describes HOW the discount is applied — as a credit on the card
statement rather than at the register. It prohibits NOTHING. Resolve it as:

- membership_required: yes
- payment_method_required: "HOT club-linked credit card"
- every combinability field: "unknown" (silence, not prohibition)
- every store_coverage field: "unknown" — the statement credit follows the
  card, not a store type. ``במעמד חיוב החשבון`` and ``בקופה`` describe when the
  discount lands; neither says branches are in or out.
- all three numeric limits: null

``יש לשלם באמצעות כרטיס האשראי של מועדון הוט: ישראכרט הוט ו/או אמריקן אקספרס
הוט`` → payment_method_required: "HOT club credit card (Isracard HOT or
American Express HOT)", membership_required: yes.

### 2. Swish digital voucher (``תו דיגיטלי``)

Opens with ``רכישת תו דיגיטלי בהנחה של X% באתר מועדון הוט``. The member buys a
discounted voucher on the club's website and redeems it at the merchant.

- ``באתר מועדון הוט`` is where the voucher is BOUGHT. It says nothing about the
  merchant's own web shop — leave is_include_online_stores "unknown".
- ``התו תקף בישיבה בלבד`` → is_include_physical_stores: yes
- ``לא תקף ב-TA ומשלוחים`` → NO field. Take-away and delivery are not "online
  stores"; do not touch is_include_online_stores for them.
- ``ההטבה אינה תקפה למבצעים`` → stackable_with_store_sale: no
- membership_required: yes; payment_method_required: "HOT club-linked credit
  card" (``יש לשלם בכרטיס אשראי המשויך למועדון הוט``).

### 3. HOTsave cashback (``הוטsave``)

An affiliate cashback service reached through a portal
(``בכל רכישה עוברים דרך הוטsave``). Registration is required
(``השירות מותנה בהרשמה מראש``) → membership_required: yes. The rest is
operational mechanics with no field — record nothing for it.

## Limits — a per-member cap is never per-TRANSACTION (read this twice)

HOT's most common numeric phrase caps how many vouchers a MEMBER may buy,
identified by ID number. Decide by the TIME WINDOW attached to it:

**No time window → all three numeric fields null.** The schema has no
"per member, ever" field, and this is NOT a per-transaction count:

- ``מוגבל לתו 1 לעמית מועדון (ת.ז.)`` · ``מוגבל ל-5 תווים לעמית מועדון (ת.ז.)``
- ``מוגבל ל-2 תווים לחבר מועדון``

**A monthly window → max_uses_per_month.** ``לעמית``/``לחבר מועדון`` says who
the quota belongs to; ``בחודש`` says how often it refills, and that IS the
field:

- ``מוגבל ל-2 קופונים לעמית בחודש`` → max_uses_per_month: 2
- ``ניתן לממש עד 12 תווים לחבר מועדון בחודש קלנדרי`` → max_uses_per_month: 12
- ``תקף לקופון 1 לעמית (ת.ז.) בחודש`` → max_uses_per_month: 1

max_uses_per_transaction still requires the count to be scoped to a single
purchase (``בעסקה``, ``בקנייה``, ``לשולחן``) — a per-member quota never fills
it, with or without a month.

A percentage in the opening line (``בהנחה של 15%``) is the deal's discount
rate, never minimum_purchase.

## Has no field — do NOT force these anywhere

- Meal/timing: ``לא כולל ארוחות עסקיות`` · ``ארוחות בראש השנה האזרחית`` ·
  ``אינו תקף בחגים וחול המועד`` · ``ללא happy hours`` · ``ארוחת בוקר ... בהתאם
  לשעות בהן מוגשת``
- Audience: ``ההטבה אינה מיועדת לקבוצות ואירועים``
- Kashrut: ``כשרות על פי הצהרת בית העסק``
- Payment detail: ``לא ניתן לשלם את הטיפ (תשר) באמצעות קוד ההטבה``
- Boilerplate: ``מימוש ההטבה בכפוף לתנאים והגבלות באתר בית העסק`` ·
  ``בכפוף לתנאי התקנון`` · ``מומלץ ליצור קשר עם בית העסק טרם ההגעה``
- Delivery mechanics: ``יתקבל מסרון עם קוד למימוש``

## Worked example

Terms::

    ההנחה בחיוב תינתן אוטומטית למשלמים בכרטיס אשראי המשויך למועדון הוט, במעמד
    חיוב החשבון. הנחה זו ניתנת על הסכום המשולם בפועל בכרטיס האשראי.

Correct output::

    {"combinability": {"stackable_with_store_sale": "unknown",
                       "stackable_with_member_discounts": "unknown",
                       "stackable_with_coupons": "unknown",
                       "stackable_with_payment_discounts": "unknown",
                       "stackable_with_giftcards": "unknown",
                       "stackable_with_cashback": "unknown"},
     "limits": {"max_uses_per_transaction": null,
                "max_uses_per_month": null,
                "minimum_purchase": null},
     "store_coverage": {"is_include_outlets_stores": "unknown",
                        "is_include_online_stores": "unknown",
                        "is_include_physical_stores": "unknown"},
     "eligibility": {"membership_required": "yes",
                     "payment_method_required": "HOT club-linked credit card"}}
"""


_HEVER_SHARED = """\
## What this source is

``חבר`` is a closed members' organisation. The benefit is a **loadable prepaid
card** (``כרטיס "חבר" הנטען``): the member loads money and receives a tiered
percentage off the load, then spends the balance at the accepting chain. The
card and the payment method are the same object.

Always true for this source:
- membership_required: yes — only a חבר member can load the card.
- stackable_with_payment_discounts: "unknown" unless the text says otherwise.

## The tiered-load sentence is ECONOMICS, not a restriction

Nearly every deal ends with some version of::

    ניתן לטעון כרטיס "חבר" הנטען ולקבל 30% הנחה על טעינת 1,000 ₪ ראשונים,
    25% הנחה על 1,000 ₪ הבאים ו-20% הנחה על 1,000 ₪ נוספים (עד 3,000 ₪ בסה"כ),
    לשימוש ברשת <chain>.

Every number in it is a load tier or a load ceiling. Read it ONLY for the chain
name. It never produces minimum_purchase, never max_uses_per_month, never
max_uses_per_transaction.

## Shekel ceilings are NOT limits

- ``עד 1,000 ש"ח לעסקה`` · ``ניתן לשלם עד 1000 ₪ לעסקה`` ·
  ``רכישה בכרטיס הנטען עד 1,000 ₪``

A shekel amount caps how much may be SPENT. minimum_purchase is a floor the
customer must reach — the opposite. max_uses_* count cards or vouchers, not
shekels. All of these → all three numeric fields null.

## Stacking

- ``לא כולל כפל הנחות מועדון הרשת`` / ``לא כולל כפל הנחות מועדון`` →
  stackable_with_member_discounts: no
- ``כולל כפל מבצעים`` → stackable_with_store_sale: yes
- Silence on a kind of stacking → "unknown" (stored as stackable).
"""


_HEVER_GIFT_CARD_PROMPT = (
    """\
# SOURCE-SPECIFIC RULES — חבר / Hever gift card (loadable card)

These rules OVERRIDE the generic guidance above wherever the two disagree.

"""
    + _HEVER_SHARED
    + """
payment_method_required: "Hever loadable club card".

Store coverage is usually unstated on this source — leave all three
"unknown" unless the text names branches, an outlet, or a web shop.

## Worked example

Terms::

    לא כולל כפל הנחות מועדון הרשת, רכישה בכרטיס הנטען עד 1,000 ₪
    ניתן לטעון כרטיס "חבר" הנטען ולקבל 30% הנחה על טעינת 1,000 ₪ ראשונים,
    25% הנחה על 1,000 ₪ הבאים ו-20% הנחה על 1,000 ₪ נוספים (עד 3,000 ₪ בסה"כ),
    לשימוש ברשת 4chef.

Correct output — note that NO number survives::

    {"combinability": {"stackable_with_store_sale": "unknown",
                       "stackable_with_member_discounts": "no",
                       "stackable_with_coupons": "unknown",
                       "stackable_with_payment_discounts": "unknown",
                       "stackable_with_giftcards": "unknown",
                       "stackable_with_cashback": "unknown"},
     "limits": {"max_uses_per_transaction": null,
                "max_uses_per_month": null,
                "minimum_purchase": null},
     "store_coverage": {"is_include_outlets_stores": "unknown",
                        "is_include_online_stores": "unknown",
                        "is_include_physical_stores": "unknown"},
     "eligibility": {"membership_required": "yes",
                     "payment_method_required": "Hever loadable club card"}}
"""
)


_HEVER_TEAMIM_PROMPT = (
    """\
# SOURCE-SPECIFIC RULES — חבר טעמים / Hever Teamim (loadable restaurant card)

These rules OVERRIDE the generic guidance above wherever the two disagree.

"""
    + _HEVER_SHARED
    + """
payment_method_required: "Hever Teamim loadable card".

## Dining terms (this source is restaurants)

- ``ישיבה במסעדה`` / ``תקף בישיבה בלבד`` → is_include_physical_stores: yes.
  Leave is_include_online_stores and is_include_outlets_stores "unknown" — a
  restaurant deal that is silent about a web shop has not excluded one.
- ``לא תקף במשלוחים`` · ``TAKE AWAY`` · ``לא כולל עסקיות`` ·
  ``לא תקף בשעות happy hour`` → NO field. Delivery and take-away are service
  channels, not online stores.
- ``מינימום הזמנה הוא לזוג`` → a party-size floor, not money → minimum_purchase
  stays null.
"""
)


_PAISPLUS_PROMPT = """\
# SOURCE-SPECIFIC RULES — פיס פלוס / Pais Plus (gift voucher)

These rules OVERRIDE the generic guidance above wherever the two disagree.

## What this source is

Pais Plus sells a **gift voucher** (``תו קנייה``), delivered as a digital code
and spent at the chain. Unlike a loadable wallet, the voucher is a countable
object — so genuine per-transaction counts DO appear here and must be captured.

## Stacking

- ``כולל כפל מבצעים והנחות`` → stackable_with_store_sale: yes. The source often
  ships this with a missing space (``כולל כפלמבצעים והנחות``) — read it the same
  way. A carve-out such as ``פרט למבצע 1+1 חינם`` does not change it: still
  "yes", and the 1+1 exclusion has no field.
- ``לא ניתן למימוש במקביל להטבות ו/או מבצעי מועדון`` /
  ``לא כולל מבצעי מועדון`` → stackable_with_member_discounts: no
- ``לא ניתן לרכוש כרטיס מתנה/גיפט קארד באמצעות התו`` →
  stackable_with_giftcards: no

## Store coverage

- ``ניתן למימוש בסניפים`` / ``ניתן למימוש לישיבה בסניפים או לאיסוף עצמי`` /
  ``בקופות הסניפים`` → is_include_physical_stores: yes
- ``לא ניתן למימוש באתרי הסחר`` / ``לא ניתן למימוש באתר הסחר`` /
  ``לא ניתן למימוש באתר`` / ``לא כולל אתר סחר`` (incl. named sites such as
  ``לרבות טרמינל X``) → is_include_online_stores: no
- ``לא ניתן למימוש בחנויות עודפים ו/או ברכישת פרטי עודפים`` →
  is_include_outlets_stores: no
- ``לא ניתן למימוש בסניפי נתב"ג`` → a NAMED branch exclusion. No field — it
  does not make physical stores excluded.

## Limits — count vouchers, not shekels

Genuine counts DO map here:
- ``ניתן לממש עד 2 תווי קנייה בעסקה אחת`` → max_uses_per_transaction: 2
- ``ניתן לממש תו אחד בלבד בעסקה`` → max_uses_per_transaction: 1

Shekel ceilings do NOT:
- ``ניתן לממש את תווי הקנייה בסכום של עד 2000 ₪ לעסקה`` → all numeric null.
  This caps the amount spent, not the number of vouchers.

``ניתן לפצל את התו למספר רכישות`` (the voucher may be spent across several
purchases) is a convenience, not a limit → no field.

## Has no field

``לא תקף במשלוחים`` · ``לא ניתן לשלם בקופות עצמיות`` ·
``לא כולל אלכוהול וסיגריות`` · ``לא כולל שטיחים / מוצרי LIMITED / אלקטרוניקה``
· ``יש לרכוש תו ייעודי לסניף הרלוונטי`` · ``הסניפים המכבדים את ההטבה: ...`` ·
``התו לא ניתן להמרה למזומן`` · ``בכפוף למלאי`` · ``גניבה/אובדן/השחתה`` ·
``האחריות על טיב המוצרים`` · issuer names (``מנפיק התו: ...``) ·
allergen notices.
"""


_PAISPLUS_NETWORKS_PROMPT = """\
# SOURCE-SPECIFIC RULES — פיס פלוס רשתות אונליין (loadable, online-first)

These rules OVERRIDE the generic guidance above wherever the two disagree.

## What this source is

A **loadable** Pais Plus voucher for chains whose redemption is primarily
online. The closing sentence — ``ניתן לטעון ולקבל 25% הנחה על טעינת 600 ₪
ראשונים ו-15% הנחה על טעינת 900 ₪ הנוספים (עד 1500 ₪ בסה"כ), לשימוש ברשת
<chain>`` — is the deal's economics. Read it only for the chain name; every
number in it is a load tier or load ceiling → all three numeric fields null.

## Store coverage — this source usually EXCLUDES branches (note the direction)

- ``ניתן למימוש באתר ובאפליקציה`` → is_include_online_stores: yes
- ``ניתן למימוש באתר בלבד`` → is_include_online_stores: yes AND
  is_include_physical_stores: no
- ``לא ניתן למימוש בסניפים`` → is_include_physical_stores: no

Do not carry over the assumption from branch-based sources that a voucher
implies physical stores. Here the default instrument is the web shop.

- ``ובהזמנות טלפוניות`` excluded → no field (phone orders are not a store type).

## Stacking

``כולל כפל מבצעים והנחות`` → stackable_with_store_sale: yes.

## Has no field

``לא ניתן להמרה למזומן`` · ``לא ניתן לשלם את עלות המשלוח באמצעות התו`` ·
``לא ניתן לפצל תשלום / לשלם באמצעי תשלום נוסף`` ·
``יש לוודא שהתו טעון בסכום גבוה יותר משווי העסקה``.

That last one is a usage instruction, NOT minimum_purchase — it compares the
voucher balance to the basket, and imposes no spend floor on the customer.
"""


_PAISPLUS_FOOD_PROMPT = """\
# SOURCE-SPECIFIC RULES — פיס פלוס רשתות מזון (loadable supermarket card)

These rules OVERRIDE the generic guidance above wherever the two disagree.

## What this source is

A **loadable** Pais Plus voucher for supermarket chains, spent at the register.
The closing ``ניתן לטעון ולקבל 7.5% הנחה על טעינת 400 ₪ ראשונים ו-5% הנחה על
טעינת 1800 ₪ הנוספים (עד 2200 ₪ בסה"כ), לשימוש ברשת <chain>`` is economics —
read it only for the chain name, and produce no numbers from it.

## Store coverage

- ``לא כולל אתר סחר`` / ``לא כולל אתר הסחר האלקטרוני`` →
  is_include_online_stores: no
- The deal is redeemed at the register, so ``ניתן לשלם בקופה`` /
  ``בקופות הסניפים`` → is_include_physical_stores: yes. Absent any such phrase,
  leave it "unknown".

## Has no field — the recurring supermarket exclusions

- ``לא ניתן לשלם בקופות עצמיות`` — self-checkout is a register type, not a
  store type. Do NOT set is_include_physical_stores to "no" for it.
- ``לא כולל אלכוהול וסיגריות`` · ``לא כולל סיגריות ומוצרי טבק`` — product
  categories.
- ``לא ניתן לשלם בקופה בסכום העולה על הסכום הטעון בתו`` — you cannot spend more
  than the card holds. Not a limit, not a minimum. All numeric fields null.
- ``או להעביר סכומי טעינה מרשת לרשת`` — balances are not transferable between
  chains.
"""


_MASTERCARD_PROMPT = """\
# SOURCE-SPECIFIC RULES — Mastercard (card-issuer promotion)

These rules OVERRIDE the generic guidance above wherever the two disagree.

## What this source is

A promotion tied to paying with a Mastercard credit card. **Mastercard is a
payment network, not a members' club** — so a requirement to pay with the card
sets payment_method_required WITHOUT implying club membership.

- ``תקף למשלמים בכרטיס אשראי מאסטרקארד`` /
  ``בלעדי למשלמים בכרטיס אשראי מאסטרקארד`` →
  payment_method_required: "Mastercard credit card",
  membership_required: "unknown" (NOT "yes" — no club is named).
- Only set membership_required: yes if the text names a customers' club the
  shopper must belong to.

## Calendar dates are NOT monthly usage limits (read this twice)

This source's signature phrase is a day-of-month window:

- ``המבצע תקף באתר ב-10 בחודש בלבד`` · ``תקף ב-10 וב-11 בחודש בלבד`` ·
  ``ההטבה תקפה ב-10 וב-11 בחודש``

``ב-10 בחודש`` is the 10th DAY of the month — a date on which the offer runs,
not a count of permitted uses. max_uses_per_month stays **null**. The schema
models no validity window; record nothing for it.

Percentages (``25% הנחה``, ``18% הנחה``) are the discount rate, never
minimum_purchase.

## Stacking

- ``כולל כפל מבצעים`` → stackable_with_store_sale: yes
- ``לא כולל כפל הנחות ומבצעים למועדוני לקוחות`` /
  ``לא כולל כפל מבצעים והנחות למועדוני לקוחות`` →
  stackable_with_member_discounts: no
- ``לא כולל כפל מבצעים`` (no qualifier about clubs) →
  stackable_with_store_sale: no

## Store coverage

- ``בתוקף על כל הפריטים באתר ובחנויות`` / ``תקף באתר ובחנויות`` →
  is_include_online_stores: yes AND is_include_physical_stores: yes
- ``תקף באתר בלבד`` → online yes, physical no

## Has no field

``קוד קופון: MASTERCARDAY`` (a coupon code is not a constraint) ·
``התמונה להמחשה בלבד`` · ``בכפוף לתקנון המלא`` · ``לתקנון`` ·
``מתן ההטבה וטיב המוצרים באחריות בית העסק בלבד`` · product carve-outs such as
``לא כולל חבילת Cruise``.
"""


_TOPCASH_PROMPT = """\
# SOURCE-SPECIFIC RULES — TopCash / טופקאש (online cashback affiliate)

These rules OVERRIDE the generic guidance above wherever the two disagree.

## What this source is

TopCash is a cashback affiliate: the shopper registers, reaches an online store
through TopCash (a browser extension or a click-through), buys there, and gets
cashback credited later. The "deal" is the cashback rate at that store.

Known facts for this source — apply them unless the text contradicts:
- membership_required: **yes** — cashback requires a TopCash account and going
  through TopCash (``יש להתחיל את תהליך הקנייה דרך TopCash`` /
  ``בצעו מעבר לחנות דרך TopCash``).
- payment_method_required: null — TopCash requires no particular instrument.

## store_coverage is FIXED for this source — do not read it from the text

TopCash is ONLINE-ONLY. The cashback exists only because TopCash tracks the
click from its own site into the merchant's web shop and is paid an affiliate
commission on that tracked online order. A purchase made at a physical counter
carries no tracking link, so it can never earn cashback — no matter what the
merchant's branches, chain size, or store network look like.

Therefore, for EVERY TopCash deal, always emit exactly:

    "store_coverage": {"is_include_outlets_stores": "no",
                       "is_include_online_stores": "yes",
                       "is_include_physical_stores": "no"}

These three values are CONSTANT. They are not a judgement call, they are not
read from the terms, and they do not depend on the merchant. Copy them verbatim
into every TopCash answer.

This OVERRIDES the generic rules above, specifically:
- It overrides "use 'unknown' when the text is silent". Silence is NOT unknown
  here: the channel is already known from the source. Never emit "unknown" for
  any of the three store_coverage fields on a TopCash deal.
- It overrides "'no' requires an explicit prohibition". The prohibition is
  structural — no tracked click, no cashback — so "no" is correct for physical
  and outlet stores even when the terms never mention them.

### Text that must NOT change these values

TopCash descriptions are marketing copy about the BRAND, and they routinely
mention the chain's physical shops. That is background about the merchant, not
the redemption channel of this cashback deal. Ignore it for store_coverage:

- ``רשת חנויות החשמל ... אשר בבעלותה יותר מ-40 סניפים ברחבי הארץ עכשיו גם
  באינטרנט`` → still physical: "no". The 40 branches are the brand's; the
  cashback is on the web shop that the same sentence ends with.
- ``העסק התחיל את דרכו בסניף קטן ברמת גן`` → company history → still
  physical: "no".
- ``מגוון הצעצועים המוצע בחנויות עומד בכל התקנים`` → product blurb → still
  physical: "no".
- ``התוסף לא עובד בחנות זו, יש להתחיל את תהליך הקנייה דרך TopCash`` →
  "חנות" here means the merchant's ONLINE shop as listed on TopCash, and the
  sentence is about extension tracking → still online: "yes", physical: "no".
- Travel and booking merchants: ``אין קאשבק עבור הזמנות דרך סוכן או צד שלישי``
  excludes agents/offices, which only reinforces online: "yes",
  physical: "no". It is not a reason to emit "unknown".
- A title of the form ``X% קאשבק באתר <brand>`` ("cashback on the WEBSITE of
  <brand>") is the normal shape of every deal here and confirms the constant.

There is no TopCash deal that is redeemable in a branch. If you believe you
found one, you have misread brand copy as redemption terms — emit the constant.

## What DOES map (things that block the cashback)

The terms are a list of what forfeits the cashback. Where such an exclusion
lines up with a schema field, use it:

- ``אין קאשבק על תשלום באמצעות Credit / נקודות מועדון`` →
  stackable_with_payment_discounts: no
- ``רכישות שנעשו באמצעות גיפטקארד`` / ``רכישות של ובאמצעות כרטיסי מתנה``
  excluded → stackable_with_giftcards: no
- ``שימוש בקופונים חיצוניים שלא סופקו על ידי TopCash עלול למנוע קבלת קאשבק`` /
  ``שימוש בקודים וקופונים חיצוניים ... עלול למנוע`` → stackable_with_coupons: no
- ``מוצרים מקטגוריית "Daily Deals" שנרכשו כחלק מעסקת קידום מכירות`` excluded →
  stackable_with_store_sale: no

## Has no field — the cashback plumbing

This source is dense with tracking mechanics. Record nothing for them, and in
particular never turn a waiting period or a percentage into a number:

- Timing of payout: ``הקאשבק הופך לזמין כ-90 ימים לאחר מימוש ההזמנה`` ·
  ``ימי ההמתנה לאישור הקאשבק, כ-130 ימים``. These are days, not limits →
  max_uses_per_month stays null.
- Tracking mechanics: ``הפעילו קאשבק בתוסף`` · ``התוסף לא עובד בחנות זו`` ·
  ``יש לבצע הזמנה במסגרת הפעלה אחת (ביקור רציף באתר ללא שיטוט בדפי אינטרנט
  חיצוניים)`` · ``מומלץ לבצע מעבר במצב מחובר``
- Rate uncertainty: ``מספקים אחוז משתנה של קאשבק ... ולכן לא ניתן לדעת במדויק
  את גובה הקאשבק``
- Support policy: ``לא ניתן לשלוח לבדיקה הזמנות עם קאשבק חסר`` ·
  ``כל שינוי בהזמנה קיימת עלול למנוע אישור הקאשבק``
- Channel/scope detail: ``קניות שנעשות דרך האפליקציה`` ·
  ``אין קאשבק עבור הזמנות דרך סוכן או צד שלישי`` ·
  ``קאשבק ינתן על הזמנת מקומות אירוח בלבד`` ·
  ``קאשבק מחושב מעלות המגורים בלבד ללא מסים, דמי שירות, מע"מ``

## Worked example 1

Terms::

    תנאים לקבלת הקאשבק • אין קאשבק על תשלום באמצעות Credit / נקודות מועדון.

Correct output::

    {"combinability": {"stackable_with_store_sale": "unknown",
                       "stackable_with_member_discounts": "unknown",
                       "stackable_with_coupons": "unknown",
                       "stackable_with_payment_discounts": "no",
                       "stackable_with_giftcards": "unknown",
                       "stackable_with_cashback": "unknown"},
     "limits": {"max_uses_per_transaction": null,
                "max_uses_per_month": null,
                "minimum_purchase": null},
     "store_coverage": {"is_include_outlets_stores": "no",
                        "is_include_online_stores": "yes",
                        "is_include_physical_stores": "no"},
     "eligibility": {"membership_required": "yes",
                     "payment_method_required": null}}

## Worked example 2 — brand copy that names branches

Terms::

    1.5% קאשבק באתר A.L.M | א.ל.מ — רשת חנויות החשמל והאלקטרוניקה המוכרת
    והאהובה אשר בבעלותה יותר מ-40 סניפים ברחבי הארץ, עכשיו גם באינטרנט.
    יש להתחיל את תהליך הקנייה דרך TopCash.

store_coverage is UNCHANGED — the 40 branches belong to the brand, not to this
cashback deal::

    {"combinability": {"stackable_with_store_sale": "unknown",
                       "stackable_with_member_discounts": "unknown",
                       "stackable_with_coupons": "unknown",
                       "stackable_with_payment_discounts": "unknown",
                       "stackable_with_giftcards": "unknown",
                       "stackable_with_cashback": "unknown"},
     "limits": {"max_uses_per_transaction": null,
                "max_uses_per_month": null,
                "minimum_purchase": null},
     "store_coverage": {"is_include_outlets_stores": "no",
                        "is_include_online_stores": "yes",
                        "is_include_physical_stores": "no"},
     "eligibility": {"membership_required": "yes",
                     "payment_method_required": null}}
"""


# Keyed by ``source_id`` as registered in ``scraping/registry.py``.
_SOURCE_PROMPTS: dict[str, str] = {
    "behatsdaa": _BEHATSDAA_PROMPT,
    "hot": _HOT_PROMPT,
    "hever_gift_card_company": _HEVER_GIFT_CARD_PROMPT,
    "hever_teamim_card_store": _HEVER_TEAMIM_PROMPT,
    "paisplus": _PAISPLUS_PROMPT,
    # The cash-card programs are split by membership tier into one source_id
    # each (see scraping/sources/paisplus_cashcards.py). The terms text is
    # identical across tiers -- only the bracket numbers differ -- so both tiers
    # of a program share its block. Without these entries the new source_ids
    # would silently fall back to the generic prompt.
    "paisplus_networks_regular": _PAISPLUS_NETWORKS_PROMPT,
    "paisplus_networks_vip": _PAISPLUS_NETWORKS_PROMPT,
    "paisplus_food_chains_regular": _PAISPLUS_FOOD_PROMPT,
    "paisplus_food_chains_vip": _PAISPLUS_FOOD_PROMPT,
    "mastercard": _MASTERCARD_PROMPT,
    "topcash": _TOPCASH_PROMPT,
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
