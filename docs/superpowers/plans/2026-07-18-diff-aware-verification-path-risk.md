# Diff-Aware Verification Planning And Path-Risk Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a provider-neutral `verify-plan` command and strict path-risk policy that map a Git diff to affected units, verifier requirements, named evidence, and review categories without suppressing existing gates.

**Architecture:** A new `agent_maintainer.verification_plan` domain owns policy models, segment-aware matching, affected-unit resolution, planning, reporting, and CLI behavior. It consumes a backward-compatible NUL-delimited change reader added to `ecosystems.git_changes`, existing ecosystem classifiers and setup evidence, and the configured verifier catalog. An optional catalog check enforces `.agent-maintainer/path-risk.toml` in normal profiles while `verify` remains the sole check executor.

**Tech Stack:** Python 3.11–3.14, standard-library `tomllib`, frozen dataclasses, `argparse`, Git name-status `-z`, pytest, Tach exact dependency contracts, DocSync.

## Global Constraints

- Policy schema version is exactly `1`.
- Default policy mode is `advisory`; only `required` rules can produce blocking findings.
- Missing required evidence exits `1` only when `--enforce` is present.
- Invalid arguments, policy, Git state, profile names, or check names exit `2`.
- The planner never executes checks and never suppresses an existing verifier gate.
- Rule matching considers rename/copy source and destination paths plus deleted source paths.
- `changed-path` evidence counts only paths present after the change.
- Glob matching is case-sensitive, segment-aware, and independent of `.gitignore`.
- No runtime dependency is added.
- All fixtures use synthetic repository data.
- Use `PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH` for repository commands until a fresh project environment is established.

---

### Task 1: Establish The Cohesive Change And Safe Policy Primitives

**Files:**
- Create: `.agent-maintainer/change-plans/diff-aware-verification-path-risk.md`
- Create: `src/agent_maintainer/core/repo_paths.py`
- Modify: `src/agent_maintainer/core/tach.domain.toml`
- Create: `src/agent_maintainer/verification_plan/__init__.py`
- Create: `src/agent_maintainer/verification_plan/models.py`
- Create: `src/agent_maintainer/verification_plan/matching.py`
- Create: `tests/verification_plan/__init__.py`
- Create: `tests/verification_plan/test_matching.py`
- Create: `tests/core/test_repo_paths.py`
- Modify: `docs/superpowers/specs/2026-07-18-diff-aware-verification-path-risk-design.md`

**Interfaces:**
- Produces: `EvidenceRequirement`, `PathRiskRule`, `PathRiskPolicy`, `AffectedUnit`, `RequirementResult`, `VerificationPlanReport` frozen dataclasses.
- Produces from `core.repo_paths`: `validate_repo_path(value: str, *, label: str) -> str` and `RepoPathError(ValueError)`.
- Produces from `matching`: `validate_repo_pattern(value: str, *, label: str) -> str`.
- Produces: `path_matches(pattern: str, path: str) -> bool`.
- Produces: `PathPatternError(ValueError)`.

- [ ] **Step 1: Create the active cohesive change plan**

Create a release-style active plan with `id = "diff-aware-verification-path-risk"`, `kind = "feature"`, `base_ref = "a119b0d"`, `requires_tests = true`, `requires_full_verify = true`, `max_changed_files = 40`, and `max_changed_lines = 3000`. Its allowed paths must enumerate the new domain, the neutral repository-path primitive, targeted Git/catalog/CLI/Tach files, `tests/verification_plan`, targeted existing tests, the policy, ADR, roadmap, README, tool map, subsystem stability table, DocSync trace/attestations, and this spec/plan. Include the required sections: Motivation, Scope, Verification plan, Risks, and Rollback.

Run:

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH python -m agent_maintainer change-plan check
```

Expected: `PASS change plans`.

- [ ] **Step 2: Write failing matcher tests**

Cover literal segments, `*`, `?`, `**` matching zero and multiple segments, case sensitivity, and rejection of leading `/`, leading `./`, backslashes, empty segments, `.`/`..`, NUL, and embedded `**`:

```python
import pytest

from agent_maintainer.verification_plan.matching import (
    PathPatternError,
    path_matches,
    validate_repo_pattern,
)


