# TypeScript LCOV Changed-Line Boundary

## Status

Accepted.

## Context

Agent Maintainer already has two distinct coverage capabilities: reusable LCOV
artifact parsing for TypeScript repair facts, and Git diff hunk mapping for the
advisory Python test-intelligence report. Phase 182 combines those inputs to
report executable changed-line coverage for TypeScript and JavaScript source.

Repository roots, workspaces, Git diffs, and provider file roles are
orchestration concerns. Moving them into `agent_repair_facts` would reverse the
internal package direction and make the reusable parser repository-aware.

## Decision

Keep generic `SF` and `DA` LCOV record parsing in
`agent_repair_facts.parsers.typescript_coverage`. Put repository confinement,
TypeScript source classification, Git changed-line mapping, weighted coverage
math, and advisory report models in
`agent_maintainer.test_intel.typescript_coverage`.

The adapter may depend inward on the reusable parser and on the existing
`test_intel.coverage_lines` Git hunk mapper. `agent_repair_facts` must not import
`agent_maintainer`.

## Why This Is Not A Coverage Gate

The adapter reads an existing artifact and reports facts only. It does not run
a JavaScript test tool, call `diff-cover`, configure a threshold or ratchet,
join a verifier profile, or change exit status based on the percentage. Python
`diff-cover` remains the existing blocking changed-line coverage backend.

## Alternatives Considered

- Extending the Python `test-intel changed` report was rejected because its
  source discovery and likely-test mapping are Python-specific.
- Calling `diff-cover` was rejected because it would blur advisory and blocking
  semantics and add an unnecessary subprocess boundary.
- Parsing Git diffs in `agent_repair_facts` was rejected because repository
  orchestration is outside that package's reusable fact contract.

## Consequences

LCOV syntax has one reusable parser, while repository and ecosystem policy stay
in Agent Maintainer. Workspaces require an explicit source root when their LCOV
records are workspace-relative. TypeScript coverage remains advisory until a
separate promotion assessment has sufficient low-noise evidence.
