+++
id = "attention-weighted-context-packs"
kind = "feature"
status = "active"
base_ref = "origin/main"
expires = 2026-07-18
allowed_paths = [
  "src/**",
  "tests/**",
  "docs/**",
  ".agent-maintainer/change-plans/**",
  "AGENTS.md",
  "AGENTS.agent-maintainer.md",
  "justfile",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 80
max_changed_lines = 8000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: attention-weighted-context-packs

## Why this change intentionally large

Phase 151 connects the Phase 150 attention ledger to context-pack payloads and
hook-safe pointer output. The work crosses context-pack builder logic, reusable
pack rendering, Tach ownership, focused tests, and roadmap status.

## Why this should not be split smaller

Adding the payload without pointer rendering would not deliver the agent-facing
ROI. Adding pointer rendering without payload tests would make the output fragile.
Keeping the adapter, renderer, tests, and docs together preserves one coherent
feature: bounded attention-aware context packs.

## What allowed to change

- Context-pack builder payload construction.
- Context-pack attention adapter helpers.
- Generic pack rendering for optional attention sections and pointer notes.
- Focused context/attention tests.
- Tach domain ownership and ADR for the new boundary.
- Roadmap Phase 151 status.
- Short verifier command aliases and generated/local agent guidance that point to
  those aliases.

## What must not change

- Existing context-pack keys or default raw context size.
- Existing verifier profile behavior.
- Existing hook execution behavior.
- Existing attention ledger generation semantics.
- Existing repair fact parser behavior.

## Verification plan

- `tests/context/test_packs.py`.
- `tests/attention/test_attention_context_pack.py`.
- `python -m agent_maintainer attention update`.
- `python -m agent_maintainer context pack`.
- `tach check --exact`.
- `python -m agent_maintainer verify --profile fast`.

## Rollback plan

Remove the context-pack attention adapter, builder payload additions, rendering
section and pointer notes, tests, Tach domain changes, ADR, and Phase 151 roadmap
completion mark. Existing context packs keep working because the new block is
optional.

## Follow-up ratchet work

Later phases can score whether attention-weighted context packs reduce repeated
file reads or improve repair success. Phase 151 only adds the local payload and
bounded pointer notes.
