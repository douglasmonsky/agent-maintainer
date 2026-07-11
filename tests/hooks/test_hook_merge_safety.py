"""Tests identity-aware hook configuration merging."""

import json
from pathlib import Path

from agent_client_hooks import merge, removal, templates
from agent_maintainer.core.structured_values import json_array, json_object


def test_claude_merge_preserves_third_party_hooks_and_order(tmp_path: Path) -> None:
    """Managed replacement leaves unrelated entries in every event untouched."""

    settings = tmp_path / "settings.json"
    third_before = _entry("third-before")
    third_after = _entry("third-after")
    old_managed = _entry(
        'python3 "$(git rev-parse --show-toplevel)/.claude/hooks/stop.py"',
    )
    custom_event = [_entry("custom-event")]
    current = {
        "theme": "dark",
        "hooks": {
            "PostToolUse": [third_before, old_managed, third_after],
            "Stop": [third_before, old_managed, third_after],
            "SubagentStop": [third_before, old_managed, third_after],
            "Notification": custom_event,
        },
    }
    settings.write_text(json.dumps(current), encoding="utf-8")

    rendered = merge.merge_claude_settings(settings, templates.claude_settings())
    payload = json.loads(rendered)
    managed = json.loads(templates.claude_settings())["hooks"]

    assert payload["theme"] == "dark"
    assert payload["hooks"]["Notification"] == custom_event
    for event in ("PostToolUse", "Stop", "SubagentStop"):
        assert payload["hooks"][event] == [
            third_before,
            *managed[event],
            third_after,
        ]


def test_claude_merge_is_idempotent_with_coexisting_hooks(tmp_path: Path) -> None:
    """A second managed merge preserves byte-for-byte JSON output."""

    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps({"hooks": {"Stop": [_entry("third-party")]}}),
        encoding="utf-8",
    )
    managed = templates.claude_settings()
    first = merge.merge_claude_settings(settings, managed)
    settings.write_text(first, encoding="utf-8")

    assert merge.merge_claude_settings(settings, managed) == first


def test_merge_keeps_valid_hooks_beside_malformed(tmp_path: Path) -> None:
    """Malformed neighboring values cannot hide a valid third-party hook."""

    settings = tmp_path / "settings.json"
    third_party = _entry("third-party")
    settings.write_text(
        json.dumps({"hooks": {"Stop": [None, third_party]}}),
        encoding="utf-8",
    )

    rendered = merge.merge_claude_settings(settings, templates.claude_settings())
    entries = json.loads(rendered)["hooks"]["Stop"]

    assert third_party in entries


def test_claude_merge_preserves_hook_sharing_managed_matcher(tmp_path: Path) -> None:
    """A third-party command survives inside an otherwise managed matcher."""

    settings = tmp_path / "settings.json"
    mixed = {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
            {"type": "command", "command": ".claude/hooks/post_tool_use.py"},
            {"type": "command", "command": "third-party"},
        ],
    }
    settings.write_text(json.dumps({"hooks": {"PostToolUse": [mixed]}}), encoding="utf-8")

    rendered = merge.merge_claude_settings(settings, templates.claude_settings())
    entries = json.loads(rendered)["hooks"]["PostToolUse"]

    assert any(_commands(entry) == ["third-party"] for entry in entries)


def test_remove_claude_settings_preserves_unrelated_and_mixed_hooks() -> None:
    """Uninstall removes managed commands at their narrowest object boundary."""

    mixed = {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
            {"type": "command", "command": ".claude/hooks/post_tool_use.py"},
            {"type": "command", "command": "third-party"},
        ],
    }
    current = json.dumps(
        {"theme": "dark", "hooks": {"PostToolUse": [mixed], "Notification": [_entry("notify")]}}
    )

    payload = json.loads(removal.remove_claude_settings(current))

    assert payload["theme"] == "dark"
    assert payload["hooks"]["Notification"] == [_entry("notify")]
    assert _commands(payload["hooks"]["PostToolUse"][0]) == ["third-party"]


def test_remove_codex_config_preserves_unrelated_sections() -> None:
    """Uninstall strips only the marked Codex block."""

    current = f"[other]\nvalue = true\n\n{templates.codex_config_block()}"

    assert removal.remove_codex_config(current) == "[other]\nvalue = true\n"


def _entry(command: str) -> dict[str, object]:
    """Return one synthetic Claude hook event entry."""

    return {"hooks": [{"type": "command", "command": command}]}


def _commands(entry: dict[str, object]) -> list[object]:
    """Return commands from one synthetic Claude event entry."""

    hooks = json_array(entry["hooks"])
    assert hooks is not None
    commands: list[object] = []
    for raw_hook in hooks:
        hook = json_object(raw_hook)
        if hook is not None and "command" in hook:
            commands.append(hook["command"])
    return commands
