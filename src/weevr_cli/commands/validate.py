"""Implementation of the weevr validate command."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pathspec
import yaml
from rich.table import Table

from weevr_cli.config import WEEVR_PROJECT_EXT, find_project_root
from weevr_cli.ignore import (
    deploy_ignore_deprecation_message,
    has_deploy_ignore,
    load_combined_ignore,
)
from weevr_cli.output import print_error, print_json
from weevr_cli.state import AppState
from weevr_cli.validation.refs import check_refs, find_orphans
from weevr_cli.validation.results import ValidationIssue, ValidationResult
from weevr_cli.validation.schema import validate_file

_WEEVR_EXTENSIONS = (".thread", ".weave", ".loom", ".warp")


def _find_weevr_files(
    directory: Path,
    *,
    ignore_spec: pathspec.PathSpec | None = None,
    ignore_root: Path | None = None,
) -> list[Path]:
    """Recursively find all .thread, .weave, .loom, .warp files in a directory.

    When ``ignore_spec`` is provided, files whose path (relative to
    ``ignore_root``) matches any ignore pattern are excluded. ``ignore_root``
    should be the project root — ignore patterns are always interpreted
    relative to it, not the scan ``directory``.
    """
    directory = directory.resolve()
    files: list[Path] = []
    for ext in _WEEVR_EXTENSIONS:
        files.extend(directory.rglob(f"*{ext}"))

    if ignore_spec is not None and ignore_root is not None:
        filtered: list[Path] = []
        for f in files:
            try:
                rel = f.relative_to(ignore_root).as_posix()
            except ValueError:
                # File is outside the ignore root — cannot be matched by
                # project-relative patterns, so keep it.
                filtered.append(f)
                continue
            if not ignore_spec.match_file(rel):
                filtered.append(f)
        files = filtered

    return sorted(files)


def _determine_project_root() -> Path | None:
    """Determine the .weevr project root for ref resolution.

    Resolution order:
    1. If cwd name ends with .weevr, use cwd.
    2. Walk up via find_project_root().
    3. None (no project root found).
    """
    cwd = Path.cwd()
    if cwd.name.endswith(WEEVR_PROJECT_EXT):
        return cwd
    return find_project_root()


def _parse_file(path: Path) -> dict[str, Any] | None:
    """Parse a YAML file, returning None on failure."""
    try:
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else None
    except (yaml.YAMLError, OSError):
        return None


def _render_rich(result: ValidationResult, state: AppState) -> None:
    """Render validation results using Rich."""
    if result.is_valid and not result.warnings:
        state.console.print(
            f"[green]Validation passed[/green] ({result.files_checked} files checked)"
        )
        return

    # Group issues by file
    by_file: dict[str, list[ValidationIssue]] = {}
    for issue in result.issues:
        by_file.setdefault(issue.file, []).append(issue)

    for file_path, issues in sorted(by_file.items()):
        table = Table(title=file_path, show_header=True)
        table.add_column("Severity", style="bold", width=8)
        table.add_column("Message")
        table.add_column("Location", style="dim")
        for issue in issues:
            style = "red" if issue.severity == "error" else "yellow"
            table.add_row(
                f"[{style}]{issue.severity}[/{style}]",
                issue.message,
                issue.location or "",
            )
        state.console.print(table)

    # Summary
    state.console.print(
        f"\n{result.files_checked} files checked, "
        f"[red]{len(result.errors)} errors[/red], "
        f"[yellow]{len(result.warnings)} warnings[/yellow]"
    )


def run_validate(
    path: str | None,
    *,
    strict: bool,
    state: AppState,
) -> None:
    """Execute the validate command.

    Args:
        path: Optional file or directory to validate.
        strict: Whether to treat warnings as errors.
        state: Application state.

    Raises:
        SystemExit: With code 1 on validation errors or no files found.
    """
    project_root = _determine_project_root()
    if project_root is not None:
        project_root = project_root.resolve()

    all_issues: list[ValidationIssue] = []
    target_path = Path(path).resolve() if path else None

    # Check that explicit target exists
    if target_path is not None and not target_path.exists():
        print_error(
            f"Path not found: {path}",
            "path_not_found",
            json_mode=state.json_mode,
            console=state.console,
        )
        raise SystemExit(1)

    # Load project-wide ignore patterns (validate does NOT honor deploy-ignore).
    # The ignore filter applies only to the full-project scan. An explicit
    # target_path — whether a file or a directory — bypasses the filter
    # entirely: if the user named it on the command line, they meant it.
    ignore_spec: pathspec.PathSpec | None = None
    if project_root is not None and target_path is None:
        ignore_spec = load_combined_ignore(project_root, include_deploy=False)
        if has_deploy_ignore(project_root) and not state.json_mode:
            state.console.print(f"[yellow]{deploy_ignore_deprecation_message()}[/yellow]")

    # Determine what to validate
    if target_path is not None and target_path.is_file():
        # Single file: schema + immediate refs
        files_to_check = [target_path]
    elif target_path is not None and target_path.is_dir():
        # Directory: recursive scan. Explicit path — ignore filter bypassed
        # intentionally. If the user ran `weevr validate scratch/`, they
        # want scratch/ validated even if it is otherwise ignored.
        files_to_check = _find_weevr_files(target_path)
    elif project_root is not None:
        # Full project scan — apply ignore filter
        files_to_check = _find_weevr_files(
            project_root, ignore_spec=ignore_spec, ignore_root=project_root
        )
    else:
        # Scan cwd as fallback
        files_to_check = _find_weevr_files(Path.cwd())

    if not files_to_check:
        print_error(
            "No weevr files found in current directory",
            "no_files_found",
            json_mode=state.json_mode,
            console=state.console,
        )
        raise SystemExit(1)

    # Schema validation for each file
    for file_path in files_to_check:
        issues = validate_file(file_path, project_root=project_root)
        all_issues.extend(issues)

    # Reference checking
    if project_root is not None:
        # Parse all files for ref extraction (skip files outside project root)
        parsed: dict[str, Any] = {}
        for file_path in files_to_check:
            try:
                # Use POSIX form so orphan detection compares consistently
                # against YAML refs regardless of host OS.
                rel = file_path.relative_to(project_root).as_posix()
            except ValueError:
                continue
            data = _parse_file(file_path)
            if data is not None:
                parsed[rel] = data

        # Check refs
        ref_issues = check_refs(parsed, project_root)
        all_issues.extend(ref_issues)

        # Orphan detection only in full-project mode (no target arg)
        if target_path is None:
            all_paths = list(parsed.keys())
            orphan_issues = find_orphans(parsed, all_paths)
            all_issues.extend(orphan_issues)
    elif target_path is not None and target_path.is_file():
        # Single file without project root — warn about limited checking
        state.console.print("[yellow]No project root found — ref checking skipped[/yellow]")

    result = ValidationResult(
        issues=all_issues,
        files_checked=len(files_to_check),
    )

    if strict:
        result.apply_strict()

    # Output
    if state.json_mode:
        print_json(result.to_dict())
    else:
        _render_rich(result, state)

    if not result.is_valid:
        raise SystemExit(1)
