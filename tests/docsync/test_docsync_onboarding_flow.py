"""Acceptance tests for the DocSync onboarding workflow."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from docsync import cli as docsync_cli

_EVIDENCE_PREFIX = "docsync:evidence"
_START_SUFFIX = "start"
_END_SUFFIX = "end"


# docsync:evidence.start evidence.docsync.onboarding_acceptance_test
def test_onboarding_flow_writes_packet(tmp_path: Path) -> None:
    """Trace authoring reaches an agent-readable review packet."""
    _write_demo_repo(tmp_path)

    _run_success(tmp_path, "init")
    _author_trace(tmp_path)
    _fill_evidence_region(tmp_path / "src" / "service.py", "evidence.demo.tax_total")
    _run_success(tmp_path, "doctor", "--fix")
    _run_success(tmp_path, "doctor")
    _commit_all(tmp_path)

    _replace_text(tmp_path / "src" / "service.py", "108", "109")

    assert _run_cli(tmp_path, "check", "--base", "HEAD") == 1
    assert _run_cli(tmp_path, "prompt", "--base", "HEAD") == 1

    _assert_packet_reviews_changed_evidence(_read_packet(tmp_path))
    _assert_prompt_mentions_trace_ids(tmp_path)


# docsync:evidence.end evidence.docsync.onboarding_acceptance_test


def _write_demo_repo(repo_root: Path) -> None:
    (repo_root / "src").mkdir()
    (repo_root / "README.md").write_text(
        "# Demo\n\nTax totals use the configured rate.\n",
        encoding="utf-8",
    )
    (repo_root / "src" / "service.py").write_text(
        "def tax_total(subtotal: int) -> int:\n    return subtotal * 108 // 100\n",
        encoding="utf-8",
    )


def _author_trace(repo_root: Path) -> None:
    _run_success(
        repo_root,
        "trace",
        "add-document",
        "docs.readme",
        "--path",
        "README.md",
        "--title",
        "Demo",
        "--audience",
        "users",
    )
    _run_success(
        repo_root,
        "trace",
        "add-object",
        "docs.readme.tax_total",
        "--document",
        "docs.readme",
        "--path",
        "README.md",
        "--marker",
        "docs.readme.tax_total",
        "--heading-level",
        "1",
        "--heading-text",
        "Demo",
        "--insert-marker",
    )
    _run_success(
        repo_root,
        "trace",
        "add-evidence",
        "evidence.demo.tax_total",
        "--path",
        "src/service.py",
        "--type",
        "code",
        "--description",
        "Tax total implementation",
        "--insert-region",
    )
    _run_success(
        repo_root,
        "trace",
        "add-claim",
        "claim.readme.tax_total",
        "--object",
        "docs.readme.tax_total",
        "--text",
        "README explains the supported tax total behavior.",
        "--severity",
        "high",
        "--evidence",
        "evidence.demo.tax_total",
    )


def _fill_evidence_region(path: Path, evidence_id: str) -> None:
    start = _evidence_marker(_START_SUFFIX, evidence_id)
    end = _evidence_marker(_END_SUFFIX, evidence_id)
    replacement = (
        f"{start}\ndef tax_total(subtotal: int) -> int:\n    return subtotal * 108 // 100\n{end}"
    )
    _replace_text(path, f"{start}\n{end}", replacement)


def _evidence_marker(suffix: str, evidence_id: str) -> str:
    return f"<!-- {_EVIDENCE_PREFIX}.{suffix} {evidence_id} -->"


def _replace_text(path: Path, old: str, new: str) -> None:
    path.write_text(
        path.read_text(encoding="utf-8").replace(old, new),
        encoding="utf-8",
    )


def _read_packet(repo_root: Path) -> dict[str, Any]:
    packet_path = repo_root / ".docsync" / "out" / "review-packet.json"
    return json.loads(packet_path.read_text(encoding="utf-8"))


def _assert_packet_reviews_changed_evidence(packet: dict[str, Any]) -> None:
    review = packet["reviews"][0]
    assert packet["findings"][0]["code"] == "DS201"
    assert review["claims"][0]["id"] == "claim.readme.tax_total"
    assert review["evidence"][0]["id"] == "evidence.demo.tax_total"
    assert "return subtotal * 109 // 100" in review["evidence"][0]["text"]
    assert "docsync attest claim.readme.tax_total" in review["suggested_actions"][1]


def _assert_prompt_mentions_trace_ids(repo_root: Path) -> None:
    prompt = (repo_root / ".docsync" / "out" / "review-prompt.md").read_text(
        encoding="utf-8",
    )
    assert "claim.readme.tax_total" in prompt
    assert "evidence.demo.tax_total" in prompt


def _run_success(repo_root: Path, *args: str) -> None:
    assert _run_cli(repo_root, *args) == 0


def _run_cli(repo_root: Path, *args: str) -> int:
    return docsync_cli.main(["--repo-root", str(repo_root), *args])


def _commit_all(repo_root: Path) -> None:
    _git(repo_root, "init")
    _git(repo_root, "add", ".")
    _git(
        repo_root,
        "-c",
        "user.name=DocSync Test",
        "-c",
        "user.email=docsync@example.invalid",
        "commit",
        "-m",
        "base",
    )


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ("git", *args),
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
