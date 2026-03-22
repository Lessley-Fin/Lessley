from __future__ import annotations

import pytest
from pathlib import Path

from lessley_deals.domain.enums import AliasSource, ReviewStatus
from lessley_deals.domain.models import ExternalReference
from lessley_deals.persistence.id_gen import generate_id
from lessley_deals.persistence.repositories.aliases import AliasJsonRepository
from lessley_deals.persistence.repositories.deals import DealJsonRepository
from lessley_deals.persistence.repositories.external_refs import ExternalRefJsonRepository
from lessley_deals.persistence.repositories.raw_deals import RawDealJsonRepository
from lessley_deals.persistence.repositories.raw_stores import RawStoreJsonRepository
from lessley_deals.persistence.repositories.reviews import ReviewJsonRepository
from lessley_deals.persistence.repositories.stores import CanonicalStoreJsonRepository
from tests.factories import (
    make_alias,
    make_deal,
    make_raw_deal,
    make_raw_store,
    make_review_item,
    make_store,
)


pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# RawDealJsonRepository
# ---------------------------------------------------------------------------

class TestRawDealRepository:
    def test_save_and_get_all(self, tmp_path: Path) -> None:
        repo = RawDealJsonRepository(tmp_path / "raw_deals.json")
        deal = make_raw_deal()
        repo.save(deal)
        result = repo.get_all()
        assert len(result) == 1
        assert result[0].id == deal.id
        assert result[0].store_name == deal.store_name

    def test_exists_by_fingerprint(self, tmp_path: Path) -> None:
        repo = RawDealJsonRepository(tmp_path / "raw_deals.json")
        deal = make_raw_deal()
        repo.save(deal)
        assert repo.exists_by_fingerprint(deal.fingerprint) is True
        assert repo.exists_by_fingerprint("nonexistent_fp") is False

    def test_get_by_source(self, tmp_path: Path) -> None:
        repo = RawDealJsonRepository(tmp_path / "raw_deals.json")
        d1 = make_raw_deal(source_id="shufersal")
        d2 = make_raw_deal(source_id="rami_levy")
        d3 = make_raw_deal(source_id="shufersal")
        repo.save_many([d1, d2, d3])

        result = repo.get_by_source("shufersal")
        assert len(result) == 2
        assert all(r.source_id == "shufersal" for r in result)

    def test_get_by_id(self, tmp_path: Path) -> None:
        repo = RawDealJsonRepository(tmp_path / "raw_deals.json")
        deal = make_raw_deal()
        repo.save(deal)
        found = repo.get_by_id(deal.id)
        assert found is not None
        assert found.id == deal.id
        assert repo.get_by_id("nonexistent") is None

    def test_save_many(self, tmp_path: Path) -> None:
        repo = RawDealJsonRepository(tmp_path / "raw_deals.json")
        deals = [make_raw_deal() for _ in range(5)]
        repo.save_many(deals)
        assert len(repo.get_all()) == 5


# ---------------------------------------------------------------------------
# RawStoreJsonRepository
# ---------------------------------------------------------------------------

class TestRawStoreRepository:
    def test_save_many_and_get_all(self, tmp_path: Path) -> None:
        repo = RawStoreJsonRepository(tmp_path / "raw_stores.json")
        stores = [
            make_raw_store(name="Store A"),
            make_raw_store(name="Store B"),
        ]
        repo.save_many(stores)
        result = repo.get_all()
        assert len(result) == 2
        names = {s.name for s in result}
        assert names == {"Store A", "Store B"}

    def test_exists_by_fingerprint(self, tmp_path: Path) -> None:
        repo = RawStoreJsonRepository(tmp_path / "raw_stores.json")
        store = make_raw_store()
        repo.save(store)
        assert repo.exists_by_fingerprint(store.fingerprint) is True
        assert repo.exists_by_fingerprint("nonexistent_fp") is False

    def test_get_by_source(self, tmp_path: Path) -> None:
        repo = RawStoreJsonRepository(tmp_path / "raw_stores.json")
        s1 = make_raw_store(source_id="src_a")
        s2 = make_raw_store(source_id="src_b")
        repo.save_many([s1, s2])
        result = repo.get_by_source("src_a")
        assert len(result) == 1
        assert result[0].source_id == "src_a"


