<!-- docsync:object docs.quick_start.overview -->
# Quick Start

This is the shortest package-first path for trying Agent Maintainer in a Python
repository.

## Install

Install the core dependency set:

```bash
python -m pip install "agent-maintainer[core]"
```

For source-checkout development on Agent Maintainer itself, use an editable
install instead:

```bash
python -m pip install -e ".[core]"
```

## Initialize

Run the initializer from the target repository:

```bash
agent-maintainer init --track core --preset existing-app
```

Preview the files first with `--dry-run`:

```bash
agent-maintainer init --track core --preset existing-app --dry-run
```

Preview classifies every destination as `ADD`, `UNCHANGED`, `MERGE`, `CONFLICT`,
or `SKIP` and never requires `--force`. Apply is all-or-nothing when unresolved
conflicts remain. Supported dependency, package metadata, Codex, and Claude
files merge without deleting unrelated content; existing `AGENTS.md` is
preserved. Explicitly forced conflicts are backed up under Git-private
`.git/agent-maintainer/backups/init/<transaction>/` storage with rollback
instructions. Non-Git targets fall back to `.agent-maintainer/backups/init/`.

The initializer writes starter files:

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

A healthy verification run is intentionally quiet:

```text
PASS
```

If verification fails, inspect the bounded repair note first:

```bash
cat .verify-logs/LAST_FAILURE.md
```

Failure notes point at a run-scoped directory under `.verify-logs/runs/`, so a
later hook run does not overwrite details needed to repair the failure.

## Choose Track

Use `core` for ordinary Python repositories.

Use `agent` when Codex, Claude Code, or another coding agent actively edits the
repo.

Use `hardening` when the repo should also start with docs/config hygiene and
security-adjacent starter files.

Read more:

- [Agent hooks](agent-client-hooks.md)
- [Optional gates](optional-gates.md)
- [Diagnostics repair loop](diagnostics-repair-loop.md)
<!-- docsync:object.end docs.quick_start.overview -->
