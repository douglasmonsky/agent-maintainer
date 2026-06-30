# Phase 67: Public Docs, Setup Advisor, and Technical Debt Score

## PR Title

```text
docs: sharpen public onboarding and score roadmap
```

## Scope

Make the public documentation easier to trust, easier to try, and easier for an
AI agent to use correctly. Keep the first PR docs-first, then implement setup
recommendations and the Technical Debt Score as focused follow-up PRs.

## Requirements

- Rewrite the README around a package-first first-run story:
  - what Agent Maintainer does;
  - why users should trust it;
  - the fastest successful trial path;
  - fresh-repo strict trial path;
  - agent-assisted adoption path;
  - supported checks/scanners;
  - ratcheting and mutation testing;
  - diagnostics and repair loop;
  - links to deeper docs placed next to relevant sections, not only at bottom.
- Keep the top social-preview graphic and consider additional graphics in the
  same style for:
  - run profiles;
  - ratcheting;
  - setup advisor;
  - Technical Debt Score.
- Add or improve docs that explain:
  - all supported scan categories;
  - which checks are default, optional, manual, security, or release-oriented;
  - how agents should use generated guidance, hooks, `.verify-logs`, context
    expansion commands, ratchet targets, and repair plans;
  - how to dogfood strict mode on a fresh repo safely.
- Add a setup-recommendation feature plan:
  - automated repository inspection for layout, tests, package metadata, CI,
    lock files, architecture files, agents/hooks, and scanner-relevant assets;
  - generated recommendations for `--track`, `--preset`, enabled optional gates,
    and follow-up questions for an AI agent to answer from repo context;
  - output as text and JSON for both humans and agents.
- Add a Technical Debt Score feature plan:
  - transparent composite score, not opaque grade;
  - category sub-scores for reviewability, tests/coverage, type/style,
    architecture, dependencies/security, docs/config hygiene, diagnostics, and
    ratchet/mutation maturity;
  - confidence level based on which evidence exists;
  - explicit “why this score changed” deltas;
  - advisory by default, never a hidden pass/fail gate.

## Acceptance Criteria

- README has a clear public-beta first impression and no compressed wall-of-text
  command blocks.
- README includes every supported check/scanner category with links to deeper
  docs beside the relevant section.
- README explicitly encourages a fresh strict trial repo and explains why that is
  the easiest way to feel the product value quickly.
- `docs/tool-map.md` remains the exhaustive reference while README stays
  outcome-first.
- Roadmap clearly separates docs polish, setup advisor, and Technical Debt Score
  implementation into follow-up PRs.
- No verifier behavior or scanner policy changes are made in the docs-only PR.

## Follow-up Implementation Phases

- Phase 68: README and docs information architecture rewrite.
- Phase 69: Supported scan matrix and agent-utilization guide.
- Phase 70: Setup advisor command and JSON output.
- Phase 71: Technical Debt Score v0 scorecard and report integration.
- Phase 72: Additional graphics for run profiles, ratchets, and scorecard.

## Verification

```bash
python3 -m agent_maintainer guidance --check
python3 -m agent_maintainer change-plan check
python3 -m agent_maintainer verify --profile precommit
python3 -m agent_maintainer verify --profile full
python3 -m agent_maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main
```
