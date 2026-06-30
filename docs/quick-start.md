# Quick Start

This page is the shortest package-first path for trying Agent Maintainer in a
Python repository.

## Install

Install the core dependency set:

```bash
python -m pip install "agent-maintainer[core]"
```

For source-checkout development of Agent Maintainer itself, use editable install
instead:

```bash
python -m pip install -e ".[core]"
```

## Initialize

Run the initializer from the target repository:

```bash
agent-maintainer init --track core --preset existing-app
```

Use `--dry-run` to preview the files first:

```bash
agent-maintainer init --track core --preset existing-app --dry-run
```

The initializer writes starter files such as:

- `config/pyproject.agent-maintainer.toml`
- `config/dev-dependencies.txt`
- `.pre-commit-config.yaml`
- `.github/workflows/verify.yml`

Merge the starter TOML into your root `pyproject.toml`, then tune source, test,
package, and coverage paths for the repository.

## Verify Setup

Run:

```bash
agent-maintainer doctor
agent-maintainer verify --profile precommit
```

Healthy verification should be quiet and end with:

```text
PASS
```

If it fails, inspect:

```bash
cat .verify-logs/LAST_FAILURE.md
```

Failure notes point to a run-scoped directory under `.verify-logs/runs/` so a
later hook run does not overwrite the details you need to repair the failure.

## Choose A Track

Use `core` for ordinary Python repositories. Use `agent` when Codex, Claude
Code, or another coding agent actively edits the repo. Use `hardening` when the
repo wants docs/config hygiene and security-adjacent starter files.

See also:

- [Agent hooks](agent-client-hooks.md)
- [Optional gates](optional-gates.md)
- [Diagnostics and repair loop](diagnostics-repair-loop.md)
