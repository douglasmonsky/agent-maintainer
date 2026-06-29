"""Tests advisory Hypothesis candidate guidance."""

from __future__ import annotations

import ast
import json
import subprocess
import textwrap
from pathlib import Path

import pytest

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.test_intel import (
    cli as test_intel_cli,
)
from agent_maintainer.test_intel import (
    hypothesis_candidates,
    hypothesis_reporting,
    hypothesis_scaffolds,
)
from agent_maintainer.test_intel.cli import main as run_test_intel_cli


def test_hypothesis_candidate_report_ranks_typed_branchy_boundaries(
    tmp_path: Path,
) -> None:
    """Typed branchy normalizers rank as Hypothesis candidates."""

    write_candidate_project(tmp_path)

    report = hypothesis_candidates.build_hypothesis_candidate_report(
        MaintainerConfig(source_roots=("src",), test_roots=("tests",)),
        tmp_path,
        changed_only=False,
    )

    assert report.candidates
    candidate = report.candidates[0]
    assert candidate.path == "src/example_pkg/score.py"
    assert candidate.qualname == "normalize_score"
    assert "typed function" in candidate.reasons
    assert any(reason.startswith("branch complexity") for reason in candidate.reasons)
    assert "numeric/string boundary behavior" in candidate.reasons
    assert candidate.suggested_scaffold[0].startswith("@given(")


def test_hypothesis_candidate_text_and_json_are_advisory(tmp_path: Path) -> None:
    """Candidate renderers include advisory note and stable JSON."""

    write_candidate_project(tmp_path)
    report = hypothesis_candidates.build_hypothesis_candidate_report(
        MaintainerConfig(source_roots=("src",), test_roots=("tests",)),
        tmp_path,
        changed_only=False,
    )

    text_output = hypothesis_reporting.render_text(report)
    payload = json.loads(hypothesis_reporting.render_json(report))

    assert "Hypothesis candidate: src/example_pkg/score.py::normalize_score" in text_output
    assert "not a verified contract" in text_output
    assert payload["candidates"][0]["path"] == "src/example_pkg/score.py"
    assert payload["note"] == hypothesis_candidates.ADVISORY_NOTE


