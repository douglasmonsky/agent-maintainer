"""Line-oriented source evidence scanner."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docsync.core.fingerprints import sha256_text
from docsync.core.models import EvidenceAnchor, Finding, LineSpan


@dataclass(frozen=True)
class EvidenceScanResult:
    """Resolved evidence regions and scanner findings."""

    anchors: tuple[EvidenceAnchor, ...]
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class OpenRegion:
    """Open source evidence region while scanning."""

    evidence_id: str
    line_number: int


@dataclass(frozen=True)
class ScanContext:
    """Stable inputs for one evidence scan."""

    path: Path
    lines: list[str]
    start_directive: str
    end_directive: str


@dataclass
class ScanState:
    """Mutable evidence scan state."""

    anchors: list[EvidenceAnchor]
    findings: list[Finding]
    open_region: OpenRegion | None = None


# docsync:evidence.start evidence.docsync.explicit_evidence_scanner
def scan_evidence_file(
    repo_root: Path,
    path: Path,
    *,
    start_directive: str,
    end_directive: str,
) -> EvidenceScanResult:
    """Scan one file for explicit DocSync evidence regions."""

    relative_path = path
    full_path = repo_root / relative_path
    if not full_path.exists():
        return EvidenceScanResult(
            anchors=(),
            findings=(
                Finding(
                    code="DS005",
                    severity="error",
                    message=f"Evidence anchor path does not exist: {relative_path}",
                    locations=(_line(relative_path),),
                ),
            ),
        )
    lines = full_path.read_text(encoding="utf-8").splitlines()
    context = ScanContext(
        path=relative_path,
        lines=lines,
        start_directive=start_directive,
        end_directive=end_directive,
    )
    state = ScanState(anchors=[], findings=[])
    for line_number, line in enumerate(lines, start=1):
        _scan_line(context, state, line_number, line)
    _close_unfinished_region(context, state)
    state.findings.extend(_empty_region_findings(state.anchors))
    return EvidenceScanResult(
        anchors=tuple(state.anchors),
        findings=tuple(state.findings),
    )


def _scan_line(
    context: ScanContext,
    state: ScanState,
    line_number: int,
    line: str,
) -> None:
    """Update scan state for one source line."""

    start_id = _directive_id(line, context.start_directive)
    end_id = _directive_id(line, context.end_directive)
    if start_id is not None:
        _handle_start(context, state, line_number, start_id)
    if end_id is not None:
        _handle_end(context, state, line_number, end_id)


def _handle_start(
    context: ScanContext,
    state: ScanState,
    line_number: int,
    evidence_id: str,
) -> None:
    """Handle an evidence-region start marker."""

    if state.open_region is not None:
        state.findings.append(
            _finding("DS004", "Nested evidence region.", context.path, line_number)
        )
        return
    state.open_region = OpenRegion(evidence_id=evidence_id, line_number=line_number)


def _handle_end(
    context: ScanContext,
    state: ScanState,
    line_number: int,
    evidence_id: str,
) -> None:
    """Handle an evidence-region end marker."""

    if state.open_region is None:
        state.findings.append(
            _finding("DS002", "Evidence region end without start.", context.path, line_number)
        )
        return
    if evidence_id != state.open_region.evidence_id:
        state.findings.append(
            _finding("DS003", "Evidence region ID mismatch.", context.path, line_number)
        )
        state.open_region = None
        return
    state.anchors.append(_anchor(context.path, context.lines, state.open_region, line_number))
    state.open_region = None


def _close_unfinished_region(context: ScanContext, state: ScanState) -> None:
    """Record an unclosed evidence region if one remains."""

    if state.open_region is None:
        return
    evidence_id = state.open_region.evidence_id
    state.findings.append(
        _finding(
            "DS001",
            f"Evidence region {evidence_id} was not closed.",
            context.path,
            state.open_region.line_number,
        )
    )


def _anchor(
    path: Path,
    lines: list[str],
    open_region: OpenRegion,
    end_line: int,
) -> EvidenceAnchor:
    """Return a resolved evidence anchor."""

    content_start = open_region.line_number + 1
    content_end = end_line - 1
    content_start_index = content_start - 1
    content = "\n".join(lines[content_start_index:content_end])
    return EvidenceAnchor(
        evidence_id=open_region.evidence_id,
        path=path,
        span=LineSpan(path=path, start_line=open_region.line_number, end_line=end_line),
        content_span=LineSpan(path=path, start_line=content_start, end_line=content_end),
        content_hash=sha256_text(content),
    )


def _empty_region_findings(anchors: list[EvidenceAnchor]) -> list[Finding]:
    """Return findings for empty evidence regions."""

    return [
        Finding(
            code="DS008",
            severity="error",
            message=f"Evidence region {anchor.evidence_id} is empty.",
            locations=(anchor.span,),
            related_evidence=(anchor.evidence_id,),
        )
        for anchor in anchors
        if anchor.content_span.end_line < anchor.content_span.start_line
    ]


def _directive_id(line: str, directive: str) -> str | None:
    """Return evidence ID following a source directive marker."""

    marker_index = line.find(directive)
    if marker_index < 0:
        return None
    suffix_start = marker_index + len(directive)
    suffix = line[suffix_start:].strip()
    if suffix.startswith(":"):
        suffix = suffix[1:].strip()
    return suffix.split()[0] if suffix else None


# docsync:evidence.end evidence.docsync.explicit_evidence_scanner
def _finding(code: str, message: str, path: Path, line: int) -> Finding:
    """Return one evidence scanner finding."""

    return Finding(
        code=code,
        severity="error",
        message=message,
        locations=(_line(path, line),),
    )


def _line(path: Path, line: int = 1) -> LineSpan:
    """Return one source line span."""

    return LineSpan(path=path, start_line=line, end_line=line)
