"""Optional MCP server for Agent Maintainer tools."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from agent_maintainer.mcp import tools

INSTALL_HINT = (
    "MCP support is optional. Install it with: python -m pip install 'agent-maintainer[mcp]'"
)


def main(argv: list[str] | None = None) -> int:
    """Run MCP server subcommands."""

    args = _parse_args([] if argv is None else argv)
    if args.command == "serve":
        return serve()
    return 2


def serve() -> int:
    """Start the optional MCP server."""

    try:
        fast_mcp = _load_fastmcp()
    except ModuleNotFoundError:
        print(INSTALL_HINT, file=sys.stderr)
        return 2

    server = build_server(fast_mcp)
    server.run()
    return 0


def build_server(fast_mcp: type[Any]) -> Any:
    """Build a FastMCP server instance and register Agent Maintainer tools."""

    server = fast_mcp("agent-maintainer")

    @server.tool()
    def verify(
        profile: str = "fast",
        base_ref: str | None = None,
        compare_branch: str | None = None,
        staged: bool = False,
        force: bool = False,
    ) -> dict[str, object]:
        """Run an Agent Maintainer verification profile."""

        return tools.run_tool_request(
            tools.verify_request(
                profile=profile,
                base_ref=base_ref,
                compare_branch=compare_branch,
                staged=staged,
                force=force,
            ),
        ).to_json()

    @server.tool()
    def context_failures(
        log_dir: str = ".verify-logs",
        limit: int = 10,
        check: str | None = None,
    ) -> dict[str, object]:
        """Read recent bounded failure facts."""

        return tools.run_tool_request(
            tools.context_failures_request(
                log_dir=log_dir,
                limit=limit,
                check=check,
            ),
        ).to_json()

    @server.tool()
    def context_pack_pointer(
        log_dir: str = ".verify-logs",
        check: str | None = None,
        base_ref: str = "HEAD",
        budget: int | None = None,
    ) -> dict[str, object]:
        """Write a context pack and return a compact pointer."""

        return tools.run_tool_request(
            tools.context_pack_pointer_request(
                log_dir=log_dir,
                check=check,
                base_ref=base_ref,
                budget=budget,
            ),
        ).to_json()

    @server.tool()
    def context_file(
        path: str,
        lines: str | None = None,
        symbol: str | None = None,
        around: int | None = None,
        context_lines: int | None = None,
    ) -> dict[str, object]:
        """Read bounded source context for a file or symbol."""

        return tools.run_tool_request(
            tools.context_file_request(
                path=path,
                lines=lines,
                symbol=symbol,
                around=around,
                context_lines=context_lines,
            ),
        ).to_json()

    @server.tool()
    def events_summary(
        events_dir: str = ".verify-logs/events",
        limit: int = 10,
        summary: str = "summary",
    ) -> dict[str, object]:
        """Summarize local runtime events."""

        return tools.run_tool_request(
            tools.events_summary_request(
                events_dir=events_dir,
                limit=limit,
                summary=summary,
            ),
        ).to_json()

    @server.tool()
    def attention(target: str = ".", limit: int = 10) -> dict[str, object]:
        """Read the top attention-ranked files."""

        return tools.run_tool_request(
            tools.attention_request(target=target, limit=limit),
        ).to_json()

    @server.tool()
    def docsync_check(
        base: str = "origin/main",
        config: str | None = None,
        trace: str | None = None,
    ) -> dict[str, object]:
        """Run DocSync traceability checks."""

        return tools.run_tool_request(
            tools.docsync_check_request(base=base, config=config, trace=trace),
        ).to_json()

    return server


def _load_fastmcp() -> type[Any]:
    """Import FastMCP only when the optional server is actually started."""

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
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
