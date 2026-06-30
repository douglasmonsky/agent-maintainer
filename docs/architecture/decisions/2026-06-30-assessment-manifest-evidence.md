# ADR: Assessment Manifest Evidence Boundary

Date: 2026-06-30

## Status

Accepted

## Context

`agent_maintainer.assess.debt_categories` now calibrates advisory Technical Debt
Score categories with the latest verifier manifest. Keeping JSON parsing,
manifest status normalization, and category scoring in one module made the
assessment boundary harder to test and pushed too much policy into category
scoring.

## Decision

Add `agent_maintainer.assess.debt_manifest` as a small domain module that reads
and normalizes verifier manifest evidence. Add
`agent_maintainer.assess.debt_security` as a small domain module that turns
repository evidence and config into security/dependency category signals.
`debt_categories` may depend on both modules to assemble category scores.
`debt_score` may depend on `debt_manifest` for confidence calibration when the
manifest is missing or malformed.

## Alternatives Considered

- Keep manifest parsing inside `debt_categories`: rejected because category
  scoring already owns enough policy and lint complexity.
- Keep security/dependency evidence inside `debt_categories`: rejected because
  optional-gate relevance is separate policy and would keep the assembler over
  the source-line cap.
- Put manifest parsing in verifier modules: rejected because assessment should
  consume verifier artifacts without importing verifier orchestration.
- Relax the Tach contract for assessment: rejected because this is a real domain
  boundary, not an exception.

## Boundary Rules

- `debt_manifest` depends on no other assessment modules.
- `debt_security` depends only on assessment models and verifier config schema.
- `debt_categories` may consume typed manifest signals but should not read JSON
  files directly. It may consume security/dependency signals but should not own
  optional security-gate relevance rules.
- Verifier modules remain producers of artifacts; assessment modules remain
  consumers of those artifacts.
