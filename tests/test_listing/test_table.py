"""Tests for the table view renderer."""

from __future__ import annotations

from weevr_cli.listing.models import DependencyGraph, GraphNode
from weevr_cli.listing.table import render_table_json


def _make_graph() -> DependencyGraph:
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


class TestRenderTableJson:
    """Tests for render_table_json."""

    def test_correct_file_count(self) -> None:
        result = render_table_json(_make_graph())
        assert result["format"] == "table"
        assert result["total_files"] == 4

    def test_orphan_count(self) -> None:
        result = render_table_json(_make_graph())
        assert result["orphan_count"] == 1

    def test_orphan_row_status(self) -> None:
        result = render_table_json(_make_graph())
        orphan_rows = [f for f in result["files"] if f["status"] == "orphan"]
        assert len(orphan_rows) == 1
        assert orphan_rows[0]["path"] == "threads/orphan.thread"

    def test_loom_always_connected(self) -> None:
        result = render_table_json(_make_graph())
        loom_rows = [f for f in result["files"] if f["type"] == "loom"]
        assert all(f["status"] == "connected" for f in loom_rows)

    def test_ref_counts_accurate(self) -> None:
        result = render_table_json(_make_graph())
        files_by_path = {f["path"]: f for f in result["files"]}

        loom = files_by_path["looms/daily.loom"]
        assert loom["refs_in"] == 0
        assert loom["refs_out"] == 1

        weave = files_by_path["weaves/customer.weave"]
        assert weave["refs_in"] == 1
        assert weave["refs_out"] == 1

        thread = files_by_path["threads/raw.thread"]
        assert thread["refs_in"] == 1
        assert thread["refs_out"] == 0

    def test_sorted_by_type_then_path(self) -> None:
        result = render_table_json(_make_graph())
        types = [f["type"] for f in result["files"]]
        # loom first, then weave, then threads
        assert types == ["loom", "weave", "thread", "thread"]