@pytest.mark.parametrize(
    ("pattern", "path", "expected"),
    (
        ("tach.toml", "tach.toml", True),
        ("src/*/tach.domain.toml", "src/api/tach.domain.toml", True),
        ("src/*/tach.domain.toml", "src/api/deep/tach.domain.toml", False),
        ("src/**/tach.domain.toml", "src/tach.domain.toml", True),
        ("src/**/tach.domain.toml", "src/api/deep/tach.domain.toml", True),
        ("src/?.py", "src/a.py", True),
        ("src/?.py", "src/ab.py", False),
        ("README.md", "readme.md", False),
    ),
)
def test_path_matches_segment_contract(pattern: str, path: str, expected: bool) -> None:
    assert path_matches(pattern, path) is expected


@pytest.mark.parametrize(
    "pattern",
    ("/root", "./src/**", "src\\**", "src//x", "src/./x", "src/../x", "src/**x", "src/\0x"),
)
def test_invalid_policy_patterns_fail_closed(pattern: str) -> None:
    with pytest.raises(PathPatternError):
        validate_repo_pattern(pattern, label="rules[0].paths[0]")
```

- [ ] **Step 3: Run the matcher tests and verify RED**

Run:

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/core/test_repo_paths.py tests/verification_plan/test_matching.py -q
```

Expected: collection fails because `agent_maintainer.verification_plan` does not exist.

- [ ] **Step 4: Implement immutable models and the segment matcher**

Use tuple-only collection fields in frozen dataclasses. Put concrete Git/repository path validation in `core.repo_paths`; policy-pattern validation and segment matching stay in `verification_plan.matching`. Implement matching by splitting validated values into segments and recursively matching `**`; compile ordinary segment patterns with `fnmatch.translate` only after rejecting separators and embedded `**`.

```python
def path_matches(pattern: str, path: str) -> bool:
    pattern_parts = validate_repo_pattern(pattern, label="pattern").split("/")
    path_parts = validate_repo_path(path, label="path").split("/")
    return _match_segments(tuple(pattern_parts), tuple(path_parts))


def _match_segments(patterns: tuple[str, ...], parts: tuple[str, ...]) -> bool:
    if not patterns:
        return not parts
    head, tail = patterns[0], patterns[1:]
    if head == "**":
        return _match_segments(tail, parts) or bool(parts) and _match_segments(patterns, parts[1:])
    return bool(parts) and _match_segment(head, parts[0]) and _match_segments(tail, parts[1:])
```

Models must carry the exact report contract from the design, including `schema_version`, current and old paths, affected units, matched rules, selected profiles/checks, requirements, commands, advisories, and blocking findings.

- [ ] **Step 5: Run focused tests and architecture checks**

Run:

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/core/test_repo_paths.py tests/verification_plan/test_matching.py -q
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH python -m agent_maintainer change-plan check
```

Expected: all matcher tests pass and change plans pass.

- [ ] **Step 6: Commit the primitives**

```bash
git add -- .agent-maintainer/change-plans/diff-aware-verification-path-risk.md docs/superpowers/specs/2026-07-18-diff-aware-verification-path-risk-design.md src/agent_maintainer/core/repo_paths.py src/agent_maintainer/core/tach.domain.toml src/agent_maintainer/verification_plan/__init__.py src/agent_maintainer/verification_plan/models.py src/agent_maintainer/verification_plan/matching.py tests/core/test_repo_paths.py tests/verification_plan/__init__.py tests/verification_plan/test_matching.py
git commit -m "feat: add verification policy primitives"
```

### Task 2: Add A Rename-Aware Neutral Git Change Reader

**Files:**
- Modify: `src/agent_maintainer/ecosystems/git_changes.py`
- Modify: `tests/ecosystems/test_git_changes.py`

**Interfaces:**
- Produces: `GitPathChange(path: str, kind: str, old_path: str | None = None)`.
- Produces: `GitPathChange.affected_paths() -> tuple[str, ...]`.
- Produces: `GitPathChange.evidence_paths() -> tuple[str, ...]`.
- Produces: `git_name_status_command(base_sha: str, *, staged: bool) -> list[str]`.
- Produces: `parse_name_status_z(output: bytes) -> tuple[GitPathChange, ...]`.
- Produces: `run_git_name_status(base_ref: str, *, staged: bool) -> tuple[GitPathChange, ...]`.
- Preserves: every existing numstat interface unchanged.

- [ ] **Step 1: Write failing parser and command tests**

Use byte payloads matching Git's `--name-status -z` contract:

```python
def test_name_status_z_preserves_rename_and_copy_identity() -> None:
    output = b"M\0src/a.py\0R100\0old.py\0new.py\0C090\0base.py\0copy.py\0D\0gone.py\0"

    assert git_changes.parse_name_status_z(output) == (
        git_changes.GitPathChange("src/a.py", "modified"),
        git_changes.GitPathChange("new.py", "renamed", old_path="old.py"),
        git_changes.GitPathChange("copy.py", "copied", old_path="base.py"),
        git_changes.GitPathChange("gone.py", "deleted"),
    )


