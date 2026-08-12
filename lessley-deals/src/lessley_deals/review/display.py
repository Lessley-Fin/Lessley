from __future__ import annotations

import logging

from bidi.algorithm import get_display
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lessley_deals.domain.models import CanonicalStore, ReviewItem
from lessley_deals.enrichment.mcc_catalog import MCC_CATEGORIES
from lessley_deals.review.queue import QueueStats

logger = logging.getLogger(__name__)


class ReviewDisplay:
    """Rich terminal rendering for the review workflow."""

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    def show_item(self, item: ReviewItem, index: int, total: int) -> None:
        """Display a review item with its candidates."""
        header = f"Review [{index}/{total}]"
        preferred_name = item.raw_input_name or item.input_name
        lines: list[str] = [
            f"[bold]Input name:[/bold]      {get_display(preferred_name)}",
            f"[bold]Normalized:[/bold]       {get_display(item.input_name_forms.normalized)}",
            f"[bold]Raw ID:[/bold]           {item.raw_id}",
            f"[bold]Status:[/bold]           {item.status.value}",
        ]

        self._console.print(Panel("\n".join(lines), title=header, expand=False))

        # Candidates table
        candidates = item.verdict.candidates
        if candidates:
            table = Table(title="Candidates", show_lines=True)
            table.add_column("#", justify="right", style="dim", width=3)
            table.add_column("Store Name", style="cyan")
            table.add_column("Confidence", justify="right", style="magenta")
            table.add_column("Stage", style="green")

            for i, c in enumerate(candidates, 1):
                table.add_row(
                    str(i),
                    get_display(c.store_name),
                    f"{c.confidence:.2f}",
                    c.stage,
                )
            self._console.print(table)
        else:
            self._console.print("[dim]No candidates found.[/dim]")

        # Explanation
        explanation = item.verdict.explanation
        self._console.print(
            f"\n[bold]Explanation:[/bold] {explanation.reason}"
        )
        if explanation.stage_matched:
            self._console.print(
                f"[bold]Matched at stage:[/bold] {explanation.stage_matched}"
            )

    def show_actions(self) -> None:
        """Display available review actions."""
        table = Table(show_header=True, show_lines=False, box=None, padding=(0, 2))
        table.add_column("Key", style="bold", width=5)
        table.add_column("Action", width=16)
        table.add_column("Parameters")

        table.add_row("[green]a[/green]", "approve",       "[dim]— approves the top candidate (no input)[/dim]")
        table.add_row("[cyan]l[/cyan]",   "link existing", "[dim]search: <query>  →  select #[/dim]")
        table.add_row("[yellow]c[/yellow]", "create new",  "[dim]name: <store name>  (Enter = use input name)[/dim]")
        table.add_row("[magenta]m[/magenta]", "set MCC",   "[dim]tag a store's categories (stays on this item)[/dim]")
        table.add_row("[red]d[/red]",     "discard",       "[dim]reason: <optional note>[/dim]")
        table.add_row("[blue]s[/blue]",   "skip",          "[dim]— defers to next session (no input)[/dim]")
        table.add_row("[dim]q[/dim]",     "quit",          "[dim]— ends the session[/dim]")

        self._console.print("\n[bold]Actions:[/bold]")
        self._console.print(table)

    def show_store_search_results(
        self,
        stores: list,
        aliases_by_store: dict[str, list[str]] | None = None,
    ) -> None:
        """Display store search results for the link-existing flow."""
        if not stores:
            self._console.print("[dim]No stores found.[/dim]")
            return
        table = Table(title="Matching Stores", show_lines=True)
        table.add_column("#", justify="right", style="dim", width=3)
        table.add_column("Name", style="cyan")
        table.add_column("Aliases", style="yellow")
        for i, store in enumerate(stores, 1):
            aliases = aliases_by_store.get(store.id, []) if aliases_by_store else []
            alias_str = ", ".join(get_display(a) for a in aliases) if aliases else "[dim]—[/dim]"
            table.add_row(str(i), get_display(store.name), alias_str)
        self._console.print(table)

    def show_store_mcc(self, store: CanonicalStore) -> None:
        """Show a store's current MCC categories before they are edited."""
        codes = store.metadata.get("mcc_codes") or []
        current = ", ".join(str(c) for c in codes) if codes else "[dim]— none —[/dim]"
        self._console.print(
            f"\n[bold]Store:[/bold] {get_display(store.name)}   "
            f"[bold]MCC:[/bold] {current}"
        )

    def show_mcc_catalog(self) -> None:
        """List the canonical categories with the numbers used to select them.

        Rendered with ``Columns`` rather than a fixed-width table: the longest
        category name is 28 characters, so a table wide enough for three of them
        gets squeezed on an 80-column terminal and rich drops the number column —
        exactly the part the reviewer types.
        """
        entries = [
            f"[dim]{i:>2}[/dim] [cyan]{name}[/cyan]"
            for i, name in enumerate(MCC_CATEGORIES, 1)
        ]
        self._console.print("\n[bold]MCC categories:[/bold]")
        self._console.print(Columns(entries, padding=(0, 2), equal=True, column_first=True))

    def show_mcc_suggestion(self, official_name: str, codes: list[str], confidence: str) -> None:
        """Show what the LLM proposed for a store."""
        self._console.print(
            f"[bold]Suggested:[/bold] {', '.join(codes) or '—'}   "
            f"[dim](official name: {get_display(official_name)}, confidence: {confidence})[/dim]"
        )

    def show_stats(self, stats: QueueStats) -> None:
        """Display queue statistics."""
        table = Table(title="Review Queue Stats", show_lines=True)
        table.add_column("Metric", style="bold")
        table.add_column("Count", justify="right")

        table.add_row("Total", str(stats.total))
        table.add_row("Pending", f"[yellow]{stats.pending}[/yellow]")
        table.add_row("Approved", f"[green]{stats.approved}[/green]")
        table.add_row("Created", f"[cyan]{stats.created}[/cyan]")
        table.add_row("Discarded", f"[red]{stats.discarded}[/red]")
        table.add_row("Skipped", f"[blue]{stats.skipped}[/blue]")

        self._console.print(table)

    def success(self, message: str) -> None:
        self._console.print(f"[bold green]{message}[/bold green]")

    def warning(self, message: str) -> None:
        self._console.print(f"[bold yellow]{message}[/bold yellow]")

    def error(self, message: str) -> None:
        self._console.print(f"[bold red]{message}[/bold red]")
