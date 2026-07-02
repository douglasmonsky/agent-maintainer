# Phase 86: Provider Contribution Guide

## Status

Complete in PR.

## Goal

Document how future contributors should add built-in experimental ecosystem
providers without promising a public plugin API or weakening Python's reference
provider behavior.

## Scope

- Add a provider contribution guide.
- Link the guide from the polyglot provider roadmap and roadmap index.
- Define maturity levels, required provider shape, tests, docs, doctor
  expectations, structured parser expectations, and promotion criteria.
- Preserve the rule that provider support starts built in and experimental.
- Preserve Python as the core/reference provider.

## Non-Goals

- No provider implementation.
- No second non-Python provider.
- No external plugin package discovery.
- No generated starter file changes.
- No verifier behavior changes.
- No config semantics changes.

## Acceptance Criteria

- Contributor guide exists.
- Provider checklist exists.
- Experimental provider policy is explicit.
- Guide says external plugin loading is deferred.
- Guide says Python behavior must not be weakened to fit a generic abstraction.
- Roadmap index links this phase.

## Verification

Run documentation-focused checks:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  node_modules/.bin/markdownlint-cli2 \
  docs/provider-contribution-guide.md \
  docs/roadmap/polyglot-ecosystem-providers.md \
  docs/roadmap/phases/phase-86-provider-contribution-guide.md \
  docs/roadmap/full-roadmap-blueprint.md \
  docs/ROADMAP.md

git diff --check
```

Run the smallest relevant Agent Maintainer check if practical:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python -m agent_maintainer verify --profile fast
```

## Notes For Future Codex Tasks

Start Phase 87 from the second-provider plan only after this guide is merged.
Do not add Rust or another provider without using the guide as a review
checklist.
