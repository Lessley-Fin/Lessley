"""Refine ``constraints`` on the seeded deals.

The enrichment LLM fills ``Deal.constraints`` one deal at a time, so the same
boilerplate paragraph — Israeli sources reuse a handful of them verbatim across
thousands of deals — occasionally comes out different on one deal than on the
two thousand others carrying identical text. This pass re-reads the Hebrew terms
with deterministic rules and rewrites only the fields the text settles
unambiguously, plus fills in constraints on deals that never got any.

Design notes
------------
* Combinability is only ever *tightened* (``True`` → ``False``) and only on an
  explicit prohibition, matching the parser's optimistic default. A clause that
  permits a kind of stacking anywhere in the same terms vetoes the tightening —
  sources routinely state a general rule and then a network-specific override.
* Hebrew nouns are spelled out in full for both numbers rather than suffixed
  with ``?``. A quantifier inside a Hebrew word is both unreadable under bidi
  and wrong: the final letter form changes with the suffix (מועדון → מועדונים),
  so ``מועדון(ים)?`` never matches the plural.

Usage::

    python scripts/refine_deal_constraints.py --dry-run      # report only
    python scripts/refine_deal_constraints.py --self-test    # check the rules
    python scripts/refine_deal_constraints.py                # rewrite the seed
"""

from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path
from typing import Any

SEED = Path(__file__).resolve().parents[1] / "data" / "seed" / "deals.json"


def _any(*words: str) -> str:
    """A non-capturing alternation over full words (longest first)."""
    return "(?:" + "|".join(sorted(words, key=len, reverse=True)) + ")"


# --- "כפל …" clause vocabulary --------------------------------------------

# Prohibition vs. permission openers. Kept apart, and the permission opener
# carries a lookbehind, so "לא כולל כפל מבצעים" is never read as a permission.
_NEG = _any("אין", "ללא", "לא כולל", "לא ניתן", "אינו כולל", "אינה כוללת", "לא תקף")
_POS = _any("כולל", "כוללת", "ניתן", "תקף")
_NEG_LOOKBEHIND = "".join(f"(?<!{word} )" for word in ("לא", "אינו", "אינה", "ללא"))

# What follows "כפל" — the kinds of discount the clause is about.
_KINDS = {
    "store_sale": _any("מבצעים", "מבצעי", "מבצע", "הטבות", "הטבת", "הנחות", "הנחה", "הנחת"),
    "coupons": _any("קופונים", "קופון"),
    "member": _any("מועדונים", "מועדוני", "מועדון"),
    "giftcards": _any("שוברים", "שובר", "גיפט", "כרטיסים דיגיטליים") + r"|תוו?י\s*" + _any("שי", "קניה", "קנייה"),
    "cashback": _any("צבירה", "צבירת", "קאשבק") + r"|קאש\s*בק",
}

# "הנחות מועדונים" is a single compound noun — a *club* discount — not "הנחות"
# (a store sale) alongside "מועדון". Matched and stripped first so the generic
# scan below cannot read it as a blanket store-sale prohibition.
_DISCOUNT_NOUN = _any("הנחות", "הנחת", "הטבות", "הטבת", "מבצעים", "מבצעי")
_MEMBER_COMPOUND = re.compile(
    rf"{_DISCOUNT_NOUN}\s*(?:עם\s*|של\s*|ל)?(?:חברי\s*)?{_any('מועדונים', 'מועדוני', 'מועדון')}"
    rf"|ל?חברי\s*מועדון"
)

# "אין כפל הטבות לעובדים/בני משפחה" is an HR rule about who may claim a staff
# perk, not a retail-promotion rule. It shares the word "הטבות" with a real
# store-sale prohibition, so clauses about it are dropped whole.
_STAFF_PERK = re.compile(_any("לעובדים", "עובדים", "בני משפחה", "בן משפחה"))

# Several sources emit one long ``<br/>``-separated blob with no periods, so the
# tail has to stop at the markup and at the sentence that starts describing the
# offer itself ("ניתן לטעון כרטיס … ולקבל 30% הנחה") — otherwise that sentence's
# stray "הנחה" reads as part of the prohibition.
_CLAUSE_TAIL = r"[^\n.<]{0,80}"
_TAIL_STOP = re.compile(r"<br|[*•·]|" + _any("ניתן לטעון", "ניתן לרכוש", "ניתן לממש", "ולקבל"))

