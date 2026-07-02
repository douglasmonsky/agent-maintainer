# Phase 99: Advisory Provider Reviewability Summaries

## Status

Planned.

## Goal

Turn Phase 98 fixture evidence into more useful advisory output without adding
blocking TypeScript/JavaScript or Go gates. `assess reviewability` should tell
agents which enabled providers have source-heavy, source-without-test, or broad
suppression signals so humans can decide whether future thresholds are worth
configuring.

## Scope

- Add advisory per-provider source/test/change summaries to
  `assess reviewability`.
- Add advisory findings for source-heavy changes, source-without-test changes,
  and broad ecosystem suppressions.
- Keep findings informational only; exit status and verifier gates stay
  unchanged.
- Document that these are evidence-gathering heuristics, not policy gates.
- Preserve Python-backed blocking `change-budget`, `file-length`,
  `structure-cohesion`, and `suppression-budget` behavior.

## Non-Goals

- No new ecosystem provider.
- No public plugin API.
- No TypeScript/Go blocking budgets.
- No package-manager or workspace autodetection.
- No config surface for thresholds until advisory output proves useful in real
  repositories.

## Acceptance Criteria

- JSON output includes provider summaries and advisory findings.
- Text output lists concise provider summaries and findings.
- TypeScript/JavaScript and Go source-without-test scenarios produce advisory
  findings without failing the command.
- Dependency-only or config-only changes do not produce source-without-test
  findings.
- Generated or ignored files remain excluded from advisory source/test signals.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/assess/test_reviewability_assessment.py -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit`

## Notes For Future Codex Tasks

Do not add configurable or blocking thresholds until real repository evidence
shows these advisory summaries are low-noise. The next phase should evaluate
output quality on fixture repos or real opt-in projects before changing policy.
