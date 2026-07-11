"""Tests safe file context command behavior."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_context.reading.files import (
    FileRequest,
    render_file_json,
    render_file_text,
    select_file_context,
)
from agent_maintainer.context import cli as context_cli

ONE_CONTEXT_LINE = 1
AROUND_LINE = 3
AROUND_START_LINE = 2
AROUND_END_LINE = 4

PYTHON_SAMPLE = '''@decorator
class Example:
    """Example docs."""

    def method(self):
        """Method docs."""
        return 1


def top_level():
    return Example()
'''


def test_symbol_context_extracts_named_method(tmp_path: Path) -> None:
    """File context can extract a named symbol."""

    path = write_python(tmp_path)

    context = select_file_context(
        FileRequest(path=path, symbol="Example.method", workspace_root=tmp_path),
    )

    assert context.mode == "symbol"
    assert context.start_line is not None
    assert "def method" in context.text
    assert "top_level" not in context.text


def test_default_python_file_context_returns_outline(tmp_path: Path) -> None:
    """Default Python file context returns outline rather than whole file."""

    path = write_python(tmp_path)

    context = select_file_context(FileRequest(path=path, workspace_root=tmp_path))

    assert context.mode == "outline"
    assert "Python outline:" in context.text
    assert "decorators=decorator" in context.text
    assert "docstring_line=" in context.text


def test_non_python_file_context_returns_line_summary(tmp_path: Path) -> None:
    """Non-Python outline mode returns a simple line summary."""

    path = tmp_path / "notes.txt"
    path.write_text("one\ntwo", encoding="utf-8")

    context = select_file_context(FileRequest(path=path, workspace_root=tmp_path))

    assert context.mode == "outline"
    assert context.text == "File lines: 2"


def test_missing_symbol_returns_bounded_message(tmp_path: Path) -> None:
    """Missing symbol requests return a bounded message."""

    path = write_python(tmp_path)

    context = select_file_context(
        FileRequest(path=path, symbol="Missing", workspace_root=tmp_path),
    )

    assert context.mode == "symbol"
    assert context.text == "Symbol not found: Missing"


def test_line_and_around_context_are_bounded(tmp_path: Path) -> None:
    """Line and around selections return requested slices."""

    path = write_python(tmp_path)

    line_context = select_file_context(
        FileRequest(path=path, line_range="1:2", workspace_root=tmp_path),
    )
    around_context = select_file_context(
        FileRequest(
            path=path,
            around=AROUND_LINE,
            context_lines=ONE_CONTEXT_LINE,
            workspace_root=tmp_path,
        ),
    )

    assert line_context.text == "@decorator\nclass Example:"
    assert around_context.start_line == AROUND_START_LINE
    assert around_context.end_line == AROUND_END_LINE


def test_file_renderers_include_metadata(tmp_path: Path) -> None:
    """File renderers include metadata and JSON payloads."""

    path = write_python(tmp_path)
    context = select_file_context(
        FileRequest(path=path, line_range="1:2", workspace_root=tmp_path),
    )

    text_output = render_file_text(context)
    json_output = json.loads(render_file_json(context))

    assert "Lines: 1:2" in text_output
    assert json_output["mode"] == "lines"


def test_refused_file_context_returns_message(tmp_path: Path) -> None:
    """File context returns refused result instead of contents."""

    path = tmp_path / "data.bin"
    path.write_bytes(b"abc\x00def")

    context = select_file_context(
        FileRequest(path=path, outline=True, workspace_root=tmp_path),
    )

    assert context.refused is True
    assert "Refused file context" in context.text


def test_file_context_refuses_workspace_escape(tmp_path: Path) -> None:
    """Default file selection cannot expand a file outside its workspace root."""

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.py"
    secret = "OUTSIDE-CONTEXT-CANARY"
    outside.write_text(secret, encoding="utf-8")

    context = select_file_context(
        FileRequest(path=Path("../outside.py"), workspace_root=workspace),
    )

    assert context.refused is True
    assert context.reason == "path escapes workspace root"
    assert secret not in context.text


def test_file_cli_outputs_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """File subcommand emits JSON output."""

    path = write_python(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert context_cli.main(["file", str(path), "--symbols", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "symbols"
    assert payload["refused"] is False


def write_python(tmp_path: Path) -> Path:
    """Write Python source fixture."""

    path = tmp_path / "sample.py"
    path.write_text(PYTHON_SAMPLE, encoding="utf-8")
    return path
