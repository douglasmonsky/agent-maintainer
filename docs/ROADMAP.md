# Roadmap

## Read This First

This file is only the implementation tracker for the Agent Maintainer roadmap.
It is a recovery checklist, not the detailed implementation spec.

The canonical detailed spec index is vendored into the repository here:

[`docs/roadmap/full-roadmap-blueprint.md`](roadmap/full-roadmap-blueprint.md).

The usage guide for the split specs is here:

[`docs/roadmap/README.md`](roadmap/README.md).

Experimental architecture track:

[`docs/roadmap/polyglot-ecosystem-providers.md`](roadmap/polyglot-ecosystem-providers.md).

Before implementing any phase:

1. Open [`docs/roadmap/README.md`](roadmap/README.md).
2. Open the roadmap index:
   [`docs/roadmap/full-roadmap-blueprint.md`](roadmap/full-roadmap-blueprint.md).
3. Reopen the matching split phase file under
   [`docs/roadmap/phases/`](roadmap/phases/).
4. Follow the phase's scope, file targets, tests, documentation requirements,
   acceptance criteria, and explicit out-of-scope rules.
5. Use this file only to track phase completion, implementation,
   verification, merge, and post-merge CI confirmation.

Do not infer phase requirements from this checklist alone. If chat context is
compacted or interrupted, resume from the checklist only after reopening the
guide and relevant split phase file. If the split roadmap appears missing or
stale, restore the source document named `agent-maintainer-full-roadmap-blueprint.md`
and split it back into `docs/roadmap/phases/` before continuing implementation.

Agent Maintainer is in beta. The current major roadmap covers context-safe
legacy ratchets, test intelligence, planned large-change support, and optional
compression. Do not collapse it into one large PR. The blueprint requires one
phase per PR unless the user explicitly changes that rule.

## Current Baseline

The public beta baseline already includes package-first onboarding, verification
profiles, diagnostics, release checks, public packaging metadata, TestPyPI/PyPI
Trusted Publishing workflow, Codex and Claude Code hooks, generated guidance,
example repos, and the first cohesive-change budget exception.

Current external release state:

- [x] `agent-maintainer==0.1.0b5` is published to TestPyPI and PyPI,
      attached to GitHub prerelease `v0.1.0b5`, and smoke-tested from both
      package indexes. Release evidence is recorded in
      [`docs/releases/0.1.0b5.md`](releases/0.1.0b5.md).

Current pre-case-study decision:

- [x] Pre-case-study hardening complete; measured proof work promoted to
      Phase 89.

## Completed Phase Archive

Completed roadmap history is bucketed so this active tracker stays short and
cheap for agents to scan. Use these files when historical recovery context is
needed:

- [Roadmap archive map](roadmap/archive/README.md)
- [Foundations and release hardening, phases 001-073](roadmap/archive/completed-phases-001-073-foundations-release-hardening.md)
- [Provider and policy stabilization, phases 074-108](roadmap/archive/completed-phases-074-108-provider-policy-stabilization.md)
- [Internal package extraction, phases 109-123](roadmap/archive/completed-phases-109-123-internal-package-extraction.md)
- [DocSync, provider evidence, and runtime, phases 124-144](roadmap/archive/completed-phases-124-144-docsync-provider-runtime.md)
- [Runtime context ROI, phases 145-148](roadmap/archive/completed-phases-145-148-runtime-context-roi.md)

## Planned: Future-Call ROI Acceleration Track

Agent Maintainer should convert local primitives into compounding leverage for future agent calls. This track prioritizes work by expected return on cost, quality, and speed: runtime-event intelligence, repair-fact coverage, surgical next actions, DocSync verifier integration, attention scoring, and a hermetic downstream task-broker incubator.
Detailed scope:

[`docs/roadmap/future-call-roi-acceleration.md`](roadmap/future-call-roi-acceleration.md)

Track work:

- [ ] Phase 149: DocSync Verifier Integration Repair Facts
- [ ] Phase 150: Attention Ledger v0
- [ ] Phase 151: Attention-Weighted Context Packs
- [ ] Phase 152: Agent Task Broker Incubator Scaffold
- [ ] Phase 153: Task Broker Handoff Result Protocol
- [ ] Phase 154: Task Broker Locks And Worktree Planning
- [ ] Phase 155: Claude Async Rewake Hook Option
- [ ] Phase 156: Agent Maintainer MCP Surface v0
- [ ] Phase 157: Context Recall Compaction Ledger v0
- [ ] Phase 158: Local Observability Export Contract
- [ ] Phase 159: Scoring Dataset Optimization Prep
- [ ] Phase 160: ROI Loop Dogfood Case Study

## Future Work

- Continue adding section-level DocSync claims as public docs materially change,
  especially where a claim can point to durable implementation or test evidence.

- Avoid adding new ecosystems until TypeScript/JavaScript satisfies the
  promotion bar in

  [`docs/case-studies/typescript-provider-maturation.md`](case-studies/typescript-provider-maturation.md).

## Final Definition Of Done

The roadmap is complete only when every phase above is implemented, tested,
documented, merged through CI, and verified against the final definition of
done in [`docs/roadmap/final-definition-of-done.md`](roadmap/final-definition-of-done.md).
