"""Per-chain redemption limitations for the Behatsdaa loadable wallets.

The Behatsdaa wallets are backed by a loadable card (``הכרטיס הנטען``) whose
real redemption rules do **not** live in ``GetWalletChain`` — that endpoint
only returns the chain list. They live on a separate public HTML page:

    https://www.dts.co.il/HtmlView/17062019-3

That page has exactly two layers, and both matter:

1. A site-wide ``הגבלות והחרגות כלליות`` block that applies to *every* chain
   (no outlet stores, in-branch only — not the chains' own websites, stacks
   with store sales but not with club-member discounts, can't buy gift cards
   with it, ...).
2. ~160 per-chain override blocks holding that chain's own exclusions and
   per-transaction ceilings (``עד 1,000 ש"ח לעסקה``, ``לא כולל עסקיות``,
   ``לא תקף ב-HAPPY HOUR``, ...).

A saved copy of the page lives at
``data/behatsdaa_snapshots/behatsdaa_chain_limitations.html`` — same
file-based convention as the rest of the Behatsdaa adapter. No login is
needed, so refreshing it is just::

    curl -sL https://www.dts.co.il/HtmlView/17062019-3 \\
      -o data/behatsdaa_snapshots/behatsdaa_chain_limitations.html

Parsing notes
-------------
Splitting on the page's named anchors (``<a name="<chain>">``) looks tempting
and is *wrong*: roughly a dozen entries have no anchor at all (NINNYO TLV, the
Crown Plaza / Vert / Poli / Indigo hotels, היכל הבמה גני תקווה), so their
blocks silently merge into the previous chain — NINNYO's Happy-hour exclusion
would end up attached to מקדונלדס.

What *is* consistent is that every heading is ``<strong>``-wrapped. So the
heading names are collected from the ``<strong>`` elements, and the detail
region is then split on **whole lines** equal to one of those names. Going
through lines rather than tag positions also neutralises inline bold inside a
bullet (``לא ניתן לממש ב- <strong>factory54cafe</strong>``), which as a tag
boundary would have started a bogus section.
"""

from __future__ import annotations

import html as html_lib
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from lessley_deals.normalization.hebrew_utils import normalize_hebrew
from lessley_deals.scraping.helpers.html_utils import clean_html

logger = logging.getLogger(__name__)

SOURCE_URL = "https://www.dts.co.il/HtmlView/17062019-3"

_STRONG_RE = re.compile(r"<strong[^>]*>(.*?)</strong>", re.IGNORECASE | re.DOTALL)
_TOC_LINK_RE = re.compile(r"<a\b[^>]*href=\"#[^\"]*\"[^>]*>.*?</a>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")

# The line that closes the general block and opens the per-chain index.
_INDEX_MARKER = "לצפייה במגבלות"

# Category headings interleaved with the chain headings. They are separators,
# not chains — a bullet following one before any chain heading belongs to
# nobody and is dropped.
_CATEGORY_HEADINGS: tuple[str, ...] = (
    "אופנה ופנאי",
    "רשתות שיווק",
    "ספורט",
    "מסעדות ובתי קפה",
    "אטרקציות",
    "הכל לבית",
    "נופש",
    "תרבות",
    "ספא",
)

# A chain key shorter than this is too ambiguous to match by containment.
_MIN_CONTAINMENT_KEY_LEN = 4

# The wallet catalogue lists a chain's web shop as a separate entry ("ויקטורי
# אונליין", "SIMMONS online"); the page documents the brand once. Strip the
# marker and retry so the online entry inherits the brand's limitations.
_ONLINE_SUFFIX_RE = re.compile(r"\s*-?\s*(?:online|אונליין|און\s*ליין)\s*$", re.IGNORECASE)

# The page is written in Hebrew; the wallet catalogue names some chains in
# Latin script. Transliteration is not something to guess at — this is the
# hand-verified set. Keys are wallet ``chainName`` values, values are the
# page's heading for the same business. Extend as new pairs are confirmed.
_ALIASES: dict[str, str] = {
    "ACE": "אייס",
    "AUTODEPOT": "אוטודיפו",
    "BLACK": "בלאק",
    "The Childrens Place": "צ'ילדרן פלייס",
}


def _key(name: str) -> str:
    """Compact match key: Hebrew-normalized, lowercased, alphanumerics only.

    Mirrors the ``compact`` form the matching pipeline uses, so ``"Foot
    locker"`` and ``"foot-locker"`` collapse to the same key and punctuation
    drift on either side of the join stops mattering.
    """
    text = normalize_hebrew(html_lib.unescape(str(name or ""))).lower()
    return re.sub(r"[^0-9a-z֐-׿]+", "", text)


_CATEGORY_KEYS: tuple[str, ...] = tuple(_key(h) for h in _CATEGORY_HEADINGS)


def _is_category(heading_key: str) -> bool:
    """Category headings carry a suffix on the page (``"...(לא תקף בעסקיות):"``)."""
    return any(heading_key.startswith(c) for c in _CATEGORY_KEYS)


