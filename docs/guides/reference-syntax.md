# Reference Syntax

Weaves and looms point at other weevr files. This page covers how those
references resolve, what forms are valid, and what `weevr validate` reports
when one is wrong. The CLI validates with weevr-core, the same loader the
engine uses in Fabric, so a reference that passes here resolves the same way
at run time.

## What is a ref?

A ref is a pointer from one weevr file to another:

- A **weave** references one or more **threads** via `threads[].ref`.
- A **loom** references one or more **weaves** via `weaves[].ref`, or by name.

Refs always resolve **relative to the project root** — the directory with the
`.weevr` suffix (e.g. `my-project.weevr/`). They never reach outside the
project.

## Valid forms

### Path refs

Write the path to the target file relative to the project root, with forward
slashes and the file's typed extension:

```yaml
# staging.weave
config_version: "1.0"
threads:
  - ref: staging/stg_customers.thread
  - ref: staging/stg_orders.thread
```

```yaml
# daily.loom
config_version: "1.0"
weaves:
  - ref: staging.weave
  - ref: curated/customer_dim.weave
```

Do not start a ref with `/` or use backslashes. A leading `/` is treated as an
absolute path, which resolves outside the project and is rejected; a
backslash is taken literally, so the file is not found.

### Loom weaves by name

A loom can also name a weave instead of giving its path. The name resolves to
`{name}.weave` at the project root:

```yaml
# daily.loom
config_version: "1.0"
weaves:
  - staging            # -> staging.weave
  - name: curated      # -> curated.weave
```

This applies to looms only. In a weave, a thread entry with only a `name` is
an inline thread definition, not a reference to `{name}.thread`.

## Error messages

When a ref is wrong, `weevr validate` reports it on the weave or loom that
contains it. The messages come from weevr-core:

### `Referenced file not found: <ref>`

The ref is well formed but the file does not exist. Usually this is a typo, a
file that was renamed or moved without updating its referrers, or a backslash
in the path.

```yaml
threads:
  - ref: staging/stg_coustomers.thread  # typo — file is stg_customers
```

Fix: correct the path, or create the missing file.

### `Reference '<ref>' resolves outside project root`

The ref would escape the project, through `..` segments or a leading `/`.
Refs are confined to the project — if you need to share data between
projects, publish it through the lakehouse rather than reaching across
filesystems.

```yaml
threads:
  - ref: ../other-project.weevr/shared.thread  # rejected
  - ref: /staging/stg_customers.thread         # rejected — drop the leading /
```

Fix: write the path relative to the project root, or copy the file in if
it's truly shared.

### `Unsupported extension '<ext>'. Expected .thread, .weave, or .loom`

The ref does not end in a typed extension. This includes empty refs such as
`""` or `"/"`, which usually come from a template that was never filled in.

```yaml
threads:
  - ref: staging/stg_customers.yaml  # rejected — use .thread
  - ref: ""                          # rejected
```

Fix: point at the `.thread`, `.weave`, or `.loom` file, or remove the
incomplete entry.

### Errors inside a referenced file

Loading a weave or loom also loads every file it references. A problem inside
a referenced thread is reported against that thread's file, once, even when
several weaves reference it.

## Checks across threads

After a weave or loom loads cleanly, `weevr validate` runs the checks the
engine otherwise only runs when it plans the weave:

- **Dependency cycles** — threads that depend on each other in a loop, whether
  through declared `dependencies` or because one reads another's target.
- **Unknown dependencies** — a `dependencies` entry naming a thread that is
  not in the weave.
- **Unordered writers** — two threads writing the same target with no
  dependency between them and no mutually exclusive conditions.
- **Incremental loads** — load and write modes that the engine rejects at run
  time, such as `incremental_watermark` with `write.mode: overwrite`.
- **Ignored settings** — thread-level `execution:` blocks, which the engine
  does not apply (warning).

These are reported on the weave file, or on the thread file for per-thread
problems. `weevr list --format dag` shows the plan the engine builds when a
weave passes.

## Variables and parameters

References to `${param.x}`, `${env.X}`, and other variables are resolved
during validation. Because validation runs without a Fabric run context:

- A declared parameter with no default and no runtime value is a **warning**.
- A `${...}` variable with nothing to resolve it and no `:-default` is a
  **warning**.
- `${fabric.workspace_id}`, `${fabric.lakehouse_id}`, and
  `${fabric.workspace_name}` resolve to placeholder values, so the rest of
  the file is still checked.

Loading stops at the first unresolved parameter or variable, so a file with
one of these warnings is only partly validated: later problems in it, and
the plan-time checks for its weave, are not reported until it resolves.
Give parameters defaults where you can, and use `--strict` in CI to treat
these warnings as errors.

## Orphan detection

`weevr validate` and `weevr list` also check for **orphans** — thread and
weave files that exist in the project but are not referenced by anything.
Orphan detection is a warning, not an error: it helps you spot dead files
without blocking validation.

- **Threads** are expected to be referenced by at least one weave.
- **Weaves** are expected to be referenced by at least one loom, by path or
  by name.
- **Looms** are top-level entry points and are never considered orphans.
- **Warps** are standalone schema contracts and are never considered orphans.

Orphans are still reported when other files in the project fail validation.
If you intentionally keep scratch or draft files in the project, add them to
a project-wide ignore file so they don't appear as orphans. See
[Configuration › Ignore files](../configuration/index.md#ignore-files).

## Explicit path bypass

When you pass a specific file or directory to `weevr validate` on the
command line, the ignore filter does not apply:

```bash
# Full-project scan — obeys .weevr/ignore
weevr validate

# Explicit path — validates the file regardless of ignore rules
weevr validate scratch/draft.thread
```

This applies only to the ignore filter. Reference rules apply in both cases,
and a targeted weave or loom still loads and checks the files it references.
