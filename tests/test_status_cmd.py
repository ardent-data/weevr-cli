"""Integration tests for the weevr status command (mocked OneLake)."""

from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from weevr_cli.cli import app
from weevr_cli.deploy.collector import compute_md5
from weevr_cli.deploy.models import RemoteFile

runner = CliRunner()

VALID_UUID_1 = "11111111-1111-1111-1111-111111111111"
VALID_UUID_2 = "22222222-2222-2222-2222-222222222222"


def _setup_project(tmp_path: Path) -> Path:
    """Create a minimal weevr project with config."""
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
    )

    threads = proj / "threads"
    threads.mkdir()
    (threads / "orders.thread").write_text("name: orders\nversion: '1.0'\nsource:\n  type: table\n")
    weaves = proj / "weaves"
    weaves.mkdir()
    (weaves / "customer.weave").write_text("name: customer_dim\nversion: '1.0'\n")
    # A non-weevr file
    (proj / "data.csv").write_text("id,name\n1,test\n")
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
        patch("weevr_cli.commands.status.OneLakeClient") as mock_cls,
    ):
        mock_client = MagicMock()
        mock_client.list_files.return_value = []
        mock_cls.return_value = mock_client
        yield mock_client


class TestStatusProjectFolder:
    def test_project_folder_in_target(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """OneLakeClient receives a target with project_folder set."""
        proj = _setup_project(tmp_path)
        monkeypatch.chdir(proj)
        with (
            patch(
                "weevr_cli.state.AppState.credential",
                new_callable=lambda: property(lambda self: MagicMock()),
            ),
            patch("weevr_cli.commands.status.OneLakeClient") as mock_cls,
        ):
            mock_client = MagicMock()
            mock_client.list_files.return_value = []
            mock_cls.return_value = mock_client
            result = runner.invoke(app, ["status"], catch_exceptions=False)
            assert result.exit_code == 0, result.output
            target_arg = mock_cls.call_args[0][0]
            assert target_arg.project_folder == "test-project.weevr"
            assert "test-project.weevr" in target_arg.base_directory


class TestStatusDiffSymbols:
    """EC-001: Colored diff symbols for each status."""

    def test_new_file_shows_plus(self, mock_azure: MagicMock) -> None:
        """Local-only file → + symbol."""
        mock_azure.list_files.return_value = []
        result = runner.invoke(app, ["status"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "+" in result.output
        assert "new, not deployed" in result.output

    def test_modified_file_shows_tilde(self, mock_azure: MagicMock) -> None:
        """Hash mismatch → ~ symbol."""
        mock_azure.list_files.return_value = [
            RemoteFile(path="threads/orders.thread", size=100, content_md5=b"\x00" * 16),
        ]
        result = runner.invoke(app, ["status"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "~" in result.output
        assert "modified locally" in result.output

    def test_in_sync_shows_equals(self, mock_azure: MagicMock) -> None:
        """Hash match → = symbol."""
        md5 = compute_md5(Path("threads/orders.thread"))
        mock_azure.list_files.return_value = [
            RemoteFile(
                path="threads/orders.thread",
                size=Path("threads/orders.thread").stat().st_size,
                content_md5=md5,
            ),
        ]
        result = runner.invoke(app, ["status"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "=" in result.output
        assert "in sync" in result.output

    def test_remote_only_shows_minus(self, mock_azure: MagicMock) -> None:
        """Remote-only file → - symbol."""
        mock_azure.list_files.return_value = [
            RemoteFile(path="threads/old.thread", size=50, content_md5=None),
        ]
        result = runner.invoke(app, ["status"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "-" in result.output
        assert "remote only" in result.output


class TestStatusTieredOutput:
    """EC-002, EC-003: Non-weevr aggregation and verbose."""

    def test_non_weevr_aggregated(self, mock_azure: MagicMock) -> None:
        """EC-002: Non-weevr files shown as aggregate counts."""
        mock_azure.list_files.return_value = []
        result = runner.invoke(app, ["status"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Other files" in result.output

    def test_verbose_shows_non_weevr(self, mock_azure: MagicMock) -> None:
        """EC-003: --verbose shows full non-weevr file listing."""
        mock_azure.list_files.return_value = []
        result = runner.invoke(app, ["status", "--verbose"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "data.csv" in result.output


class TestStatusTargetResolution:
    """EC-004: Target resolution with override flags."""

    def test_default_target(self, mock_azure: MagicMock) -> None:
        result = runner.invoke(app, ["status"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "dev" in result.output

    def test_named_target(self, mock_azure: MagicMock) -> None:
        result = runner.invoke(app, ["status", "--target", "dev"], catch_exceptions=False)
        assert result.exit_code == 0

    def test_cli_override_flags(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        proj = _setup_project(tmp_path)
        monkeypatch.chdir(proj)
        with (
            patch(
                "weevr_cli.state.AppState.credential",
                new_callable=lambda: property(lambda self: MagicMock()),
            ),
            patch("weevr_cli.commands.status.OneLakeClient") as mock_cls,
        ):
            mock_client = MagicMock()
            mock_client.list_files.return_value = []
            mock_cls.return_value = mock_client
            result = runner.invoke(
                app,
                [
                    "status",
                    "--workspace-id",
                    VALID_UUID_1,
                    "--lakehouse-id",
                    VALID_UUID_2,
                ],
                catch_exceptions=False,
            )
        assert result.exit_code == 0


class TestStatusExitCode:
    """EC-005: --exit-code flag."""

    def test_exit_0_when_in_sync(self, mock_azure: MagicMock) -> None:
        """All files in sync → exit 0."""
        md5_thread = compute_md5(Path("threads/orders.thread"))
        md5_weave = compute_md5(Path("weaves/customer.weave"))
        md5_csv = compute_md5(Path("data.csv"))
        mock_azure.list_files.return_value = [
            RemoteFile(
                "threads/orders.thread", Path("threads/orders.thread").stat().st_size, md5_thread
            ),
            RemoteFile(
                "weaves/customer.weave", Path("weaves/customer.weave").stat().st_size, md5_weave
            ),
            RemoteFile("data.csv", Path("data.csv").stat().st_size, md5_csv),
        ]
        result = runner.invoke(app, ["status", "--exit-code"], catch_exceptions=False)
        assert result.exit_code == 0

    def test_exit_1_when_differences(self, mock_azure: MagicMock) -> None:
        """Differences exist → exit 1."""
        mock_azure.list_files.return_value = []
        result = runner.invoke(app, ["status", "--exit-code"], catch_exceptions=False)
        assert result.exit_code == 1


class TestStatusEmptyRemote:
    """EC-006: Empty remote shows all as +."""

    def test_all_files_new(self, mock_azure: MagicMock) -> None:
        mock_azure.list_files.return_value = []
        result = runner.invoke(app, ["--json", "status"], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        weevr_files = data["weevr_files"]
        assert all(f["status"] == "+" for f in weevr_files)


class TestStatusJsonOutput:
    """EC-012: JSON output matches contract."""

    def test_json_default(self, mock_azure: MagicMock) -> None:
        mock_azure.list_files.return_value = []
        result = runner.invoke(app, ["--json", "status"], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "target" in data
        assert "in_sync" in data
        assert "weevr_files" in data
        assert "other_files" in data
        assert "summary" in data

    def test_json_verbose(self, mock_azure: MagicMock) -> None:
        mock_azure.list_files.return_value = []
        result = runner.invoke(app, ["--json", "status", "--verbose"], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "files" in data
        assert all("is_weevr" in f for f in data["files"])


class TestStatusAuthError:
    """Auth failure → clear error message."""

    def test_auth_failure(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        proj = _setup_project(tmp_path)
        monkeypatch.chdir(proj)
        from weevr_cli.state import AuthError

        with patch(
            "weevr_cli.state.AppState.credential",
            new_callable=lambda: property(
                lambda self: (_ for _ in ()).throw(AuthError("No Azure credentials found."))
            ),
        ):
            result = runner.invoke(app, ["status"], catch_exceptions=False)
        assert result.exit_code == 1
