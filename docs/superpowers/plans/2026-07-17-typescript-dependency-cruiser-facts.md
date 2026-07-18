# TypeScript Dependency-Cruiser Facts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit TypeScript dependency-cruiser checks and turn documented cruise-result JSON violations into bounded, path-safe repair facts and compact summaries.

**Architecture:** The experimental TypeScript provider owns exact root and workspace command registration. A dedicated `agent_repair_facts` parser owns dependency-cruiser's `summary.violations` contract, validation, path safety, deterministic ordering, and bounds. The exact-fact registry and TypeScript structured summarizer consume that same parser; public compatibility projections replay offline.

**Tech Stack:** Python 3.11+, dataclasses, JSON, pathlib, pytest, Ruff, Wemake/flake8, Pyright, Tach, Archguard, DocSync, Markdownlint, dependency-cruiser cruise-result JSON.

## Global Constraints

- Preserve opt-in behavior: `enable_typescript` and an explicit command remain required.
- Add no dependency-cruiser dependency, command inference, reporter mutation, configuration generation, thresholds, baselines, or autofix.
- Preserve the configured process exit status through the existing check runner.
- Use root and workspace check names `typescript-dependency-cruiser[:workspace]`.
- Default `typescript_dependency_cruiser_profiles` to exactly `("full", "ci")`.
- Parse only `summary.violations`; do not walk modules, folders, cycles, via paths, metrics, environment, or rule-set graphs.
- Support severities `error`, `warn`, and `info`; ignore `ignore` and unknown severities.
- Support types `dependency`, `module`, `reachability`, `cycle`, `instability`, and `folder`.
- Sort before retaining at most 500 findings.
- Cap scalars at 200 characters, targetable paths at 500 characters, messages at 1,000 characters, compact summaries at 50 total lines, and context facts at 5 per failed check.
- Never target absolute, traversal, drive-qualified, control-bearing, dot, empty, or overlong source paths.
- Keep TypeScript/JavaScript experimental and dependency-cruiser advisory.
- Use synthetic fixtures as the authoritative schema contract and two pinned public projections only as compatibility evidence.
- Base the draft PR on `codex/typescript-osv-facts` until Phase 180 PR #399 lands.

---

### Task 1: Register explicit root and workspace checks

**Files:**

- Modify: `src/agent_maintainer/config/schema.py`
- Modify: `src/agent_maintainer/config/schema_fields.py`
- Modify: `src/agent_maintainer/config/registry.py`
- Modify: `src/agent_maintainer/config/workspaces.py`
- Modify: `src/agent_maintainer/ecosystems/registry.py`
- Modify: `src/agent_maintainer/ecosystems/typescript/provider.py`
- Test: `tests/config/test_typescript_config.py`
- Test: `tests/config/test_workspace_config.py`
- Test: `tests/catalogs/test_typescript_catalog.py`
- Test: `tests/catalogs/test_global_catalog_characterization.py`
- Test: `tests/catalogs/test_provider_registry.py`
- Test: `tests/catalogs/test_java_catalog.py`

**Interfaces:**

- Consumes: existing `MaintainerConfig`, `WorkspaceConfig`, `ProviderCommandSpec`, `_configured_check`, and provider catalog aggregation.
- Produces: `typescript_dependency_cruiser_command`, `typescript_dependency_cruiser_profiles`, workspace command ownership, and stable check names.

- [ ] **Step 1: Write failing root configuration tests**

Add this input and assertions beside the Knip contract in `tests/config/test_typescript_config.py`:

```python
"typescript_dependency_cruiser_command": [
    "pnpm",
    "exec",
    "depcruise",
    "--output-type",
    "json",
    "src",
],
"typescript_dependency_cruiser_profiles": ["full", "ci"],
```

```python
assert loaded.typescript_dependency_cruiser_command == (
    "pnpm",
    "exec",
    "depcruise",
    "--output-type",
    "json",
    "src",
)
assert loaded.typescript_dependency_cruiser_profiles == ("full", "ci")
```

