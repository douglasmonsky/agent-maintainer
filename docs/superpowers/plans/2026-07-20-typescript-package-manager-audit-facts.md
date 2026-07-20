# TypeScript Package-Manager Audit Facts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit npm, pnpm, Yarn, and Bun audit checks that produce deterministic, bounded, path-safe advisory facts and summaries for TypeScript projects.

**Architecture:** Keep command execution in the existing TypeScript provider and check runner. Pass an explicit structured-parser hint through check results, manifests, failure records, and exact-fact collection to one shared `agent_repair_facts` audit model, with one narrow adapter per package manager; the manager is never inferred from a command or report. Reuse that normalized result for compact summaries and repair facts, while retaining the current subprocess status and advisory-only semantics.

**Tech Stack:** Python 3.11+, frozen dataclasses, TOML configuration, bounded JSON/NDJSON parsing, pathlib path validation, pytest fixtures, Ruff, Pyright, Tach, Archguard, DocSync, and Markdownlint.

## Global Constraints

- Accept only the explicit managers `npm`, `pnpm`, `yarn`, and `bun`; never infer a manager from a command token, lockfile, manifest, Corepack metadata, or report shape.
- Pass configured command arrays unchanged to the existing runner; adapters do not execute subprocesses, access the network, inspect or mutate lockfiles, install tools, or autofix.
- Normalize package, severity, advisory IDs, vulnerable ranges, fixed versions, scope, directness, workspace, safe source path, manager, and bounded title/summary fields.
- Apply deterministic sorting before every limit: 500 findings/report, 25 IDs/ranges/fixes/finding, 200 characters/scalar, 50 summary lines, 1,000 characters/message, and the existing five exact facts/check.
- Accept supported JSON objects/arrays and bounded NDJSON; malformed neighbors may be skipped, but an entirely unsupported or undecodable report is `invalid-input` and falls back to bounded raw output.
- Keep parser outcomes equivalent to `clean`, `findings`, and `invalid-input` (0/1/2) separate from and subordinate to the exact subprocess exit status.
- Findings are advisory only; this slice adds no thresholds, allowlists, baselines, blocking promotion, dependency updates, or mutation.
- Use synthetic fixtures for all four managers and offline pinned npm/pnpm projections; document Yarn/Bun as fixture-only unless stable public captures are available.
- Keep TypeScript/JavaScript experimental, preserve existing profile and workspace semantics, and add explicit Tach ownership for every new domain edge.
- Generate configuration reference and capabilities files through their existing generator; do not hand-edit generated output or commit generated DocSync output.

---

## File Map

Create these focused files:

- `src/agent_repair_facts/parsers/typescript_package_manager_audit.py` — immutable normalized finding/result models, bounds, path safety, sorting, and shared rendering.
- `src/agent_repair_facts/parsers/typescript_package_manager_audit_adapters.py` — pure npm, pnpm, Yarn, and Bun JSON/NDJSON adapters.
- `src/agent_maintainer/core/structured_typescript.py` additions — audit summary dispatch keyed only by the explicit parser hint.
- `tests/fixtures/typescript_package_manager_audit/` — synthetic JSON, NDJSON, malformed, bounds, and path-safety fixtures.
- `tests/fixtures/typescript_package_manager_audit_external/` — sanitized pinned npm/pnpm projections and metadata.
- `tests/repair_facts/test_typescript_package_manager_audit_facts.py` — parser contract and rendering tests.
- `tests/assess/test_typescript_package_manager_audit_external.py` — offline replay tests for public projections.
- `docs/architecture/decisions/2026-07-20-typescript-package-manager-audit-facts.md` — recorded architecture decision.
- `docs/roadmap/phases/phase-192-typescript-package-manager-audit-facts.md` — phase evidence and completion gates.

Modify the existing provider/config/transport files:

