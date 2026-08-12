from __future__ import annotations

from lessley_deals.domain.models import CanonicalStore
from lessley_deals.enrichment.mcc_catalog import MCC_CATEGORIES, coerce_category
from lessley_deals.persistence.repositories.aliases import AliasJsonRepository
from lessley_deals.persistence.repositories.deals import DealJsonRepository
from lessley_deals.persistence.repositories.raw_deals import RawDealJsonRepository
from lessley_deals.persistence.repositories.reviews import ReviewJsonRepository
from lessley_deals.persistence.repositories.stores import CanonicalStoreJsonRepository
from lessley_deals.review.actions import ReviewActions
from lessley_deals.review.display import ReviewDisplay
from lessley_deals.review.queue import QueueFilter, ReviewQueue


def parse_mcc_selection(text: str) -> tuple[list[str], list[str]]:
    """Parse a comma-separated MCC entry into (categories, unrecognized tokens).

    Each token is either a catalog number as shown by ``show_mcc_catalog``, a
    category name (any casing/spacing), or a 4-digit MCC. Order is preserved and
    duplicates are dropped so the result stays a ranked list.
    """
    categories: list[str] = []
    unknown: list[str] = []
    for token in (t.strip() for t in text.split(",")):
        if not token:
            continue
        category: str | None = None
        if token.isdigit() and 1 <= int(token) <= len(MCC_CATEGORIES):
            category = MCC_CATEGORIES[int(token) - 1]
        else:
            category = coerce_category(token)
        if category is None:
            unknown.append(token)
        elif category not in categories:
            categories.append(category)
    return categories, unknown


