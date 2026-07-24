---
name: symphony-github-work
description: Complete a GitHub issue dispatched by Symphony in Agent Maintainer. Use for unattended issues carrying `agent-ready` that require scoped implementation, verification, a clean commit, a pushed branch, a pull request, and lifecycle-label handoff through Symphony's injected `github_api` tool.
---

# Complete Symphony GitHub Work

Treat the issue as the authorization and scope contract. If objective, scope,
acceptance criteria, verification, dependencies, or resolved human decisions
are materially missing, block before editing.

## Execute

1. Read the issue and reject missing or contradictory material sections.
2. Run `/Users/Monsky/.codex-symphony/bin/symphony-git prepare` before broad
   repository reading. It validates the issue workspace, fetches `origin/main`,
   and creates or reuses `codex/symphony-gh-<issue-number>` outside the
   protected Git metadata sandbox.
3. Read applicable `AGENTS.md` files and only relevant architecture docs.
4. Add `agent-running` while retaining `agent-ready`.
5. Find or create one issue comment headed `## Symphony Workpad`. Keep the plan,
   acceptance checklist, current action, verification, and blockers there.
6. Reproduce or inspect first, implement only the issue scope, and add tests for
   behavior changes.
7. Run focused checks during development and `scripts/verify` at the coherent
   final state.
8. Review status and diffs for scope, generated files, secrets, and private data.
9. Publish only explicit changed paths with
   `/Users/Monsky/.codex-symphony/bin/symphony-git publish "<type>: <summary>" <path>...`.
10. Use `github_api` to open or update a pull request against `main`. Follow
   `.github/pull_request_template.md` and record exact verification evidence.

Use `github_api` for repository-scoped issue comments, labels, and pull-request
operations. Do not expose its host-side credential or copy it into the
workspace. Do not run ordinary mutating `git` commands. Codex protects `.git`
recursively under `workspace-write`; the installed, read-only bridge is narrowly
allowed outside the sandbox and refuses any checkout outside a direct
`GH-<number>` workspace, unexpected branch, implicit staging, or dirty publish.

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
