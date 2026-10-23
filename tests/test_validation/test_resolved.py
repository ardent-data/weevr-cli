"""Tests for the resolved-children loader."""

from __future__ import annotations

from pathlib import Path

from weevr.model import Thread

from weevr_cli.validation.resolved import load_resolved


def test_load_resolved_returns_typed_threads_with_fabric_placeholders(tmp_path: Path) -> None:
    (tmp_path / "a.thread").write_text(
        'config_version: "1.0"\n'
        "sources: {main: {type: delta, alias: silver.raw}}\n"
        'target: {path: "abfss://${fabric.workspace_id}@x/Tables/a"}\n'
    )
    (tmp_path / "w.weave").write_text('config_version: "1.0"\nthreads:\n  - ref: a.thread\n')

    loaded = load_resolved(tmp_path / "w.weave", project_root=tmp_path)

    thread = loaded.resolved_threads["w"]["a"]
    assert isinstance(thread, Thread)
    assert thread.target.path == "abfss://<fabric.workspace_id>@x/Tables/a"
