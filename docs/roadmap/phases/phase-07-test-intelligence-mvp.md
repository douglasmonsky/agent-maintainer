# Phase 7: Test Intelligence MVP

## PR Title

```text
feat: add changed-code test intelligence
```

## Goal

Give agents deterministic guidance about which tests matter for changed source.

## Files

Create:

```text
src/agent_maintainer/test_intel/__init__.py
src/agent_maintainer/test_intel/cli.py
src/agent_maintainer/test_intel/models.py
src/agent_maintainer/test_intel/changed.py
src/agent_maintainer/test_intel/mapping.py
src/agent_maintainer/test_intel/coverage.py
src/agent_maintainer/test_intel/reporting.py
```

Update CLI dispatch to support:

```bash
python -m agent_maintainer test-intel ...
agent-maintainer test-intel ...
```

## Command

Implement:

```bash
python -m agent_maintainer test-intel changed
python -m agent_maintainer test-intel changed --base-ref origin/main
python -m agent_maintainer test-intel changed --staged
python -m agent_maintainer test-intel changed --format json
```

## Inputs

Use:

```text
git changed paths
configured source_roots
configured test_roots
coverage.json if present
coverage.xml if present
pytest-junit.xml if present
AST import scanning
path naming conventions
```

## Confidence Rules

High confidence:

```text
test file naming match + imports changed module
coverage data shows test covers changed file
```

Medium confidence:

```text
test file naming match
test imports changed module
same package/domain naming
```

Low confidence:

```text
same test tree/domain only
```

## Text Output

```text
Test intelligence for changed source

Changed source:
  src/agent_maintainer/checks/change_budget.py

Likely test files:
1. tests/checks/test_change_budget.py
   confidence: high
   reasons:
     - naming match
     - imports changed module
     - covers changed lines

2. tests/catalogs/test_config_catalog.py
   confidence: medium
   reasons:
     - catalog command wiring references this behavior

Coverage:
  changed-line coverage: 92%
  branch coverage gaps: 3

Suggested next actions:
1. Add or update tests in tests/checks/test_change_budget.py.
2. Cover branch: source changed without test change but allow flag is set.
3. Run:
   python -m pytest tests/checks/test_change_budget.py -q
```

## JSON Output

Return stable structured output:

```json
{
  "changed_source": [],
  "likely_tests": [],
  "coverage": {},
  "suggested_actions": []
}
```

## Tests

Create:

```text
tests/test_intel/test_changed.py
tests/test_intel/test_mapping.py
tests/test_intel/test_reporting.py
```

Use temp repos and small fixtures.

## Acceptance Criteria

- `test-intel changed` works.
- JSON output works.
- Likely tests are ranked.
- Suggested pytest commands are emitted.
- Precommit passes.

---
