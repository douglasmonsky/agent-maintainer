# Repository maintenance for AI-assisted Python changes

The goal is maintainable code, not just passing code. Treat Agent Maintainer checks as the source of truth.

Also read `AGENTS.agent-maintainer.md` before changing code. It is generated from
`[tool.agent_maintainer]` and summarizes the active mode, paths, thresholds, and
required verification commands. If Agent Maintainer configuration changes, regenerate it
with `python3 -m agent_maintainer guidance`.

## Verification workflow

Trusted agent hooks normally run fast checks after edits and the precommit
profile before completion. If those hooks are unavailable, were bypassed, or
need a failure reproduced manually, run:

```bash
python3 -m agent_maintainer verify --profile precommit
```

Before opening or merging a larger change, run:

```bash
python3 -m agent_maintainer verify --profile full
```

Do not claim completion while required hooks or manual checks fail. Do not lower
thresholds, delete checks, or add broad suppressions to make the pipeline pass.

If the repository does not use `src/` and `tests/`, configure `[tool.agent_maintainer]` in `pyproject.toml` instead of letting checks drift or fail ambiguously.

## Design rules

1. Prefer one coherent behavior change per commit.
2. Do not mix formatting-only changes, refactors, dependency changes, and behavior changes in the same commit unless explicitly requested.
3. Keep Python files below 600 physical lines and 450 source lines.
4. Keep functions small. Split functions above roughly 75 lines unless there is a specific, local reason.
5. Keep cyclomatic complexity under the configured Xenon/Radon thresholds.
6. Use explicit return types for public functions.
7. Add docstrings to public modules, classes, and functions when they define a durable boundary.
8. Prefer typed domain objects over unstructured dictionaries at internal boundaries.
9. Do not introduce new dependencies unless the standard library or existing dependencies are insufficient.
10. New behavior requires tests unless the repository explicitly sets `require_tests = false` for a documented reason.
11. Changed code should be covered by tests; CI enforces changed-code coverage.

## Suppression policy

Suppressions must be narrow and justified.

Allowed when justified:

```python
value = legacy_call()  # type: ignore[assignment]  # legacy API has incorrect stub
```

Avoid or fix instead:

```python
value = legacy_call()  # type: ignore
from module import *  # noqa
# pylint: disable=all
```

## Architecture policy

Domain code should not import CLI, UI, filesystem, database, network, or infrastructure modules.

Application code may orchestrate domain objects but should not import concrete infrastructure unless the project intentionally uses a simpler architecture.

Infrastructure code may depend inward on domain or application interfaces.

This repository uses `tach.toml` for architecture contracts. Keep `root_module = "forbid"` and explicit modules. If a change violates the Tach contract, refactor the boundary instead of adding an ignore.

If `tach.toml`, `tach.domain.toml`, or another architecture policy file changes, add or update an architecture decision note under `docs/architecture/decisions/`. The note must explain the boundary change, why it is necessary, why it is not architecture drift, alternatives considered, and what remains forbidden. Do not run `tach sync`, add dependencies, or relax strictness flags as a silent fix.

## DocSync policy

DocSync lives in `src/docsync/` as an extractable sibling package, not under
`src/agent_maintainer/`. DocSync must not import `agent_maintainer` or
`archguard`; use public `docsync.api` as the boundary for future integration.

DocSync repository state lives under `.docsync/`. Treat `.docsync/trace.yml` as
human-authored source truth. Treat `.docsync/out/` as generated output and do
not commit generated files from that directory except `.gitignore`.

When changing DocSync boundaries, update `src/docsync/tach.domain.toml`, the
root `tach.toml` ownership entry if needed, and an architecture decision note.
Do not relax DocSync extraction tests or add broad Tach ignores to make changes
pass.

## When a hook fails

Fix the root cause. Do not bypass hooks. If the hook is wrong, make the smallest possible correction to the hook or configuration and explain why in the PR notes.

Optional checks must be explicit. Missing optional architecture config is a skip only outside configured strict mode. This repository also enforces an Interrogate docstring-coverage ratchet. Missing Agent Maintainer package entrypoints, missing configured source roots in precommit/full/ci, missing required tests, or a broken package install are failures.
