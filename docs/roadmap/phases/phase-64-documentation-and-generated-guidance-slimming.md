# Phase 64: Documentation and Generated Guidance Slimming

## PR Title

```text
docs: slim generated agent guidance
```

## Scope

Keep `AGENTS.agent-maintainer.md` compact and action-only while moving detailed
tool explanations, diagnostics policy, mutation-testing strategy, optional gate
inventory, and architecture policy into human-readable docs.

## File Targets

```text
README.md
AGENTS.agent-maintainer.md
src/agent_maintainer/core/guidance.py
tests/core/test_guidance.py
tests/docs/test_public_docs.py
docs/agent-maintainer-guidance.md
docs/quick-start.md
docs/diagnostics-repair-loop.md
docs/mutation-testing.md
docs/optional-gates.md
docs/architecture-policy.md
docs/ROADMAP.md
docs/roadmap/full-roadmap-blueprint.md
```

## Requirements

- Generated agent guidance lists active gates only.
- Generated agent guidance omits disabled optional gate inventory.
- Generated agent guidance omits scanner and tool argument dumps.
- Generated agent guidance keeps exact commands and critical thresholds.
- Human docs explain optional gates, diagnostics, mutation testing, hook safety,
  architecture policy, and quick-start onboarding.
- README uses the social preview graphic near the top.
- README places relevant read-more links next to sections, not only at the end.
- README remains package-first and public-facing.

## Acceptance Criteria

- Focused tests cover compact generated guidance and public README links.
- `python -m agent_maintainer guidance` regenerates a compact sidecar.
- `python -m agent_maintainer guidance --check` passes.
- `python -m agent_maintainer change-plan check` passes.
- `tach check --exact` passes.
- Precommit, full, ci, security, manual profiles pass before PR merge.