_COMB_KEY = {
    "store_sale": "stackable_with_store_sale",
    "coupons": "stackable_with_coupons",
    "member": "stackable_with_member_discounts",
    "giftcards": "stackable_with_giftcards",
    "cashback": "stackable_with_cashback",
}


def _clauses(text: str, opener: str) -> list[str]:
    """Every "<opener> כפל <tail>" clause in ``text``, tail only."""
    lookbehind = _NEG_LOOKBEHIND if opener is _POS else ""
    return re.findall(rf"{lookbehind}{opener}\s*כפל\s*({_CLAUSE_TAIL})", text)


def _kinds_in(tail: str) -> set[str]:
    """Which discount kinds a "כפל …" clause names.

    Only the head of the tail counts: in "אין כפל מבצעים ולא כולל מופעים
    חיצוניים" the second half is a separate restriction riding along, so the
    tail is cut at the first opener that starts a new clause.
    """
    tail = re.split(rf"\s(?:{_NEG})\s", tail)[0]
    tail = _TAIL_STOP.split(tail)[0]
    if _STAFF_PERK.search(tail):
        return set()
    found: set[str] = set()
    if _MEMBER_COMPOUND.search(tail):
        found.add("member")
        tail = _MEMBER_COMPOUND.sub(" ", tail)
    for kind, pattern in _KINDS.items():
        if re.search(pattern, tail):
            found.add(kind)
    # The enrichment prompt's own rule: "כפל הנחות" with no qualifier left on it
    # (the club compound above is already stripped) is a blanket ban, covering
    # coupons as well as store sales.
    if re.search(_any("הנחות", "הנחה"), tail):
        found.add("coupons")
    return found


# --- redemption-channel vocabulary ----------------------------------------

# Only a clause about redeeming *the benefit* counts. "בטייק אווי - בהזמנה דרך
# האתר בלבד" restricts one sub-case (takeaway), while the deal itself is still
# good in the restaurant, so bare "דרך האתר בלבד" is deliberately not matched.
_WEB_ONLY = re.compile(
    r"(?:למימוש|מימוש|לרכישה|רכישה|תקפה?|ברישום)\s*"
    r"(?:ב|ה)?(?:אתר\s*(?:הסחר|האינטרנט|הספק)?|אונליין)\s*(?:האלקטרוני\s*)?בלבד"
)
_BRANCH_ONLY = re.compile(
    r"לא ניתן למימוש באתר|לא ניתן לממש באתר|למימוש בסניפים בלבד"
    r"|בסניפי הרשת בלבד|בסניפים בלבד|לא תקף באתר|אינו תקף באתר|לא כולל מימוש באתר"
)
_BRANCHES_OK = re.compile(r"ניתן למימוש בסניפים")
# "לא ניתן למימוש באתרי הסחר, למעט אתרי הסחר של קסטרו" excludes the web in
# general and then allows some of it — too partial for a boolean.
_EXCEPTION = re.compile(r"למעט|פרט ל|אלא אם|בחלק מ")
# Terms that also say "…באתר בלבד" contradict the branch-only reading; a boolean
# cannot hold both, so neither is asserted.
_WEB_ONLY_MENTION = re.compile(r"באתר בלבד|באתר האונליין בלבד|באתר הסחר בלבד")
_WEB_MENTION = re.compile(r"אתר|אונליין|online", re.IGNORECASE)

# The Behatsdaa loadable-card paragraph settles both coverage axes on its own:
# the loaded money is for the chains' branches, not for their websites.
_BEHATSDAA_CARD = "הכסף הנטען אינו מיועד לרכישה באתרי הרשתות"
_BEHATSDAA_SPECIFIC = re.compile(r"מגבלות ספציפיות לרשת[^\n]*\n(.*)", re.S)

# --- numeric limits stated in the terms ------------------------------------

_MONTHLY_QTY = re.compile(
    rf"כמות\s*{_any('תווים', 'שוברים', 'הטבות', 'כרטיסים')}\s*ללקוח\s*"
    rf"{_any('בחודש', 'לחודש')}\s*[-–:]?\s*(\d+)"
)
_MIN_PURCHASE = re.compile(r"לרכישה\s*ב\s*[-–]?\s*(\d[\d,]*)\s*₪?\s*ומעלה")

