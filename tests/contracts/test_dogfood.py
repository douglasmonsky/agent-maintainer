"""Freshness checks for Agent Maintainer's own semantic contracts."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast

from jsonschema import Draft202012Validator

from agent_maintainer import cli as agent_cli
from agent_maintainer.contracts.baseline import load_baseline
from agent_maintainer.contracts.extraction import extract_all
from agent_maintainer.contracts.policy import load_policy
from agent_waits.registry import WaitRecord
from tests.support.paths import REPO_ROOT

CONTRACT_IDS = {
    "agent-maintainer-config",
    "agent-maintainer-cli",
    "docsync-api",
    "codex-app-server-wait",
    "agent-waits-wait-record",
}


class JsonValidator(Protocol):
    """Narrow interface used by dogfood schema assertions."""

    def validate(self, instance: object) -> None:
        """Validate one JSON-compatible instance."""


def load_json(path: Path) -> dict[str, object]:
    """Load one repository JSON object for source-freshness assertions."""
    payload: object = json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return cast(dict[str, object], payload)


def test_policy_nominates_five_agent_maintainer_contracts() -> None:
    """Dogfood policy remains explicit, beta, and independently revisioned."""
    policy = load_policy(REPO_ROOT)

    assert policy is not None
    assert {item.id for item in policy.contracts} == CONTRACT_IDS
    assert all(item.revision == 1 for item in policy.contracts)
    assert all(item.stability == "beta" for item in policy.contracts)
    assert all(
        item.migration_paths == ("CHANGELOG.md", "docs/upgrading-to-*.md")
        for item in policy.contracts
    )


def test_cli_manifest_matches_public_root_commands() -> None:
    """Every public root route is represented by one top-level manifest command."""
    payload = load_json(Path("config/agent-maintainer-cli.json"))
    commands = payload.get("commands")
    assert isinstance(commands, list)
    manifested: set[str] = set()
    for raw_item in cast(list[object], commands):
        assert isinstance(raw_item, dict)
        item = cast(dict[str, object], raw_item)
        path = item.get("path")
        assert isinstance(path, list)
        path_items = cast(list[object], path)
        if len(path_items) == 1 and isinstance(path_items[0], str):
            manifested.add(path_items[0])

    assert manifested == set(agent_cli.command_handlers())


def test_wait_record_schema_matches_serialized_keys() -> None:
    """Persistence schema names every generic and compatibility record key."""
    now = datetime(2026, 7, 18, tzinfo=UTC).isoformat()
    record = WaitRecord(
        wait_id="github-pr-291",
        kind="github-pr",
        status="pending",
        target_id="291",
        repo="douglasmonsky/agent-maintainer",
        platform="codex",
        branch="main",
        head_sha="abc123",
        interval_seconds=20,
        timeout_seconds=3600,
        created_at=now,
        updated_at=now,
        deadline_at=now,
        resume_instruction="agent-maintainer wait resume github-pr-291",
    )
    payload = record.as_dict()
    schema = load_json(Path("schemas/agent-waits-wait-record.schema.json"))

    validator = cast(JsonValidator, Draft202012Validator(schema))
    validator.validate(payload)
    properties = schema.get("properties")
    required = schema.get("required")
    assert isinstance(properties, dict)
    assert isinstance(required, list)
    property_names = cast(dict[str, object], properties)
    required_items = cast(list[object], required)
    assert all(isinstance(item, str) for item in required_items)
    assert set(property_names) == set(payload)
    assert set(cast(list[str], required_items)) <= set(payload)


def test_checked_in_baseline_exactly_matches_live_dogfood_extraction() -> None:
    """All five checked-in descriptors are canonical live facts."""
    policy = load_policy(REPO_ROOT)
    baseline = load_baseline(REPO_ROOT)

    assert policy is not None
    assert baseline is not None
    live = extract_all(REPO_ROOT, policy)
    assert {item.contract_id for item in baseline.descriptors} == CONTRACT_IDS
    assert baseline.descriptors == live