- `src/agent_maintainer/config/schema.py`, `schema_fields.py`, `registry.py`, `coercion.py`, `validation.py`, `workspaces.py` — manager, command, and profile fields plus root/workspace validation.
- `src/agent_maintainer/models.py`, `src/agent_run_artifacts/models.py`, `src/agent_maintainer/verify/artifact_adapters.py`, `src/agent_run_artifacts/artifact_manifest.py`, `src/agent_context/failures.py` — optional `structured_parser` transport metadata.
- `src/agent_maintainer/ecosystems/typescript/provider.py`, `src/agent_maintainer/ecosystems/registry.py` — explicit checks and provider metadata.
- `src/agent_maintainer/core/executor.py`, `src/agent_maintainer/core/reporting.py`, `src/agent_repair_facts/registry.py`, `src/agent_maintainer/context/pack/exact_facts.py` — preserve the hint from execution to facts and summaries.
- `docs/typescript-javascript-provider.md`, `docs/provider-status.md`, `docs/roadmap/full-roadmap-blueprint.md`, `docs/roadmap/typescript-react-parity-roadmap.md`, `.docsync/trace.yml`, and focused docs tests — claims, roadmap, and trace ownership.
- Generated `docs/configuration-reference.md` and `config/agent-maintainer-capabilities.json` — refreshed only through the repository generator.

---

### Task 1: Add explicit audit configuration and provider checks

**Files:**

- Modify: `src/agent_maintainer/config/schema.py`
- Modify: `src/agent_maintainer/config/schema_fields.py`
- Modify: `src/agent_maintainer/config/registry.py`
- Modify: `src/agent_maintainer/config/coercion.py`
- Modify: `src/agent_maintainer/config/validation.py`
- Modify: `src/agent_maintainer/config/workspaces.py`
- Modify: `src/agent_maintainer/models.py`
- Modify: `src/agent_maintainer/ecosystems/typescript/provider.py`
- Modify: `src/agent_maintainer/ecosystems/registry.py`
- Test: `tests/config/test_typescript_config.py`
- Test: `tests/config/test_workspace_config.py`
- Test: `tests/catalogs/test_typescript_catalog.py`
- Test: `tests/catalogs/test_provider_registry.py`

**Interfaces:**

- Add `typescript_package_manager_audit_manager` as an empty-by-default string, `typescript_package_manager_audit_command` as an empty tuple of strings, and `typescript_package_manager_audit_profiles` as the tuple `("full", "ci")` to root and workspace configuration models.
- Add `structured_parser: str = ""` as the final defaulted field on `Check`; this preserves existing positional constructors while allowing the provider to label `typescript-package-manager-audit` checks.
- Extend `TypeScriptProvider._configured_check(name, command, profiles, config_field, *, structured_parser="") -> Check` and set the field only for the audit check.
- Register `ProviderCommandSpec("typescript-package-manager-audit", "typescript_package_manager_audit_command")` and expose the capability without claiming blocking security enforcement.

- [ ] **Step 1: Write configuration and provider contract tests.**

```python
def test_audit_manager_and_exact_command_are_loaded() -> None:
    loaded = loader.apply_pyproject(
        MaintainerConfig(),
        {
            "enable_typescript": True,
            "typescript_package_manager_audit_manager": "pnpm",
            "typescript_package_manager_audit_command": ["pnpm", "audit", "--json"],
        },
    )
    assert loaded.typescript_package_manager_audit_manager == "pnpm"
    assert loaded.typescript_package_manager_audit_command == ("pnpm", "audit", "--json")


def test_audit_check_keeps_manager_hint_and_command() -> None:
    config = replace(
        MaintainerConfig(),
        enable_typescript=True,
        typescript_package_manager_audit_manager="pnpm",
        typescript_package_manager_audit_command=("pnpm", "audit", "--json"),
    )
    checks = TypeScriptProvider(config).checks(profile="ci")
    check = next(item for item in checks if item.name == "typescript-package-manager-audit")
    assert check.command == ("pnpm", "audit", "--json")
    assert check.structured_parser == "typescript-package-manager-audit"
```

- [ ] **Step 2: Run the focused tests to verify the new contract fails.**

Run: `PATH="${PWD}/.venv/bin:$PATH" .venv/bin/pytest tests/config/test_typescript_config.py tests/config/test_workspace_config.py tests/catalogs/test_typescript_catalog.py tests/catalogs/test_provider_registry.py -q`

