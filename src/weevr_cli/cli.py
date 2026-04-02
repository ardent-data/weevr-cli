"""Main CLI application."""

from typing import Optional

import typer

from weevr_cli import __version__

app = typer.Typer(
    name="weevr",
    help="CLI for managing weevr projects — scaffolding, validation, and deployment.",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"weevr {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Weevr CLI — manage weevr projects from your terminal."""


@app.command()
def init(
    name: str = typer.Argument(".", help="Project name or directory."),
    examples: bool = typer.Option(False, "--examples", help="Include example files."),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive wizard."),
) -> None:
    """Create a new weevr project."""
    typer.echo(f"Initializing weevr project: {name}")


@app.command()
def new(
    file_type: str = typer.Argument(..., help="File type: thread, weave, or loom."),
    name: str = typer.Argument(..., help="Name for the new file."),
) -> None:
    """Generate a new thread, weave, or loom file from a template."""
    typer.echo(f"Creating {file_type}: {name}")


@app.command()
def validate(
    path: Optional[str] = typer.Argument(None, help="File or directory to validate."),
    strict: bool = typer.Option(False, "--strict", help="Treat warnings as errors."),
) -> None:
    """Validate project files against schemas and check reference integrity."""
    target = path or "entire project"
    typer.echo(f"Validating: {target}")


@app.command()
def deploy(
    paths: Optional[list[str]] = typer.Argument(  # noqa: B008
        None, help="Specific files to deploy."
    ),
    target: str = typer.Option("", "--target", "-t", help="Named deploy target."),
    workspace_id: Optional[str] = typer.Option(None, "--workspace-id", help="Override workspace."),
    lakehouse_id: Optional[str] = typer.Option(None, "--lakehouse-id", help="Override lakehouse."),
    path_prefix: Optional[str] = typer.Option(None, "--path-prefix", help="Override path prefix."),
    full: bool = typer.Option(False, "--full", help="Full overwrite instead of smart sync."),
    clean: bool = typer.Option(False, "--clean", help="Remove remote files not present locally."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would change."),
    skip_validation: bool = typer.Option(
        False, "--skip-validation", help="Skip pre-deploy validation."
    ),
) -> None:
    """Deploy project files to a Fabric Lakehouse."""
    typer.echo("Deploying...")


@app.command()
def status(
    target: str = typer.Option("", "--target", "-t", help="Named deploy target."),
) -> None:
    """Show diff between local files and deployed state."""
    typer.echo("Checking status...")


@app.command(name="list")
def list_cmd() -> None:
    """Display project structure and dependency relationships."""
    typer.echo("Listing project structure...")


@app.command()
def schema(
    action: str = typer.Argument("version", help="Action: version or update."),
    version: Optional[str] = typer.Option(None, "--version", help="Specific schema version."),
) -> None:
    """Manage validation schemas."""
    typer.echo(f"Schema: {action}")
