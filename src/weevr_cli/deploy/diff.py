"""Diff algorithm for computing deploy plans."""

from __future__ import annotations

import pathspec

from weevr_cli.deploy.collector import LocalFile
from weevr_cli.deploy.manifest import DeployManifest
from weevr_cli.deploy.models import (
    ActionType,
    DeployAction,
    DeployPlan,
    DeployTarget,
    RemoteFile,
)

WEEVR_EXTENSIONS = {".thread", ".weave", ".loom", ".warp", ".yaml", ".yml"}


def compute_diff(
    target: DeployTarget,
    local_files: list[LocalFile],
    remote_files: list[RemoteFile],
    *,
    full: bool = False,
    clean: bool = False,
    clean_all: bool = False,
    ignore_spec: pathspec.PathSpec | None = None,
    manifest: DeployManifest | None = None,
) -> DeployPlan:
    """Compute a deploy plan by comparing local and remote files.

    Args:
        target: Resolved deploy target.
        local_files: Files collected from the local project.
        remote_files: Files listed from the remote target.
        full: If True, upload all files unconditionally (full overwrite).
        clean: If True, delete remote weevr files not present locally.
        clean_all: If True, delete all remote files not present locally.
        ignore_spec: Deploy-ignore patterns. Remote files matching these
            patterns are excluded from clean actions.
        manifest: Previously saved deploy manifest. When the remote does not
            provide content hashes, the manifest's stored hashes are used
            to detect content changes.

    Returns:
        DeployPlan with actions for each file.
    """
    remote_by_path: dict[str, RemoteFile] = {rf.path: rf for rf in remote_files}
    local_paths: set[str] = {lf.relative_path for lf in local_files}

    actions: list[DeployAction] = []

    # Process local files
    for lf in local_files:
        remote = remote_by_path.get(lf.relative_path)

        if full:
            actions.append(
                DeployAction(
                    local_path=lf.absolute_path,
                    remote_path=lf.relative_path,
                    action=ActionType.UPLOAD_FORCED,
                    reason="forced (full overwrite)",
                )
            )
        elif remote is None:
            actions.append(
                DeployAction(
                    local_path=lf.absolute_path,
                    remote_path=lf.relative_path,
                    action=ActionType.UPLOAD_NEW,
                    reason="new (not on remote)",
                )
            )
        elif _has_changed(lf, remote, manifest):
            actions.append(
                DeployAction(
                    local_path=lf.absolute_path,
                    remote_path=lf.relative_path,
                    action=ActionType.UPLOAD_MODIFIED,
                    reason="modified (content changed)",
                )
            )
        else:
            actions.append(
                DeployAction(
                    local_path=lf.absolute_path,
                    remote_path=lf.relative_path,
                    action=ActionType.SKIP,
                    reason="unchanged",
                )
            )

    # Process remote-only files for clean mode
    if clean or clean_all:
        for remote in remote_files:
            if ignore_spec is not None and ignore_spec.match_file(remote.path):
                continue
            if remote.path not in local_paths and (clean_all or _is_weevr_file(remote.path)):
                actions.append(
                    DeployAction(
                        local_path=None,
                        remote_path=remote.path,
                        action=ActionType.DELETE,
                        reason="remote only",
                    )
                )

    return DeployPlan(target=target, actions=actions)


def _has_changed(
    local: LocalFile,
    remote: RemoteFile,
    manifest: DeployManifest | None = None,
) -> bool:
    """Check if a local file differs from its remote counterpart.

    Uses MD5 hash comparison when available. When the remote does not
    provide a content hash (common with OneLake), falls back to comparing
    the local hash against the deploy manifest. Size comparison is the
    last resort when neither remote hash nor manifest is available.
    """
    if remote.content_md5 is not None:
        return local.content_md5 != remote.content_md5
    if manifest is not None:
        manifest_md5 = manifest.get_md5(local.relative_path)
        if manifest_md5 is not None:
            return local.content_md5.hex() != manifest_md5
    return local.size != remote.size


def _is_weevr_file(path: str) -> bool:
    """Check if a remote path looks like a weevr artifact file."""
    lower = path.lower()
    return any(lower.endswith(ext) for ext in WEEVR_EXTENSIONS)
