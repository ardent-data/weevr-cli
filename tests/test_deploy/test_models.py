"""Tests for deploy data models."""

from pathlib import Path

import pytest

from weevr_cli.deploy.models import (
    ActionResult,
    ActionType,
    DeployAction,
    DeployPlan,
    DeployResult,
    DeployTarget,
    RemoteFile,
)


class TestDeployTarget:
    def test_onelake_account_url(self) -> None:
        target = DeployTarget(workspace_id="ws-id", lakehouse_id="lh-id")
        assert target.onelake_account_url == "https://onelake.dfs.fabric.microsoft.com"

    def test_filesystem_name(self) -> None:
        target = DeployTarget(workspace_id="ws-id", lakehouse_id="lh-id")
        assert target.filesystem_name == "ws-id"

    def test_base_directory_without_prefix(self) -> None:
        target = DeployTarget(workspace_id="ws-id", lakehouse_id="lh-id")
        assert target.base_directory == "lh-id.Lakehouse/Files"

    def test_base_directory_with_prefix(self) -> None:
        target = DeployTarget(
            workspace_id="ws-id", lakehouse_id="lh-id", path_prefix="weevr/project"
        )
        assert target.base_directory == "lh-id.Lakehouse/Files/weevr/project"

    def test_base_directory_with_project_folder(self) -> None:
        target = DeployTarget(
            workspace_id="ws-id", lakehouse_id="lh-id", project_folder="datalake.weevr"
        )
        assert target.base_directory == "lh-id.Lakehouse/Files/datalake.weevr"

    def test_base_directory_with_prefix_and_project_folder(self) -> None:
        target = DeployTarget(
            workspace_id="ws-id",
            lakehouse_id="lh-id",
            path_prefix="custom/path",
            project_folder="datalake.weevr",
        )
        assert target.base_directory == "lh-id.Lakehouse/Files/custom/path/datalake.weevr"

    def test_project_folder_rejects_path_separators(self) -> None:
        with pytest.raises(ValueError, match="single path component"):
            DeployTarget(workspace_id="ws-id", lakehouse_id="lh-id", project_folder="bad/path")
        with pytest.raises(ValueError, match="single path component"):
            DeployTarget(workspace_id="ws-id", lakehouse_id="lh-id", project_folder="bad\\path")

    def test_name_optional(self) -> None:
        target = DeployTarget(workspace_id="ws-id", lakehouse_id="lh-id", name="dev")
        assert target.name == "dev"


class TestRemoteFile:
    def test_creation(self) -> None:
        rf = RemoteFile(path="threads/orders.yaml", size=1024, content_md5=b"\x00" * 16)
        assert rf.path == "threads/orders.yaml"
        assert rf.size == 1024
        assert rf.content_md5 == b"\x00" * 16

    def test_content_md5_optional(self) -> None:
        rf = RemoteFile(path="test.yaml", size=0)
        assert rf.content_md5 is None


class TestDeployAction:
    def test_is_upload_new(self) -> None:
        action = DeployAction(
            local_path=Path("test.yaml"),
            remote_path="test.yaml",
            action=ActionType.UPLOAD_NEW,
            reason="new",
        )
        assert action.is_upload is True

    def test_is_upload_modified(self) -> None:
        action = DeployAction(
            local_path=Path("test.yaml"),
            remote_path="test.yaml",
            action=ActionType.UPLOAD_MODIFIED,
            reason="modified",
        )
        assert action.is_upload is True

    def test_is_upload_forced(self) -> None:
        action = DeployAction(
            local_path=Path("test.yaml"),
            remote_path="test.yaml",
            action=ActionType.UPLOAD_FORCED,
            reason="forced",
        )
        assert action.is_upload is True

    def test_skip_is_not_upload(self) -> None:
        action = DeployAction(
            local_path=Path("test.yaml"),
            remote_path="test.yaml",
            action=ActionType.SKIP,
            reason="unchanged",
        )
        assert action.is_upload is False

    def test_delete_is_not_upload(self) -> None:
        action = DeployAction(
            local_path=None,
            remote_path="test.yaml",
            action=ActionType.DELETE,
            reason="remote only",
        )
        assert action.is_upload is False


class TestDeployPlan:
    def _make_plan(self) -> DeployPlan:
        target = DeployTarget(workspace_id="ws", lakehouse_id="lh")
        return DeployPlan(
            target=target,
            actions=[
                DeployAction(Path("a.yaml"), "a.yaml", ActionType.UPLOAD_NEW, "new"),
                DeployAction(Path("b.yaml"), "b.yaml", ActionType.UPLOAD_MODIFIED, "modified"),
                DeployAction(Path("c.yaml"), "c.yaml", ActionType.SKIP, "unchanged"),
                DeployAction(None, "d.yaml", ActionType.DELETE, "remote only"),
            ],
        )

    def test_uploads(self) -> None:
        plan = self._make_plan()
        assert len(plan.uploads) == 2

    def test_deletes(self) -> None:
        plan = self._make_plan()
        assert len(plan.deletes) == 1

    def test_skips(self) -> None:
        plan = self._make_plan()
        assert len(plan.skips) == 1

    def test_empty_plan(self) -> None:
        target = DeployTarget(workspace_id="ws", lakehouse_id="lh")
        plan = DeployPlan(target=target)
        assert plan.uploads == []
        assert plan.deletes == []
        assert plan.skips == []


class TestDeployResult:
    def test_all_success(self) -> None:
        action = DeployAction(Path("a.yaml"), "a.yaml", ActionType.UPLOAD_NEW, "new")
        result = DeployResult(results=[ActionResult(action=action, success=True)])
        assert result.is_success is True
        assert len(result.succeeded) == 1
        assert len(result.failed) == 0

    def test_partial_failure(self) -> None:
        a1 = DeployAction(Path("a.yaml"), "a.yaml", ActionType.UPLOAD_NEW, "new")
        a2 = DeployAction(Path("b.yaml"), "b.yaml", ActionType.UPLOAD_NEW, "new")
        result = DeployResult(
            results=[
                ActionResult(action=a1, success=True),
                ActionResult(action=a2, success=False, error="403 Forbidden"),
            ]
        )
        assert result.is_success is False
        assert len(result.succeeded) == 1
        assert len(result.failed) == 1
        assert result.failed[0].error == "403 Forbidden"

    def test_empty_result(self) -> None:
        result = DeployResult()
        assert result.is_success is True
