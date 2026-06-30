# Phase 3: Public Roadmap and Docs Stubs

## PR Title

```text
docs: plan context-safe legacy repair roadmap
```

## Goal

Restore the full layered roadmap in public docs.

## Files

Update:

```text
docs/ROADMAP.md
README.md
```

Create:

```text
docs/context-safety.md
docs/ratcheting.md
docs/cohesive-change-plans.md
docs/context-compression.md
docs/test-intelligence.md
```

## Roadmap Content

Add this section:

```markdown
## Next: Context-Safe Legacy Ratchets

Agent Maintainer's next focus is helping agents improve existing repositories
without drowning in failures, giant files, or huge diffs.

Planned work:

- Bounded failure summaries with explicit expansion commands.
- Test intelligence for changed source and relevant tests.
- Safe context commands for logs, failures, files, and diffs.
- Python file outlines for large legacy files.
- Context packs for agent repair loops.
- Ratchet baselines and ranked repair targets.
- Generated `AGENTS.ratchet.md` guidance.
- Cohesive change plans for intentional large migrations.
- Integration branch series support for large rewrites.
- Optional compression backends for sanitized supporting context.
- PR summaries and measured proof examples.
```

## Docs Stub Content

Each new doc must begin:

```markdown
# <Title>

This document tracks planned beta work. The implementation will land in small
phases. Public behavior must remain deterministic and bounded by default.
```

## README Update

Add links to:

```text
docs/context-safety.md
docs/test-intelligence.md
docs/ratcheting.md
docs/cohesive-change-plans.md
docs/context-compression.md
```

## Acceptance Criteria

- Roadmap includes all layers.
- New docs exist.
- README links the new docs.
- No behavior changes.
- Precommit passes.

---
