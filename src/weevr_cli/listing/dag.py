"""Execution plan (DAG) view for weaves.

Plans come from weevr-core's planner, the same one the engine uses, so the
groups shown here are the order threads will actually run in.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.tree import Tree
from weevr.engine.planner import ExecutionPlan
from weevr.errors import WeevError

from weevr_cli.listing.models import DependencyGraph
from weevr_cli.validation.resolved import load_resolved


class DagError(Exception):
    """A weave could not be loaded or planned."""


@dataclass
class WeavePlan:
    """One weave's execution plan.

    Attributes:
        file: The weave file, or the loom file for a weave defined inline.
        weave: The weave name.
        plan: The planner's result.
    """

    file: str
    weave: str
    plan: ExecutionPlan


def _plans_for(project_root: Path, rel: str) -> tuple[list[ExecutionPlan], dict[str, str]]:
    """Load one weave or loom and plan it.

    Returns:
        The plans, and each loom weave's file keyed by weave name (weaves
        defined inline in the loom are absent).
    """
    try:
        loaded = load_resolved(project_root / rel, project_root=project_root)
        plans = loaded.execution_plan or []
    except WeevError as exc:
        raise DagError(f"{rel}: {exc}") from exc
    weave_files = {
        name: weave.qualified_key
        for name, weave in loaded.resolved_weaves.items()
        if (project_root / weave.qualified_key).is_file()
    }
    return plans, weave_files


def build_weave_plans(project_root: Path, graph: DependencyGraph) -> list[WeavePlan]:
    """Build the execution plan of every weave in the project.

    Each weave file is planned on its own. Looms are planned too, to pick up
    weaves they define inline; a loom weave that lives in its own file is
    shown once, under that file.

    Raises:
        DagError: If any weave or loom fails to load or plan.
    """
    nodes = sorted(graph.nodes.values(), key=lambda n: n.path)
    result: list[WeavePlan] = []

    for node in nodes:
        if node.file_type == "weave":
            plans, _ = _plans_for(project_root, node.path)
            result.extend(WeavePlan(node.path, plan.weave_name, plan) for plan in plans)

    shown = {wp.file for wp in result}
    for node in nodes:
        if node.file_type == "loom":
            plans, weave_files = _plans_for(project_root, node.path)
            for plan in plans:
                if weave_files.get(plan.weave_name) not in shown:
                    result.append(WeavePlan(node.path, plan.weave_name, plan))

    return result


def _dependencies(plan: ExecutionPlan) -> dict[str, list[dict[str, str]]]:
    explicit = plan.explicit_dependencies
    return {
        thread: [
            {"thread": dep, "kind": "explicit" if dep in explicit.get(thread, []) else "inferred"}
            for dep in deps
        ]
        for thread, deps in plan.dependencies.items()
    }


def _lookup_label(index: int) -> str:
    return "before group 1" if index == 0 else f"after group {index}"


def render_dag(plans: list[WeavePlan], console: Console) -> None:
    """Render each weave's parallel groups as a Rich tree."""
    root = Tree("[bold]Execution Plans[/bold]")
    for wp in plans:
        plan = wp.plan
        deps = _dependencies(plan)
        branch = root.add(f"[bold cyan]{wp.file}[/bold cyan] [dim](weave {wp.weave})[/dim]")
        for index, group in enumerate(plan.execution_order, start=1):
            group_branch = branch.add(f"[bold]Group {index}[/bold]")
            for thread in group:
                label = f"[green]{thread}[/green]"
                upstream = ", ".join(f"{d['thread']} ({d['kind']})" for d in deps.get(thread, []))
                if upstream:
                    label += f" ← {upstream}"
                if thread in plan.cache_targets:
                    label += " [dim](cached)[/dim]"
                group_branch.add(label)
        if plan.lookup_schedule:
            lookup_branch = branch.add("[bold]Lookups[/bold]")
            for index, names in sorted(plan.lookup_schedule.items()):
                lookup_branch.add(f"{_lookup_label(index)}: {', '.join(names)}")
    console.print(root)


def render_dag_json(plans: list[WeavePlan]) -> dict[str, Any]:
    """Build the JSON form of the execution plans."""
    return {
        "weaves": [
            {
                "weave": wp.weave,
                "file": wp.file,
                "execution_order": wp.plan.execution_order,
                "dependencies": _dependencies(wp.plan),
                "cache_targets": wp.plan.cache_targets,
                "lookup_schedule": (
                    {str(k): v for k, v in wp.plan.lookup_schedule.items()}
                    if wp.plan.lookup_schedule is not None
                    else None
                ),
            }
            for wp in plans
        ]
    }
