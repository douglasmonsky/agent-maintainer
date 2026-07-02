# Phase 95: Provider-Aware File Change Classification

Status: complete in PR.

## Goal

Introduce an internal file-change classification seam that lets enabled
providers describe changed files by ecosystem, role, generated/ignored state,
and change kind without changing current Python reviewability gates.

## Scope

- Add a small internal changed-file classification model.
- Reuse existing Python, TypeScript/JavaScript, and Go file classifiers.
- Preserve current Python reviewability output, thresholds, and blocking
  behavior.
- Add tests proving Python source/test classification remains stable.
- Add tests proving TypeScript/JavaScript and Go changed files can be
  classified for advisory future policy without becoming blocking gates.
- Document that this phase creates policy input data, not new policy
  enforcement.

## Non-Goals

- No new language providers.
- No TypeScript/JavaScript or Go blocking reviewability gates.
- No change to `change-budget`, `file-length`, `structure-cohesion`, or
  `suppression-budget` command behavior.
- No config migration or new public configuration surface.
- No external provider plugin API.

## Acceptance Criteria

- A provider-aware changed-file classifier exists behind internal APIs.
- Python changed-file classification matches current source/test/generated
  root semantics.
- TypeScript/JavaScript and Go changed-file classification is available for
  advisory/reporting use but is not wired into blocking reviewability checks.
- Existing reviewability catalog characterization remains green.
- Tests fail if future refactors accidentally classify TypeScript/JavaScript
  or Go changes as current blocking Python reviewability input.

## Verification

Run focused tests:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
  tests/ecosystems tests/catalogs/test_global_catalog_characterization.py -q
```

Run static checks:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m ruff check \
  src/agent_maintainer/ecosystems tests/ecosystems
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer change-plan check
```

Before PR merge, run the standard final gates.

## Follow-Up

The next phase should decide whether advisory cross-ecosystem reviewability
summaries belong in reports, doctor, or a dedicated policy-planning command.
Do not promote TypeScript/JavaScript or Go reviewability checks to blocking
behavior until fixture repos prove low-noise results.
