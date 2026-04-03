"""Dependency graph builder for weevr project files."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

import yaml

from weevr_cli.listing.models import DependencyGraph, GraphNode
from weevr_cli.validation.refs import _extract_refs

logger = logging.getLogger(__name__)

WEEVR_EXTENSIONS: dict[str, Literal["thread", "weave", "loom"]] = {
    ".thread": "thread",
    ".weave": "weave",
    ".loom": "loom",
}


def build_dependency_graph(project_root: Path) -> DependencyGraph:
    """Build a dependency graph from weevr project files.

    Scans the project root recursively for .thread, .weave, and .loom files,
    parses their YAML content, extracts references, and builds a directed graph.

    Args:
        project_root: Root directory of the weevr project.

    Returns:
        A DependencyGraph with all discovered nodes and edges.
    """
    # Scan for weevr files
    file_data: dict[str, tuple[Literal["thread", "weave", "loom"], dict[str, Any]]] = {}

    for ext, file_type in WEEVR_EXTENSIONS.items():
        for path in sorted(project_root.rglob(f"*{ext}")):
            if not path.is_file():
                continue
            relative = path.relative_to(project_root).as_posix()
            try:
                text = path.read_text(encoding="utf-8")
                data = yaml.safe_load(text)
            except (yaml.YAMLError, OSError):
                logger.warning("Skipping unparseable file: %s", relative)
                continue
            if not isinstance(data, dict):
                logger.warning("Skipping non-mapping file: %s", relative)
                continue
            file_data[relative] = (file_type, data)

    # Build nodes with refs_out
    nodes: dict[str, GraphNode] = {}
    for relative, (file_type, data) in file_data.items():
        refs = _extract_refs(data, relative)
        refs_out = [ref_value for ref_value, _, _ in refs]
        nodes[relative] = GraphNode(
            path=relative,
            file_type=file_type,
            refs_out=refs_out,
            refs_in=[],
            is_orphan=False,
        )

    # Compute refs_in by inverting refs_out edges
    for node in nodes.values():
        for ref_target in node.refs_out:
            target_node = nodes.get(ref_target)
            if target_node is not None:
                target_node.refs_in.append(node.path)

    # Compute orphan status
    for node in nodes.values():
        if node.file_type != "loom" and len(node.refs_in) == 0:
            node.is_orphan = True

    return DependencyGraph(nodes=nodes)
