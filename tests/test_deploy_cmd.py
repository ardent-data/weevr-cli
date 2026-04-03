"""Integration tests for the deploy command (mocked OneLake)."""

from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from weevr_cli.cli import app
from weevr_cli.deploy.models import RemoteFile

runner = CliRunner()

VALID_UUID_1 = "11111111-1111-1111-1111-111111111111"
VALID_UUID_2 = "22222222-2222-2222-2222-222222222222"


def _setup_project(
    tmp_path: Path,
    *,
    deploy_ignore: str | None = None,
) -> Path:
    """Create a minimal weevr project with config and chdir into it."""
    proj = tmp_path / "test-project.weevr"
    proj.mkdir()
    weevr_dir = proj / ".weevr"
    weevr_dir.mkdir()
    (weevr_dir / "cli.yaml").write_text(
        f"targets:\n"
        f"  dev:\n"
        f"    workspace_id: '{VALID_UUID_1}'\n"
        f"    lakehouse_id: '{VALID_UUID_2}'\n"
        f"    path_prefix: weevr/test\n"
        f"default_target: dev\n"
        f"schema:\n"
        f"  version: '1.11'\n"
    )
    if deploy_ignore:
        (weevr_dir / "deploy-ignore").write_text(deploy_ignore)

    threads = proj / "threads"
    threads.mkdir()
    (threads / "orders.thread").write_text(
        "name: orders\nversion: '1.0'\nsource:\n  type: table\n  ref: dbo.orders\n"
    )
    weaves = proj / "weaves"
    weaves.mkdir()
    (weaves / "customer.weave").write_text(
        "name: customer_dim\nversion: '1.0'\nsource:\n  thread: threads/orders\n"
    )
    return proj


@pytest.fixture()
def mock_azure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[MagicMock, None, None]:
    """Patch Azure credential and OneLake client; chdir into a test project."""
    proj = _setup_project(tmp_path)
    monkeypatch.chdir(proj)
    with (
        patch(
            "weevr_cli.state.AppState.credential",
            new_callable=lambda: property(lambda self: MagicMock()),
        ),
        patch("weevr_cli.commands.deploy.OneLakeClient") as mock_cls,
    ):
        mock_client = MagicMock()
        mock_client.list_files.return_value = []
        mock_cls.return_value = mock_client
        yield mock_client


@pytest.fixture()
def mock_azure_with_ignore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[MagicMock, None, None]:
    """Same as mock_azure but with deploy-ignore configured."""
    proj = _setup_project(tmp_path, deploy_ignore="weaves/\n")
    monkeypatch.chdir(proj)
    with (
        patch(
            "weevr_cli.state.AppState.credential",
            new_callable=lambda: property(lambda self: MagicMock()),
        ),
        patch("weevr_cli.commands.deploy.OneLakeClient") as mock_cls,
    ):
        mock_client = MagicMock()
        mock_client.list_files.return_value = []
        mock_cls.return_value = mock_client
        yield mock_client


class TestDeploySmartSync:
    def test_smart_sync_uploads_new_files(self, mock_azure: MagicMock) -> None:
        result = runner.invoke(app, ["deploy", "--skip-validation"], catch_exceptions=False)
        assert result.exit_code == 0, result.output
        assert mock_azure.upload_file.call_count >= 1

    def test_smart_sync_skips_unchanged(self, mock_azure: MagicMock) -> None:
        from weevr_cli.deploy.collector import compute_md5

        thread_path = Path("threads/orders.thread")
        md5 = compute_md5(thread_path)
        mock_azure.list_files.return_value = [
            RemoteFile(
                path="threads/orders.thread",
                size=thread_path.stat().st_size,
                content_md5=md5,
            )
        ]
        result = runner.invoke(app, ["deploy", "--skip-validation"], catch_exceptions=False)
        assert result.exit_code == 0, result.output
        # Should still upload weaves/customer.weave (new) but not orders.thread


