# Pre-1.0 API Support Policy

## Supported beta surfaces

The documented `agent-maintainer`, `archguard`, and `docsync` commands,
documented `[tool.agent_maintainer]` keys, and schema-versioned documented
artifacts are supported for the current beta line.

## Intended beta Python API

`docsync.api` is the only initially named supported Python import surface.
Adding another import requires public documentation and a compatibility test.

## Internal and unstable surfaces

Distribution is not an API promise. Other modules under `agent_maintainer`,
`archguard`, `agent_context`, `agent_client_hooks`, `agent_repair_facts`,
`agent_run_artifacts`, `agent_waits`, and `docsync` remain internal unless this
policy explicitly promotes them.

## Change and deprecation window

Supported beta surfaces receive release notes, upgrade guidance, and at least
one beta release of notice before removal unless they are unsafe or unusable.
Internal surfaces may change without deprecation.

## Compatibility shims

The [compatibility-shim inventory](compatibility-shims.md) records forwarding
owners, support windows, removal conditions, and earliest removal releases.
