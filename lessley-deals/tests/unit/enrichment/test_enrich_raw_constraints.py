from __future__ import annotations

from typing import Sequence

from lessley_deals.domain.models import RawScrapedRecord
from lessley_deals.enrichment.constaints_parser import DealConstraints, empty_constraints
from lessley_deals.enrichment.enrich_raw_constraints import (
    enrich_raw_constraints,
    select_pending,
)
from tests.factories import make_raw_deal


def _terms(text: str = "ללא כפל מבצעים", **payload: object) -> dict[str, object]:
    return {"terms_and_conditions": text, **payload}


def _fixed_parser(_terms_text: str, _source_id: str | None = None) -> DealConstraints:
    return DealConstraints()


class FakeRawRepo:
    """In-memory stand-in for the raw deal repository, id-keyed like the real ones."""

    def __init__(self, records: Sequence[RawScrapedRecord]) -> None:
        self._records = {r.id: r for r in records}
        self.write_calls = 0

    def get_all(self) -> list[RawScrapedRecord]:
        return list(self._records.values())

    def update_many(self, records: Sequence[RawScrapedRecord]) -> int:
        self.write_calls += 1
        updated = 0
        for record in records:
            if record.id in self._records:
                self._records[record.id] = record
                updated += 1
        return updated


# --------------------------------------------------------------------------- #
# select_pending — which records are worth an LLM call                         #
# --------------------------------------------------------------------------- #

def test_select_pending_skips_records_without_terms() -> None:
    records = [
        make_raw_deal(id="a", raw_payload=_terms()),
        make_raw_deal(id="b", raw_payload={}),
        make_raw_deal(id="c", raw_payload={"terms_and_conditions": "   "}),
    ]

    assert [r.id for r in select_pending(records)] == ["a"]


def test_select_pending_skips_already_enriched_so_a_rerun_resumes() -> None:
    records = [
        make_raw_deal(id="done", raw_payload=_terms(constraints=empty_constraints())),
        make_raw_deal(id="todo", raw_payload=_terms()),
    ]

    assert [r.id for r in select_pending(records)] == ["todo"]


def test_select_pending_force_reparses_enriched_records() -> None:
    records = [
        make_raw_deal(id="done", raw_payload=_terms(constraints=empty_constraints())),
        make_raw_deal(id="todo", raw_payload=_terms()),
    ]

    assert {r.id for r in select_pending(records, force=True)} == {"done", "todo"}


def test_select_pending_filters_by_source_and_limit() -> None:
    records = [
        make_raw_deal(id="h1", source_id="hot", raw_payload=_terms()),
        make_raw_deal(id="h2", source_id="hot", raw_payload=_terms()),
        make_raw_deal(id="b1", source_id="behatsdaa", raw_payload=_terms()),
    ]

    assert {r.id for r in select_pending(records, source="hot")} == {"h1", "h2"}
    assert len(select_pending(records, limit=2)) == 2


# --------------------------------------------------------------------------- #
# enrich_raw_constraints — writes, checkpoints, isolation                      #
# --------------------------------------------------------------------------- #

async def test_writes_constraints_onto_raw_payload() -> None:
    repo = FakeRawRepo([make_raw_deal(id="a", raw_payload=_terms("ללא כפל מבצעים"))])

    stats = await enrich_raw_constraints(repo, parser=_fixed_parser)

    assert stats["processed"] == 1
    assert stats["failed"] == 0
    record = repo.get_all()[0]
    assert record.raw_payload["constraints"] == empty_constraints()
    # Only constraints is added — the terms text it was parsed from stays put.
    assert record.raw_payload["terms_and_conditions"] == "ללא כפל מבצעים"


async def test_checkpoints_every_chunk() -> None:
    # Distinct terms per record, so each is its own group and chunking is by 4.
    repo = FakeRawRepo(
        [make_raw_deal(id=f"d{i}", raw_payload=_terms(f"תנאי {i}")) for i in range(10)]
    )

    stats = await enrich_raw_constraints(repo, parser=_fixed_parser, chunk_size=4, concurrency=2)

    assert stats["processed"] == 10
    assert repo.write_calls == 3  # 4 + 4 + 2


