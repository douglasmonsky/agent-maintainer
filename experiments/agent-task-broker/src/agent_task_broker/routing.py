"""Deterministic model-tier routing policy for task broker."""

from __future__ import annotations

from dataclasses import dataclass

from agent_task_broker.adapters import TraceEvent

ROUTE_CHEAP_LOCAL_ALLOWED = "cheap-local-allowed"
ROUTE_STANDARD_WORKER_REQUIRED = "standard-worker-required"
ROUTE_STRONG_WORKER_REQUIRED = "strong-worker-required"
ROUTE_HUMAN_REVIEW_REQUIRED = "human-review-required"

ROUTES = (
    ROUTE_CHEAP_LOCAL_ALLOWED,
    ROUTE_STANDARD_WORKER_REQUIRED,
    ROUTE_STRONG_WORKER_REQUIRED,
    ROUTE_HUMAN_REVIEW_REQUIRED,
)

DEFAULT_MIN_CONFIDENCE = 0.7
DEFAULT_CHEAP_CONFIDENCE = 0.85
DEFAULT_CHEAP_CONTEXT_TOKENS = 6_000
DEFAULT_MAX_CONTEXT_TOKENS = 18_000
MAX_CHEAP_DIFFICULTY = 2
REPEATED_CHEAP_FAILURES = 2

HUMAN_REVIEW_TERMS = (
    "credential",
    "credentials",
    "secret",
    "secrets",
    "private data",
    "student data",
    "payment",
    "billing",
    "production access",
    "publish",
    "release",
)

STRONG_REVIEW_TERMS = (
    "architecture",
    "auth",
    "security",
    "ci",
    "workflow",
    "public api",
    "tach",
    "schema",
    "migration",
)

HUMAN_REVIEW_PATH_PARTS = (
    ".env",
    ".pypirc",
    ".github/workflows/publish",
    "docs/release",
)

STRONG_REVIEW_PATH_PARTS = (
    ".github/workflows",
    "tach.toml",
    "pyproject.toml",
    "docs/architecture",
    "src/agent_maintainer/security",
)


@dataclass(frozen=True)
class RouteInput:
    """Task evidence available to the routing policy."""

    task_id: str
    goal: str
    body: str = ""
    allowed_paths: tuple[str, ...] = ()
    do_not_edit_paths: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    acceptance_commands: tuple[str, ...] = ()
    lock_targets: tuple[str, ...] = ()
    changed_files: tuple[str, ...] = ()
    recent_failures: tuple[str, ...] = ()
    repair_facts: tuple[str, ...] = ()
    estimated_context_tokens: int = 0
    difficulty_score: int = 3
    confidence_score: float = 0.8
    cheap_worker_failures: int = 0

    @property
    def all_paths(self) -> tuple[str, ...]:
        """Return all path-like task inputs."""

        return (
            *self.allowed_paths,
            *self.do_not_edit_paths,
            *self.lock_targets,
            *self.changed_files,
        )


@dataclass(frozen=True)
class RouteDecision:
    """Advisory route decision with compact explanation."""

    task_id: str
    route: str
    confidence: float
    reasons: tuple[str, ...]
    advisory: bool = True

    def __post_init__(self) -> None:
        """Validate route."""

        if self.route not in ROUTES:
            raise ValueError(f"unknown route: {self.route}")

    @property
    def compact_reason(self) -> str:
        """Return one-line reason for handoffs."""

        return "; ".join(self.reasons[:3])

    def to_payload(self) -> dict[str, object]:
        """Return JSON-serializable handoff payload."""

        return {
            "route": self.route,
            "confidence": self.confidence,
            "advisory": self.advisory,
            "reason": self.compact_reason,
            "reasons": list(self.reasons),
        }

    def to_trace_event(self) -> TraceEvent:
        """Return compact runtime-event-shaped route event."""

        return TraceEvent(
            event_name="task.route_decided",
            task_id=self.task_id,
            status="pass",
            attributes={
                "route": self.route,
                "confidence": self.confidence,
                "advisory": self.advisory,
                "reason": self.compact_reason,
            },
        )


