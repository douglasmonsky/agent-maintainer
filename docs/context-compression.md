# Context Compression

Context compression is an optional layer for shrinking supporting evidence in
context packs. It never replaces exact diagnostics required to fix a failing
check.

Default context packs remain deterministic and bounded without external
services. Compression is opt-in through either CLI flags or
`[tool.agent_maintainer]` configuration.

## Built-In Backends

Agent Maintainer includes deterministic built-in compression backends:

- `none`: keep supporting context unchanged.
- `truncate`: keep a bounded prefix.
- `extractive`: keep lines selected from supporting context.

The compression interface preserves required terms. If a backend drops a
required preserve term, Agent Maintainer falls back to deterministic extractive
compression.

## Optional Headroom Backend

Install optional Headroom support explicitly:

```bash
python -m pip install "agent-maintainer[compression]"
```

Run a context pack with Headroom compression:

```bash
python -m agent_maintainer context pack --compress headroom
```

Require Headroom compression instead of falling back:

```bash
python -m agent_maintainer context pack --compress headroom --require-compression
```

When Headroom is missing and compression is required, the command fails with
installation guidance. When Headroom fails and compression is not required,
Agent Maintainer warns and uses deterministic extractive compression.

## Safety Boundary

Optional providers receive only sanitized supporting context from selected logs
and file outlines. They do not receive exact repair facts, structured manifests,
ratchet fingerprints, change-plan scopes, or raw unredacted logs.
