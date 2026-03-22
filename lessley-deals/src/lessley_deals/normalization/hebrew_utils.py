from __future__ import annotations

import re
import unicodedata


def strip_niqqud(text: str) -> str:
    """Remove Hebrew vowel points (U+0591-U+05C7)."""
    return re.sub(r"[\u0591-\u05C7]", "", text)


def normalize_final_forms(text: str) -> str:
    """Map Hebrew final letter forms to their regular equivalents."""
    table = str.maketrans("םןץףך", "מנצפכ")
    return text.translate(table)


def normalize_presentation_forms(text: str) -> str:
    """Map Hebrew presentation forms (U+FB1D-U+FB4F) to base characters.

    Uses NFKD decomposition to strip combining marks from presentation forms.
    """
    result: list[str] = []
    for char in text:
        cp = ord(char)
        if 0xFB1D <= cp <= 0xFB4F:
            decomposed = unicodedata.normalize("NFKD", char)
            # Keep only non-combining characters (category != M*)
            base = "".join(c for c in decomposed if not unicodedata.category(c).startswith("M"))
            result.append(base if base else char)
        else:
            result.append(char)
    return "".join(result)


def normalize_geresh(text: str) -> str:
    """Normalize Hebrew geresh (U+05F3) to apostrophe, gershayim (U+05F4) to double quote."""
    return text.replace("\u05F3", "'").replace("\u05F4", '"')


def strip_zero_width(text: str) -> str:
    """Remove zero-width and bidirectional control characters."""
    return re.sub(r"[\u200B-\u200F\uFEFF\u202A-\u202E]", "", text)


def normalize_hebrew(text: str) -> str:
    """Apply all Hebrew normalizations in order."""
    text = strip_niqqud(text)
    text = normalize_final_forms(text)
    text = normalize_presentation_forms(text)
    text = normalize_geresh(text)
    text = strip_zero_width(text)
    return text
