# PR Wait Hook Boundary

## Status

Accepted.

## Context

Agent Maintainer already owns quiet GitHub PR waiters under
`agent_maintainer.wait`. Agent-client hooks need to trigger those waiters after
a pull request is created so agents do not hand-poll or claim review readiness
before checks finish.

## Decision

Add `agent_maintainer.hooks.pr_wait` as a small hook adapter. It parses
PostToolUse hook payloads for successful `gh pr create` output, converts the PR
URL into a `wait github-pr` handoff, and delegates actual polling to
`agent_maintainer.wait.github_pr`.

The Tach contract allows only this narrow dependency from hooks to the PR waiter.
The hook adapter does not add GitHub polling logic of its own.

## Consequences

Claude Code can run the PR waiter through async rewake. Codex command hooks do
not currently support async handlers, so Codex receives a supported PostToolUse
continuation instructing it to run the wait command before review or merge.

Alternatives considered:

- Put PR creation detection in the generic hook runtime. Rejected because it
  would mix verifier enforcement with GitHub PR lifecycle handling.
- Reimplement PR polling in hooks. Rejected because the wait package already
  owns GitHub polling and compact wait rendering.
- Add a Codex SDK orchestrator now. Rejected for this boundary because it would
  introduce a separate long-running controller process beyond hook installation.
