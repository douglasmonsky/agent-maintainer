+++
id = "ci-setup-ease"
kind = "feat"
status = "complete"
base_ref = "origin/main"
expires = 2026-07-23
allowed_paths = [
  ".agent-maintainer/change-plans/**",
  ".docsync/attestations/**",
  "README.md",
  "docs/quick-start.md",
  "docs/team-policy-templates.md",
  "docs/tool-map.md",
  "src/agent_maintainer/core/scaffold/initializer.py",
  "src/agent_maintainer/core/scaffold/templates.py",
  "tests/packaging/test_initializer.py",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 14
max_changed_lines = 420
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: ci-setup-ease

## Why this change intentionally large

This branch adds a CI-only initializer path, adjusts the generated workflow so
consumer repositories do not need to be installable Python packages, and updates
linked onboarding documentation plus DocSync attestations.

## Why this should not be split smaller

The CLI flag, workflow template, initializer regression tests, and quick-start
docs describe one adoption surface. Splitting them would leave either an
undocumented command or documentation for behavior not yet covered by tests.

## What allowed to change

Only initializer templates and CLI selection, focused initializer tests,
CI-onboarding docs, DocSync attestations for those docs, and change-plan records.

## What must not change

Do not change hook behavior, verifier thresholds, bootstrap behavior, package
metadata, wait orchestration, CI for this source repo, or unrelated provider
logic.

## Verification plan

- `python -m pytest tests/packaging/test_initializer.py tests/packaging/test_onboarding_smoke.py -q`
- `ruff check src/agent_maintainer/core/scaffold/initializer.py src/agent_maintainer/core/scaffold/templates.py tests/packaging/test_initializer.py`
- `tach check --exact`
- `python -m docsync check`
- `git diff --check`
- `python -m agent_maintainer verify --profile precommit --force`

## Rollback plan

Revert this branch commit to remove the `--ci-only` flag, restore the previous
generated workflow template, and remove the associated docs/test updates.

## Follow-up ratchet work

After dogfooding, consider adding CI-provider-specific starter variants for
GitLab, Buildkite, or reusable GitHub workflow calls if downstream repos need
those surfaces.
