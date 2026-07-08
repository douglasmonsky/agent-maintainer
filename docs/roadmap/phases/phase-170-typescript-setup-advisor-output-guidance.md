# Phase 170: TypeScript Setup Advisor Output Guidance

Status: complete

## Goal

Expose TypeScript repair-fact output guidance during setup assessment, before
users enable the experimental provider.

## Scope

- Extend the setup-advisor TypeScript provider recommendation reason with stable
  output guidance.
- Add an agent prompt that recommends parser-friendly TypeScript script outputs.
- Document the setup-advisor guidance in the TypeScript/JavaScript advice
  section.
- Keep the recommendation advisory and package-manager neutral.

## Non-Goals

- No package-manager autodetection.
- No inspection of `package.json` command bodies.
- No new TypeScript config fields.
- No generated starter files.
- No TypeScript coverage adapter or blocking reviewability gate.

## Acceptance Criteria

- Repositories with relevant `package.json` script names still receive the
  advisory TypeScript provider recommendation.
- That recommendation mentions ESLint JSON, `tsc --pretty false`, Jest/Vitest
  JSON, and existing `coverage-summary.json` or `lcov.info` artifacts.
- Repositories with irrelevant scripts still do not receive TypeScript provider
  advice.
- Setup-advisor docs describe the recommendation without overstating support.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/assess/test_setup_advisor.py tests/docsync/test_public_doc_trace.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m tach check --exact
```
