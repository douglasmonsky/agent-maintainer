# Phase 145: Runtime Event Contract Expansion

Status: completed

## Goal

Expand the local runtime event foundation into useful dogfooding signal without
making normal verifier, hook, or agent output noisier. The current foundation
intentionally records only verifier profile lifecycle events. The next step is
to instrument important runtime boundaries with compact, schema-tested events
and summarize those events into a local dogfood-quality report.

## Scope

- Add event-contract coverage for required runtime boundaries:
  - CLI command start, finish, and exception.
  - Verifier profile start, finish, reused result, and fresh run.
  - Check selection, skip, start, finish, failure, and exception.
  - Hook invocation, configured-repo no-op, failure, and exception.
  - Artifact write and retention pruning.
  - Dogfood source-checkout and stale-install checks.
- Add compact exception events:
  - event name such as `command.exception`, `hook.exception`, or
    `check.exception`;
  - exception type;
  - sanitized message;
  - command, profile, check, hook, and run correlation fields where available;
  - pointer to the run-scoped artifact where the full traceback exists.
- Add local event-contract tests:
  - required event names exist for instrumented boundaries;
  - event records include available correlation fields;
  - event records stay small and JSONL-safe;
  - raw stdout, stderr, file contents, prompts, environment dumps, tracebacks,
    and obvious credential-like values are not inlined.
- Add a compact event summary command that reads
  `.verify-logs/events/*.jsonl` and summarizes:
  - recent profile and check durations;
  - reused versus fresh verifier runs;
  - hook no-ops and hook failures;
  - stale-install warnings;
  - artifact retention pruning;
  - event writer degradation warnings.
- Keep event retention bounded through the existing
  `runtime_event_history_limit` setting.
- Preserve summary-first normal verifier output.

## OpenTelemetry ROI Decision

Do not add OpenTelemetry in this phase. The current ROI favors local JSONL
events because the highest-value work is defining stable event names,
correlation fields, privacy rules, and event-contract tests. OpenTelemetry may
eventually help with exporter interoperability and cross-process correlation,
but adding it now would introduce dependency, configuration, privacy, and
support surface before the local event contract has proven useful.

If a future OpenTelemetry phase is opened, it should add an optional exporter
over the same local event contract. It should not replace the local JSONL
contract or change normal verifier output semantics.

## Non-goals

- No remote log shipping.
- No OpenTelemetry exporter.
- No `structlog` dependency.
- No raw check transcripts or full tracebacks inside runtime event records.
- No event-volume or log-count coverage metric.
- No downstream blocking gate based on runtime events.
- No noisy agent-facing status messages.

## Acceptance Criteria

- Runtime events remain disabled by default for downstream users.
- This repository continues dogfooding bounded local runtime events.
- Event-contract tests prove required boundary events for implemented surfaces.
- Exception events are compact and sanitized.
- Dogfood report output is summary-first and references event artifacts instead
  of dumping raw JSONL.
- Existing verifier output remains unchanged except for local event artifacts.
- `verify --profile precommit`, `full`, `ci`, `security`, and `manual` pass.

## Verification

Run the smallest useful checks while developing:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/runtime_events tests/verify tests/hooks -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer guidance --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer change-plan check
```

Before merge, run `precommit` and one broad local profile. Use `ci` instead of
`full` when diff/base-ref, workflow, or profile behavior changed. Run both only
when that overlap is under test. Run `security` or `manual` when touching those
gates, before release, or when explicitly requested.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile full
```

## Notes For Future Tasks

Start with the check executor and hook adapters because those are the highest
signal dogfood boundaries. Add only the event names and fields needed by the
dogfood report; avoid building a generic observability framework.