Add a default test:

```python
def test_typescript_dependency_cruiser_defaults_to_full_and_ci_profiles() -> None:
    loaded = MaintainerConfig()

    assert loaded.typescript_dependency_cruiser_command == ()
    assert loaded.typescript_dependency_cruiser_profiles == ("full", "ci")
```

Run:

```bash
PATH=.venv/bin:$PATH pytest tests/config/test_typescript_config.py -q
```

Expected: FAIL because the two configuration attributes are absent.

- [ ] **Step 2: Add root schema and coercion fields**

Add to `src/agent_maintainer/config/schema.py`:

```python
DEFAULT_TYPESCRIPT_DEPENDENCY_CRUISER_PROFILES = ("full", "ci")
```

```python
typescript_dependency_cruiser_command: tuple[str, ...] = ()
typescript_dependency_cruiser_profiles: tuple[str, ...] = (
    DEFAULT_TYPESCRIPT_DEPENDENCY_CRUISER_PROFILES
)
```

Add both names beside the existing TypeScript command/profile fields in
`src/agent_maintainer/config/schema_fields.py`. Add the command name to the
TypeScript command tuple in `src/agent_maintainer/config/registry.py`; the
profile name follows the existing schema-field coercion path.

Run the root configuration test again. Expected: PASS.

- [ ] **Step 3: Write failing workspace configuration tests**

Add this workspace field in both TOML and mapping fixtures in
`tests/config/test_workspace_config.py`:

```toml
typescript_dependency_cruiser_command = [
  "pnpm",
  "--filter",
  "api",
  "exec",
  "depcruise",
  "--output-type",
  "json",
  "src",
]
```

Assert the exact tuple:

```python
typescript_dependency_cruiser_command=(
    "pnpm",
    "--filter",
    "api",
    "exec",
    "depcruise",
    "--output-type",
    "json",
    "src",
),
```

Run:

```bash
PATH=.venv/bin:$PATH pytest tests/config/test_workspace_config.py -q
```

Expected: FAIL because `WorkspaceConfig` does not own the command.

- [ ] **Step 4: Add workspace command ownership**

Add to `WorkspaceConfig` in `src/agent_maintainer/config/workspaces.py`:

```python
typescript_dependency_cruiser_command: tuple[str, ...] = ()
```

Add the same key to the workspace command-key registry used by nested-table
coercion. Run the workspace test again. Expected: PASS.

- [ ] **Step 5: Write failing provider and catalog tests**

Extend `tests/catalogs/test_typescript_catalog.py` with exact root assertions:

```python
assert by_name["typescript-dependency-cruiser"].command == [
    "pnpm",
    "exec",
    "depcruise",
    "--output-type",
    "json",
    "src",
]
assert by_name["typescript-dependency-cruiser"].profiles == frozenset(
    ("full", "ci")
)
```

Add a configured workspace command and assert:

```python
assert checks["typescript-dependency-cruiser:api"].command == [
    "pnpm",
    "--filter",
    "api",
    "exec",
    "depcruise",
    "--output-type",
    "json",
    "src",
]
```

Update exact provider/global/Java ordering expectations to place the new check
after `typescript-knip` and before `actionlint` or Java checks. Require the
TypeScript provider metadata to expose `architecture` and the new command key.

Run:

```bash
PATH=.venv/bin:$PATH pytest tests/catalogs/test_typescript_catalog.py tests/catalogs/test_global_catalog_characterization.py tests/catalogs/test_provider_registry.py tests/catalogs/test_java_catalog.py -q
```

Expected: FAIL because the provider does not register the check.

- [ ] **Step 6: Register root, workspace, and provider metadata**

Add to the root checks list in `TypeScriptProvider.checks`:

