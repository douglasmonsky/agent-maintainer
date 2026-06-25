# Repository guardrails for AI-assisted Python changes

The goal is maintainable code, not just passing code. Treat the guardrails as the source of truth.

## Required workflow

Before finishing any code task, run:

```bash
python3 scripts/guardrail.py verify --profile precommit
```

Before opening or merging a larger change, run:

```bash
python3 scripts/guardrail.py verify --profile full
```

Do not claim completion while these checks fail. Do not lower thresholds, delete checks, or add broad suppressions to make the pipeline pass.

If the repository does not use `src/` and `tests/`, configure `[tool.ai_guardrails]` in `pyproject.toml` instead of letting checks drift or fail ambiguously.

## Design rules

1. Prefer one coherent behavior change per commit.
2. Do not mix formatting-only changes, refactors, dependency changes, and behavior changes in the same commit unless explicitly requested.
3. Keep Python files below 600 physical lines and 450 source lines.
4. Keep functions small. Split functions above roughly 75 lines unless there is a specific, local reason.
5. Keep cyclomatic complexity under the configured Xenon/Radon thresholds.
6. Use explicit return types for public functions.
7. Prefer typed domain objects over unstructured dictionaries at internal boundaries.
8. Do not introduce new dependencies unless the standard library or existing dependencies are insufficient.
9. New behavior requires tests unless the repository explicitly sets `require_tests = false` for a documented reason.
10. Changed code should be covered by tests; CI enforces changed-code coverage.

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

If `.importlinter` is configured, respect it. If a change violates the import contract, refactor the boundary instead of adding an ignore.

## When a hook fails

Fix the root cause. Do not bypass hooks. If the hook is wrong, make the smallest possible correction to the hook or configuration and explain why in the PR notes.

Optional checks must be explicit. A missing `.importlinter` is an optional skip. Missing guardrail scripts, missing configured source roots in precommit/full/ci, missing required tests, or a broken package install are failures.
