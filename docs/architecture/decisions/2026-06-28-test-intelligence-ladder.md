# Architecture Decision: Test Intelligence Ladder

Status: accepted

## Context

Agent Maintainer currently enforces tests, coverage, branch coverage, and
changed-code coverage. It can detect when source changes lack test changes, but
it does not yet tell agents which tests matter or what kind of test to add.

Coding agents need deterministic test-repair guidance. They need to know which
tests relate to changed source, where coverage gaps are, and when deeper
test-quality tools are appropriate.

## Decision

Agent Maintainer will adopt this test intelligence ladder:

1. Pytest execution.
2. `coverage.py` / `pytest-cov` total coverage.
3. Branch coverage.
4. `diff-cover` changed-code coverage.
5. Mutmut target suggestions.
6. Hypothesis candidate guidance.
7. CrossHair candidate guidance for pure, typed, contracted functions.

The first implementation focus is deterministic changed-code test intelligence.
Advanced tools remain targeted, advisory, and manual.

## Invariants

- Pytest and coverage remain baseline signals.
- `diff-cover` remains the changed-code enforcement signal.
- Mutmut is manual and targeted.
- Hypothesis starts as guidance scaffolding, not policy.
- CrossHair is opt-in only and screened for pure typed functions.
- The goal is meaningful tests, not coverage theater.

## Non-Goals

- Do not make mutation testing part of normal full verification.
- Do not require Hypothesis for every changed function.
- Do not run CrossHair on arbitrary legacy code.
- Do not auto-generate properties as authoritative contracts.
