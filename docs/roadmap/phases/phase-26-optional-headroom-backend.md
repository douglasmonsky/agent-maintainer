# Phase 26: Optional Headroom Backend

## PR Title

```text
feat: add optional headroom context compression backend
```

## Dependency

Add:

```toml
compression = ["headroom-ai"]
```

Do not add it to:

```text
core
agent
hardening
manual
all
```

## Commands

```bash
python -m agent_maintainer context pack --compress headroom
python -m agent_maintainer context pack --compress headroom --require-compression
```

## Behavior

If missing:

```text
Headroom compression requested but not installed.

Install:
  python -m pip install "agent-maintainer[compression]"
```

If compression fails and not required:

```text
WARN: Headroom compression failed; using deterministic extractive context.
```

## Rules

Headroom only receives sanitized supporting context.

Headroom never receives:

```text
exact repair facts
structured manifests
ratchet fingerprints
change-plan scopes
raw unredacted logs
```

## Tests

Mock Headroom import and behavior. Do not require Headroom in normal tests.

## Acceptance Criteria

- Soft dependency works.
- Fallback works.
- Exact facts remain uncompressed.
- Precommit passes.

---
