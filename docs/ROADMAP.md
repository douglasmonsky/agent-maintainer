# Roadmap

Agent Maintainer is in beta. The current priority is validating package-first
onboarding across real Python repositories before promising long-term 1.0
stability.

## Beta Priorities

- Validate `init --track core` across common Python package layouts.
- Improve starter templates based on external repository feedback.
- Add concise examples for `fresh-strict` and `legacy-ratchet` adoption.
- Keep public configuration stable where possible and document breaking changes
  before 1.0.
- Clarify which checks belong in normal profiles versus release-only checks.
- Ensure the GitHub `pypi` environment requires manual approval before real PyPI
  publication.
- Add a CI matrix for advertised Python versions 3.11, 3.12, 3.13, and 3.14.

## Later

- Consider additional secret scanner backends.
- Consider richer monorepo support once package-first single-repo adoption is
  proven.
- Consider optional publish automation after the manual beta release process is
  reliable.
