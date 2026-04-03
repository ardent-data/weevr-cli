"""Tests for plan executor."""

from pathlib import Path
from unittest.mock import MagicMock

from weevr_cli.deploy.executor import execute_plan
from weevr_cli.deploy.models import (
    ActionType,
    DeployAction,
    DeployPlan,
    DeployTarget,
)


def _target() -> DeployTarget:
    return DeployTarget(workspace_id="ws", lakehouse_id="lh")


class TestExecutePlan:
    def test_upload_success(self) -> None:
        client = MagicMock()
        action = DeployAction(Path("/a.yaml"), "a.yaml", ActionType.UPLOAD_NEW, "new")
        plan = DeployPlan(target=_target(), actions=[action])

        result = execute_plan(client, plan)

        assert result.is_success
        assert len(result.succeeded) == 1
        client.upload_file.assert_called_once_with(Path("/a.yaml"), "a.yaml")

    def test_delete_success(self) -> None:
        client = MagicMock()
        action = DeployAction(None, "old.yaml", ActionType.DELETE, "remote only")
        plan = DeployPlan(target=_target(), actions=[action])

        result = execute_plan(client, plan)

        assert result.is_success
        client.delete_file.assert_called_once_with("old.yaml")

    def test_skip_succeeds(self) -> None:
        client = MagicMock()
        action = DeployAction(Path("/a.yaml"), "a.yaml", ActionType.SKIP, "unchanged")
        plan = DeployPlan(target=_target(), actions=[action])

        result = execute_plan(client, plan)

        assert result.is_success
        client.upload_file.assert_not_called()
        client.delete_file.assert_not_called()

    def test_upload_failure_continues(self) -> None:
        client = MagicMock()
        client.upload_file.side_effect = [None, Exception("403 Forbidden")]

        actions = [
            DeployAction(Path("/a.yaml"), "a.yaml", ActionType.UPLOAD_NEW, "new"),
            DeployAction(Path("/b.yaml"), "b.yaml", ActionType.UPLOAD_NEW, "new"),
        ]
        plan = DeployPlan(target=_target(), actions=actions)

        result = execute_plan(client, plan)

        assert not result.is_success
        assert len(result.succeeded) == 1
        assert len(result.failed) == 1
        assert result.failed[0].error == "403 Forbidden"

    def test_delete_failure_continues(self) -> None:
        client = MagicMock()
        client.delete_file.side_effect = Exception("Network error")

        action = DeployAction(None, "file.yaml", ActionType.DELETE, "remote only")
        plan = DeployPlan(target=_target(), actions=[action])

        result = execute_plan(client, plan)

        assert not result.is_success
        assert result.failed[0].error == "Network error"

    def test_mixed_actions(self) -> None:
        client = MagicMock()
        actions = [
            DeployAction(Path("/a.yaml"), "a.yaml", ActionType.UPLOAD_NEW, "new"),
            DeployAction(Path("/b.yaml"), "b.yaml", ActionType.SKIP, "unchanged"),
            DeployAction(Path("/c.yaml"), "c.yaml", ActionType.UPLOAD_MODIFIED, "modified"),
            DeployAction(None, "d.yaml", ActionType.DELETE, "remote only"),
        ]
        plan = DeployPlan(target=_target(), actions=actions)

        result = execute_plan(client, plan)

        assert result.is_success
        assert len(result.results) == 4
        assert client.upload_file.call_count == 2
        assert client.delete_file.call_count == 1

    def test_empty_plan(self) -> None:
        client = MagicMock()
        plan = DeployPlan(target=_target())

        result = execute_plan(client, plan)

        assert result.is_success
        assert len(result.results) == 0