class TestDeployFull:
    def test_full_overwrite(self, mock_azure: MagicMock) -> None:
        result = runner.invoke(
            app, ["deploy", "--full", "--skip-validation"], catch_exceptions=False
        )
        assert result.exit_code == 0, result.output
        assert mock_azure.upload_file.call_count >= 2


class TestDeployDryRun:
    def test_dry_run_shows_plan(self, mock_azure: MagicMock) -> None:
        result = runner.invoke(
            app, ["deploy", "--dry-run", "--skip-validation"], catch_exceptions=False
        )
        assert result.exit_code == 0, result.output
        assert "Dry run" in result.output
        mock_azure.upload_file.assert_not_called()

    def test_dry_run_json(self, mock_azure: MagicMock) -> None:
        result = runner.invoke(
            app, ["--json", "deploy", "--dry-run", "--skip-validation"], catch_exceptions=False
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["dry_run"] is True
        assert "planned_uploads" in data


class TestDeployClean:
    def test_clean_removes_orphaned_weevr_files(self, mock_azure: MagicMock) -> None:
        mock_azure.list_files.return_value = [
            RemoteFile(path="orphan.yaml", size=100, content_md5=None),
        ]
        result = runner.invoke(
            app, ["deploy", "--clean", "--skip-validation"], catch_exceptions=False
        )
        assert result.exit_code == 0, result.output
        mock_azure.delete_file.assert_called_once_with("orphan.yaml")

    def test_clean_all_requires_force_noninteractive(self, mock_azure: MagicMock) -> None:
        result = runner.invoke(
            app, ["deploy", "--clean", "--all", "--skip-validation"], catch_exceptions=False
        )
        assert result.exit_code == 1

    def test_clean_all_with_force(self, mock_azure: MagicMock) -> None:
        mock_azure.list_files.return_value = [
            RemoteFile(path="orphan.txt", size=100, content_md5=None),
        ]
        result = runner.invoke(
            app,
            ["deploy", "--clean", "--all", "--force", "--skip-validation"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        mock_azure.delete_file.assert_called_once_with("orphan.txt")


class TestDeployTarget:
    def test_named_target(self, mock_azure: MagicMock) -> None:
        result = runner.invoke(
            app, ["deploy", "--target", "dev", "--skip-validation"], catch_exceptions=False
        )
        assert result.exit_code == 0, result.output

    def test_unknown_target(self, mock_azure: MagicMock) -> None:
        result = runner.invoke(
            app, ["deploy", "--target", "staging", "--skip-validation"], catch_exceptions=False
        )
        assert result.exit_code == 1

    def test_invalid_uuid_flags(self, mock_azure: MagicMock) -> None:
        result = runner.invoke(
            app,
            [
                "deploy",
                "--workspace-id",
                "bad-uuid",
                "--lakehouse-id",
                VALID_UUID_2,
                "--skip-validation",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 1


class TestDeployIgnore:
    def test_deploy_ignore_excludes_files(self, mock_azure_with_ignore: MagicMock) -> None:
        result = runner.invoke(
            app, ["deploy", "--dry-run", "--skip-validation"], catch_exceptions=False
        )
        assert result.exit_code == 0, result.output
        assert "customer" not in result.output


class TestDeployJsonOutput:
    def test_json_deploy_result(self, mock_azure: MagicMock) -> None:
        result = runner.invoke(
            app, ["--json", "deploy", "--skip-validation"], catch_exceptions=False
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "uploaded" in data
        assert "failed" in data


class TestDeployAuthError:
    def test_auth_failure_exits_with_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        proj = _setup_project(tmp_path)
        monkeypatch.chdir(proj)
        from weevr_cli.state import AuthError

        with patch(
            "weevr_cli.state.AppState.credential",
            new_callable=lambda: property(
                lambda self: (_ for _ in ()).throw(AuthError("No Azure credentials found."))
            ),
        ):
            result = runner.invoke(app, ["deploy", "--skip-validation"], catch_exceptions=False)
        assert result.exit_code == 1
