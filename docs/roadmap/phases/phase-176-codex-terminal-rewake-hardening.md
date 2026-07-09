# Phase 176: Codex Terminal Rewake Hardening

## Goal

Make known waits behave like a real suspension primitive in Codex: pending state
is polled by local wait infrastructure, not repeated model turns, and terminal
state resumes Codex exactly once when a supported local rewake surface is
available.

## Current Finding

The Codex desktop app provides `CODEX_THREAD_ID` to local commands. The bundled
`codex` CLI can run `codex app-server --listen stdio://`, and a read-only
`thread/read` probe succeeds against the current thread id. The Python
`openai-codex` package is optional and is not present in the current repo venv.

The preferred local backend is therefore app-server JSON-RPC over the bundled
`codex` CLI. The Python SDK remains a secondary fallback when installed.

## Implementation Plan

1. App-server rewake backend:
   - Add a small JSON-RPC client for `codex app-server --listen stdio://`.
   - Resume the current thread id, start one continuation turn, and detect
     terminal state from either the app-server completion event or a quiet
     `thread/read` status poll.
   - Keep all behavior behind `AGENT_MAINTAINER_CODEX_REWAKE=1`.
   - Do not persist thread ids, prompts, hook stdin, environment dumps, or auth
     material in wait records.

2. Capability detection and doctor output:
   - Report `CODEX_THREAD_ID` presence without printing its value.
   - Report Codex CLI/app-server availability, Python SDK availability, and the
     exact reason terminal rewake is or is not available.
   - Keep fallback heartbeat guidance when terminal rewake is unavailable.

3. Manual smoke harness:
   - Add a gated smoke command that sends a harmless real `turn/start` only when
     an explicit env var is set.
   - Default smoke checks must stay read-only and token-free.

4. Exactly-once terminal claim:
   - Add durable notification states such as `notifying`, `resumed`, and
     `notify_failed`.
   - Claim terminal notification before calling Codex so parallel watchers cannot
     double-wake the same wait.

5. Watcher lifecycle repair:
   - Persist watcher pid, started time, and last poll time where safe.
   - Add repair command support for stale pending waits whose watcher died.

6. Fallback heartbeat hardening:
   - Keep fallback requests marked `fallback_only: true`.
   - Include cheap-model and minimal-reasoning hints.
   - Prefer backoff over minute-by-minute model wakeups.

7. Observability and privacy:
   - Emit events for registered, watcher started, terminal observed, notify
     attempted, resumed, failed, and fallback used.
   - Add regression tests that durable wait records never contain thread ids,
     prompts, hook stdin, API keys, or private payloads.

## Current Slice

This phase starts by adding the app-server JSON-RPC backend and documenting the
full hardening roadmap. The real `turn/start` smoke remains manual and gated
until a user explicitly approves spending a Codex model turn.

## Acceptance Criteria

- Codex background waits do not silently downgrade to detached `popen` when
  launchd cannot start.
- App-server acceptance leaves waits ready for manual resume instead of marking
  them `resumed`.
- Missing app-server support leaves waits ready for manual resume.
- Handoff rendering treats heartbeat fallback as explicit model-turn fallback,
  not as no-cost automatic wake.
- Docs clearly state heartbeat fallback still costs model turns.
- Roadmap tracker links this phase for follow-up hardening work.

## Out Of Scope

- Arbitrary interception of every long-running shell command.
- Persisting Codex thread ids or private prompts in durable wait records.
- Making terminal rewake default before the gated real-turn smoke proves the
  current desktop thread resumes as intended.
