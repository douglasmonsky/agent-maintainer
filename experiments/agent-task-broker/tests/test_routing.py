"""Tests deterministic task broker model-tier routing."""

from __future__ import annotations

import json
from pathlib import Path

from agent_task_broker.adapters import LocalJsonlTraceSink
from agent_task_broker.handoff import handoff_payload, render_handoff
from agent_task_broker.routing import (
    ROUTE_CHEAP_LOCAL_ALLOWED,
    ROUTE_HUMAN_REVIEW_REQUIRED,
    ROUTE_STANDARD_WORKER_REQUIRED,
    ROUTE_STRONG_WORKER_REQUIRED,
    ModelRoutingPolicy,
    RouteInput,
)
from agent_task_broker.store import BrokerStore, TaskInput


def test_low_risk_focused_task_allows_cheap_local_route() -> None:
    """Low-risk bounded tasks can route to cheap local workers."""

    decision = ModelRoutingPolicy().route(
        RouteInput(
            task_id="task-0001",
            goal="Update README command example.",
            allowed_paths=("README.md",),
            acceptance_commands=("pytest tests/docs -q",),
            estimated_context_tokens=1_200,
            difficulty_score=1,
            confidence_score=0.95,
        )
    )

    assert decision.route == ROUTE_CHEAP_LOCAL_ALLOWED
    assert decision.advisory is True
    assert "focused low-risk task" in decision.compact_reason


def test_policy_sensitive_surface_escalates_to_strong_worker() -> None:
    """Architecture or CI surfaces require stronger workers."""

    decision = ModelRoutingPolicy().route(
        RouteInput(
            task_id="task-0002",
            goal="Change Tach architecture boundary.",
            allowed_paths=("tach.toml",),
            acceptance_commands=("tach check --exact",),
            confidence_score=0.95,
        )
    )

    assert decision.route == ROUTE_STRONG_WORKER_REQUIRED
    assert "policy-sensitive" in decision.compact_reason


def test_low_confidence_escalates_to_strong_worker() -> None:
    """Low routing confidence is never sent to cheap workers."""

    decision = ModelRoutingPolicy().route(
        RouteInput(
            task_id="task-0003",
            goal="Refactor unclear ownership boundary.",
            allowed_paths=("src/agent_task_broker/routing.py",),
            acceptance_commands=("pytest -q",),
            confidence_score=0.4,
        )
    )

    assert decision.route == ROUTE_STRONG_WORKER_REQUIRED
    assert "confidence below" in decision.compact_reason


def test_repeated_cheap_worker_failure_escalates() -> None:
    """Repeated cheap-worker failures require stronger worker routing."""

    decision = ModelRoutingPolicy().route(
        RouteInput(
            task_id="task-0004",
            goal="Fix flaky parser test.",
            allowed_paths=("src/parser.py",),
            acceptance_commands=("pytest tests/test_parser.py -q",),
            confidence_score=0.95,
            cheap_worker_failures=2,
        )
    )

    assert decision.route == ROUTE_STRONG_WORKER_REQUIRED
    assert "repeated cheap-worker failure" in decision.compact_reason


def test_verification_failure_escalates() -> None:
    """Recent verification failures require stronger workers."""

    decision = ModelRoutingPolicy().route(
        RouteInput(
            task_id="task-0005",
            goal="Continue repair after verifier failure.",
            allowed_paths=("src/checks.py",),
            acceptance_commands=("python -m agent_maintainer verify --profile fast",),
            recent_failures=("pyright failed",),
            confidence_score=0.95,
        )
    )

    assert decision.route == ROUTE_STRONG_WORKER_REQUIRED
    assert "verification failure" in decision.compact_reason


def test_sensitive_surfaces_require_human_review() -> None:
    """Credentials and sensitive data are never routed to cheap workers."""

    decision = ModelRoutingPolicy().route(
        RouteInput(
            task_id="task-0006",
            goal="Update release workflow publishing credentials.",
            allowed_paths=(".github/workflows/publish.yml",),
            acceptance_commands=("python -m agent_maintainer verify --profile security",),
            confidence_score=0.95,
        )
    )

    assert decision.route == ROUTE_HUMAN_REVIEW_REQUIRED
    assert "sensitive-data surface" in decision.compact_reason


def test_default_moderate_task_uses_standard_route() -> None:
    """Moderate but bounded work uses the standard route."""

    decision = ModelRoutingPolicy().route(
        RouteInput(
            task_id="task-0007",
            goal="Refactor task broker helpers.",
            allowed_paths=("experiments/agent-task-broker/src/helpers.py",),
            acceptance_commands=("pytest experiments/agent-task-broker/tests -q",),
            estimated_context_tokens=5_000,
            difficulty_score=3,
            confidence_score=0.82,
        )
    )

    assert decision.route == ROUTE_STANDARD_WORKER_REQUIRED
    assert "moderate task risk" in decision.compact_reason


def test_handoff_output_includes_compact_route_reason(tmp_path: Path) -> None:
    """Handoff payload and Markdown include selected advisory tier."""

    store = BrokerStore(tmp_path)
    store.init()
    task = store.add_task(
        TaskInput(
            "Update docs",
            allowed_paths=("README.md",),
            acceptance_commands=("pytest tests/docs -q",),
        )
    )
    decision = ModelRoutingPolicy().route(
        RouteInput(
            task_id=str(task["id"]),
            goal=str(task["title"]),
            allowed_paths=tuple(str(path) for path in task["allowed_paths"]),
            acceptance_commands=tuple(str(command) for command in task["acceptance_commands"]),
            estimated_context_tokens=800,
            difficulty_score=1,
            confidence_score=0.96,
        )
    )

    payload = handoff_payload(task, routing=decision.to_payload())
    markdown = render_handoff(
        task,
        output_format="markdown",
        routing=decision.to_payload(),
    )

    assert payload["model_routing"]["route"] == ROUTE_CHEAP_LOCAL_ALLOWED
    assert "## Model routing" in markdown
    assert f"- Route: `{ROUTE_CHEAP_LOCAL_ALLOWED}`" in markdown
    assert "focused low-risk task" in markdown


def test_route_decision_emits_sanitized_runtime_event(tmp_path: Path) -> None:
    """Route events use runtime-event-shaped local JSONL records."""

    decision = ModelRoutingPolicy().route(
        RouteInput(
            task_id="task-0008",
            goal="Update README command example.",
            allowed_paths=("README.md",),
            acceptance_commands=("pytest tests/docs -q",),
            estimated_context_tokens=1_200,
            difficulty_score=1,
            confidence_score=0.95,
        )
    )
    sink = LocalJsonlTraceSink(root=tmp_path)

    sink.emit(decision.to_trace_event())

    event = json.loads(sink.events_path.read_text(encoding="utf-8"))
    assert event["event_name"] == "task.route_decided"
    assert event["command"] == "task-broker"
    assert event["attributes"]["task_id"] == "task-0008"
    assert event["attributes"]["route"] == ROUTE_CHEAP_LOCAL_ALLOWED
    assert "README command example" not in json.dumps(event)


def test_router_policy_imports_no_model_provider_sdks() -> None:
    """Routing policy stays provider-neutral."""

    routing_source = (
        Path("experiments/agent-task-broker/src/agent_task_broker/routing.py")
        .read_text(encoding="utf-8")
        .lower()
    )
    provider_modules = {
        "openai",
        "anthropic",
        "langgraph",
        "autogen",
        "crewai",
    }

    for provider_module in provider_modules:
        assert f"import {provider_module}" not in routing_source
        assert f"from {provider_module}" not in routing_source
