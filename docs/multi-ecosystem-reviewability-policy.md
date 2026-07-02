# Multi-Ecosystem Reviewability Policy

Agent Maintainer is moving toward polyglot support, but blocking
reviewability policy is not fully multi-ecosystem yet. In the current beta,
reviewability gates are globally scheduled and still Python-backed.

That distinction matters:

- Python remains the core/reference provider with full reviewability policy.
- TypeScript/JavaScript and Go providers run explicitly configured commands.
- TypeScript/JavaScript and Go now emit advisory changed-file and suppression
  facts through `assess reviewability`.
- TypeScript/JavaScript and Go do not yet receive blocking change-budget,
  suppression-budget, file-length, structure-cohesion, or test-relevance gates.

For the public maturity table, see [Provider Status](provider-status.md).

## Current Blocking Gates

The following checks remain Python-backed:

| Check | Current implementation | Current blocking scope |
|---|---|---|
| `change-budget` | `agent_maintainer.checks.change_budget` | Python source/test paths under configured roots. |
| `file-length` | `agent_maintainer.checks.file_lengths` | Python files under configured file-length paths. |
| `structure-cohesion` | `agent_maintainer.checks.structure` | Folder-level Python cohesion hints. |
| `suppression-budget` | `agent_maintainer.checks.suppression_budget` | Python suppression markers such as `noqa`, `type: ignore`, `pylint: disable`, `pyright`, and `pragma: no cover`. |
| `source-without-test-change` | change-budget/test-intelligence helpers | Python source/test relevance. |

Experimental TypeScript/JavaScript and Go providers may classify files and run
configured command checks, but those facts do not widen current blocking Python
reviewability gates.

## Advisory Assessment

`python -m agent_maintainer assess reviewability` is the current bridge between
the Python-backed policy and future cross-ecosystem policy adapters.

It reports:

- changed files grouped by ecosystem;
- changed files grouped by role, such as source, test, config, docs, generated,
  dependency, and ignored;
- unclassified changed files;
- advisory TypeScript/JavaScript and Go suppression findings;
- broad advisory suppression counts;
- next commands for the existing blocking verification loop.

Advisory change collection uses a neutral git numstat reader, not Python
`change-budget` filters. This keeps TypeScript/JavaScript lockfiles, Go
dependency files, generated files, config files, and other non-Python
provider-owned changes visible to advisory reports. Blocking `change-budget`
keeps its Python-specific exclusions and behavior.

The command is advisory-only. It exits successfully when it can produce the
report, even when it finds TypeScript/JavaScript or Go suppressions.

## File-Change Classification

Phase 95 added the internal `agent_maintainer.ecosystems.file_changes` seam.
It lets enabled built-in providers classify changed paths without changing
current verifier behavior.

Current role model:

| Role | Meaning |
|---|---|
| `source` | Runtime source code for an ecosystem. |
| `test` | Test files for an ecosystem. |
| `generated` | Generated code or generated artifacts. |
| `config` | Tooling, package, or project configuration. |
| `dependency` | Dependency lock or manifest files. |
| `docs` | Documentation files. |
| `ignored` | Paths excluded from provider policy, such as build artifacts. |
| `unknown` | Not classified by an enabled provider. |

The internal model is intentionally small:

```python
@dataclass(frozen=True)
class FileChangeClassification:
    path: str
    ecosystem: str
    role: FileRole
    change_kind: ChangeKind
    generated: bool = False
    ignored: bool = False
    reason: str = ""
```

The model is evidence for future policy adapters. It is not a promise that all
roles are already blocking gates.

## Suppression Classification

Suppression classifiers remain ecosystem-specific. Agent Maintainer should not
force every language into Python suppression semantics.

Python blocking suppression examples:

- `# noqa`
- `# type: ignore`
- `# pylint: disable=...`
- `# pyright: ignore`
- `# pragma: no cover`

TypeScript/JavaScript advisory suppression examples:

- `// eslint-disable`
- `// eslint-disable-next-line`
- `/* eslint-disable */`
- `// @ts-ignore`
- `// @ts-expect-error`
- `// @ts-nocheck`
- `/* istanbul ignore */`
- `// c8 ignore next`

Go advisory suppression examples:

- `//nolint`
- `//nolint:<linter>`

Current advisory reports include the ecosystem, suppression kind, broad/narrow
status, and reason. Broad advisory suppressions should become one input to
future policy design, not an immediate blocking failure.

## Beta Decision

Keep blocking reviewability policy Python-backed until provider-aware policy
adapters are characterized and tested. Do not aggregate TypeScript/JavaScript
or Go source changes into current blocking change-budget yet.

Cross-ecosystem aggregation should progress in this order:

1. Advisory output with provider classifications and suppression facts.
2. Fixture-backed policy design for each ecosystem.
3. Configurable non-blocking thresholds.
4. Blocking policy only after real repositories prove low-noise behavior.

## File Length And Structure Cohesion

Keep file-length and structure-cohesion blocking behavior Python-only for now.

Future TypeScript/JavaScript support should start advisory because file shapes
vary across framework components, generated code, configuration files, and test
fixtures.

Future Go support should account for package directories, generated protobuf
files, and table-driven tests before applying blocking thresholds.

## Next Direction

The next reviewability-policy work should design and test provider-aware policy
adapters, not add another ecosystem provider.

Recommended sequence:

1. Add fixture repositories for TypeScript/JavaScript and Go reviewability
   policy scenarios.
2. Add advisory source-spread and source/test relationship summaries per
   ecosystem.
3. Add configurable per-provider thresholds that default to advisory.
4. Compare advisory output against real repositories before enabling blocking
   behavior.
5. Preserve Python check names, messages, thresholds, and profile behavior
   unless a separate migration explicitly changes them.
