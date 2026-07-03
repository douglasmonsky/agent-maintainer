# Phase 137: TypeScript Unsupported Surface Docs

Status: complete

## Goal

Make the experimental TypeScript/JavaScript provider's unsupported package
manager, test runner, framework, and coverage/security surfaces explicit enough
that users understand current beta limits before trying to promote the provider.

## Scope

- Expand the TypeScript/JavaScript provider docs with a concrete unsupported
  surface section.
- Keep provider behavior unchanged.
- Add focused docs regression coverage so the unsupported-surface language does
  not disappear during future polish.
- Add DocSync trace coverage for the public claim.

## Non-goals

- No package-manager autodetection.
- No new starter files.
- No TypeScript coverage, dependency, security, or mutation adapter.
- No blocking TypeScript reviewability gate.
- No new ecosystem provider.

## Acceptance Criteria

- Provider docs explicitly say npm, pnpm, yarn, and bun are usable only through
  explicit configured commands.
- Provider docs explicitly say Jest, Vitest, Playwright, Cypress, Mocha, and
  other runners are not auto-detected.
- Provider docs explicitly say Next.js, Vite, Astro, SvelteKit, and monorepo
  workspace semantics are not inferred.
- Provider docs keep Python-core and advisory-only maturity language intact.
- A focused docs test covers the unsupported-surface language.
- DocSync trace links the public claim to durable docs/test evidence.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/docs/test_first_touch_docs.py tests/docsync/test_public_doc_trace.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
