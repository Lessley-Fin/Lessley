from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import typer
from bidi.algorithm import get_display
from dotenv import load_dotenv
from rich.console import Console

# Load .env from the current directory or walk up to find it (e.g. lessley-cd/.env).
# This lets the CLI pick up DEALS_STORAGE, MONGO_URI, etc. without manual exports.
def _load_env() -> None:
    cwd = Path.cwd()
    for directory in [cwd, *cwd.parents]:
        candidate = directory / ".env"
        if candidate.is_file():
            load_dotenv(candidate, override=False)  # never overwrite already-exported vars
            return
        # Also check the lessley-cd sibling directory (monorepo layout)
        sibling = directory / "lessley-cd" / ".env"
        if sibling.is_file():
            load_dotenv(sibling, override=False)
            return

_load_env()

from lessley_deals.cli.review_session import run_review_session
from lessley_deals.matching.config import MatchConfig
from lessley_deals.matching.pipeline import MatchPipeline
from lessley_deals.normalization.pipeline import NormalizationPipeline, create_default_pipeline
from lessley_deals.persistence.config import PersistenceConfig
from lessley_deals.persistence.repositories.aliases import AliasJsonRepository
from lessley_deals.persistence.repositories.clubs import ClubJsonRepository
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


def _make_repos(data_dir: str) -> SimpleNamespace:
    """Return all repositories — MongoDB when DEALS_STORAGE=mongo, else JSON files.

    review_repo always stays on JSON — the review queue is local per-user.

    When MongoDB is selected and the stores collection is empty the seed files
    (data/seed/stores.json + data/seed/store_aliases.json) are imported
    automatically so the pipeline can start matching immediately.
    """
    config = _get_config(data_dir)
    review_repo = ReviewJsonRepository(config.reviews_path)

    storage = os.environ.get("DEALS_STORAGE", "json").lower()
    if storage == "mongo":
        from lessley_deals.persistence.mongo_client import get_database
        from lessley_deals.persistence.repositories.mongo.aliases import AliasMongoRepository
        from lessley_deals.persistence.repositories.mongo.clubs import ClubMongoRepository
        from lessley_deals.persistence.repositories.mongo.deals import DealMongoRepository
        from lessley_deals.persistence.repositories.mongo.raw_deals import RawDealMongoRepository
        from lessley_deals.persistence.repositories.mongo.raw_stores import RawStoreMongoRepository
        from lessley_deals.persistence.repositories.mongo.stores import CanonicalStoreMongoRepository
        db = get_database()
        repos = SimpleNamespace(
            store_repo=CanonicalStoreMongoRepository(db),
            alias_repo=AliasMongoRepository(db),
            deal_repo=DealMongoRepository(db),
            raw_deal_repo=RawDealMongoRepository(db),
            raw_store_repo=RawStoreMongoRepository(db),
            review_repo=review_repo,
            club_repo=ClubMongoRepository(db),
        )
        _auto_seed_mongo_if_empty(db, data_dir)
        return repos
    return SimpleNamespace(
        store_repo=CanonicalStoreJsonRepository(config.stores_path),
        alias_repo=AliasJsonRepository(config.aliases_path),
        deal_repo=DealJsonRepository(config.deals_path),
        raw_deal_repo=RawDealJsonRepository(config.raw_deals_path),
        raw_store_repo=RawStoreJsonRepository(config.raw_stores_path),
        review_repo=review_repo,
        club_repo=ClubJsonRepository(config.clubs_path),
    )


