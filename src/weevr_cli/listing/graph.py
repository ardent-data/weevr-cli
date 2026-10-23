"""Dependency graph builder for weevr project files."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal, cast

import pathspec
import yaml
from weevr.config.parser import TYPED_EXTENSIONS

from weevr_cli.listing.models import DependencyGraph, GraphNode
from weevr_cli.validation.orphans import extract_refs, normalize_ref

logger = logging.getLogger(__name__)

FileType = Literal["thread", "weave", "loom", "warp"]


def build_dependency_graph(
    project_root: Path,
    *,
    ignore_spec: pathspec.PathSpec | None = None,
) -> DependencyGraph:
    """Build a dependency graph from weevr project files.

    Scans the project root recursively for .thread, .weave, .loom, and .warp files,
    parses their YAML content, extracts references, and builds a directed graph.

    Args:
        project_root: Root directory of the weevr project.
        ignore_spec: Optional compiled ignore patterns. Files whose
            project-relative path matches any pattern are skipped.

    Returns:
        A DependencyGraph with all discovered nodes and edges.
    """
    # Scan for weevr files
    file_data: dict[str, tuple[FileType, dict[str, Any]]] = {}

    for ext, config_type in TYPED_EXTENSIONS.items():
        file_type = cast(FileType, config_type)
        for path in sorted(project_root.rglob(f"*{ext}")):
            if not path.is_file():
                continue
            relative = path.relative_to(project_root).as_posix()
            if ignore_spec is not None and ignore_spec.match_file(relative):
                continue
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
        refs = extract_refs(data, relative)
        # Normalize refs to project-root-relative POSIX form so lookups
        # against `nodes` (keyed by .as_posix()) succeed regardless of
        # whether the YAML uses a leading '/' or backslash separators.
        refs_out = [normalize_ref(ref_value) for ref_value, _, _ in refs]
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

    # Compute orphan status (looms and warps are standalone — never orphans)
    for node in nodes.values():
        if node.file_type not in ("loom", "warp") and len(node.refs_in) == 0:
            node.is_orphan = True

    return DependencyGraph(nodes=nodes)
