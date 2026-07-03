+++
id = "agent-context-compression"
kind = "single-pr"
status = "active"
base_ref = "origin/main"
expires = 2026-07-16
allowed_paths = ["src/**", "tests/**", "docs/**", ".agent-maintainer/change-plans/**"]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 120
max_changed_lines = 12000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: agent-context-compression

## Why this change intentionally large

Context compression is the next coherent internal-package boundary after Phase
118 moved rendering and sanitizing. The compression request/result contracts,
deterministic backends, and optional Headroom adapter are reusable repair-loop
primitives and do not require `MaintainerConfig`, verifier scheduling, hook
runtime, or CLI orchestration.

## Why this should not be split smaller

Moving only one compression file would leave imports split across product and
primitive packages and make Tach ownership less clear. This PR still keeps the
slice bounded: context-pack build orchestration, CLI behavior, ratchet context,
and user-facing compression options remain product-owned.

## What allowed to change

- Add `agent_context.compression` modules for models, deterministic backends,
  and Headroom adapter.
- Keep `agent_maintainer.context.compression.*` compatibility shims.
- Update product context-pack compression imports to consume `agent_context`.
- Update Tach domain contracts, architecture decision notes, roadmap entries,
  and focused tests.

## What must not change

- `python -m agent_maintainer context pack` behavior.
- `PACK.md` and `PACK.json` payload shape.
- Compression backend names or fallback warnings.
- Headroom error normalization.
- Hook output and repair capsule wording.
- Public CLI/config semantics.

## Verification plan

- Run focused Ruff/flake8 checks on touched compression modules and tests.
- Run `pytest tests/context tests/hooks/test_hook_runtime.py
  tests/architecture/test_internal_package_boundaries.py -q`.
- Run `python -m agent_maintainer context pack`.
- Run `tach check --exact`, `change-plan check`, `guidance --check`, and
  `docsync check --base origin/main`.
- Run final verifier profiles: `precommit`, `full`, `ci`, `security`, `manual`.

## Rollback plan

Revert the PR. The compatibility shims and product imports are the only runtime
wiring changes; rollback returns compression ownership to
`agent_maintainer.context.compression`.

## Follow-up ratchet work

After this lands, reassess whether context-pack compression orchestration itself
can move without dragging product config or CLI dependencies into
`agent_context`.
