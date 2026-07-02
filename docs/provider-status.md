# Ecosystem Provider Status

Agent Maintainer is Python-core today, with an internal provider seam for
careful expansion. Do not read experimental providers as feature parity.

| Ecosystem | Maturity | Current Support | Not Yet |
|---|---|---|---|
| Python | Core/reference | Full check catalog, reviewability policies, coverage, diff coverage, mutation ratchets, security/dependency checks, doctor support, repair facts, starter templates. | External plugin API. |
| TypeScript/JavaScript | Experimental | Explicit configured commands for lint, typecheck, and tests; file classification; advisory suppression classification; `tsc --pretty false` and ESLint JSON repair facts; doctor setup rows. | Package-manager autodetection, starter files, coverage adapters, mutation testing, dependency/security adapters. |
| Go | Experimental | Explicit configured commands for format, vet, and tests; file classification; advisory suppression classification; doctor setup rows. | Structured repair facts, starter files, coverage adapters, dependency/security adapters, workspace autodetection. |

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
Experimental TypeScript/JavaScript and Go providers do not yet receive blocking
change-budget, suppression-budget, file-length, structure-cohesion, or
test-relevance policy gates. See
[Multi-Ecosystem Reviewability Policy](multi-ecosystem-reviewability-policy.md).

## Related Reading

- [Experimental TypeScript/JavaScript Provider](typescript-javascript-provider.md)
- [Experimental Go Provider](go-provider.md)
- [Multi-Ecosystem Reviewability Policy](multi-ecosystem-reviewability-policy.md)
- [Provider Contribution Guide](provider-contribution-guide.md)
- [Polyglot Ecosystem Provider Roadmap](roadmap/polyglot-ecosystem-providers.md)
