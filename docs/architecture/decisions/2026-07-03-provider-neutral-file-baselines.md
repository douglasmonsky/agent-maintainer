# Provider-Neutral File Baseline Assessment Boundary

Date: 2026-07-03

## Status

Accepted

## Context

Agent Maintainer's existing blocking reviewability checks are Python-backed.
The project needs a broader advisory surface for simple file facts such as file
length, nonblank line count, changed files, and changed lines across docs,
config, tests, TSX, YAML, TOML, and other explicit file groups.

Tach remains the Python module/import boundary tool. It is not the
cross-language architecture engine.

## Decision

Add `agent_maintainer.assess.file_baselines` as an advisory assessment builder.
It depends on configuration schema and the neutral Git numstat reader, then
returns typed assessment models from `agent_maintainer.assess.models`.

Keep rendering in `agent_maintainer.assess.reporting` and CLI orchestration in
`agent_maintainer.assess.cli`.

## Boundary Change

`src/agent_maintainer/assess/tach.domain.toml` now allows:

- `cli` to call `file_baselines`;
- `file_baselines` to depend on `config.schema`, `ecosystems.git_changes`, and
  `models`.

`reporting` still depends only on `debt_score` and `models` inside the assess
package, so rendering does not import assessment builders.

## Alternatives Considered

- Extending Python `file-length` and `change-budget` checks: rejected because
  it would blur Python blocking behavior with provider-neutral advisory facts.
- Treating Tach as the generic architecture/file policy layer: rejected because
  Tach is Python module/import oriented.
- Adding a verifier gate immediately: rejected because the first surface should
  be read-only and low-noise.

## Consequences

The new command is advisory-only. It can be dogfooded safely while future work
decides whether a non-blocking verifier check or ratchet is justified.
