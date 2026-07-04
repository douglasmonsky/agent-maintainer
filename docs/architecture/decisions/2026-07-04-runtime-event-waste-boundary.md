# Runtime Event Waste Boundary

## Status

Accepted.

## Context

The priority-one cadence waste roadmap needs a local report that summarizes
duplicated verification and process-waste signals from runtime event JSONL
files. Runtime event summary code already owns compact, non-sensitive reporting
over local event records.

## Decision

Add `agent_maintainer.runtime_events.waste` as a sibling runtime-events module.
It depends only on `runtime_events.read`, emits aggregate signals, and does not
read raw conversation logs or verifier output logs. The runtime-events CLI may
depend on this module to serve `events waste`.

## Alternatives Considered

- Put cadence waste analysis in `summary.py`. Rejected because normal event
  summaries and waste heuristics have different audiences and growth paths.
- Put the report under `assess/`. Rejected for now because the command consumes
  runtime event artifacts directly and should stay close to that local log
  boundary.

## Boundary Guardrails

- `runtime_events.waste` must not import verifier internals.
- `runtime_events.waste` must not read conversation transcripts.
- Future richer signals should prefer runtime event schema additions over
  parsing raw command output or agent chat text.
