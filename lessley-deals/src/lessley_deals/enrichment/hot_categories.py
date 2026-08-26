"""HOT's own category labels, mapped to the canonical MCC vocabulary.

HOT publishes an ``item_category`` on every benefit — a Hebrew label like
``מכוני יופי והסרת שיער``. That is a merchant category assigned by the source
itself, which makes it far better evidence than anything inferred from a store's
name, and it costs no LLM call.

The map is deliberately partial. A label with no entry resolves to nothing rather
than to a guess, so a store keeps ``OTHER`` and stays visible to
``deals enrich-stores`` instead of being quietly mis-filed under a category that
merely looked close.
"""

from __future__ import annotations

# HOT label -> canonical category name (see enrichment/mcc_catalog.py).
HOT_CATEGORY_MAP: dict[str, str] = {
    # Food & drink
    "מזון ומשקאות": "FOOD_&_DRINKS_OTHER",
    "מאכלים ביתיים": "FOOD_&_DRINKS_OTHER",
    "בשרים": "GROCERIES",
    "צרכנות": "SHOPPING_OTHER",
    "מסעדות ובתי קפה": "RESTAURANT",
    "מזון מהיר": "RESTAURANT",
    "פיצריות": "RESTAURANT",
    "חומוסיות": "RESTAURANT",
    "איטלקיות": "RESTAURANT",
    "אסייתי וסושי": "RESTAURANT",
    "המבורגרים": "RESTAURANT",
    "בתי קפה": "COFFEE_&_SNACKS",
    "עולם הקפה": "COFFEE_&_SNACKS",
    "גלידריות": "COFFEE_&_SNACKS",
    "מאפיות, קונדיטוריות": "COFFEE_&_SNACKS",
    "ברים ופאבים": "BARS",
    # Fashion & personal care
    "אופנה וטיפוח": "CLOTHES_&_ACCESSORIES",
    "תכשיטים ושעונים": "CLOTHES_&_ACCESSORIES",
    "קוסמטיקה": "BEAUTY",
    "מכוני יופי והסרת שיער": "BEAUTY",
    "ספא": "BEAUTY",
    "אופטיקה": "HEALTHCARE",
    # Home
    "לבית ולגן": "HOME",
    "טקסטיל לבית": "HOME",
    "ריהוט לבית": "FURNITURE_&_INTERIOR",
    "פרחים ועציצים": "GARDEN",
    # Kids
    "ילדים ותינוקות": "KIDS",
    "עולם הילדים": "KIDS",
    # Electronics
    "חשמל ומחשבים": "ELECTRONICS",
    "סמארטפונים ואביזרים": "ELECTRONICS",
    # Leisure, culture, travel
    "נופש ובתי מלון בארץ": "VACATION",
    "תיירות ונופש": "VACATION",
    "חדש- תיירות ונופש": "VACATION",
    "צימרים": "VACATION",
    "טיולים מאורגנים": "VACATION",
    "אטרקציות": "LEISURE_OTHER",
    "אטרקציות ופנאי": "LEISURE_OTHER",
    "אטרקציות, בילוי ופנאי": "LEISURE_OTHER",
    "מופעים והצגות": "CULTURE_&_EVENTS",
    "תרבות ופנאי": "CULTURE_&_EVENTS",
    "בריאות וספורט": "SPORTS_&_FITNESS",
    "צילום ופיתוח": "HOBBIES",
    # Vehicles & transport
    "מוסכים": "CAR_&_FUEL",
    "מוצרים ושירותים לרכב": "CAR_&_FUEL",
    "רכישת רכב": "CAR_&_FUEL",
    "השכרת רכב בחו\"ל": "TRANSPORT_OTHER",
    # Other
    "חיות מחמד": "PETS",
    "לימודים קורסים וחוגים": "EDUCATION",
    "תשמישי קדושה ויודאיקה": "GIFTS",
    "שוברים ותווי קניה": "GIFTS",
}


def category_for(label: str | None) -> str | None:
    """Canonical category for a HOT label, or None when it is not mapped."""
    if not label:
        return None
    return HOT_CATEGORY_MAP.get(label.strip())