def test_deleted_path_triggers_but_cannot_satisfy_evidence() -> None:
    change = git_changes.GitPathChange("security/policy.toml", "deleted")
    assert change.affected_paths() == ("security/policy.toml",)
    assert change.evidence_paths() == ()
```

Also cover add, binary files, malformed token counts, unknown status, invalid UTF-8, NUL/path validation, copy/rename scores, an option-shaped base ref, and a subprocess failure whose message includes the selected target.

- [ ] **Step 2: Run the Git adapter tests and verify RED**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/ecosystems/test_git_changes.py -q
```

Expected: failures show the new dataclass and parser are absent.

- [ ] **Step 3: Implement the NUL-delimited reader**

Resolve non-staged refs first with `git rev-parse --verify --end-of-options BASE_REF^{commit}`. Build the diff command only from the resolved hexadecimal SHA, without a shell, and terminate the revision list with `--`:

```python
def git_name_status_command(base_sha: str, *, staged: bool) -> list[str]:
    command = [
        "git",
        "diff",
        "--name-status",
        "-z",
        "-M",
        "-C",
        "--find-copies-harder",
    ]
    if staged:
        return [*command, "--cached", "--"]
    return [*command, f"{base_sha}...HEAD", "--"]
```

Parse status and path tokens from `output.split(b"\0")`, consuming two paths for `R`/`C` status tokens and one for `A`, `M`, `T`, `U`, and `D`. Decode with strict UTF-8, validate each repository-relative path through `core.repo_paths`, map statuses to stable words, and return deterministic input order.

- [ ] **Step 4: Run focused Git tests**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/ecosystems/test_git_changes.py tests/regression/test_phase10_error_paths.py -q
```

Expected: all tests pass and existing numstat behavior remains unchanged.

- [ ] **Step 5: Commit the neutral reader**

```bash
git add -- src/agent_maintainer/ecosystems/git_changes.py tests/ecosystems/test_git_changes.py
git commit -m "feat: read structured git path changes"
```

### Task 3: Load And Validate Strict Path-Risk Policy

**Files:**
- Create: `src/agent_maintainer/verification_plan/policy.py`
- Create: `tests/verification_plan/test_policy.py`

**Interfaces:**
- Consumes: policy dataclasses and matching validation from Task 1.
- Produces: `PolicyError(ValueError)`.
- Produces: `load_policy(path: Path) -> PathRiskPolicy | None`.
- Produces: `validate_catalog_names(policy: PathRiskPolicy, *, profiles: Collection[str], checks: Collection[str]) -> None`.

- [ ] **Step 1: Write failing valid-policy and rejection tests**

Create policies with `tmp_path` and assert exact immutable values. Rejection parameterization must cover missing/unsupported version, unknown keys at every table level, bad types, empty required arrays, duplicate rule IDs, duplicate evidence IDs within a rule, invalid modes, nonpositive `minimum`, unsafe globs, invalid review-category identifiers, unknown profiles/checks, and duplicate catalog check names.

```python
def test_load_policy_defaults_to_advisory(tmp_path: Path) -> None:
    policy_path = tmp_path / "path-risk.toml"
    policy_path.write_text(
        'version = 1\n[[rules]]\nid = "docs"\npaths = ["docs/**"]\n',
        encoding="utf-8",
    )

    policy = policy_loader.load_policy(policy_path)

    assert policy is not None
    assert policy.rules[0].mode == "advisory"
    assert policy.rules[0].evidence == ()
