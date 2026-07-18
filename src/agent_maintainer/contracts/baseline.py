"""Canonical generated baseline evidence for semantic contracts."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from agent_maintainer.contracts.limits import MAX_CONTRACTS
from agent_maintainer.contracts.models import (
    BaselineError,
    ContractBaseline,
    Descriptor,
)
from agent_maintainer.contracts.paths import read_confined_text, resolve_confined_path
from agent_maintainer.core.repo_paths import RepoPathError, validate_repo_path

DEFAULT_BASELINE_PATH = Path(".agent-maintainer/contracts-baseline.json")
KINDS = frozenset(("config-capabilities", "cli-manifest", "python-api", "json-schema"))


def fingerprint(value: object) -> str:
    """Return the exact SHA-256 of canonical JSON-compatible semantic data."""

    encoded = canonical_json(value).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def canonical_json(value: object) -> str:
    """Return compact deterministic JSON for semantic ordering and hashing."""

    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def load_baseline(
    repo_root: Path,
    path: Path = DEFAULT_BASELINE_PATH,
) -> ContractBaseline | None:
    """Load canonical baseline evidence, or return None when absent."""

    candidate = repo_root / path
    if not candidate.exists() and not candidate.is_symlink():
        return None
    try:
        text = read_confined_text(repo_root, path.as_posix(), label="contract baseline")
    except ValueError as exc:
        raise BaselineError(str(exc)) from exc
    return parse_baseline(text, source=path.as_posix())


def parse_baseline(text: str, *, source: str) -> ContractBaseline:
    """Decode and verify one canonical baseline document."""

    try:
        raw = json.loads(text, object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, BaselineError) as exc:
        raise BaselineError(f"invalid contract baseline {source}") from exc
    if not isinstance(raw, dict):
        raise BaselineError("contract baseline must be a JSON object")
    payload = cast(dict[str, object], raw)
    _exact_keys(
        payload,
        frozenset(
            (
                "descriptors",
                "document_fingerprint",
                "generator",
                "package_version",
                "schema_version",
            )
        ),
        "baseline",
    )
    expected_document = _verify_document_identity(payload)
    raw_descriptors = payload.get("descriptors")
    if not isinstance(raw_descriptors, list):
        raise BaselineError("descriptors must be a bounded array")
    descriptor_values = cast(list[object], raw_descriptors)
    if len(descriptor_values) > MAX_CONTRACTS:
        raise BaselineError("descriptors must be a bounded array")
    descriptors = tuple(_decode_descriptor(item) for item in descriptor_values)
    identities = tuple(item.contract_id for item in descriptors)
    if len(identities) != len(set(identities)):
        raise BaselineError("duplicate baseline contract")
    if identities != tuple(sorted(identities)):
        raise BaselineError("baseline contracts must be sorted")
    return ContractBaseline(
        package_version=_text(payload.get("package_version"), "package_version"),
        descriptors=descriptors,
        document_fingerprint=expected_document,
    )


def render_baseline(baseline: ContractBaseline) -> str:
    """Render deterministic verified baseline JSON with one trailing newline."""

    descriptors = sorted(baseline.descriptors, key=lambda item: item.contract_id)
    payload: dict[str, object] = {
        "descriptors": [_descriptor_to_dict(item) for item in descriptors],
        "generator": baseline.generator,
        "package_version": baseline.package_version,
        "schema_version": baseline.schema_version,
    }
    payload["document_fingerprint"] = fingerprint(payload)
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def write_baseline_atomic(
    repo_root: Path,
    path: Path,
    baseline: ContractBaseline,
) -> None:
    """Atomically replace the exact confined nonsymlinked baseline path."""

    destination = _prepare_destination(repo_root, path)
    temporary_name = ""
    try:
        temporary_name = _write_temporary(destination, render_baseline(baseline))
        _revalidate_destination(repo_root, path, destination)
        os.replace(temporary_name, destination)
        temporary_name = ""
    except OSError as exc:
        raise BaselineError("could not atomically write contract baseline") from exc
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)


def _prepare_destination(repo_root: Path, path: Path) -> Path:
    try:
        destination = resolve_confined_path(repo_root, path.as_posix(), label="contract baseline")
    except ValueError as exc:
        raise BaselineError(str(exc)) from exc
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        metadata = destination.lstat()
    except FileNotFoundError:
        metadata = None
    except OSError as exc:
        raise BaselineError("contract baseline destination is unavailable") from exc
    if metadata is not None and not stat.S_ISREG(metadata.st_mode):
        raise BaselineError("contract baseline destination must be a regular file")
    return destination


def _write_temporary(destination: Path, content: str) -> str:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=destination.parent,
        prefix=f".{destination.name}.",
        delete=False,
    ) as temporary:
        os.chmod(temporary.name, 0o600)
        temporary.write(content)
        temporary.flush()
        os.fsync(temporary.fileno())
        return temporary.name


def _revalidate_destination(repo_root: Path, path: Path, destination: Path) -> None:
    try:
        revalidated = resolve_confined_path(
            repo_root,
            path.as_posix(),
            label="contract baseline",
        )
    except ValueError as exc:
        raise BaselineError(str(exc)) from exc
    if revalidated != destination:
        raise BaselineError("contract baseline destination changed during write")


def _descriptor_to_dict(descriptor: Descriptor) -> dict[str, object]:
    return {
        "body": descriptor.body,
        "contract_id": descriptor.contract_id,
        "fingerprint": descriptor.fingerprint,
        "kind": descriptor.kind,
        "owner": descriptor.owner,
        "revision": descriptor.revision,
        "sources": list(descriptor.sources),
        "stability": descriptor.stability,
    }


def _decode_descriptor(value: object) -> Descriptor:
    if not isinstance(value, dict):
        raise BaselineError("descriptor must be an object")
    raw = cast(dict[str, object], value)
    _exact_keys(
        raw,
        frozenset(
            (
                "body",
                "contract_id",
                "fingerprint",
                "kind",
                "owner",
                "revision",
                "sources",
                "stability",
            )
        ),
        "descriptor",
    )
    body = raw.get("body")
    if not isinstance(body, dict):
        raise BaselineError("descriptor body must be an object")
    kind = raw.get("kind")
    if not isinstance(kind, str) or kind not in KINDS:
        raise BaselineError("descriptor kind is unsupported")
    sources = _text_array(raw.get("sources"), "descriptor sources")
    try:
        canonical_sources = tuple(
            validate_repo_path(item, label="descriptor source")
            for item in sources
        )
    except RepoPathError as exc:
        raise BaselineError(str(exc)) from exc
    if canonical_sources != tuple(sorted(set(canonical_sources))):
        raise BaselineError("descriptor sources must be sorted and unique")
    descriptor = Descriptor(
        contract_id=_text(raw.get("contract_id"), "contract_id"),
        kind=kind,
        owner=_text(raw.get("owner"), "owner"),
        stability=_text(raw.get("stability"), "stability"),
        revision=_positive_int(raw.get("revision"), "revision"),
        sources=canonical_sources,
        body=cast(dict[str, object], body),
        fingerprint=_text(raw.get("fingerprint"), "fingerprint"),
    )
    semantic = _descriptor_to_dict(descriptor)
    semantic.pop("fingerprint")
    if fingerprint(semantic) != descriptor.fingerprint:
        raise BaselineError("descriptor fingerprint mismatch")
    return descriptor


def _verify_document_identity(payload: dict[str, object]) -> str:
    expected = _text(payload.get("document_fingerprint"), "document_fingerprint")
    semantic = {
        key: value
        for key, value in payload.items()
        if key != "document_fingerprint"
    }
    if fingerprint(semantic) != expected:
        raise BaselineError("document fingerprint mismatch")
    if payload.get("schema_version") != 1 or isinstance(payload.get("schema_version"), bool):
        raise BaselineError("baseline schema_version must be exactly 1")
    if payload.get("generator") != "agent-maintainer":
        raise BaselineError("unsupported baseline generator")
    return expected


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise BaselineError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _exact_keys(raw: Mapping[str, object], allowed: frozenset[str], label: str) -> None:
    missing = sorted(allowed - set(raw))
    unknown = sorted(set(raw) - allowed)
    if missing:
        raise BaselineError(f"{label} missing key: {missing[0]}")
    if unknown:
        raise BaselineError(f"{label} unknown key: {unknown[0]}")


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise BaselineError(f"{label} must be non-empty text")
    return value


def _text_array(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise BaselineError(f"{label} must be text")
    values = cast(list[object], value)
    if not all(isinstance(item, str) for item in values):
        raise BaselineError(f"{label} must be text")
    return tuple(item for item in values if isinstance(item, str))


def _positive_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise BaselineError(f"{label} must be a positive integer")
    return value
