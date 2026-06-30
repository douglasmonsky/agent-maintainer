# Phase 40: Exact Repair Facts From Structured Artifacts

## PR Title

```text
feat: extract exact repair facts from verifier artifacts
```

## Goal

Improve context packs from "check failed" summaries toward exact, bounded repair
facts. Agents should see the first actionable file/line/symbol/threshold facts
before expanding logs.

## Requirements

- Add structured fact extractors for artifacts already produced by the verifier,
  starting with high-value local artifacts such as Ruff JSON, Pyright JSON,
  Bandit JSON, coverage JSON/XML, file-length output, structure output, and
  change-budget output where available.
- Keep facts bounded and sorted by severity/check priority.
- Preserve expansion commands for full logs.
- Add tests for at least three artifact families with path/line/message facts.

## Out Of Scope

- Do not print whole logs or source files into context packs.
- Do not require all tools to emit structured artifacts before this phase can
  land.

## Acceptance Criteria

- Context packs include concrete file/line facts for supported structured
  artifacts.
- Existing context safety tests still prove bounded output.
- Precommit and focused context tests pass.

---
