+++
id = "broad-known-wait-orchestration"
kind = "migration"
status = "active"
base_ref = "origin/main"
expires = 2026-07-20
allowed_paths = ["src/**", "tests/**", "docs/**", ".agent-maintainer/change-plans/**", "pyproject.toml"]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 120
max_changed_lines = 12000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: broad-known-wait-orchestration

## Why this change intentionally large

Codex foreground waiters were still possible for GitHub run and verifier waits,
and the PR-only background sweeper could not support the broader known-wait
contract. This change intentionally touches the reusable wait core, maintainer
wait adapters, CLI, hooks, docs, and tests so all known wait kinds share one
background registration and sweep path.

## Why this should not be split smaller

Splitting the handler registry, CLI guards, hook handoff, and heartbeat request
shape would leave intermediate branches where some known waits still foreground
poll in Codex or the sweeper cannot resume records it can register. The code is
split internally by responsibility and can still be reviewed by subsystem.

## What allowed to change

Allowed paths are the wait core, Agent Maintainer wait adapters, Codex/Claude
hook integration, runtime wait events, wait-focused tests, architecture
decisions, and Codex hook docs.

## What must not change

Do not alter production credentials, external account settings, unrelated
verification profiles, or arbitrary tool-use interception. Do not persist Codex
thread ids, API keys, hook stdin, prompts, or private payloads in wait records.

## Verification plan

Run targeted wait, hook, and runtime-event tests; Ruff check and format check on
the touched surface; `tach check --exact`; `python -m docsync check`;
`git diff --check`; and the full Agent Maintainer verifier profile.

## Rollback plan

Revert the handler registry, CLI background guards, hook handoff changes, and
structured heartbeat rendering together. The fallback foreground wait commands
remain available when `AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT=1` is set.

## Follow-up ratchet work

After dogfooding, review runtime wait events for foreground-blocked and
background-ready counts. If stable, consider the next phase for broader known
Bash watcher classification, still separate from arbitrary tool-call
interception.
