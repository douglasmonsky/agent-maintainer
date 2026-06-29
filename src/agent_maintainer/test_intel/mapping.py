"""Map changed source files to likely focused tests."""

from __future__ import annotations

import ast
from pathlib import Path

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.test_intel.models import TestMatch

HIGH_CONFIDENCE = "high"
MEDIUM_CONFIDENCE = "medium"
LOW_CONFIDENCE = "low"
CONFIDENCE_ORDER = (HIGH_CONFIDENCE, MEDIUM_CONFIDENCE, LOW_CONFIDENCE)


def likely_tests_for_changes(
    changed_source: tuple[str, ...],
    config: MaintainerConfig,
    repo_root: Path,
) -> tuple[TestMatch, ...]:
    """Return ranked likely test files for changed source files."""

    test_files = discover_test_files(repo_root, config.test_roots)
    matches = [
        match
        for source_path in changed_source
        for match in likely_tests_for_source(source_path, test_files, config, repo_root)
    ]
    return tuple(sorted(matches, key=match_sort_key))


def likely_tests_for_source(
    source_path: str,
    test_files: tuple[str, ...],
    config: MaintainerConfig,
    repo_root: Path,
) -> tuple[TestMatch, ...]:
    """Return likely tests for one source file."""

    source_module = module_name_for_source(source_path, config.source_roots)
    source_domains = domain_parts(source_path, config.source_roots)
    matches: list[TestMatch] = []
    for test_path in test_files:
        reasons = match_reasons(source_path, source_module, source_domains, test_path, repo_root)
        if reasons:
            matches.append(
                TestMatch(
                    source_path=source_path,
                    test_path=test_path,
                    confidence=confidence_for_reasons(reasons),
                    reasons=tuple(reasons),
                )
            )
    return tuple(matches)


def discover_test_files(repo_root: Path, test_roots: tuple[str, ...]) -> tuple[str, ...]:
    """Return configured pytest-style test files."""

    files: list[str] = []
    for root in test_roots:
        root_path = repo_root / root
        if root_path.exists():
            files.extend(
                path.relative_to(repo_root).as_posix()
                for path in root_path.rglob("*.py")
                if is_pytest_file(path)
            )
    return tuple(sorted(files))


def is_pytest_file(path: Path) -> bool:
    """Return whether path follows common pytest naming."""

    return path.name.startswith("test_") or path.name.endswith("_test.py")


def match_reasons(
    source_path: str,
    source_module: str,
    source_domains: tuple[str, ...],
    test_path: str,
    repo_root: Path,
) -> list[str]:
    """Return deterministic reasons linking one test to one source."""

    reasons: list[str] = []
    if name_matches(source_path, test_path):
        reasons.append("naming match")
    if imports_source_module(repo_root / test_path, source_module):
        reasons.append("imports changed module")
    if same_domain(source_domains, test_path):
        reasons.append("same package/domain")
    return reasons


def name_matches(source_path: str, test_path: str) -> bool:
    """Return whether source and test filenames share a stem."""

    source_stem = Path(source_path).stem
    test_stem = Path(test_path).stem.removeprefix("test_").removesuffix("_test")
    return source_stem == test_stem or source_stem in test_stem


def imports_source_module(test_path: Path, source_module: str) -> bool:
    """Return whether test imports changed module."""

    imported = imported_modules(test_path)
    return any(source_module == name or source_module.startswith(f"{name}.") for name in imported)


def imported_modules(test_path: Path) -> frozenset[str]:
    """Return imported module names from a Python test file."""

    try:
        tree = ast.parse(test_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return frozenset()
    imports: set[str] = set()
    for node in ast.walk(tree):
        imports.update(import_names(node))
    return frozenset(imports)


def import_names(node: ast.AST) -> tuple[str, ...]:
    """Return imported module names for one AST node."""

    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module:
        return (node.module,)
    return ()


def module_name_for_source(source_path: str, source_roots: tuple[str, ...]) -> str:
    """Return importable module name for a source path."""

    relative = relative_to_first_root(source_path, source_roots)
    without_suffix = relative.removesuffix(".py")
    parts = [part for part in without_suffix.split("/") if part != "__init__"]
    return ".".join(parts)


def relative_to_first_root(path: str, roots: tuple[str, ...]) -> str:
    """Return path relative to first matching configured root."""

    clean_path = path.replace("\\", "/").lstrip("./")
    for root in roots:
        clean_root = root.replace("\\", "/").strip("/")
        prefix = f"{clean_root}/"
        if clean_path.startswith(prefix):
            return clean_path.removeprefix(prefix)
    return clean_path


def domain_parts(path: str, roots: tuple[str, ...]) -> tuple[str, ...]:
    """Return meaningful source directory domains."""

    relative = relative_to_first_root(path, roots)
    directories = relative.split("/")[:-1]
    if len(directories) <= 1:
        return tuple(directories)
    return tuple(directories[1:])


def same_domain(source_domains: tuple[str, ...], test_path: str) -> bool:
    """Return whether test path includes the source domain name."""

    return any(f"/{domain}/" in f"/{test_path}/" for domain in source_domains)


def confidence_for_reasons(reasons: list[str]) -> str:
    """Return confidence label from match reasons."""

    if "naming match" in reasons and "imports changed module" in reasons:
        return HIGH_CONFIDENCE
    if "naming match" in reasons or "imports changed module" in reasons:
        return MEDIUM_CONFIDENCE
    return LOW_CONFIDENCE


def match_sort_key(match: TestMatch) -> tuple[int, str, str]:
    """Return stable ranking key for likely tests."""

    return (confidence_rank(match.confidence), match.source_path, match.test_path)


def confidence_rank(confidence: str) -> int:
    """Return numeric rank for confidence label."""

    if confidence in CONFIDENCE_ORDER:
        return CONFIDENCE_ORDER.index(confidence)
    return len(CONFIDENCE_ORDER)
