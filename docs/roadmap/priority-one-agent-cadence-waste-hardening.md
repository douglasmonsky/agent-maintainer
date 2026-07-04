# Priority One: Agent Cadence Waste Hardening

## Goal

Reduce duplicated verification, model-managed polling, and low-value narration
before continuing the Future-Call ROI track. Agent Maintainer should make the
right verification cadence easier than the wasteful cadence.

## Why This Moved Ahead Of Phase 148

Recent local conversation-log analysis showed repeated patterns that increase
latency and token usage without clear quality gain:

- repeated `precommit` runs in the same turn;
- `full` and `ci` run together by habit;
- `security` and `manual` run together on ordinary changes;
- three or more heavy profiles in one turn;
- frequent empty wait polls for long-running checks;
- noisy status narration around normal-duration commands;
- heredoc Python rewrite commands where patch edits would be clearer;
- chained shell validation commands that obscure the first failing gate.

Phase 148 surgical context ranking remains valuable, but duplicated process
control is now the larger cost leak. This hardening track must land first.

## Product Principle

Waiting and readiness should be handled by tools, not by the model.

When a long local or remote check is expected, Agent Maintainer should offer a
single blocking command or hook-visible readiness state that returns one compact
final repair capsule. The agent should not spend repeated turns asking whether a
known long-running command is done.

Codex thread automations are a preferred client-level option where available:
use a heartbeat automation attached to the same thread for long-running command
checks, GitHub polling, or review loops that should preserve thread context.
Agent Maintainer should provide durable prompts and compact status commands that
fit this automation model instead of forcing the model to poll manually.

## Scope

### 1. Cadence Waste Report

Add a local report, likely:

```bash
python -m agent_maintainer events waste
```

The report should summarize waste signals without reading or printing raw
conversation content:

- repeated same-profile verifier runs in a short window;
- `full` plus `ci` in the same work segment;
- `security` plus `manual` outside release or gate-touching work;
- three or more heavy profiles in one segment;
- repeated same-state verifier results where reuse should have happened;
- excessive wait polls;
- repeated `still running` style messages when durations are within profile
  expectations;
- heredoc Python rewrite commands;
- heavily chained validation commands.

The first version can use runtime events where available and should clearly mark
signals that require richer event coverage before they can be measured
accurately.

### 2. Quiet Waiter Commands

Add a command surface that blocks internally and emits only final status, for
example:

```bash
python -m agent_maintainer wait github-run <run-id>
python -m agent_maintainer wait verifier <job-id>
```

The exact command shape may change during implementation, but the invariant is
stable: the model makes one tool call, and the command owns polling, backoff,
timeout, final status, and compact failure output.

Where Codex thread automations are available, Agent Maintainer should also
document or generate a durable thread-automation prompt that wakes the thread and
calls the quiet waiter/status command. This should hand off to the Codex app
automation surface, not create a second custom scheduler.

For GitHub Actions, the waiter should:

- poll GitHub JSON internally;
- avoid streaming every intermediate job state;
- print final pass/fail with run URL;
- on failure, print the failed job names and the next exact command to inspect
  logs;
- exit nonzero only when the watched run fails, times out, or cannot be read.

### 3. Async Verification Readiness

Design a local asynchronous verification path without requiring client-specific
magic first:

```bash
python -m agent_maintainer verify --profile full --async
python -m agent_maintainer wait verifier <job-id>
python -m agent_maintainer verify status <job-id>
```

The final command names are implementation details; the needed behavior is:

- background verifier jobs write a small state file with job id, profile,
  fingerprint, started time, status, and final run id;
- readiness status is machine-readable;
- completed jobs return the same compact repair capsule as foreground verify;
- changed repo state invalidates or labels the job result stale;
- retention prevents job-state buildup.

### 4. Hook-Visible Readiness

Hooks should be able to report readiness without rerunning the same work:

- if a hook sees an in-flight same-state verifier job, it should report pending
  with a compact pointer rather than launching a duplicate;
- if a same-state job completed, the hook should reuse the final result;
- if repo state changed, the hook should require or start fresh verification.

True proactive re-wake depends on the agent client. Agent Maintainer should
prepare the local readiness protocol first, then map Codex, Claude Code, or
other clients onto it where supported.

