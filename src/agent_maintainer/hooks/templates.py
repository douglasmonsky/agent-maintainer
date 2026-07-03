"""Compatibility exports for agent-client hook templates."""

from agent_client_hooks import constants as _constants
from agent_client_hooks import templates as _templates

CLAUDE_CODE_PLATFORM = _constants.CLAUDE_CODE_PLATFORM
CODEX_PLATFORM = _constants.CODEX_PLATFORM
POST_TOOL_USE_EVENT = _constants.POST_TOOL_USE_EVENT
STOP_EVENT = _constants.STOP_EVENT
SUBAGENT_STOP_EVENT = _constants.SUBAGENT_STOP_EVENT

CLAUDE_POST_HOOK = _templates.CLAUDE_POST_HOOK
CLAUDE_STOP_HOOK = _templates.CLAUDE_STOP_HOOK
CLAUDE_SUBAGENT_STOP_HOOK = _templates.CLAUDE_SUBAGENT_STOP_HOOK
CODEX_MARKER = _templates.CODEX_MARKER
CODEX_POST_HOOK = _templates.CODEX_POST_HOOK
CODEX_STOP_HOOK = _templates.CODEX_STOP_HOOK
MANAGED_PREFIX = _templates.MANAGED_PREFIX
claude_post_hook = _templates.claude_post_hook
claude_settings = _templates.claude_settings
claude_stop_hook = _templates.claude_stop_hook
claude_subagent_stop_hook = _templates.claude_subagent_stop_hook
codex_config_block = _templates.codex_config_block
codex_config_file = _templates.codex_config_file
codex_post_hook = _templates.codex_post_hook
codex_stop_hook = _templates.codex_stop_hook
hook_audit_shim = _templates.hook_audit_shim
hook_command = _templates.hook_command
hook_wrapper = _templates.hook_wrapper
managed_toml_block = _templates.managed_toml_block
