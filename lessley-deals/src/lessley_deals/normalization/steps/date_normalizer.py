from __future__ import annotations

import re
from datetime import datetime

# Hebrew month names to month numbers
_HEBREW_MONTHS: dict[str, int] = {
    "ינואר": 1,
    "פברואר": 2,
    "מרץ": 3,
    "אפריל": 4,
    "מאי": 5,
    "יוני": 6,
    "יולי": 7,
    "אוגוסט": 8,
    "ספטמבר": 9,
    "אוקטובר": 10,
    "נובמבר": 11,
    "דצמבר": 12,
}

# DD/MM/YYYY, DD.MM.YYYY, DD-MM-YYYY
_NUMERIC_DATE_RE = re.compile(
    r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})"
)

# "5 ינואר 2024" or "5 בינואר 2024"
_HEBREW_DATE_RE = re.compile(
    r"(\d{1,2})\s+(?:ב)?(" + "|".join(_HEBREW_MONTHS.keys()) + r")\s+(\d{4})"
)


def parse_israeli_date(text: str) -> datetime | None:
    """Parse Israeli date formats into a datetime.

    Handles:
    - DD/MM/YYYY, DD.MM.YYYY, DD-MM-YYYY
    - Hebrew month names: "5 ינואר 2024"
    """
    if not text:
        return None

    text = text.strip()

    # Try Hebrew month name first
    m = _HEBREW_DATE_RE.search(text)
    if m:
        day = int(m.group(1))
        month = _HEBREW_MONTHS[m.group(2)]
        year = int(m.group(3))
        try:
            return datetime(year, month, day)
        except ValueError:
            return None

    # Try numeric formats (DD/MM/YYYY)
    m = _NUMERIC_DATE_RE.search(text)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        year = int(m.group(3))
        # Handle 2-digit year
        if year < 100:
            year += 2000
        try:
            return datetime(year, month, day)
        except ValueError:
            return None

    return None