Expected: FAIL because the configuration fields and `Check.structured_parser` do not yet exist.

- [ ] **Step 3: Implement schema, coercion, and validation.**

Add the manager to the same field inventories as its command and profiles. Use an optional-string coercer that maps `None` and `""` to `""`, accepts only strings otherwise, and never derives a value from the command. Add cross-field diagnostics for a non-empty command without a valid manager and for an invalid non-empty manager. Add the manager and command to workspace coercion/defaults; preserve root profile selection for workspace checks.

- [ ] **Step 4: Implement provider checks and catalog metadata.**

Create root and workspace checks only when the existing TypeScript enablement/profile/path rules allow them. A configured manager without a command and a command without a valid manager use the existing optional configuration diagnostic and do not invoke a subprocess. Pass the command tuple unchanged and set the explicit parser hint. Add the command spec and capability metadata, then run the focused tests again.

Run: `PATH="${PWD}/.venv/bin:$PATH" .venv/bin/pytest tests/config/test_typescript_config.py tests/config/test_workspace_config.py tests/catalogs/test_typescript_catalog.py tests/catalogs/test_provider_registry.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the independently testable configuration slice.**

```bash
git add -- src/agent_maintainer/config/schema.py src/agent_maintainer/config/schema_fields.py src/agent_maintainer/config/registry.py src/agent_maintainer/config/coercion.py src/agent_maintainer/config/validation.py src/agent_maintainer/config/workspaces.py src/agent_maintainer/models.py src/agent_maintainer/ecosystems/typescript/provider.py src/agent_maintainer/ecosystems/registry.py tests/config/test_typescript_config.py tests/config/test_workspace_config.py tests/catalogs/test_typescript_catalog.py tests/catalogs/test_provider_registry.py
git commit -m "feat: configure TypeScript package-manager audits"
```

### Task 2: Build the shared normalized audit model and four adapters

**Files:**

- Create: `src/agent_repair_facts/parsers/typescript_package_manager_audit.py`
- Create: `src/agent_repair_facts/parsers/typescript_package_manager_audit_adapters.py`
- Create: `tests/fixtures/typescript_package_manager_audit/npm.json`
- Create: `tests/fixtures/typescript_package_manager_audit/pnpm.json`
- Create: `tests/fixtures/typescript_package_manager_audit/yarn.ndjson`
- Create: `tests/fixtures/typescript_package_manager_audit/bun.ndjson`
- Create: `tests/fixtures/typescript_package_manager_audit/malformed.ndjson`
- Test: `tests/repair_facts/test_typescript_package_manager_audit_facts.py`

**Interfaces:**

- Define frozen `PackageManagerAuditFinding` with fields `manager`, `package`, `severity`, `advisory_ids`, `vulnerable_ranges`, `fixed_versions`, `scope`, `directness`, `workspace`, `path`, `source_label`, and `title`.
- Define frozen `PackageManagerAuditParseResult` with fields `manager`, `workspace`, `outcome`, `findings`, `supported_count`, `retained_count`, and `omitted_count`.
- Export `parse_audit_report(manager: str, workspace: str, source_label: str, text: str) -> PackageManagerAuditParseResult` and `render_audit_summary(result: PackageManagerAuditParseResult, *, max_lines: int = 50, max_chars: int = 1000) -> str`.
- Keep adapter entry points pure: `parse_npm_payload`, `parse_pnpm_payload`, `parse_yarn_record`, and `parse_bun_payload` return raw records or no record; they receive decoded values and never read files or execute commands.

- [ ] **Step 1: Write failing fixture-backed tests for all manager projections.**

```python
@pytest.mark.parametrize(("manager", "fixture"), (("npm", "npm.json"), ("pnpm", "pnpm.json")))
def test_json_adapters_normalize_findings(manager: str, fixture: str) -> None:
    result = parse_audit_report(manager, "root", manager, fixture_text(fixture))
    assert result.outcome == "findings"
    assert result.findings[0].manager == manager
    assert result.findings[0].package == "lodash"
    assert result.findings[0].advisory_ids == ("GHSA-1234",)