# --- payment_method_required canonicalisation ------------------------------
#
# The LLM writes this field as free text, so ~10 real instruments arrived under
# 60+ spellings ("Behatsdaa Networks 15% wallet", "Behatsdaa 'רשתות בהצדעה 15%'"
# and "Behatsdaa Rashot 15%" are one wallet). Collapsed so the value can be
# grouped, compared and shown to a user.

_BEHATSDAA_WALLET = "__behatsdaa_wallet__"  # resolved by headline percentage

_PAYMENT_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"fighter|payter|פייטר", re.I), "Behatsdaa Fighter card"),
    (re.compile(r"restaurant|מסעד", re.I), "Behatsdaa Restaurants 20% wallet"),
    (re.compile(r"food\s*(?:\+|&|and)?\s*online|מזון", re.I), "Behatsdaa Food & Online Sites 7% wallet"),
    (re.compile(r"behatsdaa|בהצדעה", re.I), _BEHATSDAA_WALLET),
    (re.compile(r"teamim|טעמים", re.I), "Hever Teamim loadable card"),
    (re.compile(r"hever|חבר", re.I), "Hever loadable club card"),
    (re.compile(r"mastercard", re.I), "Mastercard credit card"),
    (re.compile(r"isracard|american\s*express|amex|\bhot\b|הוט", re.I), "HOT club-linked credit card"),
]


# A value that describes a club card without naming the club ("club-linked credit
# card") is resolved from the deal's own source, which always names it.
_GENERIC_INSTRUMENT = re.compile(r"club|credit|מועדון|אשראי", re.I)
_SOURCE_INSTRUMENT = {
    "hot": "HOT club-linked credit card",
    "mastercard": "Mastercard credit card",
    "hever_teamim_card_store": "Hever Teamim loadable card",
    "hever_gift_card_company": "Hever loadable club card",
}


def canonical_payment(raw: str | None, source_id: str | None = None) -> str | None:
    """Collapse a free-text payment instrument onto the canonical vocabulary."""
    if not raw or not raw.strip():
        return None
    value = raw.strip()
    for pattern, canonical in _PAYMENT_RULES:
        if not pattern.search(value):
            continue
        if canonical is not _BEHATSDAA_WALLET:
            return canonical
        if "20" in value:
            return "Behatsdaa network wallet 20%"
        if "15" in value:
            return "Behatsdaa network wallet 15%"
        return "Behatsdaa prepaid wallet"
    if _GENERIC_INSTRUMENT.search(value) and source_id in _SOURCE_INSTRUMENT:
        return _SOURCE_INSTRUMENT[source_id]
    return value


# --- constraint templates for deals that carry none ------------------------


def empty_constraints() -> dict[str, Any]:
    """The parser's own all-unknown template (see ``enrichment.constaints_parser``)."""
    return {
        "combinability": {
            "stackable_with_store_sale": True,
            "stackable_with_member_discounts": True,
            "stackable_with_coupons": True,
            "stackable_with_payment_discounts": True,
            "stackable_with_giftcards": True,
            "stackable_with_cashback": True,
        },
        "limits": {
            "max_uses_per_transaction": None,
            "max_uses_per_month": None,
            "minimum_purchase": None,
        },
        "store_coverage": {
            "is_include_outlets_stores": "unknown",
            "is_include_online_stores": "unknown",
            "is_include_physical_stores": "unknown",
        },
        "eligibility": {"membership_required": "unknown", "payment_method_required": None},
    }


def _topcash_constraints() -> dict[str, Any]:
    """TopCash is an affiliate cashback site: you click through to the store's
    own website and the cashback lands in a TopCash account. Online-only and
    account-gated — the shape the 95 already-enriched TopCash deals carry."""
    constraints = empty_constraints()
    constraints["store_coverage"] = {
        "is_include_outlets_stores": False,
        "is_include_online_stores": True,
        "is_include_physical_stores": False,
    }
    constraints["eligibility"]["membership_required"] = True
    return constraints


