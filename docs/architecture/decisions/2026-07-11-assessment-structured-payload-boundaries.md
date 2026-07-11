# 2026-07-11: Assessment Structured Payload Boundaries

## Status

Accepted.

## Context

Assessment commands consume verifier manifests, runtime-event attributes, and
repository TOML. Container checks established only that values were dictionaries
or lists, leaving their keys and elements unknown to strict Pyright. Repair-fact
JSON rendering also inspected the private `__dataclass_fields__` attribute, and
the assessment CLI annotated argparse's private subparser implementation.

Unlike standalone packages, `agent_maintainer.assess` is application code and
may depend inward on the existing dependency-free
`agent_maintainer.core.structured_values` boundary.

## Decision

Debt scoring, efficacy reporting, follow-through metrics, repository evidence,
and repair-fact coverage normalize decoded objects and arrays through
`agent_maintainer.core.structured_values`. The corresponding dependency edges
are recorded in `src/agent_maintainer/assess/tach.domain.toml`.

Repair-fact rendering uses public `dataclasses.fields` and `is_dataclass` APIs.
The CLI accepts the public `add_parser` callback it needs instead of naming
argparse's private `_SubParsersAction` class.

## Consequences

Assessment inputs cross one runtime-validated boundary before status, metric,
debt, or coverage calculations traverse them. Malformed neighboring records are
ignored without obscuring valid failures, and nested runtime attributes fail
closed. Pyright, IDEs, and future agents can follow explicit string-keyed
mappings rather than reconstructing implicit shapes.

No new helper package, external dependency, suppression, or `Any` annotation is
introduced. One existing private-attribute suppression is removed.

## Alternatives Considered

- Duplicate normalizers in each assessment module. Rejected because application
  code already owns a stable provider-neutral structured-value boundary.
- Add casts or suppressions at each failing expression. Rejected because those
  approaches would hide malformed external shapes and private API use.
- Continue annotating argparse's private implementation. Rejected because a
  typed callback describes the durable behavior without coupling to that class.
- Serialize dataclasses with `__dataclass_fields__`. Rejected because the public
  `dataclasses` inspection APIs provide the same behavior without private access.

## Verification

Mapped tests cover malformed checks beside valid debt and repair-fact records,
malformed wait-registration attributes, stable dataclass JSON rendering, and
CLI parser construction. Tach, Ruff, strict Pyright, file and change budgets,
the broad local verifier, and hosted CI enforce the boundary.
