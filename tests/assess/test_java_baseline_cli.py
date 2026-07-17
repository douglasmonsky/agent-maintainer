"""Tests explicit Java findings baseline lifecycle commands."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import cast

import pytest

from agent_maintainer.assess import cli
from agent_maintainer.ecosystems.java import baseline
from agent_maintainer.ecosystems.java.findings import JavaFinding

BASELINE_PATH = ".agent-maintainer/java-findings-baseline.json"
ARTIFACT_PATH = ".verify-logs/java-gradle/java-gradle-static.json"
ENCODING = "utf-8"
EXPECTED_INITIAL_ENTRIES = 2


# docsync:evidence.start evidence.java.structured_evidence_tests
def test_create_dry_run_and_write_are_deterministic(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Dry-run renders the exact baseline and create writes it once."""
    repo = initialized_repo(tmp_path)
    source_commit = git(repo, "rev-parse", "HEAD")
    artifact = write_artifact(repo, source_commit, (finding_payload("RuleOne"),))

    dry_status = cli.main(java_command("create", repo, artifact, "--dry-run"))
    dry_output = capsys.readouterr().out

    assert dry_status == 0
    assert not (repo / BASELINE_PATH).exists()
    assert f'"source_commit": "{source_commit}"' in dry_output

    assert cli.main(java_command("create", repo, artifact)) == 0
    written_output = capsys.readouterr().out
    baseline_path = repo / BASELINE_PATH
    assert baseline_path.read_text(encoding=ENCODING) == dry_output
    assert written_output == dry_output


def test_inspect_and_prune_have_explicit_read_write_boundaries(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Inspect is read-only and prune changes only an existing baseline."""
    repo = initialized_repo(tmp_path)
    source_commit = git(repo, "rev-parse", "HEAD")
    initial_artifact = write_artifact(
        repo,
        source_commit,
        (finding_payload("RuleOne"), finding_payload("RuleTwo")),
    )
    assert cli.main(java_command("create", repo, initial_artifact)) == 0
    capsys.readouterr()
    baseline_path = repo / BASELINE_PATH
    before_inspect = baseline_path.read_bytes()

    assert cli.main(java_command("inspect", repo, None, "--json")) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["entry_count"] == EXPECTED_INITIAL_ENTRIES
    assert baseline_path.read_bytes() == before_inspect

    git(repo, "add", BASELINE_PATH)
    git(repo, "commit", "-m", "record baseline")
    prune_source_commit = git(repo, "rev-parse", "HEAD")
    pruned_artifact = write_artifact(
        repo,
        prune_source_commit,
        (finding_payload("RuleOne"),),
    )
    assert cli.main(java_command("prune", repo, pruned_artifact, "--dry-run")) == 0
    dry_output = capsys.readouterr().out
    assert baseline_path.read_bytes() == before_inspect

    assert cli.main(java_command("prune", repo, pruned_artifact)) == 0
    capsys.readouterr()
    assert baseline_path.read_text(encoding=ENCODING) == dry_output
    assert baseline.inspect_baseline(baseline.read_baseline(baseline_path)).entry_count == 1


def test_prune_rejects_new_findings(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Prune cannot silently admit debt that was absent from the baseline."""
    repo = initialized_repo(tmp_path)
    source_commit = git(repo, "rev-parse", "HEAD")
    initial_artifact = write_artifact(repo, source_commit, (finding_payload("RuleOne"),))
    assert cli.main(java_command("create", repo, initial_artifact)) == 0
    capsys.readouterr()
    baseline_path = repo / BASELINE_PATH
    git(repo, "add", BASELINE_PATH)
    git(repo, "commit", "-m", "record baseline")
    current_head = git(repo, "rev-parse", "HEAD")
    before = baseline_path.read_bytes()
    artifact = write_artifact(
        repo,
        current_head,
        (finding_payload("RuleOne"), finding_payload("RuleTwo")),
    )

    status = cli.main(java_command("prune", repo, artifact))

    assert status != 0
    assert baseline_path.read_bytes() == before
    assert "new or regressed" in capsys.readouterr().err


@pytest.mark.parametrize(
    "mutation",
    ("malformed", "failed-gradle", "truncated", "stale"),
)
def test_create_rejects_invalid_or_stale_evidence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    mutation: str,
) -> None:
    """Invalid, failed, partial, and stale artifacts return nonzero without writes."""
    repo = initialized_repo(tmp_path)
    source_commit = git(repo, "rev-parse", "HEAD")
    artifact = write_artifact(repo, source_commit, (finding_payload("RuleOne"),))
    if mutation == "malformed":
        artifact.write_text("{", encoding=ENCODING)
    elif mutation == "failed-gradle":
        mutate_artifact(artifact, ("observation", "exit_code"), 1)
    elif mutation == "truncated":
        mutate_artifact(artifact, ("reports", "findings_truncated"), True)
    else:
        (repo / "change.txt").write_text("changed\n", encoding=ENCODING)
        git(repo, "add", "change.txt")
        git(repo, "commit", "-m", "advance")

    status = cli.main(java_command("create", repo, artifact))
    captured = capsys.readouterr()

    assert status != 0
    assert not (repo / BASELINE_PATH).exists()
    assert captured.err


