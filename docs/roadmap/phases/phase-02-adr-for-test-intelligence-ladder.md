# Phase 2: ADR for Test Intelligence Ladder

## PR Title

```text
docs: add test intelligence ladder ADR
```

## Goal

Define the test intelligence posture before implementation.

## Files

Create:

```text
docs/architecture/decisions/YYYY-MM-DD-test-intelligence-ladder.md
```

## Required Content

```markdown
# Architecture Decision: Test Intelligence Ladder

Status: accepted

## Context

Agent Maintainer currently enforces tests, coverage, branch coverage, and
changed-code coverage. It can detect when source changes lack test changes, but
it does not yet tell agents which tests matter or what kind of test to add.

Coding agents need deterministic guidance for test repair. They need to know
which tests relate to changed source, where coverage gaps are, and which deeper
test-quality tools are appropriate.

## Decision

Agent Maintainer will adopt a test intelligence ladder:

1. pytest execution
2. coverage.py / pytest-cov total coverage
3. branch coverage
4. diff-cover changed-code coverage
5. mutmut target suggestions
6. Hypothesis candidate guidance
7. CrossHair candidate guidance for pure typed contracted functions

The first implementation will focus on deterministic changed-code test
intelligence. Advanced tools remain targeted, advisory, and manual.

## Invariants

- pytest and coverage are baseline signals.
- diff-cover remains the changed-code enforcement signal.
- mutmut is manual and targeted.
- Hypothesis starts as guidance and scaffolding, not policy.
- CrossHair is opt-in and only for screened pure typed functions.
- The goal is meaningful tests, not coverage theater.

## Non-goals

- Do not make mutation testing part of normal full verification.
- Do not require Hypothesis for every changed function.
- Do not run CrossHair on arbitrary legacy code.
- Do not auto-generate properties as authoritative contracts.
```

## Acceptance Criteria

- ADR exists.
- ADR uses accepted status.
- Existing docs checks pass.
- Precommit passes.

---
