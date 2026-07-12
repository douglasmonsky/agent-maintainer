# Attention Priority Retention and Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve direct and failure-relevant paths across large-repository sampling and label every context attention entry by evidence relevance.

**Architecture:** Discover changed and verifier-failure paths against one bounded 10,000-path inventory before applying the 5,000-file background scoring budget. Context packs separately preserve direct exact/requested paths, infer log mentions, and use background ledger fallbacks without implying causal risk.

**Tech Stack:** Python 3.11+, dataclasses, pytest, bounded Git/artifact readers, JSON context packs, Markdown rendering.

## Global Constraints

- Total scored work must not exceed `DEFAULT_TRACKED_DISCOVERY_LIMIT` (10,000 paths).
- Every required path inside that bounded tracked inventory survives the background cap.
- Invalid explicit priority paths fail at the API/CLI boundary; safe untracked paths are noted and omitted from ledger scoring.
- Ledger scores remain finite numbers in `0..1`; only context entries missing from an older valid ledger may use `score: null`.
- Background-only selections emit no risk notes in tight hook output.
- Preserve all safe-read, confinement, artifact-byte, and deterministic-order guarantees.

---

### Task 1: Reserve changed, failed, and explicit paths before sampling

**Files:**

- Modify: `tests/attention/test_attention_builder.py`
- Modify: `src/agent_maintainer/attention/signal_context.py`
- Modify: `src/agent_maintainer/attention/builder.py`

**Interfaces:**

- Consumes: one tuple from `signals.tracked_files`, `signals.changed_counts`, and `signals.verifier_artifact_counts`.
- Produces: `build_attention_ledger(..., priority_paths: Sequence[str] = ())` and `AttentionSignalContext.from_paths(..., required_paths: Iterable[str] = ())`.

- [ ] **Step 1: Write failing priority-retention tests**

Add to `tests/attention/test_attention_builder.py`:

```python
def test_attention_cap_retains_changed_and_verifier_failure_paths(tmp_path: Path) -> None:
    """Automatic direct signals displace unrelated background samples."""

    _init_repo(tmp_path)
    for index in range(5):
        _write(tmp_path / "src" / f"file_{index}.py", f"VALUE = {index}\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")
    _write(tmp_path / "src" / "file_2.py", "VALUE = 20\n")
    _write(
        tmp_path / ".verify-logs" / "runs" / "run-1" / "manifest.json",
        json.dumps({"checks": [{"summary": "failure in src/file_3.py"}]}),
    )

    ledger = builder.build_attention_ledger(tmp_path, max_tracked_files=2)
    paths = {item.path for item in ledger.files}

    assert {"src/file_2.py", "src/file_3.py"} <= paths
    guards = cast(dict[str, object], ledger.inputs["performance_guards"])
    assert guards["scored_file_count"] == 2


def test_attention_required_paths_can_use_soft_background_cap(tmp_path: Path) -> None:
    """Required paths remain bounded by discovery when they exceed background cap."""

    for index in range(5):
        _write(tmp_path / "src" / f"file_{index}.py", f"VALUE = {index}\n")

    ledger = builder.build_attention_ledger(
        tmp_path,
        max_tracked_files=2,
        priority_paths=("src/file_1.py", "src/file_2.py", "src/file_3.py"),
    )
    paths = {item.path for item in ledger.files}
    guards = cast(dict[str, object], ledger.inputs["performance_guards"])

    assert {"src/file_1.py", "src/file_2.py", "src/file_3.py"} <= paths
    assert guards["scored_file_count"] == 3
    assert "required paths exceeded tracked file cap 3/2" in " ".join(
        cast(list[str], guards["notes"])
    )
```

- [ ] **Step 2: Run the tests to verify RED**

Run: `PYTHONPATH=src .venv/bin/pytest tests/attention/test_attention_builder.py -k 'cap_retains or soft_background_cap' -q`

Expected: the first test omits at least one direct path and the second errors on
the unsupported `priority_paths` argument.

- [ ] **Step 3: Add deterministic required-path sampling**

In `signal_context.py`, import `Iterable` and add a `from_paths` constructor.
Have `build` delegate to it after calling the provider exactly once:

