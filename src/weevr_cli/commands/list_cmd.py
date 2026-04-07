"""Implementation of the weevr list command."""

from __future__ import annotations

from weevr_cli.config import find_project_root
from weevr_cli.ignore import (
    deploy_ignore_deprecation_message,
    has_deploy_ignore,
    load_combined_ignore,
)
from weevr_cli.listing.graph import build_dependency_graph
from weevr_cli.listing.table import render_table, render_table_json
from weevr_cli.listing.tree import render_tree, render_tree_json
from weevr_cli.output import print_error, print_json
from weevr_cli.state import AppState


def run_list(*, format: str, state: AppState) -> None:
    """Execute the list command.

    Args:
        format: Output format — "tree" or "table".
        state: Application state.

    Raises:
        SystemExit: On errors.
    """
    project_root = find_project_root()
    if project_root is None:
        print_error(
            "No weevr project found. Run 'weevr init' to create one.",
            "config_not_found",
            json_mode=state.json_mode,
            console=state.console,
        )
        raise SystemExit(1)

    if has_deploy_ignore(project_root) and not state.json_mode:
        state.console.print(f"[yellow]{deploy_ignore_deprecation_message()}[/yellow]")
    ignore_spec = load_combined_ignore(project_root, include_deploy=False)
    graph = build_dependency_graph(project_root, ignore_spec=ignore_spec)

    if len(graph.nodes) == 0:
        if state.json_mode:
            print_json({"error": "No weevr files found in project", "code": "no_files_found"})
        else:
            state.console.print("No weevr files found in project.")
        return

    if format == "tree":
        if state.json_mode:
            print_json(render_tree_json(graph))
        else:
            render_tree(graph, state.console)
    elif format == "table":
        if state.json_mode:
            print_json(render_table_json(graph))
        else:
            render_table(graph, state.console)
    else:
        print_error(
            f"Unknown format: {format}. Valid options are 'tree' or 'table'.",
            "invalid_format",
            json_mode=state.json_mode,
            console=state.console,
        )
        raise SystemExit(1)
