---
name: symphony-github-work
description: Complete a GitHub issue dispatched by Symphony in Agent Maintainer. Use for unattended issues carrying `agent-ready` that require scoped implementation, verification, a clean commit, a pushed branch, a pull request, and lifecycle-label handoff through Symphony's injected `github_api` tool.
---

# Complete Symphony GitHub Work

Treat the issue as the authorization and scope contract. If objective, scope,
acceptance criteria, verification, dependencies, or resolved human decisions
are materially missing, block before editing.

## Execute

1. Read the issue, applicable `AGENTS.md` files, and relevant architecture docs.
2. Add `agent-running` while retaining `agent-ready`.
3. Find or create one issue comment headed `## Symphony Workpad`. Keep the plan,
   acceptance checklist, current action, verification, and blockers there.
4. Fetch `origin/main` and create or reuse `codex/symphony-gh-<issue-number>`.
5. Reproduce or inspect first, implement only the issue scope, and add tests for
   behavior changes.
6. Run focused checks during development and `scripts/verify` at the coherent
   final state.
7. Review status and diffs for scope, generated files, secrets, and private data.
8. Commit with a focused Conventional Commit message and push the branch.
9. Use `github_api` to open or update a pull request against `main`. Follow
   `.github/pull_request_template.md` and record exact verification evidence.

Use `github_api` for repository-scoped issue comments, labels, and pull-request
operations. Do not expose its host-side credential or copy it into the
workspace. Use normal `git` commands for branch and push operations.

## Hand Off

Make tracker mutations last so Symphony does not stop the run prematurely.

- Success: update the workpad with the PR URL and evidence, add `human-review`,
  then remove `agent-running` and `agent-ready`. Leave the issue open.
- External blocker: update the workpad with the required human action, reason,
  security implications, verification, and requeue instructions. Add
  `agent-blocked`, then remove `agent-running` and `agent-ready`.
- Requeue after correction: remove `agent-blocked` and restore `agent-ready`.

Do not change branch protection, merge the PR, close the issue, perform
destructive cleanup, or make unresolved product or architecture decisions.