def run_review_session(
    review_repo: ReviewJsonRepository,
    store_repo: CanonicalStoreJsonRepository,
    alias_repo: AliasJsonRepository,
    deal_repo: DealJsonRepository,
    raw_deal_repo: RawDealJsonRepository | None = None,
    batch_size: int = 0,
    source_filter: str | None = None,
    continuous: bool = False,
    mcc_on_create: bool = True,
) -> None:
    """Run an interactive review session."""
    import time

    queue = ReviewQueue(review_repo)
    actions = ReviewActions(review_repo, store_repo, alias_repo, deal_repo)
    display = ReviewDisplay()

    def _search_and_pick_store(prompt: str) -> CanonicalStore | None:
        """Search stores by name or alias and let the user pick one."""
        query = input(prompt).strip()
        if not query:
            display.warning("Cancelled.")
            return None
        results = store_repo.search(query)
        # also search by alias and merge (dedup by store id)
        alias_hits = alias_repo.search(query)
        seen_ids = {s.id for s in results}
        for a in alias_hits:
            if a.store_id not in seen_ids:
                store = store_repo.get_by_id(a.store_id)
                if store:
                    results.append(store)
                    seen_ids.add(store.id)
        # build aliases per store for display
        aliases_by_store = {
            s.id: [a.alias for a in alias_repo.get_by_store(s.id)]
            for s in results
        }
        display.show_store_search_results(results, aliases_by_store)
        if not results:
            return None
        pick = input(f"Select number (1-{len(results)}) or Enter to cancel: ").strip()
        if not pick:
            display.warning("Cancelled.")
            return None
        try:
            idx = int(pick) - 1
            if not (0 <= idx < len(results)):
                raise ValueError
        except ValueError:
            display.error("Invalid selection.")
            return None
        return results[idx]

    def _set_mcc(store: CanonicalStore) -> None:
        """Prompt for MCC categories and write them onto `store`."""
        display.show_store_mcc(store)
        display._console.print(
            "[dim]Enter categories (comma-separated names or catalog numbers), "
            "[bold]?[/bold] to list the catalog, [bold]s[/bold] for an LLM suggestion, "
            "Enter to cancel.[/dim]"
        )
        suggestion: list[str] = []

        while True:
            raw = input("MCC: ").strip()

            if not raw:
                display.warning("MCC unchanged.")
                return

            if raw == "?":
                display.show_mcc_catalog()
                continue

            if raw.lower() == "s":
                result = actions.suggest_store_mcc(store)
                if result is None:
                    display.error("Suggestion unavailable (no LLM credentials or the call failed).")
                    continue
                suggestion = list(result.mcc_codes)
                display.show_mcc_suggestion(
                    result.official_name, suggestion, result.confidence_level
                )
                display._console.print(
                    "[dim]Type [bold]y[/bold] to accept it, or enter your own categories.[/dim]"
                )
                continue

            categories: list[str]
            unknown: list[str]
            if raw.lower() == "y":
                if not suggestion:
                    display.error("No suggestion to accept — press [s] first.")
                    continue
                categories, unknown = suggestion, []
            else:
                categories, unknown = parse_mcc_selection(raw)

            if unknown:
                display.error(f"Not a known category: {', '.join(unknown)}  (use ? to list them)")
                continue
            if not categories:
                display.error("Nothing selected.")
                continue

            try:
                updated = actions.set_store_mcc(store.id, categories, reviewed_by="cli_user")
            except ValueError as exc:
                display.error(str(exc))
                continue
            display.success(
                f"MCC set: '{updated.name}' -> {', '.join(updated.metadata['mcc_codes'])}"
            )
            return

    def _hydrate_raw_input_name(item):
        if item.raw_input_name or raw_deal_repo is None:
            return item
        raw_record = raw_deal_repo.get_by_id(item.raw_id)
        if raw_record is not None:
            item.raw_input_name = raw_record.store_name
        return item

    def _process_pending() -> bool:
        """Process all pending items in the current batch.

        Returns True if the user pressed [q] to quit, False otherwise.
        """
        queue_filter = QueueFilter(source_id=source_filter) if source_filter else None

        if not queue.get_pending(queue_filter):
            return False

        processed = 0
        i = 0
        while True:
            # Reload from disk before each item so external edits are reflected.
            pending = queue.get_pending(queue_filter)
            if not pending:
                break
            if batch_size > 0 and processed >= batch_size:
                break

            i += 1
            item = pending[0]
            item = _hydrate_raw_input_name(item)
            total = len(pending)
            display._console.print(
                f"\n[bold]Review session: {total} items remaining[/bold]\n"
            )
            display.show_item(item, i, i + total - 1)
            display.show_actions()

            while True:
                choice = input("\nAction: ").strip().lower()

                if choice == "a":
                    if not item.verdict.best:
                        display.error("No candidate to approve.")
                        continue
                    actions.approve(item, reviewed_by="cli_user")
                    display.success(
                        f"Approved: '{item.input_name}' -> "
                        f"store '{item.verdict.best.store_name}'"
                    )
                    processed += 1
                    break

                elif choice == "l":
                    chosen = _search_and_pick_store("Search store name: ")
                    if chosen is None:
                        continue
                    actions.approve_existing(
                        item,
                        store_id=chosen.id,
                        store_name=chosen.name,
                        reviewed_by="cli_user",
                        note="manually linked",
                    )
                    display.success(
                        f"Linked: '{item.input_name}' -> store '{chosen.name}'"
                    )
                    processed += 1
                    break

                elif choice == "c":
                    default_name = item.raw_input_name or item.input_name
                    name = input("New store name (Enter for input name): ").strip()
                    if not name:
                        name = default_name
                    updated_item = actions.create_new(
                        item, store_name=name, reviewed_by="cli_user"
                    )
                    display.success(f"Created new store: '{name}'")
                    if mcc_on_create and updated_item.decision is not None:
                        new_store_id = updated_item.decision.store_id
                        new_store = (
                            store_repo.get_by_id(new_store_id) if new_store_id else None
                        )
                        if new_store is not None:
                            _set_mcc(new_store)
                    processed += 1
                    break

                elif choice == "m":
                    best = item.verdict.best or (
                        item.verdict.candidates[0] if item.verdict.candidates else None
                    )
                    target = store_repo.get_by_id(best.store_id) if best else None
                    if target is None:
                        display.warning(
                            "No candidate store on this item — search for the one to tag."
                        )
                        target = _search_and_pick_store("Search store name: ")
                    if target is None:
                        continue
                    _set_mcc(target)
                    continue

                elif choice == "d":
                    note = input("Reason (optional): ").strip() or None
                    actions.discard(item, reviewed_by="cli_user", note=note)
                    display.warning("Discarded.")
                    processed += 1
                    break

                elif choice == "s":
                    actions.skip(item)
                    display.warning("Skipped.")
                    processed += 1
                    break

                elif choice == "q":
                    display._console.print(
                        f"\n[bold]Session ended. Processed {processed} items.[/bold]"
                    )
                    return True

                else:
                    display.error(
                        "Invalid choice. Use: "
                        "[a]pprove, [l]ink existing, [c]reate, set [m]cc, "
                        "[d]iscard, [s]kip, [q]uit"
                    )

        display._console.print(
            f"\n[bold]Session complete. Processed {processed} items.[/bold]"
        )
        return False

    if not continuous:
        queue_filter = QueueFilter(source_id=source_filter) if source_filter else None
        if not queue.get_pending(queue_filter):
            display.warning("No pending review items.")
            return
        _process_pending()
        return

    # Continuous mode
    try:
        while True:
            queue_filter = QueueFilter(source_id=source_filter) if source_filter else None
            pending = queue.get_pending(queue_filter)
            if pending:
                quit_requested = _process_pending()
                if quit_requested:
                    return
            else:
                display.warning(
                    "Queue empty. Waiting for new items... (Ctrl+C to stop)"
                )
                time.sleep(30)
    except KeyboardInterrupt:
        display._console.print("\n[bold]Continuous mode stopped.[/bold]")
