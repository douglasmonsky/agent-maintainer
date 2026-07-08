+++
id = "runtime-efficacy-wait-metrics"
kind = "feat"
status = "active"
base_ref = "origin/main"
expires = 2026-07-22
allowed_paths = [
  ".agent-maintainer/change-plans/**",
  "src/agent_maintainer/assess/efficacy_followthrough.py",
  "tests/assess/test_efficacy.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 4
max_changed_lines = 300
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: runtime-efficacy-wait-metrics

## Why this change intentionally large

This branch adds runtime efficacy metrics for the background wait lifecycle
introduced by recent wait orchestration work.

## Why this should not be split smaller

The metric implementation and report fixture updates must change together so
the local efficacy assessment reports stable, tested fields.

## What allowed to change

Only the follow-through efficacy metrics, their focused tests, and change-plan
metadata may change.

## What must not change

Do not change runtime event schemas, wait CLI behavior, hook behavior,
heartbeat prompts, or verifier execution.

## Verification plan

Run focused efficacy tests, Ruff on touched Python files, `git diff --check`,
and broad CI before merging.

## Rollback plan

Revert this branch to remove the new metrics while preserving the existing
wait-helper success metric.

## Follow-up ratchet work

Use these metrics in the next repo assessment to compare foreground-blocked
waits, background registrations, silent heartbeat no-ops, and terminal claims.
