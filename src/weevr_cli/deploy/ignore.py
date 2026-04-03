"""Deploy-ignore file parsing using gitignore-style patterns."""

from __future__ import annotations

from pathlib import Path

import pathspec


def load_deploy_ignore(project_root: Path) -> pathspec.PathSpec:
    """Load deploy-ignore patterns from the project's .weevr/deploy-ignore file.

    Args:
        project_root: Root directory of the weevr project.

    Returns:
        A PathSpec matcher. Returns an empty matcher if the file does not exist.
    """
    ignore_path = project_root / ".weevr" / "deploy-ignore"
    if not ignore_path.is_file():
        return pathspec.PathSpec.from_lines("gitignore", [])

    lines = ignore_path.read_text(encoding="utf-8").splitlines()
    return pathspec.PathSpec.from_lines("gitignore", lines)


def is_ignored(spec: pathspec.PathSpec, relative_path: str) -> bool:
    """Check whether a relative path matches any deploy-ignore pattern.

    Args:
        spec: Compiled pathspec matcher.
        relative_path: Path relative to project root (forward slashes).

    Returns:
        True if the path should be ignored.
    """
    return spec.match_file(relative_path)
