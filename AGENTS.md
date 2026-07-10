# Repository Maintenance

For AI-assisted Python changes, the goal is maintainable code, not just passing
code. Treat Agent Maintainer checks as source truth.

Read `AGENTS.agent-maintainer.md` when starting fresh, after context
compaction, or when guidance/config files changed. If already read in current
unchanged context, do not re-read it ritualistically; use targeted `rg` for
the specific rules. It is the generated `[tool.agent_maintainer]` summary of
active mode, paths, thresholds, verification commands. If Agent Maintainer
configuration changes, regenerate with:

```bash
just guidance
```

## Serena

When Serena tools are available, activate the current repository and read
Serena's initial instructions before substantial code exploration or
refactoring.

Prefer Serena's symbol-aware tools for definitions, references,
implementations, file and class structure, IDE inspections, debugging, and
cross-file refactoring. Continue using `rg` for literal text, configuration,
documentation, generated files, and non-symbol searches.

Treat Serena memories as curated guidance rather than authoritative state.
Verify claims against current code, configuration, Git history, and tests.
Store only stable, reusable repository knowledge; never store secrets,
credentials, private data, or temporary task progress.

Inspect the resulting diff and run the repository's normal validation commands
after Serena-assisted edits. If Serena is unavailable, continue with native
repository tools rather than blocking the task.

## Verification Workflow

Trusted agent hooks normally run fast checks after edits and the precommit
profile before completion. Do not duplicate a same-state hook pass manually.
If hooks are unavailable, bypassed, or need a failure reproduced manually, run:

```bash
just vp
```

Before opening or merging a larger change, reach a coherent final state, then
run one broad local profile, usually:

```bash
just v
```

Use `ci` instead when diff/base-ref, workflow, or profile behavior changed: `just vc`. Run
both `full` and `ci` only when that overlap is under test. Run `security` or
`manual` when touching those gates, before release, or when explicitly requested.

Use `just wg <run-id>`, `just wp <pr-number>`, or `just wv <run-id>` for long
GitHub Actions or verifier jobs instead of hand-polling.

Do not claim completion while required hooks or checks for the touched surface
fail. Treat `manual` as required only when requested, before release, or when
manual gates are touched. Do not lower thresholds, delete checks, or add broad
suppressions to make the pipeline pass.

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
