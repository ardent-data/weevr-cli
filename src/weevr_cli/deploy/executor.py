"""Plan executor — runs deploy actions against OneLake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from weevr_cli.deploy.models import ActionResult, ActionType, DeployPlan, DeployResult

if TYPE_CHECKING:
    from weevr_cli.deploy.onelake import OneLakeClient


def execute_plan(client: OneLakeClient, plan: DeployPlan) -> DeployResult:
    """Execute a deploy plan, uploading, skipping, and deleting as specified.

    Continues on per-file errors so partial failures are reported.

    Args:
        client: OneLake client for remote operations.
        plan: Deploy plan to execute.

    Returns:
        DeployResult with per-action outcomes.
    """
    results: list[ActionResult] = []

    for action in plan.actions:
        if action.action == ActionType.SKIP:
            results.append(ActionResult(action=action, success=True))
            continue

        if action.is_upload:
            assert action.local_path is not None
            try:
                client.upload_file(action.local_path, action.remote_path)
                results.append(ActionResult(action=action, success=True))
            except Exception as exc:
                results.append(ActionResult(action=action, success=False, error=str(exc)))

        elif action.action == ActionType.DELETE:
            try:
                client.delete_file(action.remote_path)
                results.append(ActionResult(action=action, success=True))
            except Exception as exc:
                results.append(ActionResult(action=action, success=False, error=str(exc)))

    return DeployResult(results=results)
