# Remove Run-Artifact Compatibility Facades

## Boundary

`agent_run_artifacts` is the sole owner of artifact manifests, Git state,
history, PR summaries, summary support, and timing helpers. The corresponding
`agent_maintainer.verify` forwarding modules are deleted, and the verify Tach
domain no longer declares those removed modules.

## Why

Repository source and active tests already import the extracted package
directly. Exact reference analysis found no production consumer of the six
forwarding modules; only their compatibility test and inventory entry remained.
Keeping two import paths added policy surface without protecting a current
repository workflow.

## Why This Is Not Architecture Drift

The change removes outward-facing dependencies from the verify domain. Existing
verify modules keep their explicit direct dependencies on
`agent_run_artifacts`; no dependency direction, root strictness, or allowed
import is relaxed.

## Alternatives Considered

- Retain the forwarding modules for an arbitrary deprecation window. The
  pre-1.0 policy explicitly rejects compatibility shims once repository callers
  have migrated.
- Move the canonical implementations back under `agent_maintainer.verify`.
  That would reverse the established extractable-package boundary and recreate
  duplicated ownership.
- Delete additional facade groups in the same commit. They have separate owners
  and consumer inventories, so they remain bounded follow-up work.

## Still Forbidden

Verifier code must not recreate alternate artifact helper owners or new
forwarding modules. New artifact behavior belongs in `agent_run_artifacts`, and
verify orchestration must depend on that package through explicit Tach entries.
