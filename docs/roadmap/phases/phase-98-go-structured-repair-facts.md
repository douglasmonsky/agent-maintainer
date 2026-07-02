# Phase 98: Go Structured Repair Facts

## Status

Planned.

## Goal

Make the experimental Go provider more useful without changing its explicit
configured-command model. Add compact summaries and exact repair facts for common
`gofmt`, `go vet`, and `go test` output so agent repair loops can point at
specific files and lines instead of generic failed-check messages.

## Scope

- Add Go diagnostic parsing for common text outputs from configured Go checks.
- Surface Go summaries through normal failed-check reporting.
- Surface Go exact facts through context packs and hook repair context.
- Keep Go provider disabled by default and experimental.
- Keep configured Go commands unchanged.
- Update Go provider docs and provider status limitations.

## Non-Goals

- No new Go commands.
- No package/workspace autodetection.
- No Go coverage, dependency, or security adapter.
- No public provider API.
- No changes to Python provider behavior.
- No widening of blocking reviewability gates to Go files.

## Acceptance Criteria

- `go-format`, `go-vet`, and `go-test` logs can produce exact repair facts when
  output includes a file path and line.
- Malformed or unrecognized Go output falls back to existing generic facts.
- Compact verifier summaries prefer parsed Go diagnostics when available.
- Docs describe Go structured facts as experimental and bounded.
- Focused Go parser, reporting, and context-pack tests pass.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/ecosystems tests/context tests/core -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit`

## Notes For Future Codex Tasks

Do not promote Go beyond experimental maturity from this phase alone. Structured
facts improve repair ergonomics, but starter files, coverage adapters, and real
fixture repos are still required before Go can be considered supported.
