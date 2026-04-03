"""Rich and JSON output formatting for deploy results."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table

from weevr_cli.deploy.models import (
    ActionType,
    DeployPlan,
    DeployResult,
    DeployTarget,
)
from weevr_cli.output import print_json

_ACTION_LABELS = {
    ActionType.UPLOAD_NEW: ("upload", "green"),
    ActionType.UPLOAD_MODIFIED: ("upload", "yellow"),
    ActionType.UPLOAD_FORCED: ("upload", "yellow"),
    ActionType.SKIP: ("skip", "dim"),
    ActionType.DELETE: ("delete", "red"),
}


def render_target_header(target: DeployTarget, console: Console) -> None:
    """Display the deploy target header."""
    label = target.name or "custom"
    prefix = target.path_prefix or "(root)"
    console.print(
        f"\n[bold]Deploy target:[/bold] {label}"
        f"  workspace={target.workspace_id}"
        f"  lakehouse={target.lakehouse_id}"
        f"  path={prefix}"
    )


def render_dry_run(plan: DeployPlan, *, json_mode: bool, console: Console) -> None:
    """Display a dry-run action table."""
    if json_mode:
        print_json(_dry_run_json(plan))
        return

    console.print("\n[bold]Dry run — no changes will be made[/bold]\n")

    if not plan.actions:
        console.print("Nothing to do — local and remote are in sync.")
        return

    table = Table(show_header=True)
    table.add_column("Action", width=8)
    table.add_column("File")
    table.add_column("Reason", style="dim")

    for action in plan.actions:
        label, style = _ACTION_LABELS.get(action.action, ("unknown", ""))
        table.add_row(f"[{style}]{label}[/{style}]", action.remote_path, action.reason)

    console.print(table)
    console.print(
        f"\nPlanned: {len(plan.uploads)} uploads, "
        f"{len(plan.skips)} skips, "
        f"{len(plan.deletes)} deletes"
    )


def render_result(
    result: DeployResult,
    target: DeployTarget,
    *,
    json_mode: bool,
    console: Console,
) -> None:
    """Display deploy execution results."""
    if json_mode:
        print_json(_result_json(result, target))
        return

    if not result.results:
        console.print("Nothing to deploy — local and remote are in sync.")
        return

    # Show failures
    for r in result.failed:
        console.print(f"  [red]FAILED[/red] {r.action.remote_path}: {r.error}")

    # Summary
    uploaded = sum(1 for r in result.succeeded if r.action.is_upload)
    skipped = sum(1 for r in result.succeeded if r.action.action == ActionType.SKIP)
    deleted = sum(1 for r in result.succeeded if r.action.action == ActionType.DELETE)
    failed = len(result.failed)

    console.print(
        f"\n[bold]Deploy complete:[/bold] "
        f"[green]{uploaded} uploaded[/green], "
        f"{skipped} skipped, "
        f"[red]{deleted} deleted[/red], "
        f"{'[red]' if failed else ''}{failed} failed{'[/red]' if failed else ''}"
    )


def _dry_run_json(plan: DeployPlan) -> dict[str, Any]:
    """Build JSON output for dry-run."""
    target_info = _target_json(plan.target)
    actions = []
    for a in plan.actions:
        label, _ = _ACTION_LABELS.get(a.action, ("unknown", ""))
        actions.append(
            {
                "file": a.remote_path,
                "action": label,
                "reason": a.reason,
            }
        )
    return {
        "target": target_info,
        "dry_run": True,
        "planned_uploads": len(plan.uploads),
        "planned_skips": len(plan.skips),
        "planned_deletes": len(plan.deletes),
        "actions": actions,
    }


def _result_json(result: DeployResult, target: DeployTarget) -> dict[str, Any]:
    """Build JSON output for deploy results."""
    target_info = _target_json(target)
    actions = []
    for r in result.results:
        label, _ = _ACTION_LABELS.get(r.action.action, ("unknown", ""))
        entry: dict[str, Any] = {
            "file": r.action.remote_path,
            "action": label,
            "reason": r.action.reason,
            "status": "success" if r.success else "failed",
        }
        if r.error:
            entry["error"] = r.error
        actions.append(entry)

    uploaded = sum(1 for r in result.succeeded if r.action.is_upload)
    skipped = sum(1 for r in result.succeeded if r.action.action == ActionType.SKIP)
    deleted = sum(1 for r in result.succeeded if r.action.action == ActionType.DELETE)

    return {
        "target": target_info,
        "uploaded": uploaded,
        "skipped": skipped,
        "deleted": deleted,
        "failed": len(result.failed),
        "actions": actions,
    }


def _target_json(target: DeployTarget) -> dict[str, Any]:
    """Build JSON target info."""
    info: dict[str, Any] = {
        "workspace_id": target.workspace_id,
        "lakehouse_id": target.lakehouse_id,
    }
    if target.name:
        info["name"] = target.name
    if target.path_prefix:
        info["path_prefix"] = target.path_prefix
    return info
