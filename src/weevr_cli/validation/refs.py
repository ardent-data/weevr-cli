"""Reference integrity checking and orphan detection."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

from weevr_cli.validation.results import ValidationIssue


def extract_refs(data: dict[str, Any], file_path: str) -> list[tuple[str, str, str]]:
    """Extract ref entries from a parsed weave or loom file.

    Returns:
        List of (ref_value, source_file, location) tuples.
    """
    refs: list[tuple[str, str, str]] = []

    # Weave: threads[].ref
    threads = data.get("threads")
    if isinstance(threads, list):
        for idx, item in enumerate(threads):
            if isinstance(item, dict) and "ref" in item:
                refs.append((str(item["ref"]), file_path, f"threads[{idx}].ref"))

    # Loom: weaves[].ref
    weaves = data.get("weaves")
    if isinstance(weaves, list):
        for idx, item in enumerate(weaves):
            if isinstance(item, dict) and "ref" in item:
                refs.append((str(item["ref"]), file_path, f"weaves[{idx}].ref"))

    return refs


def check_refs(
    files: dict[str, Any],
    project_root: Path,
) -> list[ValidationIssue]:
    """Check that all ref: entries point to files that exist.

    Args:
        files: Dict mapping relative paths to parsed YAML data.
        project_root: The .weevr project root directory.

    Returns:
        List of validation issues (errors for broken refs or path traversal).
    """
    issues: list[ValidationIssue] = []

    for file_path, data in files.items():
        if not isinstance(data, dict):
            continue

        for ref_value, source_file, location in extract_refs(data, file_path):
            # Reject absolute paths and path traversal
            ref_path = PurePosixPath(ref_value)
            if ref_path.is_absolute() or ".." in ref_path.parts:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        message=(
                            f"Path traversal not allowed: '{ref_value}' "
                            f"must be a relative path within the project"
                        ),
                        file=source_file,
                        location=location,
                    )
                )
                continue

            # Check target exists
            target = project_root / ref_value
            if not target.is_file():
                issues.append(
                    ValidationIssue(
                        severity="error",
                        message=f"Broken reference: {ref_value} does not exist",
                        file=source_file,
                        location=location,
                    )
                )

    return issues


def find_orphans(
    files: dict[str, Any],
    all_paths: list[str],
) -> list[ValidationIssue]:
    """Detect files not referenced by anything.

    Threads should be referenced by weaves, weaves by looms.
    Looms are top-level entry points and are never orphans.

    Args:
        files: Dict mapping relative paths to parsed YAML data.
        all_paths: All discovered file paths in the project.

    Returns:
        List of warning issues for orphaned files.
    """
    # Collect all referenced paths
    referenced: set[str] = set()
    for data in files.values():
        if not isinstance(data, dict):
            continue
        for ref_value, _, _ in extract_refs(data, ""):
            referenced.add(ref_value)

    issues: list[ValidationIssue] = []
    for path in all_paths:
        # Looms and warps are standalone — never orphans
        if path.endswith(".loom") or path.endswith(".warp"):
            continue

        # Check if this file is referenced
        if path not in referenced:
            file_type = "weave" if path.endswith(".weave") else "thread"
            issues.append(
                ValidationIssue(
                    severity="warning",
                    message=(
                        f"Orphaned file: not referenced by any "
                        f"{'loom' if file_type == 'weave' else 'weave or loom'}"
                    ),
                    file=path,
                )
            )

    return issues
