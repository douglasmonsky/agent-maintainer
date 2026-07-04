<!-- docsync:object docs.agent_maintainer_guidance.overview -->
# Agent Maintainer Guidance

`AGENTS.agent-maintainer.md` is intentionally compact because agents load it
into working context repeatedly. It should tell a coding agent what to do now:
which roots matter, which limits block work, which gates are active, and which
commands prove the task.

This document is for humans who want the longer explanation.

## How The Sidecar Is Generated

Run:

```bash
python3 -m agent_maintainer guidance
```

The command reads `[tool.agent_maintainer]` from `pyproject.toml` and writes
`AGENTS.agent-maintainer.md`. Do not edit the generated file by hand. Change the
configuration or renderer, then regenerate.

## Why The Sidecar Is Short

The generated sidecar is part of agent working context. It should not list every
disabled integration, default, rationale, or tool an agent does not need for the
current repository.

The sidecar focuses on:

- hard working rules for small, tested, reviewable changes;
- generated/cache paths agents should not bulk-read;
- active source and test roots;
- architecture policy and ADR expectations;
- coding limits that commonly block work;
- active gates only;
- exact verification commands.

Disabled checks are omitted. Detailed gate inventories belong in
[optional gates](optional-gates.md) and the verification catalog.

## Quiet Agent Workflow

Agent Maintainer should reduce repair-loop noise, not become another source of
context waste. Agent-facing output should stay summary-first:

- check current branch/worktree state before edits, but do not re-read long
  guidance files unless starting fresh, context was compacted, branch changed,
  or guidance/config files changed;
- if guidance was already read in current unchanged context, use targeted `rg`
  or a narrow excerpt for the specific rule needed;

- completed check, actionable failure, or material plan change;
- pass/fail status, profile, run id, duration, failed checks, and exact next
  command;
- no routine "still running" updates for expected long checks;
- no narration for every focused rerun;
- no pasted raw logs when a run-scoped artifact can be referenced instead.

Manual source edits should use `apply_patch`. Avoid heredoc rewrite commands
such as `python3 - <<'PY'` for ordinary source edits because they are noisy,
harder to review, and bypass this repo's preferred patch workflow.

## Verification Cadence

The final verification bar should stay strict, but inner-loop checks should be
proportional to the change:

- small edit loop: run affected tests and touched-file lint only;
- coherent chunk: run the related focused suite plus `tach check --exact` or
  `python3 -m agent_maintainer change-plan check` when architecture or change
  budgets are involved;
- before commit: rely on trusted Stop/SubagentStop hooks when they already ran
  `precommit` for the final same-state tree; run
  `python3 -m agent_maintainer verify --profile precommit` only when hooks are
  unavailable, bypassed, or a failure needs manual reproduction;
- before PR or merge: run one broad local profile, usually `full`;
- use `ci` locally instead of `full` when diff/base-ref handling, CI profile,
  workflow behavior, or verifier profile selection changed;
- run both `full` and `ci` only when verifier/profile/CI-diff behavior is under
  test;
- run `security` or `manual` when touching those gates, before release, or when
  explicitly requested;
- before release: run release-only packaging checks.

Failure summaries should recommend the smallest useful rerun command. When
several checks fail, the verifier may fall back to the current profile command.

## Failure Expansion

Passing runs should stay quiet. Failed runs should provide a repair capsule:
result, profile, run id, top repair facts, one likely next action, and one
`Expand only if needed` command.

Do not load full context packs or raw logs unless the capsule is insufficient.

`LAST_FAILURE.md` is a latest-failure pointer and can change after another agent
or hook run. Failed runs also write retained snapshots under:

```text
.verify-logs/runs/<run-id>/
```

Use run-scoped expansion commands when repairing a specific failure:

```bash
python3 -m agent_maintainer context failures \
  --log-dir .verify-logs/runs/<run-id> \
  --limit 20
```

Retention is controlled by:

```toml
[tool.agent_maintainer.diagnostics]
run_history_limit = 10
```

## Active Gates

An active gate is a check the repository currently expects agents to respect.
Examples include strict style, docstring coverage, security scanners,
docs/config linters, release artifacts, and mutation testing when enabled.

Disabled optional tools are intentionally absent from generated guidance. They
remain discoverable in `pyproject.toml`, [optional gates](optional-gates.md),
[tool map](tool-map.md), and the verification catalog.

## When To Regenerate

Regenerate after changing:

- `[tool.agent_maintainer]`;
- verification profiles or thresholds;
- source, test, package, or coverage roots;
- active scanner or docs/config gate settings;
- architecture-tool configuration.

Then run:

```bash
python3 -m agent_maintainer guidance --check
python3 -m agent_maintainer doctor
```

## What Belongs Elsewhere

Long-form rationale, migration notes, and tool inventories belong in docs, not
in `AGENTS.agent-maintainer.md`.

- [Quick start](quick-start.md)
- [Diagnostics repair loop](diagnostics-repair-loop.md)
- [Optional gates](optional-gates.md)
- [Mutation testing](mutation-testing.md)
- [Architecture policy](architecture-policy.md)
- [Tool map](tool-map.md)
- [Architecture decisions](architecture/decisions/)
- [Troubleshooting](troubleshooting.md)
- [Roadmap](ROADMAP.md)
<!-- docsync:object.end docs.agent_maintainer_guidance.overview -->
