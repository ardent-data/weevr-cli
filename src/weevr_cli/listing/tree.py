"""Tree view renderer for the dependency graph."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.tree import Tree

from weevr_cli.listing.models import DependencyGraph, GraphNode


def render_tree(graph: DependencyGraph, console: Console) -> None:
    """Render a dependency graph as a Rich Tree.

    Shows loom → weave/warp → thread dependency chains with an
    "Unreferenced" section for orphaned files.

    Args:
        graph: The dependency graph to render.
        console: Rich Console for output.
    """
    tree = Tree("[bold]Project Structure[/bold]")

    for loom in graph.looms:
        loom_branch = tree.add(f"[bold cyan]{loom.path}[/bold cyan]")
        _add_children(graph, loom, loom_branch)

    orphans = graph.orphans
    if orphans:
        orphan_branch = tree.add("[bold yellow]Unreferenced[/bold yellow]")
        for orphan in orphans:
            orphan_branch.add(f"{orphan.path} [dim](orphan)[/dim]")

    console.print(tree)


def _add_children(graph: DependencyGraph, node: GraphNode, branch: Tree) -> None:
    """Recursively add child references to a tree branch."""
    for ref_path in node.refs_out:
        child_node = graph.nodes.get(ref_path)
        if child_node is None:
            branch.add(f"[dim]{ref_path} (not found)[/dim]")
        else:
            style = (
                "green"
                if child_node.file_type == "thread"
                else "magenta"
                if child_node.file_type == "warp"
                else "blue"
            )
            child_branch = branch.add(f"[{style}]{child_node.path}[/{style}]")
            _add_children(graph, child_node, child_branch)


def render_tree_json(graph: DependencyGraph) -> dict[str, Any]:
    """Build a JSON-serializable tree representation of the dependency graph.

    Returns:
        Dict matching the list JSON (tree) contract.
    """
    roots: list[dict[str, Any]] = []
    for loom in graph.looms:
        roots.append(_node_to_dict(graph, loom))

    unreferenced: list[dict[str, str]] = [
        {"path": orphan.path, "type": orphan.file_type} for orphan in graph.orphans
    ]

    return {
        "format": "tree",
        "roots": roots,
        "unreferenced": unreferenced,
        "total_files": len(graph.nodes),
        "orphan_count": len(unreferenced),
    }


def _node_to_dict(graph: DependencyGraph, node: GraphNode) -> dict[str, Any]:
    """Recursively convert a node and its children to a dict."""
    children: list[dict[str, Any]] = []
    for ref_path in node.refs_out:
        child_node = graph.nodes.get(ref_path)
        if child_node is not None:
            children.append(_node_to_dict(graph, child_node))
    return {
        "path": node.path,
        "type": node.file_type,
        "children": children,
    }
