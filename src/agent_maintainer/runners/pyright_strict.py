"""Run strict Pyright as a baseline ratchet."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import subprocess  # nosec B404
import sys
import typing
from pathlib import Path

from agent_maintainer.core import config as maintainer_config
from agent_maintainer.core.executor import command_env
from agent_maintainer.runners import pyright
from agent_maintainer.runners import pyright_strict_baseline as strict_baseline

PYRIGHT_STRICT_CONFIG_NAME = "pyrightconfig.strict.generated.json"
PYRIGHT_STRICT_JSON_NAME = "pyright-strict.json"
PYRIGHT_STRICT_BASELINE_CANDIDATE_NAME = "pyright-strict-baseline-candidate.json"
UNKNOWN_RULE = "unknown-rule"


@dataclasses.dataclass(frozen=True)
class StrictScope:
    """Canonical repository scope from the generated strict config."""

    repo_root: Path
    include_roots: tuple[Path, ...]
    sha256: str


class StrictPayloadError(ValueError):
    """Raised when Pyright output cannot be safely ratcheted."""


def main() -> int:
    """Run strict Pyright and compare against configured baseline."""

    config = maintainer_config.load_config()
    if not config.pyright_strict_ratchet_enabled:
        print("pyright strict ratchet skipped: disabled")
        return 0
    return run_strict_ratchet(config)


def run_strict_ratchet(config: maintainer_config.MaintainerConfig) -> int:
    """Run strict Pyright and return ratchet exit code."""

    if config.pyright_strict_max_errors != 0:
        print(
            "pyright strict max-errors budget must be 0 for the file/rule v2 ratchet; "
            "a global budget would permit error substitution."
        )
        return 1
    output_dir = Path(config.diagnostic_artifacts_dir)
    strict_config = strict_pyright_config(config)
    config_path = pyright.write_pyright_config(
        output_dir,
        strict_config,
        config_name=PYRIGHT_STRICT_CONFIG_NAME,
    )
    current = collect_current_stats(config_path, output_dir=output_dir)
    if current is None:
        return 1
    write_baseline_candidate(
        output_dir / PYRIGHT_STRICT_BASELINE_CANDIDATE_NAME,
        current,
    )
    baseline = strict_baseline.load_baseline(Path(config.pyright_strict_baseline))
    if baseline is None:
        candidate = output_dir / PYRIGHT_STRICT_BASELINE_CANDIDATE_NAME
        print(f"Candidate for intentional review: {candidate}")
        return 1
    result = strict_baseline.compare_stats(current, baseline)
    print(strict_baseline.format_result(result))
    return 0 if result.passed else 1


def collect_current_stats(
    config_path: Path,
    *,
    output_dir: Path,
) -> strict_baseline.StrictPyrightStats | None:
    """Run Pyright and return canonical stats, reporting malformed evidence."""

    try:
        scope = scope_from_config(config_path, repo_root=Path.cwd())
    except StrictPayloadError as exc:
        print(f"pyright strict scope invalid: {exc}")
        return None
    payload = run_pyright_json(config_path, output_dir / PYRIGHT_STRICT_JSON_NAME)
    if payload is None:
        return None
    try:
        return stats_from_payload(payload, scope=scope)
    except StrictPayloadError as exc:
        print(f"pyright strict output invalid: {exc}")
        return None


def strict_pyright_config(
    config: maintainer_config.MaintainerConfig,
) -> maintainer_config.MaintainerConfig:
    """Return config copy forcing strict type checking."""

    return dataclasses.replace(config, pyright_type_checking_mode="strict")


def run_pyright_json(
    config_path: Path,
    output_path: Path,
) -> dict[str, typing.Any] | None:
    """Run Pyright and return parsed JSON, preserving stdout artifact."""

    result = subprocess.run(  # nosec B603
        [
            pyright.pyright_executable(),
            "--project",
            str(config_path),
            "--pythonpath",
            pyright.python_interpreter(),
            "--outputjson",
        ],
        text=True,
        capture_output=True,
        env=command_env(),
        check=False,
    )
    pyright.write_json_output(output_path, result.stdout)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("pyright strict did not produce JSON output.")
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        return None
    if result.returncode not in {0, 1}:
        print(f"pyright strict failed with exit code {result.returncode}.")
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        return None
    if isinstance(payload, dict):
        return typing.cast(dict[str, typing.Any], payload)
    print("pyright strict JSON output was not an object.")
    return None


def stats_from_payload(
    payload: dict[str, typing.Any],
    *,
    scope: StrictScope,
) -> strict_baseline.StrictPyrightStats:
    """Build canonical, internally consistent counts from Pyright diagnostics."""

    diagnostics = diagnostic_errors(payload)
    summary = summary_payload(payload)
    reported_errors = summary_count(summary, "errorCount", minimum=0)
    if reported_errors != len(diagnostics):
        raise StrictPayloadError(
            "summary.errorCount does not match error diagnostics "
            f"({reported_errors} != {len(diagnostics)})"
        )
    files_analyzed = summary_count(summary, "filesAnalyzed", minimum=1)
    version = payload.get("version")
    if not isinstance(version, str) or not version:
        raise StrictPayloadError("version must be a non-empty string")
    return strict_baseline.StrictPyrightStats(
        files_analyzed=files_analyzed,
        pyright_version=version,
        scope_sha256=scope.sha256,
        pairs=count_by_pair(diagnostics, scope=scope),
    )


def summary_count(summary: dict[str, typing.Any], key: str, *, minimum: int) -> int:
    """Return one plain integer Pyright summary count."""

    value = summary.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise StrictPayloadError(f"summary.{key} must be an integer >= {minimum}")
    return value


def diagnostic_errors(payload: dict[str, typing.Any]) -> list[dict[str, typing.Any]]:
    """Return error diagnostics from Pyright JSON payload."""

    raw_diagnostics = payload.get("generalDiagnostics")
    if not isinstance(raw_diagnostics, list):
        raise StrictPayloadError("generalDiagnostics must be a list")
    diagnostics: list[dict[str, typing.Any]] = []
    for diagnostic in typing.cast(list[object], raw_diagnostics):
        if not isinstance(diagnostic, dict):
            raise StrictPayloadError("generalDiagnostics entries must be objects")
        typed_diagnostic = typing.cast(dict[str, typing.Any], diagnostic)
        severity = typed_diagnostic.get("severity")
        if severity not in {"error", "warning", "information"}:
            raise StrictPayloadError("diagnostic severity is invalid")
        if severity == "error":
            diagnostics.append(typed_diagnostic)
    return diagnostics


def summary_payload(payload: dict[str, typing.Any]) -> dict[str, typing.Any]:
    """Return summary object from Pyright JSON payload."""

    summary = payload.get("summary", {})
    if isinstance(summary, dict):
        return typing.cast(dict[str, typing.Any], summary)
    return {}


def count_by_pair(
    diagnostics: list[dict[str, typing.Any]],
    *,
    scope: StrictScope,
) -> strict_baseline.PairCounts:
    """Return error counts keyed by canonical file and rule."""

    pairs: strict_baseline.PairCounts = {}
    for diagnostic in diagnostics:
        file = normalize_file(diagnostic.get("file"), scope=scope)
        rule = str(diagnostic.get("rule") or UNKNOWN_RULE)
        rules = pairs.setdefault(file, {})
        rules[rule] = rules.get(rule, 0) + 1
    return pairs


def normalize_file(file_value: object, *, scope: StrictScope) -> str:
    """Return a canonical in-scope repository-relative diagnostic path."""

    if not isinstance(file_value, str) or not file_value:
        raise StrictPayloadError("diagnostic file must be a non-empty string")
    raw_path = Path(file_value)
    candidate = raw_path if raw_path.is_absolute() else scope.repo_root / raw_path
    resolved = candidate.resolve()
    try:
        relative = resolved.relative_to(scope.repo_root)
    except ValueError as exc:
        raise StrictPayloadError(f"diagnostic file escapes repository: {file_value}") from exc
    if not any(resolved == root or root in resolved.parents for root in scope.include_roots):
        raise StrictPayloadError(
            f"diagnostic file is outside strict include scope: {relative.as_posix()}"
        )
    return relative.as_posix()


def scope_from_config(config_path: Path, *, repo_root: Path) -> StrictScope:
    """Return normalized scope identity from a generated strict config."""

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StrictPayloadError(f"cannot read generated config: {exc}") from exc
    if not isinstance(raw, dict):
        raise StrictPayloadError("generated config must be an object")
    payload = typing.cast(dict[str, typing.Any], raw)
    canonical = dict(payload)
    resolved_by_key: dict[str, tuple[Path, ...]] = {}
    root = repo_root.resolve()
    for key in ("include", "exclude", "extraPaths"):
        resolved, relative = canonical_scope_paths(
            payload.get(key),
            key=key,
            config_path=config_path,
            repo_root=root,
        )
        resolved_by_key[key] = resolved
        canonical[key] = relative
    if not resolved_by_key["include"]:
        raise StrictPayloadError("generated config include must not be empty")
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return StrictScope(
        repo_root=root,
        include_roots=resolved_by_key["include"],
        sha256=hashlib.sha256(encoded).hexdigest(),
    )


def canonical_scope_paths(
    value: object,
    *,
    key: str,
    config_path: Path,
    repo_root: Path,
) -> tuple[tuple[Path, ...], list[str]]:
    """Resolve one generated path list and keep it repository-confined."""

    if not isinstance(value, list):
        raise StrictPayloadError(f"generated config {key} must be a string list")
    items = typing.cast(list[object], value)
    if any(not isinstance(item, str) for item in items):
        raise StrictPayloadError(f"generated config {key} must be a string list")
    resolved_paths: list[Path] = []
    relative_paths: list[str] = []
    for item in typing.cast(list[str], items):
        resolved = (config_path.parent / item).resolve()
        try:
            relative = resolved.relative_to(repo_root)
        except ValueError as exc:
            message = f"generated config {key} path escapes repository: {item}"
            raise StrictPayloadError(message) from exc
        resolved_paths.append(resolved)
        relative_paths.append(relative.as_posix() or ".")
    return tuple(resolved_paths), relative_paths


def write_baseline_candidate(path: Path, current: strict_baseline.StrictPyrightStats) -> None:
    """Write a non-committed v2 candidate for explicit debt review."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        strict_baseline.baseline_json(
            current,
            note="Candidate only: review genuine defects and every remaining file/rule allowance.",
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    sys.exit(main())
