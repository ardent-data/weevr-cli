"""Load a weave or loom together with its resolved children."""

from __future__ import annotations

from pathlib import Path

from weevr.config import load_resolved as _core_load_resolved
from weevr.result import LoadedConfig

from weevr_cli.validation.engine import FABRIC_PLACEHOLDERS


def load_resolved(path: Path, *, project_root: Path | None = None) -> LoadedConfig:
    """Load a thread, weave, or loom with its hydrated child threads and weaves.

    Runs the same load as validation, with the same Fabric placeholders, and
    keeps the children weevr-core resolved so plans can be built from them.

    Args:
        path: The ``.thread``, ``.weave``, or ``.loom`` file.
        project_root: The ``.weevr`` project directory; defaults to the file's
            directory.

    Returns:
        The loaded config with ``resolved_threads``, ``resolved_weaves``,
        ``warnings``, and ``execution_plan``.

    Raises:
        weevr.errors.WeevError: If the config fails to load.
    """
    return _core_load_resolved(path, runtime_params=FABRIC_PLACEHOLDERS, project_root=project_root)
