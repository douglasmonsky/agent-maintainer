"""Tests for provider-neutral scoring examples."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_maintainer.scoring import cli
from agent_maintainer.scoring.dataset import list_examples, read_examples


def test_scoring_examples_are_provider_neutral() -> None:
    """Bundled examples use route labels without model provider names."""
    examples = list_examples()

    assert examples
    payload = [example.to_payload() for example in examples]
    text = json.dumps(payload).lower()
    assert "gpt" not in text
    assert "claude" not in text
    assert {example.expected_route for example in examples} >= {
        "cheap-local-allowed",
        "strong-worker-required",
        "human-review-required",
    }


def test_scoring_examples_list_json(capsys: pytest.CaptureFixture[str]) -> None:
    """CLI lists schema-valid labeled examples."""
    status = cli.main(["examples", "list", "--format", "json"])

    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["example_id"] == "route-low-risk-doc-test"
    assert payload[0]["labels"] == ["low-risk", "docs", "focused-verification"]


def test_scoring_examples_add_writes_jsonl(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI appends local examples to the configured JSONL dataset."""
    examples_file = tmp_path / "examples.jsonl"

    status = cli.main(
        [
            "examples",
            "--examples-file",
            str(examples_file),
            "add",
            "--id",
            "route-focused-test",
            "--task-summary",
            "Run focused tests for a CLI parser change.",
            "--label",
            "cli",
            "--label",
            "focused-verification",
            "--expected-route",
            "cheap-local-allowed",
            "--evidence",
            "acceptance: pytest tests/scoring -q",
            "--notes",
            "Synthetic example only.",
        ],
    )

    assert status == 0
    assert capsys.readouterr().out.strip() == str(examples_file)
    payload = json.loads(examples_file.read_text(encoding="utf-8"))
    assert payload["example_id"] == "route-focused-test"
    assert payload["labels"] == ["cli", "focused-verification"]


def test_scoring_examples_export_jsonl_includes_local_examples(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI exports bundled and local examples as JSONL."""
    examples_file = tmp_path / "examples.jsonl"
    examples_file.write_text(
        json.dumps(
            {
                "example_id": "route-local-saved",
                "task_summary": "Saved local task.",
                "labels": ["local", "routing"],
                "expected_route": "strong-worker-required",
                "evidence": ["source: local jsonl"],
                "notes": "Persisted example.",
            },
        )
        + "\n",
        encoding="utf-8",
    )

    status = cli.main(
        [
            "examples",
            "--examples-file",
            str(examples_file),
            "export",
            "--format",
            "jsonl",
        ],
    )

    assert status == 0
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert rows[0]["example_id"] == "route-low-risk-doc-test"
    assert rows[-1]["example_id"] == "route-local-saved"


def test_scoring_examples_reject_non_object_jsonl_row(tmp_path: Path) -> None:
    """Every persisted scoring row must expose named object fields."""

    examples_file = tmp_path / "examples.jsonl"
    examples_file.write_text('["not", "an", "object"]\n', encoding="utf-8")

    with pytest.raises(ValueError, match="scoring example must be a JSON object"):
        read_examples(examples_file)
