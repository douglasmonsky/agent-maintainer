# Phase 168: TypeScript/React Doctor And Setup Guidance

Status: complete

## Goal

Improve TypeScript/React setup guidance so adopters can map existing scripts and
stable output artifacts into the experimental provider without Agent Maintainer
inferring package managers, commands, frameworks, or blocking gates.

## Scope

- Add doctor hints that point enabled TypeScript users toward stable output
  formats for repair facts.
- Keep configured commands explicit and package-manager neutral.
- Use Phase 167 parser evidence for Jest/Vitest JSON, Istanbul
  `coverage-summary.json`, and LCOV artifact guidance.
- Update public provider docs and trace evidence when doctor behavior changes.
- Keep the provider experimental and advisory-only.

## Non-Goals

- No package-manager autodetection.
- No generated TypeScript starter files.
- No TypeScript coverage command adapter or threshold gate.
- No dependency/security/mutation adapters.
- No blocking TypeScript reviewability gate.

## Acceptance Criteria

- `agent-maintainer doctor` remains silent when TypeScript is disabled.
- Enabled TypeScript configs with no commands receive stable-output setup hints.
- Configured commands with missing executables explain local executable lookup
  and make clear that no package manager is inferred.
- Provider docs describe doctor guidance without overstating TypeScript support.
- Focused doctor, docs, DocSync, formatting, and architecture checks pass.

## Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/doctor/test_typescript_doctor.py tests/docs/test_first_touch_docs.py tests/docsync/test_public_doc_trace.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m docsync check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m tach check --exact
```
