# Phase 1: ADR for Context-Safe Legacy Ratchets

## PR Title

```text
docs: add context-safe legacy ratchets ADR
```

## Goal

Anchor the architecture before implementation.

## Files

Create:

```text
docs/architecture/decisions/YYYY-MM-DD-context-safe-legacy-ratchets.md
```

Use the current date.

## Required Content

```markdown
# Architecture Decision: Context-Safe Legacy Ratchets

Status: accepted

## Context

Agent Maintainer verifies repository health through checks, profiles, CI,
managed hooks, diagnostics, generated guidance, and package-first onboarding.
This works for clean repositories.

Existing repositories have a different failure mode: huge files, old violations,
large diffs, broad failure surfaces, and noisy logs overwhelm coding agents.
Strict verification alone can drown the agent in context and cause unfocused
repairs.

## Decision

Agent Maintainer will add a context-safe legacy ratchet architecture.

The architecture has these layers:

- Verification
- Diagnostics
- Context Safety
- Test Intelligence
- Ratchet
- Planned Change
- Optional Compression
- Reporting / Proof

Agent Maintainer will preserve exact repair facts, sanitize raw content, bound
default output, provide explicit expansion commands, rank ratchet targets, and
support scoped planned large changes.

Compression backends may be added later, but only for sanitized supporting
context. Compression will never operate on exact repair facts.

## Invariants

- Exact repair facts are never compressed or paraphrased.
- Sanitization happens before summarization or compression.
- Repository content, logs, test output, and diffs are untrusted evidence.
- Default output is bounded.
- Large expansion requires explicit user intent.
- Ratchet repair prioritizes new and worsened violations.
- Large changes require cohesive change plans.
- Quality gates still apply under change plans.

## Consequences

New command groups will be added:

- `agent-maintainer context ...`
- `agent-maintainer test-intel ...`
- `agent-maintainer ratchet ...`
- `agent-maintainer change-plan ...`

A new generated file will be added when ratcheting is active:

- `AGENTS.ratchet.md`

## Non-goals

- Do not add new scanners.
- Do not make Headroom a core dependency.
- Do not use compression to preserve correctness.
- Do not bypass tests, coverage, typing, architecture, security, or suppression checks.
- Do not dump full logs, full diffs, or full huge files into hook output.
```

## Acceptance Criteria

- ADR exists.
- ADR uses accepted status.
- Existing docs checks pass.
- Precommit passes.

---
