"""Implementation of the weevr validate command."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from rich.table import Table

from weevr_cli.config import WEEVR_PROJECT_EXT, find_project_root
from weevr_cli.output import print_error, print_json
from weevr_cli.state import AppState
from weevr_cli.validation.refs import check_refs, find_orphans
from weevr_cli.validation.results import ValidationIssue, ValidationResult
from weevr_cli.validation.schema import validate_file

_WEEVR_EXTENSIONS = (".thread", ".weave", ".loom")


def _find_weevr_files(directory: Path) -> list[Path]:
    """Recursively find all .thread, .weave, .loom files in a directory."""
    directory = directory.resolve()
    files: list[Path] = []
    for ext in _WEEVR_EXTENSIONS:
        files.extend(directory.rglob(f"*{ext}"))
    return sorted(files)


def _determine_project_root(target_path: Path | None) -> Path | None:
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
    project_root = _determine_project_root(Path(path).resolve() if path else None)
    if project_root is not None:
        project_root = project_root.resolve()

    all_issues: list[ValidationIssue] = []
    target_path = Path(path).resolve() if path else None

    # Determine what to validate
    if target_path is not None and target_path.is_file():
        # Single file: schema + immediate refs
        files_to_check = [target_path]
    elif target_path is not None and target_path.is_dir():
        # Directory: recursive scan
        files_to_check = _find_weevr_files(target_path)
    elif project_root is not None:
        # Full project scan
        files_to_check = _find_weevr_files(project_root)
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
        # Parse all files for ref extraction
        parsed: dict[str, Any] = {}
        for file_path in files_to_check:
            rel = str(file_path.relative_to(project_root))
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
