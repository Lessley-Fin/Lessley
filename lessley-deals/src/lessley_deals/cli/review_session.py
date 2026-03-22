from __future__ import annotations

from lessley_deals.persistence.repositories.aliases import AliasJsonRepository
from lessley_deals.persistence.repositories.deals import DealJsonRepository
from lessley_deals.persistence.repositories.raw_deals import RawDealJsonRepository
from lessley_deals.persistence.repositories.reviews import ReviewJsonRepository
from lessley_deals.persistence.repositories.stores import CanonicalStoreJsonRepository
from lessley_deals.review.actions import ReviewActions
from lessley_deals.review.display import ReviewDisplay
from lessley_deals.review.queue import QueueFilter, ReviewQueue


def run_review_session(
    review_repo: ReviewJsonRepository,
    store_repo: CanonicalStoreJsonRepository,
    alias_repo: AliasJsonRepository,
    deal_repo: DealJsonRepository,
    raw_deal_repo: RawDealJsonRepository | None = None,
    batch_size: int = 0,
    source_filter: str | None = None,
) -> None:
    """Run an interactive review session."""
    queue = ReviewQueue(review_repo)
    actions = ReviewActions(review_repo, store_repo, alias_repo, deal_repo)
    display = ReviewDisplay()

    queue_filter = QueueFilter(source_id=source_filter) if source_filter else None
    pending = queue.get_pending(queue_filter)

    if not pending:
        display.warning("No pending review items.")
        return

    total = len(pending)
    if batch_size > 0:
        pending = pending[:batch_size]

    display._console.print(f"\n[bold]Review session: {len(pending)} items to review (of {total} pending)[/bold]\n")

    processed = 0
    for i, item in enumerate(pending):
        display.show_item(item, i + 1, len(pending))
        display.show_actions()

        while True:
            choice = input("\nAction: ").strip().lower()

            if choice == "a":
                if not item.verdict.best:
                    display.error("No candidate to approve.")
                    continue
                updated = actions.approve(item, reviewed_by="cli_user")
                display.success(
                    f"Approved: '{item.input_name}' -> store '{item.verdict.best.store_name}'"
                )
                processed += 1
                break

            elif choice == "c":
                name = input("New store name (Enter for input name): ").strip()
                if not name:
                    name = item.input_name
                updated = actions.create_new(item, store_name=name, reviewed_by="cli_user")
                display.success(f"Created new store: '{name}'")
                processed += 1
                break

            elif choice == "d":
                note = input("Reason (optional): ").strip() or None
                updated = actions.discard(item, reviewed_by="cli_user", note=note)
                display.warning("Discarded.")
                processed += 1
                break

            elif choice == "s":
                updated = actions.skip(item)
                display.warning("Skipped.")
                processed += 1
                break

            elif choice == "q":
                display._console.print(f"\n[bold]Session ended. Processed {processed}/{len(pending)} items.[/bold]")
                return

            else:
                display.error("Invalid choice. Use: [a]pprove, [c]reate, [d]iscard, [s]kip, [q]uit")

    display._console.print(f"\n[bold]Session complete. Processed {processed}/{len(pending)} items.[/bold]")
