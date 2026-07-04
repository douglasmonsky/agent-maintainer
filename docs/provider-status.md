<!-- docsync:object docs.provider_status.overview -->
# Ecosystem Provider Status

Agent Maintainer is Python-core today, with an internal provider seam for
careful expansion. Experimental providers are not feature parity.

## Current Providers

| Ecosystem | Maturity | Current Support | Not Yet |
|---|---|---|---|
| Python | Core/reference | Full check catalog, reviewability policies, coverage, diff coverage, mutation ratchets, security and dependency checks, doctor support, repair facts, and starter templates. | External plugin API. |
| TypeScript/JavaScript | Experimental | Explicit configured lint/typecheck/test commands; file classification; advisory suppression classification; `tsc --pretty false`, ESLint JSON, and Jest-compatible JSON repair facts; doctor setup rows. | Package-manager autodetection, starter files, coverage adapters, mutation testing, dependency/security adapters, and blocking reviewability gates. |

There is no active Go provider on `main`. Go remains archived historical work
until TypeScript/JavaScript has stronger evidence and the provider seam has
settled.

## Current Focus

TypeScript/JavaScript is the first serious non-Python provider maturation track.
It should not move beyond experimental status until it satisfies the promotion
bar in [TypeScript Provider Maturation Notes](case-studies/typescript-provider-maturation.md).


DocSync is not an ecosystem provider. It is a repository documentation
traceability gate that Agent Maintainer detects when `.docsync/trace.yml`
exists and runs in local verification profiles.
## Design Rule

Core owns the verification loop: profiles, command execution, bounded logs,
run-scoped diagnostics, reports, context packs, repair plans, and hooks.

Providers own ecosystem-specific excellence: commands, file classification,
suppression rules, coverage artifacts, doctor rows, repair facts, scaffold
snippets, and maturity-specific guidance.

If a provider abstraction makes an existing Python feature harder to express,
the abstraction is wrong. Python remains the reference provider and may stay
richer than experimental providers.

## Reviewability Policy

Current reviewability gates are globally scheduled but Python-backed.
Experimental TypeScript/JavaScript does not yet receive blocking change-budget,
suppression-budget, file-length, structure-cohesion, or test-relevance policy
gates.

TypeScript/JavaScript changed files are advisory, but blocking reviewability
policy is not fully multi-ecosystem yet.

In the current beta:

- Python remains the core/reference provider with full reviewability policy.
- TypeScript/JavaScript is the first serious non-Python maturation target.
- TypeScript/JavaScript providers run explicitly configured commands.
- TypeScript/JavaScript emits advisory changed-file and suppression facts
  through `assess reviewability`.
- TypeScript/JavaScript does not yet receive blocking change-budget,
  suppression-budget, file-length, structure-cohesion, or test-relevance gates.
<!-- docsync:object.end docs.provider_status.overview -->
