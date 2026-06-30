# Phase 38: Change-Plan Authority Over Legacy Overrides

## PR Title

```text
fix: prevent legacy override from clearing change-plan failures
```

## Goal

Make cohesive change plans authoritative. The older
`cohesive_change_override` mechanism must not clear invalid, expired,
out-of-scope, or otherwise failing change-plan decisions.

## Requirements

- Identify change-budget failures created by change-plan validation or scope
  violations.
- Ensure legacy cohesive override cannot remove those failures.
- Prefer making legacy override subordinate to valid active plans.
- Update docs so users understand change plans are the preferred explicit
  mechanism for intentional large changes.
- Add tests where an invalid or out-of-scope active plan remains blocking even
  when legacy override settings would otherwise allow the diff.

## Out Of Scope

- Do not remove legacy override config entirely unless tests prove it is unused
  and migration docs are updated.
- Do not loosen change-budget thresholds.

## Acceptance Criteria

- Change-plan validation failures remain failures under legacy override.
- Valid plans can still bend normal change-budget size limits.
- Precommit and targeted change-budget tests pass.

---
