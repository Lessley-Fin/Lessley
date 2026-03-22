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
    hot_benefit_type: Optional[list[str]] = typer.Option(
        None,
        "--hot-benefit-type",
        help=(
            "HOT benefit type(s) to scrape. "
            "Allowed values: 100, 300, 700, 800, 1100, 1200, 1300. "
            "Pass multiple times to include several types. "
            "Defaults to all types when omitted."
        ),
    ),
    data_dir: str = typer.Option("data", "--data-dir", "-d"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Run the full scrape -> normalize -> match -> persist pipeline."""
    _setup_logging(log_level)
    config = _get_config(data_dir)

    # Validate HOT benefit types early so we fail fast.
    from lessley_deals.scraping.sources.hot import BENEFIT_TYPES, HotAdapter
    from lessley_deals.scraping.base import SourceConfig as _SC

    if hot_benefit_type:
        invalid = [bt for bt in hot_benefit_type if bt not in BENEFIT_TYPES]
        if invalid:
            console.print(
                f"[red]Invalid --hot-benefit-type value(s): {', '.join(invalid)}[/red]\n"
                f"Allowed: {', '.join(BENEFIT_TYPES)}"
            )
            raise typer.Exit(code=1)

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

    # Override the HOT adapter if custom benefit types were requested.
    if hot_benefit_type:
        registry._adapters["hot"] = HotAdapter(
            _SC(base_url="https://www.hot.co.il", rate_limit_rps=0.7, timeout_seconds=30.0),
            benefit_types=tuple(hot_benefit_type),
        )

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


@app.command(name="discover-stores")
def discover_stores(
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Filter to one source (hot, mastercard, …)"),
    min_count: int = typer.Option(1, "--min-count", help="Only show names appearing at least N times"),
    export: Optional[str] = typer.Option(None, "--export", "-e", help="Write seed JSON snippets to this file"),
    data_dir: str = typer.Option("data", "--data-dir", "-d"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Match raw scraped deals against canonical stores and show what is unmatched.

    Reads existing raw_source_deals.json (no new scraping), normalizes every
    record, runs the 5-stage match pipeline, then prints a table of store names
    that got NO_MATCH or REVIEW so you know what to add to the seed files.

    Use --export to write ready-to-paste seed JSON snippets for the new stores.
    """
    import json
    from collections import defaultdict
    from rich.table import Table
    from lessley_deals.domain.enums import MatchDecision
    from lessley_deals.matching.index import AliasIndex
    from lessley_deals.matching.pipeline import MatchPipeline
    from lessley_deals.matching.config import MatchConfig
    from lessley_deals.normalization.pipeline import create_default_pipeline

    _setup_logging(log_level)
    config = _get_config(data_dir)

    raw_deal_repo = RawDealJsonRepository(config.raw_deals_path)
    store_repo = CanonicalStoreJsonRepository(config.stores_path)
    alias_repo = AliasJsonRepository(config.aliases_path)

    # Load raw deals
    raw_deals = raw_deal_repo.get_by_source(source) if source else raw_deal_repo.get_all()
    if not raw_deals:
        console.print("[yellow]No raw deals found. Run 'deals scrape' first.[/yellow]")
        raise typer.Exit()

    console.print(f"Loaded [bold]{len(raw_deals)}[/bold] raw deals. Running normalize → match…")

    # Normalize
    norm_pipeline = create_default_pipeline()
    normalized = [norm_pipeline.normalize(r) for r in raw_deals]

    # Build index and match
    index = AliasIndex(aliases=alias_repo.get_all(), stores=store_repo.get_all())
    match_pipeline = MatchPipeline(MatchConfig())
    verdicts = [match_pipeline.match(n, index) for n in normalized]

    # Group unmatched/review by normalized store name
    # key: (source_id, normalized_name)  value: {count, raw_name, best_confidence, decision}
    groups: dict[tuple[str, str], dict] = defaultdict(lambda: {"count": 0, "raw_name": "", "best_confidence": 0.0, "decision": ""})
    norm_map = {n.raw_id: n for n in normalized}

    auto = review_count = no_match = 0
    for verdict in verdicts:
        if verdict.decision == MatchDecision.AUTO_MATCH:
            auto += 1
            continue
        norm = norm_map.get(verdict.record_id)
        if norm is None:
            continue
        src = norm.source_id
        name = norm.store_name_forms.normalized
        key = (src, name)
        groups[key]["count"] += 1
        groups[key]["raw_name"] = norm.store_name_forms.normalized
        groups[key]["decision"] = str(verdict.decision)
        if verdict.best:
            groups[key]["best_confidence"] = max(
                groups[key]["best_confidence"], verdict.best.confidence
            )
        if verdict.decision == MatchDecision.REVIEW:
            review_count += 1
        else:
            no_match += 1

    # Filter by min_count
    filtered = {k: v for k, v in groups.items() if v["count"] >= min_count}

    # Summary
    console.print(
        f"\n[green]Auto-matched:[/green] {auto}  "
        f"[yellow]Review:[/yellow] {review_count}  "
        f"[red]No-match:[/red] {no_match}  "
        f"[dim]Total:[/dim] {len(verdicts)}\n"
    )

    if not filtered:
        console.print("[green]All stores are matched — nothing to add to the seed.[/green]")
        raise typer.Exit()

    # Sort: no_match first, then by count descending
    rows = sorted(
        filtered.items(),
        key=lambda x: (x[1]["decision"] != "no_match", -x[1]["count"]),
    )

    table = Table(title=f"Unmatched / Review Stores ({len(rows)} unique names)")
    table.add_column("Decision", style="bold")
    table.add_column("Source")
    table.add_column("Normalized Name")
    table.add_column("Deals", justify="right")
    table.add_column("Best Conf.", justify="right")

    for (src, name), info in rows:
        decision_style = "red" if info["decision"] == "no_match" else "yellow"
        table.add_row(
            f"[{decision_style}]{info['decision']}[/{decision_style}]",
            src,
            name,
            str(info["count"]),
            f"{info['best_confidence']:.2f}" if info["best_confidence"] > 0 else "-",
        )

    console.print(table)

    # Export seed snippets
    if export:
        # Find the highest existing seed IDs
        existing_stores = store_repo.get_all()
        existing_aliases = alias_repo.get_all()

        def _next_seed_id(prefix: str, existing_ids: list[str]) -> int:
            nums = []
            for eid in existing_ids:
                if eid.startswith(prefix):
                    try:
                        nums.append(int(eid[len(prefix):]))
                    except ValueError:
                        pass
            return max(nums, default=0) + 1

        store_counter = _next_seed_id("seed_store_", [s.id for s in existing_stores])
        alias_counter = _next_seed_id("seed_alias_", [a.id for a in existing_aliases])

        new_stores = []
        new_aliases = []

        for (src, name), info in rows:
            if info["decision"] != "no_match":
                continue  # only export definite no-matches as seed candidates

            compact = name.replace(" ", "").replace("-", "")
            tokens = sorted({w for w in name.split() if len(w) > 1})

            store_id = f"seed_store_{store_counter:03d}"
            store_counter += 1

            new_stores.append({
                "id": store_id,
                "name": name,
                "name_forms": {
                    "normalized": name,
                    "compact": compact,
                    "tokens": tokens,
                },
                "created_at": "2024-01-01T00:00:00+00:00",
                "updated_at": "2024-01-01T00:00:00+00:00",
                "metadata": {"category": "TODO", "source": src},
            })

            alias_id = f"seed_alias_{alias_counter:03d}"
            alias_counter += 1
            new_aliases.append({
                "id": alias_id,
                "store_id": store_id,
                "alias": name,
                "alias_forms": {"normalized": name, "compact": compact, "tokens": tokens},
                "source": "seed",
                "created_at": "2024-01-01T00:00:00+00:00",
            })

        output = {
            "instructions": (
                "Append stores_seed entries to data/seed/stores_seed.json "
                "and aliases_seed entries to data/seed/aliases_seed.json. "
                "Set metadata.category to the correct value. "
                "Add extra alias entries for any other name variants."
            ),
            "stores_seed": new_stores,
            "aliases_seed": new_aliases,
        }

        Path(export).write_text(json.dumps(output, ensure_ascii=False, indent=2))
        console.print(
            f"\n[green]Exported {len(new_stores)} store snippets → [bold]{export}[/bold][/green]\n"
            "Open the file, set [bold]metadata.category[/bold] for each store, "
            "then paste into the seed files."
        )


if __name__ == "__main__":
    app()