```python
_configured_check(
    "typescript-dependency-cruiser",
    config.typescript_dependency_cruiser_command,
    config.typescript_dependency_cruiser_profiles,
    "typescript_dependency_cruiser_command",
),
```

Add this workspace specification:

```python
(
    "typescript-dependency-cruiser",
    workspace.typescript_dependency_cruiser_command,
    config.typescript_dependency_cruiser_profiles,
    (
        f"workspaces.{workspace.name}."
        "typescript_dependency_cruiser_command"
    ),
),
```

Add the metadata command spec and capability in
`src/agent_maintainer/ecosystems/registry.py`:

```python
"architecture",
```

```python
ProviderCommandSpec(
    "typescript-dependency-cruiser",
    "typescript_dependency_cruiser_command",
),
```

Run all Task 1 tests. Expected: PASS.

- [ ] **Step 7: Commit the provider slice**

```bash
git add -- src/agent_maintainer/config/schema.py src/agent_maintainer/config/schema_fields.py src/agent_maintainer/config/registry.py src/agent_maintainer/config/workspaces.py src/agent_maintainer/ecosystems/registry.py src/agent_maintainer/ecosystems/typescript/provider.py tests/config/test_typescript_config.py tests/config/test_workspace_config.py tests/catalogs/test_typescript_catalog.py tests/catalogs/test_global_catalog_characterization.py tests/catalogs/test_provider_registry.py tests/catalogs/test_java_catalog.py
git commit -m "feat: register TypeScript dependency-cruiser checks"
```

### Task 2: Parse bounded facts and compact summaries

**Files:**

- Create: `src/agent_repair_facts/parsers/typescript_dependency_cruiser.py`
- Modify: `src/agent_repair_facts/parsers/typescript_checks.py`
- Modify: `src/agent_repair_facts/registry.py`
- Modify: `src/agent_repair_facts/tach.domain.toml`
- Modify: `src/agent_maintainer/core/structured_typescript.py`
- Modify: `src/agent_maintainer/core/tach.domain.toml`
- Create: `docs/architecture/decisions/2026-07-17-typescript-dependency-cruiser-parser-boundary.md`
- Create: `tests/fixtures/typescript_dependency_cruiser/supported-violations.json`
- Test: `tests/repair_facts/test_typescript_dependency_cruiser_facts.py`
- Test: `tests/core/test_typescript_dependency_cruiser_structured_output.py`
- Test: `tests/context/test_typescript_exact_facts.py`

**Interfaces:**

- Consumes: `FactSource`, `json_object`, `json_array`, `fact_payload`, `check_family`, and structured TypeScript summary routing.
- Produces: `DependencyCruiserFinding`, `DependencyCruiserParseResult`, `parse_dependency_cruiser_json_result`, `format_dependency_cruiser_finding`, and `dependency_cruiser_facts`.

- [ ] **Step 1: Add the authoritative synthetic fixture**

Create a valid cruise-result fixture containing deliberately unsorted error,
warn, and info violations for all six supported types. Include malformed
neighbors, `ignore`, unknown severity/type, valid `unresolvedTo`, absolute,
traversal, drive-qualified, control-bearing, dot, and empty sources. Keep
`modules` as an empty array because only summary violations are parsed.

- [ ] **Step 2: Write failing parser tests**

Define the expected public registry contract:

```python
facts = registry.log_facts_from_text(
    "typescript-dependency-cruiser:web",
    Path("typescript-dependency-cruiser.log"),
    fixture.read_text(encoding="utf-8"),
)

assert facts[0] == {
    "check": "typescript-dependency-cruiser:web",
    "path": "src/api/client.ts",
    "line": None,
    "column": None,
    "symbol": "api-not-to-db",
    "message": (
        "src/api/client.ts -> src/db/private.ts: "
        "api-not-to-db [error; dependency]"
    ),
    "severity": "error",
}
```

