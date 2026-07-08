+++
id = "wait-targeted-heartbeat-sweep"
kind = "fix"
status = "complete"
base_ref = "origin/main"
expires = 2026-07-21
allowed_paths = [
  ".agent-maintainer/change-plans/**",
  "src/agent_maintainer/wait/cli.py",
  "src/agent_maintainer/wait/cli_parsers.py",
  "tests/wait/test_wait_cli_background.py",
  "tests/wait/test_wait_cli_targeted_sweep.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 6
max_changed_lines = 400
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: wait-targeted-heartbeat-sweep

## Why this change intentionally large

This branch adds a targeted one-shot wait sweep mode so Codex heartbeats can poll
one wait record without blocking and without printing stale unrelated waits.

## Why this should not be split smaller

The CLI parser, command behavior, and focused regression coverage need to change
together to make the new heartbeat-safe command usable.

## What allowed to change

Only wait CLI sweep parsing/dispatch, focused wait CLI tests, and change-plan
records may change.

## What must not change

Do not change foreground wait defaults, watcher spawning, wait record schemas, or
GitHub/verifier polling semantics beyond the new targeted one-shot CLI path.

## Verification plan

Run focused wait CLI tests, Ruff on touched files, `git diff --check`, and broad
CI before merging.

## Rollback plan

Revert this branch to remove the targeted one-shot sweep command and restore the
previous `--once`/`--watch` sweep surface.

## Follow-up ratchet work

Update generated heartbeat prompts to prefer `wait sweep --one <wait-id>` after
this command is available on main.