def test_yarn_ndjson_keeps_valid_neighbors() -> None:
    result = parse_audit_report("yarn", "web", "yarn", fixture_text("yarn.ndjson"))
    assert result.supported_count == 1
    assert result.findings[0].workspace == "web"


def test_bun_ndjson_is_advisory_and_deterministic() -> None:
    result = parse_audit_report("bun", "root", "bun", fixture_text("bun.ndjson"))
    assert result.outcome == "findings"
    assert render_audit_summary(result).splitlines()[0].startswith("bun")
```

- [ ] **Step 2: Run the parser tests to verify they fail before implementation.**

Run: `PATH="${PWD}/.venv/bin:$PATH" .venv/bin/pytest tests/repair_facts/test_typescript_package_manager_audit_facts.py -q`

Expected: FAIL because the parser module and fixtures are absent.

- [ ] **Step 3: Add immutable models, bounds, and safe normalization.**

Implement severity normalization, bounded scalar/list helpers, explicit package/advisory validation, repository-relative path validation that rejects POSIX roots, Windows drives/UNC prefixes, dot segments, parent traversal, empty values, and overlong values, and deterministic sorting by manager, workspace, source, package, severity rank, advisory IDs, ranges, and fixes. Use constants `AUDIT_FACT_LIMIT = 500`, `AUDIT_LIST_LIMIT = 25`, `AUDIT_FIELD_CHAR_LIMIT = 200`, `AUDIT_PATH_CHAR_LIMIT = 500`, `AUDIT_MESSAGE_CHAR_LIMIT = 1000`, and `AUDIT_SUMMARY_LINE_LIMIT = 50`.

- [ ] **Step 4: Implement pure npm, pnpm, Yarn, and Bun adapters.**

Decode one JSON object/array or independent non-empty NDJSON lines. Accept only documented fields with an explicit package and advisory ID; do not synthesize IDs from URLs, ranges, package names, or line numbers. Preserve explicit scope/directness and fix/range metadata, ignore unsupported optional fields, and skip malformed neighbors while returning `invalid-input` when no supported container or record is decoded.

- [ ] **Step 5: Implement deduplication, outcomes, and rendering.**

Merge equivalent records only when manager, workspace, package, advisory IDs, ranges, and fixes agree. Return `clean` for a valid report with no findings, `findings` for one or more retained findings, and `invalid-input` for an unsupported/undecodable report. Render one bounded, truthful omission line at most 50 lines and 1,000 characters; keep parser outcome independent from subprocess status.

- [ ] **Step 6: Run the parser tests and commit.**

Run: `PATH="${PWD}/.venv/bin:$PATH" .venv/bin/pytest tests/repair_facts/test_typescript_package_manager_audit_facts.py -q`

Expected: PASS.

```bash
git add -- src/agent_repair_facts/parsers/typescript_package_manager_audit.py src/agent_repair_facts/parsers/typescript_package_manager_audit_adapters.py tests/fixtures/typescript_package_manager_audit tests/repair_facts/test_typescript_package_manager_audit_facts.py
git commit -m "feat: normalize TypeScript package-manager audit facts"
```

### Task 3: Transport the explicit parser hint and reuse the normalized result

**Files:**

- Modify: `src/agent_run_artifacts/models.py`
- Modify: `src/agent_maintainer/verify/artifact_adapters.py`
- Modify: `src/agent_run_artifacts/artifact_manifest.py`
- Modify: `src/agent_context/failures.py`
- Modify: `src/agent_maintainer/core/executor.py`
- Modify: `src/agent_maintainer/core/reporting.py`
- Modify: `src/agent_maintainer/core/structured_typescript.py`
- Modify: `src/agent_repair_facts/parsers/typescript_checks.py`
- Modify: `src/agent_repair_facts/registry.py`
- Modify: `src/agent_maintainer/context/pack/exact_facts.py`
- Test: `tests/core/test_executor_reporting.py`
- Test: `tests/core/test_reporting_artifacts.py`
- Test: `tests/context/test_failures.py`
- Test: `tests/context/test_exact_facts.py`
- Test: `tests/context/test_structured_fact_boundaries.py`
- Test: `tests/context/test_typescript_exact_facts.py`

**Interfaces:**

- Append `structured_parser: str = ""` to `CheckResult`, `ArtifactCheckResult`, and `FailureRecord`; serialize it only when non-empty so existing artifacts remain stable.
- Add `structured_parser: str = ""` to `check_payload` and copy it through `artifact_check_result`, executor result constructors, `record_from_payload`, and `FailureRecord.to_json`.
- Extend `summarize_check` and `summarize_check_from_artifacts` with keyword-only `structured_parser: str = ""`; route `"typescript-package-manager-audit"` to the shared parser.
- Extend `log_facts_from_text(check_name, path, text, *, structured_parser: str = "")` and pass the hint from `exact_facts.structured_facts`.

- [ ] **Step 1: Write failing transport and reuse tests.**

```python
def test_manifest_omits_empty_parser_hint_and_round_trips_nonempty() -> None:
    empty = check_payload(CheckResult(name="x", status="passed", structured_parser=""))
    labeled = check_payload(CheckResult(name="x", status="failed", structured_parser="typescript-package-manager-audit"))
    assert "structured_parser" not in empty
    assert labeled["structured_parser"] == "typescript-package-manager-audit"


