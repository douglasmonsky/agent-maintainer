# Internal Package Boundary Refactor Roadmap

Agent Maintainer remains one public distribution while reusable primitives live
in clear internal packages. This roadmap is now a current-state closure note,
not a prompt to restart the extraction sequence.

The original implementation handoff is retained for historical context in
[`internal-package-boundaries-implementation-guide.txt`](internal-package-boundaries-implementation-guide.txt).
Do not execute that guide literally without checking current package state,
Tach contracts, ADRs, and phase files first.

## Current Package Shape

```text
src/
  agent_maintainer/    # product orchestrator, policies, CLI, profiles
  agent_repair_facts/  # normalized repair facts from tool output
  agent_context/       # bounded context, context packs, safe expansion
  agent_run_artifacts/ # verifier artifact schemas and renderers
  agent_client_hooks/  # hook config/templates/adapters
  agent_waits/         # product-neutral wait records, watcher state, and notification claims
  docsync/             # docs evidence and claim-freshness package
  archguard/           # architecture/config validation package
```

DocSync owns the docs/evidence responsibility. The original handoff called
that boundary `docs_evidence`; do not create a second `docs_evidence` package
unless a future ADR explicitly reopens the decision.

## Completed Extraction State

- Phase 109 created this internal-package roadmap.
- Phase 110 established baseline package ownership and ADR coverage.
- Phase 111 extracted reusable repair-fact parsing into
  `agent_repair_facts`.
- Phase 112 extracted bounded context models, estimates, and safe readers into
  `agent_context`.
- Phase 113 extracted run-artifact payload, history, Git-state, PR-summary, and
  timing helpers into `agent_run_artifacts`.
- Phase 115 extracted hook templates, static client configuration, adapter
  models, adapter selection, and install planning into `agent_client_hooks`.
- Phase 116 added executable dependency-direction tests for extracted
  packages.
- `agent_waits` dependency direction is covered by the AST regression and its
  package-local Tach contract.
- Phase 118 extracted pure context-pack rendering and sanitizing helpers into
  `agent_context`.
- Phase 119 extracted reusable context-compression primitives and backend
  adapters into `agent_context`.
- Phases 120 through 122 expanded DocSync dogfooding across public and
  provider-specific docs.

Product orchestration remains in `agent_maintainer`. Context-pack build
orchestration, compression policy, CLI commands, hook runtime verification,
config interpretation, verifier execution, and user-facing workflow stay
product-owned unless a later phase explicitly moves them.

## Hard Invariants

- Keep `agent-maintainer` as the only public distribution for this pass.
- Do not change user-facing CLI behavior as a side effect of internal moves.
- Do not change context-pack JSON shape except through an explicit migration.
- Do not make extracted packages import `agent_maintainer`.
- Do not create `docs_evidence`; extend `docsync` instead.
- Update Tach ownership and ADRs before changing cross-package dependencies.
- Keep `[tool.agent_maintainer]` source, package, coverage, structure, Vulture,
  Semgrep, and cohesive-change paths aligned with real package roots.
- Regenerate `AGENTS.agent-maintainer.md` after config path changes.
- Treat Tach failures as architecture feedback, not as a reason to broaden
  module buckets.

## Current Verification Sources

- `tests/architecture/test_internal_package_boundaries.py` enforces dependency
  direction for extracted packages.
- `tests/docsync/test_boundaries.py` enforces DocSync extractability.
- `tach.toml` and package-level `tach.domain.toml` files own architecture
  policy.
- `docs/architecture/decisions/2026-07-02-internal-package-ownership.md`
  records the internal-package ownership decision.
- `.docsync/trace.yml` records public documentation evidence mappings.

## Future Work

Further extraction work should be evidence-led and phase-scoped. Likely future
work belongs in separate roadmap entries:

- remove any remaining compatibility shims only after tests prove no active
  internal or documented path depends on them;
- add more DocSync trace claims as public docs change;
- tighten extracted-package APIs where repeated product imports show a real
  boundary problem;
- revisit public distribution strategy only through a dedicated packaging ADR.

Do not restart the original Phase 0 baseline plan. Use this file and the
completed phase files as the recovery point.
