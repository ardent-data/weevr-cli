"""Implementation of the weevr plugins subcommands (list, info)."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict

import typer
from rich.table import Table

from weevr_cli.plugins.registry import get_registry
from weevr_cli.state import AppState

plugins_app = typer.Typer(
    name="plugins",
    help="Manage CLI plugins.",
    no_args_is_help=True,
)

_STATUS_STYLES: dict[str, str] = {
    "loaded": "green",
    "failed": "red",
    "skipped": "yellow",
}


@plugins_app.command(name="list")
def list_plugins(ctx: typer.Context) -> None:
    """List all discovered plugins and their status."""
    state: AppState = ctx.obj
    registry = get_registry()
    records = registry.all()

    if state.json_mode:
        data = [asdict(r) for r in records]
        sys.stdout.write(json.dumps(data) + "\n")
        sys.stdout.flush()
        return

    if not records:
        state.console.print("No plugins installed.")
        return

    table = Table(title="Plugins")
    table.add_column("Name", style="bold")
    table.add_column("Version")
    table.add_column("Status")
    table.add_column("Source")

    for record in records:
        style = _STATUS_STYLES.get(record.status, "")
        table.add_row(
            record.display_name,
            record.version or "—",
            f"[{style}]{record.status}[/{style}]",
            record.source_package or "—",
        )

    state.console.print(table)


@plugins_app.command()
def info(ctx: typer.Context, name: str = typer.Argument(..., help="Plugin name.")) -> None:
    """Show detailed information about a specific plugin."""
    state: AppState = ctx.obj
    registry = get_registry()
    record = registry.get(name)

    if record is None:
        if state.json_mode:
            sys.stderr.write(
                json.dumps({"error": f"Plugin '{name}' not found", "code": "plugin_not_found"})
                + "\n"
            )
            sys.stderr.flush()
        else:
            state.console.print(f"[red]Error:[/red] Plugin '{name}' not found.")
        raise typer.Exit(code=1)

    if state.json_mode:
        sys.stdout.write(json.dumps(asdict(record)) + "\n")
        sys.stdout.flush()
        return

    state.console.print(f"[bold]Name:[/bold] {record.display_name}")
    state.console.print(f"[bold]Entry point:[/bold] {record.entry_point_name}")
    state.console.print(f"[bold]Version:[/bold] {record.version or '—'}")
    state.console.print(f"[bold]Description:[/bold] {record.description or '—'}")
    state.console.print(f"[bold]Source package:[/bold] {record.source_package or '—'}")

    style = _STATUS_STYLES.get(record.status, "")
    state.console.print(f"[bold]Status:[/bold] [{style}]{record.status}[/{style}]")

    if record.error_message:
        state.console.print(f"[bold]Error:[/bold] {record.error_message}")

    if record.commands:
        state.console.print(f"[bold]Commands:[/bold] {', '.join(record.commands)}")
