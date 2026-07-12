# Domain-aware Archguard Map and Impact Design

**Date:** 2026-07-11

**Status:** Approved direction, written contract

## Problem

Archguard's map and impact commands read only root `tach.toml`. This repository
deliberately keeps most ownership and dependency policy in 28 nested
`tach.domain.toml` files. Consequently the commands report broad root ownership,
unassigned layers, unknown dependency direction, and weak test candidates while
`tach check --exact` enforces a much richer architecture.

## Goals

- Make `archguard map`, `impact`, and `explain-boundary` understand nested Tach
  domain ownership and explicit `depends_on` contracts.
- Preserve existing behavior for external repositories that use root modules
  and ordered layers.
- Resolve the nearest configured owner and produce useful affected-test hints.
- Keep these commands read-only explanations; Tach remains the enforcement
  engine.

## Non-goals

- Reimplementing Tach validation or import graph analysis.
- Changing any repository Tach policy merely to improve output.
- Guessing a boundary result when neither explicit dependencies nor layers
  provide one.

## Chosen architecture

`load_architecture` will parse root modules and merge valid domain payloads from
the existing `tach_config_domains` boundary. Domain discovery will also return
the path and bounded parse error for every discovered domain file that could
not be loaded; `ArchitectureMap` will retain those load errors. A `ModuleRule`
will carry:

- full module name;
- optional layer;
- `depends_on` as `None` when no explicit contract exists, or a tuple (including
  an empty tuple) when a contract is declared;
- the domain root that supplied the rule.

Domain-local dependencies such as `handlers` become
`agent_maintainer.wait.handlers`; absolute Tach dependencies such as
`//agent_waits.broker` become `agent_waits.broker`. The domain `[root]` table is
also represented when it declares ownership. Root-module parsing stays
backward-compatible.

Ownership continues to choose the longest matching module name, so a nested
domain rule supersedes a broad root package rule without removing either from
the map.

## Boundary explanation

For a proposed source-to-target dependency:

1. Any root or domain policy load error makes the result `unknown` because the
   architecture map is incomplete.
2. Unowned source or target is `unknown`.
3. Identical resolved owners are `same module`.
4. If the source declares `depends_on`, an exact configured target (or a target
   owned beneath a declared package dependency) is `allowed`; any other owned
   target is a `violation`.
5. If the source has no explicit dependency contract, ordered-layer behavior is
   used unchanged.
6. If neither mechanism applies, the result is `unknown` with the missing
   policy named.

`dependency_direction` renders the explicit allowlist when present, including
an explicit “no configured module dependencies” message for an empty list.

## Affected tests

Test candidates will use both the leaf module name and the domain root. For
example, `agent_maintainer.verify.quiet` prefers files under `tests/verify/` and
test stems containing `quiet`; `agent_maintainer.wait.broker` prefers
`tests/wait/` and stems containing `broker`. Results remain deterministic and
bounded, with an omitted-count suffix when more candidates exist.

## Error behavior

- Malformed root or domain TOML remains a blocking finding for the strict Tach
  config check. Read-only map commands render a bounded policy-load warning and
  return `unknown: architecture policy is incomplete` for dependency direction;
  they never fall back to a broad root or layer rule and report `allowed`.
- Malformed module entries are ignored defensively as root entries are today.
- Unknown ownership or policy is reported explicitly and never called allowed.

## Alternatives considered

- **Flatten all domain policy into root `tach.toml`.** Rejected because it would
  undo deliberate ownership locality and make the primary contract harder to
  maintain.
- **Shell out to Tach for a graph.** Rejected because the current supported
  Tach interface does not provide the exact stable explanatory payload needed,
  and Archguard already has a defensive TOML reader.
- **Keep map approximate and document the limitation.** Rejected because the
  documented product promise specifically includes ownership and dependency
  direction; misleading output is worse than explicit unknown output.

## Test strategy

- Preserve all existing layered-root fixture tests.
- Add nested domain fixtures for local and `//` dependency normalization,
  nearest-owner resolution, explicit empty dependencies, allowed edges,
  violations, unknown ownership, and malformed-domain fail-closed behavior.
- Add rendering assertions for domain ownership and bounded affected-test
  candidates.
- Dogfood all three commands against `verify.background_wait` and
  `wait.broker`, then run the Archguard suite, strict Tach checks, and broad
  verifier.

## Acceptance criteria

- The repository's nested verify and wait files resolve to their leaf Tach
  modules instead of broad `agent_maintainer` ownership.
- Explicit domain dependencies produce allowed or violation explanations rather
  than unassigned-layer unknowns.
- Existing root-layer repositories retain their previous output semantics.
- A malformed or incomplete config fails safely without a false allowed result.
