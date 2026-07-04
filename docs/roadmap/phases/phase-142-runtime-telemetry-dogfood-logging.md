# Phase 142: Runtime Telemetry And Dogfood Logging

Status: complete

## Goal

Design a standards-aligned runtime logging and telemetry path so Agent
Maintainer can debug its own dogfooding quality without making normal agent
output noisier.

## Scope

- Add the detailed roadmap in
  `docs/roadmap/runtime-telemetry-dogfood-logging.md`.
- Define industry-standard logging practices relevant to Agent Maintainer.
- Decide initial library stance: standard library plus internal JSONL events
  first, `structlog` and OpenTelemetry optional later.
- Define proposed config fields, event schema, event categories, retention, and
  privacy rules.
- Define failure and exception event handling, redaction, crash-safe flushing,
  and failure-path tests.
- Define event-contract tests instead of a misleading log-count coverage metric.
- Keep this phase documentation-only.

## Non-goals

- No runtime event writer implementation.
- No new dependencies.
- No OpenTelemetry exporter.
- No `structlog` integration.
- No remote log shipping.
- No verifier behavior change.
- No new downstream default gate.

## Deliverables

- `docs/roadmap/runtime-telemetry-dogfood-logging.md`
- This phase entry.
- Roadmap index links from `docs/ROADMAP.md` and
  `docs/roadmap/full-roadmap-blueprint.md`.

## Acceptance Criteria

- The roadmap explains local structured JSONL events, run/command correlation,
  retention, and privacy constraints.
- The roadmap distinguishes logs, runtime events, run-scoped verification
  artifacts, and agent-facing summaries.
- The roadmap explains why logging sufficiency should be event-contract tested,
  not measured by raw logging statement counts.
- The roadmap defines expected check-failure, unexpected exception, unwritable
  event-dir, and redaction behavior.
- The roadmap evaluates standard library logging, `structlog`, and
  OpenTelemetry with a conservative first implementation choice.
- No runtime behavior changes.

## Verification

Run:

```bash
git diff --check
npx --no-install markdownlint-cli2 docs/roadmap/runtime-telemetry-dogfood-logging.md docs/roadmap/phases/phase-142-runtime-telemetry-dogfood-logging.md docs/ROADMAP.md docs/roadmap/full-roadmap-blueprint.md
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile fast
```
