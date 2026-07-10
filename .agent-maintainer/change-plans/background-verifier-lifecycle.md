+++
id = "background-verifier-lifecycle"
kind = "fix"
status = "active"
base_ref = "58b468e"
expires = 2026-08-31
allowed_paths = [
  ".agent-maintainer/change-plans/background-verifier-lifecycle.md",
  "CHANGELOG.md",
  "docs/architecture/decisions/2026-07-07-codex-verifier-background-wait.md",
  "docs/roadmap/critical-stabilization.md",
  "src/agent_maintainer/verify/**",
  "src/agent_maintainer/wait/**",
  "tests/verify/**",
  "tests/wait/**",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 40
max_changed_lines = 5000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++
# Cohesive Change Plan: background-verifier-lifecycle

## Why this change intentionally large

CS-06 crosses the process-launch and durable-state boundary. The detached
verifier, its watcher, the async job record, and wait-result interpretation
must agree on standard streams and terminal outcomes; fixing only one `Popen`
call would leave alternate background launches or ambiguous failures behind.

## Why this should not be split smaller

Owned descriptors, typed launch failure, terminal job state, wait-registry
completion, and the closed-terminal integration test are one reliability
contract. They may land in focused commits, but the unit closes only when a
real child survives its launching terminal and reports the actual check result.

## What allowed to change

Change only async verifier lifecycle code, detached wait-watcher launch code,
their Tach contracts, focused tests, the existing background-verifier ADR, the
critical roadmap evidence, and user-facing changelog text. Add no unrelated
wait features.

## What must not change

Do not weaken verifier checks, reinterpret a quality failure as infrastructure
success, add production process management, or make detached jobs depend on an
interactive terminal. Do not hide launch errors or discard existing wait
records.

## Verification plan

Add unit coverage for owned stdin/stdout/stderr, closed inherited descriptors,
spawn failure, cancellation state, terminal state, watcher launch, and
quality-versus-infrastructure classification. Add a POSIX pseudo-terminal
integration test that closes the parent descriptor before launch, closes the
terminal after the parent exits, and observes the real verifier manifest and
wait result. Run focused verify/wait tests, static and architecture checks, then
the full profile.

## Rollback plan

Keep lifecycle state and command wiring in one focused implementation commit.
If rollback is necessary, revert that commit together; do not retain detached
launching without owned stdin. Foreground verification remains the safe
fallback.

## Follow-up ratchet work

Keep the terminal-close integration test in the required suite. Any future
noninteractive `Popen` boundary must declare all three standard streams,
descriptor inheritance, session ownership, and durable terminal reporting.
