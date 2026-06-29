"""Advisory CrossHair contract-analysis candidate ranking."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.test_intel import hypothesis_candidates

ADVISORY_NOTE = "Advisory only; this command does not run CrossHair."
DEFAULT_LIMIT = 10
MAX_BRANCH_COMPLEXITY = 8
MAX_STATEMENTS = 45
MIN_SCORE = 5
SMALL_STATEMENT_BONUS_LIMIT = 20
CONTRACT_DOC_MARKERS = frozenset(
    (
        "ensures",
        "post:",
        "postcondition",
        "pre:",
        "precondition",
        "requires",
    )
)
CONTRACT_DECORATORS = frozenset(
    (
        "deal.ensure",
        "deal.post",
        "deal.pre",
        "icontract.ensure",
        "icontract.require",
        "icontract.snapshot",
    )
)
UNSAFE_MODULES = frozenset(
    (
        "asyncio",
        "http",
        "os",
        "pathlib",
        "requests",
        "shutil",
        "socket",
        "sqlite3",
        "subprocess",
    )
)
UNSAFE_CALLS = frozenset(
    (
        "connect",
        "delete",
        "execute",
        "get",
        "mkdir",
        "open",
        "patch",
        "post",
        "put",
        "remove",
        "rename",
        "replace",
        "request",
        "rmdir",
        "run",
        "send",
        "touch",
        "unlink",
        "write",
    )
)


@dataclass(frozen=True)
class CrosshairCandidate:
    """One advisory CrossHair analysis target."""

    path: str
    qualname: str
    score: int
    complexity: int
    contract: str
    reasons: tuple[str, ...]
    suggested_command: str
    note: str = ADVISORY_NOTE

    def to_json(self) -> dict[str, object]:
        """Return stable JSON payload."""

        return {
            "path": self.path,
            "qualname": self.qualname,
            "score": self.score,
            "complexity": self.complexity,
            "contract": self.contract,
            "reasons": list(self.reasons),
            "suggested_command": self.suggested_command,
            "note": self.note,
        }


@dataclass(frozen=True)
class CrosshairCandidateReport:
    """Advisory CrossHair candidate report."""

    changed_only: bool
    changed_source: tuple[str, ...]
    candidates: tuple[CrosshairCandidate, ...]
    note: str = ADVISORY_NOTE

    def to_json(self) -> dict[str, object]:
        """Return stable JSON payload."""

        return {
            "changed_only": self.changed_only,
            "changed_source": list(self.changed_source),
            "candidates": [candidate.to_json() for candidate in self.candidates],
            "note": self.note,
        }


@dataclass(frozen=True)
class CrosshairCandidateRequest:
    """Inputs for CrossHair candidate report construction."""

    config: MaintainerConfig
    repo_root: Path
    changed_only: bool
    changed_source: tuple[str, ...] = ()
    limit: int = DEFAULT_LIMIT


@dataclass(frozen=True)
class CrosshairSignals:
    """CrossHair candidate scoring signals."""

    complexity: int
    changed: bool
    contract: str
    statement_count: int


def build_crosshair_candidate_report(
    request: CrosshairCandidateRequest,
) -> CrosshairCandidateReport:
    """Return advisory CrossHair candidate report."""

    source_paths = (
        request.changed_source
        if request.changed_only
        else hypothesis_candidates.discover_source_files(request.config, request.repo_root)
    )
    changed_set = frozenset(request.changed_source)
    candidates = [
        candidate
        for source_path in source_paths
        for candidate in candidates_for_source(
            source_path,
            request.repo_root,
            changed=source_path in changed_set,
        )
    ]
    ranked = tuple(sorted(candidates, key=candidate_sort_key)[: request.limit])
    return CrosshairCandidateReport(
        changed_only=request.changed_only,
        changed_source=request.changed_source,
        candidates=ranked,
    )


def candidates_for_source(
    source_path: str,
    repo_root: Path,
    *,
    changed: bool,
) -> tuple[CrosshairCandidate, ...]:
    """Return CrossHair candidates for one source path."""

    source_file = repo_root / source_path
    try:
        tree = ast.parse(source_file.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return ()
    candidates = [
        candidate
        for function in hypothesis_candidates.iter_public_functions(tree)
        if (
            candidate := candidate_for_function(
                source_path,
                function,
                changed=changed,
            )
        )
    ]
    return tuple(sorted(candidates, key=candidate_sort_key))


def candidate_for_function(
    source_path: str,
    function: tuple[str, ast.FunctionDef],
    *,
    changed: bool,
) -> CrosshairCandidate | None:
    """Return CrossHair candidate when function is typed, contracted, and safe."""

    qualname, node = function
    if not is_fully_typed(node) or not is_safe_for_crosshair(node):
        return None
    contract = contract_style(node)
    if not contract:
        return None
    signals = CrosshairSignals(
        complexity=hypothesis_candidates.branch_complexity(node),
        changed=changed,
        contract=contract,
        statement_count=statement_count(node),
    )
    if not is_bounded_for_analysis(signals):
        return None
    score, reasons = candidate_score(signals)
    if score < MIN_SCORE:
        return None
    return CrosshairCandidate(
        path=source_path,
        qualname=qualname,
        score=score,
        complexity=signals.complexity,
        contract=signals.contract,
        reasons=tuple(reasons),
        suggested_command=f"crosshair check {source_path}",
    )


def is_fully_typed(node: ast.FunctionDef) -> bool:
    """Return true when public inputs and output have annotations."""

    if node.returns is None:
        return False
    arguments = [
        *node.args.posonlyargs,
        *node.args.args,
        *node.args.kwonlyargs,
    ]
    public_arguments = [argument for argument in arguments if argument.arg not in {"self", "cls"}]
    return all(argument.annotation is not None for argument in public_arguments)


def contract_style(node: ast.FunctionDef) -> str:
    """Return the visible contract style for a function."""

    if any(isinstance(child, ast.Assert) for child in ast.walk(node)):
        return "assert"
    decorator = decorator_contract(node)
    if decorator:
        return decorator
    docstring = ast.get_docstring(node) or ""
    lowered = docstring.lower()
    if any(marker in lowered for marker in CONTRACT_DOC_MARKERS):
        return "docstring"
    return ""


def decorator_contract(node: ast.FunctionDef) -> str:
    """Return contract decorator style when one is present."""

    for decorator in node.decorator_list:
        name = expression_name(decorator)
        if name in CONTRACT_DECORATORS:
            return name.split(".", maxsplit=1)[0]
    return ""


def expression_name(node: ast.AST) -> str:
    """Return dotted expression name for call and attribute nodes."""

    if isinstance(node, ast.Call):
        return expression_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base_name = expression_name(node.value)
        return f"{base_name}.{node.attr}" if base_name else node.attr
    return ""


def is_safe_for_crosshair(node: ast.FunctionDef) -> bool:
    """Return true when a function avoids obvious IO and mutation."""

    for child in ast.walk(node):
        if isinstance(
            child, (ast.Await, ast.Delete, ast.Global, ast.Nonlocal, ast.While, ast.With)
        ):
            return False
        if isinstance(child, ast.Call) and is_unsafe_call(child):
            return False
        if isinstance(child, ast.Import | ast.ImportFrom):
            return False
    return True


def is_unsafe_call(node: ast.Call) -> bool:
    """Return true for calls that imply IO, subprocesses, or persistence."""

    name = expression_name(node.func)
    root_name = name.split(".", maxsplit=1)[0]
    leaf_name = name.rsplit(".", maxsplit=1)[-1]
    return root_name in UNSAFE_MODULES or leaf_name in UNSAFE_CALLS


def is_bounded_for_analysis(signals: CrosshairSignals) -> bool:
    """Return true when candidate is small enough for advisory analysis."""

    return signals.complexity <= MAX_BRANCH_COMPLEXITY and signals.statement_count <= MAX_STATEMENTS


def statement_count(node: ast.AST) -> int:
    """Return number of statement nodes below a function."""

    return sum(isinstance(child, ast.stmt) for child in ast.walk(node))


def candidate_score(signals: CrosshairSignals) -> tuple[int, list[str]]:
    """Return CrossHair candidate score and reasons."""

    score = 4
    reasons = ["fully typed function", f"{signals.contract} contract"]
    if signals.changed:
        score += 3
        reasons.append("changed source")
    if signals.complexity > 1:
        score += signals.complexity
        reasons.append(f"branch complexity {signals.complexity}")
    if signals.statement_count <= SMALL_STATEMENT_BONUS_LIMIT:
        score += 2
        reasons.append("small bounded body")
    return score, reasons


def candidate_sort_key(candidate: CrosshairCandidate) -> tuple[int, int, str, str]:
    """Return deterministic candidate sort key."""

    return (-candidate.score, candidate.complexity, candidate.path, candidate.qualname)
