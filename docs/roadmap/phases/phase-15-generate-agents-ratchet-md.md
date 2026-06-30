# Phase 15: Generate `AGENTS.ratchet.md`

## PR Title

```text
feat: generate ratchet agent guidance
```

## Files

Create:

```text
src/agent_maintainer/ratchet/guidance.py
```

Update existing guidance command.

## Output File

```text
AGENTS.ratchet.md
```

## Content Must Include

```text
current mode
baseline path
top ratchet targets
context discipline
failure discipline
one-target-at-a-time rule
safe context commands
change-plan warning
```

## Main Guidance Integration

When ratchet is active, `AGENTS.agent-maintainer.md` must link:

```text
Read AGENTS.ratchet.md for legacy ratchet repair guidance.
```

## Commands

Use existing guidance command:

```bash
python -m agent_maintainer guidance
python -m agent_maintainer guidance --check
```

Do not create a separate guidance command.

## Tests

Create:

```text
tests/ratchet/test_guidance.py
```

## Acceptance Criteria

- Ratchet guidance deterministic.
- `guidance --check` detects stale ratchet guidance.
- Main guidance links ratchet guidance when active.
- Precommit passes.

---
