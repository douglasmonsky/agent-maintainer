"""Core DocSync command handlers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from docsync import api
from docsync.commands import object_markers
from docsync.config import defaults
from docsync.config.io import read_bounded_text, validate_write_target, write_text_file
from docsync.config.paths import (
    require_strict_descendant,
    require_unreserved_output,
    resolve_directory_within,
    resolve_within,
)
from docsync.core.models import DocSyncIndex
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
    docsync_root = resolve_directory_within(
        repo_root,
        Path(".docsync"),
        label="DocSync state directory",
    )
    files = _initializer_files(repo_root)
    agents_path, agents_content = _initializer_agents(repo_root, enabled=args.agents)
    existing_paths = tuple(path for path in files if path.exists())
    if existing_paths and not args.force:
        print(f"DocSync file already exists: {existing_paths[0]}")
        return 1
    _write_initializer_files(files)
    if agents_path is not None and agents_content is not None:
        write_text_file(agents_path, agents_content, label="DocSync AGENTS.md output")
    print(f"Created DocSync files under {docsync_root}")
    return 0


def _initializer_files(repo_root: Path) -> dict[Path, str]:
    """Return every preflighted DocSync starter file."""

    candidates = {
        Path(".docsync/config.yml"): defaults.DEFAULT_CONFIG_TEXT,
        Path(".docsync/trace.yml"): (
            "version: 1\ndocuments: {}\nobjects: {}\nclaims: {}\nevidence: {}\n"
        ),
        Path(".docsync/schema.json"): defaults.DEFAULT_SCHEMA_TEXT,
        Path(".docsync/attestations/.gitkeep"): "",
        Path(".docsync/out/.gitignore"): "*\n!.gitignore\n",
    }
    return {
        validate_write_target(
            resolve_within(repo_root, candidate, label="DocSync initializer output"),
            label="DocSync initializer output",
        ): content
        for candidate, content in candidates.items()
    }


def _initializer_agents(repo_root: Path, *, enabled: bool) -> tuple[Path | None, str | None]:
    """Return the preflighted optional AGENTS.md update."""

    if enabled:
        agents_path = validate_write_target(
            resolve_within(
                repo_root,
                Path("AGENTS.md"),
                label="DocSync AGENTS.md output",
            ),
            label="DocSync AGENTS.md output",
        )
        return agents_path, _agents_section_content(agents_path)
    return None, None


def _write_initializer_files(files: dict[Path, str]) -> None:
    """Write a fully preflighted starter-file set."""

    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        write_text_file(path, content, label="DocSync initializer output")


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
    write_text_file(
        result.output_path,
        f"{json.dumps(result.to_json(), indent=2, sort_keys=True)}\n",
        label="DocSync index output",
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
    output_path = _freshness_output_path(index, args.output)
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
    if args.write_reports and result.inputs_valid:
        validate_write_target(result.config.report_json, label="DocSync JSON report output")
        validate_write_target(
            result.config.report_json.with_suffix(".sarif.json"),
            label="DocSync SARIF report output",
        )
        json_report.write_report_json(result)
        sarif.write_sarif(result)
    return 0 if result.ok else 1


def doctor_main_from_args(args: argparse.Namespace) -> int:
    """Run structural DocSync validation."""
    repo_root = args.repo_root.resolve()
    if args.fix:
        starter_paths = _starter_paths(repo_root)
        repair_result = object_markers.repair_object_end_markers(
            repo_root,
            config_path=args.config,
            trace_path=args.trace,
            write=True,
        )
        _ensure_starter_dirs(starter_paths)
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
    if not result.inputs_valid:
        print(human.render_check_result(result))
        return 1
    packet_path = result.config.review_packet_json
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_json = json.dumps(api.create_review_packet(result), indent=2, sort_keys=True)
    write_text_file(
        packet_path,
        f"{packet_json}\n",
        label="DocSync review-packet output",
    )
    prompt_path = result.config.review_prompt_md
    write_text_file(
        prompt_path,
        review_packet.review_prompt_for_result(result),
        label="DocSync review-prompt output",
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
def _agents_section_content(path: Path) -> str | None:
    existing = (
        read_bounded_text(path, label="DocSync AGENTS.md input")
        if path.exists()
        else "# Repository Instructions\n"
    )
    if "## DocSync policy" in existing:
        return None
    return f"{existing.rstrip()}\n{defaults.DOCSYNC_AGENTS_SECTION}"


def _starter_paths(repo_root: Path) -> tuple[Path, Path, Path, Path]:
    resolve_directory_within(
        repo_root,
        Path(".docsync"),
        label="DocSync state directory",
    )
    attestations_dir = resolve_directory_within(
        repo_root,
        Path(".docsync/attestations"),
        label="DocSync attestation directory",
    )
    out_dir = resolve_directory_within(
        repo_root,
        Path(".docsync/out"),
        label="DocSync generated-output directory",
    )
    gitkeep = attestations_dir / ".gitkeep"
    gitignore = out_dir / ".gitignore"
    validate_write_target(gitkeep, label="DocSync attestation placeholder")
    validate_write_target(gitignore, label="DocSync output ignore file")
    return attestations_dir, out_dir, gitkeep, gitignore


def _ensure_starter_dirs(paths: tuple[Path, Path, Path, Path]) -> None:
    attestations_dir, out_dir, gitkeep, gitignore = paths
    attestations_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not gitkeep.exists():
        write_text_file(gitkeep, "", label="DocSync attestation placeholder")
    if not gitignore.exists():
        write_text_file(gitignore, "*\n!.gitignore\n", label="DocSync output ignore file")


def _freshness_output_path(index: DocSyncIndex, configured: Path | None) -> Path:
    if configured is None:
        return default_freshness_path(index)
    resolved = resolve_within(
        index.config.repo_root,
        configured,
        label="DocSync freshness output",
    )
    contained = require_strict_descendant(
        index.config.output_dir,
        resolved,
        label="DocSync freshness output",
    )
    allowed = require_unreserved_output(contained, label="DocSync freshness output")
    return validate_write_target(allowed, label="DocSync freshness output")


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
