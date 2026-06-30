# ADR: Dogfood Doctor Support Boundary

## Status

Accepted.

## Context

The doctor command now checks whether the interactive `agent-maintainer` console
script resolves this source checkout or an older installed package. That check
needs PATH lookup, console-script shebang inspection, and a subprocess import
probe. Keeping that logic in `agent_maintainer.doctor.setup` would make the
setup module carry process-inspection helpers in addition to ordinary setup
health checks.

## Decision

Add `agent_maintainer.doctor.support.dogfood` for console-script dogfood drift
inspection and make `agent_maintainer.doctor.setup` depend on that support
module.

## Consequences

The setup module keeps the public doctor check surface, while process-specific
dogfood helpers live under `doctor.support`. Tach now assigns the helper module
explicitly so `root_module = "forbid"` continues to account for every source
file.
