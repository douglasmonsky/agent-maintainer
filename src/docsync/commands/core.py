"""Core DocSync command handlers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from docsync import api
from docsync.commands import object_markers
from docsync.config import defaults
from docsync.freshness import (
    build_freshness_report,
    default_freshness_path,
    render_freshness_text,
    write_freshness_report,
)
from docsync.reports import human, json_report, review_packet, sarif


# docsync:evidence.start evidence.docsync.generated_outputs_commands
def init_main_from_args(args: argparse.Namespace) -> int:
    """Create default DocSync repository files."""
    repo_root = args.repo_root.resolve()
    docsync_root = repo_root / ".docsync"
    files = {
        docsync_root / "config.yml": defaults.DEFAULT_CONFIG_TEXT,
        docsync_root / "trace.yml": (
            "version: 1\ndocuments: {}\nobjects: {}\nclaims: {}\nevidence: {}\n"
        ),
        docsync_root / "schema.json": defaults.DEFAULT_SCHEMA_TEXT,
        docsync_root / "attestations" / ".gitkeep": "",
        docsync_root / "out" / ".gitignore": "*\n!.gitignore\n",
    }
    for path, content in files.items():
        if path.exists() and not args.force:
            print(f"DocSync file already exists: {path}")
            return 1
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    if args.agents:
        _ensure_agents_section(repo_root / "AGENTS.md")
    print(f"Created DocSync files under {docsync_root}")
    return 0


def index_main_from_args(args: argparse.Namespace) -> int:
    """Write current trace-backed index."""
    result = api.build_index(
        api.IndexOptions(
            repo_root=args.repo_root.resolve(),
            config_path=args.config,
            trace_path=args.trace,
        )
    )
    result.output_path.parent.mkdir(parents=True, exist_ok=True)
    result.output_path.write_text(
        f"{json.dumps(result.to_json(), indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )
    print(f"Wrote DocSync index: {result.output_path}")
    return 1 if result.findings else 0


def freshness_main_from_args(args: argparse.Namespace) -> int:
    """Write passive freshness metadata for current DocSync index."""
    index = api.build_index(
        api.IndexOptions(
            repo_root=args.repo_root.resolve(),
            config_path=args.config,
            trace_path=args.trace,
        )
    )
    report = build_freshness_report(index)
    output_path = args.output or default_freshness_path(index)
    if not args.no_write:
        write_freshness_report(report, output_path)
    if args.format == "json":
        print(json.dumps(report.to_json(), indent=2, sort_keys=True))
    else:
        written_path = None if args.no_write else output_path
        print(render_freshness_text(report, written_path))
    return 0


def check_main_from_args(args: argparse.Namespace) -> int:
    """Run DocSync checks and print a human report."""
    result = api.check_repo(
        api.CheckOptions(
            repo_root=args.repo_root.resolve(),
            base_ref=args.base,
            config_path=args.config,
            trace_path=args.trace,
        )
    )
    print(human.render_check_result(result))
    json_report.write_report_json(result)
    sarif.write_sarif(result)
    return 0 if result.ok else 1


def doctor_main_from_args(args: argparse.Namespace) -> int:
    """Run structural DocSync validation."""
    repo_root = args.repo_root.resolve()
    if args.fix:
        _ensure_starter_dirs(repo_root)
        repair_result = object_markers.repair_object_end_markers(
            repo_root,
            config_path=args.config,
            trace_path=args.trace,
            write=True,
        )
        if repair_result.insertions:
            print(f"Inserted {len(repair_result.insertions)} DocSync object end marker(s).")
        _print_stale_generated_hint(repo_root)
    result = api.doctor_repo(
        api.CheckOptions(
            repo_root=repo_root,
            config_path=args.config,
            trace_path=args.trace,
        )
    )
    print(human.render_check_result(result))
    return 0 if result.ok else 1


def prompt_main_from_args(args: argparse.Namespace) -> int:
    """Write compact review packet and prompt findings."""
    result = api.check_repo(
        api.CheckOptions(
            repo_root=args.repo_root.resolve(),
            base_ref=args.base,
            config_path=args.config,
            trace_path=args.trace,
        )
    )
    packet_path = result.config.review_packet_json
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_json = json.dumps(api.create_review_packet(result), indent=2, sort_keys=True)
    packet_path.write_text(
        f"{packet_json}\n",
        encoding="utf-8",
    )
    prompt_path = result.config.review_prompt_md
    prompt_path.write_text(
        review_packet.review_prompt_for_result(result),
        encoding="utf-8",
    )
    print(f"Wrote DocSync review packet: {packet_path}")
    print(f"Wrote DocSync review prompt: {prompt_path}")
    return 0 if result.ok else 1


def attest_main_from_args(args: argparse.Namespace) -> int:
    """Create attestation evidence fingerprints."""
    path = api.create_attestation(
        args.repo_root.resolve(),
        args.claim_id,
        tuple(args.evidence),
        args.reason,
    )
    print(f"Wrote DocSync attestation: {path}")
    return 0


# docsync:evidence.end evidence.docsync.generated_outputs_commands
def _ensure_agents_section(path: Path) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else "# Repository Instructions\n"
    if "## DocSync policy" in existing:
        return
    path.write_text(
        f"{existing.rstrip()}\n{defaults.DOCSYNC_AGENTS_SECTION}",
        encoding="utf-8",
    )


def _ensure_starter_dirs(repo_root: Path) -> None:
    docsync_root = repo_root / ".docsync"
    attestations_dir = docsync_root / "attestations"
    out_dir = docsync_root / "out"
    attestations_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = attestations_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("", encoding="utf-8")
    gitignore = out_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("*\n!.gitignore\n", encoding="utf-8")


def _print_stale_generated_hint(repo_root: Path) -> None:
    trace_path = repo_root / ".docsync" / "trace.yml"
    out_dir = repo_root / ".docsync" / "out"
    if not trace_path.exists() or not out_dir.exists():
        return
    trace_mtime = trace_path.stat().st_mtime
    stale = sorted(
        path.relative_to(repo_root)
        for path in out_dir.iterdir()
        if path.is_file() and path.name != ".gitignore" and path.stat().st_mtime < trace_mtime
    )
    if stale:
        joined = ", ".join(str(path) for path in stale)
        print(f"DocSync generated output may be stale: {joined}")
