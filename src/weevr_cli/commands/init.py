"""Implementation of the weevr init command."""

from __future__ import annotations

from pathlib import Path

from weevr_cli.config import WEEVR_PROJECT_EXT
from weevr_cli.output import print_error, print_json
from weevr_cli.state import AppState
from weevr_cli.templates import get_example_files, render_cli_yaml


def _normalize_project_path(name: str) -> Path:
    """Resolve project directory path, ensuring the .weevr suffix.

    Args:
        name: Project name or "." for current directory.

    Returns:
        Resolved Path with .weevr suffix.

    Raises:
        SystemExit: If "." is used and cwd doesn't end with .weevr.
    """
    if name == ".":
        cwd = Path.cwd()
        if not cwd.name.endswith(WEEVR_PROJECT_EXT):
            msg = (
                f"Current directory '{cwd.name}' does not have the required "
                f"{WEEVR_PROJECT_EXT} extension. Use 'weevr init <name>' to create "
                f"a new project directory instead."
            )
            raise ValueError(msg)
        return cwd

    path = Path(name)
    if not path.name.endswith(WEEVR_PROJECT_EXT):
        path = Path(f"{name}{WEEVR_PROJECT_EXT}")
    return path


def init_project(
    name: str,
    *,
    examples: bool = False,
    interactive: bool = False,
    state: AppState,
) -> None:
    """Create a new weevr project.

    Creates a project directory with the .weevr suffix and a
    `.weevr/cli.yaml` configuration file inside it. The .weevr suffix
    is required by the weevr engine for project root detection.

    Args:
        name: Project directory name, or "." for current directory.
        examples: Whether to include example files.
        interactive: Whether to run the interactive wizard.
        state: Application state with console and json_mode.
    """
    try:
        target = _normalize_project_path(name)
    except ValueError as exc:
        print_error(
            str(exc),
            "invalid_project_dir",
            json_mode=state.json_mode,
            console=state.console,
        )
        raise SystemExit(1) from exc

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

    # Create project structure — only .weevr/cli.yaml by default
    try:
        target.mkdir(parents=True, exist_ok=True)
        weevr_dir = target / ".weevr"
        weevr_dir.mkdir(exist_ok=True)
        weevr_dir.joinpath("cli.yaml").write_text(cli_yaml_content, encoding="utf-8")
    except OSError as exc:
        print_error(
            f"Failed to create project: {exc}",
            "filesystem_error",
            json_mode=state.json_mode,
            console=state.console,
        )
        raise SystemExit(1) from exc

    created_files: list[str] = [".weevr/cli.yaml"]

    # Write example files if requested
    if examples:
        example_files = get_example_files()
        for rel_path, content in example_files.items():
            file_path = target / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            created_files.append(rel_path)

    # Output
    display_name = target.name
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
        target_name = Prompt.ask(
            "Target name", default="dev" if not targets else "prod", console=console
        )
        workspace_id = ""
        while not workspace_id.strip():
            workspace_id = Prompt.ask("Workspace ID", console=console)
        lakehouse_id = ""
        while not lakehouse_id.strip():
            lakehouse_id = Prompt.ask("Lakehouse ID", console=console)
        path_prefix = Prompt.ask("Path prefix (optional)", default="", console=console)

        target_config: dict[str, str] = {
            "workspace_id": workspace_id,
            "lakehouse_id": lakehouse_id,
        }
        if path_prefix:
            target_config["path_prefix"] = path_prefix

        targets[target_name] = target_config
        if first_target is None:
            first_target = target_name

        if not Confirm.ask("Add another target?", default=False, console=console):
            break

    default_target = first_target
    if len(targets) > 1:
        default_target = Prompt.ask(
            "Default target",
            choices=list(targets.keys()),
            default=first_target,
            console=console,
        )

    return render_cli_yaml(targets=targets, default_target=default_target)
