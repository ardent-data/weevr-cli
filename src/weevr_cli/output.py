"""Output helpers for Rich and JSON modes."""

from __future__ import annotations

import json
import sys
from typing import Any

from rich.console import Console
from rich.panel import Panel


def create_console(json_mode: bool = False) -> Console:
    """Create a Rich Console configured for the current output mode.

    Args:
        json_mode: If True, suppress Rich output (quiet mode).

    Returns:
        Configured Console instance.
    """
    return Console(stderr=True, quiet=json_mode)


def print_json(data: dict[str, Any]) -> None:
    """Write a JSON object to stdout.

    Args:
        data: Dictionary to serialize as JSON.
    """
    sys.stdout.write(json.dumps(data) + "\n")
    sys.stdout.flush()


def print_error(
    message: str,
    code: str,
    *,
    json_mode: bool,
    console: Console | None = None,
) -> None:
    """Display an error in the appropriate format.

    In JSON mode, writes a JSON error object to stderr.
    In interactive mode, renders a Rich error panel to stderr.

    Args:
        message: Human-readable error description.
        code: Machine-readable error code.
        json_mode: Whether to output JSON instead of Rich.
        console: Rich Console for interactive mode (ignored in JSON mode).
    """
    if json_mode:
        sys.stderr.write(json.dumps({"error": message, "code": code}) + "\n")
        sys.stderr.flush()
    else:
        err_console = console or Console(stderr=True)
        err_console.print(Panel(message, title="Error", border_style="red"), highlight=False)
