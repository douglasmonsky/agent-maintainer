# Roadmap

Agent Maintainer is in beta. The current priority is validating
package-first onboarding across real Python repositories before promising
long-term 1.0 stability.

## Beta Priorities

- Validate `init --track core` across common Python package layouts.
- Improve starter templates based on external repository feedback.
- Validate the `fresh-strict` and `legacy-ratchet` example projects against
  real repository feedback.
- Keep public configuration stable where possible and document breaking changes
  before 1.0.
- Clarify which checks belong in normal profiles versus release-only checks.
- Use the next beta release to prove the Python-version CI matrix, annotated
  tag workflow, PyPI environment approval, and GitHub release asset attachment.

## Later

- Consider additional secret scanner backends.
- Consider richer monorepo support once package-first single-repo adoption is
  proven.
- Consider optional publish automation after the manual beta release process is
  reliable.
