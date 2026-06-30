# Phase 4: Config Scaffolding

## PR Title

```text
feat: add context ratchet and change-plan config scaffolding
```

## Goal

Add inert configuration fields for the upcoming layers.

## Files

Update:

```text
src/agent_maintainer/config/schema.py
src/agent_maintainer/config/loader.py
src/agent_maintainer/config/coercion.py
config/pyproject.agent-maintainer.toml
src/agent_maintainer/core/init_template_config.py
tests/config/
```

## Config Fields

Add to `MaintainerConfig`:

```python
context_default_budget_chars: int = 12000
context_hook_budget_chars: int = 8000
context_last_failure_budget_chars: int = 16000
context_pack_budget_chars: int = 24000
context_large_file_threshold_lines: int = 800
context_large_file_threshold_bytes: int = 250_000
context_max_direct_file_read_lines: int = 250
context_max_direct_log_read_lines: int = 200
context_max_failure_items: int = 10
context_max_paths_default: int = 50
context_require_outline_for_large_files: bool = True

context_compression_enabled: bool = False
context_compression_backend: str = "extractive"
context_compression_target_ratio: float = 0.5
context_compression_require_backend: bool = False

ratchet_enabled: bool = False
ratchet_baseline_path: str = ".agent-maintainer/ratchet-baseline.json"
ratchet_guidance_path: str = "AGENTS.ratchet.md"
ratchet_target_limit: int = 5

large_changes_enabled: bool = False
large_change_plan_dirs: tuple[str, ...] = (".agent-maintainer/change-plans",)
large_change_max_active_plans: int = 1
large_change_allow_expired_plans: bool = False
large_change_require_required_sections: bool = True
large_change_fail_out_of_plan_paths: bool = True
```

## Environment Variables

Add support for:

```text
AGENT_MAINTAINER_CONTEXT_DEFAULT_BUDGET_CHARS
AGENT_MAINTAINER_CONTEXT_HOOK_BUDGET_CHARS
AGENT_MAINTAINER_CONTEXT_LAST_FAILURE_BUDGET_CHARS
AGENT_MAINTAINER_CONTEXT_PACK_BUDGET_CHARS
AGENT_MAINTAINER_CONTEXT_LARGE_FILE_THRESHOLD_LINES
AGENT_MAINTAINER_CONTEXT_LARGE_FILE_THRESHOLD_BYTES
AGENT_MAINTAINER_CONTEXT_MAX_DIRECT_FILE_READ_LINES
AGENT_MAINTAINER_CONTEXT_MAX_DIRECT_LOG_READ_LINES
AGENT_MAINTAINER_CONTEXT_MAX_FAILURE_ITEMS
AGENT_MAINTAINER_CONTEXT_MAX_PATHS_DEFAULT
AGENT_MAINTAINER_CONTEXT_REQUIRE_OUTLINE_FOR_LARGE_FILES
AGENT_MAINTAINER_CONTEXT_COMPRESSION_ENABLED
AGENT_MAINTAINER_CONTEXT_COMPRESSION_BACKEND
AGENT_MAINTAINER_CONTEXT_COMPRESSION_TARGET_RATIO
AGENT_MAINTAINER_CONTEXT_COMPRESSION_REQUIRE_BACKEND
AGENT_MAINTAINER_RATCHET_ENABLED
AGENT_MAINTAINER_RATCHET_BASELINE_PATH
AGENT_MAINTAINER_RATCHET_GUIDANCE_PATH
AGENT_MAINTAINER_RATCHET_TARGET_LIMIT
AGENT_MAINTAINER_LARGE_CHANGES_ENABLED
AGENT_MAINTAINER_LARGE_CHANGE_PLAN_DIRS
AGENT_MAINTAINER_LARGE_CHANGE_MAX_ACTIVE_PLANS
AGENT_MAINTAINER_LARGE_CHANGE_ALLOW_EXPIRED_PLANS
AGENT_MAINTAINER_LARGE_CHANGE_REQUIRE_REQUIRED_SECTIONS
AGENT_MAINTAINER_LARGE_CHANGE_FAIL_OUT_OF_PLAN_PATHS
```

## Starter Config

Add these fields to the starter config with defaults.

## Tests

Add tests for:

```text
default values
pyproject overrides
environment overrides
starter template match
invalid compression backend rejected
invalid negative budgets rejected
```

## Acceptance Criteria

- Config loads.
- Defaults are stable.
- Env overrides work.
- Starter config matches initializer.
- No behavior changes.
- Precommit passes.

---
