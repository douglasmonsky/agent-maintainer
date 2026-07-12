# Pre-1.0 API Support Policy

## Current-version documented surfaces

Documented commands, configuration, and schema-versioned artifacts are expected to work for the exact installed beta version. There is no cross-version compatibility guarantee before 1.0.

## Current Python entry points

`docsync.api` is the intended DocSync integration boundary for current code, not a frozen signature. It may change or be removed without a deprecation window before 1.0.

## Internal and unstable surfaces

Distribution is not an API promise. Internal packages and modules may change or
be removed without compatibility shims.

## Change communication

Release notes and upgrade guidance should explain material user-facing changes
when useful, but communication is not a compatibility gate.

## Forwarding-module cleanup

The [compatibility-shim cleanup inventory](compatibility-shims.md) identifies
canonical replacements. Compatibility is not a reason to retain a shim.
