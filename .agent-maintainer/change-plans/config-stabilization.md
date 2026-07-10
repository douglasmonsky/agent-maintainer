+++
id = "config-stabilization"
kind = "architectural-refactor"
status = "active"
base_ref = "a7ce1bc"
expires = 2026-08-31
allowed_paths = [
  ".agent-maintainer/change-plans/**",
  "CHANGELOG.md",
  "README.md",
  "config/**",
  "docs/**",
  "justfile",
  "pyproject.toml",
  "src/**",
  "tach.toml",
  "tests/**",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 180
max_changed_lines = 18000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: config-stabilization

## Why this change intentionally large

Configuration currently spans neutral files, pyproject tables, environment
variables, workspaces, file baselines, command overrides, and generated public
metadata. One fail-closed registry must describe those surfaces together so a
guardrail cannot be weakened through a parser path that validates less policy.

## Why this should not be split smaller

Unknown-key detection, typed coercion, bounds, cross-field rules, command entry
validation, and generated reference metadata are one contract. Landing only one
piece would preserve an alternate source or nested table that still fails open.
Implementation may use focused commits but the branch exits only when every
public configuration source reaches the same validation boundary.

## What allowed to change

Change configuration models/loaders/coercion/validation, the public command
boundary, generated capability/reference metadata, relevant docs, and focused
tests. Each field or nested structure added to the registry must carry source,
type, default, constraints, environment metadata, and public description where
applicable.

## What must not change

Do not lower verifier thresholds, silently coerce invalid values, introduce
production configuration, change credentials, or broaden unrelated command
behavior. Preserve valid existing configuration precedence and compatibility;
invalid or unknown policy must stop before command construction.

## Verification plan

Add table-driven registry/coercion/bounds tests, typo fixtures for every nesting
level and source, precedence tests, and real public-entrypoint tests proving
invalid fresh-strict policy cannot execute behavior. Run Ruff, Wemake, Pylint,
Pyright, Xenon, file length, Tach exact, generated-currentness, DocSync,
change-plan validation, and the full profile before closing the tranche.

## Rollback plan

Keep registry, validation boundary, generated metadata, and command wiring in
focused commits. Revert a complete commit if necessary; never restore silent
unknown-key dropping or invalid numeric acceptance merely for compatibility.
Document a migration diagnostic instead.

## Follow-up ratchet work

Keep registry coverage and generated-currentness required in CI. New config
fields must declare their complete specification before use, and future sources
must feed the same validator rather than creating independent coercion rules.
