# 2026-07-02: Experimental Go Provider

## Status

Accepted.

## Context

The ecosystem-provider roadmap needs a second non-Python provider to validate
that the internal provider seam is not shaped only around Python or
TypeScript/JavaScript. Go is a useful second ecosystem because its standard
toolchain is more uniform than Node-style package manager stacks, while still
having distinct source, test, dependency, generated, and workspace concepts.

## Decision

Add an experimental Go provider under `agent_maintainer.ecosystems.go` with
explicit-command checks and file classification. The provider remains disabled
by default and does not autodetect commands.

The central catalog may depend on `agent_maintainer.ecosystems.go.provider` so
the verifier can include Go checks when `[tool.agent_maintainer].enable_go` is
true. The Go provider may depend only on ecosystem models and the shared
`Check` model.

## Consequences

- Python remains the core/reference provider.
- Go validates the provider seam across a second non-Python ecosystem.
- Go support is useful but intentionally smaller than Python support.
- Deeper capabilities such as structured output parsing, coverage, dependency
  hygiene, and starter scaffolds remain future work.

## Alternatives Considered

- Add Rust instead. Rust has strong standard tooling, but Go is a smaller first
  validation target for a non-Node ecosystem.
- Autodetect `go` commands. This was rejected for the experimental phase; the
  provider should first prove explicit command configuration and classification.
- Publish a plugin API. This remains deferred until built-in providers prove the
  abstraction through real use.
