"""Tests for ValidationResult and ValidationIssue data structures."""

from __future__ import annotations

from weevr_cli.validation.results import ValidationIssue, ValidationResult


def test_validation_result_empty() -> None:
    """Empty result is valid with no issues."""
    result = ValidationResult(issues=[], files_checked=0)
    assert result.is_valid
    assert result.errors == []
    assert result.warnings == []


def test_validation_result_with_errors() -> None:
    """Result with errors is not valid."""
    issues = [
        ValidationIssue(
            severity="error",
            message="Missing required field: config_version",
            file="staging/stg_customers.thread",
        ),
    ]
    result = ValidationResult(issues=issues, files_checked=1)
    assert not result.is_valid
    assert len(result.errors) == 1
    assert len(result.warnings) == 0


def test_validation_result_with_warnings() -> None:
    """Result with only warnings is still valid."""
    issues = [
        ValidationIssue(
            severity="warning",
            message="Orphaned file: not referenced by any weave or loom",
            file="old/unused.thread",
        ),
    ]
    result = ValidationResult(issues=issues, files_checked=1)
    assert result.is_valid
    assert len(result.errors) == 0
    assert len(result.warnings) == 1


def test_strict_mode() -> None:
    """apply_strict promotes warnings to errors."""
    issues = [
        ValidationIssue(
            severity="warning",
            message="Orphaned file",
            file="old/unused.thread",
        ),
    ]
    result = ValidationResult(issues=issues, files_checked=1)
    assert result.is_valid

    result.apply_strict()
    assert not result.is_valid
    assert len(result.errors) == 1
    assert len(result.warnings) == 0
    assert result.issues[0].severity == "error"


def test_validation_issue_location() -> None:
    """ValidationIssue supports optional location field."""
    issue = ValidationIssue(
        severity="error",
        message="Invalid type",
        file="test.thread",
        location="sources.raw_customers.type",
    )
    assert issue.location == "sources.raw_customers.type"


def test_validation_result_to_dict() -> None:
    """to_dict produces the expected JSON-serializable structure."""
    issues = [
        ValidationIssue(severity="error", message="Bad field", file="a.thread"),
        ValidationIssue(severity="warning", message="Orphan", file="b.thread"),
    ]
    result = ValidationResult(issues=issues, files_checked=5)
    data = result.to_dict()
    assert data["valid"] is False
    assert data["errors"] == 1
    assert data["warnings"] == 1
    assert data["files_checked"] == 5
    assert len(data["issues"]) == 2
    assert data["issues"][0]["severity"] == "error"
