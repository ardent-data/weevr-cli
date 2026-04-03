"""Tests for the tree view renderer."""

from __future__ import annotations

from weevr_cli.listing.models import DependencyGraph, GraphNode
from weevr_cli.listing.tree import render_tree_json


def _make_chain_graph() -> DependencyGraph:
    """Simple loom → weave → thread chain."""
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
        }
    )


class TestRenderTreeJson:
    """Tests for render_tree_json."""

    def test_simple_chain(self) -> None:
        graph = _make_chain_graph()
        result = render_tree_json(graph)

        assert result["format"] == "tree"
        assert result["total_files"] == 3
        assert result["orphan_count"] == 0
        assert len(result["roots"]) == 1

        root = result["roots"][0]
        assert root["path"] == "looms/daily.loom"
        assert root["type"] == "loom"
        assert len(root["children"]) == 1

        weave = root["children"][0]
        assert weave["path"] == "weaves/customer.weave"
        assert len(weave["children"]) == 1

        thread = weave["children"][0]
        assert thread["path"] == "threads/raw.thread"
        assert thread["children"] == []

    def test_multi_ref_thread_appears_under_both_weaves(self) -> None:
        graph = DependencyGraph(
            nodes={
                "looms/daily.loom": GraphNode(
                    path="looms/daily.loom",
                    file_type="loom",
                    refs_out=["weaves/a.weave", "weaves/b.weave"],
                    refs_in=[],
                    is_orphan=False,
                ),
                "weaves/a.weave": GraphNode(
                    path="weaves/a.weave",
                    file_type="weave",
                    refs_out=["threads/shared.thread"],
                    refs_in=["looms/daily.loom"],
                    is_orphan=False,
                ),
                "weaves/b.weave": GraphNode(
                    path="weaves/b.weave",
                    file_type="weave",
                    refs_out=["threads/shared.thread"],
                    refs_in=["looms/daily.loom"],
                    is_orphan=False,
                ),
                "threads/shared.thread": GraphNode(
                    path="threads/shared.thread",
                    file_type="thread",
                    refs_out=[],
                    refs_in=["weaves/a.weave", "weaves/b.weave"],
                    is_orphan=False,
                ),
            }
        )
        result = render_tree_json(graph)
        root = result["roots"][0]
        # Thread appears under both weaves
        assert root["children"][0]["children"][0]["path"] == "threads/shared.thread"
        assert root["children"][1]["children"][0]["path"] == "threads/shared.thread"

    def test_orphan_in_unreferenced(self) -> None:
        graph = DependencyGraph(
            nodes={
                "threads/orphan.thread": GraphNode(
                    path="threads/orphan.thread",
                    file_type="thread",
                    refs_out=[],
                    refs_in=[],
                    is_orphan=True,
                ),
            }
        )
        result = render_tree_json(graph)
        assert result["orphan_count"] == 1
        assert result["unreferenced"][0]["path"] == "threads/orphan.thread"
        assert result["roots"] == []

    def test_empty_graph(self) -> None:
        graph = DependencyGraph(nodes={})
        result = render_tree_json(graph)
        assert result["total_files"] == 0
        assert result["orphan_count"] == 0
        assert result["roots"] == []
        assert result["unreferenced"] == []
