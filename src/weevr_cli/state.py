"""Application state passed through Typer context."""

from __future__ import annotations

from dataclasses import dataclass, field

from rich.console import Console

from weevr_cli.config import ConfigError, WeevrConfig


@dataclass
class AppState:
    """Typed context object stored in ctx.obj for all commands.

    Attributes:
        console: Shared Rich Console instance.
        config: Parsed project config, or None if outside a project.
        json_mode: Whether JSON output is active.
        config_error: Deferred config loading error, surfaced by require_config.
    """

    console: Console
    config: WeevrConfig | None
    json_mode: bool
    config_error: ConfigError | None = field(default=None)