```

- [ ] **Step 2: Run policy tests and verify RED**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/verification_plan/test_policy.py -q
```

Expected: import failure because `policy.py` is absent.

- [ ] **Step 3: Implement strict TOML decoding**

Use `tomllib.loads(path.read_text(encoding="utf-8"))`. Validate allowed-key sets before coercion; accept no implicit scalar-to-list conversions. Normalize tuple ordering by preserving policy declaration order, while rejecting duplicates rather than deduplicating misspellings.

```python
def load_policy(path: Path) -> PathRiskPolicy | None:
    if not path.exists():
        return None
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise PolicyError(f"invalid path-risk policy {path}: {exc}") from exc
    return _decode_policy(path, raw)
```

Catalog validation must accept profiles from `VALID_PROFILES`, validate checks against one exact configured catalog name set, and fail closed when that catalog contains duplicate names.

- [ ] **Step 4: Run policy and matcher tests**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/verification_plan/test_policy.py tests/verification_plan/test_matching.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit the policy loader**

```bash
git add -- src/agent_maintainer/verification_plan/policy.py tests/verification_plan/test_policy.py
git commit -m "feat: load strict path-risk policy"
```

### Task 4: Resolve Provider-Neutral Affected Units

**Files:**
- Create: `src/agent_maintainer/verification_plan/units.py`
- Create: `tests/verification_plan/test_units.py`

**Interfaces:**
- Consumes: `MaintainerConfig`, structured Git changes, classifications, `PackageWorkspaceEvidence`, and bounded `RepoEvidence.java_module_paths`.
- Produces: `resolve_affected_units(repo_root: Path, *, config: MaintainerConfig, changes: Sequence[GitPathChange], package_workspace: PackageWorkspaceEvidence, java_module_paths: Sequence[str]) -> tuple[tuple[AffectedUnit, ...], tuple[str, ...]]`.
- Returns: sorted units plus advisories; ambiguity always falls back to repository ownership.

- [ ] **Step 1: Write failing unit-resolution tests**

Test Python longest segment-prefix matching (`src/app` must not own `src/application`), TypeScript literal workspace expansion with nested packages and required `package.json`, a 256-root cap, out-of-root symlink rejection, duplicate/overlapping roots, Java source-derived module roots, unmatched paths, deleted paths, and byte-stable ordering.

```python
def test_python_units_use_longest_segment_prefix(tmp_path: Path) -> None:
    config = MaintainerConfig(package_paths=("src/app", "src/application"))
    changes = (
        GitPathChange("src/app/api.py", "modified"),
        GitPathChange("src/application/main.py", "modified"),
    )

    units, advisories = resolve_affected_units(
        tmp_path,
        config=config,
        changes=changes,
        package_workspace=PackageWorkspaceEvidence(),
        java_module_paths=(),
    )

    assert [(unit.root, unit.changed_paths) for unit in units] == [
        ("src/app", ("src/app/api.py",)),
        ("src/application", ("src/application/main.py",)),
    ]
    assert advisories == ()
```

- [ ] **Step 2: Run unit tests and verify RED**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/verification_plan/test_units.py -q
```

Expected: import failure because `units.py` is absent.

- [ ] **Step 3: Implement bounded resolution**

Normalize roots with the policy path validator, use tuple-of-segments prefix checks, select the unique longest root, and emit an advisory plus repository fallback on equal-specificity ambiguity. Expand only literal TypeScript declarations, cap candidate roots at 256, require a confined real path and `package.json`, and never interpret executable Gradle settings DSL.

```python
def _is_prefix(root: str, path: str) -> bool:
    root_parts = tuple(root.split("/"))
    path_parts = tuple(path.split("/"))
    return path_parts[: len(root_parts)] == root_parts
