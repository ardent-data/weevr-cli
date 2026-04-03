"""Application state passed through Typer context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.console import Console

from weevr_cli.config import ConfigError, WeevrConfig

if TYPE_CHECKING:
    from azure.core.credentials import TokenCredential


class AuthError(Exception):
    """Error acquiring Azure credentials."""

    def __init__(self, message: str) -> None:
        """Initialize with a descriptive error message including remediation hints."""
        super().__init__(message)


_AUTH_HINT = (
    "No Azure credentials found. To authenticate:\n"
    "  - Local development: run 'az login'\n"
    "  - CI/CD: set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID\n"
    "  - Azure-hosted: ensure managed identity is enabled"
)


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
    _credential: TokenCredential | None = field(default=None, repr=False)

    @property
    def credential(self) -> TokenCredential:
        """Lazy-initialized Azure credential shared across commands and plugins.

        Returns:
            A DefaultAzureCredential instance.

        Raises:
            AuthError: If credential creation fails.
        """
        if self._credential is None:
            try:
                from azure.identity import DefaultAzureCredential

                self._credential = DefaultAzureCredential()
            except Exception as exc:
                raise AuthError(f"{_AUTH_HINT}\n\nUnderlying error: {exc}") from exc
        return self._credential
