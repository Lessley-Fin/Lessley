"""
Whether a purchase and a shop are even in the same line of business.

This is a *safety net* over name matching, never a way of choosing shops. Picking shops by
category is what this replaced: ``SHOPPING_OTHER`` alone holds 3,641 shops that run a deal,
so a category can only ever say "these two are nothing alike", never "these two are the same".

Categories are compared by group rather than by name because the useful distinction is
coarse. A café transaction landing on a shop tagged ``COFFEE_&_SNACKS`` instead of
``RESTAURANT`` is the same kind of business and must not be turned down; a café transaction
landing on a car park is not.
"""

from typing import Iterable

# The 46-name closed set, gathered into lines of business. Names come from
# lessley-deals' `enrichment/mcc_catalog.py`, which is where a store's tags are written.
CATEGORY_GROUPS: dict[str, set[str]] = {
    "FOOD": {
        "RESTAURANT", "COFFEE_&_SNACKS", "BARS", "FOOD_&_DRINKS_OTHER",
        "GROCERIES", "ALCOHOL_&_TOBACCO",
    },
    "HEALTH": {"BEAUTY", "HEALTH_&_BEAUTY_OTHER", "HEALTHCARE", "PHARMACY"},
    "TRANSPORT": {"CAR_&_FUEL", "PUBLIC_TRANSPORT", "TRANSPORT_OTHER", "FLIGHTS"},
    "LEISURE": {
        "CULTURE_&_EVENTS", "LEISURE_OTHER", "HOBBIES", "SPORTS_&_FITNESS",
        "HOBBY_&_SPORTS_EQUIPMENT", "VACATION",
    },
    "HOME": {
        "HOME", "FURNITURE_&_INTERIOR", "HOME_IMPROVEMENTS_OTHER",
        "RENOVATION_&_REPAIRS", "GARDEN",
    },
    "RETAIL": {"CLOTHES_&_ACCESSORIES", "GIFTS", "ELECTRONICS", "BOOKS_&_GAMES", "KIDS", "PETS"},
    "MONEY": {
        "FINANCE_OTHER", "CAPITAL_MARKET", "INSURANCE_&_FEES", "LOANS",
        "SAVINGS", "FEES", "BUSINESS_EXPENSES",
    },
}

_GROUP_OF: dict[str, str] = {
    category: group for group, categories in CATEGORY_GROUPS.items() for category in categories
}

# Catch-all tags carry no information about what a shop sells. ``SHOPPING_OTHER`` is on 52%
# of the catalogue, so reading it as a signal would turn down far more than it should.
UNINFORMATIVE = {"SHOPPING_OTHER", "OTHER", "SERVICES", "N/A", ""}


def group_of(category: str | None) -> str | None:
    """The line of business this category belongs to, or nothing when it does not say."""
    if not category or category in UNINFORMATIVE:
        return None
    return _GROUP_OF.get(category)


def is_vetoed(transaction_category: str | None, store_categories: Iterable[str]) -> bool:
    """
    True when the purchase and the shop are in plainly different lines of business.

    Both sides have to actually say something. A shop tagged only ``SHOPPING_OTHER`` is never
    turned down — it has told us nothing, and treating silence as disagreement would favour
    the worst-tagged shops over the best-tagged ones.
    """
    spent_on = group_of(transaction_category)
    if spent_on is None:
        return False

    sells = {group_of(category) for category in store_categories}
    sells.discard(None)
    return bool(sells) and spent_on not in sells
