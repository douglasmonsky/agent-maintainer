"""Adversarial tests for bounded exact repair-fact reads."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from agent_context.failures import FailureRecord
from agent_context.reading import file_safety
from agent_maintainer.context.pack import exact_facts
from agent_repair_facts import registry
from agent_repair_facts.payloads import fact_payload

APP_PATH = "src/pkg/app.py"
LARGE_TEST_LIMIT = 32


@pytest.mark.parametrize(
    "case",
    (
        (
            "ruff",
            "ruff.json",
            json.dumps(
                [
                    {
                        "filename": APP_PATH,
                        "location": {"row": 7, "column": 3},
                        "code": "F401",
                        "message": "Unused import",
                    },
                ],
            ),
            True,
            "F401",
        ),
        (
            "pytest-coverage",
            "pytest-junit.xml",
            (
                '<testsuite><testcase name="test_app" file="tests/test_app.py" line="8">'
                '<failure message="failed">detail</failure></testcase></testsuite>'
            ),
            True,
            "pytest-failure",
        ),
        (
            "pylint",
            "pylint.log",
            f"{APP_PATH}:4:2: C0103: Invalid name\n",
            False,
            "C0103",
        ),
        (
            "typescript-typecheck",
            "typescript-typecheck.log",
            "src/app.ts(4,9): error TS2322: Type mismatch\n",
            False,
            "TS2322",
        ),
    ),
)
def test_bounded_source_is_opened_once_and_parser_never_reopens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[str, str, str, bool, str],
) -> None:
    """JSON, XML, text, and TypeScript parsers consume captured text."""

    check, filename, content, is_artifact, symbol = case
    source = tmp_path / filename
    source.write_text(content, encoding="utf-8")
    original_open = file_safety.os.open
    open_flags: list[int] = []

    def tracked_open(path: Path, flags: int) -> int:
        if Path(path) == source:
            open_flags.append(flags)
        return original_open(path, flags)

    def forbidden_reopen(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("parser reopened a path after its bounded read")

    monkeypatch.setattr(file_safety.os, "open", tracked_open)
    monkeypatch.setattr(Path, "read_text", forbidden_reopen)

    facts = exact_facts.repair_facts(
        tmp_path,
        (failure(check, source, is_artifact=is_artifact),),
    )

    assert facts[0]["symbol"] == symbol
    assert len(open_flags) == 1
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    assert no_follow == 0 or open_flags[0] & no_follow


def test_growth_after_path_inspection_is_refused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A file that grows after lstat cannot bypass the descriptor ceiling."""

    artifact = tmp_path / "ruff.json"
    artifact.write_text("[]", encoding="utf-8")
    original_inspect = file_safety.inspect_path
    parser_calls = 0
    grew = False

    def inspect_then_grow(path: Path, *, max_bytes: int) -> file_safety.FileSafety | None:
        nonlocal grew
        decision = original_inspect(path, max_bytes=max_bytes)
        if path == artifact and decision is None and not grew:
            artifact.write_text("[" + " " * LARGE_TEST_LIMIT, encoding="utf-8")
            grew = True
        return decision

    def fake_parser(check: str, path: Path, text: str) -> list[dict[str, object]]:
        nonlocal parser_calls
        parser_calls += 1
        return [fact_payload({"check": check, "path": path, "message": text})]

    monkeypatch.setattr(exact_facts, "MAX_EXACT_FACT_INPUT_BYTES", LARGE_TEST_LIMIT)
    monkeypatch.setattr(file_safety, "inspect_path", inspect_then_grow)
    monkeypatch.setattr(registry, "artifact_facts_from_text", fake_parser)
    budget = exact_facts.ExactFactReadBudget()

    facts = exact_facts.repair_facts(
        tmp_path,
        (failure("ruff", artifact, is_artifact=True),),
        read_budget=budget,
    )

    assert facts[0]["message"] == "ruff failed with exit code 1"
    assert parser_calls == 0
    assert budget.remaining_files == exact_facts.MAX_EXACT_FACT_FILES - 1
    assert budget.remaining_bytes == exact_facts.MAX_EXACT_FACT_TOTAL_BYTES


