"""Tests for OneLake client wrapper (mocked SDK)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from weevr_cli.deploy.models import DeployTarget
from weevr_cli.deploy.onelake import OneLakeClient


def _target(path_prefix: str | None = "weevr/proj") -> DeployTarget:
    return DeployTarget(
        workspace_id="11111111-1111-1111-1111-111111111111",
        lakehouse_id="22222222-2222-2222-2222-222222222222",
        path_prefix=path_prefix,
        name="dev",
    )


def _mock_path_props(
    name: str, is_dir: bool = False, size: int = 100, md5: bytes | None = None
) -> MagicMock:
    props = MagicMock()
    props.name = name
    props.is_directory = is_dir
    props.content_length = size
    if md5 is not None:
        props.content_settings = MagicMock()
        props.content_settings.content_md5 = md5
    else:
        props.content_settings = None
    return props


class TestOneLakeClient:
    @patch("weevr_cli.deploy.onelake.DataLakeServiceClient")
    def test_list_files(self, mock_service_cls: MagicMock) -> None:
        target = _target()
        mock_fs = MagicMock()
        mock_service_cls.return_value.get_file_system_client.return_value = mock_fs

        base = target.base_directory
        mock_fs.get_paths.return_value = [
            _mock_path_props(f"{base}/threads/orders.yaml", size=512, md5=b"\x01" * 16),
            _mock_path_props(f"{base}/subdir", is_dir=True),
            _mock_path_props(f"{base}/weaves/dim.yaml", size=256),
        ]

        client = OneLakeClient(target, MagicMock())
        files = client.list_files()

        assert len(files) == 2
        assert files[0].path == "threads/orders.yaml"
        assert files[0].size == 512
        assert files[0].content_md5 == b"\x01" * 16
        assert files[1].path == "weaves/dim.yaml"
        assert files[1].content_md5 is None

    @patch("weevr_cli.deploy.onelake.DataLakeServiceClient")
    def test_upload_file(self, mock_service_cls: MagicMock, tmp_path: Path) -> None:
        target = _target()
        mock_fs = MagicMock()
        mock_service_cls.return_value.get_file_system_client.return_value = mock_fs
        mock_file_client = MagicMock()
        mock_fs.get_file_client.return_value = mock_file_client

        local_file = tmp_path / "test.yaml"
        local_file.write_text("content")

        client = OneLakeClient(target, MagicMock())
        client.upload_file(local_file, "threads/test.yaml")

        expected_path = f"{target.base_directory}/threads/test.yaml"
        mock_fs.get_file_client.assert_called_once_with(expected_path)
        mock_file_client.upload_data.assert_called_once()

    @patch("weevr_cli.deploy.onelake.DataLakeServiceClient")
    def test_delete_file(self, mock_service_cls: MagicMock) -> None:
        target = _target()
        mock_fs = MagicMock()
        mock_service_cls.return_value.get_file_system_client.return_value = mock_fs
        mock_file_client = MagicMock()
        mock_fs.get_file_client.return_value = mock_file_client

        client = OneLakeClient(target, MagicMock())
        client.delete_file("old/file.yaml")

        expected_path = f"{target.base_directory}/old/file.yaml"
        mock_fs.get_file_client.assert_called_once_with(expected_path)
        mock_file_client.delete_file.assert_called_once()

    @patch("weevr_cli.deploy.onelake.DataLakeServiceClient")
    def test_list_files_no_prefix(self, mock_service_cls: MagicMock) -> None:
        target = _target(path_prefix=None)
        mock_fs = MagicMock()
        mock_service_cls.return_value.get_file_system_client.return_value = mock_fs

        base = target.base_directory
        mock_fs.get_paths.return_value = [
            _mock_path_props(f"{base}/file.yaml", size=100),
        ]

        client = OneLakeClient(target, MagicMock())
        files = client.list_files()
        assert len(files) == 1
        assert files[0].path == "file.yaml"
