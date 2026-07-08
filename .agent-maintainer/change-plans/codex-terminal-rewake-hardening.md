+++
id = "codex-terminal-rewake-hardening"
kind = "mechanical-migration"
status = "active"
base_ref = "origin/main"
expires = 2026-07-22
allowed_paths = ["src/agent_maintainer/wait/**", "src/agent_waits/**", "tests/wait/**", "tests/hooks/**", "tests/packaging/**", "docs/**"]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 120
max_changed_lines = 12000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: codex-terminal-rewake-hardening

## Why this change intentionally large

Codex terminal rewake touches the full known-wait path: wait handoff rendering,
Codex rewake orchestration, app-server JSON-RPC protocol handling, verifier
wait terminal-state detection, and regression coverage. The app-server client
was extracted to keep the rewake backend under file-size limits and to isolate
process/protocol mechanics from wait-record state changes.

## Why this should not be split smaller

The app-server backend, fallback behavior, and tests need to land together so
`AGENT_MAINTAINER_CODEX_REWAKE=1` does not expose a half-wired automatic wake
path. Splitting the cached verifier wait fix separately would leave the same
branch able to register a background verifier wait that never reaches terminal
state when the verifier reuses a cached result.

## What allowed to change

Allowed changes are limited to wait orchestration modules, reusable wait
handoff rendering, targeted wait tests, and docs/ADR text explaining the
boundary. The change may update the wait Tach domain contract only to reflect
actual imports.

## What must not change

Do not persist Codex thread ids, prompts, hook stdin, API keys, environment
dumps, or app-server request/response payloads. Do not change GitHub polling
semantics, verifier check thresholds, production settings, or unrelated
Python/TypeScript analysis behavior.

## Verification plan

Run targeted wait tests, Pyright on touched wait modules/tests, `tach
check --exact`, `python -m docsync check`, `git diff --check`, and the CI
profile through `just vc`. Include a real app-server rewake smoke when local
Codex app-server access is available.

## Rollback plan

Disable automatic rewake by leaving `AGENT_MAINTAINER_CODEX_REWAKE` unset or
set to `0`; background waits still emit manual resume capsules and heartbeat
requests. If app-server rewake is unsafe, revert the app-server client and
backend wiring while keeping verifier cached-result handling.

## Follow-up ratchet work

After dogfooding, measure terminal rewake success/fallback rates, decide
whether Codex automatic rewake should become the repo default, and consider
moving reusable non-Codex wait result parsing into a smaller standalone
package boundary if more wait kinds adopt it.
