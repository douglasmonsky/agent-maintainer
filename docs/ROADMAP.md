# Roadmap

Agent Maintainer is in beta. The current priority is validating package-first
onboarding across real Python repositories before promising long-term 1.0
stability.

## Beta Priorities

- Validate `init --track core` across common Python package layouts.
- Improve starter templates based on external repository feedback.
- Validate `fresh-strict` and `legacy-ratchet` example projects with real
  repository feedback.
- Keep public configuration stable where possible, and document breaking
  changes before 1.0.
- Clarify which checks belong in normal profiles versus release-only checks.
- Use the next beta release to prove Python-version CI matrix, annotated tag
  workflow, PyPI environment approval, and GitHub release asset attachment.

## Completed: Cohesive-Change Override

The change-budget system keeps small PRs as the default. It now has a strict
exception path for rare cohesive migrations where splitting further would create
temporary dead code, fake boundaries, or incoherent intermediate states.

- [x] Add explicit config for cohesive-change override eligibility, a narrow
  allowlist of affected paths, and maximum override size.
- [x] Require an override explanation field in the pull request body before CI
  accepts a budget override.
- [x] Require the explanation to identify why the change is one cohesive unit,
  why smaller splits would make the repository less coherent, which tests cover
  the migration, and that behavior remains unchanged.
- [x] Add verifier support that detects the PR explanation field through GitHub
  context in CI and refuses casual empty override text.
- [x] Emit a clear local warning when an override is requested but cannot be
  fully verified outside GitHub CI.
- [x] Add tests for valid override metadata, missing explanation, over-broad path
  scope, excessive line count, and normal change-budget behavior without an
  override.
- [x] Add a PR template section for the override explanation so reviewers see
  justification without hunting through logs.
- [x] Document that overrides are for cohesive infrastructure migrations only,
  not mixed feature/refactor/docs/dependency bundles.

## Later

- Consider additional secret scanner backends.
- Consider richer monorepo support once package-first single-repo adoption is
  proven.
- Consider optional publish automation once the manual beta release process is
  reliable.
