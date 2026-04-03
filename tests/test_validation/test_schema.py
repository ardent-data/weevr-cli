"""Tests for JSON schema validation of weevr files."""

from __future__ import annotations

from pathlib import Path

import pytest

from weevr_cli.validation.schema import validate_file


@pytest.fixture()
def valid_thread(tmp_path: Path) -> Path:
    """Create a minimal valid thread file."""
    f = tmp_path / "stg_customers.thread"
    f.write_text(
        'config_version: "1.0"\n'
        "sources:\n"
        "  raw_customers:\n"
        "    type: csv\n"
        "target:\n"
        "  path: Tables/stg_customers\n"
    )
    return f


@pytest.fixture()
def valid_weave(tmp_path: Path) -> Path:
    """Create a minimal valid weave file."""
    f = tmp_path / "staging.weave"
    f.write_text('config_version: "1.0"\nthreads:\n  - ref: staging/stg_customers.thread\n')
    return f


@pytest.fixture()
def valid_loom(tmp_path: Path) -> Path:
    """Create a minimal valid loom file."""
    f = tmp_path / "daily.loom"
    f.write_text('config_version: "1.0"\nweaves:\n  - ref: staging.weave\n')
    return f


def test_valid_thread_passes(valid_thread: Path) -> None:
    """A valid thread file produces no errors."""
    issues = validate_file(valid_thread)
    errors = [i for i in issues if i.severity == "error"]
    assert errors == []


def test_valid_weave_passes(valid_weave: Path) -> None:
    """A valid weave file produces no errors."""
    issues = validate_file(valid_weave)
    errors = [i for i in issues if i.severity == "error"]
    assert errors == []


def test_valid_loom_passes(valid_loom: Path) -> None:
    """A valid loom file produces no errors."""
    issues = validate_file(valid_loom)
    errors = [i for i in issues if i.severity == "error"]
    assert errors == []


def test_invalid_thread_missing_config_version(tmp_path: Path) -> None:
    """Missing config_version produces a schema error."""
    f = tmp_path / "bad.thread"
    f.write_text("sources:\n  raw:\n    type: csv\ntarget:\n  path: Tables/raw\n")
    issues = validate_file(f)
    errors = [i for i in issues if i.severity == "error"]
    assert len(errors) >= 1
    assert any("config_version" in e.message for e in errors)


def test_malformed_yaml(tmp_path: Path) -> None:
    """Unparseable YAML produces an error."""
    f = tmp_path / "broken.thread"
    f.write_text(":\n  - :\n  bad: [unclosed")
    issues = validate_file(f)
    errors = [i for i in issues if i.severity == "error"]
    assert len(errors) >= 1
    assert any("yaml" in e.message.lower() or "parse" in e.message.lower() for e in errors)


def test_unknown_extension(tmp_path: Path) -> None:
    """File without recognized extension produces an error."""
    f = tmp_path / "readme.txt"
    f.write_text("hello")
    issues = validate_file(f)
    errors = [i for i in issues if i.severity == "error"]
    assert len(errors) >= 1
    assert any("extension" in e.message.lower() or "type" in e.message.lower() for e in errors)
