"""Tests for schema resolution logic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from weevr_cli.validation.resolver import resolve_schema


def test_resolve_bundled_thread() -> None:
    """Bundled thread schema is returned when no local override."""
    path = resolve_schema("thread")
    assert path.exists()
    assert path.name == "thread.json"
    data = json.loads(path.read_text())
    assert "$defs" in data or "properties" in data


def test_resolve_bundled_weave() -> None:
    """Bundled weave schema is returned when no local override."""
    path = resolve_schema("weave")
    assert path.exists()
    assert path.name == "weave.json"


def test_resolve_bundled_loom() -> None:
    """Bundled loom schema is returned when no local override."""
    path = resolve_schema("loom")
    assert path.exists()
    assert path.name == "loom.json"


def test_resolve_local_override(tmp_path: Path) -> None:
    """Local schema in .weevr/schemas/ takes priority over bundled."""
    project_root = tmp_path / "test.weevr"
    project_root.mkdir()
    schemas_dir = project_root / ".weevr" / "schemas"
    schemas_dir.mkdir(parents=True)
    local_schema = schemas_dir / "thread.json"
    local_schema.write_text(json.dumps({"type": "object", "custom": True}))

    path = resolve_schema("thread", project_root=project_root)
    assert path == local_schema
    data = json.loads(path.read_text())
    assert data["custom"] is True


def test_resolve_local_missing_falls_back(tmp_path: Path) -> None:
    """Falls back to bundled when local schemas dir exists but type is absent."""
    project_root = tmp_path / "test.weevr"
    project_root.mkdir()
    schemas_dir = project_root / ".weevr" / "schemas"
    schemas_dir.mkdir(parents=True)
    # No thread.json in local dir

    path = resolve_schema("thread", project_root=project_root)
    assert path.exists()
    assert "weevr_cli" in str(path)  # bundled path


def test_resolve_bundled_warp() -> None:
    """Bundled warp schema is returned when no local override."""
    path = resolve_schema("warp")
    assert path.exists()
    assert path.name == "warp.json"


def test_resolve_unknown_type() -> None:
    """Unknown file type raises ValueError."""
    with pytest.raises(ValueError, match="Unknown schema type"):
        resolve_schema("pipeline")
