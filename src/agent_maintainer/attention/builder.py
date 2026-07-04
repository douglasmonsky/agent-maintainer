"""Build deterministic file attention ledgers."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from agent_maintainer.attention import signals
from agent_maintainer.attention.models import (
    SCHEMA_VERSION,
    AttentionFileScore,
    AttentionLedger,
)

DEFAULT_OUTPUT_PATH = Path(".verify-logs/attention/files.json")

WEIGHT_ITEMS = (
    ("git_changed", 0.24),
    ("git_churn", 0.18),
    ("runtime_events", 0.17),
    ("verifier_artifacts", 0.14),
    ("docsync", 0.1),
    ("file_baselines", 0.1),
    ("path", 0.07),
)


def build_attention_ledger(
    target: Path,
    *,
    log_dir: Path | None = None,
    events_dir: Path | None = None,
) -> AttentionLedger:
    """Return deterministic attention ledger for target repository."""
    repo_root = target.resolve()
    resolved_log_dir = log_dir or Path(".verify-logs")
    resolved_events_dir = events_dir or Path(".verify-logs/events")
    files = signals.tracked_files(repo_root)
    raw_components = {
        "git_changed": signals.changed_counts(repo_root),
        "git_churn": signals.churn_counts(repo_root),
        "runtime_events": signals.runtime_event_counts(
            repo_root,
            events_dir=repo_root / resolved_events_dir,
        ),
        "verifier_artifacts": signals.verifier_artifact_counts(
            repo_root,
            log_dir=repo_root / resolved_log_dir,
        ),
        "docsync": signals.docsync_counts(repo_root),
        "file_baselines": signals.file_baseline_counts(
            repo_root,
            log_dir=repo_root / resolved_log_dir,
        ),
    }
    normalized = {name: _normalize_counts(counts) for name, counts in raw_components.items()}
    scored_files = tuple(_score_file(path, normalized=normalized) for path in files)
    visible_files = tuple(
        sorted(
            (score for score in scored_files if score.score > 0),
            key=lambda score: (-score.score, score.path),
        )
    )
    return AttentionLedger(
        schema_version=SCHEMA_VERSION,
        target=str(repo_root),
        file_count=len(visible_files),
        inputs={
            "tracked_files": len(files),
            "log_dir": resolved_log_dir.as_posix(),
            "events_dir": resolved_events_dir.as_posix(),
            **{f"{name}_files": len(counts) for name, counts in raw_components.items()},
        },
        files=visible_files,
    )


def write_attention_ledger(ledger: AttentionLedger, output_path: Path) -> Path:
    """Write ledger JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(ledger.to_payload(), indent=2, sort_keys=True)
    output_path.write_text(
        f"{payload}\n",
        encoding="utf-8",
    )
    return output_path


def read_attention_ledger(path: Path) -> AttentionLedger:
    """Read attention ledger JSON."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    files = tuple(
        AttentionFileScore(
            path=str(item["path"]),
            score=float(item["score"]),
            components={str(key): float(value) for key, value in item["components"].items()},
            reasons=tuple(str(reason) for reason in item["reasons"]),
        )
        for item in payload.get("files", ())
    )
    return AttentionLedger(
        schema_version=int(payload["schema_version"]),
        target=str(payload["target"]),
        file_count=int(payload["file_count"]),
        inputs=dict(payload.get("inputs", {})),
        files=files,
    )


def _score_file(
    path: str,
    *,
    normalized: dict[str, dict[str, float]],
) -> AttentionFileScore:
    """Return weighted score for one file."""
    components = {name: values.get(path, float(0)) for name, values in normalized.items()}
    components["path"] = signals.path_heuristic_score(path)
    score = min(
        1.0,
        sum(weight * components[name] for name, weight in WEIGHT_ITEMS),
    )
    rounded_components = {
        name: round(value, 4) for name, value in sorted(components.items()) if value > 0
    }
    return AttentionFileScore(
        path=path,
        score=round(score, 4),
        components=rounded_components,
        reasons=_reasons(path, rounded_components),
    )


def _normalize_counts(counts: Counter[str]) -> dict[str, float]:
    """Normalize count values to 0..1."""
    if not counts:
        return {}
    max_count = max(counts.values())
    if max_count <= 0:
        return {}
    return {path: min(1.0, count / max_count) for path, count in counts.items() if count > 0}


def _reasons(path: str, components: dict[str, float]) -> tuple[str, ...]:
    """Return human-readable non-zero component reasons."""
    labels = {
        "docsync": "mentioned by DocSync evidence",
        "file_baselines": "mentioned by file-baseline evidence",
        "git_changed": "changed in current worktree or index",
        "git_churn": "recent committed churn",
        "path": "important repository path",
        "runtime_events": "mentioned by runtime events",
        "verifier_artifacts": "mentioned by verifier artifacts",
    }
    return tuple(f"{path}: {labels[name]}" for name in sorted(components))
