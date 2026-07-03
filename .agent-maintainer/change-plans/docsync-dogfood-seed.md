+++
id = "docsync-dogfood-seed"
kind = "docs-config-sync"
status = "active"
base_ref = "origin/main"
expires = 2026-07-16
allowed_paths = [
  ".agent-maintainer/change-plans/agent-run-artifacts-primitives.md",
  ".agent-maintainer/change-plans/docsync-dogfood-seed.md",
  ".docsync/trace.yml",
  "docs/ROADMAP.md",
  "docs/architecture/decisions/2026-07-03-docsync-dogfood-evidence-markers.md",
  "docs/docsync-extraction.md",
  "docs/roadmap/full-roadmap-blueprint.md",
  "docs/roadmap/phases/phase-114-docsync-dogfood-ratchet.md",
  "src/docsync/cli.py",
  "src/docsync/commands/core.py",
  "src/docsync/comments/scanner.py",
  "src/docsync/tach.domain.toml",
  "tests/docsync/test_boundaries.py",
  "tests/docsync/test_docsync_cli.py",
]
forbidden_paths = [
  "config/prod/**",
  ".env",
  ".env.*",
  ".docsync/out/**",
]
max_changed_files = 20
max_changed_lines = 1200
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: docsync-dogfood-seed

## Why this change intentionally large

DocSync had an empty trace, so the repository was not dogfooding the
docs-to-evidence workflow it now contains. This branch seeds a narrow trace for
DocSync's own extraction contract, adds the source/test evidence anchors that
the trace requires, and adjusts the CLI test that previously assumed this
checkout's trace was empty.

## Why this should not be split smaller

The trace, documentation object, evidence anchors, and empty-trace test update
are one coherent DocSync adoption seed. Splitting them would leave either a
trace without live anchors or anchors without a validating trace.

## What allowed to change

Allowed changes are limited to:

- DocSync trace source truth.
- DocSync extraction notes and roadmap tracking.
- Explicit evidence markers in DocSync source/test files.
- The DocSync CLI empty-trace test fixture.
- This change-plan file.

## What must not change

The branch must not make DocSync a blocking Agent Maintainer verifier gate or
broaden the trace to all public docs.

## Verification Plan

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync doctor`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync index`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check --base origin/main`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/docsync -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m ruff check src/docsync tests/docsync`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer guidance --check`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer change-plan check`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile full`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile security`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile manual`

## Rollback Plan

Restore the empty trace and remove the evidence markers. The runtime behavior
of DocSync and Agent Maintainer is unchanged, so rollback does not require data
migration.

## Follow-Up Ratchet Work

After the current extraction sequence settles, review public docs in small
groups and add DocSync coverage for durable user-facing claims. Keep broad docs
coverage advisory until the signal quality is proven.
