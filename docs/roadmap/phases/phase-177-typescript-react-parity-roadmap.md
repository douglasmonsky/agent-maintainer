# Phase 177: TypeScript/React Parity Roadmap

Status: complete

## Goal

Restore a current TypeScript/React parity roadmap on `main` and establish
advisory package-manager/workspace detection as the next bounded slice.

## Scope

- Map Python-provider capabilities to honest TypeScript/React candidates.
- Distinguish strong, partial, ecosystem-neutral, and unavailable equivalents.
- Define focused implementation slices and evidence requirements.
- Keep Phase 176 assigned to Codex terminal-rewake hardening.
- Use focused pull requests to `main` instead of a long-lived integration branch.

## Non-Goals

- No provider runtime behavior changes.
- No package-manager or workspace detector implementation.
- No inferred command execution.
- No dependency or workflow changes.
- No blocking TypeScript/React gate or provider promotion.

## Acceptance Criteria

- The durable roadmap records current evidence and remaining parity gaps.
- Phase 178 is advisory package-manager and workspace detection.
- Repository evidence is explicitly forbidden from becoming subprocess arguments.
- Every blocking candidate requires fixture and external-repository evidence.
- The compact roadmap and provider status point to the current parity track.

## Verification

Run:

```bash
.venv/bin/pytest -q tests/docs/test_roadmap_docs.py tests/docs/test_first_touch_docs.py
.venv/bin/python -m docsync check
git diff --check
```
