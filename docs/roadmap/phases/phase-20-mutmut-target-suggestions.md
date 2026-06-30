# Phase 20: Mutmut Target Suggestions

## PR Title

```text
feat: suggest mutation testing targets
```

## Commands

```bash
python -m agent_maintainer test-intel mutation-targets
python -m agent_maintainer test-intel mutation-targets --changed
python -m agent_maintainer test-intel mutation-targets --ratchet
python -m agent_maintainer test-intel mutation-targets --format json
```

## Candidate Rules

Rank higher:

```text
changed source
covered by tests
critical ratchet target
high branch complexity
pure-ish function
parser/validator/decision logic
```

## Acceptance Criteria

- Advisory only.
- Does not run mutmut.
- JSON output works.
- Precommit passes.

---
