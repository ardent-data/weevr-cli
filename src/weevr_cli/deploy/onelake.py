"""OneLake client wrapper around azure-storage-file-datalake."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.filedatalake import DataLakeServiceClient

from weevr_cli.deploy.models import DeployTarget, RemoteFile

if TYPE_CHECKING:
    from azure.core.credentials import TokenCredential


class OneLakeClient:
    """Wrapper around azure-storage-file-datalake for OneLake operations."""

    def __init__(self, target: DeployTarget, credential: TokenCredential) -> None:
        """Initialize with a deploy target and Azure credential."""
        self._target = target
        self._service_client = DataLakeServiceClient(
            account_url=target.onelake_account_url,
            credential=credential,
        )
        self._fs_client = self._service_client.get_file_system_client(
            file_system=target.filesystem_name,
        )

    def list_files(self) -> list[RemoteFile]:
        """List all files under the deploy target's base directory.

        If the base directory does not exist on the remote — typically
        because no prior deploy has populated it — this is treated as
        "remote is empty" and an empty list is returned. Upload operations
        create parent directories on demand, so smart-sync can bootstrap
        a fresh lakehouse without an explicit init step.

        Returns:
            List of RemoteFile objects representing remote files.
        """
        base_dir = self._target.base_directory
        files: list[RemoteFile] = []
        try:
            paths = self._fs_client.get_paths(path=base_dir, recursive=True)
            path_iter = list(paths)
        except ResourceNotFoundError:
            return []
        for path_props in path_iter:
            if path_props.is_directory:
                continue
            # Strip base directory prefix to get relative path
            full_path: str = path_props.name  # type: ignore[assignment]
            relative = (
                full_path[len(base_dir) + 1 :] if full_path.startswith(base_dir) else full_path
            )
            settings = getattr(path_props, "content_settings", None)
            content_md5 = getattr(settings, "content_md5", None) if settings else None
            files.append(
                RemoteFile(
                    path=relative,
                    size=path_props.content_length or 0,
                    content_md5=content_md5,
                )
            )
        return files

    def upload_file(self, local_path: Path, remote_path: str) -> None:
        """Upload a local file to the remote target.

        Creates parent directories as needed.

        Args:
            local_path: Path to the local file.
            remote_path: Relative path within the deploy target.
        """
        full_remote = f"{self._target.base_directory}/{remote_path}"
        file_client = self._fs_client.get_file_client(full_remote)
        with local_path.open("rb") as f:
            file_client.upload_data(f, overwrite=True)

    def delete_file(self, remote_path: str) -> None:
        """Delete a file from the remote target.

        Args:
            remote_path: Relative path within the deploy target.
        """
        full_remote = f"{self._target.base_directory}/{remote_path}"
        file_client = self._fs_client.get_file_client(full_remote)
        file_client.delete_file()
