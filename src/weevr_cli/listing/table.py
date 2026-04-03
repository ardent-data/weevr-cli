"""Table view renderer for the dependency graph."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table

from weevr_cli.listing.models import DependencyGraph, GraphNode

_TYPE_PRIORITY = {"loom": 0, "weave": 1, "thread": 2}


def _sort_key(node: GraphNode) -> tuple[int, str]:
    return (_TYPE_PRIORITY.get(node.file_type, 99), node.path)


def render_table(graph: DependencyGraph, console: Console) -> None:
    """Render a dependency graph as a Rich Table.

    Columns: File, Type, In, Out, Status.
    Sorted by type priority (loom > weave > thread), then path.

    Args:
        graph: The dependency graph to render.
        console: Rich Console for output.
    """
    table = Table(title="Project Files")
    table.add_column("File", style="bold")
    table.add_column("Type")
    table.add_column("In", justify="right")
    table.add_column("Out", justify="right")
    table.add_column("Status")

    for node in sorted(graph.nodes.values(), key=_sort_key):
        status_style = "[dim italic]orphan[/dim italic]" if node.is_orphan else "connected"
        table.add_row(
            node.path,
            node.file_type,
            str(len(node.refs_in)),
            str(len(node.refs_out)),
            status_style,
        )

    console.print(table)


def render_table_json(graph: DependencyGraph) -> dict[str, Any]:
    """Build a JSON-serializable table representation of the dependency graph.

    Returns:
        Dict matching the list JSON (table) contract.
    """
    files: list[dict[str, Any]] = []
    orphan_count = 0

    for node in sorted(graph.nodes.values(), key=_sort_key):
        status = "orphan" if node.is_orphan else "connected"
        if node.is_orphan:
            orphan_count += 1
        files.append(
            {
                "path": node.path,
                "type": node.file_type,
                "refs_in": len(node.refs_in),
                "refs_out": len(node.refs_out),
                "status": status,
            }
        )

    return {
        "format": "table",
        "files": files,
        "total_files": len(files),
        "orphan_count": orphan_count,
    }
