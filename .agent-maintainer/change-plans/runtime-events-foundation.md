+++
id = "runtime-events-foundation"
kind = "mechanical-migration"
status = "active"
base_ref = "origin/main"
expires = 2026-07-17
allowed_paths = ["src/**", "tests/**", "docs/**", "AGENTS.md", "AGENTS.agent-maintainer.md", "README.md", "justfile", "pyproject.toml", "tach.toml", ".docsync/**", ".agent-maintainer/change-plans/**"]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 120
max_changed_lines = 12000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: runtime-events-foundation

## Why this change intentionally large

Runtime event dogfooding and cadence-waste hardening need a cohesive foundation:
config fields, local JSONL event model, redaction, sinks, verifier profile
lifecycle instrumentation, quiet wait commands, tests, Tach ownership, and ADR.
Splitting into separate commits would leave partial runtime event or wait
plumbing either unconfigured, untested, or not architecture-owned.

## Why this should not be split smaller

The runtime event package is small, but it crosses the verifier and config
boundaries by design. The schema inventory extraction is also part of this
change because `schema.py` crossed the file-length source-line cap after adding
the new config fields. Keeping the extraction with the config change prevents a
known guard failure without weakening the guard or hiding the pressure.

## What allowed to change

- Runtime event config fields and environment loading.
- Local runtime event model, redaction, JSONL sink, retention, and tests.
- Verifier profile start/finish event emission.
- Config schema inventory extraction needed to keep file-length compliance.
- Tach domain files and ADR documenting the new boundaries.
- Focused tests for runtime events, config loading, and verifier emission.
- Quiet wait command surface for long-running external work.
- Shared compact wait repair-capsule output.
- Focused wait tests under `tests/wait`.
- Future-Call ROI roadmap planning depends on runtime event and cadence-waste
  contracts.
- DocSync trace entries and evidence anchors for the new roadmap track.

## What must not change

- No OpenTelemetry exporter, remote logging, or new logging dependency.
- No raw stdout, stderr, tracebacks, prompts, environment dumps, secrets, or
  file contents in runtime event records.
- No change to normal verifier summary wording beyond writing local events.
- No downstream default enablement; only this repository dogfoods the feature.
- No relaxing file-length, architecture, or change-budget thresholds.

## Verification plan

- Focused runtime event/config/verifier tests.
- Ruff on touched source and tests.
- `tach check --exact`.
- `python -m agent_maintainer guidance --check`.
- `python -m agent_maintainer change-plan check`.
- Final verifier profiles before merge: `precommit` plus one broad local profile
  by default. Because this branch touches verifier/profile/runtime-event behavior,
  both `full` and `ci` are relevant here; `security` and `manual` stay contextual
  unless touched or explicitly requested.

## Rollback plan

Remove the runtime event config fields, runtime event package, verifier event
emission calls, and the self-dogfood config entries. Keep or separately revert
the schema inventory extraction depending on whether `schema.py` remains under
the file-length cap after removing the runtime event fields.

## Follow-up ratchet work

Later phases should add check-level, hook-level, artifact-retention,
dogfood-quality summary events, local verifier wait/status support, and
hook-visible readiness before considering optional OpenTelemetry or `structlog`
integrations.
After Phase 145 completes, implement the Future-Call ROI Acceleration
track one phase per PR starting with runtime-event intelligence summary commands.