def test_summary_and_exact_facts_use_the_same_audit_finding(tmp_path: Path) -> None:
    raw_output = '{"vulnerabilities":{"lodash":{"severity":"high","via":[{"source":"GHSA-1234","range":"<4.17.21"}]}}}'
    summary = summarize_check(
        "typescript-package-manager-audit",
        raw_output,
        50,
        1000,
        structured_parser="typescript-package-manager-audit",
    )
    log_path = tmp_path / "audit.log"
    log_path.write_text(raw_output, encoding="utf-8")
    record = FailureRecord(
        name="typescript-package-manager-audit",
        status="failed",
        category="security/tooling",
        priority=9,
        exit_code=1,
        log_path=str(log_path),
        log_bytes=len(raw_output.encode("utf-8")),
        expansion_commands=(),
        structured_parser="typescript-package-manager-audit",
    )
    facts = structured_facts(tmp_path, record)
    assert "GHSA-1234" in summary
    assert facts[0]["symbol"] == "GHSA-1234"
```

- [ ] **Step 2: Run the focused transport tests to verify they fail.**

Run: `PATH="${PWD}/.venv/bin:$PATH" .venv/bin/pytest tests/core/test_executor_reporting.py tests/core/test_reporting_artifacts.py tests/context/test_failures.py tests/context/test_exact_facts.py tests/context/test_structured_fact_boundaries.py tests/context/test_typescript_exact_facts.py -q`

Expected: FAIL because the metadata field and contextual parser dispatch are absent.

- [ ] **Step 3: Thread metadata through artifact and failure models.**

Add the defaulted field without changing positional call sites. Include it in manifests, result adapters, executor success/failure/missing-requirement/OSError paths, and failure-record JSON only when non-empty. Preserve the existing command, exit code, log, and artifact behavior byte-for-byte for unlabeled checks.

- [ ] **Step 4: Route summaries and exact facts by explicit hint.**

Pass the hint from `Check` into all reporting calls. In `structured_typescript`, call `parse_audit_report` only when the hint exactly equals `typescript-package-manager-audit`; never inspect `command[0]`, lockfiles, package manifests, or raw report shape to choose a manager. In the fact registry, call the same parser with the recorded manager/workspace/source context and format exact facts through the existing five-fact cap.

- [ ] **Step 5: Add registry/parser-family coverage and run focused tests.**

Run: `PATH="${PWD}/.venv/bin:$PATH" .venv/bin/pytest tests/core/test_executor_reporting.py tests/core/test_reporting_artifacts.py tests/context/test_failures.py tests/context/test_exact_facts.py tests/context/test_structured_fact_boundaries.py tests/context/test_typescript_exact_facts.py -q`

Expected: PASS, including a regression assertion that an audit command beginning with another executable cannot change the explicit manager.

- [ ] **Step 6: Commit the transport slice.**

```bash
git add -- src/agent_run_artifacts/models.py src/agent_maintainer/verify/artifact_adapters.py src/agent_run_artifacts/artifact_manifest.py src/agent_context/failures.py src/agent_maintainer/core/executor.py src/agent_maintainer/core/reporting.py src/agent_maintainer/core/structured_typescript.py src/agent_repair_facts/parsers/typescript_checks.py src/agent_repair_facts/registry.py src/agent_maintainer/context/pack/exact_facts.py tests/core/test_executor_reporting.py tests/core/test_reporting_artifacts.py tests/context/test_failures.py tests/context/test_exact_facts.py tests/context/test_structured_fact_boundaries.py tests/context/test_typescript_exact_facts.py
git commit -m "feat: reuse structured TypeScript audit facts"
```

### Task 4: Add pinned public projections and offline evidence gates

**Files:**

- Create: `tests/fixtures/typescript_package_manager_audit_external/npm-node-typescript-boilerplate.json`
- Create: `tests/fixtures/typescript_package_manager_audit_external/pnpm-eslint-plugin-vitest.json`
- Create: `tests/fixtures/typescript_package_manager_audit_external/README.md`
- Test: `tests/assess/test_typescript_package_manager_audit_external.py`
- Read: `tests/fixtures/typescript_external_reviewability/node_typescript_boilerplate_550dfd2_reviewability.json`
- Read: `tests/fixtures/typescript_external_reviewability/eslint_plugin_vitest_7c697f8_reviewability.json`

**Interfaces:**

- Each projection stores public repository URL, pinned revision, UTC collection time, manager/tool/runtime versions, exact command, exit status, report SHA-256/byte count, supported/retained/omitted counts, and bounded normalized findings.
- The fixture test accepts a `Path`, `manager`, `repository`, and `head_commit` and replays the saved projection without network, package installation, a clone, or a package-manager binary.

- [ ] **Step 1: Write the offline replay test.**

```python
@pytest.mark.parametrize(
    ("path", "manager", "repository", "head_commit"),
    (
        (NPM_PROJECTION, "npm", "jsynowiec/node-typescript-boilerplate", "550dfd2a976d69254ed71eb6f5a6c5ee20060807"),
        (PNPM_PROJECTION, "pnpm", "vitest-dev/eslint-plugin-vitest", "7c697f8a53d7d7551b00ef11217d58cd45a0cf7d"),
    ),
)
def test_pinned_audit_projection_replays_offline(path: Path, manager: str, repository: str, head_commit: str) -> None:
    payload = json.loads(path.read_text())
    assert payload["manager"] == manager
    assert payload["repository"] == repository
    assert payload["head_commit"] == head_commit
    result = parse_audit_report(manager, "root", repository, payload["report"])
    assert result.retained_count == payload["retained_count"]