Add parameterized tests for malformed JSON/root/summary/violations/rules,
neighbor isolation, supported severities/types, `unresolvedTo`, deterministic
sorting, 500 findings, 200-character scalars, all unsafe-path classes, and the
1,000-character message cap.

Run:

```bash
PATH=.venv/bin:$PATH pytest tests/repair_facts/test_typescript_dependency_cruiser_facts.py -q
```

Expected: FAIL because the parser and registry entry do not exist.

- [ ] **Step 3: Implement the dedicated parser**

Create typed immutable domain objects:

```python
DEPENDENCY_CRUISER_FACT_LIMIT = 500
DEPENDENCY_CRUISER_FIELD_CHAR_LIMIT = 200
DEPENDENCY_CRUISER_PATH_CHAR_LIMIT = 500
DEPENDENCY_CRUISER_MESSAGE_CHAR_LIMIT = 1_000

SUPPORTED_SEVERITIES = frozenset(("error", "warn", "info"))
SUPPORTED_TYPES = frozenset(
    ("dependency", "module", "reachability", "cycle", "instability", "folder")
)

@dataclass(frozen=True)
class DependencyCruiserFinding:
    source_path: str | None
    source_label: str
    target_label: str
    rule: str
    severity: str
    violation_type: str | None

@dataclass(frozen=True)
class DependencyCruiserParseResult:
    findings: tuple[DependencyCruiserFinding, ...]
    supported_count: int
    valid: bool
```

Implement `parse_dependency_cruiser_json_result(raw_output: str)` by decoding
once, requiring object `summary` and array `violations`, parsing each neighbor
independently, sorting by `(source_label, target_label, rule, severity,
violation_type or "")`, and slicing only after the supported count is known.

Implement a local `_safe_path(value, unknown_label)` helper with
`PurePosixPath` and `PureWindowsPath`. Replace controls with spaces, collapse
whitespace, reject all targetability cases in the global constraints, and
return a safe basename display label for rejected paths.

Implement formatting and exact facts:

```python
def format_dependency_cruiser_finding(
    finding: DependencyCruiserFinding,
) -> str:
    details = finding.severity
    if finding.violation_type:
        details = f"{details}; {finding.violation_type}"
    message = (
        f"{finding.source_label} -> {finding.target_label}: "
        f"{finding.rule} [{details}]"
    )
    if len(message) <= DEPENDENCY_CRUISER_MESSAGE_CHAR_LIMIT:
        return message
    return f"{message[: DEPENDENCY_CRUISER_MESSAGE_CHAR_LIMIT - 3].rstrip()}..."

def dependency_cruiser_facts(
    path: FactSource,
    check: str,
) -> list[dict[str, object]]:
    try:
        raw_output = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    result = parse_dependency_cruiser_json_result(raw_output)
    return [
        fact_payload(
            {
                "check": check,
                "path": finding.source_path,
                "symbol": finding.rule,
                "message": format_dependency_cruiser_finding(finding),
                "severity": finding.severity,
            }
        )
        for finding in result.findings
    ]
```

Run the parser tests. Expected: PASS.

- [ ] **Step 4: Register the check family and facts**

Add `typescript-dependency-cruiser` to `TYPESCRIPT_CHECK_FAMILIES`. Import the
new parser in `src/agent_repair_facts/registry.py` and add:

```python
("typescript-dependency-cruiser", dependency_cruiser_facts),
```

The existing family normalizer must preserve workspace suffixes in the emitted
fact while selecting the root parser family. Run parser tests again. Expected:
PASS for root and workspace names.

- [ ] **Step 5: Write failing summary and context tests**

Add summary assertions:

```python
summary = structured_typescript.summarize_typescript_check(
    "typescript-dependency-cruiser:web",
    raw_output,
)
assert summary == (
    "src/api/client.ts -> src/db/private.ts: "
    "api-not-to-db [error; dependency]"
)
```

