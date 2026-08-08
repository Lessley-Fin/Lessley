from __future__ import annotations

import pytest

from lessley_deals.scraping.helpers.discount_parser import (
    check_stackable,
    classify_hot_benefit_type,
    deduce_hot_discount_mechanics,
    deduce_mastercard_discount,
    extract_coupon,
    extract_redeem_channels,
)


class TestDeduceHotDiscountMechanics:
    def test_voucher_1300_with_prices(self) -> None:
        """Priority 1: benefit_type 1300 + before/after prices."""
        main = {
            "benefit_type": "1300",
            "price_before_discount": 200,
            "price_after_discount": 150,
        }
        result = deduce_hot_discount_mechanics(main)
        assert result["condition"] == {"type": "exact_spend", "value": 200.0}
        assert result["reward"] == {"type": "fixed_total_amount", "value": 150.0}

    def test_voucher_1300_with_title_and_percent(self) -> None:
        """Priority 2: benefit_type 1300 + ₪ in title + percentage."""
        main = {
            "benefit_type": "1300",
            "title": "שובר 500₪",
            "value": "20%",
        }
        result = deduce_hot_discount_mechanics(main)
        assert result["condition"]["type"] == "exact_spend"
        assert result["condition"]["value"] == 500
        assert result["reward"]["type"] == "fixed_total_amount"
        assert result["reward"]["value"] == 400.0  # 500 * (1 - 0.20)

    def test_shovi_pattern(self) -> None:
        """Priority 3: 'שווי X ב Y' pattern."""
        main = {"title": "שובר", "description": ""}
        text = "שווי 100 ב-80"
        result = deduce_hot_discount_mechanics(main, text)
        assert result["condition"] == {"type": "exact_spend", "value": 100}
        assert result["reward"] == {"type": "fixed_total_amount", "value": 80}

    def test_percentage(self) -> None:
        """Priority 4: percentage in text."""
        main = {"title": "20% הנחה", "value": "20%", "description": ""}
        result = deduce_hot_discount_mechanics(main)
        assert result["reward"]["type"] == "percentage_off"
        assert result["reward"]["value"] == 0.2

    def test_percentage_found_when_combined_text_excludes_it(self) -> None:
        """Priority 4 must not be gated on *combined_text* alone.

        hot.py's ``_merge_detail`` passes only the T&C + offer-details prose,
        which never contains the headline "2%" — that lives in ``value`` /
        ``valueNum``.  Gating on ``"%" in combined_text`` silently returned the
        default ``percentage_off 0.0`` for ~45% of the HOT catalogue.
        Regression test for benefit 22570 ("כלבו 1000 מוצרים לבית").
        """
        main = {
            "benefit_type": "100",
            "title": "כלבו 1000 מוצרים לבית",
            "value": "2% הנחה",
            "valueNum": "2%",
            "description": "",
        }
        terms = "ההנחה בחיוב תינתן אוטומטית למשלמים בכרטיס אשראי המשויך למועדון הוט"
        result = deduce_hot_discount_mechanics(main, terms)
        assert result["reward"] == {"type": "percentage_off", "value": 0.02}

    def test_undefined_percent_does_not_open_percentage_branch(self) -> None:
        """HOT emits a literal "undefined%" in ``cashback_description``.

        A bare ``"%" in text`` gate lets that garbage claim priority 4; the
        record must instead fall through to the priority-6 price fallback,
        which keeps the exact prices.  Regression test for benefit 60176.
        """
        main = {
            "benefit_type": "800",
            "title": "כרטיס סרט יחיד בסינמה סיטי",
            "value": "",
            "valueNum": 0,
            "cashback_description": "המחיר לאחר undefined% הנחה בחיוב",
            "price_before_discount": "49.90",
            "price_after_discount": "41",
        }
        result = deduce_hot_discount_mechanics(main)
        assert result["condition"] == {"type": "exact_spend", "value": 49.9}
        assert result["reward"] == {"type": "fixed_total_amount", "value": 41.0}

    def test_stated_percentage_beats_spend_and_save_misfire(self) -> None:
        """A stated ``value`` percentage wins over _SPEND_SAVE_RE matching prose.

        Benefit 23743 ("7% הנחה") previously produced a ₪58,000
        ``fixed_discount_amount`` because the spend & save regex matched
        numbers in the terms text.
        """
        main = {"benefit_type": "100", "title": "מבצע", "value": "7% הנחה"}
        terms = "ההטבה ניתנת ברכישת מוצרים בסכום 100 שח 58000 נקודות"
        result = deduce_hot_discount_mechanics(main, terms)
        assert result["reward"] == {"type": "percentage_off", "value": 0.07}

    def test_agorot_fuel_discount(self) -> None:
        """Priority 7a: benefit_type "100" fuel discount stated in agorot.

        "עד 25 אגורות הנחה" — no "%" sign, no baseline price. The raw agorot
        number (25) is kept as-is with an explicit unit marker rather than
        converted, since it's a per-liter rate the caller must multiply by
        quantity, not a flat ILS amount off the purchase.
        """
        main = {
            "benefit_type": "100",
            "title": "רשת תחנות תדלוק - מיקה עתידים",
            "value": "עד 25 אגורות הנחה",
            "valueNum": "עד 25 אגורות",
        }
        result = deduce_hot_discount_mechanics(main)
        assert result["reward"] == {
            "type": "fixed_discount_amount",
            "value": 25.0,
            "unit": "agorot_per_liter",
        }

    def test_agorot_fuel_discount_short_form(self) -> None:
        """"30 אג הנחה" (short "אג" form, no "ורות" suffix)."""
        main = {"benefit_type": "100", "title": "תחנת דלק", "value": "30 אג הנחה"}
        result = deduce_hot_discount_mechanics(main)
        assert result["reward"]["value"] == 30.0
        assert result["reward"]["unit"] == "agorot_per_liter"

    def test_bare_number_treated_as_percentage_for_benefit_type_100(self) -> None:
        """Priority 7b: "3.5 הנחה" has no "%" sign — the number is still a
        percentage for benefit_type "100" listings, same as the other
        percentage deals in this category."""
        main = {"benefit_type": "100", "title": "תטעם תבין", "value": "3.5 הנחה"}
        result = deduce_hot_discount_mechanics(main)
        assert result["reward"] == {"type": "percentage_off", "value": 0.035}

    def test_bare_number_fallback_does_not_apply_outside_benefit_type_100(self) -> None:
        """The no-"%" percentage fallback is scoped to benefit_type "100" —
        other types keep returning the untouched default rather than guessing."""
        main = {"benefit_type": "700", "title": "מבצע", "value": "3.5 הנחה"}
        result = deduce_hot_discount_mechanics(main)
        assert result["reward"] == {"type": "percentage_off", "value": 0.0}

    def test_unrecoverable_null_value_stays_default(self) -> None:
        """"null הנחה" — HOT serialized a missing number as literal "null";
        there's no digit to recover, so benefit_type "100" must not invent one."""
        main = {"benefit_type": "100", "title": "פיצה pico", "value": "null הנחה"}
        result = deduce_hot_discount_mechanics(main)
        assert result["reward"] == {"type": "percentage_off", "value": 0.0}

    def test_spend_and_save(self) -> None:
        """Priority 5: spend & save pattern."""
        main = {"title": "מבצע", "description": ""}
        text = "50 ₪ הנחה ברכישת מעל 250 ₪"
        result = deduce_hot_discount_mechanics(main, text)
        assert result["condition"] == {"type": "min_spend", "value": 250}
        assert result["reward"] == {"type": "fixed_discount_amount", "value": 50}

    def test_spend_and_save_with_max_discount(self) -> None:
        """Spend & save with max discount cap — lands on `reward`, matching
        deal-optimizer's transform.py::apply_deal (no nested "constraints")."""
        main = {"title": "מבצע", "description": ""}
        text = "₪50 הנחה ברכישת מעל ₪250. עד ₪100 הנחה"
        result = deduce_hot_discount_mechanics(main, text)
        assert result["reward"]["max_discount_amount"] == 100
        assert "constraints" not in result

    def test_price_fallback(self) -> None:
        """Priority 6: price-based fallback."""
        main = {
            "title": "מבצע",
            "description": "",
            "price_before_discount": 100,
            "price_after_discount": 80,
        }
        result = deduce_hot_discount_mechanics(main)
        assert result["condition"]["value"] == 100.0
        assert result["reward"]["value"] == 80.0


