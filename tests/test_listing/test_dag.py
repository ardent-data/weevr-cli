"""Tests for the execution plan (DAG) view."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from rich.console import Console
from typer.testing import CliRunner

from weevr_cli.cli import app
from weevr_cli.listing.dag import DagError, build_weave_plans, render_dag, render_dag_json
from weevr_cli.listing.graph import build_dependency_graph

runner = CliRunner()


def _thread(source: str, target: str) -> dict:  # type: ignore[type-arg]
    return {
        "config_version": "1.0",
        "sources": {"main": {"type": "delta", "alias": source}},
        "target": {"alias": target},
    }


def _write(path: Path, data: dict) -> None:  # type: ignore[type-arg]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data), encoding="utf-8")


def _make_project(tmp_path: Path) -> Path:
    """Weave with a -> b, a -> c (inferred), and c -> d (explicit)."""
    project = tmp_path / "test.weevr"
    (project / ".weevr").mkdir(parents=True)
    (project / ".weevr" / "cli.yaml").write_text(
        yaml.dump({"targets": {"dev": {"workspace_id": "ws-1", "lakehouse_id": "lh-1"}}})
    )
    _write(project / "staging" / "a.thread", _thread("bronze.raw", "silver.a"))
    _write(project / "staging" / "b.thread", _thread("silver.a", "silver.b"))
    _write(project / "staging" / "c.thread", _thread("silver.a", "silver.c"))
    _write(project / "staging" / "d.thread", _thread("bronze.other", "silver.d"))
    _write(
        project / "staging.weave",
        {
            "config_version": "1.0",
            "threads": [
                {"ref": "staging/a.thread"},
                {"ref": "staging/b.thread"},
                {"ref": "staging/c.thread"},
                {"ref": "staging/d.thread", "dependencies": ["c"]},
            ],
        },
    )
    return project


def test_build_weave_plans_groups_and_dependencies(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    plans = build_weave_plans(project, build_dependency_graph(project))
    assert [(p.file, p.weave) for p in plans] == [("staging.weave", "staging")]
    plan = plans[0].plan
    assert plan.execution_order == [["a"], ["b", "c"], ["d"]]
    assert plan.cache_targets == ["a"]


def test_render_dag_json(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    data = render_dag_json(build_weave_plans(project, build_dependency_graph(project)))
    weave = data["weaves"][0]
    assert weave["weave"] == "staging"
    assert weave["file"] == "staging.weave"
    assert weave["execution_order"] == [["a"], ["b", "c"], ["d"]]
    assert weave["dependencies"]["b"] == [{"thread": "a", "kind": "inferred"}]
    assert weave["dependencies"]["d"] == [{"thread": "c", "kind": "explicit"}]
    assert weave["dependencies"]["a"] == []
    assert weave["cache_targets"] == ["a"]
    assert weave["lookup_schedule"] is None


def test_render_dag_rich(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    console = Console(record=True, width=120)
    render_dag(build_weave_plans(project, build_dependency_graph(project)), console)
    text = console.export_text()
    assert "staging.weave" in text
    assert "Group 1" in text and "Group 3" in text
    assert "b ← a (inferred)" in text
    assert "d ← c (explicit)" in text
    assert "cached" in text


def test_loom_inline_weave_is_listed_under_loom(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    _write(
        project / "daily.loom",
        {
            "config_version": "1.0",
            "weaves": [
                {"ref": "staging.weave"},
                {
                    "name": "extra",
                    "config_version": "1.0",
                    "threads": [{"ref": "staging/d.thread"}],
                },
            ],
        },
    )
    plans = build_weave_plans(project, build_dependency_graph(project))
    assert [(p.file, p.weave) for p in plans] == [
        ("staging.weave", "staging"),
        ("daily.loom", "extra"),
    ]


def test_planner_failure_raises_dag_error(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    _write(project / "staging" / "b.thread", _thread("silver.a", "silver.a"))
    with pytest.raises(DagError, match="staging.weave"):
        build_weave_plans(project, build_dependency_graph(project))


def test_list_dag_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["--json", "list", "--format", "dag"])
    assert result.exit_code == 0
    assert json.loads(result.output)["weaves"][0]["execution_order"][0] == ["a"]


def test_list_dag_command_failure_exits_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _make_project(tmp_path)
    _write(project / "staging" / "b.thread", {"config_version": "1.0", "sources": {}})
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["list", "--format", "dag"])
    assert result.exit_code == 1


def test_unloadable_loom_raises_dag_error(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    (project / "num.loom").write_text('config_version: "1.0"\nweaves:\n  - ref: 7\n')
    with pytest.raises(DagError, match="num.loom"):
        build_weave_plans(project, build_dependency_graph(project))