### 5. Profile Overlap Guardrails

Add structured guidance and, where practical, warnings for redundant local
validation:

- `precommit` should not be manually repeated when a trusted same-state Stop
  hook already passed;
- run one broad local profile by default, usually `full`;
- run `ci` instead of `full` when diff/base-ref/workflow/profile behavior
  changed;
- run both `full` and `ci` only when overlap itself is under test;
- run `security` or `manual` only when gates are touched, before release, or
  explicitly requested.

The implementation should prefer gentle warnings and reports over blocking
normal user commands.

### 6. Edit Discipline Signals

Add a local advisory signal for noisy edit/process patterns:

- heredoc Python rewrite commands used for manual edits;
- repeated exact command calls;
- large chained validation commands;
- generated bytecode/cache debris after direct Python commands.

This should be advisory and local-only. It should not require raw transcript
publication, and it must not print sensitive prompts, file contents, or command
output.

### 7. Passive DocSync Freshness Metadata

Add passive freshness metadata for DocSync documentation objects and evidence
regions so agents and maintainers can see when mapped documentation evidence
last changed without manually editing timestamps.

Design constraints:

- freshness collection must be passive, cheap, and incremental;
- normal development must not wait on slow whole-repo rescans;
- agents must not manually write "last updated" fields human docs;
- implementation should avoid noisy documentation diffs;
- generated freshness state should live in deterministic DocSync state or
  artifact storage, not in prose every run;
- stale or missing freshness metadata should produce actionable repair guidance,
  not block unrelated code changes by default.

Likely first implementation:

```bash
python -m docsync freshness
```

The command can update or report generated metadata such as:

- documentation object id;
- evidence id;
- last observed content hash;
- last observed Git commit or working-tree fingerprint when available;
- last observed timestamp;
- stale or missing status;
- suggested DocSync command when metadata needs refresh.

This should integrate with DocSync verifier/doctor later. initial roadmap item
should stay small: define state file, retention/update rules, non-blocking
report before making freshness hard gate.

## Implementation Status

- [x] Initial `events waste` command summarizing measured runtime-event
  cadence waste signals and explicit measurement limitations.
- [ ] Quiet waiter commands.
- [ ] Async verification readiness.
- [ ] Hook-visible readiness.
- [ ] Profile overlap guardrails beyond guidance.
- [ ] Edit discipline advisory signals.
- [ ] Passive DocSync freshness metadata.

## Non-Goals

- Do not add remote telemetry.
- Do not upload conversation logs.
- Do not block normal verification because an agent used an inefficient cadence.
- Do not require old conversation JSONL logs for normal repo operation.
- Do not make hooks globally active in unconfigured repositories.
- Do not replace existing verifier profiles.
- Do not remove final strict validation before PR/merge.

## Acceptance Criteria

- A tracked task exists ahead of Phase 148.
- A detailed implementation spec exists for cadence waste reduction.
- Tests cover cadence classification for repeated profiles and heavy-profile
  overlap.
- Tests cover quiet wait behavior with a fake long-running backend.
- Tests cover async verifier job state pass, fail, stale, and retention cases.
- Hook tests prove same-state in-flight or completed jobs do not launch
  duplicate work.
- Generated guidance says tools should own expected waiting and readiness.
- No raw conversation text is printed by cadence reports.
- Normal verification output remains compact.

## Suggested Implementation Order

1. Add `events waste` based on existing runtime event files and explicit
   limitations.
2. Add a quiet GitHub run waiter wrapper to replace noisy `gh run watch`.
3. Add local verifier job-state models and retention.
4. Add foreground `wait verifier` behavior for async jobs.
5. Teach hooks to reuse in-flight or completed same-state jobs.
6. Add cadence guidance and regression tests.
7. Dogfood the report on this repository and record the before/after signals.

## Verification

Focused implementation PRs should run:

```bash
python -m pytest tests/runtime_events tests/hooks tests/verify -q
python -m agent_maintainer guidance --check
python -m agent_maintainer change-plan check
tach check --exact
python -m agent_maintainer verify --profile precommit
python -m agent_maintainer verify --profile full
```

Use `ci` locally instead of `full` only when CI/base-ref behavior is modified.
Do not run both broad profiles unless the overlap prevention itself is under
test.
