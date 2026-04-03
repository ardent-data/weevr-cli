"""Click command exposure for documentation generation."""

import typer.main

from weevr_cli.cli import app

click_app = typer.main.get_command(app)
