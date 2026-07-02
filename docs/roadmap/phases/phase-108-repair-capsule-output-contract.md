# Phase 108: Repair Capsule Output Contract And Pointer-First Context

## Status

Completed.

## Goal

Make agent-facing failure output compact, deterministic, and immediately
actionable. Agent Maintainer should reduce context load by default: print a
strict repair capsule, write detailed context to run-scoped artifacts, and
provide one explicit expansion command when more evidence is needed.

## Scope

- Define and enforce a strict repair capsule output contract:

  ```text
  Result: FAIL
  Profile: precommit
  Run ID: <id>

  Top repair facts:
  1. <check>: <file>:<line> <message>
  2. ...

  Likely next action:
  <one command or one file/symbol to inspect>

  Expand only if needed:
  <context command>
  ```

- Use the same shape for hook failure context where feasible.
- Keep raw logs, long traces, full context packs, and detailed diagnostics in
  `.verify-logs/runs/<run-id>/` or the existing `.verify-logs/context/`
  artifacts.
- Make `context pack` pointer/write-only by default for agent-facing use.
- Add an explicit expansion mode for printing the full pack when a human or
  agent intentionally asks for it.
- Replace hook wording that says `Read: PACK.md` with pointer language that
  discourages loading full packs by default.
- Update docs and tests so future changes cannot regress into transcript-heavy
  output.

## Non-Goals

- No new scanner categories.
- No verifier profile changes.
- No changes to check pass/fail semantics.
- No removal of full context pack artifacts.
- No old-name compatibility work.

## Acceptance Criteria

- Failed verifier output starts with `Result: FAIL`, `Profile:`, and `Run ID:`.
- Failure summaries include bounded top repair facts, one likely next action,
  and one expansion command.
- Hook output uses the same repair-capsule vocabulary and does not say
  `Read: .verify-logs/context/PACK.md`.
- `python -m agent_maintainer context pack` writes the pack and prints a compact
  pointer by default.
- Full pack printing remains available behind an explicit flag.
- Tests cover verifier output, hook output, and context pack CLI defaults.

## Verification

- `pytest tests/core/test_reporting_artifacts.py tests/context/test_packs.py tests/hooks/test_hook_runtime.py tests/hooks/test_hook_output_invariants.py -q`
- `python -m agent_maintainer guidance --check`
- `python -m agent_maintainer change-plan check`
- `tach check --exact`
- Final verifier profiles after implementation.

## Notes For Future Tasks

The repair capsule is a product primitive. Prefer extending structured repair
facts and artifact pointers over adding raw tool output to agent-facing text.
