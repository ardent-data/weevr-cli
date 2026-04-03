"""Main CLI application."""

from __future__ import annotations

import typer

from weevr_cli import __version__
from weevr_cli.commands.plugins_cmd import plugins_app
from weevr_cli.commands.schema_cmd import schema_app
from weevr_cli.config import ConfigError, find_project_root, load_config
from weevr_cli.output import create_console, print_error, print_json
from weevr_cli.plugins.discovery import discover_and_mount_plugins
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
    config_error: ConfigError | None = None
    project_root = find_project_root()
    if project_root is not None:
        config_path = project_root / ".weevr" / "cli.yaml"
        try:
            config = load_config(config_path)
        except ConfigError as exc:
            config_error = exc

    ctx.obj = AppState(console=console, config=config, json_mode=json, config_error=config_error)


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
    if state.config_error is not None:
        print_error(
            str(state.config_error),
            state.config_error.code,
            json_mode=state.json_mode,
            console=state.console,
        )
        raise typer.Exit(code=1)
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
    clean_all: bool = typer.Option(False, "--all", help="With --clean, remove all remote files."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would change."),
    skip_validation: bool = typer.Option(
        False, "--skip-validation", help="Skip pre-deploy validation."
    ),
    strict_validation: bool = typer.Option(
        False, "--strict-validation", help="Block deploy on validation warnings."
    ),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompts."),
) -> None:
    """Deploy project files to a Fabric Lakehouse."""
    from weevr_cli.commands.deploy import run_deploy

    state = require_config(ctx)
    try:
        run_deploy(
            paths=paths,
            target_name=target,
            workspace_id=workspace_id,
            lakehouse_id=lakehouse_id,
            path_prefix=path_prefix,
            full=full,
            clean=clean,
            clean_all=clean_all and clean,
            dry_run=dry_run,
            skip_validation=skip_validation,
            strict_validation=strict_validation,
            force=force,
            state=state,
        )
    except SystemExit as exc:
        raise typer.Exit(code=int(exc.code) if exc.code is not None else 1) from exc


@app.command()
def status(
    ctx: typer.Context,
    target: str = typer.Option("", "--target", "-t", help="Named deploy target."),
    workspace_id: str | None = typer.Option(None, "--workspace-id", help="Override workspace."),
    lakehouse_id: str | None = typer.Option(None, "--lakehouse-id", help="Override lakehouse."),
    path_prefix: str | None = typer.Option(None, "--path-prefix", help="Override path prefix."),
    exit_code: bool = typer.Option(False, "--exit-code", help="Exit 1 if differences exist."),
    verbose: bool = typer.Option(False, "--verbose", help="Show all files including non-weevr."),
) -> None:
    """Show diff between local files and deployed state."""
    from weevr_cli.commands.status import run_status

    state = require_config(ctx)
    try:
        run_status(
            target_name=target,
            workspace_id=workspace_id,
            lakehouse_id=lakehouse_id,
            path_prefix=path_prefix,
            exit_code=exit_code,
            verbose=verbose,
            state=state,
        )
    except SystemExit as exc:
        raise typer.Exit(code=int(exc.code) if exc.code is not None else 1) from exc


@app.command(name="list")
def list_cmd(
    ctx: typer.Context,
    format: str = typer.Option("tree", "--format", "-f", help="Output format: tree or table."),
) -> None:
    """Display project structure and dependency relationships."""
    from weevr_cli.commands.list_cmd import run_list

    state: AppState = ctx.obj
    try:
        run_list(format=format, state=state)
    except SystemExit as exc:
        raise typer.Exit(code=int(exc.code) if exc.code is not None else 1) from exc


app.add_typer(schema_app, name="schema")
app.add_typer(plugins_app, name="plugins")
discover_and_mount_plugins(app)
