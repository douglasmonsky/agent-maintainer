# Changelog

## Unreleased

### Added Since 0.1.0b5

- Release evidence for `0.1.0b5`, including TestPyPI/PyPI workflow links,
  artifact hashes, and clean-install smoke commands.
- Public documentation drift tests that keep README and roadmap current-release
  references aligned with recorded release evidence.

### Changed Since 0.1.0b5

- README and roadmap current-release links now point at `0.1.0b5`.
- Agent-client installation, scaffolding, status, and uninstall selection now
  share one managed-file manifest, and status distinguishes current, stale,
  missing, and intentionally unmanaged files.
- Bootstrap is dependency-only, while explicit hook/pre-commit installation
  has strict argument parsing and side-effect-free preview.
- Initializer preview classifies additions, unchanged files, supported merges,
  conflicts, and user-owned skips before transactional apply.
- Managed hooks now expose explicit update and uninstall lifecycles driven by
  the same manifest, preflight, merge, backup, and rollback contract.

### Fixed Since 0.1.0b5

- Agent and hardening scaffolds now include the configured Codex and Claude Code
  PR-wait wrappers, and Codex hook-audit status/uninstall inventory no longer
  disagrees with installation.
- Claude hook merging preserves unrelated entries and ordering. Changed hook
  files are always backed up in ignored collision-proof transactions, including
  with `--force`, and interrupted multi-file writes roll back.
- Initializer force no longer overwrites user guidance silently: supported files
  merge, conflicts are backed up, and interrupted multi-file onboarding rolls
  back to the pre-run state.
- Hook and initializer recovery data is Git-private in repositories. Uninstall
  removes only managed identities, preserves co-located third-party commands,
  refuses unowned files, and rolls prior deletions back after later failures.

## 0.1.0b5 - 2026-07-03

Fifth beta release of Agent Maintainer.

### Added

- DocSync traceability foundation as an extractable sibling package, including
  trace validation, evidence-region indexing, claim freshness checks, prompt
  packet generation, and public-doc dogfood coverage.
- Internal ecosystem-provider architecture with Python as the core/reference
  provider and TypeScript/JavaScript as the current experimental maturation
  target.
- TypeScript/JavaScript configured-command provider support, doctor hints,
  file classification, advisory reviewability and suppression facts, and
  structured repair facts for `tsc`, ESLint JSON, and Jest-compatible JSON.
- Provider registry and provider-status documentation that keep experimental
  providers from being presented as Python feature parity.
- Neutral config path and workspace config foundations without changing
  existing `pyproject.toml` behavior for Python repositories.
- Exact repair facts for pytest JUnit XML, coverage JSON, file-length logs, and
  change-budget logs.
- Release-only state drift checks for version/changelog alignment, public
  metadata URLs, Trusted Publisher environment names, and existing release
  evidence.
- `agent-maintainer assess setup` repository onboarding recommendations with
  capped evidence collection.
- `agent-maintainer assess debt` Technical Debt Score artifacts with category
  explanations, confidence, and next actions.
- Strict Pyright ratchet support for baseline-driven strict-typing adoption.
- Advisory reviewability assessment and advisory ecosystem suppression
  classification for TypeScript/JavaScript and Go exploration.
- Split release-polish roadmap detail files to keep the main roadmap usable.

### Changed

- Extracted repair facts, agent context, run artifacts, agent-client hooks,
  context compression, context pack rendering, core tooling capabilities, and
  related internals into clearer package boundaries with Tach coverage.
- Removed the active Go provider from `main` and archived it as history so the
  product does not overclaim polyglot maturity before TypeScript/JavaScript is
  better proven.
- Context pack output now defaults to compact pointer/capsule output; full
  Markdown pack output requires explicit `--print-full`.
- Hook verifier subprocess output now streams through temporary files and
  returns only bounded stdout/stderr summaries to agent-facing context.
- Top-level CLI help is grouped by workflow area for easier first-use scanning.
- Main verifier command execution now preserves stderr visibility, bounds large
  stdout, and cleans up POSIX process groups on timeout.
- Verifier reuse fingerprints include broader repository-state and
  verification-relevant config inputs to avoid stale pass reuse.
- Mutmut run serialization now writes its lock under the active diagnostic
  artifact directory.
- Blocking Mutmut dogfood ratchet is now at `2` survivors and `99%` minimum
  score; current local manual evidence is `343/345` killed, `2` survivors,
  `99.42%`, `0` suspicious, and `0` timeouts.
- Assessment debt scoring now uses latest available verifier manifest outcomes
  and avoids penalizing irrelevant optional gates.
- Provider roadmap docs now explicitly defer new ecosystems until
  TypeScript/JavaScript satisfies the maturation bar.

### Fixed

- Git reference validation now fails early on invalid comparison refs instead
  of producing ambiguous downstream verifier failures.
- Verifier fingerprints include untracked files where relevant, reducing stale
  result reuse across overlapping agent edits.
- Verifier subprocess timeout handling now cleans up process groups and
  preserves bounded failure output.
- pip-audit dogfood scanning now uses the pinned lock fast path and bounded
  runtime behavior.
- Doctor now detects generated bytecode debris such as `__pycache__`, `*.pyc`,
  and duplicate-artifact hazards.
- Dogfood source-checkout detection warns on stale console scripts or installed
  packages pointing outside the local checkout.
- Public docs and roadmap guidance cleaned up stale context-pack,
  provider-maturity, and mutation-testing wording that could mislead future
  agents.

### Beta Notes For 0.1.0b5

- Python remains the core/reference provider. TypeScript/JavaScript remains
  experimental and explicitly configured; it is not feature parity with Python.
