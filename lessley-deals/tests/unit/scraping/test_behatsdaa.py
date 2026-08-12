from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lessley_deals.scraping.base import SourceConfig
from lessley_deals.scraping.sources.behatsdaa import BehatsdaaAdapter, _GiftcardSpec


def _chain(
    chain_id: int = 107,
    chain_name: str = "קינג סטור",
    website: str | None = "https://www.kingstore.co.il",
    logo: str | None = "https://pics.example/logo.png",
    **overrides: Any,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "errorID": "0",
        "chainID": chain_id,
        "chainName": chain_name,
        "logoURL": logo,
        "webSite": website,
    }
    record.update(overrides)
    return record


def _chains_payload(chains: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": True,
        "data": [{"tagName": "food", "walletChainData": chains}],
        "message": None,
    }


def _write_chain_file(dir_path: Path, filename: str, chains: list[dict[str, Any]]) -> None:
    (dir_path / filename).write_text(
        json.dumps(_chains_payload(chains), ensure_ascii=False), encoding="utf-8"
    )


def _write_config(dir_path: Path, entries: dict[str, Any], filename: str = "behatsdaa_giftcards_config.json") -> Path:
    path = dir_path / filename
    path.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    return path


def _spec(
    giftcard_id: str = "2110",
    file: Path | None = None,
    name: str = "15% ארנק",
    discount_percent: float = 15.0,
    max_deposit_per_month: float | None = 500.0,
    currency: str = "ILS",
    notes: str = "",
) -> _GiftcardSpec:
    return _GiftcardSpec(
        id=giftcard_id,
        file=file or Path("unused.json"),
        name=name,
        discount_percent=discount_percent,
        max_deposit_per_month=max_deposit_per_month,
        currency=currency,
        notes=notes,
    )


class TestBehatsdaaAdapterBasics:
    def test_source_id(self) -> None:
        adapter = BehatsdaaAdapter(SourceConfig(base_url="https://www.behatsdaa.org.il"))
        assert adapter.source_id == "behatsdaa"

    def test_extract_chains_flattens_groups(self) -> None:
        adapter = BehatsdaaAdapter(SourceConfig(base_url="https://www.behatsdaa.org.il"))
        payload = {
            "status": True,
            "data": [
                {"walletChainData": [_chain(chain_id=1, chain_name="A")]},
                {"walletChainData": [_chain(chain_id=2, chain_name="B")]},
            ],
        }
        chains = adapter._extract_chains(payload)
        assert [c["chainName"] for c in chains] == ["A", "B"]

    def test_extract_chains_status_false_returns_empty(self) -> None:
        adapter = BehatsdaaAdapter(SourceConfig(base_url="https://www.behatsdaa.org.il"))
        assert adapter._extract_chains({"status": False, "data": [{"walletChainData": [_chain()]}]}) == []

    def test_extract_chains_non_dict_payload_returns_empty(self) -> None:
        adapter = BehatsdaaAdapter(SourceConfig(base_url="https://www.behatsdaa.org.il"))
        assert adapter._extract_chains(["not", "a", "dict"]) == []


