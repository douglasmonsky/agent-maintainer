"""Tests compatibility shims for standalone check modules."""

from __future__ import annotations

import subprocess
import sys

from guardrail_lib.checks import change_budget, file_lengths, structure, suppression_budget
from scripts import (
    check_change_budget,
    check_file_lengths,
    check_structure,
    check_suppression_budget,
)


def test_check_shims_alias_library_modules() -> None:
    """Expose moved check modules at the legacy import paths."""
    assert check_change_budget is change_budget
    assert check_file_lengths is file_lengths
    assert check_structure is structure
    assert check_suppression_budget is suppression_budget


def test_check_shims_keep_module_help_entrypoints() -> None:
    """Keep python -m scripts.check_* compatibility."""
    modules = (
        "scripts.check_change_budget",
        "scripts.check_file_lengths",
        "scripts.check_structure",
        "scripts.check_suppression_budget",
    )

    for module in modules:
        result = subprocess.run(
            [sys.executable, "-m", module, "--help"],
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0
        assert "usage:" in result.stdout
