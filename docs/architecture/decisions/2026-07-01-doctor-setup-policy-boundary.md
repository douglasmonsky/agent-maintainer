# 2026-07-01: Doctor Setup Policy Boundary

## Status

Accepted.

## Context

`src/agent_maintainer/doctor/setup.py` had grown past the preferred source-line target while mixing local repository health checks with policy checks for architecture, thresholds, optional gates, legacy ratchet state, and tool capabilities.

## Decision

Move policy-oriented setup checks into `agent_maintainer.doctor.support.setup_policy` and keep `agent_maintainer.doctor.setup` as the compatibility facade for public doctor checks that are used by the CLI and tests.

## Consequences

`doctor.setup` remains the public import surface, while Tach now models the policy helper as an explicit support module. The split reduces the setup module size and keeps optional-gate/tool-capability dependencies away from local filesystem health helpers.

## Alternatives Considered

- Move all doctor setup checks into several tiny modules. Rejected for now because the current pressure is localized and smaller modules would add import churn without a clearer ownership rule.
- Keep the file flat and rely on future cleanup. Rejected because this repo is dogfooding its near-limit-file guidance.
