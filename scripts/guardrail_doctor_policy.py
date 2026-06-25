"""Doctor checks for guardrail policy and unsafe configuration states."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import guardrail_config
from scripts.guardrail_doctor_models import ERROR, OK, WARNING, DoctorResult


def check_pyright_config(repo_root: Path, config: guardrail_config.GuardrailConfig) -> DoctorResult:
    """Compare a root Pyright config with the generated verifier mode."""

    config_path = repo_root / "pyrightconfig.json"
    if not config_path.exists():
        return DoctorResult(
            "pyright-config",
            OK,
            "Verifier generates a Pyright project config.",
        )
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return DoctorResult("pyright-config", WARNING, f"pyrightconfig.json is invalid: {exc}")
    root_mode = payload.get("typeCheckingMode")
    if root_mode is None or root_mode == config.pyright_type_checking_mode:
        return DoctorResult(
            "pyright-config",
            OK,
            f"Pyright mode is {config.pyright_type_checking_mode}.",
        )
    return DoctorResult(
        "pyright-config",
        WARNING,
        (
            "pyrightconfig.json typeCheckingMode "
            f"{root_mode!r} differs from guardrail mode {config.pyright_type_checking_mode!r}."
        ),
    )


def check_pip_audit_safety(config: guardrail_config.GuardrailConfig) -> DoctorResult:
    """Report unsafe pip-audit configuration before ambient audits happen."""

    if not config.enable_pip_audit:
        return DoctorResult("pip-audit-config", OK, "pip-audit is disabled.")
    if config.pip_audit_args:
        args = " ".join(config.pip_audit_args)
        return DoctorResult("pip-audit-config", OK, f"pip-audit input: {args}")
    status = ERROR if config.mode == guardrail_config.FRESH_STRICT_MODE else WARNING
    return DoctorResult(
        "pip-audit-config",
        status,
        "pip-audit is enabled without pinned pip_audit_args.",
    )
