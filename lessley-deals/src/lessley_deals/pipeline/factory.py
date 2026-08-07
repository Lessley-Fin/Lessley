"""Composition root — builds a fully wired pipeline from configuration.

Everything that knows *which* concrete implementation to use lives here and
nowhere else: JSON vs MongoDB, whether versioning is enabled, which sources are
registered.  The scheduler service and the CLI both call ``build_pipeline`` so
there is exactly one wiring to keep correct.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lessley_deals.domain.protocols import CurrentDealRepository, DealVersionRepository
from lessley_deals.matching.config import MatchConfig
from lessley_deals.matching.pipeline import MatchPipeline
from lessley_deals.normalization.pipeline import create_default_pipeline
from lessley_deals.persistence.config import PersistenceConfig
from lessley_deals.pipeline.ingest_stage import IngestStage
from lessley_deals.pipeline.match_stage import MatchStage
from lessley_deals.pipeline.normalize_stage import NormalizeStage
from lessley_deals.pipeline.orchestrator import PipelineOrchestrator
from lessley_deals.pipeline.persist_stage import PersistStage
from lessley_deals.pipeline.scrape_stage import ScrapeStage
from lessley_deals.scraping.orchestrator import ScraperOrchestrator
from lessley_deals.scraping.registry import SourceRegistry
from lessley_deals.versioning.hashing import DealIdentityResolver
from lessley_deals.versioning.ingestion import IngestionConfig, IngestionService

logger = logging.getLogger(__name__)


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return default


@dataclass
class PipelineConfig:
    data_dir: Path = field(default_factory=lambda: Path(os.environ.get("DEALS_DATA_DIR", "data")))
    storage: str = field(default_factory=lambda: os.environ.get("DEALS_STORAGE", "json").lower())
    include_llm_sites: bool = field(default_factory=lambda: _env_flag("DEALS_LLM_SOURCES", True))
    enable_versioning: bool = field(default_factory=lambda: _env_flag("DEALS_VERSIONING", True))
    enrich_constraints: bool = field(default_factory=lambda: _env_flag("DEALS_ENRICH_CONSTRAINTS", False))
    constraints_concurrency: int = field(default_factory=lambda: _env_int("DEALS_CONSTRAINTS_CONCURRENCY", 5))
    review_no_match: bool = field(default_factory=lambda: _env_flag("DEALS_REVIEW_NO_MATCH", False))
    write_deals: bool = field(default_factory=lambda: _env_flag("DEALS_WRITE_LEGACY", True))
    """Write the ``deals`` collection — the source of truth every consumer reads
    (``deal-optimizer``'s ``deals_source``, and ``gateway_view``'s projection
    into ``deal_list``).  ``deals_current``/``deal_versions`` are still written
    when versioning is on, but as history only.  Turning this off leaves both
    consumers reading whatever was in ``deals`` before the run."""
    publish_gateway_view: bool = field(
        default_factory=lambda: _env_flag("DEALS_PUBLISH_GATEWAY_VIEW", True)
    )
    """Refresh ``deal_list``/``store_list`` — the read model the Gateway's deal
    search queries — after each run.  Mongo-only; no-op on JSON storage."""

    @property
    def use_mongo(self) -> bool:
        return self.storage == "mongo"


@dataclass
class IngestionTuning:
    """Env-driven overrides for the expiry heuristics (see IngestionConfig)."""

    @staticmethod
    def from_env() -> IngestionConfig:
        from datetime import timedelta

        return IngestionConfig(
            absence_threshold=_env_int("DEALS_ABSENCE_THRESHOLD", 2),
            absence_grace=timedelta(hours=_env_float("DEALS_ABSENCE_GRACE_HOURS", 24.0)),
            min_coverage_ratio=_env_float("DEALS_MIN_COVERAGE_RATIO", 0.5),
            expire_on_source_date=_env_flag("DEALS_EXPIRE_ON_SOURCE_DATE", True),
            enable_expiry_sweep=_env_flag("DEALS_EXPIRY_SWEEP", True),
        )


@dataclass
class PipelineBundle:
    """The assembled pipeline plus the pieces callers need to introspect."""

    pipeline: PipelineOrchestrator
    registry: SourceRegistry
    repos: dict[str, Any]
    version_repo: DealVersionRepository | None = None
    current_repo: CurrentDealRepository | None = None
    database: Any = None

    @property
    def source_ids(self) -> list[str]:
        return self.registry.list_all()


def build_repositories(config: PipelineConfig) -> tuple[dict[str, Any], Any]:
    """Return ``(repos, database)`` for the configured storage backend."""
    persistence = PersistenceConfig(base_dir=config.data_dir)

    # The review queue is a human workflow — always local JSON, never Mongo.
    from lessley_deals.persistence.repositories.reviews import ReviewJsonRepository

    review_repo = ReviewJsonRepository(persistence.reviews_path)

    if config.use_mongo:
        from lessley_deals.persistence.mongo_client import get_database
        from lessley_deals.persistence.repositories.mongo.aliases import AliasMongoRepository
        from lessley_deals.persistence.repositories.mongo.clubs import ClubMongoRepository
        from lessley_deals.persistence.repositories.mongo.deal_versions import (
            CurrentDealMongoRepository,
            DealVersionMongoRepository,
        )
        from lessley_deals.persistence.repositories.mongo.deals import DealMongoRepository
        from lessley_deals.persistence.repositories.mongo.raw_deals import RawDealMongoRepository
        from lessley_deals.persistence.repositories.mongo.raw_stores import RawStoreMongoRepository
        from lessley_deals.persistence.repositories.mongo.stores import CanonicalStoreMongoRepository

        from lessley_deals.persistence.seeding import seed_mongo_if_empty

        db = get_database()
        # The worker never goes through the CLI, so without this a fresh
        # deployment scrapes against an empty stores collection and sends
        # everything to NO_MATCH. No-op once anything has been seeded.
        seed_mongo_if_empty(db, config.data_dir)

        repos: dict[str, Any] = {
            "store_repo": CanonicalStoreMongoRepository(db),
            "alias_repo": AliasMongoRepository(db),
            "deal_repo": DealMongoRepository(db),
            "raw_deal_repo": RawDealMongoRepository(db),
            "raw_store_repo": RawStoreMongoRepository(db),
            "club_repo": ClubMongoRepository(db),
            "review_repo": review_repo,
            "version_repo": DealVersionMongoRepository(db),
            "current_repo": CurrentDealMongoRepository(db),
        }
        return repos, db

    from lessley_deals.persistence.repositories.aliases import AliasJsonRepository
    from lessley_deals.persistence.repositories.clubs import ClubJsonRepository
    from lessley_deals.persistence.repositories.deal_versions import (
        CurrentDealJsonRepository,
        DealVersionJsonRepository,
    )
    from lessley_deals.persistence.repositories.deals import DealJsonRepository
    from lessley_deals.persistence.repositories.raw_deals import RawDealJsonRepository
    from lessley_deals.persistence.repositories.raw_stores import RawStoreJsonRepository
    from lessley_deals.persistence.repositories.stores import CanonicalStoreJsonRepository
    from lessley_deals.persistence.seeding import seed_clubs_json

    # Same reason the Mongo branch seeds clubs: PersistStage stamps club_id from
    # this repo, so an absent file silently produces deals with club_id = None.
    seed_clubs_json(persistence.clubs_path, config.data_dir)

    base = config.data_dir
    return (
        {
            "store_repo": CanonicalStoreJsonRepository(persistence.stores_path),
            "alias_repo": AliasJsonRepository(persistence.aliases_path),
            "deal_repo": DealJsonRepository(persistence.deals_path),
            "raw_deal_repo": RawDealJsonRepository(persistence.raw_deals_path),
            "raw_store_repo": RawStoreJsonRepository(persistence.raw_stores_path),
            "club_repo": ClubJsonRepository(persistence.clubs_path),
            "review_repo": review_repo,
            "version_repo": DealVersionJsonRepository(base / "deal_versions.json"),
            "current_repo": CurrentDealJsonRepository(base / "deals_current.json"),
        },
        None,
    )


def build_identity_resolver() -> DealIdentityResolver:
    """Per-source identity extractors.

    Whenever a source exposes a real primary key, register it here — a stable id
    beats the URL/title fallback and keeps the version history intact across
    wording changes.
    """
    def _payload_id(*keys: str) -> Callable[[Any], str | None]:
        def extract(deal: Any) -> str | None:
            logic = deal.discount_logic or {}
            for key in keys:
                value = logic.get(key)
                if value:
                    return str(value)
            return None

        return extract

    return DealIdentityResolver(
        {
            "hot": _payload_id("benefit_id", "benefitId", "id"),
            "mastercard": _payload_id("benefit_id", "id"),
            "behatsdaa": _payload_id("product_id", "productId", "id"),
            "topcash": _payload_id("store_id", "id"),
        }
    )


def build_pipeline(config: PipelineConfig | None = None) -> PipelineBundle:
    """Assemble the full scrape → … → ingest pipeline."""
    config = config or PipelineConfig()
    repos, db = build_repositories(config)

    registry = SourceRegistry()
    registry.register_defaults(include_llm_sites=config.include_llm_sites)

    scrape_stage = ScrapeStage(
        ScraperOrchestrator.from_registry(registry),
        repos["raw_deal_repo"],
        repos["raw_store_repo"],
    )
    normalize_stage = NormalizeStage(create_default_pipeline())
    match_stage = MatchStage(MatchPipeline(MatchConfig()))
    persist_stage = PersistStage(
        repos["deal_repo"],
        repos["review_repo"],
        repos["store_repo"],
        review_no_match=config.review_no_match,
        club_repo=repos["club_repo"],
        write_deals=config.write_deals,
    )

    constraints_stage = None
    if config.enrich_constraints:
        from lessley_deals.pipeline.constraints_stage import ConstraintsStage

        constraints_stage = ConstraintsStage(max_concurrency=config.constraints_concurrency)

    ingest_stage = None
    if config.enable_versioning:
        ingest_stage = IngestStage(
            IngestionService(
                repos["version_repo"],
                repos["current_repo"],
                identity=build_identity_resolver(),
                config=IngestionTuning.from_env(),
            )
        )

    # Keep the Gateway's read model (deal_list/store_list) in step with every
    # run. Mongo-only: the Gateway has no JSON backend to read from.
    publish = None
    if db is not None and config.publish_gateway_view:
        from lessley_deals.persistence.gateway_view import sync_gateway_view

        publish = lambda: sync_gateway_view(db)  # noqa: E731

    pipeline = PipelineOrchestrator(
        scrape_stage=scrape_stage,
        normalize_stage=normalize_stage,
        match_stage=match_stage,
        persist_stage=persist_stage,
        store_repo=repos["store_repo"],
        alias_repo=repos["alias_repo"],
        constraints_stage=constraints_stage,
        ingest_stage=ingest_stage,
        publish=publish,
    )

    logger.info(
        "Pipeline built — storage=%s versioning=%s sources=%d",
        config.storage, config.enable_versioning, len(registry.list_all()),
    )
    return PipelineBundle(
        pipeline=pipeline,
        registry=registry,
        repos=repos,
        version_repo=repos.get("version_repo"),
        current_repo=repos.get("current_repo"),
        database=db,
    )
