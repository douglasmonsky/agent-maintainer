#!/usr/bin/env python3
"""Run repository quality checks with low-noise output.

Passing checks are silent except for explicitly skipped optional integrations.
Failed checks print a capped, actionable summary and write full raw logs to
.verify-logs/.

Profiles:
- fast:       cheap checks suitable after file edits
- precommit: medium checks suitable before local commits
- full:       local full verification
- ci:         full verification plus changed-code coverage
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, replace
from pathlib import Path

from guardrail_config import GuardrailConfig, any_path_exists, existing_paths, format_paths, load_config

LOG_DIR = Path(".verify-logs")
DEFAULT_MAX_LINES_PER_FAILURE = 50
DEFAULT_MAX_CHARS_PER_FAILURE = 8_000

Profile = str

COMMON_PROFILES = frozenset({"precommit", "full", "ci"})
ALL_PROFILES = frozenset({"fast", "precommit", "full", "ci"})
FULL_AND_CI = frozenset({"full", "ci"})
CI_ONLY = frozenset({"ci"})


@dataclass(frozen=True)
class Check:
    name: str
    command: list[str]
    profiles: frozenset[Profile]
    required_paths: tuple[str, ...] = ()
    required_executable: str | None = None
    optional_skip_reason: str | None = None


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    output: str = ""
    skipped: bool = False


def parse_csv_like(values: list[str] | None) -> tuple[str, ...] | None:
    if not values:
        return None
    items: list[str] = []
    for value in values:
        items.extend(part.strip() for part in value.split(","))
    normalized = tuple(item.rstrip("/") or "." for item in items if item)
    return normalized or None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
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
    parser.add_argument("--coverage-fail-under", type=int)
    parser.add_argument("--diff-cover-fail-under", type=int)
    parser.add_argument("--require-tests", action="store_true", default=None)
    parser.add_argument("--no-require-tests", action="store_false", dest="require_tests")
    parser.add_argument("--enable-pip-audit", action="store_true", default=None)
    parser.add_argument("--disable-pip-audit", action="store_false", dest="enable_pip_audit")
    parser.add_argument(
        "--fail-on-optional-skip",
        action="store_true",
        help="Treat skipped optional integrations, such as absent .importlinter, as failures.",
    )
    return parser.parse_args(argv)


def apply_cli_overrides(config: GuardrailConfig, args: argparse.Namespace) -> GuardrailConfig:
    updates: dict[str, object] = {}
    source_roots = parse_csv_like(args.source_root)
    test_roots = parse_csv_like(args.test_root)
    coverage_source = parse_csv_like(args.coverage_source)
    package_paths = parse_csv_like(args.package_path)
    file_length_paths = parse_csv_like(args.file_length_path)
    vulture_paths = parse_csv_like(args.vulture_path)

    if source_roots is not None:
        updates["source_roots"] = source_roots
    if test_roots is not None:
        updates["test_roots"] = test_roots
    if coverage_source is not None:
        updates["coverage_source"] = coverage_source
    if package_paths is not None:
        updates["package_paths"] = package_paths
    if file_length_paths is not None:
        updates["file_length_paths"] = file_length_paths
    if vulture_paths is not None:
        updates["vulture_paths"] = vulture_paths
    if args.coverage_fail_under is not None:
        updates["coverage_fail_under"] = args.coverage_fail_under
    if args.diff_cover_fail_under is not None:
        updates["diff_cover_fail_under"] = args.diff_cover_fail_under
    if args.require_tests is not None:
        updates["require_tests"] = args.require_tests
    if args.enable_pip_audit is not None:
        updates["enable_pip_audit"] = args.enable_pip_audit

    return replace(config, **updates)


def existing_or_configured(paths: tuple[str, ...]) -> list[str]:
    existing = existing_paths(paths)
    return existing if existing else list(paths)


def pytest_command(config: GuardrailConfig) -> list[str]:
    command = ["pytest", "-q", "--tb=short", "--disable-warnings"]
    for source in config.coverage_source:
        command.append(f"--cov={source}")
    command.extend(
        [
            "--cov-report=term-missing:skip-covered",
            "--cov-report=xml",
            f"--cov-fail-under={config.coverage_fail_under}",
        ]
    )
    command.extend(config.test_roots)
    return command


def pip_audit_check(config: GuardrailConfig) -> Check:
    if not config.enable_pip_audit:
        return Check(
            "pip-audit",
            ["pip-audit"],
            FULL_AND_CI,
            optional_skip_reason=(
                "disabled by default; enable with GUARDRAILS_ENABLE_PIP_AUDIT=1 or "
                "[tool.ai_guardrails].enable_pip_audit = true"
            ),
        )

    command = ["pip-audit", *config.pip_audit_args]
    return Check("pip-audit", command, FULL_AND_CI, required_executable="pip-audit")


def make_checks(config: GuardrailConfig, base_ref: str, compare_branch: str) -> list[Check]:
    package_paths = tuple(existing_or_configured(config.package_paths))
    file_length_paths = tuple(existing_or_configured(config.file_length_paths))
    vulture_paths = tuple(path for path in config.vulture_paths if Path(path).exists()) or package_paths

    change_budget_command = [sys.executable, "scripts/check_change_budget.py", base_ref]
    for root in config.source_roots:
        change_budget_command.extend(["--source-root", root])
    for root in config.test_roots:
        change_budget_command.extend(["--test-root", root])

    file_length_command = [sys.executable, "scripts/check_file_lengths.py", *file_length_paths]

    if config.require_tests:
        pytest_coverage_check = Check(
            "pytest-coverage",
            pytest_command(config),
            COMMON_PROFILES,
            required_executable="pytest",
        )
        diff_cover_check = Check(
            "diff-cover",
            [
                "diff-cover",
                "coverage.xml",
                f"--compare-branch={compare_branch}",
                f"--fail-under={config.diff_cover_fail_under}",
            ],
            CI_ONLY,
            required_paths=("coverage.xml", ".git"),
            required_executable="diff-cover",
        )
    else:
        pytest_coverage_check = Check(
            "pytest-coverage",
            ["pytest"],
            COMMON_PROFILES,
            optional_skip_reason="tests are disabled by require_tests = false",
        )
        diff_cover_check = Check(
            "diff-cover",
            ["diff-cover"],
            CI_ONLY,
            optional_skip_reason="changed-code coverage is disabled because require_tests = false",
        )

    return [
        Check(
            "file-length",
            file_length_command,
            ALL_PROFILES,
            required_paths=("scripts/check_file_lengths.py",),
        ),
        Check(
            "change-budget",
            change_budget_command,
            ALL_PROFILES,
            required_paths=("scripts/check_change_budget.py", ".git"),
        ),
        Check(
            "suppression-budget",
            [sys.executable, "scripts/check_suppression_budget.py", base_ref],
            ALL_PROFILES,
            required_paths=("scripts/check_suppression_budget.py", ".git"),
        ),
        Check("ruff-format", ["ruff", "format", "--check", "."], COMMON_PROFILES, required_executable="ruff"),
        Check("ruff", ["ruff", "check", "--output-format=concise", "."], ALL_PROFILES, required_executable="ruff"),
        Check("pyright", ["pyright", "--outputjson"], COMMON_PROFILES, required_executable="pyright"),
        pytest_coverage_check,
        Check("radon-cc-report", ["radon", "cc", *package_paths, "-a", "-s"], FULL_AND_CI, required_executable="radon"),
        Check("radon-mi-report", ["radon", "mi", *package_paths, "-s"], FULL_AND_CI, required_executable="radon"),
        Check(
            "xenon-complexity-gate",
            ["xenon", "--max-absolute", "B", "--max-modules", "A", "--max-average", "A", *package_paths],
            COMMON_PROFILES,
            required_executable="xenon",
        ),
        Check("pylint", ["pylint", *package_paths, "--score=n"], FULL_AND_CI, required_executable="pylint"),
        Check(
            "import-linter",
            ["lint-imports"],
            FULL_AND_CI,
            required_executable="lint-imports",
            optional_skip_reason=".importlinter is absent; architecture contracts are not configured",
        ),
        Check("deptry", ["deptry", "."], FULL_AND_CI, required_executable="deptry"),
        Check("vulture", ["vulture", *vulture_paths], FULL_AND_CI, required_executable="vulture"),
        Check("bandit", ["bandit", "-q", "-r", *package_paths], FULL_AND_CI, required_executable="bandit"),
        pip_audit_check(config),
        diff_cover_check,
    ]


def layout_failures(config: GuardrailConfig, profile: Profile) -> list[str]:
    failures: list[str] = []

    if profile in COMMON_PROFILES and not any_path_exists(config.source_roots):
        failures.append(
            "No configured source root exists. Configured source_roots: "
            f"{format_paths(config.source_roots)}. Set [tool.ai_guardrails].source_roots, "
            "GUARDRAILS_SOURCE_ROOTS, or --source-root."
        )

    if profile in COMMON_PROFILES and config.require_tests and not any_path_exists(config.test_roots):
        failures.append(
            "No configured test root exists, and tests are required. Configured test_roots: "
            f"{format_paths(config.test_roots)}. Create tests or set require_tests = false intentionally."
        )

    if profile in COMMON_PROFILES and config.require_tests and not any_path_exists(config.coverage_source):
        failures.append(
            "No configured coverage source exists. Configured coverage_source: "
            f"{format_paths(config.coverage_source)}."
        )

    if profile in COMMON_PROFILES and not any_path_exists(config.package_paths):
        failures.append(
            "No configured package/static-analysis path exists. Configured package_paths: "
            f"{format_paths(config.package_paths)}."
        )

    return failures


def missing_requirement(check: Check) -> str | None:
    if check.optional_skip_reason:
        if check.name == "import-linter" and not Path(".importlinter").exists():
            return f"optional skip: {check.optional_skip_reason}"
        if check.name == "pip-audit":
            # pip-audit supplies optional_skip_reason only when disabled.
            return f"optional skip: {check.optional_skip_reason}"
        if check.name in {"pytest-coverage", "diff-cover"}:
            return f"optional skip: {check.optional_skip_reason}"

    for required_path in check.required_paths:
        if not Path(required_path).exists():
            return f"required path {required_path!r} is absent"
    if check.required_executable and shutil.which(check.required_executable) is None:
        return f"command not found: {check.required_executable!r}. Install dev dependencies."
    return None


def compact_output(text: str, max_lines: int, max_chars: int) -> str:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "(no output)"

    if len(lines) > max_lines:
        hidden = len(lines) - max_lines
        lines = lines[:max_lines] + [f"... {hidden} more lines omitted. See .verify-logs/ for full output."]

    compact = "\n".join(lines)
    if len(compact) > max_chars:
        compact = compact[:max_chars].rstrip() + "\n... output truncated. See .verify-logs/ for full output."
    return compact


def summarize_pyright(raw: str) -> str | None:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None

    diagnostics = payload.get("generalDiagnostics", [])
    if not diagnostics:
        summary = payload.get("summary", {})
        return json.dumps(summary, indent=2) if summary else None

    lines: list[str] = []
    for diagnostic in diagnostics[:50]:
        file_name = diagnostic.get("file", "<unknown>")
        range_info = diagnostic.get("range", {}).get("start", {})
        line = int(range_info.get("line", 0)) + 1
        character = int(range_info.get("character", 0)) + 1
        severity = diagnostic.get("severity", "error")
        message = diagnostic.get("message", "")
        rule = diagnostic.get("rule")
        suffix = f" [{rule}]" if rule else ""
        lines.append(f"{file_name}:{line}:{character}: {severity}: {message}{suffix}")

    omitted = len(diagnostics) - len(lines)
    if omitted > 0:
        lines.append(f"... {omitted} more diagnostics omitted. See .verify-logs/pyright.log")
    return "\n".join(lines)


def summarize(check: Check, raw_output: str, max_lines: int, max_chars: int) -> str:
    if check.name == "pyright":
        pyright_summary = summarize_pyright(raw_output)
        if pyright_summary:
            return compact_output(pyright_summary, max_lines, max_chars)
    return compact_output(raw_output, max_lines, max_chars)


def run_check(check: Check, max_lines: int, max_chars: int) -> CheckResult:
    missing = missing_requirement(check)
    if missing:
        LOG_DIR.mkdir(exist_ok=True)
        (LOG_DIR / f"{check.name}.log").write_text(missing + "\n", encoding="utf-8")
        if missing.startswith("optional skip:"):
            return CheckResult(check.name, passed=True, output=missing.removeprefix("optional skip: "), skipped=True)
        return CheckResult(check.name, passed=False, output=missing)

    try:
        result = subprocess.run(check.command, text=True, capture_output=True)
    except OSError as exc:
        return CheckResult(check.name, passed=False, output=f"could not run {check.command!r}: {exc}")

    full_output = ""
    if result.stdout:
        full_output += result.stdout
    if result.stderr:
        if full_output:
            full_output += "\n"
        full_output += result.stderr

    LOG_DIR.mkdir(exist_ok=True)
    (LOG_DIR / f"{check.name}.log").write_text(full_output, encoding="utf-8")

    if result.returncode == 0:
        return CheckResult(check.name, passed=True)

    return CheckResult(check.name, passed=False, output=summarize(check, full_output, max_lines, max_chars))


def emit_layout_failure(failures: list[str]) -> CheckResult:
    LOG_DIR.mkdir(exist_ok=True)
    output = "Guardrail layout/configuration failed:\n\n" + "\n".join(f"  {failure}" for failure in failures)
    (LOG_DIR / "guardrail-layout.log").write_text(output + "\n", encoding="utf-8")
    return CheckResult("guardrail-layout", passed=False, output=output)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    config = apply_cli_overrides(load_config(), args)
    checks = make_checks(config, args.base_ref, args.compare_branch)
    selected = [check for check in checks if args.profile in check.profiles]

    results: list[CheckResult] = []
    layout = layout_failures(config, args.profile)
    if layout:
        results.append(emit_layout_failure(layout))
    else:
        for check in selected:
            results.append(run_check(check, args.max_lines, args.max_chars))

    if args.fail_on_optional_skip:
        results = [
            CheckResult(result.name, passed=False, output=f"optional check skipped: {result.output}", skipped=False)
            if result.skipped
            else result
            for result in results
        ]

    failures = [result for result in results if not result.passed]
    skipped = [result for result in results if result.skipped]

    if not failures:
        print("PASS")
        if skipped:
            print("SKIPPED optional checks:")
            for result in skipped:
                print(f"  {result.name}: {result.output}")
        return 0

    print(f"FAIL: {len(failures)} check(s) failed [{args.profile}]\n")
    for index, result in enumerate(failures, start=1):
        print(f"{index}. {result.name}")
        print(result.output or "(no output)")
        print()
    if skipped:
        print("Skipped optional checks:")
        for result in skipped:
            print(f"  {result.name}: {result.output}")
        print()
    print("Full logs are in .verify-logs/.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