def _auto_seed_mongo_if_empty(db: object, data_dir: str) -> None:  # type: ignore[type-arg]
    """Seed stores, aliases and clubs from the seed JSON files when MongoDB is empty.

    This is idempotent — uses $setOnInsert so existing documents are never
    overwritten.  Runs silently on every startup; the actual DB round-trip is
    negligible because count_documents returns quickly when the collection is
    non-empty.
    """
    import json
    import logging as _logging

    _log = _logging.getLogger(__name__)

    # Check if stores already exist — if so, skip (fast path).
    if db["stores"].count_documents({}, limit=1) > 0:  # type: ignore[index]
        return

    _log.info("MongoDB stores collection is empty — seeding from seed files…")

    # Prefer data/seed/ directory; fall back to data/ for stores/aliases.
    seed_candidates = [Path("data/seed"), Path(data_dir)]
    _CLUBS = [
        {"_id": "club_hot",        "name": "HOT Israel",       "source_id": "hot",        "description": "HOT Israel — cable TV & internet member benefits",   "metadata": {}, "stores": []},
        {"_id": "club_mastercard", "name": "Mastercard Israel", "source_id": "mastercard", "description": "Mastercard Israel credit card benefits",              "metadata": {}, "stores": []},
        {"_id": "club_topcash",    "name": "Isracard TopCash",  "source_id": "topcash",    "description": "Isracard TopCash cashback benefits",                  "metadata": {}, "stores": []},
        {"_id": "club_behatsdaa",  "name": "Behatsdaa",         "source_id": "behatsdaa",  "description": "Behatsdaa deals aggregator",                          "metadata": {}, "stores": []},
    ]

    def _upsert_file(collection: str, path: Path) -> int:
        if not path.exists():
            return 0
        items = json.loads(path.read_text(encoding="utf-8"))
        inserted = 0
        for d in items:
            doc = dict(d)
            doc_id = doc.pop("id", None) or doc.pop("_id", None)
            doc["_id"] = doc_id
            result = db[collection].update_one({"_id": doc_id}, {"$setOnInsert": doc}, upsert=True)  # type: ignore[index]
            if result.upserted_id is not None:
                inserted += 1
        return inserted

    for seed_dir_path in seed_candidates:
        stores_file = seed_dir_path / "stores.json"
        aliases_file = seed_dir_path / "store_aliases.json"
        if stores_file.exists():
            n = _upsert_file("stores", stores_file)
            _log.info("Auto-seeded %d stores from %s", n, stores_file)
            _upsert_file("store_aliases", aliases_file)
            break  # found and seeded — done

    # Clubs are always seeded (they're hardcoded, not from a file)
    for club_doc in _CLUBS:
        db["clubs"].update_one({"_id": club_doc["_id"]}, {"$setOnInsert": club_doc}, upsert=True)  # type: ignore[index]


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
    hot_fetch_details: bool = typer.Option(
        True,
        "--hot-fetch-details/--no-hot-fetch-details",
        help=(
            "Fetch full detail data for every HOT benefit (terms, locations, "
            "discount mechanics). On by default; use --no-hot-fetch-details to skip."
        ),
    ),
    hot_details_delay: float = typer.Option(
        2.0,
        "--hot-details-delay",
        help="Seconds to wait between each detail fetch request (default: 2.0).",
    ),
    hot_request_delay: float = typer.Option(
        1.5,
        "--hot-request-delay",
        help="Seconds to wait between page requests when listing benefits (default: 1.5).",
    ),
    review_no_match: bool = typer.Option(
        False,
        "--review-no-match",
        help=(
            "Send NO_MATCH records (confidence < 0.50) to the review queue "
            "instead of discarding them. Useful when scraping a new source "
            "where no canonical stores exist yet."
        ),
    ),
    data_dir: str = typer.Option("data", "--data-dir", "-d"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
    enrich: bool = typer.Option(
        False,
        "--enrich/--no-enrich",
        help="After scraping, classify stores missing `metadata.mcc_codes` via the LLM.",
    ),
) -> None:
    """Run the full scrape -> normalize -> match -> persist pipeline."""
    _setup_logging(log_level)

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
    repos = _make_repos(data_dir)
    raw_deal_repo = repos.raw_deal_repo
    raw_store_repo = repos.raw_store_repo
    store_repo = repos.store_repo
    alias_repo = repos.alias_repo
    deal_repo = repos.deal_repo
    review_repo = repos.review_repo

    # Build pipeline components
    registry = SourceRegistry()
    registry.register_defaults()

    # Override the HOT adapter if custom benefit types or detail mode requested.
    if hot_benefit_type or hot_fetch_details or hot_details_delay != 2.0 or hot_request_delay != 1.5:
        registry._adapters["hot"] = HotAdapter(
            _SC(base_url="https://www.hot.co.il", rate_limit_rps=0.7, timeout_seconds=30.0),
            benefit_types=tuple(hot_benefit_type) if hot_benefit_type else None,
            fetch_details=hot_fetch_details,
            details_delay_seconds=hot_details_delay,
            request_delay_seconds=hot_request_delay,
        )

    orchestrator = ScraperOrchestrator.from_registry(registry)
    scrape_stage = ScrapeStage(orchestrator, raw_deal_repo, raw_store_repo)
    normalize_stage = NormalizeStage(create_default_pipeline())
    match_pipeline = MatchPipeline(MatchConfig())
    match_stage = MatchStage(match_pipeline)
    persist_stage = PersistStage(deal_repo, review_repo, store_repo,
                                 review_no_match=review_no_match,
                                 club_repo=repos.club_repo)

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

    if enrich:
        from lessley_deals.enrichment.enrich_stores import enrich_stores as _enrich

        console.print("[cyan]Enriching stores missing mcc_codes…[/cyan]")
        stats = _enrich(data_dir=data_dir)
        console.print(
            f"[green]Enrichment done.[/green] total={stats['total']} "
            f"processed={stats['processed']} skipped={stats['skipped']} failed={stats['failed']}"
        )


