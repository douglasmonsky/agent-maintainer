"""Doctor checks for maintainer policy and unsafe configuration states."""

from __future__ import annotations

import json
from pathlib import Path

from agent_maintainer.config import schema as maintainer_config_schema
from agent_maintainer.core import config as maintainer_config
from agent_maintainer.doctor.support import context_artifacts, context_health
from agent_maintainer.doctor.support.models import (
    ACTIVE,
    DISABLED,
    ERROR,
    OK,
    UNSAFE_CONFIG,
    WARNING,
    DoctorResult,
)
from agent_maintainer.models import SECURITY_PROFILE, VALID_PROFILES

check_context_pack_upload_policy = context_artifacts.check_context_pack_upload_policy
check_context_health = context_health.check_context_health


def check_pyright_config(
    repo_root: Path, config: maintainer_config.MaintainerConfig
) -> DoctorResult:
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
        return DoctorResult(
            "pyright-config",
            WARNING,
            f"pyrightconfig.json is invalid: {exc}",
            state=UNSAFE_CONFIG,
            hint="Fix or remove pyrightconfig.json so maintainer-generated config is unambiguous.",
        )
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
            f"{root_mode!r} differs from maintainer mode {config.pyright_type_checking_mode!r}."
        ),
        state=UNSAFE_CONFIG,
        hint="Align pyrightconfig.json or rely on the generated verifier config.",
    )


def check_pip_audit_safety(config: maintainer_config.MaintainerConfig) -> DoctorResult:
    """Report unsafe pip-audit configuration before ambient audits happen."""

    if not config.enable_pip_audit:
        return DoctorResult("pip-audit-config", OK, "pip-audit is disabled.", state=DISABLED)
    if config.pip_audit_args:
        args = " ".join(config.pip_audit_args)
        return DoctorResult("pip-audit-config", OK, f"pip-audit input: {args}")
    status = ERROR if config.mode == maintainer_config_schema.FRESH_STRICT_MODE else WARNING
    return DoctorResult(
        "pip-audit-config",
        status,
        "pip-audit is enabled without pinned pip_audit_args.",
        state=UNSAFE_CONFIG,
        hint="Set pip_audit_args to a requirements or lock file.",
    )


def check_secret_scanning_policy(config: maintainer_config.MaintainerConfig) -> DoctorResult:
    """Report secret scanning backend/profile policy state."""
    if not config.enable_secret_scanning:
        return DoctorResult("secret-scanning", OK, "secret scanning disabled.", state=DISABLED)
    if config.secret_scanner not in maintainer_config_schema.SUPPORTED_SECRET_SCANNERS:
        supported = ", ".join(sorted(maintainer_config_schema.SUPPORTED_SECRET_SCANNERS))
        message = (
            f"Unsupported secret scanner backend {config.secret_scanner!r}; supported: {supported}."
        )
        return DoctorResult(
            "secret-scanning",
            ERROR,
            message,
            state=UNSAFE_CONFIG,
            hint="Choose a supported backend or add backend support before enabling it.",
        )
    invalid_profiles = invalid_secret_scan_profiles(config)
    if invalid_profiles:
        invalid_profile_names = ", ".join(invalid_profiles)
        return DoctorResult(
            "secret-scanning",
            ERROR,
            f"Invalid secret scan profile(s): {invalid_profile_names}.",
            state=UNSAFE_CONFIG,
            hint="Use valid verifier profiles for secret_scan_profiles.",
        )
    if (
        config.secret_scan_history_profiles
        and SECURITY_PROFILE not in config.secret_scan_history_profiles
    ):
        return DoctorResult(
            "secret-scanning",
            WARNING,
            "Full-history secret scans should normally run in the manual security profile.",
            state=UNSAFE_CONFIG,
            hint="Move history scans to secret_scan_history_profiles = ['security'].",
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
        state=ACTIVE,
    )


def invalid_secret_scan_profiles(config: maintainer_config.MaintainerConfig) -> list[str]:
    """Return configured secret scan profiles unknown to verifier."""
    configured = (*config.secret_scan_profiles, *config.secret_scan_history_profiles)
    return sorted({profile for profile in configured if profile not in VALID_PROFILES})
