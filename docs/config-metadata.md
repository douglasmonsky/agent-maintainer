# Configuration Metadata

Agent Maintainer treats `[tool.agent_maintainer]` as a public surface. Each
field in `MaintainerConfig` has metadata for:

- TOML key path, including nested `[tool.agent_maintainer.diagnostics]` aliases.
- `AGENT_MAINTAINER_*` environment override coverage.
- Whether `agent-maintainer verify` exposes a CLI override.
- A short docs label.
- Stability level for beta-facing documentation.

The metadata inventory exists to prevent drift. Adding a config field without
classifying its env var, CLI override status, and docs surface should fail tests
before it reaches users.

Configuration still resolves in the same order:

1. built-in defaults;
2. mode preset;
3. explicit `pyproject.toml` values;
4. `AGENT_MAINTAINER_*` environment variables;
5. verifier CLI flags.

Use `python3 -m agent_maintainer doctor --strict` after changing config policy,
and use `python3 -m agent_maintainer guidance --check` when generated guidance
may need to change.
