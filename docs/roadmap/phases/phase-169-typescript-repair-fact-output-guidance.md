# Phase 169: TypeScript Repair-Fact Output Guidance

Status: complete

## Goal

Make TypeScript doctor setup guidance more actionable after users configure
commands by pointing human-oriented scripts toward stable outputs that already
feed repair facts.

## Scope

- Add an advisory doctor row for configured TypeScript commands whose command
  text does not visibly mention parser-friendly outputs.
- Keep the row non-blocking so `doctor --strict` does not fail on advisory
  TypeScript setup guidance.
- Recommend ESLint JSON, `tsc --pretty false`, Jest/Vitest JSON, and existing
  `coverage-summary.json` or `lcov.info` artifacts.
- Keep commands explicit and package-manager neutral.
- Update public provider docs and trace evidence when doctor behavior changes.

## Non-Goals

- No package-manager autodetection.
- No new TypeScript config fields.
- No generated TypeScript starter files.
- No TypeScript coverage command adapter or threshold gate.
- No dependency/security/mutation adapters.
- No blocking TypeScript reviewability gate.

## Acceptance Criteria

- Disabled TypeScript providers remain silent.
- Missing executables still produce the existing warning row.
- Configured human-oriented TypeScript commands receive one `PASS` advisory row.
- Commands that visibly mention stable parser-friendly outputs avoid extra
  advisory noise.
- Provider docs describe the advisory row without overstating TypeScript support.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/doctor/test_typescript_doctor.py tests/docs/test_first_touch_docs.py tests/docsync/test_public_doc_trace.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m tach check --exact
```