Add exact tests for 50 total lines with a truthful omission marker based on
the pre-slice supported count, invalid-output fallback to `None`, and 600 input
violations producing `49` visible lines plus one marker.

Extend `tests/context/test_typescript_exact_facts.py` with six valid violations
and assert exactly five retained facts for the workspace-suffixed check.

Run:

```bash
PATH=.venv/bin:$PATH pytest tests/core/test_typescript_dependency_cruiser_structured_output.py tests/context/test_typescript_exact_facts.py -q
```

Expected: FAIL because structured routing does not know the new family.

- [ ] **Step 6: Implement the shared compact summary**

Add:

```python
DEPENDENCY_CRUISER_SUMMARY_LINE_LIMIT = 50

def summarize_typescript_dependency_cruiser(raw_output: str) -> str | None:
    parse_result = (
        typescript_dependency_cruiser.parse_dependency_cruiser_json_result(
            raw_output
        )
    )
    findings = parse_result.findings
    if not findings:
        return None
    visible_limit = DEPENDENCY_CRUISER_SUMMARY_LINE_LIMIT
    if parse_result.supported_count > visible_limit:
        visible_limit -= 1
    visible = findings[:visible_limit]
    lines = [
        typescript_dependency_cruiser.format_dependency_cruiser_finding(finding)
        for finding in visible
    ]
    omitted = parse_result.supported_count - len(visible)
    if omitted:
        lines.append(
            f"... {omitted} more dependency-cruiser findings omitted. "
            "See .verify-logs/"
        )
    return "\n".join(lines)
```

Route `typescript-dependency-cruiser` through this function in
`summarize_typescript_check`. Run summary and context tests. Expected: PASS.

- [ ] **Step 7: Preserve Tach ownership and document the boundary**

Add the new parser module to `src/agent_repair_facts/tach.domain.toml`. Permit
`agent_maintainer.core.structured_typescript` to import that parser through the
existing repair-facts dependency direction in
`src/agent_maintainer/core/tach.domain.toml`.

Create the ADR with these exact decisions: parser normalization belongs to
`agent_repair_facts`; core rendering imports inward; the provider owns command
execution only; no TypeScript code imports core orchestration; Tach, Archguard,
Nx, and dependency-cruiser remain separate policy surfaces.

Run:

```bash
PATH=.venv/bin:$PATH tach check --exact
PATH=.venv/bin:$PATH python -m archguard decision-check
```

Expected: PASS.

- [ ] **Step 8: Commit the facts slice**

```bash
git add -- src/agent_repair_facts/parsers/typescript_dependency_cruiser.py src/agent_repair_facts/parsers/typescript_checks.py src/agent_repair_facts/registry.py src/agent_repair_facts/tach.domain.toml src/agent_maintainer/core/structured_typescript.py src/agent_maintainer/core/tach.domain.toml docs/architecture/decisions/2026-07-17-typescript-dependency-cruiser-parser-boundary.md tests/fixtures/typescript_dependency_cruiser/supported-violations.json tests/repair_facts/test_typescript_dependency_cruiser_facts.py tests/core/test_typescript_dependency_cruiser_structured_output.py tests/context/test_typescript_exact_facts.py
git commit -m "feat: parse TypeScript architecture facts"
```

### Task 3: Record public evidence and complete Phase 181 documentation

**Files:**

- Create: `tests/fixtures/typescript_dependency_cruiser_external/npm-project.json`
- Create: `tests/fixtures/typescript_dependency_cruiser_external/pnpm-workspace.json`
- Create: `tests/assess/test_depcruise_external_fixtures.py`
- Create: `docs/roadmap/phases/phase-181-typescript-dependency-cruiser-facts.md`
- Modify: `docs/roadmap/typescript-react-parity-roadmap.md`
- Modify: `docs/roadmap/full-roadmap-blueprint.md`
- Modify: `docs/provider-status.md`
- Modify: `docs/typescript-javascript-provider.md`
- Modify: `docs/tool-map.md`
- Modify: `docs/supported-scans-and-agent-use.md`
- Modify: `docs/configuration-reference.md`
- Modify: `.docsync/trace.yml`
- Modify: `tests/docs/test_first_touch_docs.py`
- Modify: `tests/docs/test_roadmap_docs.py`
- Modify: `tests/docsync/test_public_doc_trace.py`

