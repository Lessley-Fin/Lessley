from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from lessley_deals.cli.review_session import run_review_session
from lessley_deals.matching.config import MatchConfig
from lessley_deals.matching.pipeline import MatchPipeline
from lessley_deals.normalization.pipeline import NormalizationPipeline, create_default_pipeline
from lessley_deals.persistence.config import PersistenceConfig
from lessley_deals.persistence.repositories.aliases import AliasJsonRepository
from lessley_deals.persistence.repositories.deals import DealJsonRepository
from lessley_deals.persistence.repositories.raw_deals import RawDealJsonRepository
from lessley_deals.persistence.repositories.raw_stores import RawStoreJsonRepository
from lessley_deals.persistence.repositories.reviews import ReviewJsonRepository
from lessley_deals.persistence.repositories.stores import CanonicalStoreJsonRepository
from lessley_deals.pipeline.match_stage import MatchStage
from lessley_deals.pipeline.normalize_stage import NormalizeStage
from lessley_deals.pipeline.orchestrator import PipelineOrchestrator
from lessley_deals.pipeline.persist_stage import PersistStage
from lessley_deals.pipeline.scrape_stage import ScrapeStage
from lessley_deals.review.display import ReviewDisplay
from lessley_deals.review.queue import ReviewQueue
from lessley_deals.review.stats import ReviewStats
from lessley_deals.scraping.orchestrator import ScraperOrchestrator
from lessley_deals.scraping.registry import SourceRegistry

app = typer.Typer(name="deals", help="Lessley deals scraping and store resolution CLI.")
console = Console()


def _get_config(data_dir: str) -> PersistenceConfig:
    return PersistenceConfig(base_dir=Path(data_dir))


def _setup_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


@app.command()
def scrape(
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Specific source to scrape"),
    all_sources: bool = typer.Option(False, "--all", help="Scrape all registered sources"),
    data_dir: str = typer.Option("data", "--data-dir", "-d"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Run the full scrape -> normalize -> match -> persist pipeline."""
    _setup_logging(log_level)
    config = _get_config(data_dir)

    # Build repositories
    raw_deal_repo = RawDealJsonRepository(config.raw_deals_path)
    raw_store_repo = RawStoreJsonRepository(config.raw_stores_path)
    store_repo = CanonicalStoreJsonRepository(config.stores_path)
    alias_repo = AliasJsonRepository(config.aliases_path)
    deal_repo = DealJsonRepository(config.deals_path)
    review_repo = ReviewJsonRepository(config.reviews_path)

    # Build pipeline components
    registry = SourceRegistry()
    registry.register_defaults()
    orchestrator = ScraperOrchestrator.from_registry(registry)
    scrape_stage = ScrapeStage(orchestrator, raw_deal_repo, raw_store_repo)
    normalize_stage = NormalizeStage(create_default_pipeline())
    match_pipeline = MatchPipeline(MatchConfig())
    match_stage = MatchStage(match_pipeline)
    persist_stage = PersistStage(deal_repo, review_repo)

    pipeline = PipelineOrchestrator(
        scrape_stage=scrape_stage,
        normalize_stage=normalize_stage,
        match_stage=match_stage,
        persist_stage=persist_stage,
        store_repo=store_repo,
        alias_repo=alias_repo,
    )

    source_ids = [source] if source else None
    report = asyncio.run(pipeline.run(source_ids))
    console.print(report.summary())


@app.command()
def review(
    data_dir: str = typer.Option("data", "--data-dir", "-d"),
    batch: int = typer.Option(0, "--batch", "-b", help="Process N items then stop (0=unlimited)"),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Filter by source"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Start an interactive review session for uncertain matches."""
    _setup_logging(log_level)
    config = _get_config(data_dir)

    review_repo = ReviewJsonRepository(config.reviews_path)
    store_repo = CanonicalStoreJsonRepository(config.stores_path)
    alias_repo = AliasJsonRepository(config.aliases_path)
    deal_repo = DealJsonRepository(config.deals_path)
    raw_deal_repo = RawDealJsonRepository(config.raw_deals_path)

    run_review_session(
        review_repo=review_repo,
        store_repo=store_repo,
        alias_repo=alias_repo,
        deal_repo=deal_repo,
        raw_deal_repo=raw_deal_repo,
        batch_size=batch,
        source_filter=source,
    )


@app.command(name="review-stats")
def review_stats(
    data_dir: str = typer.Option("data", "--data-dir", "-d"),
) -> None:
    """Show review queue statistics."""
    config = _get_config(data_dir)
    review_repo = ReviewJsonRepository(config.reviews_path)
    stats_calc = ReviewStats(review_repo)
    display = ReviewDisplay(console)
    display.show_stats(stats_calc.compute())


@app.command(name="list-stores")
def list_stores(
    query: Optional[str] = typer.Argument(None, help="Search query"),
    data_dir: str = typer.Option("data", "--data-dir", "-d"),
) -> None:
    """List canonical stores."""
    config = _get_config(data_dir)
    store_repo = CanonicalStoreJsonRepository(config.stores_path)

    if query:
        stores = store_repo.search(query)
    else:
        stores = store_repo.get_all()

    if not stores:
        console.print("No stores found.")
        return

    from rich.table import Table

    table = Table(title=f"Canonical Stores ({len(stores)})")
    table.add_column("ID", style="dim")
    table.add_column("Name")
    table.add_column("Normalized")
    table.add_column("Created")

    for store in stores:
        table.add_row(
            store.id[:16] + "...",
            store.name,
            store.name_forms.normalized,
            store.created_at.strftime("%Y-%m-%d"),
        )
    console.print(table)


if __name__ == "__main__":
    app()
