"""Engine rules checked after a weave or loom loads cleanly.

These are rules the engine only enforces when it plans or runs a weave:
incremental-load conflicts, ignored execution settings, dependency cycles,
and unordered writers of the same target. Running them here reports the
problem before deploy instead of in a failed Fabric run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from weevr.config.parser import TYPED_EXTENSIONS
from weevr.config.validation import validate_incremental_config
from weevr.model import Thread

from weevr_cli.validation.engine import LOAD_FAILURES, display_path
from weevr_cli.validation.resolved import load_resolved
from weevr_cli.validation.results import ValidationIssue

_PREFIXES: dict[str, Literal["error", "warning"]] = {"ERROR:": "error", "WARN:": "warning"}


def _parse_diagnostic(text: str) -> tuple[Literal["error", "warning"], str]:
    """Split weevr-core's ``ERROR:``/``WARN:`` prefix off a diagnostic message."""
    for prefix, severity in _PREFIXES.items():
        if text.startswith(prefix):
            return severity, text[len(prefix) :].strip()
    return "warning", text


def _incremental_input(thread: Thread) -> dict[str, Any]:
    """Build the dict ``validate_incremental_config`` expects.

    Mirrors how the engine builds it at executor entry
    (``weevr.engine.executor._validate_incremental``), so the CLI reports the
    same diagnostics the engine would raise on.
    """
    load_raw: dict[str, Any] = {"mode": thread.load.mode if thread.load else "full"}
    if thread.load is not None:
        load_raw["watermark_inclusive"] = thread.load.watermark_inclusive
        if thread.load.watermark_column is not None:
            load_raw["watermark_column"] = thread.load.watermark_column
        if thread.load.cdc is not None:
            load_raw["cdc"] = thread.load.cdc.model_dump()
    raw: dict[str, Any] = {"load": load_raw}
    if thread.write is not None:
        raw["write"] = {"mode": thread.write.mode}
    return raw


def check_resolved(path: Path, *, project_root: Path | None = None) -> list[ValidationIssue]:
    """Run the engine's plan-time and execution-entry checks on a weave or loom.

    Call this only for files that already passed :func:`validate_file`; a file
    that fails to load here returns no issues, since that failure is already
    reported.

    Args:
        path: The ``.weave`` or ``.loom`` file.
        project_root: The ``.weevr`` project directory.

    Returns:
        Issues attributed to the thread or weave file they concern, or to
        ``path`` for inline definitions and load warnings.
    """
    try:
        loaded = load_resolved(path, project_root=project_root)
    except LOAD_FAILURES:
        return []

    root = project_root if project_root is not None else path.parent
    loaded_file = display_path(path, project_root)

    def file_for(qualified_key: str | None, fallback: str) -> str:
        # Children loaded from a file carry their project-relative path as the
        # qualified key; inline definitions carry only their name.
        if qualified_key and Path(qualified_key).suffix in TYPED_EXTENSIONS:
            candidate = root / qualified_key
            if candidate.is_file():
                return display_path(candidate, project_root)
        return fallback

    issues: list[ValidationIssue] = []
    for text in loaded.warnings:
        severity, message = _parse_diagnostic(text)
        issues.append(ValidationIssue(severity, message, loaded_file))

    weave_files: dict[str, str] = {
        name: file_for(weave.qualified_key, loaded_file)
        for name, weave in loaded.resolved_weaves.items()
    }

    for weave_name, threads in loaded.resolved_threads.items():
        weave_file = weave_files.get(weave_name, loaded_file)
        for thread in threads.values():
            if thread.load is None or thread.load.mode == "full":
                continue
            thread_file = file_for(thread.qualified_key, weave_file)
            for text in validate_incremental_config(_incremental_input(thread)):
                severity, message = _parse_diagnostic(text)
                issues.append(ValidationIssue(severity, message, thread_file))

    for plan_issue in loaded.validate_plans():
        weave_file = weave_files.get(plan_issue.weave_name, loaded_file)
        issues.append(ValidationIssue("error", plan_issue.message, weave_file))

    return issues
