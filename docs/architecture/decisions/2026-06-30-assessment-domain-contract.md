# 2026-06-30: Assessment Domain Contract

## Status

Accepted.

## Context

The public onboarding work adds `python3 -m agent_maintainer assess setup` and
`python3 -m agent_maintainer assess debt`. These commands need repository
evidence collection, setup recommendation logic, debt scoring, and text/JSON
rendering without mixing that behavior into verifier or report modules.

## Decision

Add an `agent_maintainer.assess` domain contract with explicit modules for:

- `cli`: command orchestration;
- `evidence`: local repository evidence collection;
- `setup_advisor`: track, preset, gate, and prompt recommendations;
- `debt_categories`: Technical Debt Score category scoring;
- `debt_score`: score report assembly and artifact writing;
- `reporting`: human and JSON renderers;
- `models`: immutable report data structures.

The CLI may depend on config loading and the assessment helpers. The scoring
modules may depend on config schema and models. Rendering stays downstream of
models and does not import verifier internals.

## Consequences

Assessment remains advisory and local-only. Verifier/report surfaces can read
assessment artifacts without owning scoring policy. Future setup or score
changes should update this domain contract instead of adding hidden imports
from verifier, report, or hook modules.

## Alternatives Considered

- Put setup and debt logic under `core`: rejected because assessment is a
  product-facing command family with its own models and policy.
- Put debt scoring under `report`: rejected because the score also needs CLI
  and JSON output independent of HTML reports.
- Leave the new files in the root assessment module without Tach assignment:
  rejected because strict Tach should account for every source file.
