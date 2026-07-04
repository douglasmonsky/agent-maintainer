"""Argument parsing and CLI override handling for maintainer verification."""

from __future__ import annotations

import argparse
import os
from dataclasses import replace

from agent_maintainer.config.modes import apply_mode
from agent_maintainer.config.schema import (
    VALID_ARCHITECTURE_TOOLS,
    VALID_MODES,
    MaintainerConfig,
)
from agent_maintainer.models import VALID_PROFILES

DEFAULT_MAX_LINES_PER_FAILURE = 50
DEFAULT_MAX_CHARS_PER_FAILURE = 8_000
ACTION_APPEND = "append"
ACTION_STORE_FALSE = "store_false"
ACTION_STORE_TRUE = "store_true"


def parse_csv_like(values: list[str] | None) -> tuple[str, ...] | None:
    """Normalize repeated comma-separated verifier path options."""

    if not values:
        return None
    items: list[str] = []
    for value in values:
        items.extend(part.strip() for part in value.split(","))
    normalized = tuple(item.rstrip("/") or "." for item in items if item)
    return normalized or None


def parse_repeated_values(values: list[str] | None) -> tuple[str, ...] | None:
    """Preserve repeated option values exactly except empty entries."""

    if not values:
        return None
    normalized = tuple(value for value in values if value)
    return normalized or None


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse quiet verifier command-line options."""
    parser = argparse.ArgumentParser(
        description="Run repository quality checks with low-noise output."
    )
    parser.add_argument(
        "--profile",
        choices=sorted(VALID_PROFILES),
        default="full",
    )
    parser.add_argument("--base-ref", default=os.getenv("BASE_REF", "HEAD"))
    parser.add_argument("--compare-branch", default=os.getenv("COMPARE_BRANCH", "origin/main"))
    parser.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES_PER_FAILURE)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS_PER_FAILURE)
    parser.add_argument(
        "--staged",
        action=ACTION_STORE_TRUE,
        help="Use staged changes for diff-based checks.",
    )
    parser.add_argument(
        "--force",
        action=ACTION_STORE_TRUE,
        help="Rerun checks even when a same-state verifier result exists.",
    )
    parser.add_argument(
        "--mode",
        choices=sorted(VALID_MODES),
        help="Apply maintainer preset before other CLI overrides.",
    )
    add_path_overrides(parser)
    parser.add_argument("--coverage-fail-under", type=int)
    parser.add_argument("--diff-cover-fail-under", type=int)
    add_quality_gate_overrides(parser)
    add_secret_scan_overrides(parser)
    add_docs_config_overrides(parser)
    parser.add_argument(
        "--allow-source-without-test-change",
        action=ACTION_STORE_TRUE,
        default=None,
        help="Do not warn when source changes are covered by existing tests.",
    )
    parser.add_argument(
        "--architecture-tool",
        choices=sorted(VALID_ARCHITECTURE_TOOLS),
        help="Architecture contract checker to use for this run.",
    )
    parser.add_argument(
        "--fail-on-optional-skip",
        action=ACTION_STORE_TRUE,
        help=(
            "Treat skipped optional integrations, such as absent architecture config, as failures."
        ),
    )
    return parser.parse_args(argv)


def add_quality_gate_overrides(parser: argparse.ArgumentParser) -> None:
    """Add optional quality gate CLI overrides."""
    parser.add_argument("--require-tests", action=ACTION_STORE_TRUE, default=None)
    parser.add_argument("--no-require-tests", action=ACTION_STORE_FALSE, dest="require_tests")
    parser.add_argument("--enable-pip-audit", action=ACTION_STORE_TRUE, default=None)
    parser.add_argument("--disable-pip-audit", action=ACTION_STORE_FALSE, dest="enable_pip_audit")
    parser.add_argument("--enable-mutmut", action=ACTION_STORE_TRUE, default=None)
    parser.add_argument("--disable-mutmut", action=ACTION_STORE_FALSE, dest="enable_mutmut")
    parser.add_argument("--mutmut-arg", action=ACTION_APPEND)
    parser.add_argument("--enable-semgrep", action=ACTION_STORE_TRUE, default=None)
    parser.add_argument("--disable-semgrep", action=ACTION_STORE_FALSE, dest="enable_semgrep")
    parser.add_argument("--semgrep-arg", action=ACTION_APPEND)
    parser.add_argument("--semgrep-profile", action=ACTION_APPEND)
    parser.add_argument("--enable-wemake", action=ACTION_STORE_TRUE, default=None)
    parser.add_argument("--disable-wemake", action=ACTION_STORE_FALSE, dest="enable_wemake")
    parser.add_argument("--enable-interrogate", action=ACTION_STORE_TRUE, default=None)
    parser.add_argument(
        "--disable-interrogate", action=ACTION_STORE_FALSE, dest="enable_interrogate"
    )
    parser.add_argument("--interrogate-fail-under", type=int)


def add_docs_config_overrides(parser: argparse.ArgumentParser) -> None:
    """Add docs and config hygiene CLI overrides."""
    parser.add_argument("--enable-markdownlint", action=ACTION_STORE_TRUE, default=None)
    parser.add_argument(
        "--disable-markdownlint", action=ACTION_STORE_FALSE, dest="enable_markdownlint"
    )
    parser.add_argument("--markdownlint-path", action=ACTION_APPEND)
    parser.add_argument("--enable-yamllint", action=ACTION_STORE_TRUE, default=None)
    parser.add_argument("--disable-yamllint", action=ACTION_STORE_FALSE, dest="enable_yamllint")
    parser.add_argument("--yamllint-path", action=ACTION_APPEND)
    parser.add_argument("--enable-taplo", action=ACTION_STORE_TRUE, default=None)
    parser.add_argument("--disable-taplo", action=ACTION_STORE_FALSE, dest="enable_taplo")
    parser.add_argument("--taplo-path", action=ACTION_APPEND)
    parser.add_argument("--enable-check-jsonschema", action=ACTION_STORE_TRUE, default=None)
    parser.add_argument(
        "--disable-check-jsonschema",
        action=ACTION_STORE_FALSE,
        dest="enable_check_jsonschema",
    )
    parser.add_argument("--check-jsonschema-arg", action=ACTION_APPEND)


def add_secret_scan_overrides(parser: argparse.ArgumentParser) -> None:
    """Add backend-neutral secret scanning CLI overrides."""
    parser.add_argument("--enable-secret-scanning", action=ACTION_STORE_TRUE, default=None)
    parser.add_argument(
        "--disable-secret-scanning",
        action=ACTION_STORE_FALSE,
        dest="enable_secret_scanning",
    )
    parser.add_argument("--secret-scanner")
    parser.add_argument(
        "--secret-scan-profile",
        action=ACTION_APPEND,
        help="Secret scan normal profile. May be repeated or comma-separated.",
    )
    parser.add_argument(
        "--secret-scan-history-profile",
        action=ACTION_APPEND,
        help="Secret scan history profile. May be repeated or comma-separated.",
    )


def add_path_overrides(parser: argparse.ArgumentParser) -> None:
    """Register path override flags shared by verifier profiles."""

    parser.add_argument(
        "--source-root",
        action=ACTION_APPEND,
        help="Configured Python source root. May be repeated or comma-separated.",
    )
    parser.add_argument(
        "--test-root",
        action=ACTION_APPEND,
        help="Configured Python test root. May be repeated or comma-separated.",
    )
    parser.add_argument(
        "--coverage-source",
        action=ACTION_APPEND,
        help="Coverage source passed to pytest-cov. May be repeated or comma-separated.",
    )
    parser.add_argument(
        "--package-path",
        action=ACTION_APPEND,
        help="Package/source paths for static analysis. May be repeated or comma-separated.",
    )
    parser.add_argument(
        "--file-length-path",
        action=ACTION_APPEND,
        help="Paths scanned by the file-length check. May be repeated or comma-separated.",
    )
    parser.add_argument(
        "--file-length-baseline",
        help="JSON baseline used by the file-length ratchet.",
    )
    parser.add_argument(
        "--vulture-path",
        action=ACTION_APPEND,
        help="Paths scanned by vulture. May be repeated or comma-separated.",
    )


def apply_cli_overrides(config: MaintainerConfig, args: argparse.Namespace) -> MaintainerConfig:
    """Apply verifier CLI overrides after config and environment loading."""

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
        "mutmut_args": parse_repeated_values(args.mutmut_arg),
        "semgrep_args": parse_repeated_values(args.semgrep_arg),
        "semgrep_profiles": parse_csv_like(args.semgrep_profile),
        "secret_scan_profiles": parse_csv_like(args.secret_scan_profile),
        "secret_scan_history_profiles": parse_csv_like(args.secret_scan_history_profile),
        "markdownlint_paths": parse_csv_like(args.markdownlint_path),
        "yamllint_paths": parse_csv_like(args.yamllint_path),
        "taplo_paths": parse_csv_like(args.taplo_path),
        "check_jsonschema_args": parse_repeated_values(args.check_jsonschema_arg),
    }
    scalar_overrides = {
        "coverage_fail_under": args.coverage_fail_under,
        "diff_cover_fail_under": args.diff_cover_fail_under,
        "require_tests": args.require_tests,
        "enable_pip_audit": args.enable_pip_audit,
        "enable_mutmut": args.enable_mutmut,
        "enable_semgrep": args.enable_semgrep,
        "enable_secret_scanning": args.enable_secret_scanning,
        "secret_scanner": args.secret_scanner,
        "enable_wemake": args.enable_wemake,
        "enable_interrogate": args.enable_interrogate,
        "interrogate_fail_under": args.interrogate_fail_under,
        "enable_markdownlint": args.enable_markdownlint,
        "enable_yamllint": args.enable_yamllint,
        "enable_taplo": args.enable_taplo,
        "enable_check_jsonschema": args.enable_check_jsonschema,
        "architecture_tool": args.architecture_tool,
        "allow_source_without_test_change": args.allow_source_without_test_change,
        "file_length_baseline": args.file_length_baseline,
    }

    updates.update({field: value for field, value in tuple_overrides.items() if value is not None})
    updates.update({field: value for field, value in scalar_overrides.items() if value is not None})

    return replace(config, **updates)