async def test_identical_terms_cost_one_llm_call() -> None:
    parsed: list[str] = []

    def _counting(terms_text: str, _source_id: str | None = None) -> DealConstraints:
        parsed.append(terms_text)
        return DealConstraints()

    # 50 deals sharing one boilerplate — exactly the HOT shape.
    repo = FakeRawRepo(
        [make_raw_deal(id=f"d{i}", source_id="hot", raw_payload=_terms("אותו טקסט")) for i in range(50)]
    )

    stats = await enrich_raw_constraints(repo, parser=_counting)

    assert len(parsed) == 1
    assert stats["llm_calls"] == 1
    assert stats["processed"] == 50  # every deal still gets the block
    assert all(r.raw_payload["constraints"] == empty_constraints() for r in repo.get_all())


async def test_same_text_from_different_sources_is_parsed_separately() -> None:
    seen: list[tuple[str, str | None]] = []

    def _recording(terms_text: str, source_id: str | None = None) -> DealConstraints:
        seen.append((terms_text, source_id))
        return DealConstraints()

    # The prompt differs per source, so the same words can mean different things.
    repo = FakeRawRepo(
        [
            make_raw_deal(id="a", source_id="hot", raw_payload=_terms("זהה")),
            make_raw_deal(id="b", source_id="behatsdaa", raw_payload=_terms("זהה")),
        ]
    )

    stats = await enrich_raw_constraints(repo, parser=_recording)

    assert stats["llm_calls"] == 2
    assert {src for _, src in seen} == {"hot", "behatsdaa"}


async def test_a_failed_group_fails_every_deal_sharing_that_text() -> None:
    def _boom(_terms_text: str, _source_id: str | None = None) -> DealConstraints:
        raise RuntimeError("Request timed out.")

    repo = FakeRawRepo([make_raw_deal(id=f"d{i}", raw_payload=_terms("משותף")) for i in range(5)])

    stats = await enrich_raw_constraints(repo, parser=_boom)

    assert stats["llm_calls"] == 1
    assert stats["processed"] == 0
    assert stats["failed"] == 5  # counted per deal, not per call
    assert repo.write_calls == 0


async def test_dry_run_never_writes() -> None:
    repo = FakeRawRepo([make_raw_deal(id="a", raw_payload=_terms())])

    stats = await enrich_raw_constraints(repo, parser=_fixed_parser, dry_run=True)

    assert stats["processed"] == 1
    assert repo.write_calls == 0
    assert "constraints" not in repo.get_all()[0].raw_payload


async def test_a_failing_parse_is_counted_not_fatal() -> None:
    def _flaky(terms_text: str, _source_id: str | None = None) -> DealConstraints:
        if "boom" in terms_text:
            raise RuntimeError("Request timed out.")
        return DealConstraints()

    repo = FakeRawRepo(
        [
            make_raw_deal(id="ok", raw_payload=_terms("fine")),
            make_raw_deal(id="bad", raw_payload=_terms("boom")),
        ]
    )

    stats = await enrich_raw_constraints(repo, parser=_flaky)

    assert stats["processed"] == 1
    assert stats["failed"] == 1
    assert "constraints" in repo._records["ok"].raw_payload
    assert "constraints" not in repo._records["bad"].raw_payload


async def test_rerun_after_partial_success_only_parses_what_is_left() -> None:
    repo = FakeRawRepo(
        [
            make_raw_deal(id="a", raw_payload=_terms()),
            make_raw_deal(id="b", raw_payload=_terms()),
        ]
    )
    await enrich_raw_constraints(repo, parser=_fixed_parser, limit=1)

    parsed: list[str] = []

    def _tracking(terms_text: str, _source_id: str | None = None) -> DealConstraints:
        parsed.append(terms_text)
        return DealConstraints()

    stats = await enrich_raw_constraints(repo, parser=_tracking)

    assert len(parsed) == 1  # the already-enriched one is not paid for twice
    assert stats["processed"] == 1
    assert stats["skipped"] == 1


async def test_no_pending_records_is_a_no_op() -> None:
    repo = FakeRawRepo([make_raw_deal(id="a", raw_payload={})])

    stats = await enrich_raw_constraints(repo, parser=_fixed_parser)

    assert stats == {
        "total": 1,
        "pending": 0,
        "processed": 0,
        "skipped": 1,
        "failed": 0,
        "llm_calls": 0,
    }
    assert repo.write_calls == 0


async def test_source_id_is_passed_to_the_parser() -> None:
    seen: list[str | None] = []

    def _recording(_terms_text: str, source_id: str | None = None) -> DealConstraints:
        seen.append(source_id)
        return DealConstraints()

    repo = FakeRawRepo([make_raw_deal(id="a", source_id="behatsdaa", raw_payload=_terms())])

    await enrich_raw_constraints(repo, parser=_recording)

    assert seen == ["behatsdaa"]
