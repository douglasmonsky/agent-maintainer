# Code and Repository Conventions

- Prefer maintainable, explicit Python: typed domain objects, explicit return types on public functions, small cohesive functions, clear validation, and helpful errors.
- Ruff line length is 100; configured complexity ceiling is 8. Repository hard limits are 500 physical/375 source lines per file; split functions around 75 lines unless a local reason is documented.
- New behavior requires tests and changed source must be test-backed. Coverage floors are 90% total and 90% changed code.
- Suppressions must be narrow and justified; do not use broad `noqa`, unqualified `type: ignore`, or threshold/baseline weakening as a repair.
- Domain code must not depend on CLI/UI/filesystem/network infrastructure. Preserve exact Tach dependencies and `root_module = "forbid"`; change architecture contracts only with a matching ADR.
- External boundaries should be explicit and testable. Mutation/install/init behavior is previewable, conflict-aware, rollback-safe, and must preserve user-owned configuration.
- Validate complete resolved configuration before behavior; unknown or invalid config fails closed.
- `AGENTS.agent-maintainer.md` is generated from `pyproject.toml`; never hand-edit it. `.docsync/trace.yml` is human-authored, while `.docsync/out/` and `.verify-logs/` are generated.
- DocSync remains an extractable sibling and communicates through `docsync.api`; do not introduce imports from `docsync` into Agent Maintainer internals that violate its boundary.
- Keep changes cohesive; update source, tests, docs, configuration, generated references, and architecture notes together when their contracts change.