class TestGiftcardSpecMapping:
    def test_to_raw_store_uses_cleaned_name_and_normalized_url(self) -> None:
        adapter = BehatsdaaAdapter(SourceConfig(base_url="https://www.behatsdaa.org.il"))
        now = datetime.now(timezone.utc)
        store = adapter._to_raw_store(_chain(chain_name="קינג סטור_2", website="www.kingstore.co.il"), "קינג סטור", now)
        assert store.source_id == "behatsdaa"
        assert store.name == "קינג סטור"
        assert store.url == "https://kingstore.co.il"

    def test_to_raw_deal_price_text_and_discount_logic_reflect_the_giftcard(self) -> None:
        adapter = BehatsdaaAdapter(SourceConfig(base_url="https://www.behatsdaa.org.il"))
        now = datetime.now(timezone.utc)
        spec = _spec(discount_percent=15.0, max_deposit_per_month=500.0, name="15% ארנק")
        deal = adapter._to_raw_deal(_chain(), "קינג סטור", spec, now)

        assert deal.price_text == "15% הנחה בטעינה (עד 500 ₪ לחודש) - 15% ארנק"
        reward = deal.raw_payload["discount_logic"]["reward"]
        assert reward["value"] == 0.15
        # 15% of the 500 ₪/month cap is the real max discount reachable per month.
        assert reward["max_discount_amount"] == 75.0
        assert deal.raw_payload["deal_type"] == "giftcard_discount"
        assert deal.raw_payload["currency"] == "ILS"

    def test_to_raw_deal_without_deposit_cap_omits_max_discount_amount(self) -> None:
        adapter = BehatsdaaAdapter(SourceConfig(base_url="https://www.behatsdaa.org.il"))
        now = datetime.now(timezone.utc)
        spec = _spec(discount_percent=7.5, max_deposit_per_month=None)
        deal = adapter._to_raw_deal(_chain(), "קינג סטור", spec, now)

        assert "עד" not in deal.price_text
        assert "max_discount_amount" not in deal.raw_payload["discount_logic"]["reward"]

    def test_to_raw_deal_notes_are_prepended_to_terms(self) -> None:
        adapter = BehatsdaaAdapter(SourceConfig(base_url="https://www.behatsdaa.org.il"))
        now = datetime.now(timezone.utc)
        spec = _spec(notes="לא כולל מוצרי חשמל.")
        deal = adapter._to_raw_deal(_chain(), "קינג סטור", spec, now)
        assert deal.raw_payload["terms_and_conditions"].startswith("לא כולל מוצרי חשמל.")

    def test_to_raw_deal_fingerprint_differs_by_giftcard_for_the_same_chain(self) -> None:
        # Same chain accepted by two different wallets at different rates —
        # RawScrapedRecord.fingerprint must not collide, or ScrapeStage's
        # dedup would silently drop one of the two real, distinct deals.
        adapter = BehatsdaaAdapter(SourceConfig(base_url="https://www.behatsdaa.org.il"))
        now = datetime.now(timezone.utc)
        chain = _chain()
        spec_a = _spec(giftcard_id="2110", name="15% ארנק", discount_percent=15.0)
        spec_b = _spec(giftcard_id="2809", name="20% ארנק", discount_percent=20.0)
        d1 = adapter._to_raw_deal(chain, "קינג סטור", spec_a, now)
        d2 = adapter._to_raw_deal(chain, "קינג סטור", spec_b, now)
        assert d1.fingerprint != d2.fingerprint
        assert d1.deal_description != d2.deal_description

    def test_to_raw_deal_raw_payload_carries_title_and_full_description(self) -> None:
        # PersistStage reads deal_title/full_description straight off
        # raw_payload with no fallback, same convention as hever.py.
        adapter = BehatsdaaAdapter(SourceConfig(base_url="https://www.behatsdaa.org.il"))
        now = datetime.now(timezone.utc)
        deal = adapter._to_raw_deal(_chain(chain_name="קינג סטור"), "קינג סטור", _spec(), now)
        assert deal.raw_payload["deal_title"] == "קינג סטור" == deal.store_name
        assert deal.raw_payload["full_description"]


class TestGiftcardConfigLoading:
    def test_loads_valid_entries_and_resolves_file_relative_to_config_dir(self, tmp_path: Path) -> None:
        _write_chain_file(tmp_path, "wallet_a.json", [_chain()])
        config_path = _write_config(
            tmp_path,
            {
                "2110": {
                    "file": "wallet_a.json",
                    "name": "15% ארנק",
                    "discount_percent": 15,
                    "max_deposit_per_month": 500,
                }
            },
        )
        adapter = BehatsdaaAdapter(SourceConfig(base_url="https://www.behatsdaa.org.il"))
        specs = adapter._load_giftcard_specs(config_path)
        assert len(specs) == 1
        assert specs[0].file == tmp_path / "wallet_a.json"
        assert specs[0].discount_percent == 15.0

    def test_comment_keys_are_skipped(self, tmp_path: Path) -> None:
        _write_chain_file(tmp_path, "wallet_a.json", [_chain()])
        config_path = _write_config(
            tmp_path,
            {
                "_comment": "not a giftcard",
                "_example": {"file": "nope.json", "discount_percent": 1},
                "2110": {"file": "wallet_a.json", "name": "x", "discount_percent": 15},
            },
        )
        adapter = BehatsdaaAdapter(SourceConfig(base_url="https://www.behatsdaa.org.il"))
        specs = adapter._load_giftcard_specs(config_path)
        assert [s.id for s in specs] == ["2110"]

    def test_entry_missing_discount_percent_is_skipped(self, tmp_path: Path) -> None:
        _write_chain_file(tmp_path, "wallet_a.json", [_chain()])
        config_path = _write_config(
            tmp_path, {"2110": {"file": "wallet_a.json", "name": "x", "discount_percent": None}}
        )
        adapter = BehatsdaaAdapter(SourceConfig(base_url="https://www.behatsdaa.org.il"))
        assert adapter._load_giftcard_specs(config_path) == []

    def test_entry_marked_inactive_is_skipped(self, tmp_path: Path) -> None:
        _write_chain_file(tmp_path, "wallet_a.json", [_chain()])
        config_path = _write_config(
            tmp_path,
            {"2110": {"file": "wallet_a.json", "name": "x", "discount_percent": 15, "active": False}},
        )
        adapter = BehatsdaaAdapter(SourceConfig(base_url="https://www.behatsdaa.org.il"))
        assert adapter._load_giftcard_specs(config_path) == []

    def test_entry_with_missing_file_is_skipped(self, tmp_path: Path) -> None:
        config_path = _write_config(
            tmp_path, {"2110": {"file": "does_not_exist.json", "name": "x", "discount_percent": 15}}
        )
        adapter = BehatsdaaAdapter(SourceConfig(base_url="https://www.behatsdaa.org.il"))
        assert adapter._load_giftcard_specs(config_path) == []

    def test_missing_config_file_returns_empty(self, tmp_path: Path) -> None:
        adapter = BehatsdaaAdapter(SourceConfig(base_url="https://www.behatsdaa.org.il"))
        assert adapter._load_giftcard_specs(tmp_path / "missing.json") == []

    def test_non_dict_config_returns_empty(self, tmp_path: Path) -> None:
        config_path = _write_config(tmp_path, {})
        config_path.write_text("[1, 2, 3]", encoding="utf-8")
        adapter = BehatsdaaAdapter(SourceConfig(base_url="https://www.behatsdaa.org.il"))
        assert adapter._load_giftcard_specs(config_path) == []


