"""Tests identity-aware hook configuration merging."""

import json
from pathlib import Path

from agent_client_hooks import merge, templates


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


def _entry(command: str) -> dict[str, object]:
    """Return one synthetic Claude hook event entry."""

    return {"hooks": [{"type": "command", "command": command}]}