```

- [ ] **Step 2: Run the external replay test to verify the fixtures are absent.**

Run: `PATH="${PWD}/.venv/bin:$PATH" .venv/bin/pytest tests/assess/test_typescript_package_manager_audit_external.py -q`

Expected: FAIL because the sanitized projections do not yet exist.

- [ ] **Step 3: Create sanitized npm and pnpm projection fixtures.**

Use the existing public reviewability fixture metadata and the pinned heads above. Store the exact captured report only when it is bounded and contains no credentials or local paths; otherwise store the normalized public projection plus report hash/byte count and omit the full report. Keep `report` a JSON string or bounded NDJSON text so the offline test exercises the same parser boundary as a command artifact.

- [ ] **Step 4: Add provenance and limitations documentation.**

Document collection date, tool/runtime versions, command, exit status, hashes, counts, and the fact that the projections are not live network tests. State explicitly that Yarn and Bun remain synthetic-only until a stable public capture is reproducible.

- [ ] **Step 5: Run the replay and parser suites and commit.**

Run: `PATH="${PWD}/.venv/bin:$PATH" .venv/bin/pytest tests/assess/test_typescript_package_manager_audit_external.py tests/repair_facts/test_typescript_package_manager_audit_facts.py -q`

Expected: PASS with no network access or package-manager invocation.

```bash
git add -- tests/fixtures/typescript_package_manager_audit_external tests/assess/test_typescript_package_manager_audit_external.py
git commit -m "test: add pinned TypeScript audit projections"
```

### Task 5: Update architecture, docs, generated references, and roadmap evidence

**Files:**

- Create: `docs/architecture/decisions/2026-07-20-typescript-package-manager-audit-facts.md`
- Create: `docs/roadmap/phases/phase-192-typescript-package-manager-audit-facts.md`
- Modify: `docs/typescript-javascript-provider.md`
- Modify: `docs/provider-status.md`
- Modify: `docs/roadmap/full-roadmap-blueprint.md`
- Modify: `docs/roadmap/typescript-react-parity-roadmap.md`
- Modify: `.docsync/trace.yml`
- Modify: `tests/docs/test_first_touch_docs.py`
- Modify: `tests/docs/test_public_docs_prose.py`
- Modify: `tests/docs/test_roadmap_docs.py`
- Modify: `tests/config/test_config_reference.py`
- Generate: `docs/configuration-reference.md`
- Generate: `config/agent-maintainer-capabilities.json`

**Interfaces:**

- The ADR records the selected shared model, explicit manager boundary, advisory semantics, bounds, and rejected alternatives.
- Phase 192 records implementation commit SHAs, focused/full checks, two pinned projections, fixture-only Yarn/Bun status, and the remaining roadmap order.
- Public docs use the exact configuration keys and claim “normalized advisory facts,” never automatic manager selection or blocking security review.

- [ ] **Step 1: Write docs and roadmap tests for the new claims.**

```python
def test_typescript_docs_describe_explicit_audit_manager() -> None:
    prose = Path("docs/typescript-javascript-provider.md").read_text()
    assert "typescript_package_manager_audit_manager" in prose
    assert "advisory" in prose
    assert "manager is never inferred" in prose


