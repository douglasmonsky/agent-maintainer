# Ecosystem Provider Status

Agent Maintainer is Python-core today, with an internal provider seam for
careful expansion. Do not read experimental providers as feature parity.

| Ecosystem | Maturity | Current Support | Not Yet |
|---|---|---|---|
| Python | Core/reference | Full check catalog, reviewability policies, coverage, diff coverage, mutation ratchets, security/dependency checks, doctor support, repair facts, starter templates. | External plugin API. |
| TypeScript/JavaScript | Experimental | Explicit configured commands for lint, typecheck, and tests; file classification; advisory suppression classification; `tsc --pretty false` and ESLint JSON repair facts; doctor setup rows. | Package-manager autodetection, starter files, coverage adapters, mutation testing, dependency/security adapters. |
| Go | Deferred | Not active in `main`. Historical canary work validated that providers should not become Node-specific. | Reintroduction requires a new phase with fixtures, doctor rows, explicit commands, and advisory evidence. |

## Current Focus

TypeScript/JavaScript is the first serious non-Python provider maturation
track. Go is deferred from the active provider surface while TypeScript
fixtures and real-repo evidence mature. Do not read Go as currently supported.

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
gates. TypeScript changed files and advisory suppressions are visible through
`assess reviewability` so policy can be proven before it blocks.
See [Multi-Ecosystem Reviewability Policy](multi-ecosystem-reviewability-policy.md).

## Related Reading

- [Experimental TypeScript/JavaScript Provider](typescript-javascript-provider.md)
- [TypeScript Provider Maturation Notes](case-studies/typescript-provider-maturation.md)
- [Multi-Ecosystem Reviewability Policy](multi-ecosystem-reviewability-policy.md)
- [Provider Contribution Guide](provider-contribution-guide.md)
- [Polyglot Ecosystem Provider Roadmap](roadmap/polyglot-ecosystem-providers.md)
