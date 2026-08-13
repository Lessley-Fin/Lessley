"""
The two word lists matching cannot work out for itself, read once from disk.

Both are deliberately static rather than learned. ``PlaceVocabulary`` can infer place words
from traffic, but only once a word has been seen against several different merchants — one
person's history never gets there (a 61-row feed learns nothing at all), and the repository
holding the result is a process-wide singleton, so learning it per request would rewrite the
vocabulary for every other user at the same time.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, Set

from .store_text import normalize

logger = logging.getLogger(__name__)

_RESOURCES = Path(__file__).resolve().parents[2] / "config" / "resources"


def _read(filename: str) -> dict:
    try:
        with open(_RESOURCES / filename, encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as error:
        # A missing word list must not take the service down: matching still works without
        # it, just more cautiously about words it cannot place.
        logger.warning(
            f"Could not read {filename}, continuing without it: {error}",
            extra={"reason": "Optional reference data missing", "extra_data": {"file": filename}},
        )
        return {}


@lru_cache(maxsize=1)
def place_words() -> Set[str]:
    """Mall, street and generic-location words, normalized the way names are."""
    document = _read("place_words.json")
    words: Set[str] = set()
    for key, values in document.items():
        if key.startswith("_") or not isinstance(values, list):
            continue
        for phrase in values:
            # Multi-word entries ('סינמה סיטי') contribute each of their words, because a
            # merchant name is compared word by word.
            for word in normalize(phrase).split():
                if len(word) > 1:
                    words.add(word)
    logger.info(
        "Place vocabulary loaded",
        extra={"reason": "Data preparation for merchant-name matching",
               "extra_data": {"word_count": len(words)}},
    )
    return words


@lru_cache(maxsize=1)
def latin_towns() -> Dict[str, str]:
    """Latin spellings of Israeli towns mapped onto their Hebrew form, keyed lowercase."""
    towns = _read("latin_towns.json").get("towns", {})
    return {key.lower(): value for key, value in towns.items() if key and value}


def as_hebrew_town(town_name: str | None) -> str | None:
    """
    The Hebrew form of a town the feed may have written in Latin.

    ``strip_town`` compares the town against Hebrew merchant words with ``fuzz.ratio``, which
    scores zero across scripts — so a Latin town silently strips nothing. Roughly 38% of rows
    arrive that way ('KFAR SABA'), and every one of them keeps its town as if it were part of
    the shop's name.
    """
    if not town_name:
        return town_name
    return latin_towns().get(town_name.strip().lower(), town_name)
