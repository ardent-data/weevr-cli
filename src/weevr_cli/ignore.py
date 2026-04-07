"""Ignore-file parsing for weevr projects.

Two project-wide ignore files are supported. Both are optional, neither takes
precedence over the other, and patterns from both are unioned:

- ``.weevr/ignore`` — lives alongside other weevr config (``cli.yaml``).
- ``.weevrignore`` at the project root — the gitignore-style convention
  familiar from ``.gitignore``, ``.dockerignore``, etc.

A third file, ``.weevr/deploy-ignore``, is **deprecated** and applies only to
deploy operations. It is still honored when present but will be removed in
v1.3.0. New patterns should be added to ``.weevr/ignore`` instead.

All sources use gitignore-style pattern syntax via ``pathspec``.
"""

from __future__ import annotations

from pathlib import Path

import pathspec

PROJECT_IGNORE_PATH = (".weevr", "ignore")
ROOT_IGNORE_FILENAME = ".weevrignore"
DEPLOY_IGNORE_PATH = (".weevr", "deploy-ignore")

DEPLOY_IGNORE_REMOVAL_VERSION = "v1.3.0"


def _read_lines(path: Path) -> list[str]:
    """Read pattern lines from an ignore file. Returns [] if missing."""
    if not path.is_file():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def load_deploy_ignore(project_root: Path) -> pathspec.PathSpec:
    """Load deploy-only ignore patterns from ``.weevr/deploy-ignore``.

    .. deprecated::
        Use ``.weevr/ignore`` for project-wide ignores. This file will be
        removed in v1.3.0.

    Args:
        project_root: Root directory of the weevr project.

    Returns:
        A ``PathSpec`` matcher. Empty if the file does not exist.
    """
    lines = _read_lines(project_root / Path(*DEPLOY_IGNORE_PATH))
    return pathspec.PathSpec.from_lines("gitignore", lines)


def load_combined_ignore(
    project_root: Path,
    *,
    include_deploy: bool,
) -> pathspec.PathSpec:
    """Load the active ignore set for a command.

    Args:
        project_root: Root directory of the weevr project.
        include_deploy: When True, also include ``.weevr/deploy-ignore``
            patterns (use this for ``deploy`` and ``status`` commands).
            When False, only project-wide ignores are loaded
            (use this for ``validate`` and ``list``).

    Returns:
        A combined ``PathSpec`` matcher.
    """
    lines: list[str] = []
    lines.extend(_read_lines(project_root / Path(*PROJECT_IGNORE_PATH)))
    lines.extend(_read_lines(project_root / ROOT_IGNORE_FILENAME))
    if include_deploy:
        lines.extend(_read_lines(project_root / Path(*DEPLOY_IGNORE_PATH)))
    return pathspec.PathSpec.from_lines("gitignore", lines)


def has_deploy_ignore(project_root: Path) -> bool:
    """Return True if the deprecated ``.weevr/deploy-ignore`` file exists."""
    return (project_root / Path(*DEPLOY_IGNORE_PATH)).is_file()


def deploy_ignore_deprecation_message() -> str:
    """User-facing deprecation message for ``.weevr/deploy-ignore``."""
    return (
        ".weevr/deploy-ignore is deprecated and will be removed in "
        f"{DEPLOY_IGNORE_REMOVAL_VERSION}. "
        "Move its patterns to .weevr/ignore (project-wide) and delete the "
        "old file."
    )


def is_ignored(spec: pathspec.PathSpec, relative_path: str) -> bool:
    """Check whether a relative path matches any ignore pattern.

    Args:
        spec: Compiled ``PathSpec`` matcher.
        relative_path: Path relative to project root, forward slashes.

    Returns:
        True if the path should be ignored.
    """
    return spec.match_file(relative_path)
