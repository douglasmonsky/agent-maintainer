"""Render attention ledger output."""

from __future__ import annotations

import json

from agent_maintainer.attention.models import AttentionFileScore, AttentionLedger


def render_ledger_json(ledger: AttentionLedger) -> str:
    """Render ledger as JSON."""
    return json.dumps(ledger.to_payload(), indent=2, sort_keys=True)


def render_top_json(ledger: AttentionLedger, *, limit: int) -> str:
    """Render only the requested leading attention scores as JSON."""

    payload = ledger.to_payload()
    files = payload["files"]
    if isinstance(files, list):
        payload["files"] = files[: max(0, limit)]
        payload["returned_file_count"] = len(payload["files"])
    return json.dumps(payload, indent=2, sort_keys=True)


def render_top_text(ledger: AttentionLedger, *, limit: int) -> str:
    """Render top attention files."""
    lines = [
        "Attention Ledger",
        f"Result: {ledger.file_count} scored files",
        f"Target: {ledger.target}",
        "",
        "Top files:",
    ]
    if not ledger.files:
        lines.append("- none")
    for score in ledger.files[:limit]:
        lines.append(f"- {score.score:.4f} {score.path}")
    return "\n".join(lines)


def render_explain_text(score: AttentionFileScore | None, *, path: str) -> str:
    """Render explanation for one path."""
    if score is None:
        return "\n".join(
            (
                "Attention Explain",
                f"Path: {path}",
                "Result: not scored",
            )
        )
    lines = [
        "Attention Explain",
        f"Path: {score.path}",
        f"Score: {score.score:.4f}",
        "",
        "Components:",
    ]
    lines.extend(f"- {name}: {value:.4f}" for name, value in score.components.items())
    lines.append("")
    lines.append("Reasons:")
    lines.extend(f"- {reason}" for reason in score.reasons)
    return "\n".join(lines)


def render_changed_text(ledger: AttentionLedger, *, limit: int) -> str:
    """Render currently changed attention files."""
    changed = tuple(
        score for score in ledger.files if score.components.get("git_changed", float(0)) > 0
    )
    lines = [
        "Attention Changed",
        f"Result: {len(changed)} changed scored files",
        "",
        "Changed files:",
    ]
    if not changed:
        lines.append("- none")
    for score in changed[:limit]:
        lines.append(f"- {score.score:.4f} {score.path}")
    return "\n".join(lines)
