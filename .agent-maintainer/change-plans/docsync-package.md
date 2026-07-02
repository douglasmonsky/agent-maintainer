+++
id = "docsync-package"
kind = "mechanical-migration"
status = "active"
base_ref = "origin/main"
expires = 2026-07-16
allowed_paths = [
  ".agent-maintainer/change-plans/**",
  ".docsync/**",
  "AGENTS.agent-maintainer.md",
  "AGENTS.md",
  "config/vulture-whitelist.py",
  "docs/**",
  "pyproject.toml",
  "src/**",
  "tests/**",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 120
max_changed_lines = 12000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: docsync-package

## Why this change intentionally large

This adds DocSync as a new sibling package with its own CLI, API, trace parser, evidence scanner, review packets, attestations, tests, starter `.docsync` files, and repository guidance. The package surface is intentionally broad enough to provide an end-to-end documentation traceability foundation without including the experimental knowledge graph, vector retrieval, GraphQL, or wiki prototype.

## Why this should not be split smaller

Splitting the package into many partial commits would leave intermediate states where the CLI, index, checks, attestations, review packets, and docs disagree. The reviewable boundary is the new `src/docsync` package plus its focused tests and package metadata.

## What allowed to change

Allowed changes are DocSync package files, DocSync tests, package metadata, generated DocSync starter configuration, repository guidance that mentions DocSync, the architecture decision for the package addition, and the Vulture whitelist entry for dynamic console entry points. Existing concurrent Agent Maintainer worktree changes may be present during verification but are not part of the DocSync implementation scope.

## What must not change

Do not change production credentials, environment files, production deployment configuration, billing configuration, or private data. Do not widen DocSync dependencies to import `agent_maintainer` or `archguard`; the package must remain extractable.

The broader DocSync knowledge graph, vector retrieval, GraphQL, and wiki prototype is preserved on `experiment/docsync-knowledge-graph` for later evaluation. It is intentionally excluded from this foundation PR to keep cohesion high and avoid feature bloat before the traceability workflow is proven.

## Verification plan

Run focused DocSync tests, package metadata tests, Ruff format/check, Wemake, Pyright, Tach config validation, architecture decision checks, suppression-budget, diff whitespace checks, and the full Agent Maintainer verification profile before completion.

## Rollback plan

Rollback is to remove the DocSync package files, `.docsync` starter files, DocSync tests, package metadata entries, DocSync guidance/docs, and this change plan. Existing unrelated Agent Maintainer changes must be left untouched.

## Follow-up ratchet work

After the package lands, tighten DocSync coverage around packed Git object handling or centralize an audited Git command adapter if the local diff reader is expanded. Consider splitting future DocSync feature work into smaller package-local change plans once the initial surface exists.
