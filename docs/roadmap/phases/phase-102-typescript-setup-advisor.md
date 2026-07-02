# Phase 102: TypeScript Setup Advisor Recommendations

## Status

Planned.

## Goal

Help adopters configure the experimental TypeScript/JavaScript provider when
their repository already exposes TypeScript-like package scripts, without adding
package-manager autodetection or turning TypeScript advisory signals into
blocking gates.

## Scope

- Detect package script evidence such as `lint`, `typecheck`, and `test` in
  `package.json` during setup assessment.
- Recommend explicit TypeScript provider configuration only when the evidence is
  present.
- Keep the recommendation advisory and package-manager-neutral.
- Keep Go canary-only and unchanged.
- Update setup-advisor docs to explain the recommendation and its limits.

## Non-Goals

- No package-manager autodetection.
- No generated TypeScript starter files.
- No TypeScript blocking gates.
- No Go depth expansion.
- No new ecosystem provider.
- No changes to Python setup recommendations.

## Acceptance Criteria

- `python -m agent_maintainer assess setup` can recommend the TypeScript
  provider when `package.json` scripts contain relevant lint/typecheck/test
  commands.
- The recommendation tells users to map their existing scripts into explicit
  `typescript_*_command` fields.
- Repositories without package script evidence do not receive a TypeScript
  provider recommendation.
- Existing OSV recommendations for non-Python ecosystem files still work.
- Docs say the advisor does not infer package managers or invent commands.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/assess/test_setup_advisor.py tests/assess/test_evidence.py -q`
- `npx --no-install markdownlint-cli2 docs/setup-advisor.md docs/roadmap/phases/phase-102-typescript-setup-advisor.md`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit`

## Notes For Future Codex Tasks

Do not guess npm, pnpm, yarn, or bun commands from file names. The advisor may
point at existing scripts, but the repository owner should keep command arrays
explicit in `[tool.agent_maintainer]`.