**Interfaces:**

- Consumes: the Task 2 parser and bounded projection format.
- Produces: two offline replay fixtures, public configuration/output guidance, Phase 181 closure, and current DocSync attestations.

- [ ] **Step 1: Write failing external-fixture contract tests**

For both projections assert:

```python
assert fixture["source_repository"].startswith("https://github.com/")
assert len(fixture["commit"]) == 40
assert fixture["collected_at"].endswith("Z")
assert fixture["tool"]["name"] == "dependency-cruiser"
assert fixture["tool"]["version"]
assert fixture["command"][-2:] == ["json", "src"]
assert fixture["exit_code"] >= 0
assert fixture["supported_finding_count"] >= fixture["retained_finding_count"]
assert fixture["retained_finding_count"] <= 25
assert fixture["config_sha256"]
assert fixture["lockfile_sha256"]
assert "/Users/" not in json.dumps(fixture)
```

Reconstruct a minimal cruise-result from each projection's retained violations,
parse it through `parse_dependency_cruiser_json_result`, and assert the parser's
supported and retained counts match projection metadata.

Run:

```bash
PATH=.venv/bin:$PATH pytest tests/assess/test_depcruise_external_fixtures.py -q
```

Expected: FAIL because the projection files do not exist.

- [ ] **Step 2: Capture two pinned public repositories once**

Select one npm/package-lock repository and one pnpm workspace with TypeScript
sources and a reviewable dependency-cruiser configuration. Record the exact
commit before execution. Use a task-specific temporary directory and a pinned
dependency-cruiser release. Never run package scripts. If dependency
installation is required for resolution, use the lockfile command with
lifecycle scripts disabled.

Run the exact repository-owned JSON command or a reviewed temporary config.
Retain at most 25 parser-normalized violations. Store raw clones, dependencies,
and reports only under the temporary directory. Run the offline fixture tests.
Expected: PASS.

- [ ] **Step 3: Write failing docs and DocSync tests**

Require public docs to contain:

```text
typescript_dependency_cruiser_command
typescript_dependency_cruiser_profiles
typescript-dependency-cruiser
summary.violations
500 normalized findings
50 total lines
dependency-cruiser is the TypeScript/JavaScript architecture-boundary counterpart
```

Require Phase 181 to be complete, to name both public repositories, to keep the
provider experimental, and to name package-manager audit facts next. Add
DocSync evidence IDs for configuration registration, parser facts, summaries,
and external fixtures.

Run:

```bash
PATH=.venv/bin:$PATH pytest tests/docs/test_first_touch_docs.py tests/docs/test_roadmap_docs.py tests/docsync/test_public_doc_trace.py -q
```

Expected: FAIL because public docs and trace claims are not current.

- [ ] **Step 4: Update generated configuration reference and public docs**

Run the repository generator after schema changes:

```bash
PATH=.venv/bin:$PATH just config-reference
```

Update the listed docs with the exact command/profile, output contract, safety
bounds, pinned evidence, advisory maturity, deliberate Phase 181 sequencing,
stacked PR dependency, and next package-manager audit slice. Add Phase 181 to
the full roadmap blueprint.

Update `.docsync/trace.yml` only as human-authored source truth. Refresh the
review and repair-facts claim with exact evidence IDs:

