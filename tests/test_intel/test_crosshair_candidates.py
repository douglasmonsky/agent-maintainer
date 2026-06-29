"""Tests advisory CrossHair candidate guidance."""

from __future__ import annotations

import ast
import json
import subprocess
import textwrap
from pathlib import Path

import pytest

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.test_intel import (
    cli as maintainer_test_intel_cli,
)
from agent_maintainer.test_intel import crosshair_candidates, crosshair_reporting
from agent_maintainer.test_intel.cli import main as run_test_intel_cli


def test_crosshair_candidate_report_includes_typed_contracts(tmp_path: Path) -> None:
    """Typed bounded functions with visible contracts become candidates."""

    write_candidate_project(tmp_path)
    report = crosshair_candidates.build_crosshair_candidate_report(
        crosshair_candidates.CrosshairCandidateRequest(
            config=MaintainerConfig(source_roots=("src",), test_roots=("tests",)),
            repo_root=tmp_path,
            changed_only=False,
        )
    )

    assert report.candidates
    candidate = report.candidates[0]
    assert candidate.path == "src/example_pkg/contracts.py"
    assert candidate.qualname == "clamp_score"
    assert candidate.contract == "assert"
    assert "fully typed function" in candidate.reasons
    assert "small bounded body" in candidate.reasons
    assert candidate.suggested_command == "crosshair check src/example_pkg/contracts.py"


def test_crosshair_candidate_renderers_are_advisory(tmp_path: Path) -> None:
    """Text and JSON output make clear CrossHair is not run."""

    write_candidate_project(tmp_path)
    report = crosshair_candidates.build_crosshair_candidate_report(
        crosshair_candidates.CrosshairCandidateRequest(
            config=MaintainerConfig(source_roots=("src",), test_roots=("tests",)),
            repo_root=tmp_path,
            changed_only=False,
        )
    )

    text_output = crosshair_reporting.render_text(report)
    payload = json.loads(crosshair_reporting.render_json(report))

    assert "CrossHair candidates" in text_output
    assert "does not run CrossHair" in text_output
    assert payload["note"] == crosshair_candidates.ADVISORY_NOTE
    assert payload["candidates"][0]["suggested_command"].startswith("crosshair check")


def test_crosshair_candidates_exclude_unsafe_functions(tmp_path: Path) -> None:
    """Obvious IO and untyped functions are not candidates."""

    write_candidate_project(tmp_path)
    report = crosshair_candidates.build_crosshair_candidate_report(
        crosshair_candidates.CrosshairCandidateRequest(
            config=MaintainerConfig(source_roots=("src",), test_roots=("tests",)),
            repo_root=tmp_path,
            changed_only=False,
        )
    )

    qualnames = {candidate.qualname for candidate in report.candidates}
    assert "write_score" not in qualnames
    assert "untyped_score" not in qualnames
    assert "loop_forever" not in qualnames


def test_crosshair_changed_cli_reports_candidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Changed-source CLI output can focus CrossHair candidates."""

    write_candidate_project(tmp_path)
    create_git_repo(tmp_path)
    commit_all(tmp_path)
    source_file = tmp_path / "src" / "example_pkg" / "contracts.py"
    source_file.write_text(
        source_text(tmp_path).replace("return value", "return int(value)", 1),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert run_test_intel_cli(["crosshair-candidates", "--changed"]) == 0
    assert run_test_intel_cli(["crosshair-candidates", "--changed", "--format", "json"]) == 0


def test_crosshair_cli_reports_changed_source_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Changed-source discovery failures produce CLI errors."""

    write_candidate_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    def fail_changed_source(*_args: object, **_kwargs: object) -> tuple[str, ...]:
        raise RuntimeError("git failed")

    monkeypatch.setattr(maintainer_test_intel_cli, "changed_source_paths", fail_changed_source)

    assert run_test_intel_cli(["crosshair-candidates", "--changed"]) == 1
    assert "git failed" in capsys.readouterr().err


