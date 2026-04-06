"""Tests for deploy target resolution."""

from pathlib import Path

import pytest

from weevr_cli.config import TargetConfig, WeevrConfig
from weevr_cli.deploy.target import (
    TargetError,
    resolve_deploy_context,
    resolve_target,
    validate_uuid,
)

VALID_UUID = "12345678-1234-1234-1234-123456789abc"
VALID_UUID_2 = "abcdef01-2345-6789-abcd-ef0123456789"


def _config(
    targets: dict[str, TargetConfig] | None = None,
    default_target: str | None = "dev",
) -> WeevrConfig:
    if targets is None:
        targets = {
            "dev": TargetConfig(
                workspace_id=VALID_UUID,
                lakehouse_id=VALID_UUID_2,
                path_prefix="weevr/project",
            ),
            "prod": TargetConfig(
                workspace_id=VALID_UUID_2,
                lakehouse_id=VALID_UUID,
            ),
        }
    return WeevrConfig(targets=targets, default_target=default_target)


class TestValidateUuid:
    def test_valid_uuid(self) -> None:
        validate_uuid(VALID_UUID, "test_field")

    def test_valid_uuid_uppercase(self) -> None:
        validate_uuid(VALID_UUID.upper(), "test_field")

    def test_invalid_uuid(self) -> None:
        with pytest.raises(TargetError, match="not a valid UUID"):
            validate_uuid("not-a-uuid", "workspace_id")

    def test_invalid_uuid_code(self) -> None:
        with pytest.raises(TargetError) as exc_info:
            validate_uuid("bad", "workspace_id")
        assert exc_info.value.code == "invalid_uuid"


class TestResolveTarget:
    def test_cli_flags_override(self) -> None:
        config = _config()
        target = resolve_target(
            config,
            workspace_id=VALID_UUID,
            lakehouse_id=VALID_UUID_2,
            path_prefix="custom/path",
        )
        assert target.workspace_id == VALID_UUID
        assert target.lakehouse_id == VALID_UUID_2
        assert target.path_prefix == "custom/path"
        assert target.name is None

    def test_cli_flags_invalid_uuid(self) -> None:
        config = _config()
        with pytest.raises(TargetError, match="not a valid UUID"):
            resolve_target(config, workspace_id="bad", lakehouse_id=VALID_UUID)

    def test_incomplete_cli_flags(self) -> None:
        config = _config()
        with pytest.raises(TargetError, match="Both --workspace-id and --lakehouse-id"):
            resolve_target(config, workspace_id=VALID_UUID)

    def test_named_target(self) -> None:
        config = _config()
        target = resolve_target(config, target_name="dev")
        assert target.workspace_id == VALID_UUID
        assert target.lakehouse_id == VALID_UUID_2
        assert target.path_prefix == "weevr/project"
        assert target.name == "dev"

    def test_named_target_not_found(self) -> None:
        config = _config()
        with pytest.raises(TargetError, match="Unknown target: staging"):
            resolve_target(config, target_name="staging")

    def test_default_target(self) -> None:
        config = _config()
        target = resolve_target(config)
        assert target.name == "dev"
        assert target.workspace_id == VALID_UUID

    def test_no_default_target(self) -> None:
        config = _config(default_target=None)
        with pytest.raises(TargetError, match="No target specified"):
            resolve_target(config)

    def test_path_prefix_override_on_named_target(self) -> None:
        config = _config()
        target = resolve_target(config, target_name="dev", path_prefix="override/path")
        assert target.path_prefix == "override/path"

    def test_named_target_without_prefix(self) -> None:
        config = _config()
        target = resolve_target(config, target_name="prod")
        assert target.path_prefix is None


class TestResolveDeployContext:
    def test_sets_project_folder_from_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        proj = tmp_path / "datalake.weevr"
        proj.mkdir()
        weevr_dir = proj / ".weevr"
        weevr_dir.mkdir()
        (weevr_dir / "cli.yaml").write_text(
            f"targets:\n  dev:\n    workspace_id: '{VALID_UUID}'\n"
            f"    lakehouse_id: '{VALID_UUID_2}'\n"
        )
        monkeypatch.chdir(proj)
        config = _config()
        ctx = resolve_deploy_context(config)
        assert ctx.target.project_folder == "datalake.weevr"
        assert ctx.project_root == proj
        assert "datalake.weevr" in ctx.target.base_directory

    def test_raises_when_no_project_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        config = _config()
        with pytest.raises(TargetError, match="No weevr project found"):
            resolve_deploy_context(config)
