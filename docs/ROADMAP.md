# Roadmap

## Read This First

This file is an implementation tracker for the Agent Maintainer roadmap. It is
only a checklist recovery index, not the detailed implementation spec.

The roadmap guide explains how to use the detailed spec:

[`docs/roadmap/README.md`](roadmap/README.md).

The full roadmap blueprint is intentionally vendored into this repository here:

[`docs/roadmap/full-roadmap-blueprint.md`](roadmap/full-roadmap-blueprint.md).

Before implementing a phase, reopen the roadmap guide and the matching phase in
the full blueprint first. Follow the blueprint's scope, file targets, tests,
documentation requirements, acceptance criteria, and explicit out-of-scope
rules. Do not infer phase requirements from this checklist alone. If chat
context is compacted or interrupted, resume from this checklist only after
reopening the roadmap guide and full blueprint.

If the detailed blueprint appears missing or stale, restore the source document
named `agent-maintainer-full-roadmap-blueprint.md` before continuing
implementation.

Agent Maintainer is in beta. The current major roadmap covers context-safe
legacy ratchets, test intelligence, planned large-change support, and optional
compression. Do not collapse it into one large PR. The blueprint requires one
phase per PR unless the user explicitly changes that rule.

## Current Baseline

The public beta baseline already includes package-first onboarding, verification
profiles, diagnostics, release checks, public packaging metadata, TestPyPI/PyPI
Trusted Publishing workflow, Codex and Claude Code hooks, generated guidance,
example repos, and the first cohesive-change budget exception.

Current external release gate:

- [ ] Approve the waiting protected `pypi` environment job for
  `agent-maintainer==0.1.0b3`, then smoke-test the real PyPI install.

## Next: Context-Safe Legacy Ratchets

Agent Maintainer's next focus is helping agents improve existing repositories
without drowning in failures, giant files, huge diffs.

Planned work:

- Bounded failure summaries with explicit expansion commands.
- Test intelligence for changed source and relevant tests.
- Safe context commands for logs, failures, files, and diffs.
- Python file outlines for large legacy files.
- Context packs for agent repair loops.
- Ratchet baselines with ranked repair targets.
- Generated `AGENTS.ratchet.md` guidance.
- Cohesive change plans for intentional large migrations.
- Integration branch series support for large rewrites.
- Optional compression backends for sanitized supporting context.
- PR summaries with measured proof examples.

## Implementation Phases

- [x] Phase 1: ADR for Context-Safe Legacy Ratchets
- [x] Phase 2: ADR for Test Intelligence Ladder
- [x] Phase 3: Public Roadmap Docs Stubs
- [x] Phase 4: Config Scaffolding
- [x] Phase 5: Context Contract Implementation
- [x] Phase 6: Bounded Verifier, Hook, LAST_FAILURE Output
- [x] Phase 7: Test Intelligence MVP
- [x] Phase 8: Smarter Source-Without-Test Guidance
- [x] Phase 9: `context failures` and `context log`
- [x] Phase 10: Context Budget Estimation
- [x] Phase 11: Safe Large-File Reading
- [x] Phase 12: Diff Context Safety
- [x] Phase 13: Ratchet Baseline Status
- [x] Phase 14: Ratchet Target Ranking
- [x] Phase 15: Generate `AGENTS.ratchet.md`
- [x] Phase 16: Context Packs
- [x] Phase 17: Hook Output Uses Context Packs
- [x] Phase 18: Context Artifact Retention Upload Policy
- [x] Phase 19: Hypothesis Candidate Guidance
- [x] Phase 20: Mutmut Target Suggestions
- [ ] Phase 21: CrossHair Candidate Guidance
- [ ] Phase 22: Cohesive Change Plans
- [ ] Phase 23: Change-Budget Integration Change Plans
- [ ] Phase 24: Integration Branch Series
- [ ] Phase 25: Compression Backend Interface
- [ ] Phase 26: Optional Headroom Backend
- [ ] Phase 27: Doctor Integration
- [ ] Phase 28: Examples Proof Repos
- [ ] Phase 29: PR / GitHub Actions Summary Report
- [ ] Phase 30: Policy Packs Onboarding Presets
- [ ] Phase 31: Archguard Impact Analysis
- [ ] Phase 32: Repair Plan Command
- [ ] Phase 33: Agent Adapter API
- [ ] Phase 34: Static HTML Report
- [ ] Phase 35: External Case Studies Measured Proof Harness
- [ ] Phase 36: Monorepo / Multi-Package Support
- [ ] Phase 37: Team Policy Templates

## Final Definition Of Done

The roadmap is complete only when every phase above is implemented, tested,
documented, merged through CI, and verified against the final definition of done
in the full blueprint.
