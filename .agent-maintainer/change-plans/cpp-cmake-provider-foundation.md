+++
id = "cpp-cmake-provider-foundation"
kind = "feature"
status = "complete"
base_ref = "origin/main"
expires = 2026-08-02
allowed_paths = [
  ".agent-maintainer/change-plans/cpp-cmake-provider-foundation.md",
  ".agent-maintainer/contracts-baseline.json",
  ".docsync/**",
  "CHANGELOG.md",
  "README.md",
  "config/agent-maintainer-capabilities.json",
  "config/dev-lock.txt",
  "docs/**",
  "pyproject.toml",
  "src/**",
  "tests/**",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 80
max_changed_lines = 5000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: C/C++ CMake Provider Foundation

## Why this change intentionally large

The roadmap, configuration contract, provider registry, conservative
classification, advisory suppression evidence, static doctor diagnostics,
generated metadata, documentation, and prerelease notes form one honest
disabled-by-default foundation. Shipping only part of that boundary would
either expose unsupported configuration or claim provider behavior without
the diagnostics and documentation needed to evaluate it safely.

## Why this should not be split smaller

Implementation remains split into focused commits, but the repository change
budget evaluates the complete branch against `origin/main`. This one plan
covers the approved C/C++ design and Phase 187 implementation while its path,
line, and file limits exclude later command execution and report parsing.

## What allowed to change

Only the C/C++ roadmap and boundary docs, nested configuration, provider
metadata, path classification, advisory suppression dispatch, static doctor,
generated public metadata, compatibility baseline, release-candidate records,
and their focused tests may change. Shared modules may change only where the
new disabled provider must register through an existing extension point.

## What must not change

Do not execute compiler, formatter, analyzer, build, test, or coverage
commands. Do not add report parsing, blocking C/C++ policy, setup mutation,
credentials, production configuration, workflow changes, or provider-maturity
claims. Preserve Python, TypeScript, and Java behavior and public constructor
compatibility.

## Verification plan

Use red-green focused tests for configuration, classification, suppression,
registry selection, doctor diagnostics, generated metadata, and compatibility.
Run Ruff, Wemake, Pylint, Pyright, Tach, documentation checks, secret scanning,
the exact CI static-policy group against `origin/main`, and the full verifier.
Require the hosted pull-request matrix and independent review to pass.

## Rollback plan

Revert the focused Phase 187 commits in reverse order. The provider remains
disabled by default, never executes commands, and creates no external or
persistent migration state.

## Follow-up ratchet work

Phase 187 and its b12 release evidence are complete. Phase 188 may now wire
explicit commands and bounded artifacts under a separate plan. Static-analysis
facts, test/coverage facts, and cross-platform live proof remain in Phases 189
through 191.
