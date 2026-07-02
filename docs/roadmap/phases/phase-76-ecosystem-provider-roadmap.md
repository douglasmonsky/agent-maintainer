# Phase 76: Ecosystem Provider Roadmap

## Status

Complete when this planning PR merges.

## Goal

Create the architecture roadmap for evolving Agent Maintainer from a Python-centered verifier into a provider-based agent-maintenance framework without changing current runtime behavior. This repository phase covers provider-refactor Phase 0 planning.

## Scope

- Document core/provider boundaries.
- Define compatibility invariants.
- Define provider maturity levels.
- Define the phased implementation sequence.
- Define the testing strategy.
- Define the community contribution model.
- Link from the roadmap index.

## Non-Goals

- No provider implementation.
- No TypeScript, Rust, Java, or other non-Python support.
- No config migration.
- No public plugin API.
- No verifier behavior changes.
- No check command changes.
- No starter-file changes except roadmap links.

## Deliverables

- `docs/roadmap/polyglot-ecosystem-providers.md`.
- This numbered phase entry.
- Roadmap index links.

## Acceptance Criteria

- Documentation explains why Python should become the first provider.
- Documentation states that Phase 1 must add characterization tests before code movement.
- Documentation provides at least ten concrete compatibility invariants.
- Documentation provides a risk register.
- Documentation defines how community providers can mature from experimental to supported.
- Documentation states that external plugin loading is deferred.
- Documentation checks are attempted.
- No runtime behavior changes are included.

## Verification

Run the smallest practical documentation checks for this docs-only phase:

```bash
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer change-plan check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile fast
```

If dependencies are unavailable, record the exact failed command and blocker.

## Follow-Up Phases

Follow `docs/roadmap/polyglot-ecosystem-providers.md`:

- Phase 1: Characterization safety net.
- Phase 2: Minimal internal provider seam, Python only.
- Phase 3: Separate global checks from ecosystem checks.
- Phase 4: Generic file classification, Python only.
- Phase 5: Generalize policy checks through provider/classifier adapters.
- Phase 6: Neutral config path exploration.
- Phase 7: Experimental TypeScript/JavaScript provider.
- Phase 8: Structured artifact parser expansion.
- Phase 9: Provider contribution guide.
- Phase 10: Second non-Python provider.
- Phase 11: Public provider API decision.

## Notes For Future Codex Tasks

- Start each phase with a deep assessment of the previous phase's evidence.
- Keep changes small and independently reviewable.
- Do not move runtime code before Phase 1 characterization tests land.
- Preserve Python behavior until a deliberate migration phase says otherwise.
