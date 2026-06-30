# Test Intelligence Mutation Subpackage

## Context

Phase 73 addresses repeated structure-cohesion warnings in
`agent_maintainer.test_intel`. Mutation target selection, result reporting, sweep
planning, and sweep execution had grown into a distinct subdomain while still
living as flat sibling modules beside changed-file mapping and property-test
candidate code.

## Decision

Move mutation-specific test intelligence modules under
`agent_maintainer.test_intel.mutation` and update the local Tach contract to
list each `mutation.*` module explicitly. The top-level `test_intel.cli` remains
the command adapter, while mutation planning, execution, result parsing, and
rendering live in the mutation subpackage.

## Consequences

The top-level `test_intel` package has a clearer responsibility boundary and
fewer flat sibling modules. Tach still accounts for every file because the
domain contract uses explicit `mutation.*` modules rather than a broad bucket.

What remains forbidden: mutation modules should not import CLI orchestration
outside `mutation.cli` and `mutation.sweep_cli`, and non-mutation
test-intelligence helpers should not depend on mutation execution internals.
