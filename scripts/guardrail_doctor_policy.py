"""Doctor checks for guardrail policy and unsafe configuration states."""

from __future__ import annotations

import json
from pathlib import Path

from guardrail_lib.config import schema as guardrail_config_schema
from scripts import guardrail_config
from scripts.guardrail_doctor_models import ERROR, OK, WARNING, DoctorResult
from scripts.guardrail_models import SECURITY_PROFILE, VALID_PROFILES


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
    status = ERROR if config.mode == guardrail_config_schema.FRESH_STRICT_MODE else WARNING
    return DoctorResult(
        "pip-audit-config",
        status,
        "pip-audit is enabled without pinned pip_audit_args.",
    )


def check_secret_scanning_policy(config: guardrail_config.GuardrailConfig) -> DoctorResult:
    """Report secret scanning backend/profile policy state."""
    if not config.enable_secret_scanning:
        return DoctorResult("secret-scanning", OK, "secret scanning disabled.")
    if config.secret_scanner not in guardrail_config_schema.SUPPORTED_SECRET_SCANNERS:
        supported = ", ".join(sorted(guardrail_config_schema.SUPPORTED_SECRET_SCANNERS))
        message = (
            f"Unsupported secret scanner backend {config.secret_scanner!r}; supported: {supported}."
        )
        return DoctorResult(
            "secret-scanning",
            ERROR,
            message,
        )
    invalid_profiles = invalid_secret_scan_profiles(config)
    if invalid_profiles:
        invalid_profile_names = ", ".join(invalid_profiles)
        return DoctorResult(
            "secret-scanning",
            ERROR,
            f"Invalid secret scan profile(s): {invalid_profile_names}.",
        )
    if (
        config.secret_scan_history_profiles
        and SECURITY_PROFILE not in config.secret_scan_history_profiles
    ):
        return DoctorResult(
            "secret-scanning",
            WARNING,
            "Full-history secret scans should normally run in the manual security profile.",
        )
    profiles = ", ".join(config.secret_scan_profiles) or "none"
    history_profiles = ", ".join(config.secret_scan_history_profiles) or "none"
    return DoctorResult(
        "secret-scanning",
        OK,
        (
            f"{config.secret_scanner} active; profiles={profiles}; "
            f"history_profiles={history_profiles}."
        ),
    )


def invalid_secret_scan_profiles(config: guardrail_config.GuardrailConfig) -> list[str]:
    """Return configured secret scan profiles unknown to verifier."""
    configured = (*config.secret_scan_profiles, *config.secret_scan_history_profiles)
    return sorted({profile for profile in configured if profile not in VALID_PROFILES})
