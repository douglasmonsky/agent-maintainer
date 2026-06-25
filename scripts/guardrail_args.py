"""Argument parsing and CLI override handling for guardrail verification."""

from __future__ import annotations

import argparse
import os
from dataclasses import replace

from scripts.guardrail_config import (
    VALID_ARCHITECTURE_TOOLS,
    VALID_MODES,
    GuardrailConfig,
    apply_mode,
)

DEFAULT_MAX_LINES_PER_FAILURE = 50
DEFAULT_MAX_CHARS_PER_FAILURE = 8_000


def parse_csv_like(values: list[str] | None) -> tuple[str, ...] | None:
    if not values:
        return None
    items: list[str] = []
    for value in values:
        items.extend(part.strip() for part in value.split(","))
    normalized = tuple(item.rstrip("/") or "." for item in items if item)
    return normalized or None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run repository quality checks with low-noise output."
    )
    parser.add_argument(
        "--profile",
        choices=("fast", "precommit", "full", "ci"),
        default="full",
    )
    parser.add_argument("--base-ref", default=os.getenv("BASE_REF", "HEAD"))
    parser.add_argument("--compare-branch", default=os.getenv("COMPARE_BRANCH", "origin/main"))
    parser.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES_PER_FAILURE)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS_PER_FAILURE)
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Use staged changes for diff-based checks.",
    )
    parser.add_argument(
        "--mode",
        choices=sorted(VALID_MODES),
        help="Apply a guardrail preset for this run before other CLI overrides.",
    )

    add_path_overrides(parser)
    parser.add_argument("--coverage-fail-under", type=int)
    parser.add_argument("--diff-cover-fail-under", type=int)
    parser.add_argument("--require-tests", action="store_true", default=None)
    parser.add_argument("--no-require-tests", action="store_false", dest="require_tests")
    parser.add_argument("--enable-pip-audit", action="store_true", default=None)
    parser.add_argument("--disable-pip-audit", action="store_false", dest="enable_pip_audit")
    parser.add_argument("--enable-wemake", action="store_true", default=None)
    parser.add_argument("--disable-wemake", action="store_false", dest="enable_wemake")
    parser.add_argument("--enable-interrogate", action="store_true", default=None)
    parser.add_argument("--disable-interrogate", action="store_false", dest="enable_interrogate")
    parser.add_argument("--interrogate-fail-under", type=int)
    parser.add_argument(
        "--architecture-tool",
        choices=sorted(VALID_ARCHITECTURE_TOOLS),
        help="Architecture contract checker to use for this run.",
    )
    parser.add_argument(
        "--fail-on-optional-skip",
        action="store_true",
        help=(
            "Treat skipped optional integrations, such as absent architecture config, as failures."
        ),
    )
    return parser.parse_args(argv)


def add_path_overrides(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--source-root",
        action="append",
        help="Configured Python source root. May be repeated or comma-separated.",
    )
    parser.add_argument(
        "--test-root",
        action="append",
        help="Configured Python test root. May be repeated or comma-separated.",
    )
    parser.add_argument(
        "--coverage-source",
        action="append",
        help="Coverage source passed to pytest-cov. May be repeated or comma-separated.",
    )
    parser.add_argument(
        "--package-path",
        action="append",
        help="Package/source paths for static analysis. May be repeated or comma-separated.",
    )
    parser.add_argument(
        "--file-length-path",
        action="append",
        help="Paths scanned by the file-length check. May be repeated or comma-separated.",
    )
    parser.add_argument(
        "--vulture-path",
        action="append",
        help="Paths scanned by vulture. May be repeated or comma-separated.",
    )


def apply_cli_overrides(config: GuardrailConfig, args: argparse.Namespace) -> GuardrailConfig:
    if args.mode is not None:
        config = apply_mode(config, args.mode)

    updates: dict[str, object] = {}

    tuple_overrides = {
        "source_roots": parse_csv_like(args.source_root),
        "test_roots": parse_csv_like(args.test_root),
        "coverage_source": parse_csv_like(args.coverage_source),
        "package_paths": parse_csv_like(args.package_path),
        "file_length_paths": parse_csv_like(args.file_length_path),
        "vulture_paths": parse_csv_like(args.vulture_path),
    }
    scalar_overrides = {
        "coverage_fail_under": args.coverage_fail_under,
        "diff_cover_fail_under": args.diff_cover_fail_under,
        "require_tests": args.require_tests,
        "enable_pip_audit": args.enable_pip_audit,
        "enable_wemake": args.enable_wemake,
        "enable_interrogate": args.enable_interrogate,
        "interrogate_fail_under": args.interrogate_fail_under,
        "architecture_tool": args.architecture_tool,
    }

    updates.update({field: value for field, value in tuple_overrides.items() if value is not None})
    updates.update({field: value for field, value in scalar_overrides.items() if value is not None})

    return replace(config, **updates)
