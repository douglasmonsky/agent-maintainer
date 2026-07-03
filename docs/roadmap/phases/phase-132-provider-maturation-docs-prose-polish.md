# Phase 132: Provider Maturation Docs Prose Polish

Status: complete

## Goal

Polish the provider-status, TypeScript provider, multi-ecosystem policy, and
TypeScript maturation docs so the current polyglot posture is easy to understand
without compressed prose or overclaiming provider maturity.

## Scope

- Rewrite TypeScript/JavaScript provider docs with clear package-first,
  explicit-command examples.
- Clarify provider status: Python is core/reference; TypeScript/JavaScript is
  experimental; no other active ecosystem provider should be implied.
- Clarify multi-ecosystem reviewability policy and advisory-only TypeScript
  posture.
- Polish the TypeScript maturation notes after Phase 131 real-repo evidence.
- Add docs regression coverage for provider docs wording.

## Non-goals

- Do not add provider behavior.
- Do not add new ecosystem providers.
- Do not change TypeScript command defaults, profile membership, or config
  semantics.
- Do not promote TypeScript/JavaScript out of experimental status.
- Do not add TypeScript blocking reviewability gates.

## Acceptance Criteria

- Provider docs use complete public-facing sentences and readable command
  blocks.
- Provider docs clearly state TypeScript/JavaScript is advisory and
  experimental.
- The TypeScript maturation note explains fixture evidence, real-repo diff
  evidence, and the remaining promotion gap.
- Tests guard against known compressed provider-doc fragments.
- DocSync and docs tests pass.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/docs tests/docsync -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```