# ---------------------------------------------------------------------------
# CanonicalStoreJsonRepository
# ---------------------------------------------------------------------------

class TestCanonicalStoreRepository:
    def test_save_and_get_by_id(self, tmp_path: Path) -> None:
        repo = CanonicalStoreJsonRepository(tmp_path / "stores.json")
        store = make_store(name="Shufersal")
        repo.save(store)
        found = repo.get_by_id(store.id)
        assert found is not None
        assert found.name == "Shufersal"

    def test_save_updates_existing(self, tmp_path: Path) -> None:
        repo = CanonicalStoreJsonRepository(tmp_path / "stores.json")
        store = make_store(name="Old Name")
        repo.save(store)

        # Update the same store (same id)
        store.name = "New Name"
        repo.save(store)

        all_stores = repo.get_all()
        assert len(all_stores) == 1
        assert all_stores[0].name == "New Name"

    def test_search(self, tmp_path: Path) -> None:
        repo = CanonicalStoreJsonRepository(tmp_path / "stores.json")
        repo.save(make_store(name="Shufersal Deal"))
        repo.save(make_store(name="Rami Levy"))
        repo.save(make_store(name="Mega"))

        result = repo.search("shufersal")
        assert len(result) == 1
        assert result[0].name == "Shufersal Deal"

    def test_search_case_insensitive(self, tmp_path: Path) -> None:
        repo = CanonicalStoreJsonRepository(tmp_path / "stores.json")
        repo.save(make_store(name="Rami Levy"))
        result = repo.search("RAMI")
        assert len(result) == 1

    def test_get_by_id_missing_returns_none(self, tmp_path: Path) -> None:
        repo = CanonicalStoreJsonRepository(tmp_path / "stores.json")
        assert repo.get_by_id("nonexistent") is None


# ---------------------------------------------------------------------------
# AliasJsonRepository
# ---------------------------------------------------------------------------

class TestAliasRepository:
    def test_save_and_get_all(self, tmp_path: Path) -> None:
        repo = AliasJsonRepository(tmp_path / "aliases.json")
        store_id = generate_id()
        alias = make_alias(store_id, "Shufersal")
        repo.save(alias)
        result = repo.get_all()
        assert len(result) == 1
        assert result[0].alias == "Shufersal"

    def test_find_by_alias(self, tmp_path: Path) -> None:
        repo = AliasJsonRepository(tmp_path / "aliases.json")
        store_id = generate_id()
        alias = make_alias(store_id, "Shufersal Deal")
        repo.save(alias)

        # find_by_alias compares alias_forms.normalized (lowercased)
        found = repo.find_by_alias("shufersal deal")
        assert found is not None
        assert found.store_id == store_id

        assert repo.find_by_alias("nonexistent") is None

    def test_get_by_store(self, tmp_path: Path) -> None:
        repo = AliasJsonRepository(tmp_path / "aliases.json")
        store_a = generate_id()
        store_b = generate_id()
        repo.save(make_alias(store_a, "Alias A1"))
        repo.save(make_alias(store_a, "Alias A2"))
        repo.save(make_alias(store_b, "Alias B1"))

        result = repo.get_by_store(store_a)
        assert len(result) == 2
        assert all(a.store_id == store_a for a in result)

    def test_delete(self, tmp_path: Path) -> None:
        repo = AliasJsonRepository(tmp_path / "aliases.json")
        store_id = generate_id()
        alias = make_alias(store_id, "To Delete")
        repo.save(alias)
        assert len(repo.get_all()) == 1

        repo.delete(alias.id)
        assert len(repo.get_all()) == 0


# ---------------------------------------------------------------------------
# DealJsonRepository
# ---------------------------------------------------------------------------