@dataclass(frozen=True)
class BehatsdaaLimitations:
    """Parsed limitations page: the general block plus per-chain overrides.

    ``by_chain`` is keyed by :func:`_key` so lookups survive punctuation and
    Hebrew-form drift between the page and ``GetWalletChain``'s ``chainName``.
    """

    general: str
    by_chain: dict[str, str]

    def lookup(self, chain_name: str) -> str | None:
        """Return the limitations text for *chain_name*, or ``None``.

        Tried in order: the hand-verified alias table, an exact key match, the
        same again with an ``online`` / ``אונליין`` suffix stripped, and finally
        a containment match where the page's key *contains* the chain's key —
        the page groups some brands under a joint heading (e.g. ``"רשתות
        פקטורי 54, טומי הילפיגר, ארמני אקסצ'יינג'"`` covers a chain named just
        ``"פקטורי 54"``). The shortest containing key wins, as the most
        specific one.

        Containment is deliberately one-directional: letting a chain key
        contain a *page* key would match ``"אייס קיוב"`` against ``"אייס"``.
        Attaching no limitations is recoverable; attaching another chain's is
        not — so the page's own coverage gaps are left as gaps.
        """
        raw = str(chain_name or "").strip()
        for candidate in (_ALIASES.get(raw, raw), _ONLINE_SUFFIX_RE.sub("", raw)):
            found = self._lookup_key(_key(candidate))
            if found is not None:
                return found
        return None

    def _lookup_key(self, key: str) -> str | None:
        if not key:
            return None
        exact = self.by_chain.get(key)
        if exact is not None:
            return exact
        if len(key) < _MIN_CONTAINMENT_KEY_LEN:
            return None
        candidates = [k for k in self.by_chain if key in k]
        if not candidates:
            return None
        return self.by_chain[min(candidates, key=len)]


def _parse_general(prelude_text: str) -> str:
    """Pull the ``הגבלות והחרגות כלליות`` bullets out of the page prelude.

    The prelude is everything before the detail region: the heading, the
    site-wide bullets, then the ``לצפייה במגבלות`` line that introduces the
    per-chain index. Only the bullets in between are wanted.
    """
    bullets: list[str] = []
    for raw in prelude_text.splitlines():
        line = raw.strip()
        if not line.startswith("-"):
            continue
        if _INDEX_MARKER in line:
            break
        text = line.lstrip("- ").strip()
        if text:
            bullets.append(text)
    return "\n".join(f"- {b}" for b in bullets)


def _split_regions(html: str) -> tuple[str, str]:
    """Split the page into ``(prelude_html, detail_html)``.

    The table of contents is the run of in-page ``href="#..."`` links; the
    detail region is everything after the last of them.
    """
    toc_links = list(_TOC_LINK_RE.finditer(html))
    if not toc_links:
        logger.warning(
            "Behatsdaa limitations page has no in-page index links — layout changed? "
            "Treating the whole document as detail."
        )
        return "", html
    cut = toc_links[-1].end()
    return html[:cut], html[cut:]


def _heading_keys(detail_html: str) -> set[str]:
    """Collect the compact keys of every ``<strong>`` heading in the detail region."""
    keys: set[str] = set()
    for match in _STRONG_RE.finditer(detail_html):
        key = _key(_TAG_RE.sub("", match.group(1)))
        if key:
            keys.add(key)
    return keys


def parse_limitations_page(html: str) -> BehatsdaaLimitations:
    """Parse the saved limitations page into general + per-chain blocks.

    Chains listed under more than one heading (the page repeats e.g.
    ``מקדונלדס``) have their bullets merged, deduped, in page order.
    """
    prelude_html, detail_html = _split_regions(html)
    general = _parse_general(clean_html(prelude_html or html))

    headings = _heading_keys(detail_html)
    if not headings:
        logger.warning("Behatsdaa limitations page has no <strong> headings — wrong file?")
        return BehatsdaaLimitations(general=general, by_chain={})

    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for raw in clean_html(detail_html).splitlines():
        line = raw.strip(" \t-–•")
        if not line:
            continue
        line_key = _key(line)
        if not line_key:
            continue
        if line_key in headings:
            # A category heading ends the previous chain without opening a new
            # one, so its trailing whitespace can't leak into the next chain.
            current = None if _is_category(line_key) else sections.setdefault(line_key, [])
            continue
        if current is not None:
            current.append(line)

    by_chain = {
        key: "\n".join(f"- {ln}" for ln in _dedupe(lines))
        for key, lines in sections.items()
        if lines
    }
    logger.debug(
        "Parsed Behatsdaa limitations: %d general bullet(s), %d chain block(s)",
        len(general.splitlines()),
        len(by_chain),
    )
    return BehatsdaaLimitations(general=general, by_chain=by_chain)


def _dedupe(lines: list[str]) -> list[str]:
    """Drop repeated bullets (a few blocks state the same rule twice)."""
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        key = _key(line)
        if key in seen:
            continue
        seen.add(key)
        out.append(line)
    return out


@lru_cache(maxsize=8)
def load_limitations(path: Path) -> BehatsdaaLimitations:
    """Load and parse the saved limitations page, cached per path.

    A missing or unreadable file is **not** fatal: the adapter still emits its
    deals, just without the per-chain limitations, and logs how to refresh the
    snapshot.
    """
    try:
        html = path.read_text(encoding="utf-8")
    except OSError:
        logger.warning(
            "Behatsdaa limitations snapshot not readable at %s — deals will carry no "
            "chain limitations. Refresh it with: curl -sL %s -o %s",
            path,
            SOURCE_URL,
            path,
        )
        return BehatsdaaLimitations(general="", by_chain={})
    return parse_limitations_page(html)
