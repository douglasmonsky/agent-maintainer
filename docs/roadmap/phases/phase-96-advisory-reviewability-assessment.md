# Phase 96: Advisory Reviewability Assessment

Status: complete in PR.

## Goal

Expose provider-aware changed-file classifications as an advisory assessment so
humans and agents can see cross-ecosystem reviewability exposure without
changing current blocking verifier behavior.

## Scope

- Add an advisory `assess reviewability` subcommand.
- Reuse the Phase 95 changed-file classifier and existing git numstat parser.
- Summarize changed files by ecosystem and role.
- Clearly state that blocking reviewability gates remain Python-backed in this
  beta.
- Add text and JSON output tests.
- Update docs to point users at the advisory assessment.

## Non-Goals

- No new blocking TypeScript/JavaScript or Go gates.
- No change to `verify` profile behavior.
- No new provider.
- No config migration.
- No external plugin API.

## Acceptance Criteria

- `python -m agent_maintainer assess reviewability` reports an advisory summary
  of changed files by ecosystem and role.
- The command reports when no changed provider files are found.
- JSON output exposes stable fields for future reports.
- Tests prove TypeScript/JavaScript and Go findings remain advisory.
- Current reviewability gates and Python behavior remain unchanged.

## Verification

Run focused checks:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
  tests/assess tests/ecosystems tests/catalogs/test_global_catalog_characterization.py -q
```

Run static checks:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m ruff check \
  src/agent_maintainer/assess src/agent_maintainer/ecosystems tests/assess tests/ecosystems
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer change-plan check
```

Before PR merge, run the standard final gates.
