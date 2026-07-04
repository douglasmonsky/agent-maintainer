"""Passive freshness metadata for DocSync objects and evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess  # nosec B404
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from docsync.core.models import DocObject, DocSyncIndex, EvidenceAnchor

FreshnessStatus = Literal["current", "missing"]

FRESHNESS_VERSION = 1
DEFAULT_FRESHNESS_FILENAME = "freshness.json"
GIT_TIMEOUT_SECONDS = 5


@dataclass(frozen=True)
class RepoFreshnessState:
    """Cheap repository state associated with a freshness observation."""

    head: str | None
    dirty: bool | None
    worktree_fingerprint: str | None

    def to_json(self) -> dict[str, Any]:
        """Return JSON-ready repository state."""
        return {
            "head": self.head,
            "dirty": self.dirty,
            "worktree_fingerprint": self.worktree_fingerprint,
        }


@dataclass(frozen=True)
class FreshnessEntry:
    """Freshness metadata for one DocSync object or evidence id."""

    item_id: str
    status: FreshnessStatus
    path: str | None
    content_hash: str | None
    observed_at: str
    last_observed_commit: str | None
    last_observed_worktree_fingerprint: str | None
    anchor_count: int | None = None

    def to_json(self) -> dict[str, Any]:
        """Return JSON-ready freshness entry."""
        payload: dict[str, Any] = {
            "id": self.item_id,
            "status": self.status,
            "path": self.path,
            "content_hash": self.content_hash,
            "observed_at": self.observed_at,
            "last_observed_commit": self.last_observed_commit,
            "last_observed_worktree_fingerprint": (self.last_observed_worktree_fingerprint),
        }
        if self.anchor_count is not None:
            payload["anchor_count"] = self.anchor_count
        return payload


@dataclass(frozen=True)
class FreshnessReport:
    """Passive DocSync freshness report."""

    observed_at: str
    repo: RepoFreshnessState
    objects: tuple[FreshnessEntry, ...]
    evidence: tuple[FreshnessEntry, ...]

    @property
    def ok(self) -> bool:
        """Return whether every traced object and evidence anchor was observed."""
        return not any(entry.status == "missing" for entry in (*self.objects, *self.evidence))

    def to_json(self) -> dict[str, Any]:
        """Return JSON-ready freshness report."""
        return {
            "version": FRESHNESS_VERSION,
            "observed_at": self.observed_at,
            "ok": self.ok,
            "repo": self.repo.to_json(),
            "summary": _summary(self.objects, self.evidence),
            "objects": {entry.item_id: entry.to_json() for entry in self.objects},
            "evidence": {entry.item_id: entry.to_json() for entry in self.evidence},
        }


def default_freshness_path(index: DocSyncIndex) -> Path:
    """Return the default generated freshness output path."""
    return index.config.index_json.parent / DEFAULT_FRESHNESS_FILENAME


def build_freshness_report(
    index: DocSyncIndex,
    *,
    observed_at: str | None = None,
) -> FreshnessReport:
    """Build passive freshness metadata from an already resolved index."""
    observed = observed_at or datetime.now(tz=UTC).isoformat()
    repo = _repo_state(index.config.repo_root)
    return FreshnessReport(
        observed_at=observed,
        repo=repo,
        objects=tuple(_object_entries(index, repo, observed)),
        evidence=tuple(_evidence_entries(index, repo, observed)),
    )


def write_freshness_report(report: FreshnessReport, output_path: Path) -> None:
    """Write freshness report JSON to generated output path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        f"{json.dumps(report.to_json(), indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )


def render_freshness_text(report: FreshnessReport, output_path: Path | None) -> str:
    """Render compact human freshness summary."""
    object_counts = _status_counts(report.objects)
    evidence_counts = _status_counts(report.evidence)
    lines = [
        "DocSync freshness metadata",
        f"Objects: {object_counts['current']} current, {object_counts['missing']} missing",
        f"Evidence: {evidence_counts['current']} current, {evidence_counts['missing']} missing",
    ]
    if output_path is not None:
        lines.append(f"Wrote: {output_path.as_posix()}")
    if not report.ok:
        lines.append("Repair: run `python -m docsync check` for exact missing items.")
    return "\n".join(lines)


