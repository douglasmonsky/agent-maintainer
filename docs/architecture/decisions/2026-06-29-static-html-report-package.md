# Static HTML Report Package

## Context

Phase 34 adds `agent-maintainer report html`, which renders existing verifier
diagnostic artifacts into `.verify-logs/report/index.html`. The report needs to
read verifier manifests, PR summaries, latest failure notes, local log paths,
coverage artifacts, architecture results, release-readiness checks, and context
pack links without changing verifier execution.

## Decision

Add `agent_maintainer.report` as a focused package with a local Tach domain
contract. Keep the command adapter in `report.cli`, manifest orchestration in
`report.html`, section rendering in `report.sections`, link/table rendering in
`report.tables`, markdown extraction in `report.markdown`, styles in
`report.styles`, and report-local value objects in `report.types`.

The top-level CLI dispatches report commands dynamically, matching the existing
lazy CLI pattern for heavier subcommands. The report domain explicitly assigns
every report source module, keeping `root_module = "forbid"` coverage intact
while letting the report package depend on verifier artifact names and
PR-summary constants.

## Why This Is Not Architecture Drift

The report package consumes verifier artifacts; it does not become part of the
verifier execution path. This keeps reporting as a downstream presentation
layer and avoids importing report rendering into checks, runners, or verifier
core modules.

## Alternatives Considered

Keeping report rendering in one module was simpler initially, but it violated
the repository's module-size pressure and made table/link helpers too easy to
reuse accidentally from unrelated packages. Adding the report modules directly
to a broad root Tach entry would have satisfied compliance without documenting
the report boundary, which is the lazy pattern this repo is trying to avoid.

## Still Forbidden

Verifier checks, runners, and core execution modules must not import
`agent_maintainer.report`. Report modules must not call verifier runners or
trigger checks; they should render artifacts already produced by verification.