def test_crosshair_helpers_cover_contract_and_safety_branches(tmp_path: Path) -> None:
    """Helpers handle malformed inputs and contract detection variants."""

    malformed_source = tmp_path / "src" / "bad.py"
    malformed_source.parent.mkdir()
    malformed_source.write_text("def broken(:\n", encoding="utf-8")
    docstring_function = first_function(
        '''
        def normalize(value: int) -> int:
            """pre: value >= 0
            post: result >= 0
            """
            return value
        '''
    )
    decorator_function = first_function(
        """
        @icontract.require(lambda value: value >= 0)
        def normalize(value: int) -> int:
            return value
        """
    )
    constant_call = ast.Call(func=ast.Constant(value=1), args=[], keywords=[])

    assert (
        crosshair_candidates.candidates_for_source(
            "src/bad.py",
            tmp_path,
            changed=False,
        )
        == ()
    )
    assert crosshair_candidates.contract_style(docstring_function) == "docstring"
    assert crosshair_candidates.contract_style(decorator_function) == "icontract"
    assert not crosshair_candidates.is_safe_for_crosshair(
        first_function("def run(value: int) -> int:\n    global state\n    return value\n")
    )
    assert crosshair_candidates.expression_name(constant_call) == ""
    assert (
        crosshair_candidates.candidate_for_function(
            "src/low.py",
            ("plain", first_function("def plain(value: int) -> int:\n    return value\n")),
            changed=False,
        )
        is None
    )


def test_crosshair_reporting_empty_changed_output() -> None:
    """Empty changed reports still explain advisory status."""

    report = crosshair_candidates.CrosshairCandidateReport(
        changed_only=True,
        changed_source=(),
        candidates=(),
    )
    output = crosshair_reporting.render_text(report)

    assert "Changed source:" in output
    assert "- <none>" in output
    assert "does not run CrossHair" in output
    assert crosshair_reporting.render_changed_source(("src/pkg/module.py",)) == [
        "Changed source:",
        "- src/pkg/module.py",
        "",
    ]


def first_function(source: str) -> ast.FunctionDef:
    """Return first function from source text."""

    tree = ast.parse(textwrap.dedent(source).lstrip())
    function = tree.body[0]
    assert isinstance(function, ast.FunctionDef)
    return function


def write_candidate_project(path: Path) -> None:
    """Write a small project with CrossHair candidate examples."""

    (path / "src" / "example_pkg").mkdir(parents=True)
    (path / "tests").mkdir()
    (path / "pyproject.toml").write_text(
        textwrap.dedent(
            """
            [tool.agent_maintainer]
            source_roots = ["src"]
            test_roots = ["tests"]
            """
        ).lstrip(),
        encoding="utf-8",
    )
    (path / "src" / "example_pkg" / "contracts.py").write_text(
        textwrap.dedent(
            """
            def clamp_score(value: int) -> int:
                assert value >= -100
                if value < 0:
                    return 0
                if value > 100:
                    return 100
                return value


            def write_score(path: str, value: int) -> int:
                assert value >= 0
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(str(value))
                return value


            def untyped_score(value):
                assert value >= 0
                return value


            def loop_forever(value: int) -> int:
                assert value >= 0
                while value >= 0:
                    value += 1
                return value
            """
        ).lstrip(),
        encoding="utf-8",
    )
    (path / "tests" / "test_contracts.py").write_text(
        "from example_pkg.contracts import clamp_score\n",
        encoding="utf-8",
    )


def source_text(path: Path) -> str:
    """Return candidate source text."""

    return (path / "src" / "example_pkg" / "contracts.py").read_text(encoding="utf-8")


def create_git_repo(path: Path) -> None:
    """Initialize Git fixture repo."""

    run_git(path, "init")
    run_git(path, "config", "user.email", "agent-maintainer@example.com")
    run_git(path, "config", "user.name", "Agent Maintainer")


def commit_all(path: Path) -> None:
    """Commit fixture files."""

    run_git(path, "add", "pyproject.toml", "src", "tests")
    run_git(path, "commit", "-m", "initial")


def run_git(path: Path, *args: str) -> None:
    """Run Git in fixture repository."""

    subprocess.run(["git", *args], cwd=path, check=True, capture_output=True, text=True)
