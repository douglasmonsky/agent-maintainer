# 2026-07-02: Provider API Stability

## Status

Accepted.

## Context

Agent Maintainer now has Python as the core provider and two experimental
non-Python provider: TypeScript/JavaScript. That proves the internal
provider seam can support more than one ecosystem shape, but it has not yet
survived enough external use to freeze as a public plugin API.

Publishing external provider discovery too early would make internal refactors
harder, especially while policy checks, file classification, structured repair
facts, scaffolding, and setup advice are still evolving.

## Decision

Do not publish an external provider plugin API during beta.

Community language support should continue to land as built-in experimental
providers through normal pull request review. Internal provider interfaces may
change between beta releases when needed to preserve Python excellence, improve
diagnostics, or simplify provider ownership.

Revisit external provider loading only after:

- at least two non-Python built-in providers have been used outside this repo;
- provider capability boundaries are stable across real fixture and user repos;
- structured artifact parser expectations are clearer;
- scaffold and doctor expectations are documented per provider;
- migration cost for built-in providers is understood.

## Future Migration Path

If external providers become appropriate, design them as a separate proposal.
The migration should:

- keep built-in providers as the reference implementation;
- keep Python as the core compatibility provider;
- define provider discovery and trust behavior explicitly;
- include a versioned provider interface;
- include compatibility tests for built-in providers;
- document how experimental built-in providers can graduate to external
  packages, if that ever becomes useful.

## Consequences

- The beta surface remains simpler and easier to change.
- Community contributions remain reviewable in-repo.
- External packages cannot yet inject checks into Agent Maintainer.
- The provider guide remains accurate: built-in experimental providers are the
  supported contribution path for now.
