"""Tests for the dependency graph builder."""

from __future__ import annotations

from pathlib import Path

import yaml

from weevr_cli.listing.graph import build_dependency_graph


def _write_yaml(path: Path, data: dict) -> None:  # type: ignore[type-arg]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data), encoding="utf-8")


class TestBuildDependencyGraph:
    """Tests for build_dependency_graph."""

    def test_simple_chain(self, tmp_path: Path) -> None:
        """loom → weave → thread — all connected, no orphans."""
        root = tmp_path / "project.weevr"
        _write_yaml(root / "threads" / "raw.thread", {"name": "raw"})
        _write_yaml(
            root / "weaves" / "customer.weave",
            {"name": "customer", "threads": [{"ref": "threads/raw.thread"}]},
        )
        _write_yaml(
            root / "looms" / "daily.loom",
            {"name": "daily", "weaves": [{"ref": "weaves/customer.weave"}]},
        )

        graph = build_dependency_graph(root)
        assert len(graph.nodes) == 3
        assert graph.orphans == []
        assert len(graph.looms) == 1

        loom_node = graph.nodes["looms/daily.loom"]
        assert loom_node.refs_out == ["weaves/customer.weave"]

        weave_node = graph.nodes["weaves/customer.weave"]
        assert weave_node.refs_out == ["threads/raw.thread"]
        assert "looms/daily.loom" in weave_node.refs_in

        thread_node = graph.nodes["threads/raw.thread"]
        assert "weaves/customer.weave" in thread_node.refs_in

    def test_multi_ref_same_thread(self, tmp_path: Path) -> None:
        """A weave references the same thread twice → refs_in count is 2."""
        root = tmp_path / "project.weevr"
        _write_yaml(root / "threads" / "raw.thread", {"name": "raw"})
        _write_yaml(
            root / "weaves" / "double.weave",
            {
                "name": "double",
                "threads": [
                    {"ref": "threads/raw.thread"},
                    {"ref": "threads/raw.thread"},
                ],
            },
        )

        graph = build_dependency_graph(root)
        thread_node = graph.nodes["threads/raw.thread"]
        assert len(thread_node.refs_in) == 2

    def test_orphan_detection(self, tmp_path: Path) -> None:
        """Thread not referenced by any weave → flagged as orphan."""
        root = tmp_path / "project.weevr"
        _write_yaml(root / "threads" / "orphan.thread", {"name": "orphan"})

        graph = build_dependency_graph(root)
        assert len(graph.orphans) == 1
        assert graph.orphans[0].path == "threads/orphan.thread"
        assert graph.orphans[0].is_orphan is True

    def test_loom_with_no_refs_not_orphan(self, tmp_path: Path) -> None:
        """Loom with no references is never an orphan."""
        root = tmp_path / "project.weevr"
        _write_yaml(root / "looms" / "empty.loom", {"name": "empty"})

        graph = build_dependency_graph(root)
        assert graph.orphans == []
        assert graph.nodes["looms/empty.loom"].is_orphan is False

    def test_warp_with_no_refs_not_orphan(self, tmp_path: Path) -> None:
        """Warp with no references is never an orphan."""
        root = tmp_path / "project.weevr"
        _write_yaml(
            root / "schemas" / "customers.warp",
            {"config_version": "1.0", "columns": [{"name": "id", "type": "bigint"}]},
        )

        graph = build_dependency_graph(root)
        assert graph.orphans == []
        assert graph.nodes["schemas/customers.warp"].is_orphan is False

    def test_broken_ref_no_crash(self, tmp_path: Path) -> None:
        """Weave references non-existent thread → ref recorded, no crash."""
        root = tmp_path / "project.weevr"
        _write_yaml(
            root / "weaves" / "broken.weave",
            {"name": "broken", "threads": [{"ref": "threads/missing.thread"}]},
        )

        graph = build_dependency_graph(root)
        weave_node = graph.nodes["weaves/broken.weave"]
        assert "threads/missing.thread" in weave_node.refs_out
        # Missing target doesn't create a node
        assert "threads/missing.thread" not in graph.nodes

    def test_malformed_yaml_skipped(self, tmp_path: Path) -> None:
        """Malformed YAML is skipped; other files still processed."""
        root = tmp_path / "project.weevr"
        # Good file
        _write_yaml(root / "threads" / "good.thread", {"name": "good"})
        # Bad file
        bad = root / "threads" / "bad.thread"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text(": : invalid yaml {{{{", encoding="utf-8")

        graph = build_dependency_graph(root)
        assert "threads/good.thread" in graph.nodes
        assert "threads/bad.thread" not in graph.nodes

    def test_empty_project(self, tmp_path: Path) -> None:
        """Project with no weevr files → empty graph."""
        root = tmp_path / "project.weevr"
        root.mkdir()

        graph = build_dependency_graph(root)
        assert len(graph.nodes) == 0
        assert graph.looms == []
        assert graph.orphans == []
