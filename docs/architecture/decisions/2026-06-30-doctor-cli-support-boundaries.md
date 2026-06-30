# Doctor CLI Support Boundaries

Date: 2026-06-30

## Context

The advisory mutation sweep for `src/agent_maintainer/doctor/cli.py` showed a
large survivor cluster in command plumbing, integration-file checks, environment
checks, and output formatting. Keeping those responsibilities in the CLI module
made the module harder to test directly and kept mutation results noisy.

## Decision

Move non-CLI doctor behavior into focused support modules:

- `support.environment` owns repository-root, virtualenv, and Git-state checks.
- `support.integrations` owns pre-commit, Codex, Claude Code, and canonical
  command checks.
- `support.output` owns text row formatting, JSON conversion, and exit-code
  selection.

`doctor.cli` remains the orchestration entrypoint and re-exports the existing
public helper names so tests and internal imports do not need a large migration.

## Boundaries

The support modules may depend on `support.models` only. They must not import
the CLI. The CLI may depend on support modules and setup/policy modules to
assemble the doctor result list.

## Alternatives Considered

Leaving the helpers in `doctor.cli` would preserve fewer files, but it would
keep the CLI module as a mixed orchestration and behavior surface. Moving all
doctor checks into `setup.py` was also rejected because setup checks already own
tool/config diagnostics and would become less cohesive.

## Verification

The Tach doctor-domain contract assigns the new support modules explicitly and
keeps `root_module = "forbid"` coverage through the parent contract.
