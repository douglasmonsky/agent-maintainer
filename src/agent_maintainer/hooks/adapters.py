"""Compatibility exports for agent-client hook adapters."""

from agent_client_hooks import adapters as _adapters
from agent_client_hooks import constants as _constants

ALL_CLIENTS = _constants.ALL_CLIENTS
CLIENTS = _constants.CLIENTS
CLAUDE_CODE_CLIENT = _constants.CLAUDE_CODE_CLIENT
CODEX_CLIENT = _constants.CODEX_CLIENT
REPO_SCOPE = _constants.REPO_SCOPE
SCOPES = _constants.SCOPES
USER_SCOPE = _constants.USER_SCOPE

AgentClientAdapter = _adapters.AgentClientAdapter
ClaudeCodeAdapter = _adapters.ClaudeCodeAdapter
CodexAdapter = _adapters.CodexAdapter
HookClientStatus = _adapters.HookClientStatus
InstallOptions = _adapters.InstallOptions
PlannedWrite = _adapters.PlannedWrite
adapter_for_client = _adapters.adapter_for_client
client_adapters = _adapters.client_adapters
config_file = _adapters.config_file
home = _adapters.home
hook_script_paths = _adapters.hook_script_paths
hook_status = _adapters.hook_status
scoped_path = _adapters.scoped_path
selected_clients = _adapters.selected_clients
