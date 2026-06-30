# Phase 12: Diff Context Safety

## PR Title

```text
feat: add bounded diff context
```

## Files

Create:

```text
src/agent_maintainer/context/diff.py
```

## Commands

```bash
python -m agent_maintainer context diff --summary
python -m agent_maintainer context diff --name-only --limit 80
python -m agent_maintainer context diff --path src/foo.py
python -m agent_maintainer context diff --path src/foo.py --hunks 5
python -m agent_maintainer context diff --base-ref origin/main
python -m agent_maintainer context diff --staged
```

## Summary Must Include

```text
files changed
Python files
test files
docs files
generated/lock files
largest files by changed lines
rename/move candidates
import-only candidates
shown/omitted path counts
expansion commands
```

## Tests

Create:

```text
tests/context/test_diff.py
```

Use temp git repos.

## Acceptance Criteria

- Summary works.
- Bounded path list works.
- Path-specific diff works.
- Staged mode works.
- Precommit passes.

---
