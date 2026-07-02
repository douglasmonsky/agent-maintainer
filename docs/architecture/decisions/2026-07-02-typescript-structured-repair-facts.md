# TypeScript Structured Repair Facts

## Status

Accepted.

## Context

The experimental TypeScript provider runs configured commands and writes normal
bounded logs. Early adopters still need concise repair-loop feedback when common
tool output is structured enough to parse.

## Decision

Add TypeScript diagnostic parsing under
`agent_maintainer.ecosystems.typescript.diagnostics`. Core verifier summaries
and context exact-fact extraction consume those parsed diagnostics for two
common outputs:

- TypeScript compiler diagnostics from `tsc --pretty false`;
- ESLint JSON formatter output.

No new artifact-path config is introduced in this phase.

## Rationale

Provider-owned parsing keeps TypeScript output knowledge out of generic core
logic while still letting core surfaces render compact summaries and exact
repair facts. Parsing logs rather than adding artifact fields keeps configured
commands simple and avoids prescribing an ESLint or TypeScript command shape.

## Alternatives

- Add TypeScript artifact-path config now. Rejected because it increases config
  surface before the provider is proven in real repos.
- Parse arbitrary JavaScript test and coverage output now. Rejected because test
  runners and coverage formats vary too widely for this phase.

## Boundary Rules

- The TypeScript ecosystem module owns TypeScript/ESLint diagnostic shapes.
- Core reporting may summarize parsed TypeScript diagnostics.
- Context packs may convert parsed TypeScript diagnostics into exact facts.
- Malformed output must fall back to raw bounded summaries and generic facts.
- Do not require package-manager autodetection or public plugin APIs for parser
  support.