@app.command()
def process(
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Filter to one source (hot, mastercard, …)"),
    review_no_match: bool = typer.Option(
        False,
        "--review-no-match",
        help="Send NO_MATCH records to the review queue instead of discarding them.",
    ),
    data_dir: str = typer.Option("data", "--data-dir", "-d"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Run normalize -> match -> persist on existing raw data (no scraping)."""
    _setup_logging(log_level)

    from lessley_deals.domain.models import NormalizedRecord
    from lessley_deals.matching.index import AliasIndex
    from lessley_deals.pipeline.context import PipelineContext
    from lessley_deals.pipeline.report import PipelineReport

    repos = _make_repos(data_dir)
    raw_deal_repo = repos.raw_deal_repo
    store_repo = repos.store_repo
    alias_repo = repos.alias_repo
    deal_repo = repos.deal_repo
    review_repo = repos.review_repo

    raw_deals = raw_deal_repo.get_by_source(source) if source else raw_deal_repo.get_all()
    if not raw_deals:
        console.print("[yellow]No raw deals found. Run 'deals scrape' first.[/yellow]")
        raise typer.Exit()

    console.print(f"Loaded [bold]{len(raw_deals)}[/bold] raw deals. Running normalize → match → persist…")

    ctx = PipelineContext()
    pipeline_records = [ctx.add_raw(deal) for deal in raw_deals]

    normalize_stage = NormalizeStage(create_default_pipeline())
    normalized = normalize_stage.run(raw_deals)
    normalized_map: dict[str, NormalizedRecord] = {n.raw_id: n for n in normalized}

    index = AliasIndex(aliases=alias_repo.get_all(), stores=store_repo.get_all())
    match_pipeline = MatchPipeline(MatchConfig())
    match_stage = MatchStage(match_pipeline)
    verdicts = match_stage.run(normalized, index)
    verdict_map = {v.record_id: v for v in verdicts}

    persist_stage = PersistStage(deal_repo, review_repo, store_repo,
                                 review_no_match=review_no_match,
                                 club_repo=repos.club_repo)
    asyncio.run(persist_stage.run(pipeline_records, normalized_map, verdict_map))

    ctx.finish()
    console.print(PipelineReport.from_context(ctx).summary())


@app.command(name="sync-swish-groups")
def sync_swish_groups_cmd(
    swish_db: Optional[str] = typer.Option(
        None,
        "--swish-db",
        help="Path to swish_database.json. Defaults to $SWISH_DATA_DIR/swish_database.json.",
    ),
    data_dir: str = typer.Option("data", "--data-dir", "-d"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Refresh hot_store_groups.json with the latest Swish catalogue.

    Resolves each Swish member store against the canonical stores via the
    matching pipeline.  Auto-matched members get their store_id written into
    the config; unresolved members are pushed to the review queue.
    """
    _setup_logging(log_level)

    from lessley_deals.matching.index import AliasIndex
    from lessley_deals.scraping.helpers.swish_group_sync import sync_swish_groups
    from lessley_deals.scraping.helpers.swish_scanner import SwishPaths

    repos = _make_repos(data_dir)
    index = AliasIndex(
        aliases=repos.alias_repo.get_all(),
        stores=repos.store_repo.get_all(),
    )
    queue = ReviewQueue(repos.review_repo)

    resolved_db = Path(swish_db) if swish_db else SwishPaths.from_env().database
    if not resolved_db.exists():
        console.print(f"[red]Swish database not found at {resolved_db}[/red]")
        raise typer.Exit(code=1)

    result = sync_swish_groups(
        swish_db_path=resolved_db,
        alias_index=index,
        review_queue=queue,
    )
    console.print(
        f"Swish sync: {result.benefits_processed} benefits, "
        f"{result.members_total} members "
        f"([green]{result.members_resolved} resolved[/green], "
        f"[yellow]{result.members_to_review} to review[/yellow]), "
        f"{result.review_items_created} new review items, "
        f"{result.groups_removed} stale groups removed."
    )


@app.command(name="sync-hot-groups")
def sync_hot_groups_cmd(
    data_dir: str = typer.Option("data", "--data-dir", "-d"),
    groups_file: Optional[str] = typer.Option(
        None,
        "--groups-file",
        help="Path to hot_store_groups.json. Defaults to bundled config.",
    ),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Resolve HOT store-group member names against the canonical store database.

    Upgrades plain-string member names to {name, store_id, confidence} dicts.
    Auto-matched members get their store_id written into the config; unresolved
    members are pushed to the review queue.

    Skips Swish-managed entries (use sync-swish-groups for those).
    """
    _setup_logging(log_level)

    from lessley_deals.matching.index import AliasIndex
    from lessley_deals.scraping.helpers.hot_group_sync import sync_hot_groups

    repos = _make_repos(data_dir)
    index = AliasIndex(
        aliases=repos.alias_repo.get_all(),
        stores=repos.store_repo.get_all(),
    )
    queue = ReviewQueue(repos.review_repo)

    groups_path = Path(groups_file) if groups_file else None

    result = sync_hot_groups(
        alias_index=index,
        review_queue=queue,
        groups_config_path=groups_path,
    )
    console.print(
        f"HOT groups sync: {result.groups_processed} groups processed, "
        f"[green]{result.members_resolved} resolved[/green], "
        f"[yellow]{result.members_pending} pending[/yellow], "
        f"{result.review_items_created} new review items."
    )


def _swish_paths(data_dir: str | None) -> "SwishPaths":  # noqa: F821
    from lessley_deals.scraping.helpers.swish_scanner import SwishPaths
    if data_dir is not None:
        os.environ["SWISH_DATA_DIR"] = data_dir
    return SwishPaths.from_env()


_SWISH_DATA_DIR_OPT: str | None = typer.Option(
    None,
    "--data-dir",
    "-d",
    help="Swish data directory. Overrides $SWISH_DATA_DIR (default: data/swish).",
)


@app.command(name="swish-catalog")
def swish_catalog_cmd(
    data_dir: str | None = _SWISH_DATA_DIR_OPT,
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Map all Swish gift-card IDs via two-phase catalog scrape."""
    _setup_logging(log_level)
    from lessley_deals.scraping.helpers.swish_scanner import SwishScanner

    with SwishScanner(paths=_swish_paths(data_dir)) as scanner:
        result = scanner.catalog()

    console.print(
        f"Catalog: {len(result.ids_found)} IDs found "
        f"({len(result.new_ids)} new, {len(result.ids_found) - len(result.new_ids)} already processed). "
        f"Stable: {result.stable}"
    )
    if not result.stable:
        raise typer.Exit(code=2)


@app.command(name="swish-scan")
def swish_scan_cmd(
    data_dir: str | None = _SWISH_DATA_DIR_OPT,
    limit: int = typer.Option(0, "--limit", help="Max IDs to scrape this run (0=unlimited)."),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Scrape pending Swish gift-card IDs into swish_database.json."""
    _setup_logging(log_level)
    from lessley_deals.scraping.helpers.swish_scanner import SwishScanner

    with SwishScanner(paths=_swish_paths(data_dir), scan_limit=limit or None) as scanner:
        count = scanner.scan()

    console.print(f"Scan complete: {count} new records saved.")


@app.command(name="swish-retry")
def swish_retry_cmd(
    data_dir: str | None = _SWISH_DATA_DIR_OPT,
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Retry blocked/failed Swish gift-card IDs."""
    _setup_logging(log_level)
    from lessley_deals.scraping.helpers.swish_scanner import SwishScanner

    with SwishScanner(paths=_swish_paths(data_dir)) as scanner:
        count = scanner.retry()

    console.print(f"Retry complete: {count} records recovered.")


@app.command(name="swish-all")
def swish_all_cmd(
    data_dir: str | None = _SWISH_DATA_DIR_OPT,
    deals_data_dir: str = typer.Option(
        "data", "--deals-data-dir", help="Deals data directory (for review queue, stores, aliases)."
    ),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Full Swish run: catalog -> scan -> retry loop -> sync-swish-groups."""
    _setup_logging(log_level)
    from lessley_deals.matching.index import AliasIndex
    from lessley_deals.scraping.helpers.swish_group_sync import sync_swish_groups
    from lessley_deals.scraping.helpers.swish_scanner import SwishScanner

    paths = _swish_paths(data_dir)

    with SwishScanner(paths=paths) as scanner:
        summary = scanner.run_all()

    console.print(
        f"Swish run: {summary.ids_total} IDs, "
        f"{summary.records_new} new, {summary.records_retried} retried, "
        f"{len(summary.still_missing)} still missing, {summary.attempts} attempt(s). "
        f"Catalog stable: {summary.catalog_stable}"
    )
    if summary.still_missing:
        n_missing = len(summary.still_missing)
        console.print(
            f"[yellow]Warning: {n_missing} IDs have no record after {summary.attempts} attempts[/yellow]"
        )

    repos = _make_repos(deals_data_dir)
    index = AliasIndex(
        aliases=repos.alias_repo.get_all(),
        stores=repos.store_repo.get_all(),
    )
    queue = ReviewQueue(repos.review_repo)
    sync_result = sync_swish_groups(
        swish_db_path=paths.database,
        alias_index=index,
        review_queue=queue,
    )
    console.print(
        f"Sync: {sync_result.benefits_processed} benefits, "
        f"[green]{sync_result.members_resolved} resolved[/green], "
        f"[yellow]{sync_result.members_to_review} to review[/yellow], "
        f"{sync_result.review_items_created} new review items."
    )

    if summary.still_missing:
        raise typer.Exit(code=2)


@app.command()
def review(
    data_dir: str = typer.Option("data", "--data-dir", "-d"),
    batch: int = typer.Option(0, "--batch", "-b", help="Process N items then stop (0=unlimited)"),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Filter by source"),
    continuous: bool = typer.Option(
        False,
        "--continuous",
        help="After the queue empties, wait 30 s and reload. Loop until Ctrl+C.",
    ),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Start an interactive review session for uncertain matches."""
    _setup_logging(log_level)

    repos = _make_repos(data_dir)
    review_repo = repos.review_repo
    store_repo = repos.store_repo
    alias_repo = repos.alias_repo
    deal_repo = repos.deal_repo
    raw_deal_repo = repos.raw_deal_repo

    run_review_session(
        review_repo=review_repo,
        store_repo=store_repo,
        alias_repo=alias_repo,
        deal_repo=deal_repo,
        raw_deal_repo=raw_deal_repo,
        batch_size=batch,
        source_filter=source,
        continuous=continuous,
    )


@app.command(name="review-stats")
def review_stats(
    data_dir: str = typer.Option("data", "--data-dir", "-d"),
) -> None:
    """Show review queue statistics."""
    repos = _make_repos(data_dir)
    review_repo = repos.review_repo
    stats_calc = ReviewStats(review_repo)
    display = ReviewDisplay(console)
    display.show_stats(stats_calc.compute())


@app.command(name="list-matches")
def list_matches(
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Filter by source (hot, mastercard, …)"),
    store: Optional[str] = typer.Option(None, "--store", help="Filter by store name (substring)"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max rows to show (0=all)"),
    data_dir: str = typer.Option("data", "--data-dir", "-d"),
) -> None:
    """Show deals that were auto-matched by the pipeline."""
    from rich.table import Table

    repos = _make_repos(data_dir)
    deal_repo = repos.deal_repo
    store_repo = repos.store_repo

    deals = deal_repo.get_all()
    stores_by_id = {s.id: s for s in store_repo.get_all()}

    if source:
        deals = [d for d in deals if d.source_id == source]
    if store:
        q = store.lower()
        deals = [
            d for d in deals
            if q in (stores_by_id.get(d.store_id, None) and stores_by_id[d.store_id].name.lower() or "")
        ]

    total = len(deals)
    if limit > 0:
        deals = deals[-limit:]  # show most recent

    table = Table(
        title=f"Auto-matched deals ({total} total{f', showing last {limit}' if limit and total > limit else ''})",
        show_lines=False,
    )
    table.add_column("Store", style="cyan", min_width=16)
    table.add_column("Source", style="dim", width=12)
    table.add_column("Description", max_width=48)
    # table.add_column("Price", style="magenta", width=14)
    table.add_column("Scraped", style="dim", width=12)

    for deal in deals:
        store_obj = stores_by_id.get(deal.store_id)
        store_name = get_display(store_obj.name) if store_obj else f"[dim]{deal.store_id[:12]}…[/dim]"
        # price_str = str(deal.discount_logic) if deal.discount_logic else "—"
        scraped = deal.scraped_at.strftime("%Y-%m-%d") if deal.scraped_at else "—"
        desc = get_display(deal.deal_description[:80]) if deal.deal_description else "—"
        table.add_row(store_name, deal.source_id, desc, scraped)

    if not deals:
        console.print("[yellow]No auto-matched deals found.[/yellow]")
        return

    console.print(table)


@app.command(name="list-stores")
def list_stores(
    query: Optional[str] = typer.Argument(None, help="Search query"),
    data_dir: str = typer.Option("data", "--data-dir", "-d"),
) -> None:
    """List canonical stores."""
    repos = _make_repos(data_dir)
    store_repo = repos.store_repo

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

    repos = _make_repos(data_dir)
    raw_deal_repo = repos.raw_deal_repo
    store_repo = repos.store_repo
    alias_repo = repos.alias_repo

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


@app.command(name="seed-from-raw")
def seed_from_raw(
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Filter to one source (hot, mastercard, …)"),
    write: bool = typer.Option(False, "--write", "-w", help="Write directly into the seed files (appends)"),
    export: Optional[str] = typer.Option(None, "--export", "-e", help="Write seed JSON snippets to this file instead"),
    data_dir: str = typer.Option("data", "--data-dir", "-d"),
    seed_dir: str = typer.Option("data/seed", "--seed-dir", help="Location of the seed JSON files"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Scan raw_source_stores.json and generate seed entries for unmatched stores.

    Reads raw stores (already scraped, deduplicated per brand), normalizes
    each name, checks the alias index, then generates seed_store / seed_alias
    entries for every store that has no canonical match.

    For HOT stores the raw_payload supplies:
      - supplierWebsite  → metadata.domain
      - item_category    → metadata.category hint

    Use --write to append directly into data/seed/stores_seed.json and
    data/seed/aliases_seed.json, or --export <file> to review first.
    """
    import json
    import re as _re
    from collections import defaultdict
    from urllib.parse import urlparse
    from rich.table import Table
    from lessley_deals.matching.index import AliasIndex
    from lessley_deals.normalization.pipeline import NormalizationPipeline
    from lessley_deals.normalization.hebrew_utils import normalize_final_forms, normalize_hebrew
    from lessley_deals.normalization.text import collapse_whitespace

    _setup_logging(log_level)
    seed_path = Path(seed_dir)

    repos = _make_repos(data_dir)
    raw_store_repo = repos.raw_store_repo
    store_repo = repos.store_repo
    alias_repo = repos.alias_repo

    raw_stores = raw_store_repo.get_by_source(source) if source else raw_store_repo.get_all()
    if not raw_stores:
        console.print("[yellow]No raw stores found. Run 'deals scrape' first.[/yellow]")
        raise typer.Exit()

    console.print(f"Loaded [bold]{len(raw_stores)}[/bold] raw stores. Checking against alias index…")

    # Build alias index
    index = AliasIndex(aliases=alias_repo.get_all(), stores=store_repo.get_all())

    def _build_compact(text: str) -> str:
        normalized = collapse_whitespace(normalize_hebrew(text)).lower()
        compact = _re.sub(r"[\s\W]+", "", normalized)
        return normalize_final_forms(compact)

    def _build_normalized(text: str) -> str:
        return collapse_whitespace(normalize_hebrew(text)).lower()

    def _extract_domain(url: str | None) -> str | None:
        if not url:
            return None
        if not url.startswith("http"):
            url = "https://" + url
        try:
            host = urlparse(url).hostname or ""
            return host.lstrip("www.") or None
        except Exception:
            return None

    # Deduplicate raw stores by normalized name + source
    seen: dict[tuple[str, str], object] = {}  # (source_id, compact) -> RawStore
    for rs in raw_stores:
        compact = _build_compact(rs.name)
        key = (rs.source_id, compact)
        if key not in seen:
            seen[key] = rs
    unique_raw = list(seen.values())

    # Check each against alias index
    matched_names: list[str] = []
    unmatched: list[object] = []
    for rs in unique_raw:
        compact = _build_compact(rs.name)
        if index.exact_lookup(compact) is not None:
            matched_names.append(rs.name)
        else:
            unmatched.append(rs)

    console.print(
        f"[green]Already matched:[/green] {len(matched_names)}  "
        f"[red]Unmatched (will be seeded):[/red] {len(unmatched)}\n"
    )

    if not unmatched:
        console.print("[green]All raw stores are already in the seed — nothing to do.[/green]")
        raise typer.Exit()

    # Preview table
    table = Table(title=f"Stores to seed ({len(unmatched)})")
    table.add_column("Source")
    table.add_column("Raw Name")
    table.add_column("Domain")
    table.add_column("Category hint")

    for rs in unmatched:
        domain = _extract_domain(rs.url)
        category_hint = rs.raw_payload.get("item_category") or rs.raw_payload.get("category") or "-"
        table.add_row(rs.source_id, rs.name, domain or "-", str(category_hint))

    console.print(table)

    # Find highest existing IDs
    existing_stores = store_repo.get_all()
    existing_aliases = alias_repo.get_all()

    def _next_id(prefix: str, ids: list[str]) -> int:
        nums = [int(i[len(prefix):]) for i in ids if i.startswith(prefix) and i[len(prefix):].isdigit()]
        return max(nums, default=0) + 1

    store_counter = _next_id("seed_store_", [s.id for s in existing_stores])
    alias_counter = _next_id("seed_alias_", [a.id for a in existing_aliases])

    new_stores = []
    new_aliases = []

    for rs in unmatched:
        normalized_name = _build_normalized(rs.name)
        compact = _build_compact(rs.name)
        tokens = sorted({w for w in normalized_name.split() if len(w) > 1})
        domain = _extract_domain(rs.url)
        category_hint = rs.raw_payload.get("item_category") or rs.raw_payload.get("category") or "TODO"

        store_id = f"seed_store_{store_counter:03d}"
        store_counter += 1
        alias_id = f"seed_alias_{alias_counter:03d}"
        alias_counter += 1

        metadata: dict = {"category": str(category_hint), "source": rs.source_id}
        if domain:
            metadata["domain"] = domain

        new_stores.append({
            "id": store_id,
            "name": rs.name,
            "name_forms": {"normalized": normalized_name, "compact": compact, "tokens": tokens},
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-01T00:00:00+00:00",
            "metadata": metadata,
        })
        new_aliases.append({
            "id": alias_id,
            "store_id": store_id,
            "alias": rs.name,
            "alias_forms": {"normalized": normalized_name, "compact": compact, "tokens": tokens},
            "source": "seed",
            "created_at": "2024-01-01T00:00:00+00:00",
        })

    # --write: append directly into seed files
    if write:
        stores_seed_path = seed_path / "stores_seed.json"
        aliases_seed_path = seed_path / "aliases_seed.json"

        existing_s = json.loads(stores_seed_path.read_text(encoding="utf-8")) if stores_seed_path.exists() else []
        existing_a = json.loads(aliases_seed_path.read_text(encoding="utf-8")) if aliases_seed_path.exists() else []

        existing_s.extend(new_stores)
        existing_a.extend(new_aliases)

        stores_seed_path.write_text(json.dumps(existing_s, ensure_ascii=False, indent=2), encoding="utf-8")
        aliases_seed_path.write_text(json.dumps(existing_a, ensure_ascii=False, indent=2), encoding="utf-8")

        console.print(
            f"\n[green]Written {len(new_stores)} stores → [bold]{stores_seed_path}[/bold][/green]\n"
            f"[green]Written {len(new_aliases)} aliases → [bold]{aliases_seed_path}[/bold][/green]\n"
            "\n[yellow]Review metadata.category for each new entry — "
            "the value is taken from HOT's item_category and may need tidying.[/yellow]"
        )
        return

    # --export: write to a file for review
    if export:
        output = {
            "instructions": (
                "Append stores_seed entries to data/seed/stores_seed.json and "
                "aliases_seed entries to data/seed/aliases_seed.json. "
                "Review metadata.category — it is taken from item_category and may need tidying. "
                "Add extra alias rows for any other name variants (e.g. Hebrew-only, English-only)."
            ),
            "stores_seed": new_stores,
            "aliases_seed": new_aliases,
        }
        Path(export).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"\n[green]Exported → [bold]{export}[/bold][/green]")
        return

    console.print(
        "\nRun with [bold]--write[/bold] to append directly into the seed files, "
        "or [bold]--export <file>[/bold] to review first."
    )


@app.command(name="rematch-reviews")
def rematch_reviews(
    include_skipped: bool = typer.Option(
        True,
        "--include-skipped/--no-skipped",
        help="Also re-run matching on skipped items (default: yes).",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be approved without writing anything.",
    ),
    data_dir: str = typer.Option("data", "--data-dir", "-d"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Re-run the matching pipeline on pending review items.

    After adding new stores or aliases (to seed files or directly to the data
    files), use this command to re-process all pending and skipped review items
    without hitting any external server.  Items that now reach AUTO_MATCH
    confidence are automatically approved — alias and deal records are written
    just as if a human had approved them in the review session.
    """
    from lessley_deals.domain.enums import MatchDecision, ReviewStatus
    from lessley_deals.domain.models import NormalizedRecord
    from lessley_deals.matching.config import MatchConfig
    from lessley_deals.matching.index import AliasIndex
    from lessley_deals.matching.pipeline import MatchPipeline
    from lessley_deals.review.actions import ReviewActions
    from rich.table import Table

    _setup_logging(log_level)

    repos = _make_repos(data_dir)
    review_repo = repos.review_repo
    store_repo = repos.store_repo
    alias_repo = repos.alias_repo
    deal_repo = repos.deal_repo

    # Collect items to re-process
    target_statuses = {ReviewStatus.PENDING}
    if include_skipped:
        target_statuses.add(ReviewStatus.SKIPPED)

    items = [i for i in review_repo.get_all() if i.status in target_statuses]
    if not items:
        console.print("[green]No pending review items to re-process.[/green]")
        return

    console.print(f"Re-running match on [bold]{len(items)}[/bold] items…")

    # Rebuild index from the current (possibly updated) data files
    index = AliasIndex(aliases=alias_repo.get_all(), stores=store_repo.get_all())
    match_pipeline = MatchPipeline(MatchConfig())

    to_approve: list[tuple] = []   # (ReviewItem, new MatchVerdict)
    still_review: list = []
    no_match: list = []

    for item in items:
        normalized = NormalizedRecord(
            raw_id=item.raw_id,
            source_id="",
            store_name_forms=item.input_name_forms,
            deal_description="",
            normalized_at=item.created_at,
            domain=None,
        )
        new_verdict = match_pipeline.match(normalized, index)

        if new_verdict.decision == MatchDecision.AUTO_MATCH:
            to_approve.append((item, new_verdict))
        elif new_verdict.decision == MatchDecision.REVIEW:
            still_review.append(item)
        else:
            no_match.append(item)

    # Summary table for items that will be approved
    if to_approve:
        table = Table(title=f"Newly auto-matched ({len(to_approve)})")
        table.add_column("Input Name")
        table.add_column("Matched Store")
        table.add_column("Conf.", justify="right")
        table.add_column("Stage")
        for it, v in to_approve:
            best = v.best
            table.add_row(
                it.input_name,
                best.store_name if best else "—",
                f"{best.confidence:.3f}" if best else "—",
                best.stage if best else "—",
            )
        console.print(table)

    console.print(
        f"\n[green]Auto-match:[/green] {len(to_approve)}  "
        f"[yellow]Still review:[/yellow] {len(still_review)}  "
        f"[red]No match:[/red] {len(no_match)}\n"
    )

    if dry_run:
        console.print("[dim]--dry-run: no changes written.[/dim]")
        return

    if not to_approve:
        console.print("[green]Nothing new to approve.[/green]")
        return

    actions = ReviewActions(
        review_repo=review_repo,
        store_repo=store_repo,
        alias_repo=alias_repo,
        deal_repo=deal_repo,
    )

    for item, new_verdict in to_approve:
        item.verdict = new_verdict
        actions.approve(item, reviewed_by="system:rematch")

    console.print(f"[green]Approved {len(to_approve)} items.[/green]")


@app.command(name="seed")
def seed_mongo(
    seed_dir: str = typer.Option("data/seed", "--seed-dir", help="Directory containing seed JSON files"),
    from_live: bool = typer.Option(
        False,
        "--from-live",
        help="Also migrate current data/ JSON files (stores, aliases, deals, reviews) into MongoDB.",
    ),
    data_dir: str = typer.Option("data", "--data-dir", "-d"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Import seed data into MongoDB (idempotent — safe to run multiple times).

    Reads data/seed/stores.json and data/seed/store_aliases.json and upserts
    each record using $setOnInsert so existing documents are never overwritten.

    Use --from-live to also migrate the current working data/ JSON files into
    MongoDB (one-time operation when moving from JSON to MongoDB storage).

    Requires DEALS_STORAGE=mongo (or pass MONGO_URI directly).
    """
    import json

    _setup_logging(log_level)

    storage = os.environ.get("DEALS_STORAGE", "json").lower()
    if storage != "mongo":
        console.print(
            "[red]seed command requires DEALS_STORAGE=mongo.[/red]\n"
            "Set the environment variable and retry."
        )
        raise typer.Exit(code=1)

    from lessley_deals.persistence.mongo_client import get_database
    from lessley_deals.persistence.repositories.mongo.aliases import AliasMongoRepository
    from lessley_deals.persistence.repositories.mongo.stores import CanonicalStoreMongoRepository
    from lessley_deals.persistence.serialization import (
        alias_from_dict,
        canonical_store_from_dict,
        deal_from_dict,
        raw_deal_from_dict,
        raw_store_from_dict,
    )

    db = get_database()
    store_repo = CanonicalStoreMongoRepository(db)
    alias_repo = AliasMongoRepository(db)

    seed_path = Path(seed_dir)

    # --- Seed stores ---
    stores_file = seed_path / "stores.json"
    if stores_file.exists():
        stores_data = json.loads(stores_file.read_text(encoding="utf-8"))
        inserted = 0
        for d in stores_data:
            doc = {k: v for k, v in d.items()}
            doc_id = doc.pop("id")
            doc["_id"] = doc_id
            result = db["stores"].update_one({"_id": doc_id}, {"$setOnInsert": doc}, upsert=True)
            if result.upserted_id is not None:
                inserted += 1
        console.print(f"[green]Stores seed:[/green] {inserted} inserted, {len(stores_data) - inserted} already existed")
    else:
        console.print(f"[yellow]No stores seed file found at {stores_file}[/yellow]")

    # --- Seed aliases ---
    aliases_file = seed_path / "store_aliases.json"
    if aliases_file.exists():
        aliases_data = json.loads(aliases_file.read_text(encoding="utf-8"))
        inserted = 0
        for d in aliases_data:
            doc = {k: v for k, v in d.items()}
            doc_id = doc.pop("id")
            doc["_id"] = doc_id
            result = db["store_aliases"].update_one({"_id": doc_id}, {"$setOnInsert": doc}, upsert=True)
            if result.upserted_id is not None:
                inserted += 1
        console.print(f"[green]Aliases seed:[/green] {inserted} inserted, {len(aliases_data) - inserted} already existed")
    else:
        console.print(f"[yellow]No aliases seed file found at {aliases_file}[/yellow]")

    # --- Seed clubs (sources) ---
    _CLUBS = [
        {"_id": "club_hot",        "id": "club_hot",        "name": "HOT Israel",       "source_id": "hot",        "description": "HOT Israel — cable TV & internet member benefits", "metadata": {}},
        {"_id": "club_mastercard", "id": "club_mastercard", "name": "Mastercard Israel", "source_id": "mastercard", "description": "Mastercard Israel credit card benefits", "metadata": {}},
        {"_id": "club_topcash",    "id": "club_topcash",    "name": "Isracard TopCash",  "source_id": "topcash",    "description": "Isracard TopCash cashback benefits", "metadata": {}},
        {"_id": "club_behatsdaa",  "id": "club_behatsdaa",  "name": "Behatsdaa",         "source_id": "behatsdaa",  "description": "Behatsdaa deals aggregator", "metadata": {}},
    ]
    inserted = 0
    for club_doc in _CLUBS:
        doc = {k: v for k, v in club_doc.items() if k != "id"}
        result = db["clubs"].update_one({"_id": club_doc["_id"]}, {"$setOnInsert": doc}, upsert=True)
        if result.upserted_id is not None:
            inserted += 1
    console.print(f"[green]Clubs seed:[/green] {inserted} inserted, {len(_CLUBS) - inserted} already existed")

    if not from_live:
        console.print("\n[dim]Tip: use --from-live to also migrate your current data/ JSON files.[/dim]")
        return

    # --- Migrate live JSON data ---
    config = _get_config(data_dir)
    console.print("\n[bold]Migrating live JSON files → MongoDB…[/bold]")

    def _migrate(path: Path, collection: str, from_dict_fn, get_id) -> None:  # type: ignore[type-arg]
        from pymongo.errors import DuplicateKeyError as _DupKey
        if not path.exists():
            console.print(f"  [dim]{path} not found, skipping[/dim]")
            return
        items = json.loads(path.read_text(encoding="utf-8"))
        inserted = skipped = 0
        for raw in items:
            obj = from_dict_fn(raw)
            doc = {k: v for k, v in raw.items()}
            doc_id = get_id(obj)
            doc.pop("id", None)
            doc["_id"] = doc_id
            try:
                result = db[collection].update_one({"_id": doc_id}, {"$setOnInsert": doc}, upsert=True)
                if result.upserted_id is not None:
                    inserted += 1
                else:
                    skipped += 1
            except _DupKey:
                # Duplicate fingerprint/alias under a different _id — already in DB
                skipped += 1
        console.print(f"  [green]{collection}:[/green] {inserted} inserted, {skipped} skipped (already in DB)")

    _migrate(config.stores_path, "stores", canonical_store_from_dict, lambda o: o.id)
    _migrate(config.aliases_path, "store_aliases", alias_from_dict, lambda o: o.id)
    _migrate(config.deals_path, "deals", deal_from_dict, lambda o: o.id)
    _migrate(config.raw_deals_path, "raw_source_deals", raw_deal_from_dict, lambda o: o.id)
    _migrate(config.raw_stores_path, "raw_source_stores", raw_store_from_dict, lambda o: o.id)
    console.print("  [dim]store_match_review stays in local JSON (per-user review queue)[/dim]")

    console.print("\n[green]Migration complete.[/green]")


@app.command(name="export")
def export_stores(
    out_dir: str = typer.Option("data/seed", "--out", "-o", help="Directory to write stores.json and store_aliases.json"),
    data_dir: str = typer.Option("data", "--data-dir", "-d"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Export canonical stores and aliases from the active storage backend to JSON files.

    Works with both JSON and MongoDB storage (DEALS_STORAGE env var).
    Output files are written in the same format as the seed files, so you can
    review/edit them and re-import with: python -m deals seed-mongo --seed-dir <out>
    """
    import json

    _setup_logging(log_level)

    repos = _make_repos(data_dir)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    from lessley_deals.persistence.serialization import to_dict

    stores = repos.store_repo.get_all()
    stores_file = out_path / "stores.json"
    stores_file.write_text(
        json.dumps([to_dict(s) for s in stores], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    console.print(f"[green]Exported {len(stores)} stores →[/green] {stores_file}")

    aliases = repos.alias_repo.get_all()
    aliases_file = out_path / "store_aliases.json"
    aliases_file.write_text(
        json.dumps([to_dict(a) for a in aliases], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    console.print(f"[green]Exported {len(aliases)} aliases →[/green] {aliases_file}")


@app.command(name="enrich-stores")
def enrich_stores_cmd(
    data_dir: str = typer.Option("data", "--data-dir", "-d"),
    limit: int = typer.Option(0, "--limit", "-n", help="Enrich at most N stores (0 = all)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Call the LLM but do not write stores.json"),
    force: bool = typer.Option(False, "--force", help="Re-enrich stores that already have mcc_codes"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Add `metadata.mcc_codes` to each store in stores.json using the LLM classifier."""
    logging.basicConfig(level=log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    from lessley_deals.enrichment.enrich_stores import enrich_stores

    stats = enrich_stores(data_dir=data_dir, limit=limit, dry_run=dry_run, force=force)
    console.print(
        f"[green]Done.[/green] total={stats['total']} "
        f"processed={stats['processed']} skipped={stats['skipped']} failed={stats['failed']}"
        + (" [yellow](dry-run)[/yellow]" if dry_run else "")
    )


@app.command(name="enrich-store-urls")
def enrich_store_urls_cmd(
    data_dir: str = typer.Option("data", "--data-dir", "-d"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would change without writing stores.json"),
    force: bool = typer.Option(False, "--force", help="Re-check stores that already have a non-null store_url"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Populate `metadata.store_url` on each store from the first usable deal URL."""
    _setup_logging(log_level)

    from lessley_deals.enrichment.enrich_store_urls import enrich_store_urls

    stats = enrich_store_urls(data_dir=data_dir, dry_run=dry_run, force=force)
    console.print(
        f"[green]Done.[/green] total={stats['total']} "
        f"set={stats['set']} nulled={stats['nulled']} skipped={stats['skipped']}"
        + (" [yellow](dry-run)[/yellow]" if dry_run else "")
    )


@app.command(name="optimize")
def optimize_cmd(
    store_id: str = typer.Argument(..., help="Target store_id to optimize the cart for"),
    cart_total: float = typer.Argument(..., help="Total cart value in ILS"),
    quantity: int = typer.Option(1, "--quantity", "-q", help="Cart item quantity"),
    data_dir: str = typer.Option("data", "--data-dir", "-d", help="Reads <data-dir>/deals.json unless --file is set"),
    file: Optional[str] = typer.Option(None, "--file", help="Deals JSON file to read instead of <data-dir>/deals.json"),
    strict: bool = typer.Option(
        False, "--strict", help="Treat combinability 'unknown' as 'no' (default: optimistic 'yes')"
    ),
    wallet_id: Optional[str] = typer.Option(
        None, "--wallet-id", help="user_id to load from --wallet-file as a baseline user context"
    ),
    wallet_file: Optional[str] = typer.Option(
        None, "--wallet-file", help="Path to a mock wallets JSON file (required if --wallet-id is passed)"
    ),
    member_clubs: Optional[str] = typer.Option(
        None, "--member-clubs", help="Comma-separated club_ids the user belongs to, e.g. club_a,club_b"
    ),
    channels: Optional[str] = typer.Option(
        None, "--channels", help="Comma-separated preferred redemption channels, e.g. website,mobile_app"
    ),
    monthly_uses: Optional[str] = typer.Option(
        None, "--monthly-uses", help="Comma-separated deal_id:count already used this month, e.g. D11:1"
    ),
    top_n: int = typer.Option(5, "--top-n", help="Number of ranked options to show (default 5)"),
    verbose: bool = typer.Option(
        False, "--verbose", help="Print the eligibility prune, DP-sweep decisions, and exclusion reasons"
    ),
) -> None:
    """Find the cheapest legal stack of deals for a store + cart (deal-optimizer engine)."""
    try:
        from deal_optimizer.engine import UserContext, get_optimal_deal_path
        from deal_optimizer.wallet import load_wallets, wallet_to_user_context
    except ModuleNotFoundError as exc:
        console.print(
            "[red]deal_optimizer is not installed in this environment.[/red]\n"
            "It lives in the sibling [bold]deal-optimizer/[/bold] package. From this venv, run:\n"
            "  [bold]pip install -e ../deal-optimizer[/bold]"
        )
        raise typer.Exit(code=1) from exc

    wallet_ctx: Optional[UserContext] = None
    if wallet_id:
        if not wallet_file:
            console.print("[red]--wallet-id requires --wallet-file[/red]")
            raise typer.Exit(code=1)
        wallets = load_wallets(wallet_file)
        wallet = wallets.get(wallet_id)
        if wallet is None:
            console.print(f"[red]No wallet with user_id={wallet_id!r} in {wallet_file}[/red]")
            raise typer.Exit(code=1)
        wallet_ctx = wallet_to_user_context(wallet)

    user_context = None
    if member_clubs or channels or monthly_uses or wallet_ctx:
        uses_this_month: dict[str, int] = dict(wallet_ctx.uses_this_month) if wallet_ctx else {}
        if monthly_uses:
            for pair in monthly_uses.split(","):
                deal_id, _, count = pair.partition(":")
                uses_this_month[deal_id.strip()] = int(count.strip() or 0)

        member_club_ids = list(wallet_ctx.member_club_ids) if wallet_ctx else []
        if member_clubs:
            member_club_ids += [c.strip() for c in member_clubs.split(",")]

        preferred_channels = list(wallet_ctx.preferred_channels) if wallet_ctx else []
        if channels:
            preferred_channels += [c.strip() for c in channels.split(",")]

        user_context = UserContext(
            member_club_ids=member_club_ids,
            preferred_channels=preferred_channels,
            uses_this_month=uses_this_month,
        )

    results = get_optimal_deal_path(
        file_path=file or str(Path(data_dir) / "deals.json"),
        target_store_id=store_id,
        cart_total=cart_total,
        cart_quantity=quantity,
        user_context=user_context,
        unknown_as_yes=not strict,
        top_n=top_n,
        verbose=verbose,
    )

    print(f"\nStore: {store_id}  |  Cart: {cart_total:.2f} ILS  |  Items: {quantity}")
    print(f"Starting price: {cart_total:.2f}")
    if not results or not results[0]["per_step"]:
        print("No applicable deals found.")
        return

    print(f"Top {len(results)} option(s) (cheapest first):")
    for result in results:
        print("=" * 60)
        console.print(
            f"[bold]#{result['rank']}[/bold] — [green]Final price: {result['final_price']:.2f}[/green]  "
            f"(saved {result['total_savings']:.2f})"
        )
        print("-" * 60)
        for i, step in enumerate(result["per_step"], 1):
            deal = result["path"][i - 1]
            title = deal.get("title") or deal.get("deal_description") or deal.get("id")
            print(f"  {i}. [{deal.get('deal_type', '?')}] {title}")
            if step["ils_covered"] is not None:
                print(f"     pays for {step['ils_covered']:.2f} ILS of the bill via this instrument")
            print(f"     {step['price_in']:.2f} -> {step['price_out']:.2f}  (deal {step['deal_id']})")


@app.command(name="enrich-constraints")
def enrich_constraints_cmd(
    data_dir: str = typer.Option("data", "--data-dir", "-d"),
    source: str = typer.Option(
        "hot",
        "--source",
        "-s",
        help="Only enrich deals from this source_id. Pass an empty string to enrich all sources.",
    ),
    limit: int = typer.Option(0, "--limit", "-n", help="Enrich at most N deals (0 = all)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Call the LLM but do not write deals.json"),
    force: bool = typer.Option(False, "--force", help="Re-parse deals that already have constraints"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Parse `terms_and_conditions` into a structured `constraints` object on each deal."""
    _setup_logging(log_level)

    from lessley_deals.enrichment.enrich_deal_constraints import enrich_deal_constraints

    stats = enrich_deal_constraints(
        data_dir=data_dir, source=source, limit=limit, dry_run=dry_run, force=force
    )
    console.print(
        f"[green]Done.[/green] total={stats['total']} "
        f"processed={stats['processed']} skipped={stats['skipped']} failed={stats['failed']}"
        + (" [yellow](dry-run)[/yellow]" if dry_run else "")
    )


if __name__ == "__main__":
    app()
