"""Main CLI application."""

from __future__ import annotations

import typer

from weevr_cli import __version__
from weevr_cli.config import ConfigError, find_project_root, load_config
from weevr_cli.output import create_console, print_error, print_json
from weevr_cli.state import AppState

app = typer.Typer(
    name="weevr",
    help="CLI for managing weevr projects — scaffolding, validation, and deployment.",
    no_args_is_help=True,
)


def _version_callback(ctx: typer.Context, value: bool) -> None:
    """Print version and exit."""
    if not value:
        return
    json_mode = ctx.params.get("json", False)
    if json_mode:
        print_json({"version": __version__})
    else:
        typer.echo(f"weevr {__version__}")
    raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    json: bool = typer.Option(
        False,
        "--json",
        help="Output in JSON format for machine consumption.",
        is_eager=True,
    ),
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Weevr CLI — manage weevr projects from your terminal."""
    console = create_console(json_mode=json)

    config = None
    project_root = find_project_root()
    if project_root is not None:
        config_path = project_root / ".weevr" / "cli.yaml"
        try:
            config = load_config(config_path)
        except ConfigError as exc:
            print_error(str(exc), exc.code, json_mode=json, console=console)
            raise typer.Exit(code=1) from exc

    ctx.obj = AppState(console=console, config=config, json_mode=json)


def require_config(ctx: typer.Context) -> AppState:
    """Get AppState from context, failing if config is not loaded.

    Args:
        ctx: Typer context with AppState in obj.

    Returns:
        AppState with a guaranteed non-None config.

    Raises:
        typer.Exit: If no config is available.
    """
    state: AppState = ctx.obj
    if state.config is None:
        print_error(
            "No weevr project found. Run 'weevr init' to create one, "
            "or run this command from within a weevr project directory.",
            "config_not_found",
            json_mode=state.json_mode,
            console=state.console,
        )
        raise typer.Exit(code=1)
    return state


@app.command()
def init(
    ctx: typer.Context,
    name: str = typer.Argument(".", help="Project name or directory."),
    examples: bool = typer.Option(False, "--examples", help="Include example files."),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive wizard."),
) -> None:
    """Create a new weevr project."""
    from weevr_cli.commands.init import init_project

    state: AppState = ctx.obj
    try:
        init_project(name, examples=examples, interactive=interactive, state=state)
    except SystemExit as exc:
        raise typer.Exit(code=int(exc.code) if exc.code is not None else 1) from exc


@app.command()
def new(
    ctx: typer.Context,
    file_type: str = typer.Argument(..., help="File type: thread, weave, or loom."),
    name: str = typer.Argument(..., help="Name for the new file."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing file."),
) -> None:
    """Generate a new thread, weave, or loom file from a template."""
    from weevr_cli.commands.new import new_file

    state: AppState = ctx.obj
    try:
        new_file(file_type, name, force=force, state=state)
    except SystemExit as exc:
        raise typer.Exit(code=int(exc.code) if exc.code is not None else 1) from exc


@app.command()
def validate(
    ctx: typer.Context,
    path: str | None = typer.Argument(None, help="File or directory to validate."),
    strict: bool = typer.Option(False, "--strict", help="Treat warnings as errors."),
) -> None:
    """Validate project files against schemas and check reference integrity."""
    from weevr_cli.commands.validate import run_validate

    state: AppState = ctx.obj
    try:
        run_validate(path, strict=strict, state=state)
    except SystemExit as exc:
        raise typer.Exit(code=int(exc.code) if exc.code is not None else 1) from exc


@app.command()
def deploy(
    ctx: typer.Context,
    paths: list[str] | None = typer.Argument(  # noqa: B008
        None, help="Specific files to deploy."
    ),
    target: str = typer.Option("", "--target", "-t", help="Named deploy target."),
    workspace_id: str | None = typer.Option(None, "--workspace-id", help="Override workspace."),
    lakehouse_id: str | None = typer.Option(None, "--lakehouse-id", help="Override lakehouse."),
    path_prefix: str | None = typer.Option(None, "--path-prefix", help="Override path prefix."),
    full: bool = typer.Option(False, "--full", help="Full overwrite instead of smart sync."),
    clean: bool = typer.Option(False, "--clean", help="Remove remote files not present locally."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would change."),
    skip_validation: bool = typer.Option(
        False, "--skip-validation", help="Skip pre-deploy validation."
    ),
) -> None:
    """Deploy project files to a Fabric Lakehouse."""
    require_config(ctx)
    typer.echo("Deploying...")


@app.command()
def status(
    ctx: typer.Context,
    target: str = typer.Option("", "--target", "-t", help="Named deploy target."),
) -> None:
    """Show diff between local files and deployed state."""
    require_config(ctx)
    typer.echo("Checking status...")


@app.command(name="list")
def list_cmd(ctx: typer.Context) -> None:
    """Display project structure and dependency relationships."""
    require_config(ctx)
    typer.echo("Listing project structure...")


@app.command()
def schema(
    action: str = typer.Argument("version", help="Action: version or update."),
    version: str | None = typer.Option(None, "--version", help="Specific schema version."),
) -> None:
    """Manage validation schemas."""
    typer.echo(f"Schema: {action}")