```

The repository fallback unit is exactly `AffectedUnit(kind="repository", name="repository", root=".", ...)`.

- [ ] **Step 4: Run focused resolver tests**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/verification_plan/test_units.py tests/assess/test_package_workspace_evidence.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit affected-unit resolution**

```bash
git add -- src/agent_maintainer/verification_plan/units.py tests/verification_plan/test_units.py
git commit -m "feat: resolve affected repository units"
```

### Task 5: Build And Render Deterministic Verification Plans

**Files:**
- Create: `src/agent_maintainer/verification_plan/planner.py`
- Create: `src/agent_maintainer/verification_plan/reporting.py`
- Create: `tests/verification_plan/test_planner.py`
- Create: `tests/verification_plan/test_reporting.py`

**Interfaces:**
- Consumes: Tasks 1–4, configured `MaintainerConfig`, and `catalogs.catalog.make_checks`.
- Produces: `build_verification_plan(target: Path, *, base_ref: str, staged: bool, policy_path: Path) -> VerificationPlanReport`.
- Produces: `plan_from_facts(...) -> VerificationPlanReport` as a pure core for focused tests.
- Produces: `report_to_dict(report: VerificationPlanReport) -> dict[str, object]`.
- Produces: `render_json(report: VerificationPlanReport) -> str` and `render_text(report: VerificationPlanReport) -> str`.

- [ ] **Step 1: Write failing pure-planner tests**

Cover overlapping rules, stable unions, required dominating only its own missing evidence, rule-local evidence, `minimum > 1`, renamed/deleted triggers, destination-only evidence, generated/ignored matching, catalog validation, absent policy, and canonical commands.

```python
def test_required_missing_evidence_is_blocking_but_advisory_is_not() -> None:
    report = plan_from_facts(
        target=Path("/repo"),
        base_ref="origin/main",
        staged=False,
        changes=(GitPathChange("tach.toml", "modified"),),
        classifications=(),
        affected_units=(),
        unit_advisories=(),
        policy=policy_with_required_adr_and_advisory_docs(),
        catalog_checks=(check("tach"),),
    )

    assert report.blocking_findings == (
        "architecture-policy/architecture-decision: Add or update an architecture decision record.",
    )
    assert report.advisories == (
        "docs-guidance/docs-note: Update relevant documentation.",
    )
```

- [ ] **Step 2: Write failing rendering tests**

Assert exact schema keys, sorted lists, requirement fields, no timestamp, trailing newline, bounded text sections, and identical JSON for identical inputs:

```python
def test_json_is_byte_stable(report: VerificationPlanReport) -> None:
    first = render_json(report)
    second = render_json(report)
    assert first == second
    assert first.endswith("\n")
    assert json.loads(first)["schema_version"] == 1
```

- [ ] **Step 3: Run planner/reporting tests and verify RED**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/verification_plan/test_planner.py tests/verification_plan/test_reporting.py -q
```

Expected: import failures for missing planner/reporting modules.

- [ ] **Step 4: Implement pure planning then repository orchestration**

Match rules against `change.affected_paths()`, match evidence against the union of `change.evidence_paths()`, namespace requirements by `(rule_id, evidence_id)`, and sort output explicitly. Build the configured catalog once and reject duplicate names before validating policy references.

```python
def _recommended_commands(profiles: Iterable[str]) -> tuple[str, ...]:
    return tuple(
        f"python -m agent_maintainer verify --profile {profile}"
        for profile in sorted(set(profiles))
    )
```

The repository orchestrator loads config once, reads Git changes once, collects bounded evidence once, classifies every affected path, resolves units, builds the catalog once, validates policy names, and calls the pure planner.

- [ ] **Step 5: Implement stable rendering**

Use explicit dict construction rather than generic dataclass serialization so the public schema is intentional. Render JSON with `indent=2`, `sort_keys=True`, and one trailing newline. Text output must include Policy, Changed paths, Affected units, Requirements, Review categories, Recommended commands, Advisories, and Blocking findings/Ready sections.

