# Scoring Dataset Boundary

## Status

Accepted.

## Context

Future routing and scoring work needs labeled examples before introducing
deterministic heuristics, LLM scoring, DSPy optimization, or provider-specific
model choices. Phase 159 creates that local dataset surface.

## Decision

Add `agent_maintainer.scoring` as a standalone package for provider-neutral
example data. Its CLI depends on the dataset module, and the dataset module does
not import runtime-event, task-broker, provider, or optimization framework code.

Examples are bundled in code for immediate inspection and may be appended to
`.verify-logs/scoring/examples.jsonl` through the CLI. The export format is
JSONL so future tools can consume examples without a new dependency.

## Consequences

Scoring examples can be collected and exported before any scorer is introduced.
The package remains local and provider-neutral, so no model provider names,
credentials, network calls, or optimization frameworks enter this phase.

Alternatives considered:

- Put examples under task-broker modules. Rejected because examples are reusable
  routing evidence, not broker execution state.
- Store only Markdown examples. Rejected because future scoring tools need a
  structured JSONL contract.
- Add DSPy or LLM scoring now. Rejected because this phase only prepares the
  dataset and explicitly avoids optimization framework adoption.
