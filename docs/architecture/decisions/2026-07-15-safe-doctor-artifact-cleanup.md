# Safe Doctor Artifact Cleanup Boundary

## Context

Doctor could identify duplicate generated files and Python bytecode, but it
offered no bounded cleanup operation. Generic recursive deletion would risk
removing user-authored Finder copies or following symlinks outside the
repository.

## Decision

`agent_maintainer.doctor.artifact_cleanup` owns both generated-artifact name
classification and cleanup. It may remove bytecode only below owned source and
test roots, and duplicate-named files only below known generated roots such as
`.verify-logs`, `build`, and `dist`.

Cleanup is a dry run unless the caller explicitly supplies `--apply`. Every
candidate is checked for repository confinement and symlink traversal during
planning and again immediately before deletion. User-authored source copies and
change plans may still be diagnosed, but they are never cleanup candidates.

`doctor.setup` depends inward on this module for duplicate-name
classification, and `doctor.cli` depends on it for explicit cleanup
orchestration. The Tach contract records both edges.

## Alternatives considered

- Delete every path reported by the existing duplicate detector. Rejected
  because reports include potentially user-authored source and plan copies.
- Follow generated-root symlinks. Rejected because repository-root confinement
  would become ambiguous.
- Add a general-purpose filesystem cleanup framework. Rejected as unnecessary;
  the safe allowlist is intentionally small and local.

## Consequences

The common case can remove large bytecode and verifier-copy debris safely while
unknown paths fail closed. Adding another generated root requires an explicit
code and test change.

## Verification

Tests cover dry-run behavior, explicit application, preserved user files,
source-copy exclusion, change-plan exclusion, symlink refusal, and CLI output.
Tach enforces the new dependency direction.
