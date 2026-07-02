# Phase 99: Advisory Provider Reviewability Summaries

## Status

Complete.

## Goal

Turn Phase 98 fixture evidence into more useful advisory output without adding
blocking TypeScript/JavaScript or Go gates. `assess reviewability` should tell
agents which enabled providers have changed source/test shape and broad
suppression signals while keeping provider maturity explicit: TypeScript is the
first richer source/test advisory target, and Go remains a thin experimental
canary.

## Scope

- Add advisory per-provider source/test/change summaries to `assess reviewability`.
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
- No TypeScript/Go blocking budgets.
- No Go source/test policy maturation.
- No package-manager or workspace autodetection.
- No config-surface thresholds until advisory output proves useful in real
  repositories.

## Acceptance Criteria

- JSON output includes provider summaries and advisory findings.
- Text output lists concise provider summaries and findings.
- TypeScript/JavaScript source-without-test scenarios produce advisory findings
  without failing the command.
- Go source changes remain visible in summaries without adding source/test
  policy findings.
- Dependency-only and config-only changes do not produce source-without-test
  findings.
- Generated and ignored files remain excluded from advisory source/test signals.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/assess/test_reviewability_assessment.py tests/assess/test_reviewability_advisories.py -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit`

## Result

Implemented advisory provider summaries and advisory findings in
`assess reviewability`. The report now exposes source/test line counts, broad
suppression counts, and advisory findings without changing command exit status
or blocking verifier profiles.

TypeScript/JavaScript receives the first richer source/test advisory heuristics.
Go remains visible in provider summaries and broad suppression findings only,
preserving its role as an experimental design canary rather than a parallel
maturation track.

## Notes For Future Codex Tasks

Do not add configurable blocking thresholds until real repository evidence shows
advisory summaries are low-noise. The next provider phase should mature
TypeScript/JavaScript first, keep Go thin, and avoid new ecosystems.
