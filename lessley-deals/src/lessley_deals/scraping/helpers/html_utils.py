"""HTML cleaning utilities shared by scrapers.

Ported from legacy ``hot_extract_format.py :: clean_html``.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup


# Characters to strip from extracted text (RTL markers + NBSP).
_JUNK_CHARS = str.maketrans("", "", "\xa0\u200e\u200f\u202a\u202b")

# Block-level elements that should have a trailing newline.
_BLOCK_TAGS = {"p", "div", "li", "h1", "h2", "h3"}


def clean_html(raw_html: str | None) -> str:
    """Convert raw HTML to clean plain text.

    - Replaces ``<br>`` with newlines.
    - Appends newlines after block-level elements.
    - Strips RTL markers and NBSP.
    - Collapses whitespace.
    """
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for block in soup.find_all(_BLOCK_TAGS):
        block.append("\n")
    text = soup.get_text(separator=" ")
    text = text.translate(_JUNK_CHARS)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" \n", "\n", text)
    text = re.sub(r"\n ", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
