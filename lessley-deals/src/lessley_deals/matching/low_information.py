from __future__ import annotations

from lessley_deals.domain.models import NameForms

_LOW_INFORMATION_TOKEN_SETS = frozenset(
    {
        frozenset({"מרפאת", "שיניים"}),
        frozenset({"בית", "מרקחת"}),
        frozenset({"סלון", "יופי"}),
        frozenset({"מרכז", "וטרינרי"}),
        frozenset({"מוסך"}),
    }
)


def is_low_information_alias(forms: NameForms) -> bool:
    """Return True for generic business-category aliases that are unsafe to match.

    These labels describe a category, not a specific business, and should not
    participate in automatic matching.
    """

    return frozenset(forms.tokens) in _LOW_INFORMATION_TOKEN_SETS
