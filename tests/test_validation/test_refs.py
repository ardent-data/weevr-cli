"""Tests for reference integrity checking."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from weevr_cli.validation.refs import check_refs, find_orphans

# Minimal valid YAML content for each file type.
_THREAD = 'config_version: "1.0"\nsources:\n  raw:\n    type: csv\ntarget:\n  path: Tables/raw\n'
_WEAVE = 'config_version: "1.0"\nthreads:\n  - ref: staging/stg_customers.thread\n'
_LOOM = 'config_version: "1.0"\nweaves:\n  - ref: staging.weave\n'


def _make_project(tmp_path: Path, files: dict[str, str]) -> Path:
    """Create a .weevr project directory with given files."""
    project = tmp_path / "test.weevr"
    project.mkdir()
    weevr_dir = project / ".weevr"
    weevr_dir.mkdir()
    for rel_path, content in files.items():
        f = project / rel_path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)
    return project


def _parse_files(project: Path) -> dict[str, Any]:
    """Parse all weevr files in the project into {rel_path: data}."""
    result: dict[str, Any] = {}
    for ext in (".thread", ".weave", ".loom"):
        for f in project.rglob(f"*{ext}"):
            rel = str(f.relative_to(project))
            result[rel] = yaml.safe_load(f.read_text()) or {}
    return result


def test_valid_refs(tmp_path: Path) -> None:
    """All refs point to existing files — no errors."""
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": _THREAD,
            "staging.weave": _WEAVE,
            "daily.loom": _LOOM,
        },
    )
    files = _parse_files(project)
    issues = check_refs(files, project)
    errors = [i for i in issues if i.severity == "error"]
    assert errors == []


def test_broken_ref(tmp_path: Path) -> None:
    """Ref to non-existent file produces error."""
    weave = 'config_version: "1.0"\nthreads:\n  - ref: staging/missing.thread\n'
    project = _make_project(
        tmp_path,
        {
            "staging.weave": weave,
        },
    )
    files = _parse_files(project)
    issues = check_refs(files, project)
    errors = [i for i in issues if i.severity == "error"]
    assert len(errors) == 1
    assert "missing.thread" in errors[0].message


def test_path_traversal_rejected(tmp_path: Path) -> None:
    """Ref containing ../ produces error."""
    weave = 'config_version: "1.0"\nthreads:\n  - ref: ../outside.thread\n'
    project = _make_project(tmp_path, {"staging.weave": weave})
    files = _parse_files(project)
    issues = check_refs(files, project)
    errors = [i for i in issues if i.severity == "error"]
    assert len(errors) == 1
    assert ".." in errors[0].message


def test_orphaned_thread(tmp_path: Path) -> None:
    """Thread not referenced by any weave produces warning."""
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": _THREAD,
            "staging/stg_orders.thread": _THREAD,
            "staging.weave": _WEAVE,
            "daily.loom": _LOOM,
        },
    )
    files = _parse_files(project)
    all_paths = list(files.keys())
    issues = find_orphans(files, all_paths)
    warnings = [i for i in issues if i.severity == "warning"]
    assert len(warnings) == 1
    assert "stg_orders.thread" in warnings[0].file


def test_orphaned_weave(tmp_path: Path) -> None:
    """Weave not referenced by any loom produces warning."""
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": _THREAD,
            "staging.weave": _WEAVE,
        },
    )
    files = _parse_files(project)
    all_paths = list(files.keys())
    issues = find_orphans(files, all_paths)
    warnings = [i for i in issues if i.severity == "warning"]
    assert len(warnings) == 1
    assert "staging.weave" in warnings[0].file


def test_loom_not_orphan(tmp_path: Path) -> None:
    """Loom files are top-level entry points — never reported as orphans."""
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": _THREAD,
            "staging.weave": _WEAVE,
            "daily.loom": _LOOM,
        },
    )
    files = _parse_files(project)
    all_paths = list(files.keys())
    issues = find_orphans(files, all_paths)
    orphan_files = [i.file for i in issues]
    assert not any("loom" in f for f in orphan_files)


def test_no_orphans(tmp_path: Path) -> None:
    """When all threads/weaves are referenced, no orphan warnings."""
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": _THREAD,
            "staging.weave": _WEAVE,
            "daily.loom": _LOOM,
        },
    )
    files = _parse_files(project)
    all_paths = list(files.keys())
    issues = find_orphans(files, all_paths)
    assert issues == []
