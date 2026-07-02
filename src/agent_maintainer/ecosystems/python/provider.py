"""Internal Python ecosystem provider."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer import models
from agent_maintainer.catalogs import python as python_checks
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.ecosystems.models import EcosystemCheckContext
from agent_maintainer.models import Check


class PythonProvider:
    """Build Python-owned checks while preserving catalog order externally."""

    name = "python"

    def checks(self, context: EcosystemCheckContext) -> list[Check]:
        """Return current Python ecosystem checks."""
        config = context.config
        package_paths = context.package_paths
        return [
            Check(
                "ruff-format",
                ["ruff", "format", "--check", "."],
                models.LOCAL_GATE_PROFILES,
                required_executable="ruff",
            ),
            python_checks.ruff_check(config),
            python_checks.pyright_check(config),
            python_checks.pyright_strict_ratchet_check(config),
            python_checks.pytest_check(config),
            python_checks.mutmut_target_ratchet_check(config),
            Check(
                "radon-cc-report",
                ["radon", "cc", *package_paths, "-a", "-s"],
                models.FULL_PROFILES,
                required_executable="radon",
            ),
            Check(
                "radon-mi-report",
                ["radon", "mi", *package_paths, "-s"],
                models.FULL_PROFILES,
                required_executable="radon",
            ),
            Check(
                "xenon-complexity-gate",
                [
                    "xenon",
                    "--max-absolute",
                    config.xenon_max_absolute,
                    "--max-modules",
                    config.xenon_max_modules,
                    "--max-average",
                    config.xenon_max_average,
                    *package_paths,
                ],
                models.LOCAL_GATE_PROFILES,
                required_executable="xenon",
            ),
            Check(
                "pylint",
                ["pylint", *package_paths, "--score=n"],
                models.FULL_PROFILES,
                required_executable="pylint",
            ),
            Check(
                "deptry",
                ["deptry", "."],
                models.FULL_PROFILES,
                required_executable="deptry",
            ),
            Check(
                "vulture",
                ["vulture", *vulture_paths(config, package_paths)],
                models.FULL_PROFILES,
                required_executable="vulture",
            ),
            python_checks.bandit_check(config),
            python_checks.pip_audit_check(config),
            python_checks.mutmut_check(config),
            python_checks.wemake_check(config, package_paths),
            python_checks.interrogate_check(config, package_paths),
            python_checks.diff_cover_check(config, context.compare_branch),
        ]


def vulture_paths(
    config: MaintainerConfig,
    package_paths: tuple[str, ...],
) -> tuple[str, ...]:
    """Return existing vulture scan paths, falling back to package paths."""
    paths = tuple(path for path in config.vulture_paths if Path(path).exists())
    return paths or package_paths