class TestDeduceMastercardDiscount:
    def test_spend_and_save(self) -> None:
        result = deduce_mastercard_discount("₪50 הנחה ברכישת מעל ₪250", "50 הנחה")
        assert result is not None
        assert result["type"] == "spend_and_save"
        assert result["condition"]["value"] == 250

    def test_percentage(self) -> None:
        result = deduce_mastercard_discount("20% הנחה על כל המוצרים", "20% הנחה")
        assert result is not None
        assert result["type"] == "percentage"
        assert result["percent"] == 20

    def test_none_when_no_pattern(self) -> None:
        result = deduce_mastercard_discount("מבצע מיוחד ללקוחות", "מבצע מיוחד")
        assert result is None

    def test_spend_and_save_max_discount_lands_on_reward_not_constraints(self) -> None:
        # deal-optimizer's transform.py reads the savings cap straight off
        # `reward["max_discount_amount"]` (see apply_deal()) — there's no
        # nested "constraints" block in the new schema.
        result = deduce_mastercard_discount("₪50 הנחה ברכישת מעל ₪250. עד ₪100 הנחה", "50 הנחה")
        assert result is not None
        assert result["reward"]["max_discount_amount"] == 100
        assert "constraints" not in result

    def test_percentage_has_no_constraints_key(self) -> None:
        result = deduce_mastercard_discount("20% הנחה על כל המוצרים", "20% הנחה")
        assert result is not None
        assert "constraints" not in result


