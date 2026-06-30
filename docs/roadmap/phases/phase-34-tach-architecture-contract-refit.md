# Phase 34: Tach Architecture Contract Refit

## PR Title

```text
refactor: split tach architecture contracts by domain
```

## Problem

Do not let `tach.toml` become a compliance bucket. A passing Tach config is not
enough if modules are lumped into broad `paths = [...]` groups without real
`depends_on` contracts. Agents must preserve architecture meaning, not only
`root_module = "forbid"` coverage.

## Required Direction

- Keep root `tach.toml` short.
- Put package-level contracts beside code in `tach.domain.toml` files.
- Require every Tach module and domain root to declare `depends_on`, even when
  empty.
- Reject broad module path buckets above the configured limit.
- Keep `tach check --exact` passing so stale dependency declarations fail.
- Keep `archguard tach-config --strict-root-module` aware of domain files.

## Acceptance Criteria

- Root `tach.toml` no longer contains large catchall path buckets.
- Domain configs are split by package responsibility.
- Archguard validates root and domain Tach configs.
- Tests prove missing `depends_on` and oversized path groups fail.
- `tach check --exact` passes.
- Precommit passes.

---
