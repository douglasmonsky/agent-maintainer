# Generated Agent Maintainer Guidance

Generated from `[tool.agent_maintainer]` by
`python3 -m agent_maintainer guidance`. Do not edit by hand.
Details: `docs/agent-maintainer-guidance.md`.

## Hard Rules

- Keep commits small, tested, and aligned with configured boundaries.
- Treat failing checks as design feedback before adding suppressions.
- Update source, tests, docs, and config together when behavior changes.
- Do not relax thresholds or architecture rules to make checks pass.

## Context Hygiene

- Prefer `rg --files` or `git ls-files` for file discovery.
- Do not bulk-read generated/cache/binary paths:
  `__pycache__`, `*.pyc`, `.venv`, `venv`, `.verify-logs`, `.coverage`,
  `coverage.xml`, `htmlcov`, `mutants`, `build`, `dist`.
- Use `AGENT_MAINTAINER_WRITE_BYTECODE=true` or
  `AGENT_MAINTAINER_KEEP_MUTANTS=true` only when explicitly debugging
  those artifacts.

## Repo Contract

- Mode: `fresh-strict`
- Source roots: `src/agent_maintainer`, `src/archguard`, `src/docsync`, `.codex/hooks`, `.claude/hooks`
- Tests: `tests`
- Architecture: `tach` with Tach domain contracts
- If Tach policy changes, add or update an ADR under
  `docs/architecture/decisions/`.

## Blocking Limits

- Coverage floors: total `90%`, changed `90%`
- File length: `500` physical / `375` source lines
- Change budget blocks: `600` lines or `12` files
- New suppression budget: `1`
- Complexity: Ruff `8`, Xenon `B`
- Source-only changes without test-file changes: `blocked`

## Active Gates

- pip-audit
- Mutmut
- Semgrep
- OSV Scanner
- Python SBOM
- License checking
- Secret scanning: gitleaks
- wemake-python-styleguide
- Interrogate
- Markdown linting
- YAML linting
- TOML formatting
- Schema validation

## Failure Loop

- Keep chat updates summary-first: completed check, actionable failure,
 or plan change.
- Do not emit routine `still running` updates for expected long checks.
- Use `apply_patch` for manual edits; avoid heredoc rewrite commands.
- Read `.verify-logs/LAST_FAILURE.md` before changing code or config.
- Prefer run-scoped `context --log-dir ...` commands from failures.
- Expand only needed context:
 `python3 -m agent_maintainer context failures --limit 20`.
- Fix the root cause; do not lower thresholds or add broad suppressions.

## Required Commands

- Normal finish: `python3 -m agent_maintainer verify --profile precommit`
- Larger/shared changes: `python3 -m agent_maintainer verify --profile full`
- Before PR/merge: run `full`, `ci`, `security`, and `manual` once.
- Config changes: `python3 -m agent_maintainer guidance` and
  `python3 -m agent_maintainer doctor`

## Escape Hatches

- Prefer config or code fixes over one-off environment overrides.
- Use cohesive change plans for intentional large diffs; include a reason
  and verification plan.
- If a check is wrong, make the smallest fix to the check, config, or docs.
