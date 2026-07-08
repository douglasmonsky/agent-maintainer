+++
id = "wait-heartbeat-one-shot-prompts"
kind = "fix"
status = "active"
base_ref = "origin/main"
expires = 2026-07-21
allowed_paths = [
  ".agent-maintainer/change-plans/**",
  "src/agent_waits/broker.py",
  "tests/wait/test_agent_waits_core.py",
  "docs/codex-hooks.md",
  "docs/agent-client-hooks.md",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 7
max_changed_lines = 400
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: wait-heartbeat-one-shot-prompts

## Why this change intentionally large

This branch updates generated Codex heartbeat requests to use the new targeted
one-shot wait sweep command.

## Why this should not be split smaller

The request renderer, regression test, and Codex-facing guidance must change
together so generated automation instructions match the supported CLI.

## What allowed to change

Only the wait request renderer, its focused tests, Codex wait docs, and
change-plan records may change.

## What must not change

Do not change wait record schemas, watcher spawning, foreground wait policy, or
the `wait heartbeat` repo-level fallback command.

## Verification plan

Run focused wait-core tests, Ruff on touched Python files, docs checks where
applicable, `git diff --check`, and broad CI before merging.

## Rollback plan

Revert this branch to make generated heartbeat requests use the repo-level
heartbeat command again.

## Follow-up ratchet work

Dogfood the generated request on the next PR wait to confirm it neither blocks
nor surfaces stale unrelated waits.
