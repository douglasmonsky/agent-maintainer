# Generated Ratchet Guidance

This file is generated from `[tool.agent_maintainer]` by
`python3 -m agent_maintainer guidance`. Do not edit it by hand; update
configuration first, then regenerate it.

## Current Ratchet Configuration

- Current mode: `fresh-strict`
- Baseline path: `.agent-maintainer/ratchet-baseline.json`
- Target limit: `5`

## Top Ratchet Targets

- Start by listing current targets:
  `python3 -m agent_maintainer ratchet next --limit 5`.
- Use JSON output for automation:
  `python3 -m agent_maintainer ratchet next --format json`.

## One Target At A Time

- Work one ratchet target at a time unless a cohesive change plan exists.
- Prefer the top target when it is already in the current diff.
- Do not mix unrelated cleanup with the selected ratchet repair.

## Context Discipline

- Use bounded context commands instead of dumping whole files or logs.
- Start with the target's first command from `ratchet next`.
- Expand only the symbol, line range, diff hunk, or log section needed.

## Safe Context Commands

- `python3 -m agent_maintainer context file <path> --outline`
- `python3 -m agent_maintainer context file <path> --symbol <name>`
- `python3 -m agent_maintainer context diff --path <path> --hunks 5`
- `python3 -m agent_maintainer context failures --limit 20`

## Failure Discipline

- Treat new or worsened findings as repair targets, not suppressions.
- If a target is resolved, refresh baseline only after reviewing the diff.
- If status looks stale, inspect baseline provenance before changing code.

## Change-Plan Warning

- Large multi-file ratchet repairs need a cohesive change plan.
- Without a plan, split broad repairs into smaller ratchet targets.