```bash
PATH=.venv/bin:$PATH python -m docsync review --base HEAD
PATH=.venv/bin:$PATH python -m docsync attest claim.docs.typescript_provider_repair_facts --evidence evidence.typescript.dependency_cruiser_config_tests --evidence evidence.typescript.dependency_cruiser_fact_tests --evidence evidence.typescript.dependency_cruiser_summary_tests --evidence evidence.typescript.dependency_cruiser_external_fixtures --reason "Reviewed Phase 181 explicit dependency-cruiser commands, bounded path-safe architecture facts and summaries, and pinned public compatibility evidence; the TypeScript provider repair-fact documentation is accurate."
PATH=.venv/bin:$PATH python -m docsync check
```

Do not edit `.docsync/out/`.

- [ ] **Step 5: Run the complete focused phase suite**

```bash
PATH=.venv/bin:$PATH pytest tests/config/test_typescript_config.py tests/config/test_workspace_config.py tests/catalogs/test_typescript_catalog.py tests/catalogs/test_global_catalog_characterization.py tests/catalogs/test_provider_registry.py tests/catalogs/test_java_catalog.py tests/repair_facts/test_typescript_dependency_cruiser_facts.py tests/core/test_typescript_dependency_cruiser_structured_output.py tests/context/test_typescript_exact_facts.py tests/assess/test_depcruise_external_fixtures.py tests/docs/test_first_touch_docs.py tests/docs/test_roadmap_docs.py tests/docsync/test_public_doc_trace.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit evidence and documentation**

Stage only the two bounded projections, their test, human-authored docs/trace,
generated configuration reference, tests, and current attestations:

```bash
git commit -m "docs: complete TypeScript architecture facts phase"
```

### Task 4: Independent review, full verification, and publication

**Files:**

- Review: all files changed from `codex/typescript-osv-facts...HEAD`
- Modify only when review or verification finds a demonstrated defect.

**Interfaces:**

- Consumes: Tasks 1–3 and repository verification profiles.
- Produces: reviewed commits, clean status, pushed branch, and a stacked draft PR.

- [ ] **Step 1: Run targeted static and architecture gates**

```bash
PATH=.venv/bin:$PATH ruff check src tests
PATH=.venv/bin:$PATH flake8 src tests
PATH=.venv/bin:$PATH pyright
PATH=.venv/bin:$PATH tach check --exact
PATH=.venv/bin:$PATH python -m archguard decision-check
PATH=.venv/bin:$PATH python -m docsync check
./node_modules/.bin/markdownlint-cli2 "docs/**/*.md"
```

Expected: every command exits `0`.

- [ ] **Step 2: Request one batched independent review**

Review correctness, schema fidelity, malicious/malformed JSON safety, path
targetability, bounds, workspace behavior, exit semantics, Tach direction,
fixture privacy, documentation accuracy, and roadmap sequencing. Fix every
confirmed high/medium issue test-first, then rerun the smallest affected suite.

- [ ] **Step 3: Run fresh repository verification**

Run the full profile after the coherent final state:

```bash
PATH=.venv/bin:$PATH just v
```

Use the emitted run ID with `just wv <run-id>` or inspect the authoritative job
record when launchd wakeups are unavailable. Run `security` or `manual` only if
the final diff touches those gate definitions; parsing architecture output alone
does not require them.

- [ ] **Step 4: Inspect the final repository state**

```bash
git status --short --branch
git diff --check codex/typescript-osv-facts...HEAD
git diff --stat codex/typescript-osv-facts...HEAD
git diff --name-status codex/typescript-osv-facts...HEAD
git log --oneline codex/typescript-osv-facts..HEAD
```

Inspect the actual diff and scan it for credentials, private paths, and private
data. Verify that only intended files are staged or committed.

- [ ] **Step 5: Publish the stacked draft PR**

Push `codex/typescript-dependency-cruiser-facts`. Create a draft pull request
with base `codex/typescript-osv-facts`, explain that it stacks on PR #399, list
the parser/config/safety bounds and exact verification evidence, and state that
hosted CI must pass before merge. Never force-push or rewrite the Phase 180
branch.
