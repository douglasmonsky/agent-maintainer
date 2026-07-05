+++
id = "claude-async-rewake-hook-option"
kind = "feature"
status = "active"
base_ref = "origin/main"
expires = 2026-07-19
allowed_paths = [
  "src/agent_client_hooks/**",
  "src/agent_maintainer/hooks/**",
  "tests/hooks/**",
  "docs/agent-client-hooks.md",
  "docs/codex-hooks.md",
  "docs/ROADMAP.md",
  "docs/roadmap/phases/phase-155-claude-async-rewake-hook-option.md",
  ".agent-maintainer/change-plans/**",
]
forbidden_paths = [".env", ".env.*"]
max_changed_files = 20
max_changed_lines = 1800
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: claude-async-rewake-hook-option

## Why this change intentionally large

Phase 155 adds an opt-in Claude Code async rewake install mode. The CLI flag, adapter/template plumbing, dry-run output, and regression tests need land together so default Claude settings remain unchanged while slow Stop/SubagentStop validation can be installed asynchronously when requested.

## Why this should not be split smaller

Adding a flag without template output would be misleading. Template changes without tests could silently alter default hook behavior. Dry-run coverage is required to make the option inspectable before installation.

## What allowed to change

- Hook installer CLI and adapter/template code for Claude Code.
- Hook template tests and package boundary tests.
- Roadmap Phase 155 status files.
- Active change-plan cleanup.

## What must not change

- Default Claude Code settings output.
- Codex hook template behavior.
- Fast PostToolUse hook synchrony.
- Verifier profile semantics.

## Verification plan

- `tests/hooks/test_hook_templates.py`.
- `tests/hooks/test_agent_client_hooks_package.py`.
- Dry-run `python3 -m agent_maintainer hooks install claude-code --dry-run --async-rewake-stop`.
- `python3 -m agent_maintainer verify --profile fast`.
- `just change-plan-check`.
- `tach check --exact`.

## Rollback plan

Revert the Phase 155 commit. Claude Code hook installation will keep the current synchronous Stop/SubagentStop settings.

## Follow-up ratchet work

After async rewake behavior is proven in real Claude Code usage, add hook audit evidence that distinguishes synchronous and async rewake hook installations.