```python
@classmethod
def from_paths(
    cls,
    repo_root: Path,
    paths: tuple[str, ...],
    *,
    required_paths: Iterable[str] = (),
    max_tracked_files: int = DEFAULT_MAX_TRACKED_FILES,
    artifact_read_limit_bytes: int = DEFAULT_ARTIFACT_READ_LIMIT_BYTES,
) -> AttentionSignalContext:
    """Build one bounded context from an already collected inventory."""

    required = frozenset(required_paths).intersection(paths)
    sampled_paths = _sample_paths(paths, max_tracked_files, required_paths=required)
    notes: list[str] = []
    if len(sampled_paths) < len(paths):
        notes.append(
            "tracked file set capped "
            f"{len(sampled_paths)}/{len(paths)} using deterministic sampling"
        )
    if len(required) > max_tracked_files > 0:
        notes.append(
            "required paths exceeded tracked file cap "
            f"{len(required)}/{max_tracked_files}; retained within "
            f"{len(paths)}-path discovery inventory"
        )
    return cls(
        repo_root=repo_root,
        tracked_paths=sampled_paths,
        all_tracked_file_count=len(paths),
        artifact_read_limit_bytes=artifact_read_limit_bytes,
        performance_notes=notes,
    )
```

Change `_sample_paths` to accept `required_paths: frozenset[str]`. If no cap is
active, return `paths`. Otherwise reserve every required path, even when the
required count exceeds the background cap, even-sample only the remaining
slots, and return the sorted union. Extract the old index math to
`_even_sample(paths, limit)` so both paths stay deterministic.

- [ ] **Step 4: Discover automatic required paths against the full inventory**

In `builder.py`, add `priority_paths: Sequence[str] = ()` to
`build_attention_ledger`. Collect `tracked_paths = signals.tracked_files(repo_root)`
once and construct an inventory context directly from all tracked paths. Compute
`changed` and `verifier_artifacts` before sampling. Validate explicit paths with:

```python
def _validated_priority_paths(
    values: Sequence[str],
    *,
    tracked_paths: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    tracked = set(tracked_paths)
    retained: set[str] = set()
    omitted: list[str] = []
    for value in values:
        normalized = _repo_relative_path(value)
        if file_safety.sensitive_path(Path(normalized)):
            raise ValueError(f"priority path is sensitive: {normalized!r}")
        if normalized in tracked:
            retained.add(normalized)
        else:
            omitted.append(f"priority path not tracked and omitted: {normalized}")
    return tuple(sorted(retained)), tuple(omitted)
```

Build the final context with required paths equal to the union of changed,
verifier-artifact, and validated explicit keys. Reuse the precomputed changed
and verifier counters in `raw_components`; calculate all other signals with the
sampled context. Carry bounded artifact-refusal notes and explicit omission
notes into the final performance notes.

- [ ] **Step 5: Verify GREEN and collection count**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest \
  tests/attention/test_attention_builder.py::test_attention_cap_retains_changed_and_verifier_failure_paths \
  tests/attention/test_attention_builder.py::test_attention_required_paths_can_use_soft_background_cap \
  tests/attention/test_attention_builder.py::test_attention_ledger_collects_tracked_files_once \
  tests/attention/test_attention_builder.py::test_attention_ledger_reports_tracked_file_cap -q
```

Expected: PASS; the old cap-note test keeps its exact text when required paths
do not overflow.

- [ ] **Step 6: Commit the sampling slice**

```bash
git add -- tests/attention/test_attention_builder.py src/agent_maintainer/attention/signal_context.py src/agent_maintainer/attention/builder.py
git commit -m "fix: retain required attention paths"
```

### Task 2: Expose explicit priority paths through the attention CLI

**Files:**

- Modify: `tests/attention/test_attention_cli.py`
- Modify: `src/agent_maintainer/attention/cli.py`

**Interfaces:**

- Consumes: `build_attention_ledger(..., priority_paths=...)` from Task 1.
- Produces: repeatable `attention --priority-path <repo-relative-path>` on update and in-memory builds.

- [ ] **Step 1: Write failing parser and forwarding tests**

Add:

```python
def test_attention_cli_accepts_repeatable_priority_paths() -> None:
    """Callers can preserve explicitly requested repository paths."""

    args = cli.parse_args(
        [
            "--priority-path",
            "src/app.py",
            "update",
            "--priority-path",
            "tests/test_app.py",
        ]
    )

    assert args.priority_path == ["src/app.py", "tests/test_app.py"]
```

Add this builder test:

```python
def test_attention_priority_paths_reject_noncanonical_input(tmp_path: Path) -> None:
    """Explicit priority paths cannot escape the repository."""

    with pytest.raises(ValueError, match="canonical repository-relative"):
        builder.build_attention_ledger(
            tmp_path,
            priority_paths=("../outside",),
        )
