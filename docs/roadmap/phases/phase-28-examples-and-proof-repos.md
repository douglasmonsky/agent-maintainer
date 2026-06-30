# Phase 28: Examples and Proof Repos

## PR Title

```text
docs: add context-safe ratchet proof examples
```

## Add Examples

```text
examples/context-safe-ratchet/
examples/cohesive-change-plan/
examples/test-intelligence/
```

## Each Example Includes

```text
README.md
pyproject.toml
small source fixture
test fixture
expected commands
expected outputs
intentional failure
repair path
```

## Commands Shown

```bash
agent-maintainer ratchet baseline create
agent-maintainer ratchet status
agent-maintainer ratchet next
agent-maintainer test-intel changed
agent-maintainer context file src/legacy/big.py --outline
agent-maintainer context failures
agent-maintainer verify --profile precommit
```

## Acceptance Criteria

- Examples are lightweight.
- Examples run locally.
- Docs explain agent repair flow.
- Precommit passes.

---
