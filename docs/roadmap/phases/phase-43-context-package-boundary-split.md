# Phase 43: Context Package Boundary Split

## PR Title

```text
refactor: split context package boundaries
```

## Goal

Reduce `src/agent_maintainer/context` from one broad package with more than 20
Python files into clearer subpackages before adding public case studies that rely
on context commands.

## Requirements

- Split by responsibility, preserving CLI behavior:
  - file/log/diff reading and safety;
  - context-pack construction and rendering;
  - compression backends;
  - exact repair facts.
- Update imports, tests, and Tach domain contracts.
- Add or update an ADR under `docs/architecture/decisions/` explaining the
  boundary split and what remains forbidden.
- Keep `root_module = "forbid"` coverage; do not relax Tach.

## Acceptance Criteria

- `tach check --exact` passes.
- Context-focused tests pass.
- `verify --profile precommit` and `verify --profile full` pass.
- The structure-cohesion warning for `src/agent_maintainer/context` is resolved
  or replaced by a narrower, justified warning.

---
