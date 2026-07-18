"""Declarative catalog composition for maintainer checks."""

from __future__ import annotations

import sys

from agent_maintainer import models
from agent_maintainer.catalogs.docs import docs_config_checks, docsync_checks
from agent_maintainer.catalogs.global_checks import (
    architecture_checks,
    contract_compatibility_check,
    existing_or_configured,
    reviewability_checks,
    verification_plan_check,
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
from agent_maintainer.ecosystems.registry import (
    experimental_check_providers,
    python_provider,
)

_CATALOG_PYTHON_EXECUTABLE = sys.executable


# docsync:evidence.start evidence.readme.catalog_composition
def make_checks(
    config: MaintainerConfig,
    base_ref: str,
    compare_branch: str,
    *,
    staged: bool = False,
) -> list[models.Check]:
    """Build complete catalog for verifier profiles."""
    package_paths = existing_or_configured(config.package_paths)
    ecosystem_context = EcosystemCheckContext(
        config=config,
        compare_branch=compare_branch,
        package_paths=package_paths,
    )
    python_provider_checks = python_provider().checks_by_name(ecosystem_context)
    experimental_provider_checks = [
        check
        for provider in experimental_check_providers()
        for check in provider.checks(ecosystem_context)
    ]
    return [
        *reviewability_checks(config, base_ref, staged=staged),
        verification_plan_check(base_ref, staged=staged),
        contract_compatibility_check(config, base_ref),
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
        *experimental_provider_checks,
        *workflow_checks(),
        python_provider_checks["wemake"],
        python_provider_checks["interrogate"],
        *docs_config_checks(config),
        *docsync_checks(base_ref),
        python_provider_checks["diff-cover"],
    ]


# docsync:evidence.end evidence.readme.catalog_composition
