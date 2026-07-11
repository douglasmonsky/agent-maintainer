# 2026-07-11: Agent Repair-Fact Payload Boundary

## Status

Accepted.

## Context

The reusable `agent_repair_facts` package parses decoded output from Ruff,
Pyright, Bandit, coverage.py, DocSync, Jest, and Vitest. Runtime `dict` and
`list` checks did not establish string-keyed objects or explicitly typed array
elements, leaving every production module in the package with strict Pyright
debt. The TypeScript test parser had the same boundary problem but its Tach
contract allowed only its TypeScript diagnostic sibling.

## Decision

`agent_repair_facts.payloads` owns the package-local JSON object and array
normalizers alongside its existing scalar and location normalizers. Artifact
parsers may depend on that module, including
`agent_repair_facts.parsers.typescript_tests`. The TypeScript parser's new
dependency edge is recorded in `src/agent_repair_facts/tach.domain.toml`.

The pytest parser also models the narrow XML element interface returned by
the optional defusedxml parser. A runtime type guard verifies that interface
before JUnit data reaches repair-fact logic.

## Consequences

All decoded repair-fact inputs now cross an explicit runtime-validated
boundary before domain parsing. Pyright, IDEs, and future agents can follow
stable `dict[str, object]`, `list[object]`, and XML element contracts without
implicit unknown types. Malformed array entries remain fail-closed and cannot
obscure valid neighboring facts.

The package remains reusable and imports no `agent_maintainer` modules. The
declared TypeScript dependency matches the existing DocSync, lint, logs, and
pytest parser dependency direction.

## Alternatives Considered

- Keep casts in each parser. Rejected because they asserted nested shapes
  without one shared runtime contract.
- Duplicate the helpers in the TypeScript parser. Rejected because the helper
  is provider-neutral and already owned by the package payload boundary.
- Import the application-level structured-value helper. Rejected because the
  repair-fact package must remain independently reusable.
- Add suppressions or broad `Any`. Rejected because that would conceal the
  untrusted-data boundary rather than clarify it.

## Verification

Boundary tests cover mixed valid and malformed Ruff, Pyright, Bandit,
coverage.py, and DocSync entries. JUnit tests cover the safe XML parser path.
Tach, Bandit, Ruff, wemake, strict Pyright, manual verification, and the
CI-equivalent profile enforce the dependency and behavior.
