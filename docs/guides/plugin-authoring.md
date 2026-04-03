# Plugin Authoring

Plugins extend the weevr CLI with custom subcommand groups. This guide covers creating, registering, and testing a plugin.

!!! warning "Stability Notice"
    The plugin API may evolve in future releases. The v1.0 stability contract covers CLI commands, flags, exit codes, and the configuration format — but not the plugin protocol.

## How Plugins Work

A plugin is a Python package that:

1. Exports a [Typer](https://typer.tiangolo.com/) app from a module
2. Registers that module as a `weevr.plugins` entry point

The CLI discovers plugins at startup, validates them, and mounts each one as a subcommand group (e.g., `weevr <plugin-name> <command>`).

## Minimal Example

Create a package with a single module:

```python
# my_weevr_plugin/__init__.py
import typer

app = typer.Typer(help="My custom commands.")


@app.command()
def hello(name: str = typer.Argument("world")) -> None:
    """Say hello."""
    typer.echo(f"Hello, {name}!")
```

Register the entry point in your `pyproject.toml`:

```toml
[project.entry-points."weevr.plugins"]
my-plugin = "my_weevr_plugin"
```

Install the package (in the same environment as weevr-cli), and the command is available:

```bash
weevr my-plugin hello
# Hello, world!
```

## Entry Point Registration

The entry point group must be `weevr.plugins`. The entry point name becomes the subcommand name:

```toml
[project.entry-points."weevr.plugins"]
custom-name = "my_package.module"
```

This makes `weevr custom-name` available. The module must have an `app` attribute that is a `typer.Typer` instance.

!!! note
    Plugin names cannot collide with built-in commands (`init`, `new`, `validate`, `deploy`, `status`, `list`, `schema`, `plugins`). Colliding plugins are skipped with a warning.

## Plugin Metadata

Optionally export a `plugin_meta` object for richer information in `weevr plugins list`:

```python
from weevr_cli.plugins import PluginMetadata

plugin_meta = PluginMetadata(
    name="My Plugin",
    version="0.1.0",
    description="Custom commands for my workflow.",
    min_cli_version="0.1.8",
)
```

| Field | Required | Description |
|---|---|---|
| `name` | No | Display name (defaults to entry point name) |
| `version` | No | Plugin version |
| `description` | No | One-line description |
| `min_cli_version` | No | Minimum weevr-cli version required (plugin is skipped if not met) |

## Accessing Application State

Plugin commands can access the CLI's shared state through the Typer context:

```python
import typer

app = typer.Typer()


@app.command()
def info(ctx: typer.Context) -> None:
    """Show current config."""
    state = ctx.obj  # AppState instance
    # state.console      — Rich console for output
    # state.config       — WeevrConfig (or None if no project found)
    # state.config_error — ConfigError (or None if config loaded OK)
    # state.json_mode    — True if --json was passed
```

## Testing Plugins

Use Typer's `CliRunner` to test plugin commands:

```python
from typer.testing import CliRunner
from my_weevr_plugin import app

runner = CliRunner()


def test_hello():
    result = runner.invoke(app, ["hello", "test"])
    assert result.exit_code == 0
    assert "Hello, test!" in result.output
```

## Debugging

List discovered plugins and their status:

```bash
weevr plugins list
```

Get detailed information about a specific plugin:

```bash
weevr plugins info <plugin-name>
```

Plugins can have one of three statuses:

- **loaded** — successfully mounted
- **skipped** — passed loading but failed validation (name collision, version incompatibility)
- **failed** — error during import or missing `app` attribute
