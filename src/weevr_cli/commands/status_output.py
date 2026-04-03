"""Rich and JSON output formatting for the status command."""

from __future__ import annotations

from typing import Any

from rich.console import Console

from weevr_cli.commands.status_models import StatusEntry, aggregate_non_weevr
from weevr_cli.deploy.models import DeployTarget

_STATUS_STYLES: dict[str, str] = {
    "+": "green",
    "~": "yellow",
    "=": "dim",
    "-": "red",
}


def print_status_header(target: DeployTarget, console: Console) -> None:
    """Print the target header for status output.

    Args:
        target: Resolved deploy target.
        console: Rich Console for output.
    """
    name = target.name or "unnamed"
    console.print(f"\n[bold]Target:[/bold] {name}")
    console.print(f"  Workspace: {target.workspace_id}")
    console.print(f"  Lakehouse: {target.lakehouse_id}")
    if target.path_prefix:
        console.print(f"  Path prefix: {target.path_prefix}")
    console.print()


def print_status_entries(entries: list[StatusEntry], console: Console) -> None:
    """Print colored diff symbols for status entries.

    Args:
        entries: Status entries to display.
        console: Rich Console for output.
    """
    for entry in entries:
        style = _STATUS_STYLES.get(entry.status, "")
        console.print(f"  [{style}]{entry.status}[/{style}] {entry.path}    ({entry.reason})")


def print_non_weevr_aggregate(counts: dict[str, int], console: Console) -> None:
    """Print aggregated counts for non-weevr files.

    Args:
        counts: Counts by status category.
        console: Rich Console for output.
    """
    parts: list[str] = []
    if counts["in_sync"]:
        parts.append(f"{counts['in_sync']} in sync")
    if counts["new"]:
        parts.append(f"{counts['new']} new")
    if counts["modified"]:
        parts.append(f"{counts['modified']} modified")
    if counts["remote_only"]:
        parts.append(f"{counts['remote_only']} remote only")
    if parts:
        console.print(f"\n  [dim]Other files: {', '.join(parts)}[/dim]")


def print_status_summary(entries: list[StatusEntry], console: Console) -> None:
    """Print a summary line with total counts.

    Args:
        entries: All status entries.
        console: Rich Console for output.
    """
    counts = {"new": 0, "modified": 0, "in_sync": 0, "remote_only": 0}
    for entry in entries:
        if entry.status == "+":
            counts["new"] += 1
        elif entry.status == "~":
            counts["modified"] += 1
        elif entry.status == "=":
            counts["in_sync"] += 1
        elif entry.status == "-":
            counts["remote_only"] += 1

    total = len(entries)
    parts = [f"{total} files"]
    if counts["new"]:
        parts.append(f"[green]{counts['new']} new[/green]")
    if counts["modified"]:
        parts.append(f"[yellow]{counts['modified']} modified[/yellow]")
    if counts["in_sync"]:
        parts.append(f"[dim]{counts['in_sync']} in sync[/dim]")
    if counts["remote_only"]:
        parts.append(f"[red]{counts['remote_only']} remote only[/red]")

    console.print(f"\n  Summary: {', '.join(parts)}")


def format_status_json(
    entries: list[StatusEntry],
    target: DeployTarget,
    verbose: bool,
) -> dict[str, Any]:
    """Build JSON output for status command.

    Args:
        entries: All status entries.
        target: Resolved deploy target.
        verbose: Whether verbose mode is active.

    Returns:
        Dict matching the status JSON contract.
    """
    in_sync = all(e.status == "=" for e in entries)

    # Count summary
    summary: dict[str, int] = {"new": 0, "modified": 0, "in_sync": 0, "remote_only": 0}
    for entry in entries:
        if entry.status == "+":
            summary["new"] += 1
        elif entry.status == "~":
            summary["modified"] += 1
        elif entry.status == "=":
            summary["in_sync"] += 1
        elif entry.status == "-":
            summary["remote_only"] += 1
    summary["total"] = len(entries)

    target_info: dict[str, str] = {"workspace_id": target.workspace_id}
    if target.name:
        target_info["name"] = target.name

    result: dict[str, Any] = {
        "target": target_info,
        "in_sync": in_sync,
    }

    if verbose:
        result["files"] = [
            {
                "path": e.path,
                "status": e.status,
                "reason": e.reason,
                "is_weevr": e.is_weevr,
            }
            for e in entries
        ]
    else:
        weevr_entries = [e for e in entries if e.is_weevr]
        non_weevr_entries = [e for e in entries if not e.is_weevr]
        result["weevr_files"] = [
            {"path": e.path, "status": e.status, "reason": e.reason} for e in weevr_entries
        ]
        result["other_files"] = aggregate_non_weevr(non_weevr_entries)

    result["summary"] = summary
    return result