```

- [ ] **Step 2: Run tests to verify RED**

Run: `PYTHONPATH=src .venv/bin/pytest tests/attention/test_attention_cli.py::test_attention_cli_accepts_repeatable_priority_paths tests/attention/test_attention_builder.py -k 'priority_paths or outside' -q`

Expected: argparse rejects `--priority-path`.

- [ ] **Step 3: Add and forward the repeatable option**

In `_add_common_options`, use a suppressed subparser default and append action:

```python
priority_default = argparse.SUPPRESS if suppress_defaults else []
parser.add_argument(
    "--priority-path",
    action="append",
    default=priority_default,
    help="Repository-relative path that must survive background sampling; repeatable.",
)
```

Pass `priority_paths=tuple(args.priority_path or ())` in both the update build
and `_load_or_build` fallback build.

- [ ] **Step 4: Verify GREEN and commit**

Run: `PYTHONPATH=src .venv/bin/pytest tests/attention/test_attention_cli.py tests/attention/test_attention_builder.py -q`

Expected: PASS.

```bash
git add -- tests/attention/test_attention_cli.py tests/attention/test_attention_builder.py src/agent_maintainer/attention/cli.py
git commit -m "feat: accept attention priority paths"
```

### Task 3: Add direct, inferred, and background context provenance

**Files:**

- Modify: `tests/attention/test_attention_context_pack.py`
- Modify: `src/agent_maintainer/context/pack/attention.py`
- Modify: `src/agent_maintainer/context/pack/builder.py`
- Modify: `src/agent_context/attention_rendering.py`

**Interfaces:**

- Consumes: exact-fact paths, `ContextPackRequest.files`, selected logs, and a valid attention ledger.
- Produces: attention block schema version 1 and entries with `relevance` in `direct | inferred | background`.

- [ ] **Step 1: Write failing provenance tests**

Update the no-ledger expected payload to include `"schema_version": 1`. Extend
the exact-fact and log tests with:

```python
assert entries[0]["relevance"] == "direct"
assert fact["attention"]["relevance"] == "direct"
```

and:

```python
assert entries[0]["relevance"] == "inferred"
```

Add these cases:

```python
def test_direct_fact_survives_valid_ledger_without_score(tmp_path: Path) -> None:
    """An older sampled ledger cannot replace direct evidence with background."""

    log_dir = tmp_path / ".verify-logs"
    write_ledger(log_dir, "tests/test_other.py")
    write_ruff_manifest(log_dir, APP_PATH)

    pack = write_context_pack(ContextPackRequest(log_dir=log_dir, budget=8_000))
    attention = cast(dict[str, Any], pack.payload["attention"])
    entries = cast(list[dict[str, Any]], attention["entries"])

    assert entries[0]["path"] == APP_PATH
    assert entries[0]["score"] is None
    assert entries[0]["relevance"] == "direct"
    assert [entry["path"] for entry in entries] == [APP_PATH]


def test_explicitly_requested_file_is_direct_attention_context(tmp_path: Path) -> None:
    """Requested supporting files carry direct provenance."""

    log_dir = tmp_path / ".verify-logs"
    requested = tmp_path / OTHER_PATH
    requested.parent.mkdir(parents=True)
    requested.write_text("# Guide\n", encoding="utf-8")
    write_ledger(log_dir, APP_PATH)
    write_manifest(log_dir, "custom-check")
    write_log(log_dir, "custom-check", "failure without repository path\n")

    pack = write_context_pack(
        ContextPackRequest(
            log_dir=log_dir,
            budget=8_000,
            files=(requested,),
        )
    )
    attention = cast(dict[str, Any], pack.payload["attention"])
    entries = cast(list[dict[str, Any]], attention["entries"])

    assert entries[0]["path"] == OTHER_PATH
    assert entries[0]["relevance"] == "direct"


def test_background_fallback_has_no_tight_risk_notes(tmp_path: Path) -> None:
    """Unrelated top-ledger fallback never becomes a hook risk claim."""

    log_dir = tmp_path / ".verify-logs"
    write_ledger(log_dir, APP_PATH)
    write_manifest(log_dir, "custom-check")
    write_log(log_dir, "custom-check", "failure without repository path\n")

    pack = write_context_pack(ContextPackRequest(log_dir=log_dir, budget=8_000))
    attention = cast(dict[str, Any], pack.payload["attention"])
    entries = cast(list[dict[str, Any]], attention["entries"])

    assert entries[0]["relevance"] == "background"
    assert attention["risk_notes"] == []
    assert "Attention notes:" not in render_pack_pointer(
        pack.payload,
        display_path=str(pack.markdown_path),
    )
```

- [ ] **Step 2: Run tests to verify RED**

Run: `PYTHONPATH=src .venv/bin/pytest tests/attention/test_attention_context_pack.py -q`

Expected: FAIL because the context payload has no schema or relevance labels and
falls back to `OTHER_PATH` for the missing direct score.

- [ ] **Step 3: Implement provenance-aware selection**

In `context/pack/attention.py`, add:

```python
ATTENTION_CONTEXT_SCHEMA_VERSION = 1
DIRECT_RELEVANCE = "direct"
INFERRED_RELEVANCE = "inferred"
BACKGROUND_RELEVANCE = "background"