def test_hypothesis_candidate_cli_outputs_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI command emits JSON without modifying source files."""

    write_candidate_project(tmp_path)
    before = source_text(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert run_test_intel_cli(["hypothesis-candidates", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["candidates"][0]["qualname"] == "normalize_score"
    assert source_text(tmp_path) == before


def test_hypothesis_candidate_cli_changed_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Changed mode limits candidates to changed source files."""

    write_candidate_project(tmp_path)
    create_git_repo(tmp_path)
    commit_all(tmp_path)
    source_path = tmp_path / "src" / "example_pkg" / "score.py"
    source_path.write_text(source_text(tmp_path).replace("100", "101"), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert run_test_intel_cli(["hypothesis-candidates", "--changed", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["changed_only"] is True
    assert payload["changed_source"] == ["src/example_pkg/score.py"]
    assert payload["candidates"][0]["path"] == "src/example_pkg/score.py"
    assert "recently changed" in payload["candidates"][0]["reasons"]


def test_hypothesis_candidate_cli_reports_changed_source_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Changed mode reports Git-diff errors."""

    write_candidate_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    def fail_changed_source(*_args: object, **_kwargs: object) -> tuple[str, ...]:
        raise RuntimeError("git failed")

    monkeypatch.setattr(test_intel_cli, "changed_source_paths", fail_changed_source)

    assert run_test_intel_cli(["hypothesis-candidates", "--changed"]) == 1
    assert "git failed" in capsys.readouterr().err


def test_hypothesis_candidate_discovery_skips_missing_and_cache_dirs(
    tmp_path: Path,
) -> None:
    """Source discovery skips missing roots and cache directories."""

    (tmp_path / "src" / "__pycache__").mkdir(parents=True)
    (tmp_path / "src" / "__pycache__" / "cached.py").write_text("", encoding="utf-8")
    (tmp_path / "src" / "module.py").write_text("", encoding="utf-8")

    paths = hypothesis_candidates.discover_source_files(
        MaintainerConfig(source_roots=("missing", "src")),
        tmp_path,
    )

    assert paths == ("src/module.py",)


def test_hypothesis_candidates_skip_unreadable_or_low_signal_sources(
    tmp_path: Path,
) -> None:
    """Malformed files and low-signal helpers do not become candidates."""

    source_path = tmp_path / "src" / "bad.py"
    source_path.parent.mkdir()
    source_path.write_text("def broken(:\n", encoding="utf-8")

    assert (
        hypothesis_candidates.candidates_for_source(
            "src/bad.py",
            tmp_path,
            changed=False,
            likely_test_count=0,
        )
        == ()
    )
    function = first_function("def helper():\n    return 1\n")
    assert (
        hypothesis_candidates.candidate_for_function(
            "src/helper.py",
            ("helper", function),
            changed=False,
            likely_test_count=2,
        )
        is None
    )


def test_hypothesis_candidates_collect_methods_and_side_effect_signals() -> None:
    """Candidate helpers cover method collection and impure call detection."""

    tree = ast.parse(
        textwrap.dedent(
            """
            class Parser:
                def normalize(self, value: int) -> int:
                    if value < 0:
                        return 0
                    return value

                def _private(self):
                    return 1
            """
        )
    )
    functions = hypothesis_candidates.iter_public_functions(tree)

    assert functions[0][0] == "Parser.normalize"
    assert len(functions) == 1
    assert not hypothesis_candidates.is_pureish(
        first_function("def write_item(items):\n    items.append(1)\n")
    )
    assert not hypothesis_candidates.is_pureish(
        first_function("def read_file(path):\n    with open(path):\n        return None\n")
    )
    assert (
        hypothesis_candidates.call_name(ast.Call(func=ast.Constant(value=1), args=[], keywords=[]))
        == ""
    )


def test_hypothesis_reporting_empty_changed_output() -> None:
    """Empty changed reports still explain advisory status."""

    report = hypothesis_candidates.HypothesisCandidateReport(
        changed_only=True,
        changed_source=(),
        candidates=(),
    )

    output = hypothesis_reporting.render_text(report)

    assert "Changed source:" in output
    assert "- <none>" in output
    assert "not a verified contract" in output
    assert hypothesis_reporting.render_changed_source(("src/pkg/module.py",)) == [
        "Changed source:",
        "- src/pkg/module.py",
        "",
    ]


def test_hypothesis_scaffolds_cover_generic_and_strategy_branches() -> None:
    """Scaffold helpers handle methods, strings, and missing annotations."""

    class_node = ast.parse(
        textwrap.dedent(
            """
            class Parser:
                def normalize(self, value: int) -> int:
                    return value
            """
        )
    ).body[0]
    assert isinstance(class_node, ast.ClassDef)
    method = class_node.body[0]
    assert isinstance(method, ast.FunctionDef)
    string_function = first_function("def parse_text(value: str) -> str:\n    return value\n")
    no_arg_function = first_function("def build_value():\n    return 1\n")
    untyped_function = first_function("def parse_value(value):\n    return value\n")

    assert hypothesis_scaffolds.required_argument_names(method) == ("value",)
    assert hypothesis_scaffolds.scaffold_lines("Parser.normalize", method)[0] == (
        "@given(data=st.data())"
    )
    assert hypothesis_scaffolds.preferred_strategy(string_function) == "st.text()"
    assert hypothesis_scaffolds.preferred_strategy(no_arg_function) == "st.data()"
    assert hypothesis_scaffolds.annotation_text(untyped_function.args.args[0].annotation) == ""


def first_function(source: str) -> ast.FunctionDef:
    """Return first function from source text."""

    node = ast.parse(textwrap.dedent(source).lstrip()).body[0]
    assert isinstance(node, ast.FunctionDef)
    return node


def write_candidate_project(path: Path) -> None:
    """Write a minimal project with one property-test candidate."""

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
    (path / "src" / "example_pkg" / "score.py").write_text(
        textwrap.dedent(
            """
        def normalize_score(value: int) -> float:
            if value < 0:
                return 0.0
            if value > 100:
                return 1.0
            if value == 50:
                return 0.5
            return value / 100
        """
        ).lstrip(),
        encoding="utf-8",
    )
    (path / "tests" / "test_score.py").write_text(
        "from example_pkg.score import normalize_score\n",
        encoding="utf-8",
    )


def source_text(path: Path) -> str:
    """Return candidate source text."""

    return (path / "src" / "example_pkg" / "score.py").read_text(encoding="utf-8")


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