- [ ] **Step 6: Run focused planning tests**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/verification_plan -q
```

Expected: all verification-plan tests pass.

- [ ] **Step 7: Commit planning and rendering**

```bash
git add -- src/agent_maintainer/verification_plan/planner.py src/agent_maintainer/verification_plan/reporting.py tests/verification_plan/test_planner.py tests/verification_plan/test_reporting.py
git commit -m "feat: build deterministic verification plans"
```

### Task 6: Expose The `verify-plan` CLI And Root Route

**Files:**
- Create: `src/agent_maintainer/verification_plan/cli.py`
- Modify: `src/agent_maintainer/cli.py`
- Create: `tests/verification_plan/test_cli.py`
- Modify: `tests/packaging/test_script_helpers.py`

**Interfaces:**
- Produces: `parse_args(argv: list[str]) -> argparse.Namespace`.
- Produces: `main(argv: list[str]) -> int` with exact `0/1/2` semantics.
- Produces: lazy root route `verify_plan_command(command_args: list[str]) -> int`.

- [ ] **Step 1: Write failing CLI tests**

Use synthetic Git repositories and monkeypatch only the orchestration seam where subprocess behavior is not under test. Cover text/JSON success, absent policy, `--staged`, custom policy, required missing evidence with and without `--enforce`, malformed policy, bad base ref, and root lazy dispatch.

```python
def test_enforcement_changes_only_exit_status(monkeypatch, capsys) -> None:
    report = report_with_blocking_finding()
    monkeypatch.setattr(cli, "build_verification_plan", lambda *args, **kwargs: report)

    assert cli.main(["--json"]) == 0
    first = capsys.readouterr().out
    assert cli.main(["--json", "--enforce"]) == 1
    second = capsys.readouterr().out
    assert first == second
```

- [ ] **Step 2: Run CLI tests and verify RED**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/verification_plan/test_cli.py tests/packaging/test_script_helpers.py -q
```

Expected: missing CLI module/route failures.

- [ ] **Step 3: Implement CLI and lazy dispatch**

Parse `--target`, `--base-ref`, `--staged`, `--policy`, `--json`, and `--enforce`. Catch only expected domain/Git/config errors, print a concise `FAIL verify-plan: ...` to stderr, and return `2`; do not catch programming errors.

Add `verify-plan` to the stable workflow/help text, `command_handlers()`, and a `@preflight.ValidatedCommand` route that calls `_run_module_main("agent_maintainer.verification_plan.cli", command_args)`.

- [ ] **Step 4: Run CLI and runtime-event tests**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/verification_plan/test_cli.py tests/packaging/test_script_helpers.py tests/runtime_events/test_command_runtime_events.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit the public command**

```bash
git add -- src/agent_maintainer/verification_plan/cli.py src/agent_maintainer/cli.py tests/verification_plan/test_cli.py tests/packaging/test_script_helpers.py
git commit -m "feat: expose verification planning command"
```

### Task 7: Integrate Tach, The Optional Catalog Gate, And Repository Policy

**Files:**
- Create: `src/agent_maintainer/verification_plan/tach.domain.toml`
- Modify: `src/agent_maintainer/ecosystems/tach.domain.toml`
- Modify: `src/agent_maintainer/catalogs/tach.domain.toml`
- Modify: `tach.toml`
- Modify: `src/agent_maintainer/catalogs/global_checks.py`
- Modify: `src/agent_maintainer/catalogs/catalog.py`
- Modify: `tests/catalogs/test_config_catalog.py`
- Create: `.agent-maintainer/path-risk.toml`
- Create: `docs/architecture/decisions/2026-07-18-diff-aware-verification-planning.md`

**Interfaces:**
- Produces: `verification_plan_check(base_ref: str, *, staged: bool) -> Check`.
- Adds: `verification-plan-policy` to `fast`, `precommit`, `full`, and `ci` via `ALL_PROFILES`.
- Adds: exact Tach dependencies for every implemented import.

- [ ] **Step 1: Write failing catalog tests**

Assert the exact check name, profiles, required policy path, optional skip metadata, base ref, staged flag, and command:

```python
def test_verification_plan_policy_check_is_optional_and_exact() -> None:
    check = by_name(make_checks(MaintainerConfig(), "origin/main", "main"))[
        "verification-plan-policy"
    ]
    assert check.profiles == ALL_PROFILES
    assert check.required_paths == (".agent-maintainer/path-risk.toml",)
    assert check.command == [
        sys.executable,
        "-m",
        "agent_maintainer",
        "verify-plan",
        "--base-ref",
        "origin/main",
        "--enforce",
    ]
```

