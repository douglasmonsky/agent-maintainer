"""Tests surgical context expansion command ranking."""

from __future__ import annotations

from agent_context.next_actions import next_action_commands
from agent_context.pack_rendering import render_pack_pointer


def test_next_action_prefers_exact_file_line_before_broad_fallback() -> None:
    """Line-level repair facts should be the first expansion command."""

    commands = next_action_commands(
        [
            {
                "check": "pyright",
                "path": "src/pkg/app.py",
                "line": 42,
                "message": "Type mismatch",
            }
        ],
        ["python -m agent_maintainer context failures --limit 20"],
    )

    assert commands[0] == (
        "python -m agent_maintainer context file src/pkg/app.py --around 42 --context 30"
    )
    assert commands[1] == "python -m agent_maintainer context failures --limit 20"


def test_next_action_prefers_file_outline_when_fact_has_path_only() -> None:
    """Path-only repair facts should inspect the file outline first."""

    commands = next_action_commands(
        [{"check": "ruff", "path": "src/pkg/app.py", "line": None}],
        ["python -m agent_maintainer context pack --budget 2200"],
    )

    assert commands[0] == "python -m agent_maintainer context file src/pkg/app.py --outline"


def test_next_action_uses_check_specific_failure_and_log_when_no_path() -> None:
    """Check-only facts should stay narrower than broad failure expansion."""

    commands = next_action_commands(
        [{"check": "docsync", "message": "Trace drift"}],
        ["python -m agent_maintainer context failures --limit 20"],
    )

    assert commands[:2] == [
        "python -m agent_maintainer context failures --check docsync --limit 3",
        "python -m agent_maintainer context log docsync --tail 80",
    ]


def test_rendered_pointer_uses_ranked_commands_for_likely_action() -> None:
    """Hook-safe pointer output should surface the surgical command first."""

    pointer = render_pack_pointer(
        {
            "exact_repair_facts": [
                {
                    "check": "pyright",
                    "path": "src/pkg/app.py",
                    "line": 7,
                    "message": "Bad assignment",
                }
            ],
            "expansion_commands": ["python -m agent_maintainer context failures --limit 20"],
        },
        display_path=".verify-logs/context/PACK.md",
    )

    assert (
        "Likely next action:\n"
        "python -m agent_maintainer context file src/pkg/app.py "
        "--around 7 --context 30"
    ) in pointer
    assert "Expand only if needed:" in pointer
