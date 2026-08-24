"""The reference cache is rebuilt on a timer, and a failed rebuild must not empty it.

Deals are scraped continuously. A cache loaded only at startup makes every deal added
afterwards invisible to missed-savings and club matching until the process restarts — a
failure with no symptom except quietly thinner results, which is why the refresh exists.

The refresh runs against a live service, so the interesting case is not the happy path but
what a reader sees while a rebuild is in flight or after one has failed. ``load_async``
builds into locals and publishes in one block precisely so the answer is "the previous
snapshot, in full" rather than "whatever had been assigned so far".
"""

import pytest

from services.reference_data_repository import ReferenceDataRepository


class _Doc:
    """Stands in for a Beanie document class returning fixed rows.

    Both entry points the repository uses are supported: ``find_all()`` for the
    collections it loads whole, and ``find(query)`` for deals, which are filtered
    on their lifecycle. The query is recorded so a test can assert on it.
    """

    def __init__(self, rows: list, fails: bool = False):
        self._rows = rows
        self._fails = fails
        self.last_query: dict | None = None

    def find_all(self):
        if self._fails:
            raise RuntimeError("mongo is down")
        return self

    def find(self, query=None):
        self.last_query = query
        return self.find_all()

    async def to_list(self):
        return self._rows


def _store(store_id: str, name: str, mcc: str):
    from types import SimpleNamespace

    return SimpleNamespace(
        store_id=store_id,
        name=name,
        names=[name],
        metadata=SimpleNamespace(mcc_codes=[mcc]),
    )


def _patch_sources(monkeypatch, stores: _Doc, deals: _Doc, clubs: _Doc):
    import services.reference_data_repository as module

    monkeypatch.setattr(module, "Store", stores)
    monkeypatch.setattr(module, "Deal", deals)
    monkeypatch.setattr(module, "Club", clubs)
    monkeypatch.setattr(module, "StoreAlias", _Doc([]))
    # Identity folding is exercised elsewhere; here it only needs to not touch the database.
    monkeypatch.setattr(module, "build_identities", lambda *_: {})
    monkeypatch.setattr(module, "DealShopFinder", lambda identities: [])


async def _load(monkeypatch, repo, stores, force=False, deals_fail=False):
    _patch_sources(
        monkeypatch,
        _Doc(stores),
        _Doc([], fails=deals_fail),
        _Doc([]),
    )
    await repo.load_async(force=force)


@pytest.mark.asyncio
async def test_a_second_load_is_skipped_unless_forced(monkeypatch):
    repo = ReferenceDataRepository()

    await _load(monkeypatch, repo, [_store("s1", "First", "GROCERIES")])
    assert set(repo._stores) == {"s1"}

    # Without force, an already-loaded cache is left alone even though the source has changed.
    await _load(monkeypatch, repo, [_store("s2", "Second", "GROCERIES")])
    assert set(repo._stores) == {"s1"}


@pytest.mark.asyncio
async def test_forcing_a_reload_picks_up_newly_scraped_rows(monkeypatch):
    repo = ReferenceDataRepository()

    await _load(monkeypatch, repo, [_store("s1", "First", "GROCERIES")])
    await _load(monkeypatch, repo, [_store("s1", "First", "GROCERIES"), _store("s2", "Second", "FUEL")], force=True)

    assert set(repo._stores) == {"s1", "s2"}
    assert set(repo._stores_by_category) == {"GROCERIES", "FUEL"}


@pytest.mark.asyncio
async def test_a_failed_refresh_keeps_the_previous_snapshot(monkeypatch):
    repo = ReferenceDataRepository()

    await _load(monkeypatch, repo, [_store("s1", "First", "GROCERIES")])

    # The store read succeeds and the deal read then fails, so the rebuild dies half-way —
    # the exact shape that would leave a mutate-in-place cache holding new stores and no deals.
    with pytest.raises(RuntimeError):
        await _load(
            monkeypatch,
            repo,
            [_store("s9", "Replacement", "FUEL")],
            force=True,
            deals_fail=True,
        )

    assert set(repo._stores) == {"s1"}, "a failed rebuild must not publish partial data"
    assert repo._loaded is True, "the cache is still usable, so it must still count as loaded"


@pytest.mark.asyncio
async def test_expired_deals_are_left_out_of_the_snapshot(monkeypatch):
    """Recommending a benefit that no longer exists is worse than missing one.

    The scraping pipeline flags deals its sources have stopped offering; loading
    them anyway would put retired offers into missed-savings analysis, where a
    user is told what they *should* have done.
    """
    deals = _Doc([])
    _patch_sources(monkeypatch, _Doc([]), deals, _Doc([]))

    await ReferenceDataRepository().load_async(force=True)

    assert deals.last_query == {"status": {"$ne": "expired"}}
