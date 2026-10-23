# Release Notes

## Upgrading to 2.0

Version 2.0 replaces the CLI's own validation with
[weevr-core](https://pypi.org/project/weevr-core/), the loader and planner the
weevr engine runs in Fabric. `weevr validate` now accepts exactly what the
engine accepts.

### Breaking changes

- **Python 3.11 only.** weevr-core targets Fabric Runtime 1.3, so Python 3.12
  is no longer supported.
- **`weevr schema` is removed.** There are no bundled schemas to show or
  update; validation follows the installed weevr-core version.
- **Local schema overrides in `.weevr/schemas/` are no longer used.**
- **`schema.version` in `cli.yaml` is ignored** and prints a deprecation
  warning. It will be removed in 3.0.
- **Validation is stricter.** Files are now checked for parameters,
  variables, inheritance, model rules, and the engine's plan-time rules
  (dependency cycles, unordered writers of one target, incremental load
  conflicts). Projects that passed 1.x validation may now report errors the
  engine would have raised in Fabric.
- **Leading-slash refs are rejected.** `ref: /staging.weave` resolves outside
  the project root in the engine; write `ref: staging.weave`.
- **Validation messages have changed.** They now come from weevr-core. The
  `--json` output keeps the same fields.

### Migration steps

1. Use a Python 3.11 environment and reinstall the CLI:
   `uv tool install --python 3.11 weevr-cli`.
2. Delete the `schema:` section from `.weevr/cli.yaml`, and any
   `.weevr/schemas/` directory.
3. Replace `weevr schema version` in scripts with `weevr --version`, which
   shows the weevr-core version. Upgrade weevr-core to validate against a
   newer weevr release.
4. Remove any leading `/` from `ref:` values.
5. Run `weevr validate` and fix what it reports. Missing runtime parameters
   are warnings; use `--strict` in CI if you want them to fail the build.

--8<-- "CHANGELOG.md:2"