Add a staged variant asserting `--staged` and no base-ref ambiguity.

- [ ] **Step 2: Run catalog tests and verify RED**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/catalogs/test_config_catalog.py -q
```

Expected: `verification-plan-policy` is absent.

- [ ] **Step 3: Implement the optional catalog check**

Construct one `Check` with `profiles=ALL_PROFILES`, `required_paths=(".agent-maintainer/path-risk.toml",)`, a clear optional skip reason/status, and the exact lazy CLI command. Add it once to `make_checks` without changing existing check order except for the new documented slot.

- [ ] **Step 4: Add the initial repository policy and ADR**

Add required rules for architecture policy (`tach.toml`, `src/**/tach.domain.toml`), dependency/lock surfaces, workflows, release/version surfaces, and security-policy files. Keep ordinary source rules advisory or absent. Every requirement must be satisfiable by this implementation diff and name exact existing profiles/checks.

The ADR records the additive planner boundary, strict versioned policy, destination-only evidence, no dynamic skipping, and why this domain is separate from reviewability and verify execution.

- [ ] **Step 5: Add exact Tach contracts and run focused gates**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH tach check --exact
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH python -m archguard decision-check
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/catalogs/test_config_catalog.py tests/verification_plan -q
```

Expected: all commands pass and the repository's own current diff satisfies its required policy evidence.

- [ ] **Step 6: Commit architecture and enforcement integration**

```bash
git add -- .agent-maintainer/path-risk.toml docs/architecture/decisions/2026-07-18-diff-aware-verification-planning.md src/agent_maintainer/verification_plan/tach.domain.toml src/agent_maintainer/ecosystems/tach.domain.toml src/agent_maintainer/catalogs/tach.domain.toml tach.toml src/agent_maintainer/catalogs/global_checks.py src/agent_maintainer/catalogs/catalog.py tests/catalogs/test_config_catalog.py
git commit -m "feat: enforce declarative path-risk policy"
```

### Task 8: Document Phase 183 And The Public Contract

**Files:**
- Modify: `README.md`
- Modify: `docs/tool-map.md`
- Modify: `docs/architecture/subsystem-stability.md`
- Modify: `docs/ROADMAP.md`
- Create: `docs/roadmap/phases/phase-183-diff-aware-verification-planning.md`
- Modify: `.docsync/trace.yml`
- Create: `.docsync/attestations/attest.<timestamp>.claim.<claim>.<sha>.yml` through DocSync tooling
- Modify: `tests/packaging/test_public_docs.py`

**Interfaces:**
- Documents: command syntax, exit codes, policy schema, JSON schema version, examples, additive/non-suppression boundary, and Phase 183 promotion evidence.
- Labels: `agent-maintainer verify-plan` exactly once in subsystem stability.

- [ ] **Step 1: Write failing public-documentation assertions**

Extend public docs tests to require the command, default policy path, `schema_version = 1`, `--enforce` semantics, and the phrase that existing verifier gates are never suppressed.

```python
def test_verify_plan_public_contract_is_documented() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    assert "agent-maintainer verify-plan" in readme
    assert ".agent-maintainer/path-risk.toml" in readme
    assert "--enforce" in readme
    assert "never suppresses existing verifier gates" in readme
```

- [ ] **Step 2: Run docs tests and verify RED**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/packaging/test_public_docs.py -q
```

Expected: missing public contract/stability row failures.

- [ ] **Step 3: Update README, tool map, stability table, roadmap, and phase record**

README must show one advisory planning command and one enforced command. The phase record must list exact files, test commands, the real full verification run ID after it exists, and final protected PR evidence before completion. Do not claim dynamic verification minimization.

Record local evidence only after it exists; before that, describe the required evidence generically without invented IDs.

- [ ] **Step 4: Add DocSync trace claims and attest through the supported command**

Add claims for the README command/behavior and policy schema, then run the repository's existing DocSync attestation workflow against immutable committed evidence. Do not hand-edit generated output or attestation bodies.

- [ ] **Step 5: Run documentation checks**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/packaging/test_public_docs.py tests/docsync/test_public_doc_trace.py -q
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH python -m docsync check
```

