"""Provider-neutral labeled examples for future scoring work."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.core.structured_values import json_array, json_object

JSONL_FORMAT = "jsonl"
DEFAULT_EXAMPLES_FILE = Path(".verify-logs/scoring/examples.jsonl")


@dataclass(frozen=True)
class ScoringExample:
    """One labeled routing or repair example."""

    example_id: str
    task_summary: str
    labels: tuple[str, ...]
    expected_route: str
    evidence: tuple[str, ...]
    notes: str

    def to_payload(self) -> dict[str, object]:
        """Return JSON-serializable example payload."""
        return {
            "example_id": self.example_id,
            "task_summary": self.task_summary,
            "labels": list(self.labels),
            "expected_route": self.expected_route,
            "evidence": list(self.evidence),
            "notes": self.notes,
        }


DEFAULT_EXAMPLES = (
    ScoringExample(
        example_id="route-low-risk-doc-test",
        task_summary="Update a README command example and run focused doc tests.",
        labels=("low-risk", "docs", "focused-verification"),
        expected_route="cheap-local-allowed",
        evidence=("allowed_paths: README.md", "acceptance: pytest tests/docs -q"),
        notes="No provider-specific model name is encoded.",
    ),
    ScoringExample(
        example_id="route-architecture-policy",
        task_summary="Change Tach boundaries for an internal package.",
        labels=("architecture", "policy-sensitive", "requires-adr"),
        expected_route="strong-worker-required",
        evidence=("touches: tach.toml", "requires: architecture decision note"),
        notes="Architecture policy changes escalate before dispatch.",
    ),
    ScoringExample(
        example_id="route-credentials-release",
        task_summary="Prepare release automation touching publishing credentials.",
        labels=("release", "credential-sensitive", "human-review"),
        expected_route="human-review-required",
        evidence=("surface: release workflow", "risk: credentials or publishing"),
        notes="Sensitive external-account work is never cheap-worker eligible.",
    ),
)


def list_examples() -> tuple[ScoringExample, ...]:
    """Return bundled provider-neutral scoring examples."""
    return DEFAULT_EXAMPLES


def list_all_examples(
    examples_file: Path = DEFAULT_EXAMPLES_FILE,
) -> tuple[ScoringExample, ...]:
    """Return bundled examples plus locally collected examples."""
    return (*DEFAULT_EXAMPLES, *read_examples(examples_file))


def read_examples(examples_file: Path) -> tuple[ScoringExample, ...]:
    """Read local JSONL scoring examples if the file exists."""
    if not examples_file.exists():
        return ()
    return tuple(
        example_from_payload(_example_payload(line))
        for line in examples_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def _example_payload(line: str) -> dict[str, object]:
    decoded: object = json.loads(line)
    payload = json_object(decoded)
    if payload is None:
        raise ValueError("scoring example must be a JSON object")
    return payload


def add_example(
    example: ScoringExample,
    examples_file: Path = DEFAULT_EXAMPLES_FILE,
) -> Path:
    """Append one local scoring example as JSONL."""
    examples_file.parent.mkdir(parents=True, exist_ok=True)
    with examples_file.open("a", encoding="utf-8") as file_obj:
        file_obj.write(json.dumps(example.to_payload(), sort_keys=True))
        file_obj.write("\n")
    return examples_file


def examples_json(examples_file: Path = DEFAULT_EXAMPLES_FILE) -> str:
    """Return deterministic JSON examples list."""
    return json.dumps(
        [example.to_payload() for example in list_all_examples(examples_file)],
        indent=2,
        sort_keys=True,
    )


def examples_jsonl(examples_file: Path = DEFAULT_EXAMPLES_FILE) -> str:
    """Return deterministic JSONL examples export."""
    rows = [
        json.dumps(example.to_payload(), sort_keys=True)
        for example in list_all_examples(examples_file)
    ]
    if rows:
        body = "\n".join(rows)
        return f"{body}\n"
    return ""


def example_from_payload(payload: dict[str, object]) -> ScoringExample:
    """Build one scoring example from JSON object payload."""
    return ScoringExample(
        example_id=str(payload["example_id"]),
        task_summary=str(payload["task_summary"]),
        labels=_string_tuple(payload["labels"]),
        expected_route=str(payload["expected_route"]),
        evidence=_string_tuple(payload["evidence"]),
        notes=str(payload["notes"]),
    )


def _string_tuple(value: object) -> tuple[str, ...]:
    """Return a tuple of strings from a JSON list field."""
    values = json_array(value)
    if values is not None:
        return tuple(str(item) for item in values)
    raise ValueError("expected list-like scoring example field")
