"""CLI helpers for context pack commands."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from agent_context import pack_rendering
from agent_maintainer.context.compression import (
    backends as compression_backends,
)
from agent_maintainer.context.compression import (
    headroom as headroom_backend,
)
from agent_maintainer.context.pack import builder as packs
from agent_maintainer.core.config import load_config

FORMAT_JSON = "json"
FORMAT_TEXT = "text"
STORE_TRUE = "store_true"


def add_pack_parser(
    subparsers: Any,
) -> None:
    """Register context pack subcommand."""

    parser = subparsers.add_parser("pack", help="Write bounded repair context pack.")
    parser.add_argument("--budget", type=int)
    parser.add_argument("--check")
    parser.add_argument("--file", action="append", type=Path, default=[])
    parser.add_argument("--base-ref", default="HEAD")
    parser.add_argument(
        "--compress",
        choices=(
            compression_backends.BACKEND_NONE,
            compression_backends.BACKEND_TRUNCATE,
            compression_backends.BACKEND_EXTRACTIVE,
            headroom_backend.BACKEND_HEADROOM,
        ),
    )
    parser.add_argument("--require-compression", action=STORE_TRUE)
    parser.add_argument("--format", choices=(FORMAT_TEXT, FORMAT_JSON), default=FORMAT_TEXT)
    parser.add_argument(
        "--print-full",
        action=STORE_TRUE,
        help="Print full Markdown pack instead of compact pointer.",
    )


def run_pack(args: argparse.Namespace) -> int:
    """Run context pack subcommand."""

    config = load_config()
    budget = args.budget if isinstance(args.budget, int) else config.context_pack_budget_chars
    try:
        pack = packs.write_context_pack(
            packs.ContextPackRequest(
                log_dir=args.log_dir,
                budget=budget,
                check=args.check,
                files=tuple(args.file),
                base_ref=args.base_ref,
                baseline_path=Path(config.ratchet_baseline_path),
                failure_limit=config.context_max_failure_items,
                target_limit=config.ratchet_target_limit,
                compression_backend=compression_backend(args, config),
                compression_target_chars=compression_target_chars(budget, config),
                compression_required=(
                    args.require_compression
                    or getattr(config, "context_compression_require_backend", False)
                ),
            ),
        )
    except (
        headroom_backend.CompressionBackendError,
        headroom_backend.CompressionBackendUnavailable,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.format == FORMAT_JSON:
        output = pack_rendering.render_pack_json(pack.payload)
    elif args.print_full:
        output = pack.markdown
    else:
        output = pack_rendering.render_pack_pointer(
            pack.payload,
            display_path=str(pack.markdown_path),
        )
    print(output.rstrip())
    for warning in pack.warnings:
        print(f"WARN: {warning}", file=sys.stderr)
    return 0


def compression_backend(args: argparse.Namespace, config: object) -> str:
    """Return requested compression backend context packs."""

    if args.compress:
        return str(args.compress)
    if getattr(config, "context_compression_enabled", False):
        return str(getattr(config, "context_compression_backend", ""))
    return ""


def compression_target_chars(budget: int, config: object) -> int:
    """Return target character count compressed supporting items."""

    ratio = getattr(config, "context_compression_target_ratio", 0.5)
    return max(1, int(budget * ratio))
