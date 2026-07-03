# Repository Maintenance

For AI-assisted Python changes, the goal is maintainable code, not just passing
code. Treat Agent Maintainer checks as source truth.

Also read `AGENTS.agent-maintainer.md` before changing code. It is generated
from `[tool.agent_maintainer]` and summarizes active mode, paths, thresholds,
and required verification commands. If Agent Maintainer configuration changes,
regenerate it with:

```bash
python3 -m agent_maintainer guidance
```

## Verification Workflow

Trusted agent hooks normally run fast checks after edits and the precommit
profile before completion. If hooks are unavailable, bypassed, or need a failure
reproduced manually, run:

```bash
python3 -m agent_maintainer verify --profile precommit
```

Before opening or merging a larger change, run:

```bash
python3 -m agent_maintainer verify --profile full
```

Do not claim completion while required hooks or manual checks fail. Do not lower
thresholds, delete checks, or add broad suppressions to make the pipeline pass.

If the repository does not use `src/` and `tests/`, configure
`[tool.agent_maintainer]` in `pyproject.toml` instead of letting checks drift or
fail ambiguously.

## Design Rules

1. Prefer one coherent behavior change per commit.
2. Do not mix formatting-only changes, refactors, dependency changes, and
   behavior changes in the same commit unless explicitly requested.
3. Keep Python files below 600 physical lines and 450 source lines.
4. Keep functions small. Split functions above roughly 75 lines unless there is
   a specific local reason.
5. Keep cyclomatic complexity under configured Xenon/Radon thresholds.
6. Use explicit return types for public functions.
7. Add docstrings to public modules, classes, and functions that define durable
   boundaries.
8. Prefer typed domain objects over unstructured dictionaries at internal
   boundaries.
9. Do not introduce new dependencies unless the standard library and existing
   dependencies are insufficient.
10. New behavior requires tests unless the repository explicitly sets
    `require_tests = false` with a documented reason.
11. Changed code should be covered by tests; CI enforces changed-code coverage.

## Suppression Policy

Suppressions must be narrow and justified.

Allowed when justified:

```python
value = legacy_call()  # type: ignore[assignment]  # legacy API has incorrect stub
```

Avoid or fix instead:

```python
value = legacy_call()  # type: ignore  # noqa  # pylint: disable=all
```

## Architecture Policy

Domain code should not import CLI, UI, filesystem, database, network, or
infrastructure modules.

Application code may orchestrate domain objects, but it should not import
concrete infrastructure unless the project intentionally uses simpler
architecture.

Infrastructure code may depend inward on domain or application interfaces.

This repository uses `tach.toml` architecture contracts. Keep
`root_module = "forbid"` and explicit modules. If a change violates a Tach
contract, refactor the boundary instead of adding an ignore.

If `tach.toml`, `tach.domain.toml`, or another architecture policy file changes,
add or update an architecture decision note under `docs/architecture/decisions/`.
The note must explain:

- what boundary changed;
- why it was necessary;
- why it is not architecture drift;
- alternatives considered;
- what remains forbidden.

Do not run `tach sync`, add dependencies, or relax strictness flags as a silent
fix.

## DocSync Policy

DocSync lives in `src/docsync/` as an extractable sibling package, not under
`src/agent_maintainer/`.

DocSync must not import `agent_maintainer` or `archguard`; use the public
`docsync.api` boundary for future integration.

DocSync repository state lives under `.docsync/`. Treat `.docsync/trace.yml` as
human-authored source truth. Treat `.docsync/out/` as generated output; do not
commit generated files in that directory except `.gitignore`.

When changing DocSync boundaries, update `src/docsync/tach.domain.toml`, the root
`tach.toml` ownership entry if needed, and an architecture decision note.

Do not relax DocSync extraction tests or add broad Tach ignores to make changes
pass.

## When A Hook Fails

Fix the root cause. Do not bypass hooks.

If a hook is wrong, make the smallest possible correction to the hook or
configuration and explain why in PR notes.

Optional checks must be explicit. Missing optional architecture config may skip
only outside configured strict mode.

This repository also enforces an Interrogate docstring-coverage ratchet. Missing
Agent Maintainer package entrypoints, missing configured source roots in
precommit/full/ci, missing active docs/config tooling, stale guidance, stale
DocSync traces, or stale architecture decisions are repo issues, not hook noise.