def refine(deal: dict[str, Any], report: collections.Counter) -> bool:
    """Apply every rule to one deal in place. True if anything changed."""
    text = deal.get("terms_and_conditions") or ""
    changed = False

    constraints = deal.get("constraints")
    if not constraints:
        constraints = _topcash_constraints() if deal.get("source_id") == "topcash" else empty_constraints()
        deal["constraints"] = constraints
        report["added a missing constraints block"] += 1
        changed = True

    comb = constraints["combinability"]
    cover = constraints["store_coverage"]
    limits = constraints["limits"]
    elig = constraints["eligibility"]

    def put(section: dict[str, Any], key: str, value: Any, label: str) -> None:
        nonlocal changed
        if section.get(key) != value:
            section[key] = value
            report[label] += 1
            changed = True

    # 1. Explicit stacking prohibitions, tightening only, and never against a
    #    permission the same terms grant elsewhere.
    permitted: set[str] = set()
    for tail in _clauses(text, _POS):
        permitted |= _kinds_in(tail)
    for tail in _clauses(text, _NEG):
        for kind in _kinds_in(tail) - permitted:
            key = _COMB_KEY[kind]
            if comb.get(key) is True:
                put(comb, key, False, f"combinability.{key} → False (terms prohibit it)")

    # 2. Redemption channel: the terms name one and exclude the other.
    web_only = bool(_WEB_ONLY.search(text))
    branch_match = _BRANCH_ONLY.search(text)
    branch_excludes_web = (
        bool(branch_match)
        and not _EXCEPTION.search(text[max(0, branch_match.start() - 25) : branch_match.end() + 60])
        and not _WEB_ONLY_MENTION.search(text)
    )
    branch_only = bool(branch_match) or bool(_BRANCHES_OK.search(text))
    if web_only and not branch_only:
        put(cover, "is_include_online_stores", True, "store_coverage.online → True (terms say online only)")
        put(cover, "is_include_physical_stores", False, "store_coverage.physical → False (terms say online only)")
    elif branch_only and not web_only:
        put(cover, "is_include_physical_stores", True, "store_coverage.physical → True (terms say in-branch)")
        if branch_excludes_web:
            put(cover, "is_include_online_stores", False, "store_coverage.online → False (terms exclude the website)")

    # 3. Behatsdaa loadable card — branch-only unless the network's own section
    #    says otherwise (a handful of chains do allow their website).
    if _BEHATSDAA_CARD in text:
        specific = _BEHATSDAA_SPECIFIC.search(text)
        if not (specific and _WEB_MENTION.search(specific.group(1))):
            put(
                cover,
                "is_include_online_stores",
                False,
                "store_coverage.online → False (Behatsdaa card is branch-only)",
            )
            put(
                cover,
                "is_include_physical_stores",
                True,
                "store_coverage.physical → True (Behatsdaa card is branch-only)",
            )

    # 4. Numeric limits the terms state outright but the parser left null.
    monthly = _MONTHLY_QTY.search(text)
    if monthly and limits.get("max_uses_per_month") is None:
        put(limits, "max_uses_per_month", int(monthly.group(1)), "limits.max_uses_per_month ← stated in terms")
    minimum = _MIN_PURCHASE.search(text)
    if minimum and limits.get("minimum_purchase") is None:
        put(
            limits,
            "minimum_purchase",
            int(minimum.group(1).replace(",", "")),
            "limits.minimum_purchase ← stated in terms",
        )

    # 5. Limits are positive whole numbers or None (mirrors the Limits validator).
    for key in ("max_uses_per_transaction", "max_uses_per_month", "minimum_purchase"):
        value = limits.get(key)
        if value is None:
            continue
        coerced = int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None
        if coerced is not None and coerced <= 0:
            coerced = None
        if coerced != value:
            put(limits, key, coerced, f"limits.{key} → normalised to a positive int or null")

    # 6. Payment instrument: canonical spelling, and a deal that demands one is
    #    by definition gated on holding it.
    canonical = canonical_payment(elig.get("payment_method_required"), deal.get("source_id"))
    put(elig, "payment_method_required", canonical, "eligibility.payment_method_required → canonical spelling")
    if canonical and elig.get("membership_required") == "unknown":
        put(
            elig,
            "membership_required",
            True,
            "eligibility.membership_required → True (a payment instrument is required)",
        )

    return changed


# --- self-test -------------------------------------------------------------

_CASES = [
    ("אין כפל הנחות מועדונים", {"member"}),
    ("אין כפל מבצעים והנחות", {"store_sale", "coupons"}),
    ("אין כפל מבצעים", {"store_sale"}),
    ("ללא כפל מבצעים לחברי מועדון", {"member"}),
    ("אין כפל מבצעים/הנחות/עסקיות/מועדון/שוברים", {"store_sale", "member", "giftcards", "coupons"}),
    ("לא כולל כפל קופונים, מועדונים או כרטיסים דיגיטליים", {"coupons", "member", "giftcards"}),
    ("ללא כפל הנחות/ צבירה חברי מועדון", {"store_sale", "coupons", "cashback", "member"}),
    ("אין כפל הטבות לעובדים/בני משפחה", set()),
]