# docsync:evidence.end evidence.java.structured_evidence_tests


def initialized_repo(tmp_path: Path) -> Path:
    """Create a clean configured Git repository."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        f'[tool.agent_maintainer.java]\nfindings_baseline = "{BASELINE_PATH}"\n',
        encoding=ENCODING,
    )
    (repo / ".gitignore").write_text(".verify-logs/\n", encoding=ENCODING)
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test User")
    git(repo, "add", "pyproject.toml", ".gitignore")
    git(repo, "commit", "-m", "initial")
    return repo


def write_artifact(
    repo: Path,
    source_commit: str,
    findings: tuple[dict[str, object], ...],
) -> Path:
    """Write one complete runner-compatible Java evidence artifact."""
    artifact = repo / ARTIFACT_PATH
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "provider": "java-gradle",
                "status": "report-failed",
                "reports_parsed": True,
                "evidence_status": "regression",
                "observation": {"exit_code": 0},
                "reports": {
                    "source_commit": source_commit,
                    "finding_count": len(findings),
                    "findings": findings,
                    "findings_truncated": False,
                },
            },
            sort_keys=True,
        ),
        encoding=ENCODING,
    )
    return artifact


def finding_payload(rule: str) -> dict[str, object]:
    """Return one strict serialized Java finding."""
    payload: dict[str, object] = {
        "tool": "checkstyle",
        "rule": rule,
        "path": "src/main/java/example/App.java",
        "subject": rule,
        "message": f"{rule} message",
        "severity": "warning",
        "line": 7,
        "metric": None,
    }
    finding = JavaFinding(
        tool="checkstyle",
        rule=rule,
        path="src/main/java/example/App.java",
        subject=rule,
        message=f"{rule} message",
        severity="warning",
        line=7,
    )
    payload["fingerprint"] = finding.fingerprint
    return payload


def mutate_artifact(path: Path, keys: tuple[str, str], value: object) -> None:
    """Change one nested artifact field."""
    payload = json.loads(path.read_text(encoding=ENCODING))
    assert isinstance(payload, dict)
    typed_payload = cast(dict[str, object], payload)
    nested = typed_payload[keys[0]]
    assert isinstance(nested, dict)
    typed_nested = cast(dict[str, object], nested)
    typed_nested[keys[1]] = value
    path.write_text(json.dumps(typed_payload, sort_keys=True), encoding=ENCODING)


def java_command(
    operation: str,
    repo: Path,
    artifact: Path | None,
    *extra: str,
) -> list[str]:
    """Return one Java baseline CLI argument list."""
    command = ["java-baseline", operation, "--target", str(repo)]
    if artifact is not None:
        command.extend(("--artifact", str(artifact)))
    command.extend(extra)
    return command


def git(repo: Path, *args: str) -> str:
    """Run one local Git fixture command."""
    result = subprocess.run(
        ("git", "-C", str(repo), *args),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()
