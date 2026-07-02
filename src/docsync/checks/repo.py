"""Repository-level DocSync checks."""

from __future__ import annotations

from pathlib import Path

from docsync.attestations.load import load_attestations
from docsync.checks.claims import changed_claim_findings
from docsync.checks.doctor import run_doctor
from docsync.core.models import CheckResult, Finding
from docsync.git.diff import GitDiffError, changed_line_spans


def run_check(
    *,
    repo_root: Path,
    config_path: Path | None,
    trace_path: Path | None,
    base_ref: str,
) -> CheckResult:
    """Run structural and changed-claim checks for a repository."""
    doctor_result = run_doctor(
        repo_root=repo_root,
        config_path=config_path,
        trace_path=trace_path,
        command="check",
        base_ref=base_ref,
    )
    if not doctor_result.ok or doctor_result.index is None:
        return doctor_result
    try:
        changed_spans = changed_line_spans(doctor_result.repo_root, base_ref)
    except GitDiffError as exc:
        return CheckResult(
            command="check",
            repo_root=doctor_result.repo_root,
            config=doctor_result.config,
            findings=(_git_finding(exc.message),),
            base_ref=base_ref,
            index=doctor_result.index,
        )
    attestations = load_attestations(doctor_result.index)
    findings = (
        *attestations.findings,
        *changed_claim_findings(doctor_result.index, changed_spans, attestations),
    )
    return CheckResult(
        command="check",
        repo_root=doctor_result.repo_root,
        config=doctor_result.config,
        findings=findings,
        base_ref=base_ref,
        index=doctor_result.index,
    )


def _git_finding(message: str) -> Finding:
    return Finding(
        code="DS000",
        severity="error",
        message=f"Unable to read Git diff: {message}",
    )
