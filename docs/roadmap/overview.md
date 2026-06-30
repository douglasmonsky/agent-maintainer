<!-- markdownlint-disable MD024 MD025 -->

# Agent Maintainer Roadmap: Context-Safe Legacy Ratchets, Test Intelligence, Planned Large Changes, and Optional Compression

**Status:** Master implementation blueprint
**Audience:** Codex Goal Mode / implementation agent
**Purpose:** Provide a complete ordered roadmap for the next major Agent Maintainer capability layer.
**Rule:** Execute this plan phase-by-phase. Do not collapse it into one large PR.

---

## 0. Mission

Agent Maintainer already verifies repository health through checks, profiles, diagnostics, CI, hooks, generated guidance, release packaging, and package-first onboarding.

The next major product layer is:

> **Context-safe legacy ratchets with test intelligence and planned large-change support.**

Agent Maintainer must evolve from:

```text
This check failed.
```

to:

```text
Here is the next repair target.
Here is the exact failure.
Here is the smallest safe context.
Here is what was omitted.
Here is the command to expand only the next useful slice.
Here are the tests that matter for this change.
Here is the ratchet target.
Here is the change-plan scope.
Here is what quality gates still apply.
```

The objective is not to add more scanners. The objective is to make AI-assisted repair of existing Python repositories safe, bounded, test-aware, and reviewable.

---

## 1. Current Baseline

Agent Maintainer currently has these major capabilities:

```text
Package-first CLI
  agent-maintainer
  python -m agent_maintainer

Architecture utility CLI
  archguard

Verification profiles
  fast
  precommit
  full
  ci
  security
  manual

Adoption modes
  custom
  legacy-ratchet
  fresh-strict

Managed hooks
  Codex
  Claude Code

Generated guidance
  AGENTS.agent-maintainer.md

Diagnostics
  .verify-logs/
  manifest.json
  LAST_FAILURE.md
  structured tool artifacts

Static product graphics
  docs/assets/graphics/*.png

Release discipline
  release checklist
  release packaging tests
  TestPyPI/PyPI publish workflow
  wheel/sdist checks
```

Do not destabilize those baseline capabilities.

---

## 2. Final Architecture Target

The final architecture must have these layers:

```text
Agent Maintainer
├── Verification layer
│   └── checks, profiles, CI, hooks
├── Diagnostics layer
│   └── manifests, logs, LAST_FAILURE.md, structured artifacts
├── Context Safety layer
│   └── bounded output, safe file/log/diff expansion, context packs
├── Test Intelligence layer
│   └── changed-code test mapping, coverage gaps, test suggestions
├── Ratchet layer
│   └── baselines, target ranking, AGENTS.ratchet.md
├── Planned Change layer
│   └── cohesive change plans, integration branch series
├── Optional Compression layer
│   └── swappable backends for sanitized supporting context
└── Reporting / Proof layer
    └── PR summaries, static reports, examples, measured case studies
```

The implementation must preserve this layered separation. Do not blend these into one ambiguous “context” feature.

---

## 3. Absolute Rules

### 3.1 Product Rules

1. Do not add more scanners as part of this roadmap.
2. Do not add legacy compatibility for old names.
3. Do not reintroduce `ai_guardrails`, `ai-guardrails`, `[tool.ai_guardrails]`, or `AGENTS.guardrails.md`.
4. Do not make Headroom or any compression backend part of the core package.
5. Do not let compression decide correctness.
6. Do not dump full logs, full diffs, full huge files, or hundreds of findings by default.
7. Do not bypass quality gates under large-change plans.
8. Do not call planned large-change support a bypass.
9. Do not make mutation testing, Hypothesis, or CrossHair normal default gates.
10. Do not make Playwright or graphics rendering part of normal verification.
11. Do not use model-generated summaries as the default mechanism for correctness-sensitive context.
12. Do not create behavior that depends on network services.

### 3.2 Context Rules

1. Exact repair facts are never compressed.
2. Raw content is sanitized before summarization or compression.
3. File excerpts, log excerpts, diffs, and test output are untrusted evidence.
4. Default output is bounded.
5. Large expansions require explicit flags.
6. Every omitted section reports what was omitted.
7. Every bounded output provides expansion commands.
8. JSON output exists for agent-facing automation commands.
9. Context commands must be deterministic by default.
10. Agents must never need to scrape prose when JSON output is available.

### 3.3 Exact Repair Facts

These must remain exact and uncompressed:

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
change-plan allowed paths
change-plan forbidden paths
ratchet target IDs
expansion commands
verification commands
```

### 3.4 Supporting Context

These can be summarized, truncated, extracted, or optionally compressed after sanitization:

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

### 3.5 Terminology

Use these terms:

```text
cohesive change plan
planned large change
migration plan
integration branch series
context pack
ratchet target
exact repair facts
supporting context
```

Do not use these terms for planned large changes:

```text
bypass
override loophole
disable the budget
turn off the checks
```

---

## 4. Implementation Execution Rules

1. One phase equals one PR.
2. Split a phase if it exceeds the normal change budget.
3. Every PR must include focused tests.
4. Every user-facing PR must include docs.
5. Do not mix unrelated refactors into feature PRs.
6. Keep output stable and deterministic.
7. Update generated guidance only when the phase requires it.
8. Run focused tests first.
9. Run precommit before finishing every phase.
10. Run full/ci when shared verifier behavior changes.
11. Run release checks only when packaging changes.

### 4.1 Standard Verification Commands

Run for most phases:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer guidance --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer doctor --strict
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
```

Run when verifier, hooks, diagnostics, or config behavior changes:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile full
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main
```

Run only for packaging changes:

```bash
.venv/bin/just release-check
```

---
