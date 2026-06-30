# Phase 11: Safe Large-File Reading

## PR Title

```text
feat: add safe file context outlines
```

## Files

Create:

```text
src/agent_maintainer/context/files.py
src/agent_maintainer/context/python_outline.py
src/agent_maintainer/context/file_safety.py
```

## Commands

```bash
python -m agent_maintainer context file <path> --outline
python -m agent_maintainer context file <path> --symbols
python -m agent_maintainer context file <path> --symbol Class.method
python -m agent_maintainer context file <path> --lines 400:520
python -m agent_maintainer context file <path> --around 887 --context 40
python -m agent_maintainer context file <path> --format json
```

## AST Outline

Extract:

```text
imports
module globals
classes
methods
functions
decorators
line ranges
docstring first line
line counts
```

## Fallback Outline

For syntax-broken Python:

```text
top-level def/class regex
indentation chunks
blank-line chunks
line-count chunks
```

## Safety

Refuse or summarize:

```text
binary files
non-UTF-8 files
huge JSON
minified files
lock files
generated files
.venv
node_modules
symlinks
notebooks
```

## Tests

Create:

```text
tests/context/test_file_outline.py
tests/context/test_file_safety.py
```

## Acceptance Criteria

- Large files never dump by default.
- Symbol extraction works.
- Around/lines extraction works.
- Syntax-broken fallback works.
- JSON output works.
- Precommit passes.

---
