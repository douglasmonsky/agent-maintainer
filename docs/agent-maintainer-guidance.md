# Agent Maintainer Guidance

`AGENTS.agent-maintainer.md` is intentionally compact because agents load it into
working context repeatedly. It should tell a coding agent what to do, which
paths not to bulk-read, what limits matter, and which commands prove the work.

This document is for humans who want the fuller explanation.

## How The Sidecar Is Generated

Run:

```bash
python3 -m agent_maintainer guidance
```

The command reads `[tool.agent_maintainer]` from `pyproject.toml` and writes
`AGENTS.agent-maintainer.md`. Do not edit the generated file by hand. Change
configuration or the renderer, then regenerate.

## Why The Sidecar Is Short

The generated sidecar is part of the agent working context. It should not list
every disabled integration, default, long rationale, or tool the agent does not
need for the current repository.

Disabled checks are omitted. Active gates are listed only when they affect work
in this repo. The sidecar focuses on:

- working rules for small, tested, reviewable changes;
- generated/cache paths agents should not read in bulk;
- active source/test roots;
- architecture policy and ADR requirements;
- coding limits that commonly block work;
- active gates only;
- commands required before completion.

## Quiet Agent Workflow

Agent Maintainer should reduce repair-loop noise, not become another source of
context waste. Agent-facing output should be summary-first:

- completed check, actionable failure, or material plan change;
- pass/fail status, profile, run id, failed checks, exact next commands;
- no routine "still running" updates for expected long checks;
- no narration for every focused rerun;
- no pasted raw logs when a run-scoped artifact can be referenced instead.

Manual file edits should use `apply_patch`. Avoid heredoc rewrite commands such
as `python3 - <<'PY'` for ordinary source edits because they are noisy, harder
to review, and bypass the repo's preferred patch workflow.

## Verification Cadence

The final verification bar should stay strict, but inner-loop checks should be
proportional to the change:

- small edit loop: run affected tests and touched-file lint only;
- coherent chunk: run the related focused suite plus `tach check --exact` or
  `python3 -m agent_maintainer change-plan check` when architecture or change
  budgets are involved;
- before commit: run `python3 -m agent_maintainer verify --profile precommit`;
- before PR or merge: run `full`, `ci`, `security`, and `manual` once;
- before release: run release-only packaging checks.

Failure summaries should recommend the smallest useful rerun command instead of
implying every profile must be rerun after every small fix.

## Failure Expansion

Passing runs should stay quiet. Failed runs should provide just-in-time context
commands next to the failing checks instead of forcing agents to guess which log
or manifest to open.

`LAST_FAILURE.md` is the latest failure pointer and can change after another
agent or hook run. To avoid stale context, failed runs also write retained
snapshots under:

```text
.verify-logs/runs/<run-id>/
```

Those snapshots include a run-scoped manifest, failure note, and copied check
logs. Snapshot expansion commands include `--log-dir .verify-logs/runs/<run-id>`
so agents can inspect the exact failed run even if another verifier run happens
later.

Retention is controlled by:

```toml
[tool.agent_maintainer.diagnostics]
run_history_limit = 10
```

Use `0` only when run history must be disabled.

## Active Gates

An active gate is a check the repository currently expects agents to respect.
Examples include strict style, docstring coverage, security scanners,
docs/config linters, and release artifacts when enabled in configuration.

Disabled optional tools are intentionally absent from the generated sidecar.
They remain discoverable in `pyproject.toml`, `docs/tool-map.md`, and the
verification catalog, but they do not need to consume agent context.

## When To Regenerate

Regenerate after changing:

- `[tool.agent_maintainer]`;
- verification profiles or thresholds;
- source/test/package roots;
- active scanner or docs/config gate settings;
- architecture-tool configuration.

Then run:

```bash
python3 -m agent_maintainer guidance --check
python3 -m agent_maintainer doctor
```

## What Belongs Elsewhere

Long-form rationale, migration notes, and tool inventories belong in normal
docs, not in `AGENTS.agent-maintainer.md`.

Use:

- `docs/tool-map.md` for the supported-tool catalog.
- `docs/architecture/decisions/` for boundary decisions.
- `docs/troubleshooting.md` for failure recovery.
- `docs/roadmap/` for future work.
