"""Optional MCP server for Agent Maintainer tools."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_maintainer.mcp import path_safety, tools

INSTALL_HINT = (
    "MCP support is optional. Install it with: python -m pip install 'agent-maintainer[mcp]'"
)

ToolHandler = Callable[..., dict[str, object]]
McpServerFactory = Callable[[str], Any]


def main(argv: list[str] | None = None) -> int:
    """Run MCP server subcommands."""
    args = _parse_args([] if argv is None else argv)
    if args.command == "serve":
        return serve(workspace_root=args.workspace_root)
    return 2


def serve(*, workspace_root: Path | None = None) -> int:
    """Run the optional MCP server."""
    try:
        fast_mcp = _load_fastmcp()
    except ModuleNotFoundError:
        print(INSTALL_HINT, file=sys.stderr)
        return 2

    server = build_server(fast_mcp, workspace_root=workspace_root)
    server.run()
    return 0


def build_server(
    fast_mcp: McpServerFactory,
    *,
    workspace_root: Path | None = None,
) -> Any:
    """Build a FastMCP server and register Agent Maintainer tools."""

    service = McpService.create(Path.cwd() if workspace_root is None else workspace_root)
    server = fast_mcp("agent-maintainer")
    for tool_handler in service.handlers():
        server.tool()(tool_handler)
    return server


class _PrimaryMcpHandlers:
    """Verification and context MCP handlers."""

    workspace_root: Path

    def primary_handlers(self) -> tuple[ToolHandler, ...]:
        """Return verification and context handlers."""

        return (
            self.verify,
            self.context_failures,
            self.context_pack_pointer,
            self.context_file,
        )

    def verify(
        self,
        profile: str = "fast",
        base_ref: str | None = None,
        compare_branch: str | None = None,
        staged: bool = False,
        force: bool = False,
    ) -> dict[str, object]:
        """Run an Agent Maintainer verification profile."""

        return _run_request(
            self.workspace_root,
            tools.verify_request(
                workspace_root=self.workspace_root,
                options=tools.VerifyRequestOptions(
                    profile=profile,
                    base_ref=base_ref,
                    compare_branch=compare_branch,
                    staged=staged,
                    force=force,
                ),
            ),
        )

    def context_failures(
        self,
        log_dir: str = ".verify-logs",
        limit: int = 10,
        check: str | None = None,
    ) -> dict[str, object]:
        """Read recent bounded failure facts."""

        return _run_request(
            self.workspace_root,
            tools.context_failures_request(
                workspace_root=self.workspace_root,
                log_dir=log_dir,
                limit=limit,
                check=check,
            ),
        )

    def context_pack_pointer(
        self,
        log_dir: str = ".verify-logs",
        check: str | None = None,
        base_ref: str = "HEAD",
        budget: int | None = None,
    ) -> dict[str, object]:
        """Write a context pack and return a compact pointer."""

        return _run_request(
            self.workspace_root,
            tools.context_pack_pointer_request(
                workspace_root=self.workspace_root,
                log_dir=log_dir,
                check=check,
                base_ref=base_ref,
                budget=budget,
            ),
        )

    def context_file(
        self,
        path: str,
        lines: str | None = None,
        symbol: str | None = None,
        around: int | None = None,
        context_lines: int | None = None,
    ) -> dict[str, object]:
        """Read a bounded repository source file slice or symbol."""

        return _run_request(
            self.workspace_root,
            tools.context_file_request(
                workspace_root=self.workspace_root,
                options=tools.ContextFileRequestOptions(
                    path=path,
                    lines=lines,
                    symbol=symbol,
                    around=around,
                    context_lines=context_lines,
                ),
            ),
        )


class _SecondaryMcpHandlers:
    """Runtime, attention, and DocSync MCP handlers."""

    workspace_root: Path

    def secondary_handlers(self) -> tuple[ToolHandler, ...]:
        """Return runtime, attention, and DocSync handlers."""

        return (self.events_summary, self.attention, self.docsync_check)

    def events_summary(
        self,
        events_dir: str = ".verify-logs/events",
        limit: int = 10,
        summary: tools.EventSummaryKind = "summary",
    ) -> dict[str, object]:
        """Summarize local runtime events."""

        return _run_request(
            self.workspace_root,
            tools.events_summary_request(
                workspace_root=self.workspace_root,
                events_dir=events_dir,
                limit=limit,
                summary=summary,
            ),
        )

    def attention(self, target: str = ".", limit: int = 10) -> dict[str, object]:
        """Read top attention-ranked files."""

        return _run_request(
            self.workspace_root,
            tools.attention_request(
                workspace_root=self.workspace_root,
                target=target,
                limit=limit,
            ),
        )

    def docsync_check(
        self,
        base: str = "origin/main",
        config: str | None = None,
        trace: str | None = None,
    ) -> dict[str, object]:
        """Run DocSync traceability checks."""

        return _run_request(
            self.workspace_root,
            tools.docsync_check_request(
                workspace_root=self.workspace_root,
                base=base,
                config=config,
                trace=trace,
            ),
        )


@dataclass(frozen=True)
class McpService(_PrimaryMcpHandlers, _SecondaryMcpHandlers):
    """MCP handlers bound to one immutable workspace trust boundary."""

    workspace_root: Path

    @classmethod
    def create(cls, workspace_root: Path) -> McpService:
        """Create a service with one canonical existing workspace root."""

        return cls(path_safety.resolve_workspace_root(workspace_root))

    def handlers(self) -> tuple[ToolHandler, ...]:
        """Return the bounded MCP tool surface for registration."""

        return self.primary_handlers() + self.secondary_handlers()


def _run_request(
    workspace_root: Path,
    request: tools.McpToolRequest,
) -> dict[str, object]:
    """Run one validated request at the captured workspace root."""

    return tools.run_tool_request(request, cwd=workspace_root).to_json()


def _load_fastmcp() -> McpServerFactory:
    """Import FastMCP only when the optional server is actually started."""
    # Keep the optional MCP dependency out of core installs and help paths.
    # pylint: disable-next=import-outside-toplevel
    from mcp.server.fastmcp import FastMCP

    return FastMCP


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse MCP command arguments without importing optional dependencies."""
    parser = argparse.ArgumentParser(prog="python -m agent_maintainer mcp")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "serve",
        help="Run Agent Maintainer MCP server.",
        description="Run Agent Maintainer MCP server.",
    ).add_argument(
        "--workspace-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root that bounds every MCP filesystem path.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
