# Changelog

## Unreleased (target: 0.1.0b6)

`0.1.0b6` is an unpublished release candidate. `0.1.0b5` remains the latest
published package and its release-evidence record remains authoritative until
the candidate passes the complete exact-commit release matrix.

### Security Since 0.1.0b5

- All repository-controlled filesystem access is confined to approved roots.
  MCP and DocSync reads reject escapes, special files, oversized inputs, and
  unsafe write destinations before opening or replacing data.
- GitHub Actions use full-SHA-pinned implementations, explicit concurrency, and
  strict unfiltered workflow security checks instead of mutable action tags.
- Publishing requires fresh full, CI, security, manual, and release manifests
  from one clean commit. Every consumer revalidates the exact-commit evidence
  aggregate before using it.
- Wheel and source-distribution transfers carry a deterministic manifest with
  the exact inventory, byte sizes, and SHA-256 digests. Release jobs bind that
  manifest to a separately carried digest and verify it immediately before
  attachment or Trusted Publishing.
- The fixed `markdownlint-cli2` 0.23.0 dependency removes the accepted
  `js-yaml` advisory, and current Semgrep support restores the `manual` and
  `all` extras across Python 3.11 through 3.14.

### Added Since 0.1.0b5

- Structured runtime events now cover checks, hooks, commands, verifier
  artifacts, waits, and efficacy outcomes. New summary, waste, JSONL, and
  OpenTelemetry-compatible export commands make local behavior inspectable
  without uploading raw logs.
- Background-safe durable waits now cover GitHub runs, PR checks, and local
  verifiers with a persistent registry, targeted sweeps, background workers,
  heartbeat handoffs, terminal and app-server rewake backends, and manually
  recoverable state.
- The attention ledger, attention-weighted context packs, recall ledger, and
  surgical next-action ranking retain high-value repair context while reducing
  repeated broad reads.
- Optional MCP commands expose bounded Agent Maintainer operations through
  static, capability-aware handlers while keeping MCP dependencies opt-in.
- Agent-task-broker experiments add handoff results, lock/worktree planning,
  adapter contracts, model-tier routing, and a Codex SDK plan backend under an
  explicitly incubating surface.
- TypeScript/React advisory support now records package/workspace shape,
  configured command ownership, React/Vite/Next fixtures, test and coverage
  repair facts, suppression facts, reviewability thresholds, and doctor/setup
  guidance without claiming Python gate parity.
- Provider-neutral file baselines report matched and changed files, changed
  lines, and compact next actions across configured documentation, config,
  test, and frontend file groups.
- DocSync gained explicit object-end markers, freshness metadata, verifier
  repair facts, extraction review tooling, a standalone README, and an
  onboarding fixture for the supported public boundary.
- Registry-generated configuration reference documentation, versioned
  capability metadata, repair-fact coverage assessment, scoring example
  datasets, and agent efficacy assessment are now available.
- Existing-application onboarding fixtures now exercise a mature `src/`
  library, a flat-layout service with third-party agent configuration, and a
  `uv` Python/JavaScript application through preview, apply, and idempotent
  rerun behavior.
- An owned, expiring dependency-risk register now binds accepted advisories to
  exact OSV expiry records, while Dependabot covers Python, npm, and pinned
  GitHub Actions dependencies.

### Changed Since 0.1.0b5

- Agent-client installation, scaffolding, status, update, and uninstall now use
  one managed hook inventory. Status distinguishes current, stale, missing, and
  intentionally unmanaged files.
- Bootstrap is dependency-only. Hook and pre-commit mutation is an explicit,
  strictly parsed action with side-effect-free preview, conflict classification,
  collision-proof backup, transactional apply, and rollback.
- Initializer preview classifies additions, unchanged files, supported merges,
  conflicts, and user-owned skips. Force no longer means silently replacing
  guidance or unrelated client configuration.
- Complete configuration preflight now resolves file settings, environment
  overrides, and CLI flags through one registry. Unknown, mistyped,
  contradictory, type-confused, out-of-range, or path-escaping policy fails
  closed before behavior begins.
- Detached verifier and wait processes own their terminal lifecycle, persist
  launch/running/terminal state, and separate quality failures from spawn,
  cancellation, and transport failures.
- Strict Pyright debt ratchets by file/rule pair under a versioned,
  tool-and-scope-bound baseline rather than an aggregate error allowance.
- Public documentation now distinguishes published release evidence from
  candidate intent, validates repository-local links, and provides a
  version-matched candidate guide and release index.
- Python 3.11 through 3.14 compatibility CI now builds both distribution
  formats, installs each into a clean environment, and runs every advertised
  console script instead of relying on editable-install smoke alone.
- Consumer-repository doctor and bootstrap flows now honor the requested root,
  linked-worktree metadata, and package-first execution instead of assuming the
  Agent Maintainer source repository.

### Fixed Since 0.1.0b5

- Claude and Codex hook merges preserve unrelated commands and ordering.
  Uninstall removes only managed identities, refuses unowned files, and rolls
  prior removals back if a later operation fails.
- Agent and hardening scaffolds include every configured PR-wait and audit
  wrapper; install, status, update, and uninstall no longer disagree about the
  managed inventory.
- Async verifier readiness, PR wait handoff, heartbeat scoping, local-HEAD wait
  identity, warning handling, targeted sweeps, launchd tool paths, and terminal
  completion detection now remain correct across terminal closure and restart.
- Runtime-event waste, attention scanning, efficacy metrics, retained mutation
  results, duplicate artifact warnings, and Pylint, Vulture, DocSync,
  TypeScript, pytest, coverage, and change-budget repair facts now handle their
  defensive and fallback paths consistently.
- The mutation quality gate and strict typing baseline are restored without
  lowering thresholds, and repository Markdown links resolve after roadmap
  archival moves.
- Pytest now removes repository-local Git overrides inherited from hooks, so
  synthetic repositories cannot replace a caller's staged or worktree index.

### Experimental and Advisory

- Task-broker, model-tier routing, Codex SDK planning, optional MCP, and
  TypeScript/React provider work remain opt-in or advisory. They do not expand
  the stable Python blocking contract for this beta.
- Review [the b6 candidate notes](docs/releases/0.1.0b6.md) and
  [the upgrade guide](docs/upgrading-to-0.1.0b6.md) before evaluating the
  candidate in an existing application.

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
