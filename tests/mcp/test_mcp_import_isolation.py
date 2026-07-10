"""Tests Python import isolation for MCP child processes."""

from pathlib import Path

import pytest

from agent_maintainer.mcp import tools
from docsync.config.defaults import DEFAULT_CONFIG_TEXT

ENCODING = "utf-8"


@pytest.mark.parametrize("shadow_kind", ("file", "package"))
def test_agent_child_ignores_workspace_shadow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    shadow_kind: str,
) -> None:
    """An MCP context child imports only the trusted Agent Maintainer package."""

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "source.py").write_text("value = 1\n", encoding=ENCODING)
    canary = tmp_path / "outside-canary.txt"
    canary.write_text("unchanged\n", encoding=ENCODING)
    _write_module_shadow(workspace, "agent_maintainer", shadow_kind, canary)
    monkeypatch.setenv("PYTHONPATH", ".:src")

    result = tools.run_tool_request(
        tools.context_file_request(
            workspace_root=workspace,
            options=tools.ContextFileRequestOptions(path="source.py", lines="1:1"),
        ),
        cwd=workspace,
    )

    assert result.returncode == 0
    assert "MALICIOUS-SHADOW" not in result.stdout
    assert canary.read_text(encoding=ENCODING) == "unchanged\n"


@pytest.mark.parametrize("shadow_kind", ("file", "package"))
def test_docsync_child_ignores_workspace_shadow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    shadow_kind: str,
) -> None:
    """An MCP DocSync child imports only the trusted DocSync package."""

    workspace = tmp_path / "workspace"
    docsync_root = workspace / ".docsync"
    docsync_root.mkdir(parents=True)
    (docsync_root / "config.yml").write_text(DEFAULT_CONFIG_TEXT, encoding=ENCODING)
    (docsync_root / "trace.yml").write_text(
        "version: 1\ndocuments: {}\nobjects: {}\nclaims: {}\nevidence: {}\n",
        encoding=ENCODING,
    )
    canary = tmp_path / "outside-canary.txt"
    canary.write_text("unchanged\n", encoding=ENCODING)
    _write_module_shadow(workspace, "docsync", shadow_kind, canary)
    monkeypatch.setenv("PYTHONPATH", ".:src")

    result = tools.run_tool_request(
        tools.docsync_check_request(
            workspace_root=workspace,
            base="HEAD",
            config=".docsync/config.yml",
            trace=".docsync/trace.yml",
        ),
        cwd=workspace,
    )

    assert "MALICIOUS-SHADOW" not in result.stdout
    assert canary.read_text(encoding=ENCODING) == "unchanged\n"


def _write_module_shadow(
    workspace: Path,
    module_name: str,
    shadow_kind: str,
    canary: Path,
) -> None:
    """Write a synthetic checkout-level Python module shadow."""

    content = "\n".join(
        (
            "from pathlib import Path",
            f"Path({str(canary)!r}).write_text('SHADOWED\\n', encoding='utf-8')",
            "print('MALICIOUS-SHADOW')",
        )
    )
    if shadow_kind == "file":
        (workspace / f"{module_name}.py").write_text(content, encoding=ENCODING)
        return
    package = workspace / module_name
    package.mkdir()
    (package / "__init__.py").write_text("", encoding=ENCODING)
    (package / "__main__.py").write_text(content, encoding=ENCODING)
