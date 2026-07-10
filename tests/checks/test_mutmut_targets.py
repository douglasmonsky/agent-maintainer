"""Tests Mutmut target ratchet checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.checks import mutmut_targets


def test_mutmut_target_ratchet_passes_when_floor_met(tmp_path: Path) -> None:
    """Configured path-like mutation targets count toward ratchet floor."""

    write_pyproject(
        tmp_path,
        """
        [tool.mutmut]
        only_mutate = [
          "src/package/config.py",
          "src/package/runtime.py",
        ]
        """,
    )
    write_source(tmp_path, "src/package/config.py")
    write_source(tmp_path, "src/package/runtime.py")

    issues = mutmut_targets.mutmut_target_issues(tmp_path, "pyproject.toml", 2)

    assert issues == ()


def test_mutmut_target_ratchet_fails_when_floor_not_met(tmp_path: Path) -> None:
    """Ratchet floor rejects shrinking the explicit mutation target list."""

    write_pyproject(
        tmp_path,
        """
        [tool.mutmut]
        only_mutate = ["src/package/runtime.py"]
        """,
    )
    write_source(tmp_path, "src/package/runtime.py")

    issues = mutmut_targets.mutmut_target_issues(tmp_path, "pyproject.toml", 2)

    assert issues == ("configured mutmut only_mutate targets 1 below required floor 2",)


def test_mutmut_target_ratchet_fails_missing_path_target(tmp_path: Path) -> None:
    """Path-like configured mutation targets must still exist."""

    write_pyproject(
        tmp_path,
        """
        [tool.mutmut]
        only_mutate = [
          "src/package/runtime.py",
          "src/package/missing.py",
        ]
        """,
    )
    write_source(tmp_path, "src/package/runtime.py")

    issues = mutmut_targets.mutmut_target_issues(tmp_path, "pyproject.toml", 2)

    assert issues == ("mutmut target path does not exist: src/package/missing.py",)


def test_mutmut_target_ratchet_fails_missing_also_copy_path(tmp_path: Path) -> None:
    """Concrete also_copy paths must exist before Mutmut runs."""

    write_pyproject(
        tmp_path,
        """
        [tool.mutmut]
        only_mutate = ["src/package/runtime.py"]
        also_copy = ["src/package/support"]
        """,
    )
    write_source(tmp_path, "src/package/runtime.py")

    issues = mutmut_targets.mutmut_target_issues(tmp_path, "pyproject.toml", 1)

    assert issues == ("mutmut also_copy path does not exist: src/package/support",)


def test_mutmut_target_ratchet_fails_missing_do_not_mutate_path(tmp_path: Path) -> None:
    """Concrete do_not_mutate paths must point at existing excluded files."""

    write_pyproject(
        tmp_path,
        """
        [tool.mutmut]
        only_mutate = ["src/package/runtime.py"]
        do_not_mutate = ["src/package/generated.py"]
        """,
    )
    write_source(tmp_path, "src/package/runtime.py")

    issues = mutmut_targets.mutmut_target_issues(tmp_path, "pyproject.toml", 1)

    assert issues == ("mutmut do_not_mutate path does not exist: src/package/generated.py",)


def test_mutmut_target_ratchet_rejects_unsupported_keys(tmp_path: Path) -> None:
    """Unsupported Mutmut config keys are probably ignored by Mutmut."""

    write_pyproject(
        tmp_path,
        """
        [tool.mutmut]
        only_mutate = ["src/package/runtime.py"]
        cache_invalidation_files = ["pyproject.toml"]
        """,
    )
    write_source(tmp_path, "src/package/runtime.py")

    issues = mutmut_targets.mutmut_target_issues(tmp_path, "pyproject.toml", 1)

    assert issues == ("unsupported mutmut config key: cache_invalidation_files",)


def test_mutmut_target_ratchet_ignores_non_path_patterns(tmp_path: Path) -> None:
    """Module-like and glob targets count but are not filesystem path checked."""

    write_pyproject(
        tmp_path,
        """
        [tool.mutmut]
        only_mutate = [
          "package.runtime*",
          "src/package/*.py",
        ]
        """,
    )

    issues = mutmut_targets.mutmut_target_issues(tmp_path, "pyproject.toml", 2)

    assert issues == ()


def test_mutmut_target_ratchet_main_reports_issues(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI prints ratchet issues and exits nonzero."""

    monkeypatch.chdir(tmp_path)
    write_pyproject(
        tmp_path,
        """
        [tool.mutmut]
        only_mutate = []
        """,
    )

    assert mutmut_targets.main(["--min-targets", "1"]) == 1

    assert (
        "configured mutmut only_mutate targets 0 below required floor 1" in capsys.readouterr().out
    )


def test_mutmut_target_ratchet_main_reports_success(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI prints a compact pass message."""

    monkeypatch.chdir(tmp_path)
    write_pyproject(
        tmp_path,
        """
        [tool.mutmut]
        only_mutate = ["src/package/runtime.py"]
        """,
    )
    write_source(tmp_path, "src/package/runtime.py")

    assert mutmut_targets.main(["--min-targets", "1"]) == 0

    assert "mutmut target ratchet passed: 1 target floor" in capsys.readouterr().out


def test_mutmut_target_ratchet_zero_floor_is_disabled(tmp_path: Path) -> None:
    """Zero target floor disables the ratchet."""

    issues = mutmut_targets.mutmut_target_issues(tmp_path, "missing.toml", 0)

    assert issues == ()


def test_mutmut_target_ratchet_handles_missing_or_invalid_pyproject(tmp_path: Path) -> None:
    """Missing and malformed pyproject files behave as empty target config."""

    assert mutmut_targets.mutmut_target_issues(tmp_path, "missing.toml", 1) == (
        "configured mutmut only_mutate targets 0 below required floor 1",
    )

    tmp_path.joinpath("pyproject.toml").write_text("[tool.mutmut", encoding="utf-8")

    assert mutmut_targets.mutmut_target_issues(tmp_path, "pyproject.toml", 1) == (
        "configured mutmut only_mutate targets 0 below required floor 1",
    )


def test_explicit_mutation_targets_ignores_malformed_tables() -> None:
    """Malformed tool/mutmut tables return no explicit targets."""

    assert mutmut_targets.explicit_mutation_targets({"tool": []}) == ()
    assert mutmut_targets.explicit_mutation_targets({"tool": {"mutmut": []}}) == ()
    assert (
        mutmut_targets.explicit_mutation_targets(
            {"tool": {"mutmut": {"only_mutate": "src/package/runtime.py"}}},
        )
        == ()
    )


def write_pyproject(path: Path, content: str) -> None:
    """Write a minimal pyproject fixture."""

    path.joinpath("pyproject.toml").write_text(content.strip(), encoding="utf-8")


def write_source(path: Path, relative: str) -> None:
    """Write a placeholder source file."""

    source_path = path / relative
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("def example() -> int:\n    return 1\n", encoding="utf-8")
