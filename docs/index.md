# weevr-cli

**CLI for managing weevr projects — scaffolding, validation, and deployment to Microsoft Fabric.**

The [weevr](https://github.com/ardent-data/weevr) engine runs inside Fabric notebooks. The CLI runs on your workstation and in CI/CD pipelines, bridging the gap between your Git repository and the Fabric Lakehouse where weevr project files live.

## Key Features

- **Project scaffolding** — `weevr init` creates a project with the standard layout; `weevr new` generates thread, weave, loom, and warp files from templates
- **YAML validation** — `weevr validate` checks schema conformance and cross-file reference integrity
- **Smart deployment** — `weevr deploy` syncs files to a Fabric Lakehouse via the OneLake API, uploading only what changed
- **Status tracking** — `weevr status` diffs local files against what's deployed; `weevr list` shows project structure and dependencies
- **Schema management** — `weevr schema` manages validation schemas with version pinning
- **Plugin system** — extend the CLI with custom commands via entry-point plugins

## Quick Install

```bash
uv tool install weevr-cli
```

Or with pipx or pip:

```bash
pipx install weevr-cli
# or
pip install weevr-cli
```

## Next Steps

- [Getting Started](getting-started.md) — full walkthrough from install to first deploy
- [CLI Reference](cli/index.md) — every command and flag
- [Configuration](configuration/index.md) — `.weevr/cli.yaml` and deploy targets
- [Deploy Workflows](guides/deploy-workflows.md) — smart sync, full overwrite, CI/CD patterns
- [Plugin Authoring](guides/plugin-authoring.md) — extend the CLI with custom commands
