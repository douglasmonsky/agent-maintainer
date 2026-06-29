"""Tests bounded verifier failure artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.models import CheckResult
from agent_maintainer.verify import artifacts

LAST_FAILURE_LIMIT = 500
LARGE_OUTPUT = "\n".join(f"failure line {index}" for index in range(200))


def run_context(repo_root: Path) -> artifacts.RunContext:
    """Return verifier run context with a tight failure budget."""

    return artifacts.RunContext(
        repo_root=repo_root,
        profile="full",
        base_ref="HEAD",
        compare_branch="origin/main",
        staged=False,
        config=MaintainerConfig(context_last_failure_budget_chars=LAST_FAILURE_LIMIT),
        run_id="20260625T100000Z-full-test",
    )


def test_last_failure_is_bounded_and_manifest_has_context_metadata(
    tmp_path: Path,
) -> None:
    """Huge failure output is capped while full logs remain referenced."""

    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    log_path = log_dir / "ruff.log"
    log_path.write_text(LARGE_OUTPUT, encoding="utf-8")
    result = CheckResult(
        "ruff",
        passed=False,
        output=LARGE_OUTPUT,
        command=("ruff", "check"),
        exit_code=1,
        log_path=str(log_path),
        started_at="2026-06-25T10:00:00Z",
        ended_at="2026-06-25T10:00:01Z",
    )

    artifacts.write_run_artifacts(log_dir, run_context(tmp_path), [result])

    failure_note = (log_dir / artifacts.LAST_FAILURE_NAME).read_text(encoding="utf-8")
    manifest = json.loads((log_dir / artifacts.MANIFEST_NAME).read_text(encoding="utf-8"))
    check_payload = manifest["checks"][0]

    assert len(failure_note) <= LAST_FAILURE_LIMIT + artifacts.TRUNCATION_NOTE_ALLOWANCE
    assert "Run ID: `20260625T100000Z-full-test`" in failure_note
    assert (
        "Stable snapshot: `.verify-logs/runs/20260625T100000Z-full-test/LAST_FAILURE.md`"
    ) in failure_note
    assert "omitted" in failure_note
    assert check_payload["log_bytes"] == len(LARGE_OUTPUT.encode("utf-8"))
    assert check_payload["summary_chars"] == len(LARGE_OUTPUT)
    assert check_payload["summary_truncated"] is True
    assert check_payload["omitted_chars"] > 0
    assert check_payload["omitted_lines"] > 0
    assert check_payload["expansion_commands"] == [
        "python -m agent_maintainer context failures --check ruff --limit 20",
        "python -m agent_maintainer context log ruff --tail 120",
    ]
