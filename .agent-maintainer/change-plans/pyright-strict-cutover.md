+++
id = "pyright-strict-cutover"
kind = "mechanical-migration"
status = "complete"
base_ref = "origin/main"
expires = 2026-07-25
allowed_paths = [
  ".agent-maintainer/change-plans/pyright-strict-cutover.md",
  "config/pyright-strict-baseline.json",
  "docs/roadmap/phases/phase-75-below-10-debt-and-strict-typing-ratchets.md",
  "docs/superpowers/plans/2026-07-11-strict-pyright-cutover.md",
  "docs/superpowers/specs/2026-07-11-strict-pyright-cutover-design.md",
  "pyproject.toml",
  "tests/config/test_pyright_strict_config.py",
]
forbidden_paths = ["src/**", ".github/**", "config/prod/**", ".env", ".env.*"]
max_changed_files = 7
max_changed_lines = 500
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = ["tests/config/test_pyright_strict_config.py"]
+++
# Cohesive Change Plan: pyright-strict-cutover

## Why this change intentionally large

The dogfood repository has completed its strict-typing migration and now has
zero strict diagnostics across 740 analyzed files. Repository policy, the
obsolete baseline artifact, its focused regression test, and the roadmap
completion note must move together so enforcement cannot become ambiguous.

## Why this should not be split smaller

Deleting the baseline before promoting ordinary Pyright would remove strict
enforcement, while promoting ordinary Pyright without disabling the ratchet
would retain duplicate checks and a meaningless zero baseline. The seven-file
branch includes the already-approved design and execution plan plus one atomic
policy cutover.

## What allowed to change

Only this change plan, the cutover design/implementation plan, repository
Pyright settings, the zero baseline deletion, the focused config-policy test,
and the Phase 75 completion note may change.

## What must not change

Do not modify reusable ratchet source, configuration schema/defaults, generated
consumer references, workflows, dependencies, profiles, production config, or
environment files. Do not add suppressions, unchecked casts, or permissive
types.

## Verification plan

Use a red test to prove the old dogfood policy, then promote ordinary Pyright to
strict, disable the repository ratchet, and delete the baseline. Run focused
config tests, ordinary and ratchet runner checks, Ruff, formatting, change-plan
validation, and the full local verifier. Merge only after CodeQL, Python
3.11-3.14, hosted verification, and review state are clean.

## Rollback plan

Revert the cutover commit and its two documentation commits to restore standard
ordinary checking, the enabled ratchet, and the reviewed zero baseline.

## Follow-up ratchet work

No dogfood ratchet debt remains. Keep the reusable migration feature covered and
documented for downstream repositories, while all future changes in this
repository must pass ordinary strict Pyright at zero errors.