@dataclass(frozen=True)
class ModelRoutingPolicy:
    """Deterministic advisory model-tier routing policy."""

    min_confidence: float = DEFAULT_MIN_CONFIDENCE
    cheap_confidence: float = DEFAULT_CHEAP_CONFIDENCE
    cheap_context_tokens: int = DEFAULT_CHEAP_CONTEXT_TOKENS
    max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS

    def route(self, route_input: RouteInput) -> RouteDecision:
        """Return advisory route for task evidence."""

        human_reason = human_review_reason(route_input)
        if human_reason:
            return self._decision(
                route_input,
                ROUTE_HUMAN_REVIEW_REQUIRED,
                human_reason,
            )

        escalation_reason = strong_worker_reason(route_input, self)
        if escalation_reason:
            return self._decision(
                route_input,
                ROUTE_STRONG_WORKER_REQUIRED,
                escalation_reason,
            )

        if cheap_worker_allowed(route_input, self):
            return self._decision(
                route_input,
                ROUTE_CHEAP_LOCAL_ALLOWED,
                "focused low-risk task with bounded verification",
            )

        return self._decision(
            route_input,
            ROUTE_STANDARD_WORKER_REQUIRED,
            "default advisory route for moderate task risk",
        )

    def _decision(
        self,
        route_input: RouteInput,
        route: str,
        reason: str,
    ) -> RouteDecision:
        """Build a route decision."""

        return RouteDecision(
            task_id=route_input.task_id,
            route=route,
            confidence=route_input.confidence_score,
            reasons=(reason,),
        )


def human_review_reason(route_input: RouteInput) -> str:
    """Return human-review reason or empty string."""

    evidence = searchable_text(route_input)
    if contains_any(evidence, HUMAN_REVIEW_TERMS):
        return "credential, release, production, or sensitive-data surface"
    if path_contains_any(route_input.all_paths, HUMAN_REVIEW_PATH_PARTS):
        return "sensitive path requires human review before dispatch"
    return ""


def strong_worker_reason(route_input: RouteInput, policy: ModelRoutingPolicy) -> str:
    """Return strong-worker escalation reason or empty string."""

    reasons = strong_worker_reasons(route_input, policy)
    if reasons:
        return reasons[0]
    return ""


def strong_worker_reasons(
    route_input: RouteInput,
    policy: ModelRoutingPolicy,
) -> tuple[str, ...]:
    """Return all strong-worker escalation reasons."""

    reasons: list[str] = []
    if route_input.recent_failures:
        reasons.append("recent verification failure requires stronger worker")
    if route_input.confidence_score < policy.min_confidence:
        reasons.append("routing confidence below deterministic threshold")
    if route_input.cheap_worker_failures >= REPEATED_CHEAP_FAILURES:
        reasons.append("repeated cheap-worker failure requires escalation")
    if route_input.estimated_context_tokens > policy.max_context_tokens:
        reasons.append("estimated context exceeds cheap-worker bounds")
    if not route_input.allowed_paths and not route_input.lock_targets:
        reasons.append("ambiguous ownership scope requires escalation")
    if contains_any(searchable_text(route_input), STRONG_REVIEW_TERMS):
        reasons.append("policy-sensitive or architecture-adjacent surface")
    if path_contains_any(route_input.all_paths, STRONG_REVIEW_PATH_PARTS):
        reasons.append("high-risk file path requires stronger worker")
    return tuple(reasons)


def cheap_worker_allowed(route_input: RouteInput, policy: ModelRoutingPolicy) -> bool:
    """Return whether cheap local worker route is allowed."""

    return (
        route_input.difficulty_score <= MAX_CHEAP_DIFFICULTY
        and route_input.confidence_score >= policy.cheap_confidence
        and route_input.estimated_context_tokens <= policy.cheap_context_tokens
        and bool(route_input.acceptance_commands)
        and bool(route_input.allowed_paths)
    )


def searchable_text(route_input: RouteInput) -> str:
    """Return lower-case route evidence string."""

    return " ".join(
        (
            route_input.goal,
            route_input.body,
            *route_input.allowed_paths,
            *route_input.do_not_edit_paths,
            *route_input.constraints,
            *route_input.evidence,
            *route_input.acceptance_commands,
            *route_input.lock_targets,
            *route_input.changed_files,
            *route_input.recent_failures,
            *route_input.repair_facts,
        )
    ).lower()


def contains_any(text: str, terms: tuple[str, ...]) -> bool:
    """Return whether text contains any term."""

    return any(term in text for term in terms)


def path_contains_any(paths: tuple[str, ...], parts: tuple[str, ...]) -> bool:
    """Return whether any path contains a risky part."""

    lowered = tuple(path.lower() for path in paths)
    return any(part in path for path in lowered for part in parts)
