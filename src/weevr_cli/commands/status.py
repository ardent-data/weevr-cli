"""Implementation of the weevr status command."""

from __future__ import annotations

from weevr_cli.commands.status_models import (
    actions_to_status_entries,
    aggregate_non_weevr,
    partition_entries,
)
from weevr_cli.commands.status_output import (
    format_status_json,
    print_non_weevr_aggregate,
    print_status_entries,
    print_status_header,
    print_status_summary,
)
from weevr_cli.deploy.collector import collect_local_files
from weevr_cli.deploy.diff import compute_diff
from weevr_cli.deploy.ignore import load_deploy_ignore
from weevr_cli.deploy.onelake import OneLakeClient
from weevr_cli.deploy.target import TargetError, resolve_deploy_context
from weevr_cli.output import print_error, print_json
from weevr_cli.state import AppState, AuthError


def run_status(
    *,
    target_name: str,
    workspace_id: str | None,
    lakehouse_id: str | None,
    path_prefix: str | None,
    exit_code: bool,
    verbose: bool,
    state: AppState,
) -> None:
    """Execute the status command.

    Args:
        target_name: Named target from --target flag.
        workspace_id: Override workspace ID.
        lakehouse_id: Override lakehouse ID.
        path_prefix: Override path prefix.
        exit_code: If True, exit 1 when differences exist.
        verbose: If True, show all files including non-weevr.
        state: Application state.

    Raises:
        SystemExit: On errors or when --exit-code is used with differences.
    """
    config = state.config
    if config is None:
        print_error(
            "No weevr project found. Run 'weevr init' to create one.",
            "config_not_found",
            json_mode=state.json_mode,
            console=state.console,
        )
        raise SystemExit(1)

    # 1. Resolve target and project root
    try:
        ctx = resolve_deploy_context(
            config,
            target_name=target_name,
            workspace_id=workspace_id,
            lakehouse_id=lakehouse_id,
            path_prefix=path_prefix,
        )
    except TargetError as exc:
        print_error(str(exc), exc.code, json_mode=state.json_mode, console=state.console)
        raise SystemExit(1) from exc

    target = ctx.target
    project_root = ctx.project_root

    # 2. Display target header
    if not state.json_mode:
        print_status_header(target, state.console)

    # 3. Collect local files
    ignore_spec = load_deploy_ignore(project_root)
    local_files = collect_local_files(project_root, ignore_spec)

    # 4. Authenticate and list remote files
    try:
        client = OneLakeClient(target, state.credential)
    except AuthError as exc:
        print_error(str(exc), "auth_failed", json_mode=state.json_mode, console=state.console)
        raise SystemExit(1) from exc

    try:
        remote_files = client.list_files()
    except Exception as exc:
        print_error(
            f"Failed to connect to OneLake: {exc}",
            "network_error",
            json_mode=state.json_mode,
            console=state.console,
        )
        raise SystemExit(1) from exc

    # 5. Compute diff (smart sync mode, include remote-only for status)
    plan = compute_diff(
        target, local_files, remote_files, clean=True, clean_all=True, ignore_spec=ignore_spec
    )

    # 6. Convert to status entries
    entries = actions_to_status_entries(plan.actions)
    weevr_entries, non_weevr_entries = partition_entries(entries)

    # 7. Output
    if state.json_mode:
        data = format_status_json(entries, target, verbose)
        print_json(data)
    else:
        print_status_entries(weevr_entries, state.console)
        if verbose:
            if non_weevr_entries:
                state.console.print("\n  [bold]Other files:[/bold]")
                print_status_entries(non_weevr_entries, state.console)
        else:
            counts = aggregate_non_weevr(non_weevr_entries)
            print_non_weevr_aggregate(counts, state.console)
        print_status_summary(entries, state.console)

    # 8. Exit code handling
    in_sync = all(e.status == "=" for e in entries)
    if exit_code and not in_sync:
        raise SystemExit(1)
