# Contributing To Agent Maintainer

Thank you for improving Agent Maintainer. The project favors small, test-backed
changes that preserve local-first operation, bounded diagnostics, and safe
behavior in existing repositories.

By participating, follow the [Code of Conduct](CODE_OF_CONDUCT.md). Report
vulnerabilities privately through [SECURITY.md](SECURITY.md), and use
[SUPPORT.md](SUPPORT.md) for usage questions.

## Before You Start

Search existing issues and the [critical stabilization roadmap](docs/roadmap/critical-stabilization.md).
Open an issue before a large feature, public API, provider, schema, or workflow
change so scope and acceptance criteria can be agreed first. Small bug fixes,
tests, and documentation corrections can go directly to a pull request.

Do not include real credentials, private repositories, production data, or
student/customer records. Use synthetic fixtures and redacted diagnostics.

## Development Setup

Use Python 3.11 through 3.14. Node.js 22 or newer is required for the optional
Markdown and TOML repository gates.

```bash
git clone https://github.com/douglasmonsky/agent-maintainer.git
cd agent-maintainer
just bootstrap
npm ci
just doctor
```

`just bootstrap` installs development dependencies without mutating Git hooks.
Run `.venv/bin/python -m agent_maintainer install --dry-run` before explicitly
installing managed hooks.

## Make A Focused Change

- Add or update tests for behavior changes.
- Preserve existing applications and fail closed on unsafe or ambiguous input.
- Keep private data and raw logs local; return bounded summaries.
- Update `CHANGELOG.md` for user-facing changes.
- Update setup, command, contract, or privacy documentation in the same change.
- Follow the repository's architecture and generated-file guidance in
  `AGENTS.md`.
- Use Conventional Commit prefixes such as `fix:`, `feat:`, `docs:`, `test:`,
  `refactor:`, or `chore:`.

Do not broaden a pull request with unrelated refactors. A little duplication is
preferable to speculative infrastructure.

## Verify The Change

Start with the narrowest meaningful test, then expand in proportion to risk.

```bash
.venv/bin/python -m pytest path/to/relevant_test.py -q
just vp
```

Before a larger pull request, run `just v`. Use `just vc` when CI, workflow, or
diff/profile behavior changes. Run security or manual profiles when the changed
surface requires them. Release changes also require `just release-check`.

Do not lower thresholds, remove checks, or add broad suppressions to make a
change pass. If a check is wrong, fix the smallest underlying rule and explain
the decision.

## Pull Requests

Complete the pull request template with:

- the problem and user/developer impact;
- the focused verification commands and outcomes;
- skipped checks with reasons;
- documentation, changelog, compatibility, security, and privacy effects;
- any rollout, rollback, or follow-up requirement.

The maintainer may ask for a smaller diff, a synthetic reproduction, stronger
failure-mode tests, or updated docs before merging. Release and security changes
require especially clear evidence. Contributions are made under the repository's
[MIT License](LICENSE); submit only work you have the right to contribute.
