# Phase 94: Multi-Ecosystem Reviewability Policy Design

Status: complete in PR.

## Goal

Decide and document how Agent Maintainer should extend reviewability policies
across ecosystems without weakening Python behavior or pretending experimental
providers have parity.

## Scope

- State current behavior: reviewability checks are globally scheduled but
  Python-backed.
- Decide whether change-budget should aggregate enabled non-Python ecosystem
  source changes now or stay Python-only until policy adapters mature.
- Design the future file-change classification layer needed for multi-ecosystem
  reviewability.
- Define TypeScript/JavaScript suppression patterns separately from Python
  suppression patterns.
- Decide whether file length and structure cohesion should apply to
  TypeScript/JavaScript and Go now, or remain Python-only for the current beta.
- Add characterization tests that pin current Python-backed reviewability
  behavior before future policy generalization.

## Non-Goals

- No new language providers.
- No behavior change to Python reviewability checks.
- No TypeScript or Go reviewability gate enabled in this phase.
- No public plugin API.
- No config migration.
- No attempt to make experimental providers parity providers.

## Acceptance Criteria

- A public policy doc explains current behavior and future direction.
- An ADR records the beta decision for cross-ecosystem reviewability.
- Tests prove current reviewability checks still call the Python-backed policy
  modules and keep existing names/profiles.
- Docs clearly say TypeScript and Go configured commands do not yet imply
  full reviewability policy support.
- The next implementation phase can start from explicit policy decisions rather
  than inferring behavior from Python checks.

## Verification

Run focused checks:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
  tests/catalogs/test_global_catalog_characterization.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src node_modules/.bin/markdownlint-cli2 \
  docs/multi-ecosystem-reviewability-policy.md \
  docs/architecture/decisions/2026-07-02-multi-ecosystem-reviewability-policy.md \
  docs/roadmap/phases/phase-94-multi-ecosystem-reviewability-policy-design.md
```

Then run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer change-plan check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit --base-ref HEAD --staged
```

## Follow-Up

The next implementation phase should introduce a provider-aware file-change
classification model behind tests, while keeping Python output and thresholds
unchanged.
