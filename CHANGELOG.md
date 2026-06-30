# Changelog

## Unreleased

### Added

- Exact repair facts for pytest JUnit XML, coverage JSON, file-length logs, and
  change-budget logs.
- Release-only state drift checks for version/changelog alignment, public
  metadata URLs, Trusted Publisher environment names, and existing release
  evidence.

### Changed

- Hook verifier subprocess output now streams through temporary files and returns
  only bounded stdout/stderr summaries to agent-facing context.
- Top-level CLI help is grouped by workflow area for easier first-use scanning.

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
