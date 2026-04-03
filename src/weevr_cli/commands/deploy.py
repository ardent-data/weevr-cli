"""Implementation of the weevr deploy command."""

from __future__ import annotations

import sys

from weevr_cli.config import find_project_root
from weevr_cli.deploy.collector import collect_local_files
from weevr_cli.deploy.diff import compute_diff
from weevr_cli.deploy.executor import execute_plan
from weevr_cli.deploy.ignore import load_deploy_ignore
from weevr_cli.deploy.onelake import OneLakeClient
from weevr_cli.deploy.output import render_dry_run, render_result, render_target_header
from weevr_cli.deploy.target import TargetError, resolve_target
from weevr_cli.output import print_error
from weevr_cli.state import AppState, AuthError


def run_deploy(
    *,
    paths: list[str] | None,
    target_name: str,
    workspace_id: str | None,
    lakehouse_id: str | None,
    path_prefix: str | None,
    full: bool,
    clean: bool,
    clean_all: bool,
    dry_run: bool,
    skip_validation: bool,
    strict_validation: bool,
    force: bool,
    state: AppState,
) -> None:
    """Execute the deploy command.

    Args:
        paths: Specific files/directories to deploy (selective mode).
        target_name: Named target from --target flag.
        workspace_id: Override workspace ID.
        lakehouse_id: Override lakehouse ID.
        path_prefix: Override path prefix.
        full: Full overwrite mode.
        clean: Remove orphaned weevr files from remote.
        clean_all: Remove all orphaned files from remote.
        dry_run: Show plan without executing.
        skip_validation: Skip pre-deploy validation.
        strict_validation: Treat warnings as errors in validation.
        force: Skip confirmation prompts.
        state: Application state.

    Raises:
        SystemExit: On errors.
    """
    assert state.config is not None

    # 1. Resolve target
    try:
        target = resolve_target(
            state.config,
            target_name=target_name,
            workspace_id=workspace_id,
            lakehouse_id=lakehouse_id,
            path_prefix=path_prefix,
        )
    except TargetError as exc:
        print_error(str(exc), exc.code, json_mode=state.json_mode, console=state.console)
        raise SystemExit(1) from exc

    # 2. Display target header
    if not state.json_mode:
        render_target_header(target, state.console)

    # 3. Find project root
    project_root = find_project_root()
    if project_root is None:
        print_error(
            "No weevr project found.",
            "config_not_found",
            json_mode=state.json_mode,
            console=state.console,
        )
        raise SystemExit(1) from None

    # 4. Pre-deploy validation (unless skipped)
    if not skip_validation:
        from weevr_cli.commands.validate import run_validate

        if not state.json_mode:
            state.console.print("\n[bold]Running pre-deploy validation...[/bold]")
        try:
            run_validate(None, strict=strict_validation, state=state)
        except SystemExit:
            print_error(
                "Validation failed. Use --skip-validation to bypass.",
                "validation_failed",
                json_mode=state.json_mode,
                console=state.console,
            )
            raise SystemExit(1) from None
        if not state.json_mode:
            state.console.print()

    # 5. Collect local files
    ignore_spec = load_deploy_ignore(project_root)
    try:
        local_files = collect_local_files(
            project_root,
            ignore_spec,
            selective_paths=paths if paths else None,
        )
    except FileNotFoundError as exc:
        print_error(str(exc), "path_not_found", json_mode=state.json_mode, console=state.console)
        raise SystemExit(1) from exc

    # 6. Confirm --clean --all
    if clean_all and not force and not dry_run:
        if not sys.stdin.isatty():
            print_error(
                "--clean --all requires --force in non-interactive mode.",
                "confirmation_required",
                json_mode=state.json_mode,
                console=state.console,
            )
            raise SystemExit(1) from None
        if not state.json_mode:
            confirmed = state.console.input(
                "[bold red]WARNING:[/bold red] --clean --all will delete ALL remote files "
                "not present locally. Continue? [y/N] "
            )
            if confirmed.lower() not in ("y", "yes"):
                state.console.print("Aborted.")
                raise SystemExit(0) from None

    # 7. Authenticate and list remote files
    try:
        client = OneLakeClient(target, state.credential)
    except AuthError as exc:
        print_error(str(exc), "auth_failed", json_mode=state.json_mode, console=state.console)
        raise SystemExit(1) from exc

    try:
        remote_files = client.list_files()
    except Exception as exc:
        print_error(
            f"Failed to list remote files: {exc}",
            "remote_error",
            json_mode=state.json_mode,
            console=state.console,
        )
        raise SystemExit(1) from exc

    # 8. Compute diff
    plan = compute_diff(
        target,
        local_files,
        remote_files,
        full=full,
        clean=clean and not clean_all,
        clean_all=clean_all,
    )

    # 9. Dry run — show plan and exit
    if dry_run:
        render_dry_run(plan, json_mode=state.json_mode, console=state.console)
        return

    # 10. Execute plan
    if not plan.uploads and not plan.deletes:
        if state.json_mode:
            from weevr_cli.output import print_json

            print_json(
                {
                    "uploaded": 0,
                    "skipped": len(plan.skips),
                    "deleted": 0,
                    "failed": 0,
                    "actions": [],
                }
            )
        else:
            state.console.print("\nNothing to deploy — local and remote are in sync.")
        return

    if not state.json_mode:
        state.console.print(
            f"\nDeploying: {len(plan.uploads)} uploads, {len(plan.deletes)} deletes..."
        )

    result = execute_plan(client, plan)

    # 11. Output results
    render_result(result, json_mode=state.json_mode, console=state.console)

    if not result.is_success:
        raise SystemExit(1) from None
