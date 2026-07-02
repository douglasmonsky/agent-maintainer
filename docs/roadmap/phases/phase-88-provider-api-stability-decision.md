# Phase 88: Provider API Stability Decision

## Status

Complete in PR.

## Goal

Make public provider API decision after Python and TypeScript/JavaScript
provider milestones: keep provider interfaces internal during beta and continue
accepting language support as built-in experimental providers.

## Scope

- Add an explicit architecture decision record for provider API stability.
- Update provider roadmap API policy wording.
- Update provider contribution guide with the current beta contribution path.
- Link this phase from the roadmap index.

## Non-Goals

- No external provider loader.
- No entry point discovery.
- No runtime behavior change.
- No config behavior change.
- No new ecosystem provider.

## Acceptance Criteria

- Explicit decision record exists.
- API stability policy says no external plugin API during beta.
- Built-in experimental providers remain the contribution path.
- Future migration path is documented if external providers are introduced.
- Roadmap index links this phase.

## Verification

Run documentation-focused checks:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  node_modules/.bin/markdownlint-cli2 \
  docs/architecture/decisions/2026-07-02-provider-api-stability.md \
  docs/roadmap/phases/phase-88-provider-api-stability-decision.md \
  docs/roadmap/polyglot-ecosystem-providers.md \
  docs/provider-contribution-guide.md \
  docs/roadmap/full-roadmap-blueprint.md \
  docs/ROADMAP.md

git diff --check
```

Run the smallest relevant Agent Maintainer check:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv/bin/python -m agent_maintainer verify --profile fast
```
