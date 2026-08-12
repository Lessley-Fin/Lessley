from __future__ import annotations

from datetime import UTC, datetime

from lessley_deals.domain.enums import MatchDecision
from lessley_deals.domain.models import (
    Explanation,
    MatchCandidate,
    MatchVerdict,
    NameForms,
    NormalizedRecord,
    PipelineRecord,
)
from lessley_deals.enrichment.constaints_parser import empty_constraints
from lessley_deals.persistence.repositories.deals import DealJsonRepository
from lessley_deals.persistence.repositories.reviews import ReviewJsonRepository
from lessley_deals.persistence.repositories.stores import CanonicalStoreJsonRepository
from lessley_deals.pipeline.persist_stage import PersistStage
from tests.factories import make_raw_deal


def _auto_match_setup(tmp_path):
    raw = make_raw_deal(id="r1", store_name="X", raw_payload={"deal_title": "X deal"})
    prec = PipelineRecord(raw=raw)
    normalized = NormalizedRecord(
        raw_id="r1",
        source_id=raw.source_id,
        store_name_forms=NameForms(normalized="x", compact="x", tokens=("x",)),
        deal_description="d",
        normalized_at=datetime(2026, 7, 6, tzinfo=UTC),
    )
    cand = MatchCandidate(store_id="s1", store_name="X", confidence=1.0, stage="exact_alias")
    verdict = MatchVerdict(
        record_id="r1",
        input_name="X",
        decision=MatchDecision.AUTO_MATCH,
        candidates=(cand,),
        explanation=Explanation(stages_run=("exact_alias",), reason="match"),
        best=cand,
    )
    stage = PersistStage(
        deal_repo=DealJsonRepository(tmp_path / "deals.json"),
        review_repo=ReviewJsonRepository(tmp_path / "reviews.json"),
        store_repo=CanonicalStoreJsonRepository(tmp_path / "stores.json"),
    )
    return stage, prec, normalized, verdict


async def test_constraints_map_lands_on_deal(tmp_path) -> None:
    stage, prec, normalized, verdict = _auto_match_setup(tmp_path)
    constraints = empty_constraints()
    constraints["limits"]["max_uses_per_transaction"] = 2

    await stage.run(
        pipeline_records=[prec],
        normalized_map={"r1": normalized},
        verdict_map={"r1": verdict},
        constraints_map={"r1": constraints},
    )

    saved = stage._deal_repo.get_all()  # type: ignore[attr-defined]
    assert len(saved) == 1
    assert saved[0].constraints == constraints


async def test_no_constraints_map_leaves_deal_unconstrained(tmp_path) -> None:
    stage, prec, normalized, verdict = _auto_match_setup(tmp_path)

    await stage.run(
        pipeline_records=[prec],
        normalized_map={"r1": normalized},
        verdict_map={"r1": verdict},
    )

    saved = stage._deal_repo.get_all()  # type: ignore[attr-defined]
    assert len(saved) == 1
    assert saved[0].constraints is None
