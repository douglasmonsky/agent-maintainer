# Phase 73: Release Polish, Debt Score Clarity, Mutation UX, and Cohesion

## PR Title

```text
feat: polish mutation results debt score and cohesion
```

## Scope

Improve release polish after Phase 67 public-docs assessment work and PR #139
Mutmut/Hypothesis hardening pass. This phase improves user trust and agent
usability without adding new scanners or changing public verification profile
semantics.

## Requirements

- Make roadmap phase first commit before behavior changes.
- Improve `test-intel mutation-results` so successful cleaned Mutmut runs remain
  readable from run-scoped manual artifacts.
- Keep `mutants/mutmut-cicd-stats.json` as the highest-priority stats source
  when present.
- Report stats source clearly: live `mutants/` artifact or
  `.verify-logs/runs/<run-id>/mutmut.log`.
- Preserve default cleanup of `mutants/`; do not keep generated mutation files
  only to support reporting.
- Refine Technical Debt Score output so low scores read as healthy watch items
  rather than urgent debt.
- Make debt category output clearer about observed debt versus configured
  tolerance where practical.
- Keep Technical Debt Score advisory-only and lower-is-better.
- Add focused tests for healthy current-repo-style debt output and missing or
  unreadable report fallback behavior.
- Add Hypothesis tests only for deterministic pure logic: change-plan path
  matching, scope validation, and safe context path rejection.
- Keep Hypothesis dev-only; do not add it to package extras.
- Start cohesion refactors only for recurring warning packages:
  `src/agent_maintainer/core` and `src/agent_maintainer/test_intel`.
- Do one cohesion target per PR unless the split is tiny.
- Add or update Tach domain files and ADRs for architecture policy changes.

## Acceptance Criteria

- `mutation-results` can summarize the latest successful manual Mutmut run after
  `mutants/` has been cleaned.
- Debt score text, Markdown, HTML, and PR-summary surfaces distinguish healthy
  watch items from failures.
- New Hypothesis tests cover at least one additional pure policy surface beyond
  assessment scoring.
- Cohesion warnings are reduced for one target package, or a concrete follow-up
  split plan is documented based on actual module clusters.
- No new scanner category, public profile, or default blocking gate is added.
- PRs remain small enough to review and preserve quiet verifier output.

## Progress

- [x] Added roadmap-first Phase 73 recovery checklist.
- [x] Taught `test-intel mutation-results` to read latest run-scoped Mutmut
  artifacts when `mutants/` cleanup removed live stats.
- [x] Clarified Technical Debt Score interpretation across text, JSON,
  Markdown, HTML, and PR-summary output.
- [x] Added Hypothesis property coverage for change-plan scope and safe context
  path refusal rules.
- [x] Split mutation test-intelligence modules into
  `agent_maintainer.test_intel.mutation` with explicit Tach modules and ADR.
- [x] Split otherwise reduce remaining `src/agent_maintainer/core`
  structure-cohesion warning in a follow-up PR.

## Verification

```bash
python3 -m agent_maintainer guidance --check
python3 -m agent_maintainer change-plan check
tach check --exact
python3 -m agent_maintainer verify --profile precommit
python3 -m agent_maintainer verify --profile full
python3 -m agent_maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main
python3 -m agent_maintainer verify --profile security
python3 -m agent_maintainer verify --profile manual
```

Run `just release-check` only if packaging, release checklist, or distribution
metadata changes.
