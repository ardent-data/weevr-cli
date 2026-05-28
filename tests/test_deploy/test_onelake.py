"""Tests for OneLake client wrapper (mocked SDK)."""

import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

from azure.core.exceptions import AzureError, ResourceNotFoundError

from weevr_cli.deploy.models import DeployTarget
from weevr_cli.deploy.onelake import OneLakeClient


def _target(path_prefix: str | None = "weevr/proj") -> DeployTarget:
    return DeployTarget(
        workspace_id="11111111-1111-1111-1111-111111111111",
        lakehouse_id="22222222-2222-2222-2222-222222222222",
        path_prefix=path_prefix,
        name="dev",
    )


def _mock_path_props(name: str, is_dir: bool = False, size: int = 100) -> MagicMock:
    props = MagicMock()
    props.name = name
    props.is_directory = is_dir
    props.content_length = size
    return props


def _mock_file_props(md5: bytes | None = None, *, has_content_settings: bool = True) -> MagicMock:
    """Build a mock return value for get_file_properties()."""
    props = MagicMock()
    if has_content_settings:
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
            _mock_path_props(f"{base}/threads/orders.yaml", size=512),
            _mock_path_props(f"{base}/subdir", is_dir=True),
            _mock_path_props(f"{base}/weaves/dim.yaml", size=256),
        ]

        mock_file_client = MagicMock()
        mock_file_client.get_file_properties.side_effect = [
            _mock_file_props(md5=b"\x01" * 16),
            _mock_file_props(md5=None),
        ]
        mock_fs.get_file_client.return_value = mock_file_client

        client = OneLakeClient(target, MagicMock())
        files = client.list_files()

        assert len(files) == 2
        assert files[0].path == "threads/orders.yaml"
        assert files[0].size == 512
        assert files[0].content_md5 == b"\x01" * 16
        assert files[1].path == "weaves/dim.yaml"
        assert files[1].content_md5 is None

    @patch("weevr_cli.deploy.onelake.DataLakeServiceClient")
    def test_list_files_properties_error_gives_none_md5(self, mock_service_cls: MagicMock) -> None:
        target = _target()
        mock_fs = MagicMock()
        mock_service_cls.return_value.get_file_system_client.return_value = mock_fs

        base = target.base_directory
        mock_fs.get_paths.return_value = [
            _mock_path_props(f"{base}/file.yaml", size=100),
        ]
        mock_file_client = MagicMock()
        mock_file_client.get_file_properties.side_effect = AzureError("rate limited")
        mock_fs.get_file_client.return_value = mock_file_client

        client = OneLakeClient(target, MagicMock())
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            files = client.list_files()

        assert len(files) == 1
        assert files[0].content_md5 is None
        assert len(w) == 1
        assert "rate limited" in str(w[0].message)

    @patch("weevr_cli.deploy.onelake.DataLakeServiceClient")
    def test_list_files_no_content_settings(self, mock_service_cls: MagicMock) -> None:
        target = _target()
        mock_fs = MagicMock()
        mock_service_cls.return_value.get_file_system_client.return_value = mock_fs

        base = target.base_directory
        mock_fs.get_paths.return_value = [
            _mock_path_props(f"{base}/file.yaml", size=100),
        ]
        mock_file_client = MagicMock()
        mock_file_client.get_file_properties.return_value = _mock_file_props(
            has_content_settings=False,
        )
        mock_fs.get_file_client.return_value = mock_file_client

        client = OneLakeClient(target, MagicMock())
        files = client.list_files()

        assert len(files) == 1
        assert files[0].content_md5 is None

    @patch("weevr_cli.deploy.onelake.DataLakeServiceClient")
    def test_upload_file_sets_content_md5(
        self, mock_service_cls: MagicMock, tmp_path: Path
    ) -> None:
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
        upload_call = mock_file_client.upload_data.call_args
        assert upload_call is not None
        assert upload_call.kwargs.get("overwrite") is True
        cs = upload_call.kwargs.get("content_settings")
        assert cs is not None
        assert cs.content_md5 is not None

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
    def test_list_files_path_not_found_returns_empty(self, mock_service_cls: MagicMock) -> None:
        """First-deploy: missing remote subfolder is treated as empty, not an error."""
        target = _target()
        mock_fs = MagicMock()
        mock_service_cls.return_value.get_file_system_client.return_value = mock_fs
        mock_fs.get_paths.side_effect = ResourceNotFoundError("PathNotFound")

        client = OneLakeClient(target, MagicMock())
        files = client.list_files()

        assert files == []

    @patch("weevr_cli.deploy.onelake.DataLakeServiceClient")
    def test_list_files_path_not_found_on_iteration(self, mock_service_cls: MagicMock) -> None:
        """ItemPaged from get_paths raises lazily on iteration — must still be caught."""
        target = _target()
        mock_fs = MagicMock()
        mock_service_cls.return_value.get_file_system_client.return_value = mock_fs

        def _raise_on_iter() -> list[MagicMock]:
            raise ResourceNotFoundError("PathNotFound")

        lazy = MagicMock()
        lazy.__iter__ = lambda self: iter(_raise_on_iter())
        mock_fs.get_paths.return_value = lazy

        client = OneLakeClient(target, MagicMock())
        files = client.list_files()

        assert files == []

    @patch("weevr_cli.deploy.onelake.DataLakeServiceClient")
    def test_list_files_no_prefix(self, mock_service_cls: MagicMock) -> None:
        target = _target(path_prefix=None)
        mock_fs = MagicMock()
        mock_service_cls.return_value.get_file_system_client.return_value = mock_fs

        base = target.base_directory
        mock_fs.get_paths.return_value = [
            _mock_path_props(f"{base}/file.yaml", size=100),
        ]
        mock_file_client = MagicMock()
        mock_file_client.get_file_properties.return_value = _mock_file_props(md5=None)
        mock_fs.get_file_client.return_value = mock_file_client

        client = OneLakeClient(target, MagicMock())
        files = client.list_files()
        assert len(files) == 1
        assert files[0].path == "file.yaml"
