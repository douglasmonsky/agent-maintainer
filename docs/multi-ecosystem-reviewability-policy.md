<!-- docsync:object docs.multi_ecosystem_reviewability_policy.overview -->
# Multi-Ecosystem Reviewability Policy

Agent Maintainer is still Python-core. TypeScript/JavaScript is the active
experimental non-Python maturation track. Blocking reviewability gates remain
Python-backed until provider-aware policy adapters have fixture and real-repo
evidence.

## Current Blocking Gates

The following checks remain Python-backed:

| Check | Current implementation | Current blocking scope |
|---|---|---|
| `change-budget` | `agent_maintainer.checks.change_budget` | Python source/test paths under configured roots. |
| `file-length` | `agent_maintainer.checks.file_lengths` | Python files under configured file-length paths. |
| `structure-cohesion` | `agent_maintainer.checks.structure` | Folder-level Python cohesion hints. |
| `suppression-budget` | `agent_maintainer.checks.suppression_budget` | Python suppression markers such as `noqa`, `type: ignore`, `pylint: disable`, `pyright`, and `pragma: no cover`. |
| `source-without-test-change` | change-budget/test-intelligence helpers | Python source/test relevance. |

Experimental TypeScript/JavaScript providers may classify files and run
configured command checks, but those facts do not widen current blocking Python
reviewability gates.

## Advisory Assessment

`python -m agent_maintainer assess reviewability` is the current bridge between
Python-backed policy and future cross-ecosystem policy adapters. It reports:

- changed files classified by enabled providers;
- TypeScript/JavaScript source-heavy changes;
- TypeScript/JavaScript source files changed without provider test files;
- broad TypeScript/JavaScript suppression additions.

These summaries are evidence-gathering heuristics. They do not change exit
status, widen verifier gates, or create TypeScript/JavaScript blocking policy.

## File-Change Classification

Phase 95 added the internal `agent_maintainer.ecosystems.file_changes` seam. It
lets enabled built-in providers classify changed paths without changing current
verifier behavior.

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

The internal model intentionally stays small:

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

This model records evidence for future policy adapters. It is not a promise that
all roles already affect blocking gates.

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

Current advisory reports include ecosystem, suppression kind, broad/narrow
status, and reason. Broad advisory suppressions are one input to future policy
design, not immediate blocking failures.

## Beta Decision

Keep blocking reviewability policy Python-backed until provider-aware policy
adapters are characterized and tested. Do not aggregate TypeScript/JavaScript
source changes into the current blocking change-budget yet.

Cross-ecosystem aggregation should progress in order:

1. Advisory output with provider classifications and suppression facts.
2. Fixture-backed policy design for each ecosystem.
3. Configurable non-blocking thresholds.
4. Blocking policy only after real repositories prove low-noise behavior.

## File Length And Structure Cohesion

Keep file-length and structure-cohesion blocking behavior Python-only for now.
Future TypeScript/JavaScript support should start advisory because file shapes
vary across framework components, generated code, configuration files, and test
fixtures.

## Next Direction

The next provider work should mature TypeScript/JavaScript first, not add
another ecosystem.

Recommended sequence:

1. Keep Python as the core/reference provider and preserve its behavior.
2. Treat TypeScript/JavaScript as the first serious non-Python provider.
3. Use advisory evidence before introducing opt-in thresholds.
4. Add blocking policy only after real-repo output stays low-noise.
