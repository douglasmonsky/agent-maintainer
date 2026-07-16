+++
id = "java-gradle-support-design"
kind = "design"
status = "active"
base_ref = "origin/main"
expires = 2026-08-15
allowed_paths = [
  ".agent-maintainer/change-plans/beta7-release.md",
  ".agent-maintainer/change-plans/java-gradle-support-design.md",
  "docs/superpowers/specs/2026-07-15-java-gradle-support-contracts.md",
  "docs/superpowers/specs/2026-07-15-java-gradle-support-design.md",
  "docs/superpowers/specs/2026-07-15-java-gradle-support-validation.md",
  "docs/superpowers/plans/2026-07-16-java-gradle-foundation.md",
  "docs/superpowers/plans/2026-07-16-java-gradle-setup-ratchets.md",
  "docs/superpowers/plans/2026-07-16-java-gradle-structured-baselines.md",
  "docs/superpowers/plans/2026-07-16-java-gradle-coverage-rollout.md",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 9
max_changed_lines = 4000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: Java and Gradle Support Design

## Why this change intentionally large

The architecture, runtime contract, and validation gates must jointly define
one decision-complete Java/Gradle feature boundary. The detail is necessary to
prevent incompatible implementations of wrapper confinement, report freshness,
multi-project coverage, and debt ratchets.

## Why this should not be split smaller

Committing only one companion would leave the approved design internally
incomplete. The three documents are one specification separated solely to keep
each file below the repository's maintainability ceiling.

## What allowed to change

Only the three Java/Gradle design documents, their four executable
implementation plans, this scoped plan, and the completed beta release plan's
status may change.

## What must not change

Do not change runtime behavior, provider code, configuration parsing, quality
thresholds, release artifacts, credentials, environments, or publishing state.

## Verification plan

Run Markdown lint, staged diff validation, and the full precommit profile on the
exact staged documents. Require the change-budget hook to accept this plan.

## Rollback plan

Revert the documentation commit. No runtime or external state requires cleanup.

## Follow-up ratchet work

Execute the four approved implementation plans in order. Before runtime edits,
complete this design plan and activate a phase-specific cohesive change plan.
