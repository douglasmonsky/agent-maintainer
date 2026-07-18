"""Stable JSON and human-readable verification-plan rendering."""

from __future__ import annotations

import json
from collections.abc import Sequence

from agent_maintainer.verification_plan.models import (
    AffectedUnit,
    PathClassification,
    PlannedChange,
    RequirementResult,
    VerificationPlanReport,
)

MAX_TEXT_ITEMS = 100
MAX_UNIT_PATHS = 100
TextItem = AffectedUnit | PlannedChange | RequirementResult | str


def report_to_dict(report: VerificationPlanReport) -> dict[str, object]:
    """Return the intentional schema-versioned public report mapping."""
    return {
        "advisories": list(report.advisories),
        "affected_units": [_unit_to_dict(unit) for unit in report.affected_units],
        "base_ref": report.base_ref,
        "blocking_findings": list(report.blocking_findings),
        "changes": [_change_to_dict(change) for change in report.changes],
        "matched_rules": list(report.matched_rules),
        "policy_configured": report.policy_configured,
        "policy_path": report.policy_path,
        "recommended_commands": list(report.recommended_commands),
        "requirements": [_requirement_to_dict(requirement) for requirement in report.requirements],
        "review_categories": list(report.review_categories),
        "schema_version": report.schema_version,
        "selected_checks": list(report.selected_checks),
        "selected_profiles": list(report.selected_profiles),
        "staged": report.staged,
        "target": report.target,
    }


def render_json(report: VerificationPlanReport) -> str:
    """Render stable pretty JSON with exactly one trailing newline."""
    return "\n".join((json.dumps(report_to_dict(report), indent=2, sort_keys=True), ""))


def render_text(report: VerificationPlanReport) -> str:
    """Render one bounded, deterministic human-readable plan."""
    lines = [
        f"Verification plan for {_safe_text(report.target)}",
        "",
        "Policy:",
        f"- Path: {_safe_text(report.policy_path)}",
        f"- Configured: {_configured_text(report)}",
        f"- Diff: {_diff_text(report)}",
    ]
    _section(lines, "Changed paths", report.changes)
    _section(
        lines,
        "Affected units",
        report.affected_units,
    )
    _section(
        lines,
        "Requirements",
        report.requirements,
    )
    _string_section(lines, "Review categories", report.review_categories)
    _string_section(lines, "Recommended commands", report.recommended_commands)
    _string_section(lines, "Advisories", report.advisories)
    if report.blocking_findings:
        _string_section(lines, "Blocking findings", report.blocking_findings)
    else:
        _string_section(lines, "Ready", ("No blocking findings.",))
    return "\n".join((*lines, ""))


def _change_to_dict(change: PlannedChange) -> dict[str, object]:
    result: dict[str, object] = {
        "classifications": [_classification_to_dict(item) for item in change.classifications],
        "kind": change.kind,
        "path": change.path,
    }
    if change.old_path is not None:
        result["old_path"] = change.old_path
    return result


def _classification_to_dict(item: PathClassification) -> dict[str, object]:
    return {
        "ecosystem": item.ecosystem,
        "generated": item.generated,
        "ignored": item.ignored,
        "path": item.path,
        "relation": item.relation,
        "role": item.role,
    }


def _unit_to_dict(unit: AffectedUnit) -> dict[str, object]:
    return {
        "changed_paths": list(unit.changed_paths),
        "kind": unit.kind,
        "name": unit.name,
        "root": unit.root,
    }


def _requirement_to_dict(requirement: RequirementResult) -> dict[str, object]:
    return {
        "id": requirement.id,
        "kind": requirement.kind,
        "matched_paths": list(requirement.matched_paths),
        "message": requirement.message,
        "minimum": requirement.minimum,
        "mode": requirement.mode,
        "paths": list(requirement.paths),
        "rule_id": requirement.rule_id,
        "status": requirement.status,
    }


def _change_text(change: PlannedChange) -> str:
    if change.old_path is not None:
        return (
            f"{_safe_text(change.kind)}: {_safe_text(change.old_path)} -> {_safe_text(change.path)}"
        )
    return f"{_safe_text(change.kind)}: {_safe_text(change.path)}"


def _unit_text(unit: AffectedUnit) -> str:
    visible_paths = unit.changed_paths[:MAX_UNIT_PATHS]
    paths = ", ".join(_safe_text(path) for path in visible_paths)
    omitted = len(unit.changed_paths) - len(visible_paths)
    suffix = f", ... {omitted} more paths" if omitted else ""
    return (
        f"{_safe_text(unit.kind)} {_safe_text(unit.name)} "
        f"({_safe_text(unit.root)}): {paths}{suffix}"
    )


def _requirement_text(requirement: RequirementResult) -> str:
    identity = f"{requirement.rule_id}/{requirement.id}"
    progress = f"{len(requirement.matched_paths)}/{requirement.minimum}"
    return (
        f"[{_safe_text(requirement.status)}] {_safe_text(identity)} "
        f"({progress}): {_safe_text(requirement.message)}"
    )


def _configured_text(report: VerificationPlanReport) -> str:
    return "yes" if report.policy_configured else "no"


def _diff_text(report: VerificationPlanReport) -> str:
    return "staged changes" if report.staged else _safe_text(report.base_ref)


def _string_section(lines: list[str], title: str, items: Sequence[str]) -> None:
    _section(lines, title, items)


def _safe_text(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)[1:-1]


def _section(
    lines: list[str],
    title: str,
    items: Sequence[TextItem],
) -> None:
    lines.extend(("", f"{title}:"))
    if not items:
        lines.append("- None")
        return
    visible = items[:MAX_TEXT_ITEMS]
    lines.extend(f"- {_item_text(item)}" for item in visible)
    omitted = len(items) - len(visible)
    if omitted:
        lines.append(f"- ... {omitted} more")


def _item_text(item: TextItem) -> str:
    if isinstance(item, PlannedChange):
        return _change_text(item)
    if isinstance(item, AffectedUnit):
        return _unit_text(item)
    if isinstance(item, RequirementResult):
        return _requirement_text(item)
    return _safe_text(item)
