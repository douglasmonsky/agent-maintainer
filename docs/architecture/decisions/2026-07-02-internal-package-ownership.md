# Architecture Decision: Internal Package Ownership

Status: accepted

## What Changed?

Agent Maintainer will keep one public distribution, `agent-maintainer`, while
extracting reusable primitives into internal top-level packages under `src/`.
This decision defines package ownership and dependency direction before any
runtime code is moved.

## Why Necessary?

The repository now has enough reusable machinery that the product package risks
becoming a catch-all namespace: repair fact parsing, bounded context packs,
run-scoped artifacts, hook templates, architecture validation, and documentation
traceability each have different ownership. Naming those boundaries before the
move prevents broad refactors that only shuffle files to satisfy metrics.

## Package Ownership

- `agent_maintainer` owns the product workflow: CLI orchestration, profiles,
  policy selection, verifier scheduling, user-facing commands, and compatibility
  shims.
- `agent_repair_facts` will own normalized repair facts and parsers for tool
  output.
- `agent_context` will own bounded context construction, context packs, safe
  expansion commands, and compression behavior.
- `agent_run_artifacts` will own verifier artifact schemas, run manifests,
  run-scoped summaries, history retention, and latest-pointer rendering.
- `agent_client_hooks` will own generated client hook templates and client
  adapter configuration.
- `docsync` owns docs/evidence traceability, claim freshness, review packets,
  and attestations. It replaces the earlier roadmap placeholder named
  `docs_evidence`.
- `archguard` continues to own architecture and configuration validation.

## Dependency Direction

`agent_maintainer` may depend on all internal packages as the orchestrator.
The reusable packages must not import `agent_maintainer`.

Allowed lower-level dependencies for the first extraction pass:

- `agent_repair_facts`: standard library and package-declared parser
  dependencies only.
- `agent_context`: `agent_repair_facts`.
- `agent_run_artifacts`: `agent_context` and `agent_repair_facts`.
- `agent_client_hooks`: standard library only unless an explicit adapter ADR
  approves otherwise.
- `docsync`: standard library and package-declared dependencies; it must remain
  extractable and must not import `agent_maintainer` or `archguard`.
- `archguard`: remains independent from `agent_maintainer`.

## Why This Is Not Architecture Drift

The split does not create new public packages or new user-facing install
surfaces. It makes existing responsibilities explicit while preserving the
current CLI, profiles, generated artifacts, and hook behavior.

## Alternatives Considered

1. Keep all code under `agent_maintainer`.
   Rejected because the current namespace already mixes product orchestration
   with reusable repair, context, artifact, and hook primitives.
2. Publish separate distributions now.
   Rejected because versioning and release coordination would add friction
   before the internal seams are proven.
3. Create a new `docs_evidence` package.
   Rejected because DocSync now owns that boundary and creating both would split
   one concept across two packages.

## What Remains Forbidden?

- Do not move multiple package boundaries in one PR.
- Do not make extracted packages import `agent_maintainer`.
- Do not change CLI behavior as a side effect of moving ownership.
- Do not weaken Tach contracts to make moves pass.
- Do not create a `docs_evidence` package without a new ADR.

## Review Or Expiration Condition

Revisit this decision after `agent_repair_facts`, `agent_context`, and
`agent_run_artifacts` have landed, or before publishing any separate
distribution or external plugin API.
