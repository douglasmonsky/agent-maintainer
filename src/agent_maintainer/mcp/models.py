"""Models for the Agent Maintainer MCP command surface."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_OUTPUT_LIMIT_CHARS = 4_000
DEFAULT_TIMEOUT_SECONDS = 900


@dataclass(frozen=True)
class McpToolRequest:
    """Bounded request for an Agent Maintainer-backed MCP tool."""

    name: str
    description: str
    command: tuple[str, ...]
    output_limit_chars: int = DEFAULT_OUTPUT_LIMIT_CHARS
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS


@dataclass(frozen=True)
class McpToolResult:
    """Compact command result suitable for MCP responses."""

    name: str
    command: tuple[str, ...]
    cwd: Path
    returncode: int
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool

    @property
    def ok(self) -> bool:
        """Return whether the command succeeded."""

        return self.returncode == 0

    def to_json(self) -> dict[str, object]:
        """Return a JSON-serializable result payload."""

        return {
            "tool": self.name,
            "ok": self.ok,
            "returncode": self.returncode,
            "command": list(self.command),
            "cwd": str(self.cwd),
            "stdout": self.stdout,
            "stderr": self.stderr,
            "stdout_truncated": self.stdout_truncated,
            "stderr_truncated": self.stderr_truncated,
        }
