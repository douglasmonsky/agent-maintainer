"""Tests verifier result summary helpers."""

from __future__ import annotations

from agent_maintainer.models import CheckResult
from agent_maintainer.verify import result_summary


def test_smallest_rerun_command_uses_single_failed_check_command() -> None:
    """One failed check can rerun exactly that check command."""

    command = result_summary.smallest_rerun_command(
        "precommit",
        [
            CheckResult(
                "ruff",
                passed=False,
                command=("python", "-m", "ruff", "check", "src path"),
            )
        ],
    )

    assert command == "python -m ruff check 'src path'"


def test_smallest_rerun_command_falls_back_to_profile_for_multiple_failures() -> None:
    """Multiple failures should rerun the selected verifier profile."""

    command = result_summary.smallest_rerun_command(
        "full",
        [
            CheckResult("ruff", passed=False, command=("ruff", "check")),
            CheckResult("pyright", passed=False, command=("pyright",)),
        ],
    )

    assert command == "python3 -m agent_maintainer verify --profile full"


def test_smallest_rerun_command_falls_back_without_check_command() -> None:
    """Synthetic failures without command metadata rerun verifier profile."""

    command = result_summary.smallest_rerun_command(
        "ci",
        [CheckResult("maintainer-layout", passed=False)],
    )

    assert command == "python3 -m agent_maintainer verify --profile ci"
