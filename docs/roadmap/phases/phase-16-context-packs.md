# Phase 16: Context Packs

## PR Title

```text
feat: generate bounded context packs
```

## Files

Create:

```text
src/agent_maintainer/context/packs.py
```

## Commands

```bash
python -m agent_maintainer context pack
python -m agent_maintainer context pack --budget 16000
python -m agent_maintainer context pack --check pytest-coverage
python -m agent_maintainer context pack --file src/legacy/big.py
python -m agent_maintainer context pack --format json
```

## Outputs

```text
.verify-logs/context/PACK.md
.verify-logs/context/PACK.json
```

## Sections

```text
exact repair facts
supporting context
untrusted content labels
ratchet state
top targets
selected file outlines
selected logs
omitted counts
expansion commands
```

## Tests

Create:

```text
tests/context/test_packs.py
```

## Acceptance Criteria

- Pack bounded.
- Pack JSON exists.
- Exact facts separate from supporting context.
- Omitted counts present.
- Expansion commands present.
- Precommit passes.

---
