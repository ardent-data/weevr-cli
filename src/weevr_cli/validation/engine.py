"""Validate weevr files with weevr-core's config loader."""

from __future__ import annotations

import logging
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError
from weevr.config import load_config
from weevr.errors import (
    ConfigError,
    ConfigSchemaError,
    ReferenceResolutionError,
    VariableResolutionError,
    WeevError,
)

from weevr_cli.validation.results import ValidationIssue

# There is no Fabric runtime on a workstation or CI runner, so ${fabric.x}
# references get placeholder strings. weevr-core only resolves the nested
# form; a flat "fabric.workspace_id" key is ignored.
FABRIC_PLACEHOLDERS: dict[str, Any] = {
    "fabric": {
        "workspace_id": "<fabric.workspace_id>",
        "lakehouse_id": "<fabric.lakehouse_id>",
        "workspace_name": "<fabric.workspace_name>",
    }
}

_NO_PROJECT_HINT = "(run from inside a .weevr project so references resolve)"

# weevr-core raises WeevError for config problems, but some malformed input
# escapes as a plain exception: a file that is not UTF-8 (UnicodeDecodeError,
# a ValueError), or a non-string ref such as ``ref: 7`` (TypeError from
# pathlib). Treat these as a problem with the file rather than a crash.
LOAD_FAILURES: tuple[type[Exception], ...] = (WeevError, OSError, TypeError, ValueError)


def silence_weevr_logging() -> None:
    """Keep weevr-core's log output off the terminal.

    weevr-core logs load warnings as well as returning them. With no handler
    configured, Python prints those records raw to stderr. Commands that
    report the warnings as issues call this first.
    """
    logger = logging.getLogger("weevr")
    if not any(isinstance(handler, logging.NullHandler) for handler in logger.handlers):
        logger.addHandler(logging.NullHandler())


def _upgrade_hint() -> str:
    try:
        installed = version("weevr-core")
    except PackageNotFoundError:
        installed = "unknown"
    return (
        f"(weevr-core {installed} installed — if this is a newer weevr feature, "
        "upgrade: pip install --upgrade weevr-core)"
    )


def display_path(path: Path, project_root: Path | None) -> str:
    """Return ``path`` relative to the project root in POSIX form, if inside it."""
    if project_root is not None:
        try:
            return path.resolve().relative_to(project_root.resolve()).as_posix()
        except ValueError:
            pass
    return str(path)


def _issue_file(exc: WeevError, validated: Path, project_root: Path | None) -> str:
    """Pick the file an exception belongs to.

    weevr-core names the file it was loading when the error happened. For a
    bad ``ref:`` it names the ref string itself, which is not a real file, so
    the issue goes on the file being validated instead.
    """
    file_path = getattr(exc, "file_path", None)
    if file_path:
        candidate = Path(file_path)
        if candidate.is_absolute() and candidate.is_file():
            return display_path(candidate, project_root)
    return display_path(validated, project_root)


def _severity(exc: WeevError) -> Literal["error", "warning"]:
    if isinstance(exc, VariableResolutionError):
        return "warning"
    # A declared param with no runtime value is expected when validating
    # without a run context. weevr-core raises the same exception type for
    # structural errors, so match on the message; if the wording changes the
    # param is reported as an error, which is the safe direction.
    if (
        isinstance(exc, ConfigSchemaError)
        and exc.config_key is not None
        and "Required parameter" in exc.message
    ):
        return "warning"
    return "error"


def _is_unknown_field(error_type: str, message: str) -> bool:
    return error_type == "extra_forbidden" or "Extra inputs are not permitted" in message


def _issues_from_exception(
    exc: WeevError, validated: Path, project_root: Path | None
) -> list[ValidationIssue]:
    severity = _severity(exc)
    file = _issue_file(exc, validated, project_root)

    if isinstance(exc.cause, ValidationError):
        issues: list[ValidationIssue] = []
        for error in exc.cause.errors():
            message = error["msg"]
            if _is_unknown_field(error["type"], message):
                message = f"{message} {_upgrade_hint()}"
            location = ".".join(str(part) for part in error["loc"]) or None
            issues.append(ValidationIssue(severity, message, file, location))
        if issues:
            return issues

    message = exc.message
    if _is_unknown_field("", message):
        message = f"{message} {_upgrade_hint()}"
    if isinstance(exc, ReferenceResolutionError) and project_root is None:
        message = f"{message} {_NO_PROJECT_HINT}"
    location = exc.config_key if isinstance(exc, ConfigError) else None
    return [ValidationIssue(severity, message, file, location)]


def validate_file(path: Path, *, project_root: Path | None = None) -> list[ValidationIssue]:
    """Validate one weevr file by loading it through weevr-core.

    A weave or loom load also validates every child it references, so errors
    in a child come back attributed to the child's file.

    Args:
        path: The ``.thread``, ``.weave``, ``.loom``, or ``.warp`` file.
        project_root: The ``.weevr`` project directory. References resolve
            against it; without one they resolve against the file's directory.

    Returns:
        The issues found; empty when the file loads cleanly.
    """
    try:
        load_config(path, runtime_params=FABRIC_PLACEHOLDERS, project_root=project_root)
    except WeevError as exc:
        return _issues_from_exception(exc, path, project_root)
    except LOAD_FAILURES as exc:
        message = f"Cannot load file: {type(exc).__name__}: {exc}"
        return [ValidationIssue("error", message, display_path(path, project_root))]
    return []


def dedupe_issues(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    """Drop repeated issues, keeping the first of each.

    A broken thread is reported when it is validated and again for every
    weave that references it; all of those name the thread's file.
    """
    seen: set[tuple[str, str, str | None, str]] = set()
    unique: list[ValidationIssue] = []
    for issue in issues:
        key = (issue.severity, issue.file, issue.location, issue.message)
        if key not in seen:
            seen.add(key)
            unique.append(issue)
    return unique
