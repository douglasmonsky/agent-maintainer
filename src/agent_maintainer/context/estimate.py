"""Estimate bounded context expansion size."""

from __future__ import annotations

import json
import subprocess  # nosec B404
from dataclasses import dataclass, field
from pathlib import Path

from agent_maintainer.context.failures import (
    DEFAULT_CONTEXT_BUDGET,
    failure_records,
    render_failures_text,
)
from agent_maintainer.context.logs import LogRequest, resolve_log_path, slice_text

TOKEN_CHAR_RATIO = 4
DEFAULT_DIFF_CONTEXT_LINES = 3


@dataclass(frozen=True)
class ContextEstimate:
    """Estimated context expansion size."""

    label: str
    chars: int
    tokens: int
    budget: int
    recommended: str

    def to_json(self) -> dict[str, object]:
        """Return stable JSON payload."""

        return {
            "label": self.label,
            "chars": self.chars,
            "tokens": self.tokens,
            "budget": self.budget,
            "recommended": self.recommended,
        }


@dataclass(frozen=True)
class EstimateRequest:
    """Requested context estimate target."""

    log_dir: Path
    file_path: Path | None = None
    log_check: str | None = None
    log_request: LogRequest = field(default_factory=lambda: LogRequest(confirm_large=True))
    diff: bool = False
    diff_summary: bool = False
    budget: int = DEFAULT_CONTEXT_BUDGET


def estimate_context(request: EstimateRequest) -> ContextEstimate:
    """Return context size estimate for requested source."""

    if request.file_path is not None:
        return estimate_file(request.file_path, request.budget)
    if request.log_check is not None:
        return estimate_log(request.log_dir, request.log_check, request.log_request, request.budget)
    if request.diff:
        return estimate_diff(request.diff_summary, request.budget)
    return estimate_failures(request.log_dir, request.budget)


def estimate_file(path: Path, budget: int) -> ContextEstimate:
    """Return output estimate for a file expansion."""

    text = read_text(path)
    return build_estimate(
        label=f"file {path}",
        chars=len(text),
        budget=budget,
        recommended=f"--file {path} --budget {recommend_budget(len(text))} --confirm-large",
    )


def estimate_log(
    log_dir: Path,
    check_name: str,
    log_request: LogRequest,
    budget: int,
) -> ContextEstimate:
    """Return output estimate for a verifier log expansion."""

    path = resolve_log_path(log_dir, check_name)
    text = read_text(path)
    selected, _omitted_lines = slice_text(text, log_request)
    return build_estimate(
        label=f"log {check_name}",
        chars=len(selected),
        budget=budget,
        recommended=log_recommendation(check_name, len(selected)),
    )


def estimate_diff(summary: bool, budget: int) -> ContextEstimate:
    """Return output estimate for current Git diff expansion."""

    args = (
        ["git", "diff", "--stat"]
        if summary
        else ["git", "diff", f"--unified={DEFAULT_DIFF_CONTEXT_LINES}"]
    )
    text = run_git_diff(args)
    return build_estimate(
        label="diff summary" if summary else "diff",
        chars=len(text),
        budget=budget,
        recommended=f"--diff --budget {recommend_budget(len(text))} --confirm-large",
    )


def estimate_failures(log_dir: Path, budget: int) -> ContextEstimate:
    """Return output estimate for current failure summary."""

    text = render_failures_text(failure_records(log_dir), log_dir=log_dir, budget=budget)
    return build_estimate(
        label="failures",
        chars=len(text),
        budget=budget,
        recommended=f"--budget {recommend_budget(len(text))}",
    )


def build_estimate(label: str, chars: int, budget: int, recommended: str) -> ContextEstimate:
    """Build normalized estimate payload."""

    return ContextEstimate(
        label=label,
        chars=chars,
        tokens=estimate_tokens(chars),
        budget=budget,
        recommended=recommended,
    )


def estimate_tokens(chars: int) -> int:
    """Estimate token count from character count."""

    return (chars + TOKEN_CHAR_RATIO - 1) // TOKEN_CHAR_RATIO


def recommend_budget(chars: int) -> int:
    """Return rounded budget that can fit estimated output."""

    return max(DEFAULT_CONTEXT_BUDGET, chars)


def log_recommendation(check_name: str, chars: int) -> str:
    """Return safer log expansion recommendation."""

    budget = recommend_budget(chars)
    return f"--log {check_name} --tail 120 --budget {budget} --confirm-large"


def read_text(path: Path) -> str:
    """Read UTF-8 text returning empty text when missing."""

    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def run_git_diff(args: list[str]) -> str:
    """Return Git diff output for current repository."""

    result = subprocess.run(  # nosec B603
        args,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout


def render_estimate_text(estimate: ContextEstimate) -> str:
    """Return human-readable estimate output."""

    return "\n".join(
        (
            f"Estimated output: {estimate.label}",
            f"chars: {estimate.chars:,}",
            f"tokens: ~{estimate.tokens:,}",
            f"default budget: {estimate.budget:,} chars",
            f"Recommended: {estimate.recommended}",
        ),
    )


def render_estimate_json(estimate: ContextEstimate) -> str:
    """Return stable JSON estimate output."""

    return json.dumps(estimate.to_json(), indent=2, sort_keys=True)