Expected: all tests and DocSync pass.

- [ ] **Step 6: Commit public documentation**

```bash
git add -- README.md docs/tool-map.md docs/architecture/subsystem-stability.md docs/ROADMAP.md docs/roadmap/phases/phase-183-diff-aware-verification-planning.md .docsync/trace.yml .docsync/attestations tests/packaging/test_public_docs.py
git commit -m "docs: publish verification planning contract"
```

### Task 9: Complete Verification, Review, And Evidence

**Files:**
- Modify only files allowed by the active change plan when verification reveals a defect.
- Modify: `docs/roadmap/phases/phase-183-diff-aware-verification-planning.md` only to record real immutable verification evidence.

**Interfaces:**
- Produces: clean focused, architecture, documentation, full, manual, and security evidence.
- Produces: one comprehensive independent review with no unresolved important findings.

- [ ] **Step 1: Run the focused feature matrix**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH pytest tests/verification_plan tests/ecosystems/test_git_changes.py tests/catalogs/test_config_catalog.py tests/packaging/test_script_helpers.py tests/packaging/test_public_docs.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run architecture and documentation gates**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH tach check --exact
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH python -m archguard decision-check
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH python -m docsync check
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH python -m agent_maintainer change-plan check
```

Expected: every command passes.

- [ ] **Step 3: Exercise the public command against synthetic and repository diffs**

Run text and JSON advisory plans, an enforced satisfied plan, and a synthetic missing-evidence plan. Confirm exact exit statuses `0`, `0`, `0`, and `1`; confirm invalid policy exits `2` without a traceback.

- [ ] **Step 4: Run the full repository gate**

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT=1 just v
```

Expected: `Result: PASS` with a durable full run ID.

- [ ] **Step 5: Run manual and security profiles when required by the repository policy**

Use the repository's named tasks or verifier profiles, preserving their durable run IDs. Do not bypass unavailable required tooling; repair the environment or report a real blocker.

- [ ] **Step 6: Request one comprehensive independent review**

Review the full diff against the design, focusing on path confinement, rename/delete semantics, deterministic output, policy fail-closed behavior, catalog recursion, Tach edges, and accidental gate suppression. Fix every important finding test-first, rerun the smallest affected gates, then rerun full verification once.

- [ ] **Step 7: Record real evidence and commit only if documentation changed**

```bash
git add -- docs/roadmap/phases/phase-183-diff-aware-verification-planning.md
git commit -m "docs: record verification planner evidence"
```

Skip this commit when the phase record already contains the final immutable evidence through an earlier commit.

### Task 10: Publish Through Protected PR And Close The Change Plan

**Files:**
- Modify after the implementation PR merges: `.agent-maintainer/change-plans/diff-aware-verification-path-risk.md`

**Interfaces:**
- Produces: protected implementation PR merged to `main`.
- Produces: follow-up protected plan-closure PR merged to `main`.

- [ ] **Step 1: Perform the final local audit**

Check `git status --short --branch`, `git diff --stat origin/main...HEAD`, the actual diff, staged state, and secret/private-data exposure. Confirm only intended files changed and the worktree is clean.

- [ ] **Step 2: Push and create the implementation PR**

Use a conventional PR title such as `feat: add diff-aware verification planning`. Include exact local run IDs and the self-policy result in the body.

- [ ] **Step 3: Wait for all protected checks and merge**

Use the repository PR waiter. Merge only after every protected check passes. Verify the exact merge commit on `origin/main`; do not amend, rebase, squash, or force-push.

- [ ] **Step 4: Create a fresh closure branch from merged `origin/main`**

Change only the active plan's status from `active` to `complete`, run:

```bash
PATH=/private/tmp/agent-maintainer-b8-release-venv/bin:$PATH python -m agent_maintainer change-plan check
```

Expected: `PASS change plans`.

- [ ] **Step 5: Commit, push, protect, and merge the closure PR**

```bash
git add -- .agent-maintainer/change-plans/diff-aware-verification-path-risk.md
git commit -m "chore: complete verification planner change plan"
```

Push the closure branch, create the PR, wait for all protected checks, merge, and verify final `origin/main` state.
