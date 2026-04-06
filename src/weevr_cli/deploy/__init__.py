"""Deploy engine for syncing project files to OneLake."""

from weevr_cli.deploy.collector import LocalFile, collect_local_files, compute_md5
from weevr_cli.deploy.diff import compute_diff
from weevr_cli.deploy.executor import execute_plan
from weevr_cli.deploy.ignore import is_ignored, load_deploy_ignore
from weevr_cli.deploy.models import (
    ActionResult,
    ActionType,
    DeployAction,
    DeployPlan,
    DeployResult,
    DeployTarget,
    RemoteFile,
)
from weevr_cli.deploy.onelake import OneLakeClient
from weevr_cli.deploy.target import (
    DeployContext,
    TargetError,
    resolve_deploy_context,
    resolve_target,
)

__all__ = [
    "ActionResult",
    "ActionType",
    "DeployAction",
    "DeployContext",
    "DeployPlan",
    "DeployResult",
    "DeployTarget",
    "LocalFile",
    "OneLakeClient",
    "RemoteFile",
    "TargetError",
    "collect_local_files",
    "compute_diff",
    "compute_md5",
    "execute_plan",
    "is_ignored",
    "load_deploy_ignore",
    "resolve_deploy_context",
    "resolve_target",
]
