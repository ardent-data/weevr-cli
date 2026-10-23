"""Orphan detection for weevr project files.

Works on raw parsed YAML rather than weevr-core's loader, so orphans are
still reported when other files in the project fail validation.
"""

from __future__ import annotations

from typing import Any

from weevr_cli.validation.results import ValidationIssue


def normalize_ref(ref_value: str) -> str:
    """Normalize a ref to a project-root-relative POSIX path.

    Accepts the documented leading-'/' project-root marker and strips it.
    Backslashes are converted to forward slashes so refs authored on
    Windows still compare correctly against POSIX file paths.
    """
    return ref_value.replace("\\", "/").lstrip("/")


def extract_refs(data: dict[str, Any], file_path: str) -> list[tuple[str, str, str]]:
    """Extract file references from a parsed weave or loom.

    Follows weevr-core's conventions: a weave's ``threads[].ref`` and a loom's
    ``weaves[].ref`` name a file relative to the project root. A loom entry
    given only by name (``- w1`` or ``- name: w1``) refers to ``w1.weave`` at
    the project root. A weave thread entry given only by name is an inline
    thread, not a file reference.

    Returns:
        List of (ref_value, source_file, location) tuples.
    """
    refs: list[tuple[str, str, str]] = []

    threads = data.get("threads")
    if isinstance(threads, list):
        for idx, item in enumerate(threads):
            if isinstance(item, dict) and "ref" in item:
                refs.append((str(item["ref"]), file_path, f"threads[{idx}].ref"))

    weaves = data.get("weaves")
    if isinstance(weaves, list):
        for idx, item in enumerate(weaves):
            if isinstance(item, dict) and "ref" in item:
                refs.append((str(item["ref"]), file_path, f"weaves[{idx}].ref"))
            elif isinstance(item, str) and item:
                refs.append((f"{item}.weave", file_path, f"weaves[{idx}]"))
            elif isinstance(item, dict) and item.get("name"):
                refs.append((f"{item['name']}.weave", file_path, f"weaves[{idx}]"))

    return refs


def find_orphans(files: dict[str, Any], all_paths: list[str]) -> list[ValidationIssue]:
    """Detect threads and weaves that nothing references.

    Threads should be referenced by weaves, weaves by looms. Looms are
    top-level entry points and warps are standalone, so neither is flagged.

    Args:
        files: Dict mapping project-relative paths to parsed YAML data.
        all_paths: All discovered file paths in the project.

    Returns:
        A warning issue for each orphaned file.
    """
    referenced: set[str] = set()
    for data in files.values():
        if not isinstance(data, dict):
            continue
        for ref_value, _, _ in extract_refs(data, ""):
            referenced.add(normalize_ref(ref_value))

    issues: list[ValidationIssue] = []
    for path in all_paths:
        # Windows-collected paths use backslashes; refs are always POSIX.
        normalized_path = path.replace("\\", "/")
        if normalized_path.endswith((".loom", ".warp")):
            continue
        if normalized_path not in referenced:
            referrer = "loom" if normalized_path.endswith(".weave") else "weave or loom"
            issues.append(
                ValidationIssue(
                    severity="warning",
                    message=f"Orphaned file: not referenced by any {referrer}",
                    file=normalized_path,
                )
            )

    return issues
