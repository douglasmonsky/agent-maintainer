+++
id = "generated-artifact-hygiene"
kind = "fix"
status = "complete"
base_ref = "origin/main"
expires = 2026-07-21
allowed_paths = [
  ".agent-maintainer/change-plans/**",
  "src/agent_maintainer/runtime_events/waste.py",
  "tests/runtime_events/test_runtime_event_waste.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 6
max_changed_lines = 400
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: generated-artifact-hygiene

## Why this change intentionally large

This branch improves generated-artifact waste reporting so agents can see the
bounded path sample and cleanup guidance instead of only a count.

## Why this should not be split smaller

The renderer and its regression test need to change together, and the previous
active roadmap plan must be retired so this focused branch passes change-budget.

## What allowed to change

Only the runtime-event waste renderer, focused runtime-event tests, and
change-plan records may change.

## What must not change

Do not delete generated files automatically, alter verifier thresholds, change
runtime-event schemas beyond the new optional cleanup hint, or touch unrelated
docs and configuration.

## Verification plan

Run the targeted runtime-event waste tests, Ruff on touched files, `git diff
--check`, and the broad verifier before merging.

## Rollback plan

Revert this branch's commits to restore prior count-only waste text rendering.

## Follow-up ratchet work

No ratchet baseline changes are expected. A later cleanup command can be planned
separately if manual inspection remains too costly.
