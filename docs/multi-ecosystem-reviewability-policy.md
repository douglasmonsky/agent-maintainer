<!-- docsync:object docs.multi_ecosystem_reviewability_policy.overview -->
# Multi-Ecosystem Reviewability Policy

Agent Maintainer is still Python-core. TypeScript/JavaScript is the active
experimental non-Python maturation track. Blocking reviewability gates remain
Python-backed until provider-aware policy adapters have fixture and real-repo
evidence that they are low noise.

## Current Blocking Gates

These checks remain Python-backed:

| Check | Current Implementation | Current Blocking Scope |
|---|---|---|
| `change-budget` | `agent_maintainer.checks.change_budget` | Python source/test paths under configured roots. |
| `file-length` | `agent_maintainer.checks.file_lengths` | Python files under configured file-length paths. |
| `structure-cohesion` | `agent_maintainer.checks.structure` | Python files under configured structure paths. |
| `suppression-budget` | `agent_maintainer.checks.suppression_budget` | Python suppression patterns. |
| `source-without-test-change` / test relevance | Python source/test roots. | Python source/test paths. |

These checks are scheduled globally by the verifier, but their policy
implementation is still Python-focused.

## Advisory Provider Signals

`python -m agent_maintainer assess reviewability` reports provider-aware
advisory facts for enabled ecosystems. The command currently reports:

- changed-file counts by ecosystem and role;
- TypeScript/JavaScript source and test file counts;
- TypeScript/JavaScript source-heavy and source-without-test advisory findings;
- broad TypeScript/JavaScript suppression additions.

These summaries are evidence-gathering heuristics. They do not change exit
status, widen verifier gates, or create TypeScript/JavaScript blocking policy.

TypeScript/JavaScript advisory thresholds are configurable through:

```toml
[tool.agent_maintainer]
typescript_advisory_source_warn_files = 4
typescript_advisory_source_warn_lines = 200
typescript_advisory_broad_suppression_warn = 1
```

These values only affect `assess reviewability` findings. They are not
precommit, CI, or merge gates.

## File-Change Classification

The internal `agent_maintainer.ecosystems.file_changes` seam lets enabled
built-in providers classify changed paths without changing current verifier
behavior.

| Role | Meaning |
|---|---|
| `source` | Runtime source code for the ecosystem. |
| `test` | Test files for the ecosystem. |
| `generated` | Generated code or generated artifacts. |
| `config` | Tooling, package, or project configuration. |
| `dependency` | Dependency lock or manifest files. |
| `docs` | Documentation files. |
| `ignored` | Paths excluded from provider policy, such as build artifacts. |
| `unknown` | Not classified by an enabled provider. |

This model records evidence for future policy adapters. It does not promise
that all roles already affect blocking gates.

`python -m agent_maintainer assess file-baselines` reports provider-neutral
file group facts from explicit include/exclude globs. It covers simple facts
such as matched files, changed files, changed lines, physical lines, and
nonblank lines across docs, config, tests, TSX, YAML, TOML, or other configured
groups. It does not perform import graph or language architecture analysis.

## Suppression Classification

Suppression classifiers remain ecosystem-specific. Agent Maintainer does not
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

Current advisory reports include ecosystem, suppression kind, broad/narrow
status, and reason. Broad advisory suppressions are one input for future policy
design, not immediate blocking failures.

## Beta Decision

Keep blocking reviewability policy Python-backed until provider-aware policy
adapters are characterized and tested.

Do not aggregate TypeScript/JavaScript source changes into the current blocking
change-budget yet. Cross-ecosystem aggregation should progress in this order:

1. Advisory output with provider classifications and suppression facts.
2. Fixture-backed policy design for each ecosystem.
3. Configurable non-blocking thresholds.
4. Blocking policy only after real repositories prove low-noise behavior.

## File Length And Structure Cohesion

Keep file-length and structure-cohesion blocking behavior Python-only for now.
Future TypeScript/JavaScript or another ecosystem should move through
provider-neutral file-baseline evidence first, then provider-specific policy
adapters when language semantics matter.

## Next Direction

The next provider work should mature TypeScript/JavaScript first, not add
another ecosystem.

Recommended sequence:

1. Keep Python as the core/reference provider and preserve its behavior.
2. Treat TypeScript/JavaScript as the first serious non-Python provider.
3. Use advisory evidence before introducing opt-in thresholds.
4. Add blocking policy only after real-repo output stays low-noise.