class TestCheckStackable:
    def test_not_stackable(self) -> None:
        assert check_stackable("לא כולל כפל מבצעים") is False

    def test_not_stackable_variant(self) -> None:
        assert check_stackable("ללא כפל מבצעים") is False

    def test_stackable(self) -> None:
        assert check_stackable("כולל כפל מבצעים") is True

    def test_default(self) -> None:
        assert check_stackable("מבצע רגיל") is False


class TestExtractRedeemChannels:
    def test_online(self) -> None:
        assert "online" in extract_redeem_channels("באתר הרשמי")

    def test_app(self) -> None:
        assert "mobile_app" in extract_redeem_channels("באפליקציית החנות")

    def test_physical(self) -> None:
        assert "physical_store" in extract_redeem_channels("בחנויות הרשת")

    def test_multiple(self) -> None:
        channels = extract_redeem_channels("באתר ובחנויות")
        assert "online" in channels
        assert "physical_store" in channels

    def test_empty(self) -> None:
        assert extract_redeem_channels("מבצע") == []


class TestExtractCoupon:
    def test_found(self) -> None:
        assert extract_coupon("קוד קופון: SAVE20 לקבלת ההנחה") == "SAVE20"

    def test_not_found(self) -> None:
        assert extract_coupon("מבצע ללא קופון") is None


class TestClassifyHotBenefitType:
    def test_cashback(self) -> None:
        assert classify_hot_benefit_type({"title": "Cashback on purchase"}) == "cashback"

    def test_voucher(self) -> None:
        assert classify_hot_benefit_type({"title": "Gift card voucher"}) == "voucher"

    def test_coupon(self) -> None:
        assert classify_hot_benefit_type({"title": "Coupon code offer"}) == "coupon"

    def test_default(self) -> None:
        assert classify_hot_benefit_type({"title": "הנחה בחנות"}) == "discount_at_billing"
