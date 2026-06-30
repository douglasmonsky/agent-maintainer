"""Repository evidence collection for advisory assessments."""

from __future__ import annotations

import os
import tomllib
from collections.abc import Iterable
from pathlib import Path

from agent_maintainer.assess.models import RepoEvidence

IGNORED_PARTS = frozenset(
    (
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        ".verify-logs",
        "__pycache__",
        "build",
        "dist",
        "htmlcov",
        "mutants",
        "node_modules",
        "venv",
    ),
)


def collect_evidence(target: Path) -> RepoEvidence:
    """Collect cheap local repository evidence."""
    root = target.resolve()
    paths = tuple(_walk_files(root))
    python_files = tuple(path for path in paths if path.suffix == ".py")
    test_files = tuple(path for path in python_files if _is_test_path(root, path))
    source_files = tuple(path for path in python_files if not _is_test_path(root, path))
    return RepoEvidence(
        target=str(root),
        has_agent_config=_has_agent_config(root),
        has_pyproject=(root / "pyproject.toml").exists(),
        has_git=(root / ".git").exists(),
        has_tests=any((root / name).exists() for name in ("tests", "test")),
        has_src=(root / "src").exists(),
        has_ci=(root / ".github" / "workflows").exists(),
        has_pre_commit=(root / ".pre-commit-config.yaml").exists(),
        has_agent_guidance=any(
            (root / name).exists() for name in ("AGENTS.md", "AGENTS.agent-maintainer.md")
        ),
        has_codex_hooks=(root / ".codex" / "hooks").exists(),
        has_claude_hooks=(root / ".claude" / "hooks").exists(),
        has_tach=(root / "tach.toml").exists(),
        has_import_linter=(root / ".importlinter").exists(),
        has_lock_file=_any_exists(root, ("config/dev-lock.txt", "uv.lock", "poetry.lock")),
        has_dependency_file=_any_exists(
            root,
            (
                "config/dev-dependencies.txt",
                "requirements.txt",
                "pyproject.toml",
                "Pipfile",
            ),
        ),
        has_package_json=(root / "package.json").exists(),
        has_go_mod=(root / "go.mod").exists(),
        has_container_or_iac=_has_container_or_iac(root, paths),
        python_files=len(python_files),
        source_files=len(source_files),
        test_files=len(test_files),
        yaml_files=_count_suffixes(paths, (".yml", ".yaml")),
        toml_files=_count_suffixes(paths, (".toml",)),
        json_files=_count_suffixes(paths, (".json",)),
    )


def _walk_files(root: Path) -> Iterable[Path]:
    """Yield non-generated files under root."""
    for current, dirs, files in os.walk(root):
        allowed_dirs = [name for name in dirs if name not in IGNORED_PARTS]
        dirs.clear()
        dirs.extend(allowed_dirs)
        current_path = Path(current)
        if IGNORED_PARTS.intersection(current_path.relative_to(root).parts):
            continue
        for filename in files:
            path = current_path / filename
            if not IGNORED_PARTS.intersection(path.relative_to(root).parts):
                yield path


def _has_agent_config(root: Path) -> bool:
    """Return whether pyproject declares Agent Maintainer config."""
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return False
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return False
    tool = data.get("tool", {})
    return isinstance(tool, dict) and isinstance(tool.get("agent_maintainer"), dict)


def _is_test_path(root: Path, path: Path) -> bool:
    """Return whether path belongs to a test tree or test module."""
    relative = path.relative_to(root)
    return "tests" in relative.parts or path.name.startswith("test_")


def _any_exists(root: Path, names: tuple[str, ...]) -> bool:
    """Return whether any named path exists under root."""
    return any((root / name).exists() for name in names)


def _has_container_or_iac(root: Path, paths: tuple[Path, ...]) -> bool:
    """Return whether container, Kubernetes, or Terraform assets exist."""
    if _any_exists(root, ("Dockerfile", "docker-compose.yml", "docker-compose.yaml")):
        return True
    return any(path.suffix == ".tf" or "k8s" in path.parts for path in paths)


def _count_suffixes(paths: tuple[Path, ...], suffixes: tuple[str, ...]) -> int:
    """Count files with matching suffixes."""
    return sum(1 for path in paths if path.suffix in suffixes)
