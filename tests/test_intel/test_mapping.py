"""Tests changed-source to test-file mapping."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.test_intel.mapping import likely_tests_for_changes


def test_likely_tests_rank_by_name_and_imports(tmp_path: Path) -> None:
    """Likely tests are ranked by confidence and stable path order."""

    write_file(
        tmp_path / "tests/checks/test_change_budget.py",
        "import agent_maintainer.checks.change_budget\n",
    )
    write_file(
        tmp_path / "tests/checks/test_other.py",
        "import agent_maintainer.checks.change_budget\n",
    )
    write_file(
        tmp_path / "tests/checks/test_domain_only.py",
        "def test_domain() -> None:\n    pass\n",
    )
    write_file(
        tmp_path / "tests/catalogs/test_catalog.py",
        "def test_catalog() -> None:\n    pass\n",
    )

    matches = likely_tests_for_changes(
        ("src/agent_maintainer/checks/change_budget.py",),
        MaintainerConfig(source_roots=("src",), test_roots=("tests",)),
        tmp_path,
    )

    assert [match.test_path for match in matches] == [
        "tests/checks/test_change_budget.py",
        "tests/checks/test_other.py",
        "tests/checks/test_domain_only.py",
    ]
    assert matches[0].confidence == "high"
    assert matches[0].reasons == (
        "naming match",
        "imports changed module",
        "same package/domain",
    )
    assert matches[1].confidence == "medium"
    assert matches[2].confidence == "low"


def write_file(path: Path, text: str) -> None:
    """Write a test fixture file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
