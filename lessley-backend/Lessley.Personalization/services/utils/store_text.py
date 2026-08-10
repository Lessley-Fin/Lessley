import re
import unicodedata
from typing import Iterable, List, Set

from rapidfuzz import fuzz

from config.constants import STORE_MATCH

# Hebrew letters change shape at the end of a word. The same name can be written either
# way depending on who typed it, so we fold them together before comparing anything.
_FINAL_LETTERS = str.maketrans({"ם": "מ", "ן": "נ", "ץ": "צ", "ף": "פ", "ך": "כ"})

# A geresh belongs *inside* the word — ג'ירף is one word, not two. Splitting on it
# (which is what stripping punctuation would do) turns brand names into unusable scraps.
_APOSTROPHES = re.compile(r"['’׳\"״]")

_BRANCH_SUFFIX = re.compile(r"[#*]\s*\d+\b")   # "STARBUCKS #123"
_TERMINAL_DIGITS = re.compile(r"\b\d{4,}\b")   # till/terminal numbers, but not "7-Eleven"
_PUNCTUATION = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WHITESPACE = re.compile(r"\s+")

_HEBREW_LETTER = re.compile(r"[֐-׿]")


def _fold(word: str) -> str:
    return unicodedata.normalize("NFKC", word).lower().translate(_FINAL_LETTERS)


# Card feeds staple the same handful of words onto every merchant: company suffixes and
# the clearing house's own filler. These are fixed artefacts of the format, not a
# vocabulary that grows — a real location vocabulary is learned instead (see below).
_BOILERPLATE: Set[str] = {
    _fold(word)
    for word in (
        "בעמ בע מ בהמ ltd inc llc co "
        "קהל נכבד סניף רשת שיווק גמא ניהול חברת עסק תשלום עסקה כללי"
    ).split()
}


def normalize(raw_name: str | None) -> str:
    """
    Turn a raw name — from a card feed or from our own store list — into the plain,
    comparable form everything downstream works with.
    """
    if not raw_name or not raw_name.strip():
        return ""

    text = unicodedata.normalize("NFKC", raw_name).lower()
    text = _APOSTROPHES.sub("", text)        # ג'ירף -> גירף, before punctuation splits it
    text = text.translate(_FINAL_LETTERS)
    text = _BRANCH_SUFFIX.sub(" ", text)
    text = _TERMINAL_DIGITS.sub(" ", text)
    text = _PUNCTUATION.sub(" ", text)
    return _WHITESPACE.sub(" ", text).strip()


def tokenize(normalized: str) -> List[str]:
    """The words of a normalized name, minus single letters and bare numbers."""
    return [word for word in normalized.split() if len(word) > 1 and not word.isdigit()]


def strip_boilerplate(tokens: Iterable[str]) -> List[str]:
    """
    Drop card-feed filler. If a name is *nothing but* filler we keep it as-is rather
    than hand back an empty name and lose the transaction entirely.
    """
    tokens = list(tokens)
    kept = [token for token in tokens if token not in _BOILERPLATE]
    return kept or tokens


def is_hebrew(token: str) -> bool:
    return bool(_HEBREW_LETTER.search(token))


def script_groups(tokens: List[str]) -> List[List[str]]:
    """
    Split a name into its Hebrew and Latin halves.

    Our store list often carries both spellings in one field — 'גולדה - Golda',
    'קפה קפה - cafe cafe'. They are two ways of writing one shop, not a four-word name,
    so each half is matched on its own and the better half wins.
    """
    hebrew = [token for token in tokens if is_hebrew(token)]
    latin = [token for token in tokens if not is_hebrew(token)]
    return [group for group in (hebrew, latin) if group] or [tokens]


def strip_town(tokens: Iterable[str], town_name: str | None) -> List[str]:
    """
    Remove the branch's town from a merchant name.

    The card feed tells us where the purchase happened, so we do not have to guess which
    words are a place: 'סטימצקי G כפר סבא' bought in כפר סבא is just Steimatzky. Feeds
    also truncate at ~20 characters, which leaves a *prefix* of the town ('הוד השרון'
    arriving as 'הו'), and the town itself is sometimes lightly misspelled — so a word
    counts as the town if it matches one of its words exactly, is a prefix of one, or is
    a near-miss.

    Callers must keep the unstripped words too: a shop is allowed to have the town in its
    own name ('VERT לגון נתניה'), and it still has to be able to match on it.
    """
    tokens = list(tokens)
    if not town_name:
        return tokens

    town_words = tokenize(normalize(town_name))
    if not town_words:
        return tokens

    def is_town(word: str) -> bool:
        return any(
            word == town_word
            or town_word.startswith(word)
            or fuzz.ratio(word, town_word) >= STORE_MATCH.TOWN_FUZZ_MIN
            for town_word in town_words
        )

    kept = [token for token in tokens if not is_town(token)]
    return kept or tokens
