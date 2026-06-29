"""Advisory Hypothesis property-test candidate ranking."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.test_intel.hypothesis_scaffolds import scaffold_lines
from agent_maintainer.test_intel.mapping import likely_tests_for_changes

ADVISORY_NOTE = "Scaffold is a starting point, not a verified contract."
DEFAULT_LIMIT = 10
MIN_SCORE = 5
MIN_BRANCH_COMPLEXITY = 3
BRANCH_NODES = (
    ast.BoolOp,
    ast.ExceptHandler,
    ast.For,
    ast.If,
    ast.IfExp,
    ast.Match,
    ast.Try,
    ast.While,
)
BOUNDARY_NAMES = frozenset(
    (
        "bound",
        "clamp",
        "coerce",
        "convert",
        "limit",
        "normalize",
        "parse",
        "range",
        "score",
        "validate",
    )
)
SIDE_EFFECT_NAMES = frozenset(
    (
        "append",
        "extend",
        "insert",
        "mkdir",
        "open",
        "pop",
        "print",
        "remove",
        "rename",
        "replace",
        "rmdir",
        "touch",
        "unlink",
        "write",
    )
)
NUMERIC_TYPES = frozenset(("float", "int"))
STRING_TYPES = frozenset(("str",))


@dataclass(frozen=True)
class HypothesisCandidate:
    """One advisory property-test target."""

    path: str
    qualname: str
    score: int
    complexity: int
    reasons: tuple[str, ...]
    suggested_scaffold: tuple[str, ...]
    note: str = ADVISORY_NOTE

    def to_json(self) -> dict[str, object]:
        """Return stable JSON payload."""

        return {
            "path": self.path,
            "qualname": self.qualname,
            "score": self.score,
            "complexity": self.complexity,
            "reasons": list(self.reasons),
            "suggested_scaffold": list(self.suggested_scaffold),
            "note": self.note,
        }


@dataclass(frozen=True)
class HypothesisCandidateReport:
    """Advisory Hypothesis candidate report."""

    changed_only: bool
    changed_source: tuple[str, ...]
    candidates: tuple[HypothesisCandidate, ...]
    note: str = ADVISORY_NOTE

    def to_json(self) -> dict[str, object]:
        """Return stable JSON payload."""

        return {
            "changed_only": self.changed_only,
            "changed_source": list(self.changed_source),
            "candidates": [candidate.to_json() for candidate in self.candidates],
            "note": self.note,
        }


def build_hypothesis_candidate_report(
    config: MaintainerConfig,
    repo_root: Path,
    *,
    changed_only: bool,
    changed_source: tuple[str, ...] = (),
    limit: int = DEFAULT_LIMIT,
) -> HypothesisCandidateReport:
    """Return advisory Hypothesis candidate report."""

    source_paths = changed_source if changed_only else discover_source_files(config, repo_root)
    changed_set = frozenset(changed_source)
    test_counts = likely_test_counts(source_paths, config, repo_root)
    candidates = [
        candidate
        for source_path in source_paths
        for candidate in candidates_for_source(
            source_path,
            repo_root,
            changed=source_path in changed_set,
            likely_test_count=test_counts.get(source_path, 0),
        )
    ]
    ranked = tuple(sorted(candidates, key=candidate_sort_key)[:limit])
    return HypothesisCandidateReport(
        changed_only=changed_only,
        changed_source=changed_source,
        candidates=ranked,
    )


def discover_source_files(config: MaintainerConfig, repo_root: Path) -> tuple[str, ...]:
    """Return Python source files under configured source roots."""

    paths: set[str] = set()
    for source_root in config.source_roots:
        root_path = repo_root / source_root
        if not root_path.exists():
            continue
        for path in root_path.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            paths.add(path.relative_to(repo_root).as_posix())
    return tuple(sorted(paths))


def likely_test_counts(
    source_paths: tuple[str, ...], config: MaintainerConfig, repo_root: Path
) -> dict[str, int]:
    """Return likely focused test count per source file."""

    matches = likely_tests_for_changes(source_paths, config, repo_root)
    counts = dict.fromkeys(source_paths, 0)
    for match in matches:
        counts[match.source_path] = counts.get(match.source_path, 0) + 1
    return counts


def candidates_for_source(
    source_path: str,
    repo_root: Path,
    *,
    changed: bool,
    likely_test_count: int,
) -> tuple[HypothesisCandidate, ...]:
    """Return ranked candidates for one source path."""

    source_file = repo_root / source_path
    try:
        tree = ast.parse(source_file.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return ()

    candidates = [
        candidate
        for function in iter_public_functions(tree)
        if (
            candidate := candidate_for_function(
                source_path,
                function,
                changed=changed,
                likely_test_count=likely_test_count,
            )
        )
    ]
    return tuple(sorted(candidates, key=candidate_sort_key))


def iter_public_functions(tree: ast.AST) -> tuple[tuple[str, ast.FunctionDef], ...]:
    """Return public top-level functions and methods with qualified names."""

    results: list[tuple[str, ast.FunctionDef]] = []
    for node in ast.iter_child_nodes(tree):
        collect_public_functions(node, (), results)
    return tuple(results)


def collect_public_functions(
    node: ast.AST,
    parents: tuple[str, ...],
    results: list[tuple[str, ast.FunctionDef]],
) -> None:
    """Collect public functions without descending into function bodies."""

    if isinstance(node, ast.ClassDef):
        for child in node.body:
            collect_public_functions(child, (*parents, node.name), results)
        return
    if not isinstance(node, ast.FunctionDef) or node.name.startswith("_"):
        return
    results.append((".".join((*parents, node.name)), node))


def candidate_for_function(
    source_path: str,
    function: tuple[str, ast.FunctionDef],
    *,
    changed: bool,
    likely_test_count: int,
) -> HypothesisCandidate | None:
    """Return candidate when a function has enough property-test signals."""

    qualname, node = function
    complexity = branch_complexity(node)
    score, reasons = candidate_score(
        node,
        qualname,
        complexity=complexity,
        changed=changed,
        likely_test_count=likely_test_count,
    )
    if score < MIN_SCORE:
        return None
    return HypothesisCandidate(
        path=source_path,
        qualname=qualname,
        score=score,
        complexity=complexity,
        reasons=tuple(reasons),
        suggested_scaffold=scaffold_lines(qualname, node),
    )


def candidate_score(
    node: ast.FunctionDef,
    qualname: str,
    *,
    complexity: int,
    changed: bool,
    likely_test_count: int,
) -> tuple[int, list[str]]:
    """Return candidate score and explanation reasons."""

    score = 0
    reasons: list[str] = []
    if changed:
        score += 4
        reasons.append("recently changed")
    if has_type_hints(node):
        score += 3
        reasons.append("typed function")
    if complexity >= MIN_BRANCH_COMPLEXITY:
        score += complexity
        reasons.append(f"branch complexity {complexity}")
    if is_pureish(node):
        score += 2
        reasons.append("pure-ish function")
    if has_boundary_name(qualname):
        score += 3
        reasons.append("parser/validator/normalizer name")
    if has_boundary_logic(node):
        score += 2
        reasons.append("numeric/string boundary behavior")
    if likely_test_count <= 1:
        score += 1
        reasons.append("narrow current tests")
    return score, reasons


def branch_complexity(node: ast.AST) -> int:
    """Return lightweight branch complexity estimate."""

    return 1 + sum(isinstance(child, BRANCH_NODES) for child in ast.walk(node))


def has_type_hints(node: ast.FunctionDef) -> bool:
    """Return whether function has argument or return annotations."""

    args = (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
    return node.returns is not None or any(arg.annotation is not None for arg in args)


def is_pureish(node: ast.AST) -> bool:
    """Return whether function avoids obvious IO or mutation calls."""

    for child in ast.walk(node):
        if isinstance(child, (ast.Await, ast.Global, ast.Nonlocal, ast.With, ast.Yield)):
            return False
        if isinstance(child, ast.Call) and call_name(child) in SIDE_EFFECT_NAMES:
            return False
    return True


def call_name(node: ast.Call) -> str:
    """Return simple function or method call name."""

    function = node.func
    if isinstance(function, ast.Name):
        return function.id
    if isinstance(function, ast.Attribute):
        return function.attr
    return ""


def has_boundary_name(qualname: str) -> bool:
    """Return whether function name hints parser, validator, or normalization."""

    lowered = qualname.lower()
    return any(name in lowered for name in BOUNDARY_NAMES)


def has_boundary_logic(node: ast.AST) -> bool:
    """Return whether function contains numeric or string boundary signals."""

    return any(
        has_boundary_annotation(child)
        or isinstance(child, (ast.BinOp, ast.Compare, ast.Subscript))
        or has_boundary_constant(child)
        for child in ast.walk(node)
    )


def has_boundary_annotation(node: ast.AST) -> bool:
    """Return whether annotation names numeric or string boundary types."""

    if not isinstance(node, ast.arg) or node.annotation is None:
        return False
    annotation = ast.unparse(node.annotation).lower()
    return annotation in NUMERIC_TYPES or annotation in STRING_TYPES


def has_boundary_constant(node: ast.AST) -> bool:
    """Return whether node is a numeric or string constant."""

    return isinstance(node, ast.Constant) and isinstance(node.value, (int, float, str))


def candidate_sort_key(candidate: HypothesisCandidate) -> tuple[int, str, str]:
    """Return deterministic candidate sort key."""

    return (-candidate.score, candidate.path, candidate.qualname)
