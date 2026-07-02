# Python File Classification Boundary

## Status

Accepted.

## Context

The ecosystem-provider roadmap requires generic file-role classification before
policy checks can move from Python-specific path logic to provider/classifier
adapters. Phase 80 introduces the classifier but does not rewire runtime policy
checks yet.

## Decision

Add generic file classification models under `agent_maintainer.ecosystems` and a
Python-specific classifier under `agent_maintainer.ecosystems.python`. The
classifier may depend on configuration path-root helpers, but policy checks,
verifier execution, reports, hooks, and doctor orchestration must not depend on
the classifier during this phase.

The Python classifier is internal and preserves current source/test root
semantics. It also identifies generated, ignored, docs, config, dependency, and
unknown Python-adjacent files for future policy adapter work.

## Alternatives Considered

- Rewire change-budget, file-length, suppression-budget, and structure checks
  immediately. That would combine classification with policy behavior changes
  and make drift harder to diagnose.
- Keep classification private inside each policy check. That would keep current
  behavior but would not create a reusable provider capability.
- Add non-Python classification at the same time. That would validate less
  because Python behavior is the compatibility contract for this refactor.

## Consequences

Future phases can adapt policy checks against a shared classifier while Phase 80
remains behavior-preserving. The Tach contract now assigns
`python.classification` explicitly under the internal ecosystem package.
