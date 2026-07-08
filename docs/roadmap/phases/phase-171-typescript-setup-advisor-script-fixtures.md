# Phase 171: TypeScript Setup Advisor Script Fixtures

Status: active

## Goal

Back setup-advisor TypeScript adoption guidance with common pnpm, Vite/Vitest,
and Next.js/Jest script shapes while keeping behavior advisory.

## Scope

- Add fixture-backed setup-advisor tests for common TypeScript app scripts.
- Prove evidence records script names only, not command bodies.
- Document common script shapes as examples requiring explicit config mapping.
- Keep roadmap and DocSync trace aligned with the new evidence.

## Non-Goals

- No package-manager autodetection.
- No command body parsing.
- No generated TypeScript starter files.
- No TypeScript gate promotion to blocking status.

## Acceptance Criteria

- pnpm Vite/Vitest, Vite/Vitest, and Next.js/Jest script shapes all receive
  the existing advisory TypeScript provider recommendation.
- Irrelevant package scripts still do not receive TypeScript provider advice.
- Docs explain examples without implying automatic command inference.
- Phase 171 stays a docs/test evidence slice.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/assess/test_setup_advisor.py tests/docsync/test_public_doc_trace.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m tach check --exact
```
