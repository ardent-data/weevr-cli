"""Implementation of the weevr schema command (version + update)."""

from __future__ import annotations

from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import typer

from weevr_cli.config import WEEVR_PROJECT_EXT, find_project_root
from weevr_cli.output import print_error, print_json
from weevr_cli.state import AppState
from weevr_cli.validation.resolver import VALID_SCHEMA_TYPES

schema_app = typer.Typer(
    name="schema",
    help="Manage validation schemas.",
    no_args_is_help=True,
)

_GITHUB_BASE = (
    "https://raw.githubusercontent.com/ardent-data/weevr"
)


def _get_project_root() -> Path | None:
    """Find the .weevr project root."""
    cwd = Path.cwd()
    if cwd.name.endswith(WEEVR_PROJECT_EXT):
        return cwd
    return find_project_root()


@schema_app.command()
def version(ctx: typer.Context) -> None:
    """Show the active schema version and source."""
    state: AppState = ctx.obj
    project_root = _get_project_root()

    local_schemas = None
    if project_root is not None:
        local_dir = project_root / ".weevr" / "schemas"
        if local_dir.is_dir() and any(local_dir.iterdir()):
            local_schemas = local_dir

    if local_schemas is not None:
        source = "local"
        location = str(local_schemas)
    else:
        source = "bundled"
        location = "weevr_cli/schemas/"

    if state.json_mode:
        print_json({
            "source": source,
            "location": location,
            "types": list(VALID_SCHEMA_TYPES),
        })
    else:
        state.console.print(
            f"Schema source: [bold]{source}[/bold] ({location})"
        )
        state.console.print(
            f"Types: {', '.join(VALID_SCHEMA_TYPES)}"
        )


@schema_app.command()
def update(
    ctx: typer.Context,
    schema_version: str | None = typer.Option(
        None,
        "--version",
        help="Specific schema version (git tag/branch).",
    ),
) -> None:
    """Fetch latest schemas from GitHub to .weevr/schemas/."""
    state: AppState = ctx.obj
    project_root = _get_project_root()

    if project_root is None:
        print_error(
            "No weevr project found. Run 'weevr init' first.",
            "config_not_found",
            json_mode=state.json_mode,
            console=state.console,
        )
        raise typer.Exit(code=1)

    branch = schema_version or "main"
    schemas_dir = project_root / ".weevr" / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)

    fetched: list[str] = []
    for schema_type in VALID_SCHEMA_TYPES:
        url = f"{_GITHUB_BASE}/{branch}/docs/schema/{schema_type}.json"
        try:
            with urlopen(url) as resp:  # noqa: S310
                content = resp.read()
            target = schemas_dir / f"{schema_type}.json"
            target.write_bytes(content)
            fetched.append(schema_type)
        except (URLError, OSError) as exc:
            print_error(
                f"Failed to fetch {schema_type} schema: {exc}",
                "schema_fetch_failed",
                json_mode=state.json_mode,
                console=state.console,
            )
            raise typer.Exit(code=1) from exc

    if state.json_mode:
        print_json({
            "updated": True,
            "schemas_updated": fetched,
            "location": str(schemas_dir),
        })
    else:
        state.console.print(
            f"[green]Updated schemas:[/green] "
            f"{', '.join(fetched)}"
        )
        state.console.print(f"Location: {schemas_dir}")
