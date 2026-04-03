"""Tests for the listing data models."""

from __future__ import annotations

from weevr_cli.listing.models import DependencyGraph, GraphNode


class TestGraphNode:
    """Tests for GraphNode construction."""

    def test_basic_construction(self) -> None:
        node = GraphNode(
            path="threads/raw.thread",
            file_type="thread",
            refs_out=[],
            refs_in=["weaves/customer.weave"],
            is_orphan=False,
        )
        assert node.path == "threads/raw.thread"
        assert node.file_type == "thread"
        assert node.refs_out == []
        assert node.refs_in == ["weaves/customer.weave"]
        assert node.is_orphan is False

    def test_orphan_node(self) -> None:
        node = GraphNode(
            path="threads/unused.thread",
            file_type="thread",
            refs_out=[],
            refs_in=[],
            is_orphan=True,
        )
        assert node.is_orphan is True


class TestDependencyGraph:
    """Tests for DependencyGraph."""

    def _make_graph(self) -> DependencyGraph:
        return DependencyGraph(
            nodes={
                "looms/daily.loom": GraphNode(
                    path="looms/daily.loom",
                    file_type="loom",
                    refs_out=["weaves/customer.weave"],
                    refs_in=[],
                    is_orphan=False,
                ),
                "weaves/customer.weave": GraphNode(
                    path="weaves/customer.weave",
                    file_type="weave",
                    refs_out=["threads/raw.thread"],
                    refs_in=["looms/daily.loom"],
                    is_orphan=False,
                ),
                "threads/raw.thread": GraphNode(
                    path="threads/raw.thread",
                    file_type="thread",
                    refs_out=[],
                    refs_in=["weaves/customer.weave"],
                    is_orphan=False,
                ),
                "threads/orphan.thread": GraphNode(
                    path="threads/orphan.thread",
                    file_type="thread",
                    refs_out=[],
                    refs_in=[],
                    is_orphan=True,
                ),
            }
        )

    def test_looms_returns_only_loom_nodes(self) -> None:
        graph = self._make_graph()
        looms = graph.looms
        assert len(looms) == 1
        assert looms[0].file_type == "loom"
        assert looms[0].path == "looms/daily.loom"

    def test_orphans_returns_non_loom_with_no_refs_in(self) -> None:
        graph = self._make_graph()
        orphans = graph.orphans
        assert len(orphans) == 1
        assert orphans[0].path == "threads/orphan.thread"

    def test_looms_are_never_orphans(self) -> None:
        graph = DependencyGraph(
            nodes={
                "looms/solo.loom": GraphNode(
                    path="looms/solo.loom",
                    file_type="loom",
                    refs_out=[],
                    refs_in=[],
                    is_orphan=False,
                ),
            }
        )
        assert graph.orphans == []

    def test_refs_for_returns_refs_out(self) -> None:
        graph = self._make_graph()
        refs = graph.refs_for("weaves/customer.weave")
        assert refs == ["threads/raw.thread"]

    def test_refs_for_unknown_path_returns_empty(self) -> None:
        graph = self._make_graph()
        assert graph.refs_for("nonexistent.thread") == []

    def test_empty_graph(self) -> None:
        graph = DependencyGraph(nodes={})
        assert graph.looms == []
        assert graph.orphans == []
