"""Tests for the optional Agent Maintainer MCP surface."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent_maintainer.mcp import server, tools
from agent_maintainer.mcp.models import McpToolResult
from tests.support.paths import REPO_ROOT

MISSING_DEPENDENCY_STATUS = 2


def test_mcp_tool_requests_use_current_module_entrypoints() -> None:
    """Tool requests should keep behavior backed by existing CLIs."""

    verify = tools.verify_request(profile="precommit", staged=True, force=True)
    assert verify.command[:3] == (sys.executable, "-m", "agent_maintainer")
    assert verify.command[3:] == (
        "verify",
        "--profile",
        "precommit",
        "--staged",
        "--force",
    )

    failures = tools.context_failures_request(check="pyright", limit=3)
    assert failures.command[:4] == (
        sys.executable,
        "-m",
        "agent_maintainer",
        "context",
    )
    assert "failures" in failures.command
    assert "--format" in failures.command
    assert "json" in failures.command

    docsync = tools.docsync_check_request(base="origin/main")
    assert docsync.command == (
        sys.executable,
        "-m",
        "docsync",
        "check",
        "--base",
        "origin/main",
    )


def test_context_pack_request_returns_pointer_not_full_pack_command() -> None:
    """MCP context packs must default to compact pointer output."""

    request = tools.context_pack_pointer_request(check="pyright", budget=1000)
    assert request.command[:4] == (
        sys.executable,
        "-m",
        "agent_maintainer",
        "context",
    )
    assert "pack" in request.command
    assert "--print-full" not in request.command
    assert "--format" in request.command
    assert "json" in request.command


def test_run_tool_request_bounds_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Tool execution captures bounded output instead of leaking transcripts."""

    def fake_run(*args: object, **kwargs: object) -> SimpleNamespace:
        assert kwargs["cwd"] == tmp_path
        assert kwargs["capture_output"] is True
        assert kwargs["check"] is False
        return SimpleNamespace(
            returncode=1,
            stdout="x" * 20,
            stderr="y" * 20,
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    request = tools.verify_request(profile="fast")
    short_request = request.__class__(
        name=request.name,
        description=request.description,
        command=request.command,
        output_limit_chars=12,
        timeout_seconds=request.timeout_seconds,
    )

    result = tools.run_tool_request(short_request, cwd=tmp_path)

    assert result.returncode == 1
    assert result.stdout_truncated is True
    assert result.stderr_truncated is True
    assert result.stdout.endswith("x")
    assert result.stderr.endswith("y")


def test_mcp_serve_help_does_not_require_optional_dependency() -> None:
    """The help path must work in core installs without the MCP extra."""

    result = subprocess.run(  # nosec B603
        [
            sys.executable,
            "-m",
            "agent_maintainer",
            "mcp",
            "serve",
            "--help",
        ],
        cwd=REPO_ROOT,
        env={"PYTHONPATH": str(REPO_ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Run Agent Maintainer MCP server" in result.stdout


def test_mcp_serve_missing_dependency_exits_with_install_hint(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Starting the server without MCP dependency returns actionable guidance."""

    def missing_fastmcp() -> type[object]:
        raise ModuleNotFoundError("mcp")

    monkeypatch.setattr(server, "_load_fastmcp", missing_fastmcp)

    assert server.main(["serve"]) == MISSING_DEPENDENCY_STATUS
    captured = capsys.readouterr()
    assert "agent-maintainer[mcp]" in captured.err


def test_build_server_registers_expected_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    """FastMCP registration stays limited to the Phase 156 surface."""

    class FakeFastMCP:
        def __init__(self, name: str) -> None:
            self.name = name
            self.tools: dict[str, object] = {}

        def tool(self) -> Callable[[Callable[..., object]], Callable[..., object]]:
            def decorate(function: Callable[..., object]) -> Callable[..., object]:
                self.tools[function.__name__] = function
                return function

            return decorate

        def run(self) -> None:
            raise AssertionError("test should not start server loop")

    def fake_run_tool_request(_request: object) -> McpToolResult:
        return McpToolResult(
            name="fake",
            command=("fake",),
            cwd=REPO_ROOT,
            returncode=0,
            stdout="ok",
            stderr="",
            stdout_truncated=False,
            stderr_truncated=False,
        )

    monkeypatch.setattr(tools, "run_tool_request", fake_run_tool_request)

    fake_server = server.build_server(FakeFastMCP)

    assert fake_server.name == "agent-maintainer"
    assert set(fake_server.tools) == {
        "attention",
        "context_failures",
        "context_file",
        "context_pack_pointer",
        "docsync_check",
        "events_summary",
        "verify",
    }
    assert fake_server.tools["context_pack_pointer"] is server.context_pack_pointer
    assert fake_server.tools["verify"]() == {
        "tool": "fake",
        "ok": True,
        "returncode": 0,
        "command": ["fake"],
        "cwd": str(REPO_ROOT),
        "stdout": "ok",
        "stderr": "",
        "stdout_truncated": False,
        "stderr_truncated": False,
    }
