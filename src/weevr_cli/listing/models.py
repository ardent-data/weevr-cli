"""Data models for the listing engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class GraphNode:
    """A single file node in the dependency graph."""

    path: str
    file_type: Literal["thread", "weave", "loom", "warp"]
    refs_out: list[str] = field(default_factory=list)
    refs_in: list[str] = field(default_factory=list)
    is_orphan: bool = False


@dataclass
class DependencyGraph:
    """Directed dependency graph of weevr project files."""

    nodes: dict[str, GraphNode] = field(default_factory=dict)

    @property
    def looms(self) -> list[GraphNode]:
        """Return all loom nodes, sorted by path."""
        return sorted(
            (n for n in self.nodes.values() if n.file_type == "loom"),
            key=lambda n: n.path,
        )

    @property
    def orphans(self) -> list[GraphNode]:
        """Return non-loom nodes with no incoming references."""
        return sorted(
            (n for n in self.nodes.values() if n.is_orphan),
            key=lambda n: n.path,
        )

    def refs_for(self, path: str) -> list[str]:
        """Return outgoing references for a given file path."""
        node = self.nodes.get(path)
        if node is None:
            return []
        return node.refs_out