- Go provider work is archived out of active `main` for now.
- Broad multi-ecosystem blocking reviewability gates are still deferred.
- Headroom remains optional experimental and is not enabled by default.
- Semgrep remains excluded from `manual` and `all` extras on Python 3.13+
  while upstream dependency resolution remains unstable there.
- Agent-facing output remains intentionally token-bounded; inspect
  `.verify-logs/LAST_FAILURE.md`, run-scoped artifacts, and context expansion
  commands for full detail.

## 0.1.0b4 - 2026-06-29

Fourth beta release of Agent Maintainer.

### Added In 0.1.0b4

- Context-safe repair loop commands for bounded failure summaries, log excerpts,
  file outlines, diff context, and context packs.
- Ratchet baseline status, ranked repair targets, and generated
  `AGENTS.ratchet.md` guidance for legacy-repo cleanup.
- Test-intelligence hints for changed-source tests, Hypothesis candidates,
  Mutmut targets, and CrossHair candidates.
- Cohesive change plans, change-budget integration, and integration branch
  series support for intentional large migrations.
- Optional context compression backend interface with experimental Headroom
  support.
- GitHub Actions/PR summary reports, policy-pack onboarding presets, Archguard
  impact analysis, repair-plan command, agent adapter API, and static HTML
  verification reports.
- Exact repair facts from structured Ruff, Pyright, and Bandit artifacts.

### Changed In 0.1.0b4

- Hook output is quiet on success and bounded on failure: failures now route
  agents to context-pack pointers and verification artifacts instead of dumping
  full logs into the turn.
- Successful post-edit hooks remain silent; Stop/SubagentStop hooks only emit the
  minimal continue response required by agent-client protocols.
- Tach contracts were refit into explicit domain files so every source file stays
  assigned under `root_module = "forbid"` without lumping unrelated paths
  together.
- Changed-code coverage now separates changed source-file coverage from true
  changed-line coverage.
- Explicit change-plan failures take precedence over legacy cohesive-change
  overrides.

### Fixed In 0.1.0b4

- Headroom compression now calls the adapter with message lists and consumes
  compressed result messages correctly.
- Coverage reporting no longer presents whole-file coverage averages as changed
  line coverage.
- Legacy cohesive-change overrides can no longer clear invalid, expired, or
  out-of-scope change-plan failures.

### Beta Notes For 0.1.0b4

- Headroom compression remains optional and experimental. Agent Maintainer works
  without context compression.
- Semgrep remains excluded from `manual` and `all` extras on Python 3.13+ while
  upstream dependency resolution is unstable there.
- Agent-facing failure output is intentionally token-bounded; inspect
  `.verify-logs/LAST_FAILURE.md`, context packs, and uploaded CI artifacts for
  full detail.

## 0.1.0b3 - 2026-06-28

Third beta release of Agent Maintainer.

### Added In 0.1.0b3

- Managed agent-client hook installer, status checks, and runtime support for
  Codex and Claude Code.
- Repo-local Claude Code hook templates and generated hook syntax coverage.
- Agent hook diagnostics in `doctor` and generated agent guidance.
- Agent-client hook documentation covering repo-local and user-level installs.
- Editable README graphics sources, rendered PNGs, and graphics freshness
  checks.
- Roadmap item for systematic cohesive-change override support with required
  PR explanation and verifier checks.

### Changed In 0.1.0b3

- `install`, `bootstrap`, and `init --track agent` now wire managed agent hooks
  through the shared hook installer.
- Starter config and self-dogfooding paths include `.claude/hooks`.
- GitHub artifact upload/download actions moved to the Node 24 action majors.

### Fixed In 0.1.0b3

- Doctor now recognizes generated Claude Code settings that reference
  `.claude/hooks` wrapper files.

### Beta Notes For 0.1.0b3

- Known limitation: Semgrep is excluded from `manual` and `all` extras on
  Python 3.13+ while upstream dependency resolution remains unstable there.
- Managed user-level hooks are repo opt-in; outside repositories with
  `[tool.agent_maintainer]`, they exit successfully without running
  verification.

## 0.1.0b2 - 2026-06-27

Second beta release of Agent Maintainer.

### Added In 0.1.0b2

- Archguard CLI: `archguard` and `python -m archguard` for architecture policy
  governance.
- Architecture decision-note enforcement when Tach policy files change.
- Python compatibility CI matrix for Python 3.11, 3.12, 3.13, and 3.14.
- GitHub release artifact attachment for built wheel and sdist distributions.
- Fresh-strict and legacy-ratchet example projects.
- First-run onboarding walkthrough focused on diagnostics and repair loops.

### Changed In 0.1.0b2

- Agent Maintainer now consumes Archguard for Tach configuration validation.
- The real PyPI publishing environment requires manual reviewer approval.

### Beta Notes For 0.1.0b2

- Known limitation: Semgrep is excluded from `manual` and `all` extras on Python
  3.13+ while upstream dependency resolution is unstable there.

## 0.1.0b1 - 2026-06-27

Initial beta release of Agent Maintainer.

### Added In 0.1.0b1

- Package-first CLI: `agent-maintainer` and `python -m agent_maintainer`.
- `init` tracks: `core`, `agent`, and `hardening`.
- Low-noise verification profiles: `fast`, `precommit`, `full`, `ci`,
  `security`, and `manual`.
- Change budget, file length, suppression budget, structure cohesion, type
  checking, coverage, architecture, dependency hygiene, security, docs/config
  hygiene, and diagnostic artifact support.
- Generated agent guidance via `AGENTS.agent-maintainer.md`.
- Release-only packaging checks for dependency resolution, wheel/sdist builds,
  artifact metadata, and console-script smoke tests.

### Beta Notes For 0.1.0b1

- Starter files and defaults may change before 1.0.
- Public config is intended to stabilize through beta feedback.