def test_budget_charges_bytes_observed_by_bounded_reader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Aggregate accounting uses post-resolution content, not stale stat size."""

    artifact = tmp_path / "ruff.json"
    initial_content = "{}"
    grown_content = initial_content + " " * 10
    artifact.write_text(initial_content, encoding="utf-8")
    log = tmp_path / "ruff.log"
    log_content = f"{APP_PATH}:4:2: C0103: Invalid name\n"
    log.write_text(log_content, encoding="utf-8")
    original_reader = file_safety.read_bounded_utf8_file
    grew = False

    def grow_before_read(
        path: Path,
        *,
        workspace_root: Path | None = None,
        max_bytes: int,
    ) -> file_safety.SafeTextRead:
        nonlocal grew
        if path == artifact and not grew:
            artifact.write_text(grown_content, encoding="utf-8")
            grew = True
        return original_reader(
            path,
            workspace_root=workspace_root,
            max_bytes=max_bytes,
        )

    monkeypatch.setattr(file_safety, "read_bounded_utf8_file", grow_before_read)
    total_bytes = len((grown_content + log_content).encode("utf-8"))
    budget = exact_facts.ExactFactReadBudget(
        remaining_bytes=total_bytes,
        remaining_files=2,
    )

    facts = exact_facts.repair_facts(
        tmp_path,
        (failure_with_artifact_and_log("pylint", artifact, log),),
        read_budget=budget,
    )

    assert facts[0]["symbol"] == "C0103"
    assert budget.remaining_bytes == 0
    assert budget.remaining_files == 0


def test_file_count_stops_fallback_reader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A malformed artifact consumes the sole file-read slot before fallback."""

    artifact = tmp_path / "ruff.json"
    artifact.write_text("{}", encoding="utf-8")
    log = tmp_path / "ruff.log"
    log.write_text(f"{APP_PATH}:4:2: C0103: Invalid name\n", encoding="utf-8")
    original_reader = file_safety.read_bounded_utf8_file
    read_paths: list[Path] = []

    def tracked_reader(
        path: Path,
        *,
        workspace_root: Path | None = None,
        max_bytes: int,
    ) -> file_safety.SafeTextRead:
        read_paths.append(path)
        return original_reader(
            path,
            workspace_root=workspace_root,
            max_bytes=max_bytes,
        )

    monkeypatch.setattr(file_safety, "read_bounded_utf8_file", tracked_reader)
    budget = exact_facts.ExactFactReadBudget(remaining_files=1)

    facts = exact_facts.repair_facts(
        tmp_path,
        (failure_with_artifact_and_log("ruff", artifact, log),),
        read_budget=budget,
    )

    assert facts[0]["message"] == "ruff failed with exit code 1"
    assert read_paths == [artifact]
    assert budget.remaining_files == 0


def test_aggregate_byte_budget_is_the_reader_ceiling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Content larger than remaining aggregate bytes never reaches a parser."""

    artifact = tmp_path / "ruff.json"
    content = json.dumps([{"message": "actionable"}])
    artifact.write_text(content, encoding="utf-8")
    parser_calls = 0

    def fake_parser(check: str, path: Path, text: str) -> list[dict[str, object]]:
        nonlocal parser_calls
        parser_calls += 1
        return [fact_payload({"check": check, "path": path, "message": text})]

    monkeypatch.setattr(registry, "artifact_facts_from_text", fake_parser)
    budget = exact_facts.ExactFactReadBudget(
        remaining_bytes=len(content.encode("utf-8")) - 1,
    )

    facts = exact_facts.repair_facts(
        tmp_path,
        (failure("ruff", artifact, is_artifact=True),),
        read_budget=budget,
    )

    assert facts[0]["message"] == "ruff failed with exit code 1"
    assert parser_calls == 0
    assert budget.remaining_files == exact_facts.MAX_EXACT_FACT_FILES - 1


def test_deeply_nested_json_artifact_fails_closed(tmp_path: Path) -> None:
    """A bounded recursive JSON artifact cannot crash exact-fact parsing."""

    artifact = tmp_path / "ruff.json"
    nesting = 2_000
    artifact.write_text(
        "".join(("[" * nesting, "0", "]" * nesting)),
        encoding="utf-8",
    )

    facts = exact_facts.repair_facts(
        tmp_path,
        (failure("ruff", artifact, is_artifact=True),),
    )

    assert facts[0]["message"] == "ruff failed with exit code 1"


def failure(check: str, source: Path, *, is_artifact: bool) -> FailureRecord:
    """Return a failure with the source registered as artifact or log."""

    return FailureRecord(
        name=check,
        status="failed",
        category="test",
        priority=1,
        exit_code=1,
        log_path=str(source.with_suffix(".log") if is_artifact else source),
        log_bytes=0,
        expansion_commands=(),
        artifact_paths=(str(source),) if is_artifact else (),
    )


def failure_with_artifact_and_log(
    check: str,
    artifact: Path,
    log: Path,
) -> FailureRecord:
    """Return a failure that may fall back from artifact to log."""

    return FailureRecord(
        name=check,
        status="failed",
        category="test",
        priority=1,
        exit_code=1,
        log_path=str(log),
        log_bytes=0,
        expansion_commands=(),
        artifact_paths=(str(artifact),),
    )
