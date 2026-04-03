"""Validation result data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ValidationIssue:
    """A single validation finding.

    Attributes:
        severity: Either "error" or "warning".
        message: Human-readable description of the issue.
        file: Path to the file where the issue was found.
        location: Optional JSON-path-like location within the file.
    """

    severity: Literal["error", "warning"]
    message: str
    file: str
    location: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary."""
        return {
            "severity": self.severity,
            "file": self.file,
            "message": self.message,
            "location": self.location,
        }


@dataclass
class ValidationResult:
    """Aggregated validation outcome across one or more files.

    Attributes:
        issues: All validation issues found.
        files_checked: Number of files that were validated.
    """

    issues: list[ValidationIssue] = field(default_factory=list)
    files_checked: int = 0

    @property
    def errors(self) -> list[ValidationIssue]:
        """Return only error-severity issues."""
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Return only warning-severity issues."""
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def is_valid(self) -> bool:
        """True if there are no errors."""
        return len(self.errors) == 0

    def apply_strict(self) -> None:
        """Promote all warnings to errors."""
        for issue in self.issues:
            if issue.severity == "warning":
                issue.severity = "error"

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON output contract structure."""
        return {
            "valid": self.is_valid,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "files_checked": self.files_checked,
            "issues": [i.to_dict() for i in self.issues],
        }
