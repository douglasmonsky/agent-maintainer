# Agent Maintainer Roadmap Overview

**Status:** current-state roadmap overview
**Audience:** implementation agents and maintainers
**Purpose:** summarize the product direction, architecture boundaries, and
execution rules for the split roadmap specs.

Use this file for orientation only. Use
[`full-roadmap-blueprint.md`](full-roadmap-blueprint.md) as the compact index
and the matching file under [`phases/`](phases/) as the implementation spec for
any phase.

## Mission

Agent Maintainer helps AI-assisted repositories keep changes small, tested,
diagnosable, reviewable, and aligned with repository policy. It should reduce
repair-loop noise by giving agents compact repair facts and exact next commands
while keeping detailed logs and artifacts off-context.

The product is currently Python-core with a provider architecture:

- Python is the core/reference provider.
- TypeScript/JavaScript is experimental and explicitly configured.
- Java/Gradle coverage and live-CI rollout is implemented with exact ratchets,
  truthful project labels, and controlled calibration; it remains experimental.
- Go provider history is archived out of the active mainline.
- Java priority for future repositories intentionally supersedes the former
  TypeScript-first sequence; further ecosystems still require low-noise evidence.

## Current Baseline

Current baseline capabilities include:

- package-first CLI: `agent-maintainer` and `python -m agent_maintainer`;
- architecture utility CLI: `archguard`;
- verification profiles: `fast`, `precommit`, `full`, `ci`, `security`,
  `manual`;
- adoption modes: `custom`, `legacy-ratchet`, `fresh-strict`;
- managed Codex and Claude Code hooks;
- generated compact guidance in `AGENTS.agent-maintainer.md`;
- repair capsule output, run ids, and run-scoped `.verify-logs/` artifacts;
- context packs with pointer-first expansion behavior;
- ratchets, change plans, integration branch series, and setup assessment;
- technical debt assessment and static HTML reports;
- DocSync traceability under `src/docsync/` and `.docsync/trace.yml`;
- internal packages for repair facts, context, run artifacts, hooks, DocSync,
  and architecture validation;
- release packaging checks, TestPyPI/PyPI publishing workflow, and Python
  compatibility smoke checks.

Do not destabilize these baseline capabilities while implementing later phases.

## Architecture Target

Keep the architecture layered:

```text
Agent Maintainer
  Verification layer
    checks, profiles, CI, hooks
  Diagnostics layer
    manifests, logs, LAST_FAILURE.md, structured artifacts
  Repair-facts layer
    exact facts from verifier and tool output
  Context-safety layer
    bounded output, safe file/log/diff expansion, context packs
  Test-intelligence layer
    changed-code test mapping, coverage gaps, mutation guidance
  Ratchet layer
    baselines, target ranking, strict typing and mutation ratchets
  Planned-change layer
    cohesive change plans, integration branch series
  Ecosystem-provider layer
    Python core provider, experimental TypeScript/JavaScript and Java/Gradle providers
  Documentation-trace layer
    DocSync evidence regions, claims, attestations, review packets
  Reporting/proof layer
    PR summaries, static reports, examples, measured case studies
```

The core owns orchestration, profiles, execution, diagnostics, hooks, reports,
and stable output contracts. Providers own ecosystem-specific file
classification, check generation, suppression classification, structured repair
facts, doctor hints, and guidance snippets.

## Product Rules

1. Do not add more scanner categories without a roadmap phase and evidence that
   the signal will be low-noise.
2. Do not reintroduce old product identity strings such as `ai_guardrails`,
   `ai-guardrails`, `[tool.ai_guardrails]`, or `AGENTS.guardrails.md`.
3. Do not make Headroom or any compression backend part of the core package.
4. Do not let compression decide correctness; exact repair facts stay exact.
5. Do not dump full logs, full diffs, huge files, or large finding clusters by
   default.
6. Do not bypass quality gates under large-change plans.
7. Do not call planned large-change support a bypass or loophole.
8. Do not make mutation testing, Hypothesis, CrossHair, or release packaging
   checks normal precommit defaults.
9. Do not create behavior that depends on network services for normal
   verification.
10. Do not add new ecosystems until provider evidence justifies the added
   maintenance surface.

## Context And Repair Rules

Exact repair facts must remain uncompressed:

```text
file paths
line numbers
column numbers
symbols
check names
exit codes
thresholds
ratchet fingerprints
change-plan IDs
change-plan allowed and forbidden paths
ratchet target IDs
expansion commands
verification commands
```

Supporting context may be summarized, truncated, extracted, or optionally
compressed after sanitization:

```text
log excerpts
tracebacks
test failure bodies
nearby source lines
diff hunks
large file slices
prose explanations
long warning clusters
bulk tool output
```

Default output should be a compact repair capsule: result, profile, run id,
top repair facts, one likely next action, and one explicit expansion command.

## Implementation Rules

1. One roadmap phase should normally land as one PR.
2. Split any phase that exceeds the configured change budget.
3. Every PR needs focused verification.
4. User-facing behavior changes need docs.
5. Do not mix unrelated refactors into feature PRs.
6. Keep output stable, deterministic, and summary-first.
7. Update generated guidance only when the phase requires it.
8. Run focused tests during the edit loop.
9. Run `just verify-precommit` before finishing a phase when hooks have not
   already verified the same repository state.
10. Run one broad local profile before PR/merge, usually `full`; use `ci` instead
    when diff/base-ref, workflow, or profile behavior changed. Run both only when
    that overlap is under test.
11. Run release checks only when packaging or release behavior changes.

## Standard Verification

Most phases:

```bash
just guidance-check
just doctor
just verify-precommit
```

Verifier, hook, diagnostics, config, or architecture changes:

```bash
just verify
just verify-ci
```

Packaging and release changes:

```bash
just release-check
```
