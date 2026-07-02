# Phase 99: Advisory Provider Reviewability Summaries

## Status

Complete.

## Goal

Turn Phase 98 fixture evidence into more useful advisory output without adding
blocking TypeScript/JavaScript gates. `assess reviewability` should tell agents
when enabled providers changed source/test shape and broad suppression signals
exist while keeping provider maturity explicit.

## Scope

- Add advisory per-provider source/test/change summaries to `assess
  reviewability`.
- Add TypeScript/JavaScript advisory findings for source-heavy changes and
  source-without-test changes.
- Add broad suppression advisory findings for enabled experimental providers.
- Keep findings informational only; exit status and verifier gates stay
  unchanged.
- Document evidence-gathering heuristics, not policy gates.
- Preserve Python-backed blocking `change-budget`, `file-length`,
  `structure-cohesion`, and `suppression-budget` behavior.

## Non-Goals

- No new ecosystem provider.
- No public plugin API.
- No TypeScript/JavaScript blocking budgets.
- No package-manager or workspace autodetection.
- No config-surface thresholds until advisory output proves useful in real
  repositories.

## Acceptance Criteria

- JSON output includes provider summaries and advisory findings.
- Text output lists concise provider summaries and findings.
- TypeScript/JavaScript source-without-test scenarios produce advisory findings
  without failing the command.
- Dependency-only and config-only changes do not produce source-without-test
  findings.
- Generated ignored files remain excluded from advisory source/test signals.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/assess/test_reviewability_assessment.py tests/assess/test_reviewability_advisories.py -q`

## Result

Added advisory provider summaries and TypeScript/JavaScript source/test
findings. Kept all reviewability findings non-blocking.
