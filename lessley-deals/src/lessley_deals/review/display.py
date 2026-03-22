from __future__ import annotations

import logging

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lessley_deals.domain.models import ReviewItem
from lessley_deals.review.queue import QueueStats

logger = logging.getLogger(__name__)


class ReviewDisplay:
    """Rich terminal rendering for the review workflow."""

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    def show_item(self, item: ReviewItem, index: int, total: int) -> None:
        """Display a review item with its candidates."""
        header = f"Review [{index}/{total}]"
        lines: list[str] = [
            f"[bold]Input name:[/bold]      {item.input_name}",
            f"[bold]Normalized:[/bold]       {item.input_name_forms.normalized}",
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
                    c.store_name,
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
        self._console.print(
            "\n[bold]Actions:[/bold] "
            "[green][a][/green]pprove  "
            "[yellow][c][/yellow]reate new  "
            "[red][d][/red]iscard  "
            "[blue][s][/blue]kip  "
            "[dim][q][/dim]uit"
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
