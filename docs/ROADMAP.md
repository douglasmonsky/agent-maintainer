# Roadmap

Agent Maintainer is in beta. The current priority is validating package-first
onboarding across real Python repositories before promising long-term 1.0
stability.

## Beta Priorities

- Validate `init --track core` across common Python package layouts.
- Improve starter templates based on external repository feedback.
- Validate `fresh-strict` and `legacy-ratchet` example projects against real
  repository feedback.
- Add a systematic cohesive-change override for rare large but single-purpose
  infrastructure migrations.
- Keep public configuration stable where possible, and document breaking changes
  before 1.0.
- Clarify which checks belong in normal profiles versus release-only checks.
- Use the next beta release to prove the Python-version CI matrix, annotated tag
  workflow, PyPI environment approval, and GitHub release asset attachment.

## Planned: Cohesive-Change Override

The change-budget system should keep small PRs as the default. It also needs a
strict exception path for rare cohesive migrations where splitting further would
create temporary dead code, fake boundaries, or incoherent intermediate states.

- [ ] Add explicit config for cohesive-change override eligibility, with a
  narrow allowlist of affected paths and maximum override size.
- [ ] Require an override explanation field in the pull request body before CI
  accepts a budget override.
- [ ] Require the explanation to identify why the change is one cohesive unit,
  why smaller splits would make the repository less coherent, what tests cover
  the migration, and what behavior must remain unchanged.
- [ ] Add verifier support that detects the PR explanation field through GitHub
  context in CI and refuses casual or empty override text.
- [ ] Emit a clear local warning when an override is requested but cannot be
  fully verified outside GitHub CI.
- [ ] Add tests for valid override metadata, missing explanation, over-broad
  path scope, excessive line count, and normal change-budget behavior without
  an override.
- [ ] Add a PR template section for the override explanation so reviewers see
  the justification without hunting through logs.
- [ ] Document that overrides are for cohesive infrastructure migrations only,
  not mixed feature/refactor/docs/dependency bundles.

## Later

- Consider additional secret scanner backends.
- Consider richer monorepo support once package-first single-repo adoption is
  proven.
- Consider optional publish automation once the manual beta release process is
  reliable.