class TestBehatsdaaAdapterScrape:
    async def test_scrape_end_to_end_across_two_giftcards(self, tmp_path: Path) -> None:
        _write_chain_file(tmp_path, "wallet_15.json", [_chain(chain_id=1, chain_name="קינג סטור")])
        _write_chain_file(
            tmp_path,
            "wallet_20.json",
            [_chain(chain_id=1, chain_name="קינג סטור"), _chain(chain_id=2, chain_name="ויקטורי")],
        )
        config_path = _write_config(
            tmp_path,
            {
                "2110": {
                    "file": "wallet_15.json", "name": "15% ארנק",
                    "discount_percent": 15, "max_deposit_per_month": 500,
                },
                "2809": {
                    "file": "wallet_20.json", "name": "20% ארנק",
                    "discount_percent": 20, "max_deposit_per_month": 300,
                },
            },
        )
        adapter = BehatsdaaAdapter(
            SourceConfig(base_url="https://www.behatsdaa.org.il"), giftcards_config_path=config_path
        )
        stores, deals = await adapter.scrape()

        # קינג סטור is shared by both wallets -> one store, two deals.
        assert sorted(s.name for s in stores) == ["ויקטורי", "קינג סטור"]
        assert len(deals) == 3
        king_store_deals = [d for d in deals if d.store_name == "קינג סטור"]
        assert len(king_store_deals) == 2
        assert king_store_deals[0].fingerprint != king_store_deals[1].fingerprint

    async def test_scrape_filters_generic_behatsdaa_brand(self, tmp_path: Path) -> None:
        _write_chain_file(
            tmp_path,
            "wallet_15.json",
            [_chain(chain_name="בהצדעה"), _chain(chain_id=2, chain_name="קינג סטור")],
        )
        config_path = _write_config(
            tmp_path, {"2110": {"file": "wallet_15.json", "name": "15% ארנק", "discount_percent": 15}}
        )
        adapter = BehatsdaaAdapter(
            SourceConfig(base_url="https://www.behatsdaa.org.il"), giftcards_config_path=config_path
        )
        stores, deals = await adapter.scrape()
        assert [s.name for s in stores] == ["קינג סטור"]

    async def test_scrape_with_no_usable_giftcards_returns_empty(self, tmp_path: Path) -> None:
        config_path = _write_config(tmp_path, {})
        adapter = BehatsdaaAdapter(
            SourceConfig(base_url="https://www.behatsdaa.org.il"), giftcards_config_path=config_path
        )
        stores, deals = await adapter.scrape()
        assert stores == []
        assert deals == []

    async def test_scrape_defaults_to_the_bundled_data_config(self) -> None:
        # No giftcards_config_path override -> resolves to
        # data/behatsdaa_snapshots/behatsdaa_giftcards_config.json relative
        # to the package root.
        # Should not raise even before real discount numbers are filled in.
        adapter = BehatsdaaAdapter(SourceConfig(base_url="https://www.behatsdaa.org.il"))
        stores, deals = await adapter.scrape()
        assert isinstance(stores, list)
        assert isinstance(deals, list)


def test_clubs_json_has_a_matching_entry_for_behatsdaa() -> None:
    """PersistStage sets Deal.club_id by looking up Club.source_id — a
    clubs.json entry is what actually gives Behatsdaa deals a club_id."""
    clubs_path = Path(__file__).resolve().parents[3] / "data" / "clubs.json"
    clubs = json.loads(clubs_path.read_text(encoding="utf-8"))
    behatsdaa_club = next((c for c in clubs if c["source_id"] == "behatsdaa"), None)
    assert behatsdaa_club is not None
    assert behatsdaa_club["id"] == "club_behatsdaa"
