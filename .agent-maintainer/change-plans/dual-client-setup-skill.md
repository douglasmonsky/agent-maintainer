+++
id = "dual-client-setup-skill"
kind = "cohesive-feature"
status = "active"
base_ref = "origin/main"
expires = 2026-07-28
allowed_paths = [
  ".agent-maintainer/change-plans/dual-client-setup-skill.md",
  ".docsync/**",
  "README.md",
  "config/dependency-risks.toml",
  "docs/agent-maintainer-setup-skill.md",
  "docs/architecture/decisions/2026-07-13-dual-client-setup-skill.md",
  "docs/dependency-risk-register.md",
  "docs/quick-start.md",
  "docs/superpowers/plans/2026-07-13-dual-client-setup-skill.md",
  "docs/superpowers/specs/2026-07-13-dual-client-setup-skill-design.md",
  "pyproject.toml",
  "osv-scanner.toml",
  "src/agent_maintainer/cli.py",
  "src/agent_maintainer/skill/**",
  "tach.toml",
  "tests/config/test_config_cli_boundary.py",
  "tests/docs/test_first_touch_docs.py",
  "tests/docsync/test_public_doc_trace.py",
  "tests/packaging/**",
  "tests/release/test_release_packaging.py",
  "tests/skill/**",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 50
max_changed_lines = 3200
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: dual-client-setup-skill

## Why this change intentionally large

The feature packages one canonical setup skill, exposes its lifecycle through the public CLI, and installs the same owned resource for Codex and Claude Code. Safe updates require ownership metadata, transaction boundaries, package data, architecture contracts, tests, and user documentation to land together.

## Why this should not be split smaller

Splitting the package resource, lifecycle, CLI, or client documentation would leave a published intermediate commit that either cannot install the skill safely or advertises behavior unavailable from one client. The implementation was already developed and reviewed as one cohesive feature across nine focused commits.

## What allowed to change

Only the exact setup-skill implementation, its CLI boundary, package metadata, architecture contracts, focused tests, DocSync evidence, public setup documentation, and the time-bounded dependency-risk record listed in allowed_paths may change.

## What must not change

Existing repository initialization behavior, unrelated command surfaces, production configuration, credentials, deployment workflows, and other client integrations must remain unchanged. This work must not add an MCP server, a compatibility shim, or broad lifecycle abstractions.

## Verification plan

Run the complete pytest suite, clean wheel and source-distribution installation smoke, Ruff, Wemake, Pylint, Pyright, Tach, Archguard, DocSync, Markdown lint, secret scanning, the precommit profile, and the CI profile. Confirm both installed client copies report current and preserve the recorded live-client limitations.

## Rollback plan

Revert the feature commits and uninstall the owned setup-skill directories through the lifecycle command. The ownership manifest and staged replacement transaction prevent unrelated client files from being removed during rollback.

## Follow-up ratchet work

Mark this plan complete immediately after integration. Revisit DR-005 by 2026-07-28 and remove its single-advisory pip-audit ignore as soon as Semgrep permits Click 8.3.3 or newer.
