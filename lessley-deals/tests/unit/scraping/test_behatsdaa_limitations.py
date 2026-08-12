from __future__ import annotations

from pathlib import Path

from lessley_deals.scraping.helpers.behatsdaa_limitations import (
    BehatsdaaLimitations,
    load_limitations,
    parse_limitations_page,
)

# A miniature stand-in for the real page, reproducing the three markup shapes
# that actually matter: an anchored heading, an *un*anchored heading (which
# anchor-based splitting would silently merge into the previous chain), and
# inline bold inside a bullet (which tag-position splitting would treat as a
# new section).
_PAGE = """\
<p>הגבלות והחרגות כלליות</p>
<p>- לא כולל חנויות עודפים<br />
- הכרטיס כולל כפל מבצעים והנחות (גם בסוף עונה) לא כולל הנחות חברי מועדון<br />
- לצפייה במגבלות, יש ללחוץ על בית העסק הרצוי:<br />
<strong>אופנה ופנאי:</strong></p>
<p><a href="#Foot locker">Foot locker</a><br />
<a href="#אדידס">אדידס</a><br />
NINNYO TLV</p>

<p><strong>אופנה ופנאי:</strong></p>
<p><u><strong>Foot locker</strong><a id="Foot locker" name="Foot locker"></a></u><br />
- לא ניתן לממש כרטיס מכל סוג שהוא ברכישת נעלי השקה<br />
- בסניפי עודפים ניתן לממש על קולקציה חדשה בלבד</p>
<p><u><strong>אדידס</strong><a id="אדידס" name="אדידס"></a></u><br />
- לא כולל חנויות עודפים, חנויות POP UP<br />
- לא ניתן לממש ב- <strong>factory54cafe</strong><br />
<br />
<u><strong>NINNYO TLV</strong></u><br />
- לא כולל עסקיות ו- Happy hour</p>
"""


class TestParseLimitationsPage:
    def test_general_block_stops_at_the_index_marker(self) -> None:
        result = parse_limitations_page(_PAGE)
        assert result.general == (
            "- לא כולל חנויות עודפים\n"
            "- הכרטיס כולל כפל מבצעים והנחות (גם בסוף עונה) לא כולל הנחות חברי מועדון"
        )

    def test_per_chain_block_excludes_its_own_heading(self) -> None:
        result = parse_limitations_page(_PAGE)
        foot_locker = result.lookup("Foot locker")
        assert foot_locker is not None
        assert "Foot locker" not in foot_locker
        assert "נעלי השקה" in foot_locker

    def test_unanchored_heading_still_starts_its_own_section(self) -> None:
        # NINNYO TLV has no anchor on the real page. Splitting on anchors would
        # fold its Happy-hour exclusion into אדידס.
        result = parse_limitations_page(_PAGE)
        assert result.lookup("NINNYO TLV") == "- לא כולל עסקיות ו- Happy hour"
        adidas = result.lookup("אדידס")
        assert adidas is not None
        assert "Happy hour" not in adidas

    def test_inline_bold_inside_a_bullet_does_not_split_a_section(self) -> None:
        adidas = parse_limitations_page(_PAGE).lookup("אדידס")
        assert adidas is not None
        assert "factory54cafe" in adidas
        assert "POP UP" in adidas

    def test_category_headings_are_not_chains(self) -> None:
        result = parse_limitations_page(_PAGE)
        assert result.lookup("אופנה ופנאי") is None

    def test_page_without_headings_yields_no_chains(self) -> None:
        result = parse_limitations_page("<p>לצפייה במגבלות</p><p><a href='#x'>x</a></p>")
        assert result.by_chain == {}


class TestLookup:
    def test_matches_across_punctuation_and_hebrew_final_forms(self) -> None:
        limits = BehatsdaaLimitations(general="", by_chain={"מוצצימ": "- עד 1,000 ₪"})
        assert limits.lookup("מוצצים") == "- עד 1,000 ₪"

    def test_online_variant_inherits_the_brands_limitations(self) -> None:
        limits = BehatsdaaLimitations(general="", by_chain={"ויקטורי": "- לא תקף על סיגריות"})
        assert limits.lookup("ויקטורי אונליין") == "- לא תקף על סיגריות"
        assert limits.lookup("SIMMONS online") is None  # no such brand block

    def test_alias_bridges_a_latin_chain_name_to_a_hebrew_heading(self) -> None:
        limits = BehatsdaaLimitations(general="", by_chain={"אייס": "- סכום מקסימלי בעסקה 500 ₪"})
        assert limits.lookup("ACE") == "- סכום מקסימלי בעסקה 500 ₪"

    def test_joint_heading_covers_a_single_brand_from_the_group(self) -> None:
        limits = BehatsdaaLimitations(
            general="", by_chain={"רשתותפקטורי54טומיהילפיגר": "- לא כולל חנויות עודפים"}
        )
        assert limits.lookup("פקטורי 54") == "- לא כולל חנויות עודפים"

    def test_does_not_match_a_longer_chain_name_onto_a_shorter_brand(self) -> None:
        # "אייס קיוב" is a different business from "אייס" — inheriting ACE's
        # 500 ₪ ceiling would be worse than having no limitations at all.
        limits = BehatsdaaLimitations(general="", by_chain={"אייס": "- סכום מקסימלי בעסקה 500 ₪"})
        assert limits.lookup("אייס קיוב") is None

    def test_short_names_never_match_by_containment(self) -> None:
        limits = BehatsdaaLimitations(general="", by_chain={"אבגדה": "- x"})
        assert limits.lookup("אבג") is None

    def test_blank_name_is_a_miss(self) -> None:
        assert BehatsdaaLimitations(general="", by_chain={"x": "- y"}).lookup("") is None


class TestLoadLimitations:
    def test_missing_snapshot_degrades_to_empty_not_an_error(self, tmp_path: Path) -> None:
        result = load_limitations(tmp_path / "nope.html")
        assert result.general == ""
        assert result.by_chain == {}

    def test_bundled_snapshot_parses(self) -> None:
        # The committed snapshot is what production reads; a layout change on
        # dts.co.il that breaks parsing should fail here, not silently strip
        # every Behatsdaa deal's constraints.
        path = (
            Path(__file__).resolve().parents[3]
            / "data"
            / "behatsdaa_snapshots"
            / "behatsdaa_chain_limitations.html"
        )
        result = load_limitations(path)
        assert "לא כולל חנויות עודפים" in result.general
        assert len(result.by_chain) > 100
        # Spot-check the two shapes most likely to regress.
        assert result.lookup("NINNYO TLV") == "- לא כולל עסקיות ו- Happy hour"
        crown_plaza = result.lookup("מלון קראון פלאזה תל אביב")
        assert crown_plaza is not None and "750" in crown_plaza
