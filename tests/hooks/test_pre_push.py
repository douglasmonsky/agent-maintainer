"""Tests for exact outgoing-ref pre-push verification."""

from __future__ import annotations

import importlib
import subprocess
from pathlib import Path

import pytest

from agent_maintainer.checks import change_budget


def git(repo_root: Path, *args: str) -> str:
    """Run Git in a temporary repository and return stdout."""

    result = subprocess.run(  # nosec B603
        ("git", "-C", str(repo_root), *args),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def test_pre_push_inspects_committed_source_since_remote_ref(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A source-only outgoing commit must reach the complete diff gate."""

    repo_root = tmp_path / "repo"
    source = repo_root / "src" / "example.py"
    test = repo_root / "tests" / "test_example.py"
    source.parent.mkdir(parents=True)
    test.parent.mkdir(parents=True)
    git(repo_root.parent, "init", "-b", "main", str(repo_root))
    git(repo_root, "config", "user.email", "test@example.invalid")
    git(repo_root, "config", "user.name", "Test User")
    source.write_text("VALUE = 1\n", encoding="utf-8")
    test.write_text("def test_value() -> None:\n    assert True\n", encoding="utf-8")
    git(repo_root, "add", "src/example.py", "tests/test_example.py")
    git(repo_root, "commit", "-m", "baseline")
    from_ref = git(repo_root, "rev-parse", "HEAD")
    source.write_text("VALUE = 2\n", encoding="utf-8")
    git(repo_root, "add", "src/example.py")
    git(repo_root, "commit", "-m", "source only")
    to_ref = git(repo_root, "rev-parse", "HEAD")
    monkeypatch.chdir(repo_root)
    pre_push = importlib.import_module("agent_maintainer.hooks.pre_push")

    def run_verify(argv: list[str]) -> int:
        base_ref = argv[argv.index("--base-ref") + 1]
        compare_branch = argv[argv.index("--compare-branch") + 1]
        assert base_ref == from_ref
        assert compare_branch == from_ref
        return change_budget.main(
            [
                base_ref,
                "--source-root",
                "src",
                "--test-root",
                "tests",
                "--missing-test-change-as-error",
            ]
        )

    status = pre_push.run_pre_push(
        {
            "PRE_COMMIT_FROM_REF": from_ref,
            "PRE_COMMIT_TO_REF": to_ref,
        },
        verifier=run_verify,
    )

    assert status == 1


def test_pre_push_requires_exact_refs_without_invoking_verifier(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A ref-less manual stage run fails closed with an actionable message."""

    pre_push = importlib.import_module("agent_maintainer.hooks.pre_push")

    def fail_verify(_argv: list[str]) -> int:
        pytest.fail("verifier must not run without exact push refs")

    assert pre_push.run_pre_push({}, verifier=fail_verify) == pre_push.USAGE_ERROR_STATUS
    assert "requires PRE_COMMIT_FROM_REF" in capsys.readouterr().err


def test_pre_push_refuses_non_head_local_ref_without_invoking_verifier(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A pushed SHA other than checked-out HEAD must fail closed."""

    pre_push = importlib.import_module("agent_maintainer.hooks.pre_push")
    monkeypatch.setattr(
        pre_push.fingerprint_inputs,
        "git_output",
        lambda *_args: "checked-out-head\n",
    )

    def fail_verify(_argv: list[str]) -> int:
        pytest.fail("verifier must not run for a non-HEAD local ref")

    status = pre_push.run_pre_push(
        {
            "PRE_COMMIT_FROM_REF": "remote-sha",
            "PRE_COMMIT_TO_REF": "other-local-sha",
        },
        verifier=fail_verify,
    )

    assert status == pre_push.USAGE_ERROR_STATUS
    assert "expected other-local-sha, found checked-out-head" in capsys.readouterr().err
