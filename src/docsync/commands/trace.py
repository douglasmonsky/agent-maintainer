"""DocSync trace authoring command handlers."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

from docsync.trace import edit

TraceEdit = Callable[..., Path]


def add_document_main_from_args(args: argparse.Namespace) -> int:
    """Add one document entry to the DocSync trace."""
    return _run_edit(
        edit.add_document,
        args,
        args.document_id,
        edit.DocumentEdit(
            path=args.path,
            title=args.title,
            audience=args.audience,
            force=args.force,
        ),
    )


def add_object_main_from_args(args: argparse.Namespace) -> int:
    """Add one object entry to the DocSync trace."""
    return _run_edit(
        edit.add_object,
        args,
        args.object_id,
        edit.ObjectEdit(
            document_id=args.document,
            path=args.path,
            marker=args.marker,
            heading_level=args.heading_level,
            heading_text=args.heading_text,
            insert_marker=args.insert_marker,
            force=args.force,
        ),
    )


def add_evidence_main_from_args(args: argparse.Namespace) -> int:
    """Add one evidence entry to the DocSync trace."""
    return _run_edit(
        edit.add_evidence,
        args,
        args.evidence_id,
        edit.EvidenceEdit(
            path=args.path,
            evidence_type=args.type,
            description=args.description,
            insert_region=args.insert_region,
            force=args.force,
        ),
    )


def add_claim_main_from_args(args: argparse.Namespace) -> int:
    """Add one claim entry to the DocSync trace."""
    return _run_edit(
        edit.add_claim,
        args,
        args.claim_id,
        edit.ClaimEdit(
            object_id=args.object,
            text=args.text,
            severity=args.severity,
            evidence_ids=tuple(args.evidence),
            force=args.force,
        ),
    )


def list_main_from_args(args: argparse.Namespace) -> int:
    """Print trace IDs grouped by section."""
    try:
        summary = edit.trace_summary(args.repo_root.resolve(), args.trace)
    except edit.TraceEditError as exc:
        print(f"DocSync trace edit failed: {exc}")
        return 1
    for section, item_ids in summary.items():
        print(f"{section}:")
        for item_id in item_ids:
            print(f"  - {item_id}")
    return 0


def add_common_options(parser: argparse.ArgumentParser) -> None:
    """Add shared trace edit options."""
    parser.add_argument("--trace", type=Path, default=None)
    parser.add_argument("--force", action="store_true")


def _run_edit(
    function: TraceEdit,
    args: argparse.Namespace,
    item_id: str,
    options: object,
) -> int:
    try:
        path = function(args.repo_root.resolve(), args.trace, item_id, options)
    except edit.TraceEditError as exc:
        print(f"DocSync trace edit failed: {exc}")
        return 1
    print(f"Updated DocSync trace: {path}")
    return 0