def self_test() -> None:
    for tail_text, expected in _CASES:
        tails = _clauses(tail_text, _NEG)
        assert tails, f"no NEG clause parsed from {tail_text!r}"
        got = _kinds_in(tails[0])
        assert got == expected, f"{tail_text!r}: expected {expected}, got {got}"

    # A permission must not be read out of a prohibition.
    assert not _clauses("לא כולל כפל מבצעים", _POS), "negated clause leaked into permissions"
    assert _clauses("הכרטיס כולל כפל מבצעים והנחות", _POS)

    assert canonical_payment("Behatsdaa 'רשתות בהצדעה 15%'") == "Behatsdaa network wallet 15%"
    assert canonical_payment("Behatsdaa - Network Wallet 20%") == "Behatsdaa network wallet 20%"
    assert canonical_payment("Isracard HOT or American Express HOT") == "HOT club-linked credit card"
    assert canonical_payment("Hever Teamim") == "Hever Teamim loadable card"
    assert canonical_payment(None) is None
    assert canonical_payment("club-linked credit card", "hot") == "HOT club-linked credit card"
    assert canonical_payment("PayPal", "topcash") == "PayPal"

    assert _WEB_ONLY.search("ניתן למימוש באתר הסחר בלבד")
    assert _WEB_ONLY.search("ההטבה תקפה ברישום באתר בלבד")
    assert _BRANCH_ONLY.search("לא ניתן למימוש באתר")
    assert not _WEB_ONLY.search("לא ניתן למימוש באתר")
    assert not _WEB_ONLY.search("בטייק אווי - בהזמנה דרך האתר בלבד")
    assert _EXCEPTION.search("לא ניתן למימוש באתרי הסחר, למעט אתרי הסחר של קסטרו")
    assert _kinds_in("הנחות מועדון LIFE STYLE ניתן לטעון כרטיס ולקבל 30% הנחה") == {"member"}
    print("self-test: ok")


def main() -> None:
    parser = argparse.ArgumentParser(description="Refine deal constraints in the seed file.")
    parser.add_argument("--dry-run", action="store_true", help="report without writing")
    parser.add_argument("--self-test", action="store_true", help="run the rule assertions and exit")
    parser.add_argument("--path", type=Path, default=SEED)
    parser.add_argument("--sample", type=int, default=0, help="print N changed deals for review")
    parser.add_argument("--report", type=Path, help="write a per-deal before/after JSON changelog")
    args = parser.parse_args()

    self_test()
    if args.self_test:
        return

    deals = json.loads(args.path.read_text(encoding="utf-8"))
    report: collections.Counter = collections.Counter()
    before = {d["id"]: json.dumps(d.get("constraints"), sort_keys=True, ensure_ascii=False) for d in deals}

    touched = [d for d in deals if refine(d, report)]

    print(f"deals: {len(deals)}   changed: {len(touched)}")
    for label, count in report.most_common():
        print(f"  {count:6d}  {label}")

    for deal in touched[: args.sample]:
        print("\n" + "=" * 70)
        print(deal["id"], deal["source_id"], deal["deal_type"], deal["title"])
        print((deal.get("terms_and_conditions") or "")[:700])
        print("  BEFORE:", before[deal["id"]])
        print("  AFTER :", json.dumps(deal["constraints"], sort_keys=True, ensure_ascii=False))

    if args.report:
        args.report.write_text(
            json.dumps(
                [
                    {
                        "id": deal["id"],
                        "source_id": deal.get("source_id"),
                        "title": deal.get("title"),
                        "before": json.loads(before[deal["id"]]) if before[deal["id"]] != "null" else None,
                        "after": deal["constraints"],
                    }
                    for deal in touched
                ],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"changelog: {args.report}")

    if not args.dry_run:
        # Same formatting the seed already uses: 2-space indent, literal Hebrew,
        # no trailing newline — so the diff shows only the constraint edits.
        args.path.write_text(json.dumps(deals, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nwrote {args.path}")


if __name__ == "__main__":
    main()