def test_phase_192_is_listed_after_phase_191() -> None:
    roadmap = Path("docs/roadmap/full-roadmap-blueprint.md").read_text()
    assert roadmap.index("Phase 191") < roadmap.index("Phase 192")
```

- [ ] **Step 2: Run the docs tests to verify the claims are not yet present.**

Run: `PATH="${PWD}/.venv/bin:$PATH" .venv/bin/pytest tests/docs/test_first_touch_docs.py tests/docs/test_public_docs_prose.py tests/docs/test_roadmap_docs.py tests/config/test_config_reference.py -q`

Expected: FAIL on the new manager, advisory, and Phase 192 assertions.

- [ ] **Step 3: Write the ADR and phase record.**

Copy the approved decision into concise architecture prose, list the exact normalized fields and limits, state that parser outcomes do not override subprocess status, and record the two pinned public projections plus synthetic-only Yarn/Bun evidence. Assign this slice Phase 192 because Phase 185 is reserved for failure intelligence and Phases 186–191 are the C/C++ sequence already on the roadmap.

- [ ] **Step 4: Update provider docs, status, roadmap, and DocSync.**

Add root/workspace examples for npm, pnpm, Yarn, and Bun, a supported projection matrix, path-safety and deterministic-bound rules, and an advisory-only note. Remove the stale “package-manager audit not implemented” claim while retaining the not-yet-implemented mutation/blocking claims. Add Phase 192 after Phase 191 and link its evidence. Add trace claims/evidence for configuration ownership, parser bounds, public projections, and fixture-only limitations.

- [ ] **Step 5: Regenerate references and run docs checks.**

Run: `PATH="${PWD}/.venv/bin:$PATH" .venv/bin/python -m agent_maintainer.config.reference`

Then run: `PATH="${PWD}/.venv/bin:$PATH" .venv/bin/pytest tests/docs/test_first_touch_docs.py tests/docs/test_public_docs_prose.py tests/docs/test_roadmap_docs.py tests/config/test_config_reference.py -q`

Expected: PASS; generated files change only through the reference command.

- [ ] **Step 6: Commit documentation and evidence metadata.**

```bash
git add -- docs/architecture/decisions/2026-07-20-typescript-package-manager-audit-facts.md docs/roadmap/phases/phase-192-typescript-package-manager-audit-facts.md docs/typescript-javascript-provider.md docs/provider-status.md docs/roadmap/full-roadmap-blueprint.md docs/roadmap/typescript-react-parity-roadmap.md .docsync/trace.yml tests/docs/test_first_touch_docs.py tests/docs/test_public_docs_prose.py tests/docs/test_roadmap_docs.py tests/config/test_config_reference.py docs/configuration-reference.md config/agent-maintainer-capabilities.json
git commit -m "docs: document TypeScript audit facts"
```

### Task 6: Run the full verification gate and prepare handoff

**Files:**

- Read: all files changed in Tasks 1–5
- Test: repository verification commands and the final diff

**Interfaces:**

- No new public interface; this task proves the complete contract and records the exact evidence used for handoff.

- [ ] **Step 1: Run focused functional, parser, transport, and docs checks.**

Run: `PATH="${PWD}/.venv/bin:$PATH" .venv/bin/pytest tests/config/test_typescript_config.py tests/config/test_workspace_config.py tests/catalogs/test_typescript_catalog.py tests/catalogs/test_provider_registry.py tests/repair_facts/test_typescript_package_manager_audit_facts.py tests/core/test_executor_reporting.py tests/core/test_reporting_artifacts.py tests/context/test_failures.py tests/context/test_exact_facts.py tests/context/test_structured_fact_boundaries.py tests/context/test_typescript_exact_facts.py tests/assess/test_typescript_package_manager_audit_external.py tests/docs/test_first_touch_docs.py tests/docs/test_public_docs_prose.py tests/docs/test_roadmap_docs.py tests/config/test_config_reference.py -q`

Expected: PASS.

- [ ] **Step 2: Run static and architecture gates.**

Run: `PATH="${PWD}/.venv/bin:$PATH" .venv/bin/ruff check src tests`

Run: `PATH="${PWD}/.venv/bin:$PATH" .venv/bin/pyright`

Run: `PATH="${PWD}/.venv/bin:$PATH" .venv/bin/python -m tach check`

Run: `PATH="${PWD}/.venv/bin:$PATH" .venv/bin/python -m archguard check`

Expected: PASS with an ownership edge for the new parser domain and no relaxed policy.

- [ ] **Step 3: Run the repository's complete local verification.**

Run: `PATH="${PWD}/.venv/bin:$PATH" just verify`

Expected: PASS, or a recorded pre-existing failure packet that is not caused by these changes.

- [ ] **Step 4: Inspect status, diff, and staged content for safety.**

Run: `git status --short --branch`, `git diff --stat`, `git diff --check`, `git diff --name-only`, and `git diff --cached --name-only` from the canonical worktree. Confirm no `.env`, credentials, private records, full external reports, local absolute paths, generated DocSync output, or unrelated user changes are staged.

- [ ] **Step 5: Record the phase evidence and final focused commit.**

Update the Phase 192 record with the actual commit SHAs and command results, stage only the phase record if it changed, and commit with:

```bash
git add -- docs/roadmap/phases/phase-192-typescript-package-manager-audit-facts.md
git commit -m "chore: record TypeScript audit facts verification"
```

Expected: clean worktree with the implementation commits listed in the phase record; do not push or release until the user separately requests publication.

## Self-Review Checklist

- [ ] Every spec goal, non-goal, bound, outcome, safety rule, evidence requirement, documentation claim, and architecture gate maps to a named task.
- [ ] No step relies on placeholder language or an unspecified implementation; each code-changing step names files, interfaces, and concrete checks.
- [ ] `PackageManagerAuditFinding`, `PackageManagerAuditParseResult`, `parse_audit_report`, `render_audit_summary`, and `structured_parser` use the same names and types in every task.
- [ ] The only manager selection input is explicit configuration transported through the check result; command tokens and report shapes are never used for inference.
- [ ] Generated configuration files are refreshed by the existing generator, and external fixtures contain only bounded public metadata/projections.
- [ ] Phase 192 remains after Phase 191 and before later generated-policy and blocking-promotion assessment work.
