# Architecture Decision: Add Cohesive-Change Override Check

Status: accepted

## What Changed?

`tach.toml` now explicitly assigns `agent_maintainer.checks.cohesive_override`
to the existing runtime/checks module boundary.

## Why Was This Necessary?

The change-budget checker now delegates override validation to a focused helper
module. Keeping that logic in its own check module makes the PR-body parsing,
path eligibility rules, and size-limit validation testable without expanding
the existing budget-check module.

## Why Is This Not Architecture Drift?

This does not relax any Tach rule or add a new dependency direction. The new
module stays inside the existing check/runtime boundary and depends on shared
configuration plus the source-change model. It does not import CLI, doctor, hook,
or verifier orchestration code.

## Alternatives Considered

- Keep all override logic inside `change_budget.py`. Rejected because it would
  increase complexity in a file that already owns budget calculation and CLI
  reporting.
- Add a new architecture layer for overrides. Rejected because the behavior is
  still part of change-budget checking, not a separate subsystem.

## Still Forbidden

Check modules must not depend on CLI orchestration, doctor setup, hook client
wrappers, or verifier reporting. Future override features should remain narrow
and should not become a general bypass mechanism for unrelated quality gates.
