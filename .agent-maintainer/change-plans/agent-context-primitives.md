+++
id = "agent-context-primitives"
kind = "mechanical-migration"
status = "active"
base_ref = "origin/main"
expires = 2026-07-16
allowed_paths = [
  "src/agent_context/**",
  "src/{agent_maintainer/context => agent_context}/**",
  "src/agent_maintainer/context/**",
  "src/agent_maintainer/core/**",
  "src/agent_maintainer/hooks/**",
  "src/agent_maintainer/repair_plan/**",
  "src/agent_maintainer/verify/**",
  "tests/context/**",
  "docs/**",
  ".agent-maintainer/change-plans/agent-context-primitives.md",
  "AGENTS.agent-maintainer.md",
  "pyproject.toml",
]
forbidden_paths = [
  "config/prod/**",
  ".env",
  ".env.*",
]
max_changed_files = 120
max_changed_lines = 12000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: agent-context-primitives

## Why this change intentionally large

This change extracts context-pack primitives and safe file-reading helpers into
the new `agent_context` internal package. The move is intentionally large
because the extracted modules are used together by context CLI, context-pack
builder/rendering, hook context generation, repair-plan rendering, verifier
artifact summaries, and tests.

## Why this should not be split smaller

Splitting individual primitive modules across separate commits would leave the
repository in a half-migrated import state and would require repeated Tach,
guidance, and compatibility-shim updates. One scoped migration keeps the
dependency direction reviewable: `agent_context` must not import
`agent_maintainer`, while product-owned orchestration remains under
`agent_maintainer`.

## What allowed to change

- New `src/agent_context/**` primitive and reading modules.
- Compatibility shims under `src/agent_maintainer/context/**`.
- Import sites that now depend on `agent_context`.
- Tach domain files needed to express the new package boundary.
- Context-focused tests and compatibility assertions.
- Roadmap, ADR, generated guidance, and config path updates for the new source
  root.

## What must not change

- Public CLI behavior and context-pack output semantics.
- Verifier pass/fail logic, profile selection, and hook output contract.
- Runtime artifact filenames or `.verify-logs` layout.
- DocSync, vector, GraphQL, wiki, or retrieval experiment scope.
- Thresholds, coverage floors, suppression rules, or architecture strictness.

## Verification plan

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/docs/test_roadmap_docs.py tests/context -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer guidance --check`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer change-plan check`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m ruff check src/agent_context src/agent_maintainer/context src/agent_maintainer/verify/artifact_manifest.py src/agent_maintainer/verify/artifacts.py tests/context`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile full`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile security`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile manual`

## Rollback plan

Revert this commit to restore context primitives under
`agent_maintainer.context`. Because the public CLI and artifact formats are
unchanged, rollback does not require data migration or configuration migration.

## Follow-up ratchet work

Keep future context extraction phases separate. Do not move context-pack
builder/rendering, compression, ratchet context, or CLI ownership into
`agent_context` until product dependencies are inverted and covered by their
own focused change plan.
