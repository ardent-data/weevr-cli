# Contributing to weevr-cli

Thank you for your interest in contributing. This guide covers what you need to get started.

## Prerequisites

- **Python 3.10+** — pinned in `.python-version`
- **[uv](https://docs.astral.sh/uv/)** — dependency and virtual environment management
- **Git** — configured with your name and email

## Setup

```bash
# Clone the repository
git clone https://github.com/ardent-data/weevr-cli.git
cd weevr-cli

# Install Python (if needed) and sync dependencies
uv python install 3.10
uv sync --dev
```

This creates a `.venv/` with all development dependencies.

## Development Workflow

### 1. Create a branch

All changes go through feature branches — never commit directly to `main`.

```bash
git checkout -b feat/my-feature
```

Branch prefixes: `feat/`, `fix/`, `chore/`, `docs/`, `ci/`

### 2. Make your changes

Write code, add tests, update docs as needed. Tests mirror the source structure under `tests/`.

### 3. Run quality checks

Before opening a PR, verify everything passes locally:

```bash
uv run ruff check .          # Lint
uv run ruff format --check . # Format check
uv run mypy .                # Type check
uv run pytest                # Tests
```

All four must pass — CI runs the same checks.

### 4. Commit

This project uses [Conventional Commits](https://www.conventionalcommits.org/) for automated changelog generation via Release Please.

```bash
# Format: type(scope): description
git commit -s -m "feat: add validate command"
git commit -s -m "fix: handle missing cli.yaml gracefully"
git commit -s -m "docs: update deploy command usage"
```

The `-s` flag adds a `Signed-off-by` line for the [Developer Certificate of Origin (DCO)](https://developercertificate.org/). All commits must include this sign-off.

### 5. Open a pull request

Push your branch and open a PR against `main`. Use the PR template — it includes a checklist.

## Code Style

The project uses Ruff for linting and formatting, configured in `pyproject.toml`:

- **Line length**: 100 characters
- **Quotes**: Double quotes
- **Indent**: 4 spaces
- **Target**: Python 3.10
- **Rules**: E, F, I, UP, B, SIM, D (Google-style docstrings)

Docstrings are required for all public APIs. Use Google style:

```python
def deploy(target: str, dry_run: bool = False) -> DeployResult:
    """Deploy project files to a Fabric Lakehouse.

    Args:
        target: Named target from cli.yaml (e.g., "dev", "prod").
        dry_run: If True, show what would change without uploading.

    Returns:
        Result containing counts of files uploaded, skipped, and deleted.

    Raises:
        ConfigError: If the target is not defined in cli.yaml.
        AuthError: If Azure credentials are not available.
    """
```

## Type Checking

The project uses mypy in strict mode. All functions require type annotations.

## Pull Request Guidelines

- **Title**: Use Conventional Commit format — this becomes the squash-merge commit message
- **Description**: Fill out the PR template (summary, why, what changed, how to test)
- **Size**: Keep PRs focused. One feature or fix per PR.
- **Tests**: Include tests for new functionality. Bug fixes should include a regression test.
- **Breaking changes**: Note in the PR description and use `feat!:` or `fix!:` prefix

## Merge Strategy

PRs are squash-merged into `main`. The PR title becomes the commit message, so Conventional Commit formatting in the title is important for changelog generation.

## DCO Sign-Off

All commits must be signed off to indicate you agree to the [Developer Certificate of Origin](https://developercertificate.org/). Use `git commit -s` to add the sign-off automatically.

A GitHub App enforces this on all PRs.

## Questions?

Open an issue for questions about contributing. We're happy to help.