def _object_entries(
    index: DocSyncIndex,
    repo: RepoFreshnessState,
    observed_at: str,
) -> list[FreshnessEntry]:
    entries: list[FreshnessEntry] = []
    for object_id, trace_object in sorted(index.trace.objects.items()):
        entries.append(
            _object_entry(
                object_id,
                trace_object.path,
                index.doc_objects.get(object_id),
                repo,
                observed_at,
            )
        )
    return entries


def _object_entry(
    object_id: str,
    trace_path: Path,
    doc_object: DocObject | None,
    repo: RepoFreshnessState,
    observed_at: str,
) -> FreshnessEntry:
    if doc_object:
        return FreshnessEntry(
            item_id=object_id,
            status="current",
            path=doc_object.path.as_posix(),
            content_hash=doc_object.content_hash,
            observed_at=observed_at,
            last_observed_commit=repo.head,
            last_observed_worktree_fingerprint=repo.worktree_fingerprint,
        )
    return FreshnessEntry(
        item_id=object_id,
        status="missing",
        path=trace_path.as_posix(),
        content_hash=None,
        observed_at=observed_at,
        last_observed_commit=repo.head,
        last_observed_worktree_fingerprint=repo.worktree_fingerprint,
    )


def _evidence_entries(
    index: DocSyncIndex,
    repo: RepoFreshnessState,
    observed_at: str,
) -> list[FreshnessEntry]:
    entries: list[FreshnessEntry] = []
    for evidence_id, trace_evidence in sorted(index.trace.evidence.items()):
        anchors = index.evidence_anchors.get(evidence_id, ())
        entries.append(
            FreshnessEntry(
                item_id=evidence_id,
                status="current" if anchors else "missing",
                path=_evidence_path(trace_evidence, anchors),
                content_hash=_evidence_content_hash(anchors),
                observed_at=observed_at,
                last_observed_commit=repo.head,
                last_observed_worktree_fingerprint=repo.worktree_fingerprint,
                anchor_count=len(anchors),
            )
        )
    return entries


def _repo_state(repo_root: Path) -> RepoFreshnessState:
    head = _git_output(repo_root, "rev-parse", "HEAD")
    status = _git_output(repo_root, "status", "--porcelain=v1")
    if status is None:
        return RepoFreshnessState(
            head=head,
            dirty=None,
            worktree_fingerprint=None,
        )
    return RepoFreshnessState(
        head=head,
        dirty=bool(status.strip()),
        worktree_fingerprint=_sha256_text(status),
    )


def _git_output(repo_root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(  # nosec B603
            ("git", *args),
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _evidence_path(
    trace_evidence: object,
    anchors: tuple[EvidenceAnchor, ...],
) -> str | None:
    if anchors:
        return anchors[0].path.as_posix()
    trace_anchors = getattr(trace_evidence, "anchors", ())
    if trace_anchors:
        return trace_anchors[0].path.as_posix()
    return None


def _evidence_content_hash(anchors: tuple[EvidenceAnchor, ...]) -> str | None:
    if not anchors:
        return None
    if len(anchors) == 1:
        return anchors[0].content_hash
    return _sha256_text("\n".join(anchor.content_hash for anchor in anchors))


def _summary(
    objects: tuple[FreshnessEntry, ...],
    evidence: tuple[FreshnessEntry, ...],
) -> dict[str, Any]:
    return {
        "objects": _status_counts(objects),
        "evidence": _status_counts(evidence),
    }


def _status_counts(entries: tuple[FreshnessEntry, ...]) -> dict[str, int]:
    return {
        "current": sum(1 for entry in entries if entry.status == "current"),
        "missing": sum(1 for entry in entries if entry.status == "missing"),
    }


def _sha256_text(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
