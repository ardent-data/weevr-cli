"""Implementation of the weevr new command."""

from __future__ import annotations

from pathlib import Path

from weevr_cli.output import print_error, print_json
from weevr_cli.state import AppState
from weevr_cli.templates import VALID_TYPES, get_template


def new_file(
    file_type: str,
    name: str,
    *,
    force: bool = False,
    state: AppState,
) -> None:
    """Generate a new weevr file from a template.

    Args:
        file_type: One of "thread", "weave", or "loom".
        name: Name for the new file (without extension).
        force: Whether to overwrite an existing file.
        state: Application state with console and json_mode.
    """
    if file_type not in VALID_TYPES:
        valid = ", ".join(VALID_TYPES)
        print_error(
            f"Invalid file type: '{file_type}'. Must be one of: {valid}.",
            "invalid_type",
            json_mode=state.json_mode,
            console=state.console,
        )
        raise SystemExit(1)

    filename = f"{name}.{file_type}"
    file_path = Path(filename)

    if file_path.exists() and not force:
        print_error(
            f"File already exists: {filename}. Use --force to overwrite.",
            "file_exists",
            json_mode=state.json_mode,
            console=state.console,
        )
        raise SystemExit(1)

    template = get_template(file_type)
    content = template.format(name=name)

    try:
        file_path.write_text(content, encoding="utf-8")
    except OSError as exc:
        print_error(
            f"Failed to create file: {exc}",
            "filesystem_error",
            json_mode=state.json_mode,
            console=state.console,
        )
        raise SystemExit(1) from exc

    if state.json_mode:
        print_json({"created": filename})
    else:
        state.console.print(f"[green]Created:[/green] {filename}")