class TestDealRepository:
    def test_save_and_get_by_store(self, tmp_path: Path) -> None:
        repo = DealJsonRepository(tmp_path / "deals.json")
        store_id = generate_id()
        deal = make_deal(store_id=store_id)
        repo.save(deal)

        result = repo.get_by_store(store_id)
        assert len(result) == 1
        assert result[0].store_id == store_id

    def test_exists_by_fingerprint(self, tmp_path: Path) -> None:
        repo = DealJsonRepository(tmp_path / "deals.json")
        deal = make_deal()
        repo.save(deal)
        assert repo.exists_by_fingerprint(deal.fingerprint) is True
        assert repo.exists_by_fingerprint("nonexistent_fp") is False

    def test_get_all(self, tmp_path: Path) -> None:
        repo = DealJsonRepository(tmp_path / "deals.json")
        repo.save(make_deal())
        repo.save(make_deal())
        assert len(repo.get_all()) == 2


# ---------------------------------------------------------------------------
# ReviewJsonRepository
# ---------------------------------------------------------------------------

class TestReviewRepository:
    def test_save_and_get_pending(self, tmp_path: Path) -> None:
        repo = ReviewJsonRepository(tmp_path / "reviews.json")
        item = make_review_item()
        repo.save(item)

        pending = repo.get_pending()
        assert len(pending) == 1
        assert pending[0].id == item.id
        assert pending[0].status == ReviewStatus.PENDING

    def test_update(self, tmp_path: Path) -> None:
        repo = ReviewJsonRepository(tmp_path / "reviews.json")
        item = make_review_item()
        repo.save(item)

        # Mutate and update
        item.status = ReviewStatus.APPROVED
        repo.update(item)

        updated = repo.get_by_id(item.id)
        assert updated is not None
        assert updated.status == ReviewStatus.APPROVED

    def test_get_all(self, tmp_path: Path) -> None:
        repo = ReviewJsonRepository(tmp_path / "reviews.json")
        repo.save(make_review_item())
        repo.save(make_review_item())
        assert len(repo.get_all()) == 2

    def test_get_pending_excludes_non_pending(self, tmp_path: Path) -> None:
        repo = ReviewJsonRepository(tmp_path / "reviews.json")
        pending = make_review_item()
        approved = make_review_item()
        repo.save(pending)
        repo.save(approved)

        approved.status = ReviewStatus.APPROVED
        repo.update(approved)

        result = repo.get_pending()
        assert len(result) == 1
        assert result[0].id == pending.id


# ---------------------------------------------------------------------------
# ExternalRefJsonRepository
# ---------------------------------------------------------------------------

class TestExternalRefRepository:
    def _make_ref(self, store_id: str, system: str = "pos") -> ExternalReference:
        return ExternalReference(
            id=generate_id(),
            store_id=store_id,
            system=system,
            external_id=f"ext_{generate_id()}",
            metadata={},
        )

    def test_save_and_get_by_store(self, tmp_path: Path) -> None:
        repo = ExternalRefJsonRepository(tmp_path / "ext_refs.json")
        store_id = generate_id()
        ref = self._make_ref(store_id)
        repo.save(ref)

        result = repo.get_by_store(store_id)
        assert len(result) == 1
        assert result[0].store_id == store_id

    def test_get_by_system(self, tmp_path: Path) -> None:
        repo = ExternalRefJsonRepository(tmp_path / "ext_refs.json")
        store_id = generate_id()
        repo.save(self._make_ref(store_id, system="pos"))
        repo.save(self._make_ref(store_id, system="erp"))

        result = repo.get_by_system("pos")
        assert len(result) == 1
        assert result[0].system == "pos"

    def test_delete(self, tmp_path: Path) -> None:
        repo = ExternalRefJsonRepository(tmp_path / "ext_refs.json")
        store_id = generate_id()
        ref = self._make_ref(store_id)
        repo.save(ref)
        assert len(repo.get_by_store(store_id)) == 1

        repo.delete(ref.id)
        assert len(repo.get_by_store(store_id)) == 0
