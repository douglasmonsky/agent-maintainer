"""Models for the Agent Maintainer MCP command surface."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_OUTPUT_LIMIT_CHARS = 4_000
DEFAULT_TIMEOUT_SECONDS = 900
DEFAULT_HARD_OUTPUT_LIMIT_BYTES = 1_048_576


@dataclass(frozen=True)
class McpToolRequest:
    """Bounded request for an Agent Maintainer-backed MCP tool."""

    name: str
    description: str
    command: tuple[str, ...]
    output_limit_chars: int = DEFAULT_OUTPUT_LIMIT_CHARS
    hard_output_limit_bytes: int = DEFAULT_HARD_OUTPUT_LIMIT_BYTES
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    environment: tuple[tuple[str, str], ...] = ()
    generated_root: str | None = None


@dataclass(frozen=True)
class McpToolResult:
    """Compact command result suitable for MCP responses."""

    name: str
    description: str
    command: tuple[str, ...]
    cwd: Path
    returncode: int
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool
    generated_root: str | None = None
    timed_out: bool = False
    stdout_limit_exceeded: bool = False
    stderr_limit_exceeded: bool = False

    @property
    def ok(self) -> bool:
        """Return whether the command succeeded."""

        return (
            self.returncode == 0
            and not self.timed_out
            and not self.stdout_limit_exceeded
            and not self.stderr_limit_exceeded
        )

    def to_json(self) -> dict[str, object]:
        """Return a JSON-serializable result payload."""

        payload: dict[str, object] = {
            "tool": self.name,
            "description": self.description,
            "ok": self.ok,
            "returncode": self.returncode,
            "command": list(self.command),
            "cwd": str(self.cwd),
            "stdout": self.stdout,
            "stderr": self.stderr,
            "stdout_truncated": self.stdout_truncated,
            "stderr_truncated": self.stderr_truncated,
            "timed_out": self.timed_out,
            "stdout_limit_exceeded": self.stdout_limit_exceeded,
            "stderr_limit_exceeded": self.stderr_limit_exceeded,
        }
        if self.generated_root is not None:
            payload["generated_root"] = self.generated_root
        return payload
