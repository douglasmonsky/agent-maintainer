"""Shared agent-client hook constants."""

CODEX_PLATFORM = "codex"
CLAUDE_CODE_PLATFORM = "claude-code"

POST_TOOL_USE_EVENT = "PostToolUse"
STOP_EVENT = "Stop"
SUBAGENT_STOP_EVENT = "SubagentStop"

CODEX_CLIENT = "codex"
CLAUDE_CODE_CLIENT = "claude-code"
ALL_CLIENTS = "all"
CLIENTS = (CODEX_CLIENT, CLAUDE_CODE_CLIENT)

REPO_SCOPE = "repo"
USER_SCOPE = "user"
SCOPES = (REPO_SCOPE, USER_SCOPE)
