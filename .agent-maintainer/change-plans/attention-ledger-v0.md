+++
id = "attention-ledger-v0"
kind = "feature"
status = "active"
base_ref = "origin/main"
expires = 2026-07-18
allowed_paths = ["src/**", "tests/**", "docs/**", "README.md", ".docsync/**", ".agent-maintainer/change-plans/**"]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 120
max_changed_lines = 12000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: attention-ledger-v0

## Why this change intentionally large

Phase 150 adds a new attention ledger command surface plus the supporting
deterministic scoring package. The change crosses CLI routing, local artifact
writing, Tach ownership, DocSync command-registry evidence, and focused tests.

## Why this should not be split smaller

Splitting the package from the CLI would leave unreachable code. Splitting the
CLI from DocSync attestations would knowingly leave stale documentation
evidence. The scope is still one coherent feature: file-level attention scoring.

## What allowed to change

- `src/agent_maintainer/attention/**` models, signals, builder, rendering, CLI.
- Top-level CLI command registry for `attention`.
- Focused `tests/attention/**` coverage.
- Tach domain ownership for the new package.
- README command-surface mention and DocSync attestations required by changed
  CLI evidence.
- Roadmap Phase 150 status.

## What must not change

- Existing verifier profile behavior.
- Existing runtime-event, context, DocSync, report, or repair-plan semantics.
- Existing hook behavior.
- Existing check names, thresholds, or gate strictness.

## Verification plan

- Focused attention tests.
- Ruff on attention source/tests and CLI routing.
- `python -m agent_maintainer attention update`.
- `python -m agent_maintainer attention top/explain/changed` smoke checks.
- `python -m docsync check`.
- `tach check --exact`.
- `python -m agent_maintainer verify --profile fast`.

## Rollback plan

Remove the attention package, top-level CLI routing, tests, Tach domain file,
README command mention, fresh DocSync attestations, and Phase 150 completion
mark. Restore the previous DocSync attestations only if the command registry
also returns to its previous fingerprint.

## Follow-up ratchet work

Phase 151 should use `.verify-logs/attention/files.json` to weight context
packs. Later phases can add attention quality measurements, but Phase 150 keeps
the score advisory and local.
