"""Implementation of the weevr init command."""

from __future__ import annotations

from pathlib import Path

from weevr_cli.output import print_error, print_json
from weevr_cli.state import AppState
from weevr_cli.templates import get_example_files, render_cli_yaml

_DEFAULT_DIRS = ("threads", "weaves", "looms")


def init_project(
    name: str,
    *,
    examples: bool = False,
    interactive: bool = False,
    state: AppState,
) -> None:
    """Create a new weevr project with standard directory layout.

    Args:
        name: Project directory name, or "." for current directory.
        examples: Whether to include example files.
        interactive: Whether to run the interactive wizard.
        state: Application state with console and json_mode.
    """
    target = Path.cwd() if name == "." else Path(name)

    # Check for existing project
    config_path = target / ".weevr" / "cli.yaml"
    if config_path.is_file():
        print_error(
            f"Project already exists: .weevr/cli.yaml found in {target}",
            "project_exists",
            json_mode=state.json_mode,
            console=state.console,
        )
        raise SystemExit(1)

    # Collect config from wizard or use template
    cli_yaml_content = _run_wizard(state) if interactive else render_cli_yaml()

    # Create project structure
    try:
        target.mkdir(parents=True, exist_ok=True)
        weevr_dir = target / ".weevr"
        weevr_dir.mkdir(exist_ok=True)
        weevr_dir.joinpath("cli.yaml").write_text(cli_yaml_content, encoding="utf-8")

        for dirname in _DEFAULT_DIRS:
            (target / dirname).mkdir(exist_ok=True)
    except OSError as exc:
        print_error(
            f"Failed to create project: {exc}",
            "filesystem_error",
            json_mode=state.json_mode,
            console=state.console,
        )
        raise SystemExit(1) from exc

    created_files: list[str] = [
        ".weevr/cli.yaml",
        *[f"{d}/" for d in _DEFAULT_DIRS],
    ]

    # Write example files if requested
    if examples:
        example_files = get_example_files()
        for rel_path, content in example_files.items():
            file_path = target / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            created_files.append(rel_path)

    # Output
    display_name = name if name != "." else str(target.name)
    if state.json_mode:
        print_json({"created": display_name, "files": created_files})
    else:
        state.console.print(f"[green]Created weevr project:[/green] {display_name}")
        for f in created_files:
            state.console.print(f"  {f}")


def _run_wizard(state: AppState) -> str:
    """Run interactive wizard to collect target configuration.

    Args:
        state: Application state with console.

    Returns:
        Rendered cli.yaml content.
    """
    from rich.prompt import Confirm, Prompt

    console = state.console
    targets: dict[str, dict[str, str]] = {}
    first_target: str | None = None

    console.print("\n[bold]weevr project setup[/bold]\n")

    while True:
        target_name = Prompt.ask("Target name", default="dev" if not targets else "prod")
        workspace_id = Prompt.ask("Workspace ID")
        lakehouse_id = Prompt.ask("Lakehouse ID")
        path_prefix = Prompt.ask("Path prefix (optional)", default="")

        target_config: dict[str, str] = {
            "workspace_id": workspace_id,
            "lakehouse_id": lakehouse_id,
        }
        if path_prefix:
            target_config["path_prefix"] = path_prefix

        targets[target_name] = target_config
        if first_target is None:
            first_target = target_name

        if not Confirm.ask("Add another target?", default=False):
            break

    default_target = first_target
    if len(targets) > 1:
        default_target = Prompt.ask(
            "Default target",
            choices=list(targets.keys()),
            default=first_target,
        )

    return render_cli_yaml(targets=targets, default_target=default_target)
