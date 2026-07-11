"""Setup health diagnostics for Agent Maintainer."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_maintainer.core import config as maintainer_config
from agent_maintainer.doctor import setup as maintainer_doctor_setup
from agent_maintainer.doctor.support import environment as maintainer_doctor_environment
from agent_maintainer.doctor.support import hook_audit as maintainer_doctor_hook_audit
from agent_maintainer.doctor.support import integrations as maintainer_doctor_integrations
from agent_maintainer.doctor.support import logs as maintainer_doctor_logs
from agent_maintainer.doctor.support import models as maintainer_doctor_models
from agent_maintainer.doctor.support import output as maintainer_doctor_output
from agent_maintainer.doctor.support import policy as maintainer_doctor_policy

DoctorResult = maintainer_doctor_models.DoctorResult
ERROR = maintainer_doctor_models.ERROR
OK = maintainer_doctor_models.OK
WARNING = maintainer_doctor_models.WARNING

check_python_version = maintainer_doctor_setup.check_python_version
check_agent_guidance = maintainer_doctor_setup.check_agent_guidance
check_layout = maintainer_doctor_setup.check_layout
check_optional_gates = maintainer_doctor_setup.check_optional_gates
check_source_checkout_dogfood = maintainer_doctor_setup.check_source_checkout_dogfood
check_tests = maintainer_doctor_setup.check_tests
check_tool_capabilities = maintainer_doctor_setup.check_tool_capabilities
check_unknown_config_keys = maintainer_doctor_policy.check_unknown_config_keys

check_repo_root = maintainer_doctor_environment.check_repo_root
check_virtualenv = maintainer_doctor_environment.check_virtualenv
check_git_state = maintainer_doctor_environment.check_git_state

check_pre_commit = maintainer_doctor_integrations.check_pre_commit
check_codex_hooks = maintainer_doctor_integrations.check_codex_hooks
check_codex_rewake_capabilities = maintainer_doctor_integrations.check_codex_rewake_capabilities
check_claude_code_hooks = maintainer_doctor_integrations.check_claude_code_hooks
check_canonical_commands = maintainer_doctor_integrations.check_canonical_commands
normalized_text = maintainer_doctor_integrations.normalized_text

print_text = maintainer_doctor_output.print_text
status_code = maintainer_doctor_output.status_code


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse doctor command-line options."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit nonzero when any warning is present.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable diagnostic results.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format. Defaults to text.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root to inspect. Defaults to current directory.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    """Run setup diagnostics and emit text or JSON output."""

    args = parse_args(argv)
    repo_root = args.root.resolve()
    config = maintainer_config.load_config(repo_root)
    results = run_doctor(repo_root, config)
    if args.json or args.format == "json":
        print(maintainer_doctor_output.json_text(results))
    else:
        print_text(results)
    return status_code(results, strict=args.strict)


def run_doctor(
    repo_root: Path,
    config: maintainer_config.MaintainerConfig,
) -> list[DoctorResult]:
    """Run setup diagnostics against the repository root."""

    return [
        check_python_version(),
        check_repo_root(repo_root),
        check_unknown_config_keys(repo_root),
        check_virtualenv(repo_root),
        check_source_checkout_dogfood(repo_root),
        maintainer_doctor_setup.check_console_script_dogfood(repo_root),
        check_tool_capabilities(repo_root, config),
        maintainer_doctor_setup.check_architecture_backend(repo_root, config),
        check_layout(config),
        check_tests(repo_root, config),
        maintainer_doctor_setup.check_thresholds(config),
        maintainer_doctor_setup.check_structure_thresholds(config),
        maintainer_doctor_setup.check_ratchet_baseline(repo_root, config),
        maintainer_doctor_policy.check_pyright_config(repo_root, config),
        check_pre_commit(repo_root),
        check_codex_hooks(repo_root),
        *check_codex_rewake_capabilities(),
        check_claude_code_hooks(repo_root),
        maintainer_doctor_hook_audit.check_hook_audit(repo_root, config),
        maintainer_doctor_policy.check_pip_audit_safety(config),
        maintainer_doctor_policy.check_secret_scanning_policy(config),
        maintainer_doctor_policy.check_provider_status(config),
        *maintainer_doctor_policy.check_typescript_provider(config),
        maintainer_doctor_policy.check_context_pack_upload_policy(repo_root, config),
        *maintainer_doctor_policy.check_context_health(repo_root, config),
        check_optional_gates(repo_root, config),
        maintainer_doctor_setup.check_duplicate_generated_artifacts(repo_root),
        check_canonical_commands(repo_root),
        check_agent_guidance(repo_root, config),
        check_git_state(repo_root),
        maintainer_doctor_logs.check_recent_logs(repo_root, config),
    ]