@dataclass(frozen=True)
class ContextAttentionEntry:
    path: str
    relevance: str
    ledger_score: AttentionFileScore | None
```

Include `schema_version` in every available and unavailable payload. Add a
keyword-only `requested_paths: Iterable[Path] = ()` argument to
`attention_payload`. Normalize requested paths by confining them to
`workspace_root`, converting them to repository-relative POSIX paths, and
omitting unsafe/outside paths without reading them.

Selection order is:

```python
direct_paths = _unique_paths((*_fact_paths(exact_facts), *_requested_paths(...)))
inferred_paths = tuple(path for path in _log_paths(...) if path not in direct_paths)
entries = _context_entries(by_path, direct_paths, relevance=DIRECT_RELEVANCE)
entries.extend(_context_entries(by_path, inferred_paths, relevance=INFERRED_RELEVANCE))
if not entries:
    entries = [
        ContextAttentionEntry(item.path, BACKGROUND_RELEVANCE, item)
        for item in ledger.files[:MAX_ATTENTION_ENTRIES]
    ]
```

`_context_entries` must create a direct entry even when `by_path` has no score;
inferred paths still require a ledger score. `_entry_payload` emits `score=None`,
empty components, and reason `direct context path has no sampled attention
score` for an unscored direct entry. It always emits `relevance`.

Generate risk notes only for non-background entries. For an unscored direct
entry, use the bounded note `<path> selected directly; no sampled attention
score`; otherwise preserve the current score/reason note.

- [ ] **Step 4: Thread explicitly requested files and render nullable scores**

Add `requested_paths: tuple[Path, ...] = ()` to
`repair_facts_with_attention`, pass it to `attention_payload`, and call it from
`build_context_pack` with `requested_paths=request.files`.

In `agent_context.attention_rendering._attention_entry_lines`, render `None` as
`unscored`:

```python
score = entry.get("score")
score_text = "unscored" if score is None else str(score)
lines.append(f"  - {score_text}: {path}")
```

Include `relevance` beside score/reasons in `attach_attention_to_facts`.

- [ ] **Step 5: Verify GREEN and commit**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest \
  tests/attention/test_attention_context_pack.py \
  tests/hooks/test_hook_output_invariants.py -q
```

Expected: PASS with bounded hook-pointer output and provenance-aware context
pack rendering.

```bash
git add -- \
  tests/attention/test_attention_context_pack.py \
  src/agent_maintainer/context/pack/attention.py \
  src/agent_maintainer/context/pack/builder.py \
  src/agent_context/attention_rendering.py
git commit -m "feat: label attention relevance"
```

### Task 4: Document the contract, close roadmap items, and run the broad gate

**Files:**

- Modify: `docs/tool-map.md`
- Modify: `docs/ROADMAP.md`
- Modify: `tests/docs/test_roadmap_docs.py`

**Interfaces:**

- Consumes: Tasks 1-3.
- Produces: public semantics for priority paths, nullable direct scores, and relevance labels.

- [ ] **Step 1: Update roadmap assertions before docs**

Change the governance roadmap test to require:

```python
assert "[x] Guarantee changed, failed, exact-fact" in text
assert "[x] Validate attention schema version" in text
```

Run: `PYTHONPATH=src .venv/bin/pytest tests/docs/test_roadmap_docs.py::test_active_roadmap_reports_current_strict_and_api_state -q`

Expected: FAIL while the attention checkboxes remain open.

- [ ] **Step 2: Document and close the attention items**

In `docs/tool-map.md`, document repeatable `--priority-path`, the 5,000-file
background budget, the 10,000-path hard discovery ceiling, required-path
overflow notes, relevance labels, and nullable score only for direct paths
missing from an older valid ledger. Check both attention roadmap items; do not
change Phase 176 or b6 publication state.

- [ ] **Step 3: Run focused architecture/type checks**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest tests/attention tests/docs/test_roadmap_docs.py tests/docs/test_markdown_links.py -q
PYTHONPATH=src .venv/bin/pyright
```

Expected: all tests PASS and Pyright reports zero errors.

- [ ] **Step 4: Commit docs and run full verification**

```bash
git add -- docs/tool-map.md docs/ROADMAP.md tests/docs/test_roadmap_docs.py
git commit -m "docs: close attention hardening roadmap"
just v
```

Expected: terminal full-profile PASS after reviewing the original run manifest.
