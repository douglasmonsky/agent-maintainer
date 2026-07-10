<!-- docsync:object docs.config_metadata.overview -->
# Configuration Metadata

Agent Maintainer treats `[tool.agent_maintainer]`, neutral TOML files, and
`AGENT_MAINTAINER_*` overrides as one public surface. The authoritative field
registry covers every field in `MaintainerConfig` with metadata for:

- Canonical TOML key path and explicit compatibility aliases.
- Value kind, choices, bounds, path/profile handling, and whether empty values
  are allowed.
- `AGENT_MAINTAINER_*` environment override coverage.
- Whether `agent-maintainer verify` exposes a CLI override.
- A short docs label.
- Stability level for beta-facing documentation.

The registry drives coercion, validation, environment maps, compatibility
metadata, and generated reference data. Adding a config field without a full
classification fails drift tests before it reaches users. Unknown top-level or
nested keys fail with their physical source and dotted public key. Established
top-level diagnostic and file-baseline spellings remain aliases; using an alias
and canonical spelling together fails rather than depending on merge order.

Configuration still resolves in the same order:

1. built-in defaults;
2. mode preset;
3. explicit `pyproject.toml` values;
4. `AGENT_MAINTAINER_*` environment variables;
5. verifier CLI flags.

The complete resolved policy is validated after file and environment merges
and again after verifier CLI overrides. Validation distinguishes booleans from
integers and enforces numeric bounds, cross-field ordering, compression
consistency, repository-scoped paths, and verification profile names before
behavior continues.

Use `python3 -m agent_maintainer doctor --strict` after changing config policy,
and use `python3 -m agent_maintainer guidance --check` when generated guidance
may need to change.
<!-- docsync:object.end docs.config_metadata.overview -->
