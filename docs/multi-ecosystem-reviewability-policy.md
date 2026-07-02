# Multi-Ecosystem Reviewability Policy

Agent Maintainer is moving toward polyglot support, but reviewability policy is
not fully multi-ecosystem yet. In the current beta, reviewability checks are
globally scheduled and Python-backed.

That distinction matters:

- Python remains the core/reference provider with full reviewability policy.
- TypeScript/JavaScript and Go providers run explicitly configured commands.
- TypeScript/JavaScript and Go do not yet receive blocking change-budget,
  suppression-budget, file-length, structure-cohesion, or test-relevance policy
  gates from their classifiers.

## Current Behavior

The following checks are currently Python-backed:

| Check | Current implementation | Current scope |
|---|---|---|
| `change-budget` | `agent_maintainer.checks.change_budget` | Python source/test paths and configured roots. |
| `file-length` | `agent_maintainer.checks.file_lengths` | Python files under configured file-length paths. |
| `structure-cohesion` | `agent_maintainer.checks.structure` | Python files and folder-level Python cohesion hints. |
| `suppression-budget` | `agent_maintainer.checks.suppression_budget` | Python suppression markers such as `noqa`, `type: ignore`, `pylint: disable`, `pyright`, and `pragma: no cover`. |
| `source-without-test-change` | change-budget/test-intelligence helpers | Python source/test relevance. |

Experimental TypeScript/JavaScript and Go providers may classify files and emit
configured command checks, but those classifications are preparatory. They do
not currently widen the blocking Python reviewability checks.

## Beta Decision

Keep blocking reviewability policy Python-backed until provider-aware policy
adapters are characterized and tested.

Do not aggregate TypeScript/JavaScript or Go source changes into the current
blocking change-budget yet. Cross-ecosystem aggregation should start as
advisory output, then become configurable, then become a blocking policy only
after fixture repos prove low-noise behavior.

## Future File-Change Classification

Future policy adapters should consume a generic file-change model rather than
hard-coding one language's file patterns into every policy check.

Proposed internal shape, non-binding:

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

The policy engine should ask enabled providers to classify changed files, then
apply policy by capability:

- source spread and reviewability budgets;
- source/test relationship;
- suppression additions;
- file-size and folder-cohesion hints;
- generated and ignored-file exclusions.

Python output, thresholds, and messages must remain stable unless a separate
migration explicitly changes them.

## Suppression Policy Direction

Suppression classifiers must remain ecosystem-specific. Do not force every
language into Python suppression semantics.

Python suppression examples:

- `# noqa`
- `# type: ignore`
- `# pylint: disable=...`
- `# pyright: ignore`
- `# pragma: no cover`

TypeScript/JavaScript suppression examples to model later:

- `// eslint-disable`
- `// eslint-disable-next-line`
- `/* eslint-disable */`
- `// @ts-ignore`
- `// @ts-expect-error`
- `// @ts-nocheck`
- `/* istanbul ignore */`
- `// c8 ignore next`

Go suppression examples to model later:

- `//nolint`
- `//nolint:<linter>`
- build tags or generated markers only when policy can distinguish suppression
  from normal Go metadata.

The future suppression budget should report the ecosystem and exact suppression
kind, not just a generic count.

## File Length And Structure Cohesion

Keep file-length and structure-cohesion blocking behavior Python-only for now.

Future TypeScript/JavaScript support should start advisory because file shape
varies across framework components, generated code, configuration files, and
test fixtures. Future Go support should account for package directories,
generated protobuf files, and table-driven tests before applying blocking
thresholds.

## Next Implementation Step

The next code phase should introduce provider-aware file-change classification
behind characterization tests. It should not enable new blocking TypeScript or
Go policy gates by default.

Recommended sequence:

1. Add tests that pin current Python reviewability output.
2. Introduce a generic internal file-change classification model.
3. Have Python populate the model with current behavior unchanged.
4. Add advisory TypeScript/JavaScript and Go classification reports.
5. Only later consider configurable cross-ecosystem policy gates.

## Related Reading

- [Ecosystem Provider Status](provider-status.md)
- [Experimental TypeScript/JavaScript Provider](typescript-javascript-provider.md)
- [Experimental Go Provider](go-provider.md)
- [Polyglot Ecosystem Provider Roadmap](roadmap/polyglot-ecosystem-providers.md)
