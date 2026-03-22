from __future__ import annotations

import re
from urllib.parse import urlparse


def collapse_whitespace(text: str) -> str:
    """Collapse multiple whitespace characters into a single space and strip."""
    return re.sub(r"\s+", " ", text).strip()


def normalize_punctuation(text: str) -> str:
    """Normalize dash types to hyphen and various quote styles to standard quotes."""
    # Normalize dashes: em-dash, en-dash, minus sign, figure dash -> hyphen
    text = re.sub(r"[\u2012\u2013\u2014\u2015\u2212]", "-", text)
    # Normalize left/right single quotes and prime to apostrophe
    text = re.sub(r"[\u2018\u2019\u201A\u2032]", "'", text)
    # Normalize left/right double quotes and double prime to double quote
    text = re.sub(r"[\u201C\u201D\u201E\u2033]", '"', text)
    return text


_LEGAL_SUFFIXES_RE = re.compile(
    r"""\s*(?:
        בע"מ |
        בע״מ |
        ltd\.? |
        inc\.? |
        llc
    )\s*$""",
    re.IGNORECASE | re.VERBOSE,
)


def strip_legal_suffixes(text: str) -> str:
    """Remove Israeli and common legal entity suffixes from end of string."""
    return _LEGAL_SUFFIXES_RE.sub("", text).rstrip()


_BRANCH_PATTERNS = [
    # "סניף X" pattern
    re.compile(r"^(.+?)\s*[-–—]\s*סניף\s+(.+)$"),
    re.compile(r"^(.+?)\s+סניף\s+(.+)$"),
    # "- branch_name" at the end
    re.compile(r"^(.+?)\s*[-–—]\s+(.+)$"),
    # "branch X" pattern (English)
    re.compile(r"^(.+?)\s+branch\s+(.+)$", re.IGNORECASE),
]


def extract_branch(text: str) -> tuple[str, str | None]:
    """Extract branch info from store name.

    Returns (name_without_branch, branch_or_none).
    """
    for pattern in _BRANCH_PATTERNS:
        m = pattern.match(text)
        if m:
            name = m.group(1).strip()
            branch = m.group(2).strip()
            if name and branch:
                return name, branch
    return text, None


def extract_domain(url: str | None) -> str | None:
    """Extract domain from URL, stripping www. prefix."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
        domain = parsed.hostname or ""
        if domain.startswith("www."):
            domain = domain[4:]
        return domain if domain else None
    except Exception:
        return None
