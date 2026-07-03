+++
id = "agent-client-hooks-package"
kind = "mechanical-migration"
status = "active"
base_ref = "origin/main"
expires = 2026-07-17
allowed_paths = [
  ".agent-maintainer/change-plans/agent-client-hooks-package.md",
  ".agent-maintainer/change-plans/docsync-dogfood-seed.md",
  "AGENTS.agent-maintainer.md",
  "docs/ROADMAP.md",
  "docs/architecture/decisions/**",
  "docs/roadmap/full-roadmap-blueprint.md",
  "docs/roadmap/internal-package-boundaries.md",
  "docs/roadmap/phases/phase-115-agent-client-hooks-package.md",
  "pyproject.toml",
  "semgrep.yml",
  "tach.toml",
  "src/agent_client_hooks/**",
  "src/{agent_maintainer/hooks => agent_client_hooks}/adapters.py",
  "src/{agent_maintainer/hooks => agent_client_hooks}/merge.py",
  "src/{agent_maintainer/hooks => agent_client_hooks}/templates.py",
  "src/agent_maintainer/core/scaffold/templates.py",
  "src/agent_maintainer/core/tach.domain.toml",
  "src/agent_maintainer/hooks/**",
  "tests/hooks/**",
]
forbidden_paths = [
  "config/prod/**",
  ".env",
  ".env.*",
  ".docsync/out/**",
]
max_changed_files = 80
max_changed_lines = 6000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: agent-client-hooks-package

## Why this change intentionally large

The client-hook extraction touches templates, adapters, merge helpers, product
manager imports, Tach ownership, repo config paths, tests, and docs together.
Those files form one behavior-preserving package boundary move.

## Why this should not be split smaller

Moving templates without adapters would leave install planning split across
packages. Moving adapters without manager imports would leave the extracted
package unused. The smallest coherent slice is: new package, compatibility
shims, direct tests, Tach/config/docs updates.

## What allowed to change

- `agent_client_hooks` package files.
- Compatibility shims under `agent_maintainer.hooks`.
- Product imports in `agent_maintainer.hooks.manager` and runtime constants.
- Hook template/adapter/merge tests.
- Tach/config/static-analysis paths and generated guidance.
- Architecture decision and roadmap files for this phase.

## What must not change

- Hook install CLI behavior.
- Generated Codex/Claude config semantics.
- Hook runtime verification, context assembly, audit logging, subprocess
  execution, and hook output contract.
- Existing import compatibility for `agent_maintainer.hooks.templates`,
  `agent_maintainer.hooks.adapters`, and `agent_maintainer.hooks.merge`.

## Verification Plan

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/hooks -q`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m ruff check src/agent_client_hooks src/agent_maintainer/hooks tests/hooks`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer guidance --check`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer change-plan check`
- final verifier profiles: `precommit`, `full`, `ci`, `security`, `manual`.

## Rollback Plan

Restore templates, adapters, and merge helpers under `agent_maintainer.hooks`
and remove `src/agent_client_hooks`. Generated user files and runtime hook
behavior should not require migration because this phase preserves emitted
config and wrapper content.

## Follow-up ratchet work

After the extraction series settles, decide whether compatibility shims remain
supported internal paths or are removed in a documented cleanup phase. Do not
add new agent clients until the package boundary has proven stable.
