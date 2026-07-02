"""Declarative catalog composition for maintainer checks."""

from __future__ import annotations

import sys

from agent_maintainer import models
from agent_maintainer.catalogs.docs import docs_config_checks
from agent_maintainer.catalogs.global_checks import (
    architecture_checks,
    existing_or_configured,
    reviewability_checks,
    workflow_checks,
)
from agent_maintainer.catalogs.security import (
    license_check_checks,
    osv_scanner_checks,
    sbom_checks,
    secret_scan_checks,
    semgrep_checks,
    trivy_checks,
)
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.ecosystems.models import EcosystemCheckContext
from agent_maintainer.ecosystems.python.provider import PythonProvider

_CATALOG_PYTHON_EXECUTABLE = sys.executable


def make_checks(
    config: MaintainerConfig,
    base_ref: str,
    compare_branch: str,
    *,
    staged: bool = False,
) -> list[models.Check]:
    """Build complete catalog for verifier profiles."""
    package_paths = existing_or_configured(config.package_paths)
    python_provider_checks = PythonProvider().checks_by_name(
        EcosystemCheckContext(
            config=config,
            compare_branch=compare_branch,
            package_paths=package_paths,
        )
    )
    return [
        *reviewability_checks(config, base_ref, staged=staged),
        python_provider_checks["ruff-format"],
        python_provider_checks["ruff"],
        python_provider_checks["pyright"],
        python_provider_checks["pyright-strict-ratchet"],
        python_provider_checks["pytest-coverage"],
        python_provider_checks["mutmut-target-ratchet"],
        python_provider_checks["radon-cc-report"],
        python_provider_checks["radon-mi-report"],
        python_provider_checks["xenon-complexity-gate"],
        python_provider_checks["pylint"],
        *architecture_checks(config, base_ref, staged=staged),
        python_provider_checks["deptry"],
        python_provider_checks["vulture"],
        python_provider_checks["bandit"],
        python_provider_checks["pip-audit"],
        python_provider_checks["mutmut"],
        *semgrep_checks(config),
        *osv_scanner_checks(config),
        *trivy_checks(config),
        *sbom_checks(config),
        *license_check_checks(config),
        *secret_scan_checks(config, base_ref, staged=staged),
        *workflow_checks(),
        python_provider_checks["wemake"],
        python_provider_checks["interrogate"],
        *docs_config_checks(config),
        python_provider_checks["diff-cover"],
    ]
