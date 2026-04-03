"""Local file collection with deploy-ignore support."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pathspec


@dataclass
class LocalFile:
    """A local file to be considered for deployment."""

    absolute_path: Path
    relative_path: str
    size: int
    content_md5: bytes


def compute_md5(path: Path) -> bytes:
    """Compute the MD5 hash of a file's contents.

    Args:
        path: Path to the file.

    Returns:
        16-byte MD5 digest.
    """
    hasher = hashlib.md5()  # noqa: S324
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.digest()


def collect_local_files(
    project_root: Path,
    ignore_spec: pathspec.PathSpec,
    *,
    selective_paths: list[str] | None = None,
) -> list[LocalFile]:
    """Collect local files eligible for deployment.

    Walks the project root, excludes the .weevr directory's cli.yaml and
    deploy-ignore (config files), and applies deploy-ignore patterns.

    Args:
        project_root: Root directory of the weevr project.
        ignore_spec: Compiled deploy-ignore patterns.
        selective_paths: If provided, only include files matching these
            relative paths or directories. Paths are relative to project root.

    Returns:
        Sorted list of LocalFile objects.

    Raises:
        FileNotFoundError: If a selective path does not exist.
    """
    if selective_paths is not None:
        return _collect_selective(project_root, ignore_spec, selective_paths)
    return _collect_all(project_root, ignore_spec)


def _collect_all(project_root: Path, ignore_spec: pathspec.PathSpec) -> list[LocalFile]:
    """Collect all deployable files from the project root."""
    files: list[LocalFile] = []
    for path in sorted(project_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(project_root).as_posix()
        if _is_config_file(relative):
            continue
        if ignore_spec.match_file(relative):
            continue
        files.append(
            LocalFile(
                absolute_path=path,
                relative_path=relative,
                size=path.stat().st_size,
                content_md5=compute_md5(path),
            )
        )
    return files


def _collect_selective(
    project_root: Path,
    ignore_spec: pathspec.PathSpec,
    selective_paths: list[str],
) -> list[LocalFile]:
    """Collect only files matching the specified paths."""
    files: list[LocalFile] = []
    seen: set[str] = set()

    for sel_path in selective_paths:
        full_path = project_root / sel_path
        if not full_path.exists():
            raise FileNotFoundError(f"Path does not exist: {sel_path}")

        if full_path.is_file():
            relative = full_path.relative_to(project_root).as_posix()
            if relative not in seen and not ignore_spec.match_file(relative):
                seen.add(relative)
                files.append(
                    LocalFile(
                        absolute_path=full_path,
                        relative_path=relative,
                        size=full_path.stat().st_size,
                        content_md5=compute_md5(full_path),
                    )
                )
        elif full_path.is_dir():
            for path in sorted(full_path.rglob("*")):
                if not path.is_file():
                    continue
                relative = path.relative_to(project_root).as_posix()
                if relative in seen:
                    continue
                if _is_config_file(relative):
                    continue
                if ignore_spec.match_file(relative):
                    continue
                seen.add(relative)
                files.append(
                    LocalFile(
                        absolute_path=path,
                        relative_path=relative,
                        size=path.stat().st_size,
                        content_md5=compute_md5(path),
                    )
                )

    return sorted(files, key=lambda f: f.relative_path)


_CONFIG_FILES = {".weevr/cli.yaml", ".weevr/deploy-ignore"}


def _is_config_file(relative_path: str) -> bool:
    """Check if a path is a weevr config file that should not be deployed."""
    return relative_path in _CONFIG_FILES
