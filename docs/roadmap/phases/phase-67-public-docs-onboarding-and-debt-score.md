# Phase 67: Public Docs, Setup Advisor, and Technical Debt Score

## PR Title

```text
docs: sharpen public onboarding and score roadmap
```

## Scope

Make public documentation easier to trust, easier to try, and easier for coding
agents to use correctly. Keep the README outcome-first while moving detailed
reference material into linked docs.

## Requirements

- Rewrite the README around the package-first first-run story:
  - what Agent Maintainer does;
  - why users should trust it;
  - fastest successful trial path;
  - fresh-repo strict trial path;
  - agent-assisted adoption path;
  - supported checks/scanners;
  - ratcheting and mutation testing;
  - diagnostics repair loop;
  - links to deeper docs beside relevant sections, not only at the bottom.
- Keep the top social-preview graphic and static run-profile graphic.
- Add or improve docs explaining:
  - all supported scan categories;
  - which checks are default, optional, manual, security, or release-oriented;
  - how agents should use generated guidance, hooks, `.verify-logs`, context
    expansion commands, ratchet targets, and repair plans;
  - how to dogfood strict mode on a fresh repo safely.
- Implement setup recommendations:
  - inspect layout, tests, package metadata, CI, lock files, architecture files,
    agents/hooks, and scanner-relevant assets;
  - recommend `--track`, `--preset`, optional gates, and follow-up questions a
    coding agent should answer from repo context;
  - emit text and JSON for humans and agents.
- Implement a Technical Debt Score:
  - transparent composite score, not an opaque grade;
  - category sub-scores for reviewability, tests/coverage, type/style,
    architecture, dependencies/security, docs/config hygiene, diagnostics, and
    ratchet/mutation maturity;
  - confidence level based on available evidence;
  - advisory default, never a hidden pass/fail gate.

## Acceptance Criteria

- README has a clear public-beta first impression and no compressed wall of
  commands.
- README includes every supported check/scanner category and links deeper docs
  beside relevant sections.
- README explicitly encourages a fresh strict trial repo as the easiest way to
  feel product value quickly.
- `docs/tool-map.md` remains the exhaustive reference while README stays
  outcome-first.
- Roadmap separates docs polish, setup advisor, and Technical Debt Score work.
- No raw generated report logs are committed.

## Completed Implementation Phases

- Phase 68: README docs information architecture rewrite.
- Phase 69: Supported scan matrix and agent-utilization guide.
- Phase 70: Setup advisor command and JSON output.
- Phase 71: Technical Debt Score v0 scorecard and report integration.
- Phase 72: Static graphics strategy cleanup; the repo keeps committed PNGs and
  removes the old HTML render pipeline.

## Verification

```bash
python3 -m agent_maintainer guidance --check
python3 -m agent_maintainer change-plan check
python3 -m agent_maintainer verify --profile precommit
python3 -m agent_maintainer verify --profile full
python3 -m agent_maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main
```
